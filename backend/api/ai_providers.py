from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import User, AiProvider
from schemas import (
    AiProviderIn, AiProviderUpdate, AiProviderOut,
    AiProviderBindReq, AiProviderTestResult,
)

router = APIRouter(prefix="/api/ai-providers", tags=["ai-providers"])

VALID_TASK_KEYS = {
    "generate_outline", "review_outline", "modify_outline_module", "batch_modify_outline",
    "generate_characters", "review_characters",
    "generate_episode", "review_episode", "fix_episode", "rewrite_segment",
    "parse_import",
}


def _row_to_out(p: AiProvider) -> dict:
    key = p.api_key_enc or ""
    preview = ""
    if key and len(key) >= 10:
        preview = key[:6] + "****" + key[-4:]
    elif key:
        preview = "****"
    return {
        "id": p.id,
        "name": p.name,
        "provider": p.provider,
        "model_name": p.model_name,
        "base_url": p.base_url,
        "has_key": bool(key),
        "key_preview": preview,
        "task_bindings": p.task_bindings or [],
        "is_active": p.is_active,
        "priority": p.priority,
        "created_at": p.created_at,
    }


def _validate_task_bindings(bindings: List[str]):
    if not isinstance(bindings, list):
        raise HTTPException(400, "task_bindings 必须是字符串数组")
    for b in bindings:
        if b != "*" and b not in VALID_TASK_KEYS:
            raise HTTPException(400, f"非法的 task_key: {b}；合法值：{sorted(VALID_TASK_KEYS)} 或 '*'")


@router.get("", response_model=dict)
def list_providers(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    rows = db.query(AiProvider).order_by(AiProvider.priority.asc(), AiProvider.id.asc()).all()
    return {"providers": [_row_to_out(p) for p in rows]}


@router.post("", response_model=dict)
def create_provider(
    payload: AiProviderIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if db.query(AiProvider).filter(AiProvider.name == payload.name).first():
        raise HTTPException(409, f"已存在名为 {payload.name} 的 provider")
    if payload.provider not in ("openai", "mock"):
        raise HTTPException(400, "provider 只能是 openai 或 mock")
    _validate_task_bindings(payload.task_bindings)
    if payload.provider == "openai" and (not payload.base_url or not payload.api_key or not payload.model_name):
        raise HTTPException(400, "openai 协议必须填写 base_url / api_key / model_name")
    p = AiProvider(
        name=payload.name,
        provider=payload.provider,
        model_name=payload.model_name,
        base_url=payload.base_url,
        api_key_enc=payload.api_key,
        task_bindings=payload.task_bindings or ["*"],
        is_active=payload.is_active,
        priority=payload.priority,
    )
    db.add(p); db.commit(); db.refresh(p)
    return {"provider": _row_to_out(p)}


@router.get("/{name}", response_model=dict)
def get_provider(
    name: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    p = db.query(AiProvider).filter(AiProvider.name == name).first()
    if not p:
        raise HTTPException(404, "provider 不存在")
    return {"provider": _row_to_out(p)}


@router.put("/{name}", response_model=dict)
def update_provider(
    name: str,
    payload: AiProviderUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    p = db.query(AiProvider).filter(AiProvider.name == name).first()
    if not p:
        raise HTTPException(404, "provider 不存在")
    data = payload.model_dump(exclude_unset=True)
    if "api_key" in data:
        data["api_key_enc"] = data.pop("api_key")
    if "task_bindings" in data:
        _validate_task_bindings(data["task_bindings"])
    if "provider" in data and data["provider"] not in ("openai", "mock"):
        raise HTTPException(400, "provider 只能是 openai 或 mock")
    for k, v in data.items():
        setattr(p, k, v)
    db.commit(); db.refresh(p)
    return {"provider": _row_to_out(p)}


@router.delete("/{name}", response_model=dict)
def delete_provider(
    name: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    p = db.query(AiProvider).filter(AiProvider.name == name).first()
    if not p:
        raise HTTPException(404, "provider 不存在")
    if p.name == "mock":
        raise HTTPException(400, "内置 mock provider 不能删除")
    db.delete(p); db.commit()
    return {"deleted": True, "name": name}


@router.post("/{name}/activate", response_model=dict)
def activate_provider(
    name: str,
    active: bool = True,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    p = db.query(AiProvider).filter(AiProvider.name == name).first()
    if not p:
        raise HTTPException(404, "provider 不存在")
    p.is_active = active
    db.commit(); db.refresh(p)
    return {"provider": _row_to_out(p)}


@router.post("/{name}/bindings", response_model=dict)
def set_bindings(
    name: str,
    payload: AiProviderBindReq,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    p = db.query(AiProvider).filter(AiProvider.name == name).first()
    if not p:
        raise HTTPException(404, "provider 不存在")
    _validate_task_bindings(payload.task_bindings)
    p.task_bindings = payload.task_bindings
    db.commit(); db.refresh(p)
    return {"provider": _row_to_out(p)}


@router.post("/{name}/set-default", response_model=dict)
def set_default_provider(
    name: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """把指定 provider 设为通配兜底（task_bindings=['*'] 且 priority 最低/最高优先）。
    逻辑：把其它 provider 的 priority 调成比它大 10，把它调成 10，bindings=['*']。"""
    target = db.query(AiProvider).filter(AiProvider.name == name).first()
    if not target:
        raise HTTPException(404, "provider 不存在")
    if not target.is_active:
        raise HTTPException(400, "该 provider 未激活，不能设为默认")
    if target.provider == "openai" and not target.api_key_enc:
        raise HTTPException(400, "该 openai provider 未填写 api_key，不能设为默认")
    target.task_bindings = ["*"]
    target.priority = 10
    others = db.query(AiProvider).filter(AiProvider.id != target.id).all()
    for o in others:
        if o.priority <= 10:
            o.priority = 20
    db.commit()
    return {"default": _row_to_out(target)}


@router.post("/{name}/test", response_model=AiProviderTestResult)
async def test_provider(
    name: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    import httpx
    p = db.query(AiProvider).filter(AiProvider.name == name).first()
    if not p:
        raise HTTPException(404, "provider 不存在")
    if not p.is_active:
        return AiProviderTestResult(ok=False, provider=name, error="provider 未激活")
    if p.provider == "mock" or not p.api_key_enc:
        return AiProviderTestResult(ok=True, provider=name, model=p.model_name, reply="pong(mock)")
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{p.base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {p.api_key_enc}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": p.model_name,
                    "messages": [
                        {"role": "system", "content": "Reply with exactly the word 'pong' and nothing else."},
                        {"role": "user", "content": "ping"},
                    ],
                    "stream": False,
                },
            )
            if resp.status_code != 200:
                return AiProviderTestResult(
                    ok=False, provider=name,
                    error=f"HTTP {resp.status_code}: {resp.text[:300]}"
                )
            data = resp.json()
            reply = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
            usage = data.get("usage")
            return AiProviderTestResult(
                ok=True, provider=name, model=p.model_name, reply=reply.strip(), usage=usage
            )
    except Exception as e:
        return AiProviderTestResult(ok=False, provider=name, error=str(e))
