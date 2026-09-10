from datetime import datetime
from typing import Any, Optional, List
from pydantic import BaseModel, Field


# ---------- Auth ----------
class UserRegister(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    email: Optional[str] = None
    display_name: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Script ----------
class ScriptCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    path_type: str = "ai"
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    config: Optional[dict] = None
    content: Optional[dict] = Field(default_factory=dict)


class ScriptPatch(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    cover_url: Optional[str] = None
    status: Optional[str] = None
    step: Optional[int] = None
    progress: Optional[int] = None
    path_type: Optional[str] = None
    tags: Optional[List[str]] = None
    config: Optional[dict] = None
    content: Optional[dict] = None


class ScriptLockRequest(BaseModel):
    commit_message: Optional[str] = "定稿版本"
    name: Optional[str] = None


class ScriptListItem(BaseModel):
    id: int
    title: str
    path_type: str
    description: Optional[str] = None
    cover_url: Optional[str] = None
    status: str
    step: int
    progress: int
    tags: Optional[List[str]] = None
    current_version_id: Optional[int] = None
    locked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScriptOut(BaseModel):
    id: int
    title: str
    path_type: str
    description: Optional[str] = None
    cover_url: Optional[str] = None
    status: str
    step: int
    progress: int
    tags: Optional[List[str]] = None
    config: Optional[dict] = None
    current_version_id: Optional[int] = None
    content: dict
    owner_id: int
    locked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScriptDuplicateOut(BaseModel):
    new_id: int
    title: str


# ---------- Version ----------
class VersionCreate(BaseModel):
    name: Optional[str] = None
    commit_message: Optional[str] = None
    content: Optional[dict] = None


class VersionOut(BaseModel):
    id: int
    script_id: int
    version_number: int
    name: Optional[str] = None
    commit_message: Optional[str] = None
    is_final: bool
    content: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class VersionDiffOut(BaseModel):
    v1: int
    v2: int
    diff_count: int
    changes: List[dict]


# ---------- Tags ----------
class TagOut(BaseModel):
    id: int
    category: str
    name: str
    weight: int
    sort_order: int

    model_config = {"from_attributes": True}


# ---------- AI (request bodies; responses are SSE streams) ----------
class AiGenerateOutlineReq(BaseModel):
    script_id: Optional[int] = None
    style: Optional[str] = "爽文短剧"
    episodes: int = 20
    pregen: int = 3
    ep_duration: int = 90
    shot_sec: int = 8
    prompt: Optional[str] = ""
    tags: Optional[dict] = None
    pace: Optional[dict] = None
    art_style: Optional[List[str]] = None
    shot_perf: Optional[List[str]] = None
    sewing_novels: Optional[List[str]] = None


class AiModuleModifyReq(BaseModel):
    script_id: int
    module_id: str
    module: dict
    issues: Optional[List[dict]] = None
    note: Optional[str] = ""


class AiBatchModifyReq(BaseModel):
    script_id: int
    modules: List[dict]
    global_note: Optional[str] = ""


class AiReviewOutlineReq(BaseModel):
    script_id: int
    outline: List[dict]


class AiReviewCharactersReq(BaseModel):
    script_id: int
    characters: List[dict]
    outline: Optional[List[dict]] = None


class AiGenerateCharactersReq(BaseModel):
    script_id: int
    outline: List[dict]
    existing_characters: Optional[List[dict]] = None


class AiGenerateEpisodeReq(BaseModel):
    script_id: int
    episode_index: int
    outline: List[dict]
    characters: List[dict]
    previous_episodes: Optional[List[dict]] = None
    episode_hook: Optional[str] = ""
    ep_duration: int = 90
    sb_sec: int = 8
    pace: Optional[dict] = None


class AiReviewEpisodeReq(BaseModel):
    script_id: int
    episode_index: int
    episode: dict
    outline: Optional[List[dict]] = None
    characters: Optional[List[dict]] = None
    previous_episodes: Optional[List[dict]] = None


class AiFixEpisodeReq(BaseModel):
    script_id: int
    episode_index: int
    episode: dict
    issues: List[dict]


class AiRewriteSegmentReq(BaseModel):
    script_id: int
    episode_index: int
    behavior: dict
    instruction: str
    candidates: int = 2


class AiParseImportReq(BaseModel):
    text: str
    file_name: Optional[str] = ""
    episodes: int = 20
    ep_duration: int = 90
    tone: str = "保持原作风味"


class AiTaskOut(BaseModel):
    id: int
    task_key: str
    status: str
    progress: int
    error_msg: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Characters (nested under script.content["characters"]) ----------
class CharacterIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    model_config = {"extra": "allow"}


class CharacterOut(BaseModel):
    id: str
    model_config = {"extra": "allow"}


class CharacterListOut(BaseModel):
    script_id: int
    count: int
    characters: List[dict]


# ---------- Episodes (nested under script.content["episodes"]) ----------
class EpisodeIn(BaseModel):
    title: Optional[str] = None
    model_config = {"extra": "allow"}


class EpisodeOut(BaseModel):
    id: Any
    model_config = {"extra": "allow"}


class EpisodeListOut(BaseModel):
    script_id: int
    count: int
    episodes: List[dict]


class EpisodeValidateOut(BaseModel):
    episode_id: Any
    valid: bool
    expected_duration: int
    actual_duration: int
    diff: int
    issues: List[str]


class EpisodePassOut(BaseModel):
    episode_id: Any
    passed: bool
    passed_at: Optional[datetime] = None
    validation: EpisodeValidateOut
