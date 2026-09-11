from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_current_user
from config import settings
from database import get_db
from models import (
    User, AiTask, AiTaskEvent, AiCall,
    TASK_STATUS_QUEUED, TASK_STATUS_RUNNING, TASK_STATUS_SUCCESS,
    TASK_STATUS_FAILED, TASK_STATUS_DEAD_LETTER, TASK_STATUS_CANCELLED,
)
from schemas import AiTaskOut, AiTaskDetailOut, AiTaskStatsOut
from ai.queue import get_queue, estimated_wait


router = APIRouter(prefix="/api/ai/tasks", tags=["ai-tasks"])


def _ensure_owner(task: Optional[AiTask], user_id: int) -> AiTask:
    if not task or task.user_id != user_id:
        raise HTTPException(404, "任务不存在或无权访问")
    return task


@router.get("", response_model=List[AiTaskOut])
def list_tasks(
    status: Optional[str] = Query(None, description="按状态过滤：queued/running/success/failed/dead_letter/cancelled"),
    task_key: Optional[str] = None,
    script_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    q = db.query(AiTask).filter(AiTask.user_id == current.id)
    if status:
        q = q.filter(AiTask.status == status)
    if task_key:
        q = q.filter(AiTask.task_key == task_key)
    if script_id:
        q = q.filter(AiTask.script_id == script_id)
    rows = q.order_by(AiTask.created_at.desc()).offset(offset).limit(limit).all()

    result = []
    running = db.query(func.count(AiTask.id)).filter(AiTask.status == TASK_STATUS_RUNNING).scalar() or 0
    for t in rows:
        wait = 0
        if t.status == TASK_STATUS_QUEUED:
            wait = estimated_wait(db, t)
        result.append(AiTaskOut(
            id=t.id, task_key=t.task_key, skill_name=t.skill_name, user_id=t.user_id,
            script_id=t.script_id, provider_name=t.provider_name, model_name=t.model_name,
            status=t.status, priority=t.priority, progress=t.progress, phase=t.phase,
            error_class=t.error_class, error_msg=t.error_msg,
            attempts=t.attempts, max_retries=t.max_retries,
            queue_wait_ms=t.queue_wait_ms, exec_ms=t.exec_ms, total_ms=t.total_ms,
            input_tokens=t.input_tokens, output_tokens=t.output_tokens,
            result_json=t.result_json,
            created_at=t.created_at, started_at=t.started_at, finished_at=t.finished_at,
            estimated_wait_sec=wait, worker_id=t.worker_id,
        ))
    return result


@router.get("/stats", response_model=AiTaskStatsOut)
def task_stats(
    since_hours: int = Query(24, ge=1, le=720),
    scope: str = Query("me", description="me=只看自己，all=管理员看全局"),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    since = datetime.utcnow() - timedelta(hours=since_hours)
    base = db.query(AiTask).filter(AiTask.created_at >= since)
    if scope == "me":
        base = base.filter(AiTask.user_id == current.id)

    total = base.count()
    def cnt(st):
        return base.filter(AiTask.status == st).count()

    def group_by(col):
        rows = (
            base.with_entities(col, func.count(AiTask.id))
                .filter(col.isnot(None)).group_by(col).all()
        )
        return {str(k): int(v) for k, v in rows}

    done = base.filter(AiTask.status == TASK_STATUS_SUCCESS)
    avg_lat = done.with_entities(func.avg(AiTask.exec_ms)).scalar() or 0
    avg_wait = base.filter(AiTask.status.in_([TASK_STATUS_SUCCESS, TASK_STATUS_FAILED, TASK_STATUS_DEAD_LETTER])).with_entities(
        func.avg(AiTask.queue_wait_ms)).scalar() or 0
    total_in = done.with_entities(func.coalesce(func.sum(AiTask.input_tokens), 0)).scalar() or 0
    total_out = done.with_entities(func.coalesce(func.sum(AiTask.output_tokens), 0)).scalar() or 0

    return AiTaskStatsOut(
        total=total,
        queued=cnt(TASK_STATUS_QUEUED),
        running=cnt(TASK_STATUS_RUNNING),
        success=cnt(TASK_STATUS_SUCCESS),
        failed=cnt(TASK_STATUS_FAILED),
        dead_letter=cnt(TASK_STATUS_DEAD_LETTER),
        cancelled=cnt(TASK_STATUS_CANCELLED),
        concurrency=settings.queue_max_concurrency,
        by_task_key=group_by(AiTask.task_key),
        by_provider=group_by(AiTask.provider_name),
        by_error_class=group_by(AiTask.error_class),
        avg_latency_ms=round(float(avg_lat), 1),
        avg_queue_wait_ms=round(float(avg_wait), 1),
        total_input_tokens=int(total_in),
        total_output_tokens=int(total_out),
    )


@router.get("/{task_id}", response_model=AiTaskDetailOut)
def get_task(
    task_id: int,
    include_events: bool = Query(True),
    include_result_text: bool = Query(True),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    t = _ensure_owner(db.query(AiTask).filter(AiTask.id == task_id).first(), current.id)
    events_out = []
    if include_events:
        evs = db.query(AiTaskEvent).filter(AiTaskEvent.task_id == task_id).order_by(AiTaskEvent.seq.asc()).all()
        events_out = evs
    wait = estimated_wait(db, t) if t.status == TASK_STATUS_QUEUED else 0
    return AiTaskDetailOut(
        id=t.id, task_key=t.task_key, skill_name=t.skill_name, user_id=t.user_id,
        script_id=t.script_id, provider_name=t.provider_name, model_name=t.model_name,
        status=t.status, priority=t.priority, progress=t.progress, phase=t.phase,
        error_class=t.error_class, error_msg=t.error_msg,
        attempts=t.attempts, max_retries=t.max_retries,
        queue_wait_ms=t.queue_wait_ms, exec_ms=t.exec_ms, total_ms=t.total_ms,
        input_tokens=t.input_tokens, output_tokens=t.output_tokens,
        result_json=t.result_json, result_text=t.result_text if include_result_text else None,
        events=events_out,
        created_at=t.created_at, started_at=t.started_at, finished_at=t.finished_at,
        estimated_wait_sec=wait, worker_id=t.worker_id,
    )


@router.post("/{task_id}/cancel", response_model=AiTaskOut)
def cancel_task(task_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    q = get_queue()
    ok = q.cancel(db, task_id, current.id)
    if not ok:
        t = db.query(AiTask).filter(AiTask.id == task_id).first()
        if not t or t.user_id != current.id:
            raise HTTPException(404, "任务不存在或无权访问")
        raise HTTPException(400, f"当前状态 {t.status} 无法取消")
    return get_task(task_id, False, False, db, current)


@router.post("/{task_id}/retry", response_model=AiTaskOut)
def retry_task(task_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    q = get_queue()
    t = q.retry(db, task_id, current.id)
    if not t:
        existing = db.query(AiTask).filter(AiTask.id == task_id).first()
        if not existing or existing.user_id != current.id:
            raise HTTPException(404, "任务不存在或无权访问")
        raise HTTPException(400, f"当前状态 {existing.status} 不允许重试")
    db.refresh(t)
    wait = estimated_wait(db, t)
    return AiTaskOut(
        id=t.id, task_key=t.task_key, skill_name=t.skill_name, user_id=t.user_id,
        script_id=t.script_id, provider_name=t.provider_name, model_name=t.model_name,
        status=t.status, priority=t.priority, progress=t.progress, phase=t.phase,
        error_class=t.error_class, error_msg=t.error_msg,
        attempts=t.attempts, max_retries=t.max_retries,
        queue_wait_ms=t.queue_wait_ms, exec_ms=t.exec_ms, total_ms=t.total_ms,
        input_tokens=t.input_tokens, output_tokens=t.output_tokens,
        result_json=t.result_json,
        created_at=t.created_at, started_at=t.started_at, finished_at=t.finished_at,
        estimated_wait_sec=wait, worker_id=t.worker_id,
    )


@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    t = _ensure_owner(db.query(AiTask).filter(AiTask.id == task_id).first(), current.id)
    if t.status in (TASK_STATUS_QUEUED, TASK_STATUS_RUNNING):
        raise HTTPException(400, "任务进行中，请先取消再删除")
    db.query(AiTaskEvent).filter(AiTaskEvent.task_id == task_id).delete()
    db.delete(t)
    db.commit()
    return {"ok": True}
