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
    script_id: Optional[int] = None


class AiTaskSubmitOut(BaseModel):
    task_id: int
    status: str
    position: int = 0
    estimated_wait_sec: int = 0
    stream_url: str


class AiTaskEventOut(BaseModel):
    id: int
    seq: int
    event_type: str
    phase: Optional[str] = None
    progress: Optional[int] = None
    data: Optional[str] = None
    meta: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AiTaskOut(BaseModel):
    id: int
    task_key: str
    skill_name: Optional[str] = None
    user_id: int
    script_id: Optional[int] = None
    provider_name: Optional[str] = None
    model_name: Optional[str] = None
    status: str
    priority: int
    progress: int
    phase: Optional[str] = None
    error_class: Optional[str] = None
    error_msg: Optional[str] = None
    attempts: int
    max_retries: int
    queue_wait_ms: int = 0
    exec_ms: int = 0
    total_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    result_json: Optional[Any] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    estimated_wait_sec: int = 0
    worker_id: Optional[str] = None

    model_config = {"from_attributes": True}


class AiTaskDetailOut(AiTaskOut):
    result_text: Optional[str] = None
    events: List[AiTaskEventOut] = Field(default_factory=list)


class AiTaskStatsOut(BaseModel):
    total: int = 0
    queued: int = 0
    running: int = 0
    success: int = 0
    failed: int = 0
    dead_letter: int = 0
    cancelled: int = 0
    concurrency: int = 0
    by_task_key: dict = Field(default_factory=dict)
    by_provider: dict = Field(default_factory=dict)
    by_error_class: dict = Field(default_factory=dict)
    avg_latency_ms: float = 0
    avg_queue_wait_ms: float = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0


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


# ---------- AI Provider 模型管理 ----------
class AiProviderIn(BaseModel):
    model_config = {"protected_namespaces": ()}

    name: str = Field(min_length=1, max_length=64, description="唯一标识名，如 deepseek/gpt4o")
    provider: str = Field(default="openai", description="协议类型，目前支持 openai（兼容协议）/mock")
    model_name: str = Field(min_length=1, max_length=128, description="模型名，如 deepseek-chat / gpt-4o-mini")
    base_url: str = Field(default="", max_length=255, description="OpenAI 兼容端点根，如 https://api.deepseek.com/v1")
    api_key: str = Field(default="", max_length=512, description="API Key；mock 可留空")
    task_bindings: List[str] = Field(default_factory=list, description="绑定的 task_key 列表；['*'] 表示全部任务兜底")
    is_active: bool = True
    priority: int = 100


class AiProviderUpdate(BaseModel):
    model_config = {"protected_namespaces": ()}

    provider: Optional[str] = None
    model_name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    task_bindings: Optional[List[str]] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None


class AiProviderOut(BaseModel):
    id: int
    name: str
    provider: str
    model_name: str
    base_url: str
    has_key: bool = False
    key_preview: str = ""
    task_bindings: List[str] = []
    is_active: bool
    priority: int
    created_at: datetime

    model_config = {"from_attributes": True, "protected_namespaces": ()}


class AiProviderBindReq(BaseModel):
    task_bindings: List[str] = Field(description="task_key 数组，如 ['generate_outline','generate_episode']；['*'] 为全任务兜底")


class AiProviderTestResult(BaseModel):
    ok: bool
    provider: str
    model: Optional[str] = None
    reply: Optional[str] = None
    usage: Optional[dict] = None
    error: Optional[str] = None


# ---------- AI Skill / Prompt 管理 ----------
class PromptVersionOut(BaseModel):
    id: int
    task_key: str
    version: str
    system_prompt: str
    user_prompt_template: str
    variables: Optional[dict] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AiSkillListItem(BaseModel):
    key: str
    name: str
    description: Optional[str] = None
    category: str
    api_path: str
    result_key: Optional[str] = None
    prompt_version: str
    temperature: float
    priority: int
    timeout: int
    max_tokens: int = 4096
    stream_progress: bool
    auto_review: bool
    script_id_field: Optional[str] = None
    is_active: bool
    is_builtin: bool
    updated_at: datetime

    model_config = {"from_attributes": True}


class AiSkillDetailOut(AiSkillListItem):
    input_schema: Optional[dict] = None
    output_schema: Optional[dict] = None
    active_prompt: Optional[PromptVersionOut] = None
    versions: List[PromptVersionOut] = Field(default_factory=list)
    created_at: datetime


class AiSkillUpdateReq(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    temperature: Optional[float] = None
    priority: Optional[int] = None
    timeout: Optional[int] = None
    max_tokens: Optional[int] = None
    stream_progress: Optional[bool] = None
    auto_review: Optional[bool] = None
    is_active: Optional[bool] = None
    prompt_version: Optional[str] = None
    new_system_prompt: Optional[str] = None
    new_user_prompt_template: Optional[str] = None
    new_version_label: Optional[str] = None
