from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Script, ScriptVersion, User
from schemas import (
    ScriptCreate, ScriptUpdate, ScriptOut, ScriptListItem,
    VersionCreate, VersionOut, VersionRestore,
)

router = APIRouter(prefix="/api/scripts", tags=["scripts"])


# ---------- Script CRUD ----------
@router.get("", response_model=List[ScriptListItem])
def list_scripts(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    q = db.query(Script).filter(Script.owner_id == current.id)
    if status_filter:
        q = q.filter(Script.status == status_filter)
    return q.order_by(Script.updated_at.desc()).all()


@router.post("", response_model=ScriptOut)
def create_script(
    payload: ScriptCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    script = Script(
        owner_id=current.id,
        title=payload.title,
        path_type=payload.path_type,
        description=payload.description,
        content=payload.content or {},
    )
    db.add(script)
    db.commit()
    db.refresh(script)

    initial = ScriptVersion(
        script_id=script.id,
        version_number=1,
        name="初始版本",
        commit_message="创建剧本",
        content=script.content,
        created_by=current.id,
    )
    db.add(initial)
    db.commit()
    db.refresh(initial)
    script.current_version_id = initial.id
    db.commit()
    db.refresh(script)
    return script


@router.get("/{script_id}", response_model=ScriptOut)
def get_script(
    script_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    script = _get_owned(script_id, current.id, db)
    return script


@router.put("/{script_id}", response_model=ScriptOut)
def update_script(
    script_id: int,
    payload: ScriptUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    script = _get_owned(script_id, current.id, db)
    data = payload.model_dump(exclude_unset=True)
    if "content" in data and data["content"] is not None:
        script.content = data.pop("content")
    for k, v in data.items():
        if v is not None:
            setattr(script, k, v)
    db.commit()
    db.refresh(script)
    return script


@router.delete("/{script_id}")
def delete_script(
    script_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    script = _get_owned(script_id, current.id, db)
    db.delete(script)
    db.commit()
    return {"ok": True}


# ---------- Versions ----------
@router.get("/{script_id}/versions", response_model=List[VersionOut])
def list_versions(
    script_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    _get_owned(script_id, current.id, db)
    return (
        db.query(ScriptVersion)
        .filter(ScriptVersion.script_id == script_id)
        .order_by(ScriptVersion.version_number.desc())
        .all()
    )


@router.post("/{script_id}/versions", response_model=VersionOut)
def create_version(
    script_id: int,
    payload: VersionCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    script = _get_owned(script_id, current.id, db)
    next_num = (
        db.query(func.coalesce(func.max(ScriptVersion.version_number), 0))
        .filter(ScriptVersion.script_id == script_id)
        .scalar()
    ) + 1

    content = payload.content if payload.content is not None else script.content
    ver = ScriptVersion(
        script_id=script_id,
        version_number=next_num,
        name=payload.name or f"v{next_num}",
        commit_message=payload.commit_message,
        content=content,
        created_by=current.id,
    )
    db.add(ver)
    script.content = content
    script.current_version_id = ver.id
    db.commit()
    db.refresh(ver)
    return ver


@router.get("/{script_id}/versions/{version_id}", response_model=VersionOut)
def get_version(
    script_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    _get_owned(script_id, current.id, db)
    ver = (
        db.query(ScriptVersion)
        .filter(
            ScriptVersion.script_id == script_id,
            ScriptVersion.id == version_id,
        )
        .first()
    )
    if not ver:
        raise HTTPException(404, "版本不存在")
    return ver


@router.post("/{script_id}/versions/{version_id}/restore", response_model=ScriptOut)
def restore_version(
    script_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    script = _get_owned(script_id, current.id, db)
    ver = (
        db.query(ScriptVersion)
        .filter(
            ScriptVersion.script_id == script_id,
            ScriptVersion.id == version_id,
        )
        .first()
    )
    if not ver:
        raise HTTPException(404, "版本不存在")
    script.content = ver.content
    script.current_version_id = ver.id
    db.commit()
    db.refresh(script)
    return script


@router.delete("/{script_id}/versions/{version_id}")
def delete_version(
    script_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    _get_owned(script_id, current.id, db)
    ver = (
        db.query(ScriptVersion)
        .filter(
            ScriptVersion.script_id == script_id,
            ScriptVersion.id == version_id,
        )
        .first()
    )
    if not ver:
        raise HTTPException(404, "版本不存在")
    if ver.id == Script.current_version_id:
        raise HTTPException(400, "当前版本不可删除")
    db.delete(ver)
    db.commit()
    return {"ok": True}


# ---------- Helpers ----------
def _get_owned(script_id: int, user_id: int, db: Session) -> Script:
    script = db.query(Script).filter(Script.id == script_id, Script.owner_id == user_id).first()
    if not script:
        raise HTTPException(404, "剧本不存在或无权访问")
    return script
