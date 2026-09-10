import json
import copy
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, and_
from sqlalchemy.orm import Session

from auth import get_current_user, get_current_user_optional
from database import get_db
from models import Script, ScriptVersion, User, ScriptImport
from schemas import (
    ScriptCreate, ScriptPatch, ScriptOut, ScriptListItem, ScriptLockRequest,
    ScriptDuplicateOut, VersionCreate, VersionOut, VersionDiffOut,
)

router = APIRouter(prefix="/api/scripts", tags=["scripts"])


def _get_owned(script_id: int, user_id: int, db: Session, include_deleted: bool = False) -> Script:
    q = db.query(Script).filter(Script.id == script_id, Script.owner_id == user_id)
    if not include_deleted:
        q = q.filter(Script.deleted_at.is_(None))
    script = q.first()
    if not script:
        raise HTTPException(404, "剧本不存在或无权访问")
    return script


@router.get("", response_model=List[ScriptListItem])
def list_scripts(
    status_filter: Optional[str] = Query(None, alias="status"),
    q: Optional[str] = Query(None, alias="q"),
    path_type: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    archived: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    query = db.query(Script).filter(Script.owner_id == current.id)
    if not archived:
        query = query.filter(Script.deleted_at.is_(None))
    else:
        query = query.filter(Script.deleted_at.isnot(None))
    if status_filter:
        query = query.filter(Script.status == status_filter)
    if path_type:
        query = query.filter(Script.path_type == path_type)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Script.title.like(like), Script.description.like(like)))
    if tag:
        query = query.filter(Script.tags.contains(json.dumps(tag, ensure_ascii=False)))
    return (
        query.order_by(Script.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )


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
        tags=payload.tags,
        config=payload.config or {},
        content=payload.content or {},
        step=0,
        progress=0,
        status="draft",
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
    return _get_owned(script_id, current.id, db)


@router.patch("/{script_id}", response_model=ScriptOut)
def patch_script(
    script_id: int,
    payload: ScriptPatch,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    script = _get_owned(script_id, current.id, db)
    data = payload.model_dump(exclude_unset=True)
    if "content" in data and data["content"] is not None:
        script.content = data.pop("content")
        script.updated_at = datetime.utcnow()
    for k, v in data.items():
        if v is not None:
            setattr(script, k, v)
    db.commit()
    db.refresh(script)
    return script


@router.put("/{script_id}", response_model=ScriptOut)
def update_script(
    script_id: int,
    payload: ScriptPatch,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    return patch_script(script_id, payload, db, current)


@router.delete("/{script_id}")
def delete_script(
    script_id: int,
    permanent: bool = Query(False),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    script = _get_owned(script_id, current.id, db, include_deleted=True)
    if permanent:
        db.delete(script)
        db.commit()
        return {"ok": True, "permanent": True}
    script.deleted_at = datetime.utcnow()
    script.status = "archived"
    db.commit()
    return {"ok": True, "permanent": False}


@router.post("/{script_id}/restore")
def restore_script(
    script_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    script = _get_owned(script_id, current.id, db, include_deleted=True)
    if not script.deleted_at:
        raise HTTPException(400, "剧本未被删除")
    script.deleted_at = None
    if script.status == "archived":
        script.status = "draft"
    db.commit()
    db.refresh(script)
    return {"ok": True, "script_id": script.id}


@router.post("/{script_id}/duplicate", response_model=ScriptDuplicateOut)
def duplicate_script(
    script_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    src = _get_owned(script_id, current.id, db)
    new_script = Script(
        owner_id=current.id,
        title=f"{src.title}（副本）",
        path_type=src.path_type,
        description=src.description,
        tags=copy.deepcopy(src.tags) if src.tags else None,
        config=copy.deepcopy(src.config) if src.config else {},
        content=copy.deepcopy(src.content),
        step=src.step,
        progress=src.progress,
        status="draft",
        cover_url=src.cover_url,
    )
    db.add(new_script)
    db.commit()
    db.refresh(new_script)

    ver = ScriptVersion(
        script_id=new_script.id,
        version_number=1,
        name="副本初始版本",
        commit_message=f"从《{src.title}》复制创建",
        content=copy.deepcopy(new_script.content),
        created_by=current.id,
    )
    db.add(ver)
    db.commit()
    db.refresh(ver)
    new_script.current_version_id = ver.id
    db.commit()
    return ScriptDuplicateOut(new_id=new_script.id, title=new_script.title)


@router.post("/{script_id}/lock", response_model=ScriptOut)
def lock_script(
    script_id: int,
    payload: ScriptLockRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    script = _get_owned(script_id, current.id, db)
    if script.locked_at:
        raise HTTPException(400, "剧本已锁定（已定稿）")

    next_num = (
        db.query(func.coalesce(func.max(ScriptVersion.version_number), 0))
        .filter(ScriptVersion.script_id == script_id)
        .scalar()
    ) + 1

    final_ver = ScriptVersion(
        script_id=script_id,
        version_number=next_num,
        name=payload.name or f"定稿版本 v{next_num}",
        commit_message=payload.commit_message or "定稿版本",
        content=copy.deepcopy(script.content),
        is_final=True,
        created_by=current.id,
    )
    db.add(final_ver)
    script.locked_at = datetime.utcnow()
    script.status = "final"
    script.current_version_id = final_ver.id
    db.commit()
    db.refresh(script)
    return script


@router.post("/{script_id}/unlock", response_model=ScriptOut)
def unlock_script(
    script_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    script = _get_owned(script_id, current.id, db)
    if not script.locked_at:
        raise HTTPException(400, "剧本未锁定")
    script.locked_at = None
    if script.status == "final":
        script.status = "draft"
    db.commit()
    db.refresh(script)
    return script


@router.get("/{script_id}/export")
def export_script(
    script_id: int,
    format: str = Query("json", pattern="^(json|txt)$"),
    version_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    script = _get_owned(script_id, current.id, db)
    if version_id:
        ver = (
            db.query(ScriptVersion)
            .filter(ScriptVersion.script_id == script_id, ScriptVersion.id == version_id)
            .first()
        )
        if not ver:
            raise HTTPException(404, "版本不存在")
        content = ver.content
        version_label = f"_v{ver.version_number}"
    else:
        content = script.content
        version_label = ""

    filename = f"{script.title}{version_label}"

    if format == "json":
        data = json.dumps(
            {"title": script.title, "description": script.description, "content": content},
            ensure_ascii=False, indent=2,
        )
        return Response(
            content=data,
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}.json"'},
        )
    else:
        lines = [f"《{script.title}》", "=" * 40, ""]
        outline = content.get("outline", []) if isinstance(content, dict) else []
        characters = content.get("characters", []) if isinstance(content, dict) else []
        episodes = content.get("episodes", []) if isinstance(content, dict) else []

        if outline:
            lines.append("【大纲】")
            for m in outline:
                lines.append(f"  ■ {m.get('title', '')}")
                if m.get("summary"):
                    lines.append(f"    {m['summary']}")
                if m.get("episodes"):
                    for ep in m["episodes"]:
                        lines.append(f"      · {ep.get('range','')} {ep.get('hook','')}：{ep.get('summary','')}")
            lines.append("")

        if characters:
            lines.append("【人物小传】")
            for c in characters:
                lines.append(f"  ■ {c.get('name','')}（{c.get('role','')} {c.get('gender','')} {c.get('age','')}岁）")
                if c.get("description"):
                    lines.append(f"    {c['description']}")
                if c.get("personality"):
                    lines.append(f"    性格：{c['personality']}")
                if c.get("background"):
                    lines.append(f"    背景：{c['background']}")
                if c.get("tagline"):
                    lines.append(f"    金句：「{c['tagline']}」")
            lines.append("")

        if episodes:
            lines.append("【分集剧本】")
            for ep in episodes:
                lines.append(f"  第{ep.get('id','?')}集 《{ep.get('title','')}》（{ep.get('duration','?')}秒）")
                for sb in ep.get("storyboards", []):
                    lines.append(f"    ◇ {sb.get('title','')}")
                    for cam in sb.get("cameras", []):
                        lines.append(f"      【{cam.get('shotType','')} | {cam.get('camMove','')}】")
                        for b in cam.get("behaviors", []):
                            loc = b.get("location", "")
                            visual = b.get("visual", "")
                            char = b.get("character", "")
                            action = b.get("action", "")
                            dialog = b.get("dialog", "")
                            tag = b.get("dialogTag", "")
                            tag_label = {"lip": "[画内]", "voicover": "[画外]", "os": "[OS]", "narrator": "[旁白]"}.get(tag, "")
                            if visual:
                                lines.append(f"        · {visual}")
                            if char or action:
                                lines.append(f"          人物：{char}  动作：{action}")
                            if dialog:
                                lines.append(f"          {tag_label}{dialog}")
                lines.append("")

        text = "\n".join(lines)
        return Response(
            content=text,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}.txt"'},
        )


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
    if script.locked_at:
        raise HTTPException(400, "剧本已定稿锁定，无法创建新版本")
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
    script.updated_at = datetime.utcnow()
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
        .filter(ScriptVersion.script_id == script_id, ScriptVersion.id == version_id)
        .first()
    )
    if not ver:
        raise HTTPException(404, "版本不存在")
    return ver


@router.get("/{script_id}/versions/diff", response_model=VersionDiffOut)
def diff_versions(
    script_id: int,
    v1: int = Query(...),
    v2: int = Query(...),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    _get_owned(script_id, current.id, db)
    ver1 = db.query(ScriptVersion).filter(
        ScriptVersion.script_id == script_id, ScriptVersion.version_number == v1
    ).first()
    ver2 = db.query(ScriptVersion).filter(
        ScriptVersion.script_id == script_id, ScriptVersion.version_number == v2
    ).first()
    if not ver1 or not ver2:
        raise HTTPException(404, "版本不存在")

    changes = _compute_diff(ver1.content, ver2.content)
    return VersionDiffOut(v1=v1, v2=v2, diff_count=len(changes), changes=changes)


@router.post("/{script_id}/versions/{version_id}/restore", response_model=ScriptOut)
def restore_version(
    script_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    script = _get_owned(script_id, current.id, db)
    if script.locked_at:
        raise HTTPException(400, "剧本已定稿锁定，无法回退版本")
    ver = (
        db.query(ScriptVersion)
        .filter(ScriptVersion.script_id == script_id, ScriptVersion.id == version_id)
        .first()
    )
    if not ver:
        raise HTTPException(404, "版本不存在")
    script.content = copy.deepcopy(ver.content)
    script.current_version_id = ver.id
    script.updated_at = datetime.utcnow()
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
    script = _get_owned(script_id, current.id, db)
    ver = (
        db.query(ScriptVersion)
        .filter(ScriptVersion.script_id == script_id, ScriptVersion.id == version_id)
        .first()
    )
    if not ver:
        raise HTTPException(404, "版本不存在")
    if ver.id == script.current_version_id:
        raise HTTPException(400, "当前版本不可删除")
    if ver.is_final:
        raise HTTPException(400, "定稿版本不可删除")
    db.delete(ver)
    db.commit()
    return {"ok": True}


def _compute_diff(c1: dict, c2: dict, path: str = "") -> list:
    changes = []
    if isinstance(c1, dict) and isinstance(c2, dict):
        keys = set(c1.keys()) | set(c2.keys())
        for k in keys:
            p = f"{path}.{k}" if path else k
            if k not in c1:
                changes.append({"path": p, "type": "added", "newValue": c2[k]})
            elif k not in c2:
                changes.append({"path": p, "type": "removed", "oldValue": c1[k]})
            elif c1[k] != c2[k]:
                if isinstance(c1[k], (dict, list)) and isinstance(c2[k], (dict, list)):
                    changes.extend(_compute_diff(c1[k], c2[k], p))
                else:
                    changes.append({"path": p, "type": "modified", "oldValue": c1[k], "newValue": c2[k]})
    elif isinstance(c1, list) and isinstance(c2, list):
        if len(c1) != len(c2):
            changes.append({"path": path, "type": "list_length", "oldLen": len(c1), "newLen": len(c2)})
        for i in range(min(len(c1), len(c2))):
            changes.extend(_compute_diff(c1[i], c2[i], f"{path}[{i}]"))
    return changes
