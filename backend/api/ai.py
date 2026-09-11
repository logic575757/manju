import asyncio
import json
import time
from typing import Optional, Any, Dict, Type

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import (
    User, Script, AiTask, AiTaskEvent, AiSkill,
    TASK_STATUS_QUEUED, TASK_STATUS_RUNNING, TASK_STATUS_SUCCESS,
    TASK_STATUS_FAILED, TASK_STATUS_DEAD_LETTER, TASK_STATUS_CANCELLED,
)
from schemas import (
    AiGenerateOutlineReq, AiModuleModifyReq, AiBatchModifyReq,
    AiReviewOutlineReq, AiReviewCharactersReq, AiGenerateCharactersReq,
    AiGenerateEpisodeReq, AiReviewEpisodeReq, AiFixEpisodeReq,
    AiRewriteSegmentReq, AiParseImportReq, AiTaskSubmitOut,
)
from ai.queue import get_queue, estimated_wait
from ai.skills_registry import BUILTIN_SKILLS


router = APIRouter(prefix="/api/ai", tags=["ai"])


class GenericSkillReq(BaseModel):
    model_config = ConfigDict(extra="allow")


SCHEMA_MAP: Dict[str, Type[BaseModel]] = {
    "generate_outline": AiGenerateOutlineReq,
    "review_outline": AiReviewOutlineReq,
    "modify_outline_module": AiModuleModifyReq,
    "batch_modify_outline": AiBatchModifyReq,
    "generate_characters": AiGenerateCharactersReq,
    "review_characters": AiReviewCharactersReq,
    "generate_episode": AiGenerateEpisodeReq,
    "review_episode": AiReviewEpisodeReq,
    "fix_episode": AiFixEpisodeReq,
    "rewrite_segment": AiRewriteSegmentReq,
    "parse_import": AiParseImportReq,
}


def _load_skill(db: Session, task_key: str) -> AiSkill:
    skill = db.query(AiSkill).filter(AiSkill.key == task_key, AiSkill.is_active == True).first()
    if not skill:
        raise HTTPException(404, f"Skill 不存在或已禁用: {task_key}")
    return skill


def _check_script_access(script_id: Optional[int], user_id: int, db: Session) -> Optional[Script]:
    if not script_id:
        return None
    script = db.query(Script).filter(Script.id == script_id, Script.owner_id == user_id).first()
    if not script:
        raise HTTPException(404, "剧本不存在或无权访问")
    return script


