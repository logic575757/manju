from datetime import datetime
from typing import List, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from auth import get_current_user
from database import get_db
from models import User, Script
from schemas import (
    EpisodeOut, EpisodeListOut,
    EpisodeValidateOut, EpisodePassOut,
)

router = APIRouter(prefix="/api/scripts", tags=["episodes"])


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


def _ensure_passed_map(script: Script) -> dict:
    if not isinstance(script.content, dict):
        script.content = {}
    pm = script.content.get("passedEpisodes")
    if not isinstance(pm, dict):
        pm = {}
        script.content["passedEpisodes"] = pm
    return pm


def _next_ep_id(eps: list) -> int:
    max_n = 0
    for e in eps:
        eid = e.get("id") if isinstance(e, dict) else None
        if isinstance(eid, int) and eid > max_n:
            max_n = eid
        elif isinstance(eid, str):
            try:
                n = int(eid)
                if n > max_n:
                    max_n = n
            except ValueError:
                pass
    return max_n + 1


def _get_expected_duration(script: Script, ep: dict) -> int:
    target = ep.get("duration")
    if isinstance(target, int) and target > 0:
        return target
    cfg = script.config if isinstance(script.config, dict) else {}
    cd = cfg.get("ep_duration")
    if isinstance(cd, int) and cd > 0:
        return cd
    return 90


def _sum_behavior_durations(ep: dict) -> int:
    total = 0
    for sb in (ep.get("storyboards") or []):
        if not isinstance(sb, dict):
            continue
        for cam in (sb.get("cameras") or []):
            if not isinstance(cam, dict):
                continue
            for b in (cam.get("behaviors") or []):
                if not isinstance(b, dict):
                    continue
                try:
                    total += max(0, int(b.get("duration", 0) or 0))
                except (TypeError, ValueError):
                    pass
    return total


def _validate_episode_duration(script: Script, ep: dict) -> dict:
    expected = _get_expected_duration(script, ep)
    actual = _sum_behavior_durations(ep)
    diff = actual - expected
    issues: List[str] = []
    if diff < 0:
        issues.append(f"当前集内容总时长 {actual}s，未达到本集设定 {expected}s，还差 {abs(diff)}s。")
    elif diff > 0:
        issues.append(f"当前集内容总时长 {actual}s，超出本集设定 {expected}s，多了 {diff}s。")

    if not (ep.get("storyboards") or []):
        issues.append("本集尚未生成分镜内容。")

    return {
        "valid": diff == 0 and not issues,
        "expected_duration": expected,
        "actual_duration": actual,
        "diff": diff,
        "issues": issues,
    }


def _find_episode(eps: list, episode_id: Any):
    for idx, e in enumerate(eps):
        if not isinstance(e, dict):
            continue
        if str(e.get("id")) == str(episode_id):
            return idx, e
    return None, None


def _touch(script: Script, db: Session):
    flag_modified(script, "content")
    script.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(script)


