import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import User, Script
from schemas import (
    AiGenerateOutlineReq, AiModuleModifyReq, AiBatchModifyReq,
    AiReviewOutlineReq, AiReviewCharactersReq, AiGenerateCharactersReq,
    AiGenerateEpisodeReq, AiReviewEpisodeReq, AiFixEpisodeReq,
    AiRewriteSegmentReq, AiParseImportReq,
)
from ai.service import AiService

router = APIRouter(prefix="/api/ai", tags=["ai"])


def _check_script_access(script_id: int, user_id: int, db: Session) -> Optional[Script]:
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


@router.post("/outline/generate")
async def ai_generate_outline(
    payload: AiGenerateOutlineReq,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if payload.script_id:
        _check_script_access(payload.script_id, current.id, db)
    svc = AiService(db)
    params = payload.model_dump()
    return _sse_stream(
        svc.stream(
            task_key="generate_outline",
            method_name="generate_outline",
            params=params,
            user_id=current.id,
            script_id=payload.script_id,
        )
    )


@router.post("/outline/review")
async def ai_review_outline(
    payload: AiReviewOutlineReq,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    _check_script_access(payload.script_id, current.id, db)
    svc = AiService(db)
    return _sse_stream(
        svc.stream(
            task_key="review_outline",
            method_name="review_outline",
            params=payload.model_dump(),
            user_id=current.id,
            script_id=payload.script_id,
        )
    )


@router.post("/outline/modify-module")
async def ai_modify_module(
    payload: AiModuleModifyReq,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    _check_script_access(payload.script_id, current.id, db)
    svc = AiService(db)
    return _sse_stream(
        svc.stream(
            task_key="modify_outline_module",
            method_name="modify_module",
            params=payload.model_dump(),
            user_id=current.id,
            script_id=payload.script_id,
        )
    )


@router.post("/outline/batch-modify")
async def ai_batch_modify(
    payload: AiBatchModifyReq,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    _check_script_access(payload.script_id, current.id, db)
    svc = AiService(db)
    return _sse_stream(
        svc.stream(
            task_key="batch_modify_outline",
            method_name="batch_modify",
            params=payload.model_dump(),
            user_id=current.id,
            script_id=payload.script_id,
        )
    )


@router.post("/characters/generate")
async def ai_generate_characters(
    payload: AiGenerateCharactersReq,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    _check_script_access(payload.script_id, current.id, db)
    svc = AiService(db)
    return _sse_stream(
        svc.stream(
            task_key="generate_characters",
            method_name="generate_characters",
            params=payload.model_dump(),
            user_id=current.id,
            script_id=payload.script_id,
        )
    )


@router.post("/characters/review")
async def ai_review_characters(
    payload: AiReviewCharactersReq,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    _check_script_access(payload.script_id, current.id, db)
    svc = AiService(db)
    return _sse_stream(
        svc.stream(
            task_key="review_characters",
            method_name="review_characters",
            params=payload.model_dump(),
            user_id=current.id,
            script_id=payload.script_id,
        )
    )


@router.post("/episode/generate")
async def ai_generate_episode(
    payload: AiGenerateEpisodeReq,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    _check_script_access(payload.script_id, current.id, db)
    svc = AiService(db)
    return _sse_stream(
        svc.stream(
            task_key="generate_episode",
            method_name="generate_episode",
            params=payload.model_dump(),
            user_id=current.id,
            script_id=payload.script_id,
        )
    )


@router.post("/episode/review")
async def ai_review_episode(
    payload: AiReviewEpisodeReq,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    _check_script_access(payload.script_id, current.id, db)
    svc = AiService(db)
    return _sse_stream(
        svc.stream(
            task_key="review_episode",
            method_name="review_episode",
            params=payload.model_dump(),
            user_id=current.id,
            script_id=payload.script_id,
        )
    )


@router.post("/episode/fix")
async def ai_fix_episode(
    payload: AiFixEpisodeReq,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    _check_script_access(payload.script_id, current.id, db)
    svc = AiService(db)
    return _sse_stream(
        svc.stream(
            task_key="fix_episode",
            method_name="fix_episode",
            params=payload.model_dump(),
            user_id=current.id,
            script_id=payload.script_id,
        )
    )


@router.post("/episode/rewrite-segment")
async def ai_rewrite_segment(
    payload: AiRewriteSegmentReq,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    _check_script_access(payload.script_id, current.id, db)
    svc = AiService(db)
    return _sse_stream(
        svc.stream(
            task_key="rewrite_segment",
            method_name="rewrite_segment",
            params=payload.model_dump(),
            user_id=current.id,
            script_id=payload.script_id,
        )
    )


@router.post("/import/parse")
async def ai_parse_import(
    payload: AiParseImportReq,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    svc = AiService(db)
    return _sse_stream(
        svc.stream(
            task_key="parse_import",
            method_name="parse_import",
            params=payload.model_dump(),
            user_id=current.id,
        )
    )
