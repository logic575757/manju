import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple

from sqlalchemy import and_, func, update
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal
from models import (
    AiTask, AiTaskEvent,
    TASK_STATUS_QUEUED, TASK_STATUS_RUNNING, TASK_STATUS_SUCCESS,
    TASK_STATUS_FAILED, TASK_STATUS_CANCELLED, TASK_STATUS_DEAD_LETTER,
    ERROR_CLASS_TIMEOUT, ERROR_CLASS_CANCELLED, ERROR_CLASS_UNKNOWN,
)


def _utcnow() -> datetime:
    return datetime.utcnow()


class TaskQueue:
    """基于数据库的任务队列。

    设计要点：
    - 用 SELECT ... FOR UPDATE 行锁 + status 原子切换实现多 worker 抢占，无中心化协调者
    - 每个 running 任务必须定期 heartbeat；超过 stale_timeout 无心跳视为 worker 崩溃，自动回收为 queued
    - 所有事件（phase/delta/progress/result/error）双写 ai_task_events 表，便于断线重连 + 事后分析
    """

    def __init__(self, worker_id: Optional[str] = None):
        self.worker_id = worker_id or f"w-{uuid.uuid4().hex[:8]}"

    # ---------- 提交 ----------
    def submit(
        self,
        db: Session,
        *,
        task_key: str,
        user_id: int,
        params: Dict[str, Any],
        script_id: Optional[int] = None,
        version_id: Optional[int] = None,
        priority: int = 100,
        max_retries: Optional[int] = None,
        skill_name: Optional[str] = None,
    ) -> AiTask:
        pending_count = db.query(func.count(AiTask.id)).filter(
            AiTask.user_id == user_id,
            AiTask.status.in_([TASK_STATUS_QUEUED, TASK_STATUS_RUNNING]),
        ).scalar() or 0
        if pending_count >= settings.queue_user_max_pending:
            raise RuntimeError(
                f"您当前有 {pending_count} 个任务在排队/执行中，请等待或取消部分任务后再试（上限 {settings.queue_user_max_pending}）"
            )

        task = AiTask(
            task_key=task_key,
            skill_name=skill_name or task_key,
            user_id=user_id,
            script_id=script_id,
            version_id=version_id,
            priority=priority,
            params=params,
            status=TASK_STATUS_QUEUED,
            max_retries=settings.queue_max_retries if max_retries is None else max_retries,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        db.add(task)
        db.flush()
        self.append_event(db, task.id, event_type="queued", meta={
            "worker": None, "priority": priority,
        })
        db.commit()
        db.refresh(task)
        return task

    # ---------- 事件追加 ----------
    def append_event(
        self,
        db: Session,
        task_id: int,
        event_type: str,
        phase: Optional[str] = None,
        progress: Optional[int] = None,
        data: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> AiTaskEvent:
        mx = db.query(func.max(AiTaskEvent.seq)).filter(AiTaskEvent.task_id == task_id).scalar()
        seq = (mx or 0) + 1
        evt = AiTaskEvent(
            task_id=task_id,
            seq=seq,
            event_type=event_type,
            phase=phase,
            progress=progress,
            data=data,
            meta=meta,
            created_at=_utcnow(),
        )
        db.add(evt)
        db.flush()
        return evt

    # ---------- Worker 抢占一个任务 ----------
    def claim_next(self, db: Session) -> Optional[AiTask]:
        """原子地挑一个最早的 queued 任务，把它切到 running 并绑定自己 worker_id。"""
        stale_cutoff = _utcnow() - timedelta(seconds=settings.queue_stale_timeout)
        db.execute(
            update(AiTask).where(
                AiTask.status == TASK_STATUS_RUNNING,
                AiTask.heartbeat_at < stale_cutoff,
            ).values(
                status=TASK_STATUS_QUEUED,
                worker_id=None,
                heartbeat_at=None,
                error_class=ERROR_CLASS_TIMEOUT,
                error_msg="worker 心跳超时，任务重新入队",
            )
        )

        cancelled = db.query(AiTask).filter(
            AiTask.status == TASK_STATUS_CANCELLED,
        ).update({"cancelled_at": AiTask.cancelled_at or _utcnow()}, synchronize_session=False)

        row = db.query(AiTask).filter(
            AiTask.status == TASK_STATUS_QUEUED,
        ).order_by(
            AiTask.priority.desc(), AiTask.created_at.asc(),
        ).with_for_update(skip_locked=True).first()

        if row is None:
            db.commit()
            return None

        now = _utcnow()
        wait_ms = int((now - row.created_at).total_seconds() * 1000) if row.created_at else 0
        row.status = TASK_STATUS_RUNNING
        row.worker_id = self.worker_id
        row.started_at = row.started_at or now
        row.heartbeat_at = now
        row.attempts = (row.attempts or 0) + 1
        row.queue_wait_ms = wait_ms
        row.phase = "开始处理"
        row.progress = 1
        db.flush()
        self.append_event(db, row.id, event_type="started",
                          phase=row.phase, progress=1, meta={
                              "worker": self.worker_id, "attempt": row.attempts, "queue_wait_ms": wait_ms,
                          })
        db.commit()
        db.refresh(row)
        return row

    # ---------- 心跳 ----------
    def heartbeat(self, db: Session, task_id: int, progress: Optional[int] = None, phase: Optional[str] = None):
        now = _utcnow()
        q = db.query(AiTask).filter(AiTask.id == task_id, AiTask.worker_id == self.worker_id)
        updates = {"heartbeat_at": now, "updated_at": now}
        if progress is not None:
            updates["progress"] = min(max(int(progress), 0), 99)
        if phase is not None:
            updates["phase"] = phase
        q.update(updates, synchronize_session=False)
        db.commit()

    # ---------- 中间事件（phase/delta/progress） ----------
    def emit_phase(self, db: Session, task_id: int, phase: str, progress: Optional[int] = None):
        if progress is not None:
            db.query(AiTask).filter(AiTask.id == task_id).update(
                {"phase": phase, "progress": min(max(int(progress), 0), 99),
                 "heartbeat_at": _utcnow(), "updated_at": _utcnow()},
                synchronize_session=False,
            )
        else:
            db.query(AiTask).filter(AiTask.id == task_id).update(
                {"phase": phase, "heartbeat_at": _utcnow(), "updated_at": _utcnow()},
                synchronize_session=False,
            )
        self.append_event(db, task_id, event_type="phase", phase=phase, progress=progress)
        db.commit()

    def emit_delta(self, db: Session, task_id: int, text: str):
        self.append_event(db, task_id, event_type="delta", data=text)
        db.query(AiTask).filter(AiTask.id == task_id).update(
            {"heartbeat_at": _utcnow(), "updated_at": _utcnow()}, synchronize_session=False,
        )
        db.commit()

    def emit_progress(self, db: Session, task_id: int, progress: int, phase: Optional[str] = None):
        updates = {"progress": min(max(int(progress), 0), 99),
                   "heartbeat_at": _utcnow(), "updated_at": _utcnow()}
        if phase:
            updates["phase"] = phase
        db.query(AiTask).filter(AiTask.id == task_id).update(updates, synchronize_session=False)
        self.append_event(db, task_id, event_type="progress", phase=phase, progress=progress)
        db.commit()

    # ---------- 结束 ----------
    def mark_success(
        self,
        db: Session,
        task_id: int,
        result_json: Any = None,
        result_text: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        exec_ms: int = 0,
    ):
        now = _utcnow()
        task = db.query(AiTask).filter(AiTask.id == task_id).first()
        if not task:
            return
        total_ms = int((now - task.created_at).total_seconds() * 1000) if task.created_at else exec_ms
        task.status = TASK_STATUS_SUCCESS
        task.progress = 100
        task.phase = "完成"
        task.result_json = result_json
        task.result_text = result_text
        task.input_tokens = input_tokens
        task.output_tokens = output_tokens
        task.exec_ms = exec_ms
        task.total_ms = total_ms
        task.finished_at = now
        task.updated_at = now
        task.error_class = None
        task.error_msg = None
        task.worker_id = None
        self.append_event(db, task_id, event_type="result", phase="完成", progress=100,
                          data=json.dumps(result_json, ensure_ascii=False) if result_json is not None else None,
                          meta={"input_tokens": input_tokens, "output_tokens": output_tokens,
                                "exec_ms": exec_ms, "total_ms": total_ms})
        self.append_event(db, task_id, event_type="done", phase="完成", progress=100,
                          meta={"total_ms": total_ms})
        db.commit()

    def mark_failed(
        self,
        db: Session,
        task_id: int,
        error_class: str,
        error_msg: str,
        will_retry: bool = False,
        exec_ms: int = 0,
    ):
        now = _utcnow()
        task = db.query(AiTask).filter(AiTask.id == task_id).first()
        if not task:
            return
        if will_retry:
            task.status = TASK_STATUS_QUEUED
            task.worker_id = None
            task.heartbeat_at = None
            task.error_class = error_class
            task.error_msg = error_msg
            task.phase = f"失败，准备第 {task.attempts + 1} 次重试"
            self.append_event(db, task_id, event_type="retry", phase=task.phase,
                              meta={"error_class": error_class, "error_msg": error_msg,
                                    "attempt": task.attempts, "next_attempt": task.attempts + 1})
        else:
            task.status = TASK_STATUS_DEAD_LETTER if task.attempts > task.max_retries else TASK_STATUS_FAILED
            task.worker_id = None
            task.error_class = error_class
            task.error_msg = error_msg
            task.finished_at = now
            task.total_ms = int((now - task.created_at).total_seconds() * 1000) if task.created_at else exec_ms
            task.exec_ms = exec_ms
            self.append_event(db, task_id, event_type="error", phase="失败",
                              meta={"error_class": error_class, "error_msg": error_msg,
                                    "attempt": task.attempts, "dead_letter": task.status == TASK_STATUS_DEAD_LETTER})
        task.updated_at = now
        db.commit()

    def cancel(self, db: Session, task_id: int, user_id: int) -> bool:
        task = db.query(AiTask).filter(AiTask.id == task_id, AiTask.user_id == user_id).first()
        if not task:
            return False
        if task.status in (TASK_STATUS_SUCCESS, TASK_STATUS_FAILED, TASK_STATUS_DEAD_LETTER, TASK_STATUS_CANCELLED):
            return False
        now = _utcnow()
        task.status = TASK_STATUS_CANCELLED
        task.cancelled_at = now
        task.finished_at = now
        task.error_class = ERROR_CLASS_CANCELLED
        task.error_msg = "用户取消"
        task.worker_id = None
        task.updated_at = now
        self.append_event(db, task_id, event_type="cancelled", meta={"at": now.isoformat()})
        db.commit()
        return True

    def retry(self, db: Session, task_id: int, user_id: int) -> Optional[AiTask]:
        task = db.query(AiTask).filter(AiTask.id == task_id, AiTask.user_id == user_id).first()
        if not task:
            return None
        if task.status not in (TASK_STATUS_FAILED, TASK_STATUS_DEAD_LETTER, TASK_STATUS_CANCELLED):
            return None
        task.status = TASK_STATUS_QUEUED
        task.priority = (task.priority or 100) + 10
        task.attempts = 0
        task.worker_id = None
        task.heartbeat_at = None
        task.started_at = None
        task.finished_at = None
        task.cancelled_at = None
        task.progress = 0
        task.phase = "等待重试"
        task.error_class = None
        task.error_msg = None
        task.result_json = None
        task.result_text = None
        task.input_tokens = 0
        task.output_tokens = 0
        task.queue_wait_ms = 0
        task.exec_ms = 0
        task.total_ms = 0
        task.updated_at = _utcnow()
        db.query(AiTaskEvent).filter(AiTaskEvent.task_id == task_id).delete()
        db.flush()
        self.append_event(db, task_id, event_type="queued", meta={"retry_of": task_id})
        db.commit()
        db.refresh(task)
        return task


_queue_instance: Optional[TaskQueue] = None


def get_queue() -> TaskQueue:
    global _queue_instance
    if _queue_instance is None:
        _queue_instance = TaskQueue()
    return _queue_instance


def estimated_wait(db: Session, task: AiTask) -> int:
    ahead = db.query(func.count(AiTask.id)).filter(
        AiTask.status == TASK_STATUS_QUEUED,
        (AiTask.priority > task.priority) | (
            and_(AiTask.priority == task.priority, AiTask.created_at < task.created_at)
        ),
    ).scalar() or 0
    running = db.query(func.count(AiTask.id)).filter(AiTask.status == TASK_STATUS_RUNNING).scalar() or 0
    avg_latency = db.query(func.avg(AiTask.exec_ms)).filter(
        AiTask.status == TASK_STATUS_SUCCESS,
        AiTask.task_key == task.task_key,
    ).scalar() or 30000
    batches = max(1, (ahead + max(0, settings.queue_max_concurrency - running)) // max(1, settings.queue_max_concurrency))
    return int(batches * float(avg_latency) / 1000)
