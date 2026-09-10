from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from auth import get_current_user
from database import get_db
from models import User, Script
from schemas import CharacterIn, CharacterOut, CharacterListOut

router = APIRouter(prefix="/api/scripts", tags=["characters"])


def _get_owned_script(script_id: int, user_id: int, db: Session) -> Script:
    script = (
        db.query(Script)
        .filter(Script.id == script_id, Script.owner_id == user_id, Script.deleted_at.is_(None))
        .first()
    )
    if not script:
        raise HTTPException(404, "剧本不存在或无权访问")
    return script


def _ensure_content_array(script: Script, key: str) -> list:
    if not isinstance(script.content, dict):
        script.content = {}
    arr = script.content.get(key)
    if not isinstance(arr, list):
        arr = []
        script.content[key] = arr
    return arr


def _save(script: Script, db: Session):
    flag_modified(script, "content")
    script.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(script)


def _next_char_id(characters: list) -> str:
    max_n = 0
    for c in characters:
        cid = c.get("id", "") if isinstance(c, dict) else ""
        if isinstance(cid, str) and cid.startswith("c"):
            try:
                n = int(cid[1:])
                if n > max_n:
                    max_n = n
            except ValueError:
                pass
    return f"c{max_n + 1}"


@router.get("/{script_id}/characters", response_model=CharacterListOut)
def list_characters(
    script_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    script = _get_owned_script(script_id, current.id, db)
    chars = _ensure_content_array(script, "characters")
    return {"script_id": script_id, "count": len(chars), "characters": chars}


@router.post("/{script_id}/characters", response_model=CharacterOut, status_code=201)
def create_character(
    script_id: int,
    payload: CharacterIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    script = _get_owned_script(script_id, current.id, db)
    chars = _ensure_content_array(script, "characters")

    data = payload.model_dump(exclude_unset=True)
    if not data.get("id"):
        data["id"] = _next_char_id(chars)
    else:
        for existing in chars:
            if existing.get("id") == data["id"]:
                raise HTTPException(400, f"角色ID {data['id']} 已存在")
    chars.append(data)
    script.content["characters"] = chars
    _save(script, db)
    return data


@router.get("/{script_id}/characters/{character_id}", response_model=CharacterOut)
def get_character(
    script_id: int,
    character_id: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    script = _get_owned_script(script_id, current.id, db)
    chars = _ensure_content_array(script, "characters")
    for c in chars:
        if c.get("id") == character_id:
            return c
    raise HTTPException(404, "角色不存在")


@router.put("/{script_id}/characters/{character_id}", response_model=CharacterOut)
def update_character(
    script_id: int,
    character_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    script = _get_owned_script(script_id, current.id, db)
    chars = _ensure_content_array(script, "characters")
    for idx, c in enumerate(chars):
        if c.get("id") == character_id:
            if not isinstance(payload, dict):
                raise HTTPException(400, "请求体必须为对象")
            merged = {**c, **payload}
            merged["id"] = character_id
            chars[idx] = merged
            script.content["characters"] = chars
            _save(script, db)
            return merged
    raise HTTPException(404, "角色不存在")


@router.delete("/{script_id}/characters/{character_id}")
def delete_character(
    script_id: int,
    character_id: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    script = _get_owned_script(script_id, current.id, db)
    chars = _ensure_content_array(script, "characters")
    before = len(chars)
    new_chars = [c for c in chars if c.get("id") != character_id]
    if len(new_chars) == before:
        raise HTTPException(404, "角色不存在")
    script.content["characters"] = new_chars
    _save(script, db)
    return {"deleted": True, "id": character_id}