def _sse_stream(generator, media_type="text/event-stream"):
    return StreamingResponse(
        generator,
        media_type=media_type,
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse_fmt(event: str, data: Any, sep: str = "\n\n") -> str:
    if not isinstance(data, str):
        data = json.dumps(data, ensure_ascii=False)
    return f"event:{event}\ndata:{data}{sep}"


def _submit(task_key: str, payload, user: User, db: Session) -> AiTaskSubmitOut:
    skill = _load_skill(db, task_key)
    params = payload.model_dump() if hasattr(payload, "model_dump") else dict(payload)
    script_field = skill.script_id_field
    script_id = params.get(script_field) if script_field else None
    version_id = params.get("version_id")
    _check_script_access(script_id, user.id, db)
    q = get_queue()
    try:
        task = q.submit(
            db,
            task_key=task_key,
            skill_name=skill.name,
            user_id=user.id,
            script_id=script_id,
            version_id=version_id,
            params=params,
            priority=int(skill.priority or 100),
        )
    except RuntimeError as e:
        raise HTTPException(429, str(e))
    wait_sec = estimated_wait(db, task)
    ahead = db.query(func.count(AiTask.id)).filter(
        AiTask.status == TASK_STATUS_QUEUED,
        AiTask.id < task.id,
    ).scalar() or 0
    return AiTaskSubmitOut(
        task_id=task.id,
        status=task.status,
        position=ahead + 1,
        estimated_wait_sec=wait_sec,
        stream_url=f"/api/ai/tasks/{task.id}/stream",
    )


def _make_endpoint(task_key: str):
    schema_cls = SCHEMA_MAP.get(task_key, GenericSkillReq)

    async def endpoint(
        payload: schema_cls,
        db: Session = Depends(get_db),
        current: User = Depends(get_current_user),
    ):
        return _submit(task_key, payload, current, db)

    endpoint.__name__ = f"submit_{task_key}"
    return endpoint


def _register_builtin_routes():
    for task_key, meta in BUILTIN_SKILLS.items():
        router.add_api_route(
            "/" + meta["api_path"],
            _make_endpoint(task_key),
            methods=["POST"],
            response_model=AiTaskSubmitOut,
            summary=f"{meta['name']}（提交到队列）",
        )


_register_builtin_routes()


@router.post("/skills/submit/{task_key}", response_model=AiTaskSubmitOut, summary="通用 skill 提交接口（DB 动态添加的 skill 可走此路由）")
async def generic_submit(
    task_key: str,
    payload: GenericSkillReq,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    return _submit(task_key, payload, current, db)


@router.get("/tasks/{task_id}/stream")
async def stream_task_events(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    task = db.query(AiTask).filter(AiTask.id == task_id, AiTask.user_id == current.id).first()
    if not task:
        raise HTTPException(404, "任务不存在或无权访问")

    async def event_generator():
        from ai.queue import _utcnow
        sent_seq = 0
        terminal = {TASK_STATUS_SUCCESS, TASK_STATUS_FAILED, TASK_STATUS_DEAD_LETTER, TASK_STATUS_CANCELLED}

        yield _sse_fmt("meta", {
            "task_id": task.id, "task_key": task.task_key, "status": task.status,
            "progress": task.progress, "phase": task.phase,
        })

        if task.status == TASK_STATUS_SUCCESS and task.result_json is not None:
            yield _sse_fmt("result", task.result_json)
            yield _sse_fmt("done", {"total_ms": task.total_ms})
            return

        last_poll = time.time()
        while True:
            if await request.is_disconnected():
                return
            db.rollback()
            db.expire_all()
            t = db.query(AiTask).filter(AiTask.id == task_id).first()
            if not t:
                yield _sse_fmt("error", {"error_class": "not_found", "error_msg": "任务不存在"})
                return

            new_events = db.query(AiTaskEvent).filter(
                AiTaskEvent.task_id == task_id, AiTaskEvent.seq > sent_seq,
            ).order_by(AiTaskEvent.seq.asc()).all()
            for ev in new_events:
                sent_seq = ev.seq
                if ev.event_type == "phase":
                    yield _sse_fmt("phase", {"phase": ev.phase, "progress": ev.progress})
                elif ev.event_type == "delta" and ev.data:
                    yield _sse_fmt("delta", {"delta": ev.data})
                elif ev.event_type == "progress":
                    yield _sse_fmt("progress", {"progress": ev.progress, "phase": ev.phase})
                elif ev.event_type == "started":
                    yield _sse_fmt("phase", {"phase": "开始处理", "progress": 1})
                elif ev.event_type == "result":
                    try:
                        payload = json.loads(ev.data) if ev.data else None
                    except Exception:
                        payload = ev.data
                    yield _sse_fmt("result", payload)
                elif ev.event_type == "done":
                    yield _sse_fmt("done", ev.meta or {})
                    return
                elif ev.event_type == "error":
                    yield _sse_fmt("error", {
                        "error_class": (ev.meta or {}).get("error_class"),
                        "error_msg": (ev.meta or {}).get("error_msg"),
                        "dead_letter": (ev.meta or {}).get("dead_letter", False),
                        "attempt": (ev.meta or {}).get("attempt"),
                    })
                    return
                elif ev.event_type == "cancelled":
                    yield _sse_fmt("error", {"error_class": "cancelled", "error_msg": "任务已取消"})
                    return
                elif ev.event_type == "retry":
                    yield _sse_fmt("phase", {
                        "phase": f"第 {(ev.meta or {}).get('attempt', 0)} 次失败，正在重试",
                        "progress": 0,
                    })
                elif ev.event_type == "queued":
                    if sent_seq == 1 or ev.seq == 1:
                        yield _sse_fmt("phase", {"phase": "已入队，等待空闲 worker", "progress": 0})

            if t.status in terminal:
                if t.status == TASK_STATUS_SUCCESS:
                    if t.result_json is not None:
                        yield _sse_fmt("result", t.result_json)
                    yield _sse_fmt("done", {"total_ms": t.total_ms})
                elif t.status == TASK_STATUS_CANCELLED:
                    yield _sse_fmt("error", {"error_class": "cancelled", "error_msg": "任务已取消"})
                else:
                    yield _sse_fmt("error", {
                        "error_class": t.error_class,
                        "error_msg": t.error_msg,
                        "dead_letter": t.status == TASK_STATUS_DEAD_LETTER,
                        "attempt": t.attempts,
                    })
                return

            now = time.time()
            if now - last_poll > 5:
                yield _sse_fmt("heartbeat", {"status": t.status, "progress": t.progress, "phase": t.phase})
                last_poll = now
                yield ": keepalive\n\n"
            await asyncio.sleep(0.3)

    return _sse_stream(event_generator())
