from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import User, AiSkill, PromptTemplate
from schemas import (
    AiSkillListItem, AiSkillDetailOut, AiSkillUpdateReq, PromptVersionOut,
)

router = APIRouter(prefix="/api/ai/skills", tags=["ai-skills"])


@router.get("", response_model=List[AiSkillListItem], summary="列出所有 AI skill（含内置/自定义，含启用/禁用）")
def list_skills(
    category: str = None,
    is_active: bool = None,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    q = db.query(AiSkill)
    if category:
        q = q.filter(AiSkill.category == category)
    if is_active is not None:
        q = q.filter(AiSkill.is_active == is_active)
    return q.order_by(AiSkill.category.asc(), AiSkill.priority.desc(), AiSkill.key.asc()).all()


@router.get("/{key}", response_model=AiSkillDetailOut, summary="获取 skill 详情（含当前 active prompt + 历史版本列表）")
def get_skill(
    key: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    skill = db.query(AiSkill).filter(AiSkill.key == key).first()
    if not skill:
        raise HTTPException(404, "Skill 不存在")
    versions = (
        db.query(PromptTemplate)
        .filter(PromptTemplate.task_key == key)
        .order_by(PromptTemplate.created_at.desc())
        .all()
    )
    active_prompt = None
    for v in versions:
        if v.version == skill.prompt_version and v.is_active:
            active_prompt = v
            break
    return {
        **{c.name: getattr(skill, c.name) for c in AiSkill.__table__.columns},
        "active_prompt": active_prompt,
        "versions": versions,
    }


@router.put("/{key}", response_model=AiSkillDetailOut, summary="更新 skill 元数据；若传 new_system_prompt 则创建新 prompt 版本")
def update_skill(
    key: str,
    body: AiSkillUpdateReq,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    skill = db.query(AiSkill).filter(AiSkill.key == key).first()
    if not skill:
        raise HTTPException(404, "Skill 不存在")

    scalar_fields = [
        "name", "description", "category", "temperature", "priority",
        "timeout", "max_tokens", "stream_progress", "auto_review", "is_active", "prompt_version",
    ]
    changed = False
    for f in scalar_fields:
        val = getattr(body, f, None)
        if val is not None:
            setattr(skill, f, val)
            changed = True

    new_sys = body.new_system_prompt
    new_tpl = body.new_user_prompt_template
    if new_sys or new_tpl:
        latest = (
            db.query(PromptTemplate)
            .filter(PromptTemplate.task_key == key)
            .order_by(PromptTemplate.id.desc())
            .first()
        )
        next_ver_num = 2
        if latest:
            try:
                next_ver_num = int(latest.version.lstrip("v")) + 1
            except Exception:
                next_ver_num = (latest.id or 0) + 1
        new_version = body.new_version_label or f"v{next_ver_num}"

        exists = (
            db.query(PromptTemplate)
            .filter(PromptTemplate.task_key == key, PromptTemplate.version == new_version)
            .first()
        )
        if exists:
            raise HTTPException(400, f"prompt 版本 {new_version} 已存在，请换一个 version label")

        (
            db.query(PromptTemplate)
            .filter(PromptTemplate.task_key == key, PromptTemplate.is_active == True)
            .update({"is_active": False})
        )

        active = (
            db.query(PromptTemplate)
            .filter(PromptTemplate.task_key == key, PromptTemplate.version == skill.prompt_version)
            .first()
        )
        row = PromptTemplate(
            task_key=key,
            version=new_version,
            system_prompt=new_sys if new_sys is not None else (active.system_prompt if active else ""),
            user_prompt_template=new_tpl if new_tpl is not None else (active.user_prompt_template if active else ""),
            is_active=True,
        )
        db.add(row)
        skill.prompt_version = new_version
        changed = True

    if changed:
        db.commit()
        db.refresh(skill)

    return get_skill(key, db, current)


@router.post("/{key}/activate-version/{version}", response_model=AiSkillDetailOut, summary="切换 skill 使用的 prompt 版本")
def activate_prompt_version(
    key: str,
    version: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    skill = db.query(AiSkill).filter(AiSkill.key == key).first()
    if not skill:
        raise HTTPException(404, "Skill 不存在")
    target = (
        db.query(PromptTemplate)
        .filter(PromptTemplate.task_key == key, PromptTemplate.version == version)
        .first()
    )
    if not target:
        raise HTTPException(404, f"prompt 版本不存在: {version}")
    (
        db.query(PromptTemplate)
        .filter(PromptTemplate.task_key == key, PromptTemplate.is_active == True)
        .update({"is_active": False})
    )
    target.is_active = True
    skill.prompt_version = version
    db.commit()
    db.refresh(skill)
    return get_skill(key, db, current)