@router.get("/{script_id}/episodes", response_model=EpisodeListOut)
def list_episodes(
    script_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    script = _get_owned_script(script_id, current.id, db)
    eps = _ensure_content_array(script, "episodes")
    return {"script_id": script_id, "count": len(eps), "episodes": eps}


@router.post("/{script_id}/episodes", response_model=EpisodeOut, status_code=201)
def create_episode(
    script_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    script = _get_owned_script(script_id, current.id, db)
    eps = _ensure_content_array(script, "episodes")

    data = payload if isinstance(payload, dict) else {}
    if "id" not in data or data.get("id") in (None, ""):
        data["id"] = _next_ep_id(eps)
    else:
        for existing in eps:
            if str(existing.get("id")) == str(data["id"]):
                raise HTTPException(400, f"分集ID {data['id']} 已存在")

    if "title" not in data or not data.get("title"):
        data["title"] = f"第 {data['id']} 集 · 待生成"
    if "storyboards" not in data:
        data["storyboards"] = []
    if "duration" not in data:
        cfg = script.config if isinstance(script.config, dict) else {}
        data["duration"] = cfg.get("ep_duration", 90)

    eps.append(data)
    script.content["episodes"] = eps
    _touch(script, db)
    return data


@router.get("/{script_id}/episodes/{episode_id}", response_model=EpisodeOut)
def get_episode(
    script_id: int,
    episode_id: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    script = _get_owned_script(script_id, current.id, db)
    eps = _ensure_content_array(script, "episodes")
    _, ep = _find_episode(eps, episode_id)
    if ep is None:
        raise HTTPException(404, "分集不存在")
    return ep


@router.put("/{script_id}/episodes/{episode_id}", response_model=EpisodeOut)
def update_episode(
    script_id: int,
    episode_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    script = _get_owned_script(script_id, current.id, db)
    eps = _ensure_content_array(script, "episodes")
    idx, ep = _find_episode(eps, episode_id)
    if ep is None:
        raise HTTPException(404, "分集不存在")
    if not isinstance(payload, dict):
        raise HTTPException(400, "请求体必须为对象")
    merged = {**ep, **payload}
    merged["id"] = ep["id"]
    eps[idx] = merged
    script.content["episodes"] = eps
    _touch(script, db)
    return merged


@router.delete("/{script_id}/episodes/{episode_id}")
def delete_episode(
    script_id: int,
    episode_id: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    script = _get_owned_script(script_id, current.id, db)
    eps = _ensure_content_array(script, "episodes")
    pm = _ensure_passed_map(script)
    before = len(eps)
    new_eps = [e for e in eps if str(e.get("id")) != str(episode_id)]
    if len(new_eps) == before:
        raise HTTPException(404, "分集不存在")
    pm.pop(str(episode_id), None)
    script.content["episodes"] = new_eps
    script.content["passedEpisodes"] = pm
    _touch(script, db)
    return {"deleted": True, "id": episode_id}


@router.post("/{script_id}/episodes/{episode_id}/validate", response_model=EpisodeValidateOut)
def validate_episode(
    script_id: int,
    episode_id: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    script = _get_owned_script(script_id, current.id, db)
    eps = _ensure_content_array(script, "episodes")
    _, ep = _find_episode(eps, episode_id)
    if ep is None:
        raise HTTPException(404, "分集不存在")
    result = _validate_episode_duration(script, ep)
    return {"episode_id": episode_id, **result}


@router.post("/{script_id}/episodes/{episode_id}/pass", response_model=EpisodePassOut)
def pass_episode(
    script_id: int,
    episode_id: str,
    force: bool = False,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    script = _get_owned_script(script_id, current.id, db)
    eps = _ensure_content_array(script, "episodes")
    idx, ep = _find_episode(eps, episode_id)
    if ep is None:
        raise HTTPException(404, "分集不存在")

    result = _validate_episode_duration(script, ep)
    if not result["valid"] and not force:
        raise HTTPException(409, {
            "message": "本集时长校验未通过，无法标记为已通过",
            "validation": {"episode_id": episode_id, **result},
        })

    ep["passed"] = True
    ep["passed_at"] = datetime.utcnow().isoformat()
    eps[idx] = ep
    script.content["episodes"] = eps

    pm = _ensure_passed_map(script)
    pm[str(episode_id)] = {
        "passed": True,
        "passed_at": ep["passed_at"],
        "actual_duration": result["actual_duration"],
        "expected_duration": result["expected_duration"],
    }
    script.content["passedEpisodes"] = pm
    _touch(script, db)

    return {
        "episode_id": episode_id,
        "passed": True,
        "passed_at": datetime.fromisoformat(ep["passed_at"]),
        "validation": {"episode_id": episode_id, **result},
    }


@router.post("/{script_id}/episodes/{episode_id}/unpass")
def unpass_episode(
    script_id: int,
    episode_id: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    script = _get_owned_script(script_id, current.id, db)
    eps = _ensure_content_array(script, "episodes")
    idx, ep = _find_episode(eps, episode_id)
    if ep is None:
        raise HTTPException(404, "分集不存在")
    ep["passed"] = False
    ep.pop("passed_at", None)
    eps[idx] = ep
    pm = _ensure_passed_map(script)
    pm.pop(str(episode_id), None)
    script.content["episodes"] = eps
    script.content["passedEpisodes"] = pm
    _touch(script, db)
    return {"unpassed": True, "id": episode_id}


@router.get("/{script_id}/episodes/passed/all")
def list_passed_episodes(
    script_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    script = _get_owned_script(script_id, current.id, db)
    pm = _ensure_passed_map(script)
    eps = _ensure_content_array(script, "episodes")
    passed_ids = set(pm.keys())
    passed_list = []
    for e in eps:
        if str(e.get("id")) in passed_ids:
            passed_list.append({"id": e.get("id"), "title": e.get("title"), **pm[str(e.get("id"))]})
    return {
        "script_id": script_id,
        "total": len(eps),
        "passed_count": len(passed_list),
        "all_passed": len(eps) > 0 and len(passed_list) == len(eps),
        "passed": passed_list,
    }
