from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Date, ForeignKey, JSON, Boolean,
    BigInteger, Float, Index, UniqueConstraint, LargeBinary,
)
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(128), unique=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(64), nullable=True)
    avatar_url = Column(String(512), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    quota_daily = Column(Integer, default=200, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    scripts = relationship("Script", back_populates="owner", cascade="all, delete-orphan")


class Script(Base):
    __tablename__ = "scripts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    path_type = Column(String(16), default="ai", nullable=False)
    description = Column(Text, nullable=True)
    cover_url = Column(String(512), nullable=True)
    status = Column(String(16), default="draft", nullable=False)
    step = Column(Integer, default=0, nullable=False)
    progress = Column(Integer, default=0, nullable=False)
    tags = Column(JSON, nullable=True)
    config = Column(JSON, nullable=True)
    current_version_id = Column(Integer, nullable=True)
    content = Column(JSON, nullable=False, default=dict)
    locked_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    owner = relationship("User", back_populates="scripts")
    versions = relationship(
        "ScriptVersion", back_populates="script",
        cascade="all, delete-orphan", order_by="ScriptVersion.version_number.desc()",
    )


class ScriptVersion(Base):
    __tablename__ = "script_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    script_id = Column(Integer, ForeignKey("scripts.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    name = Column(String(128), nullable=True)
    commit_message = Column(String(512), nullable=True)
    is_final = Column(Boolean, default=False, nullable=False)
    content = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    script = relationship("Script", back_populates="versions")

    __table_args__ = (
        Index("ix_version_script_num", "script_id", "version_number", unique=True),
    )


class ScriptImport(Base):
    __tablename__ = "script_imports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    script_id = Column(Integer, ForeignKey("scripts.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(16), nullable=False)
    file_size = Column(Integer, default=0, nullable=False)
    file_url = Column(String(512), nullable=True)
    raw_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class TagDictionary(Base):
    __tablename__ = "tag_dictionaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(32), nullable=False, index=True)
    name = Column(String(64), nullable=False)
    weight = Column(Integer, default=0, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("category", "name", name="uq_tag_cat_name"),
    )


class AiProvider(Base):
    __tablename__ = "ai_providers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), unique=True, nullable=False)
    provider = Column(String(32), nullable=False)
    model_name = Column(String(128), nullable=False)
    base_url = Column(String(255), nullable=False, default="")
    api_key_enc = Column(String(512), nullable=False, default="")
    task_bindings = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_key = Column(String(64), nullable=False, index=True)
    version = Column(String(16), nullable=False)
    system_prompt = Column(Text, nullable=False)
    user_prompt_template = Column(Text, nullable=False)
    variables = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("task_key", "version", name="uq_prompt_task_ver"),
    )


class AiSkill(Base):
    __tablename__ = "ai_skills"

    key = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(32), nullable=False, default="general", index=True)
    api_path = Column(String(128), nullable=False, unique=True)
    result_key = Column(String(64), nullable=True)
    prompt_version = Column(String(16), nullable=False, default="v1")
    temperature = Column(Float, nullable=False, default=0.7)
    priority = Column(Integer, nullable=False, default=100)
    timeout = Column(Integer, nullable=False, default=120)
    max_tokens = Column(Integer, nullable=False, default=4096)
    input_schema = Column(JSON, nullable=True)
    output_schema = Column(JSON, nullable=True)
    stream_progress = Column(Boolean, nullable=False, default=False)
    auto_review = Column(Boolean, nullable=False, default=False)
    script_id_field = Column(String(64), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    is_builtin = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AiCall(Base):
    __tablename__ = "ai_calls"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    queue_task_id = Column(BigInteger, ForeignKey("ai_tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    script_id = Column(Integer, ForeignKey("scripts.id"), index=True, nullable=True)
    version_id = Column(Integer, ForeignKey("script_versions.id"), nullable=True)
    task_key = Column(String(64), nullable=False, index=True)
    provider_id = Column(Integer, ForeignKey("ai_providers.id"), nullable=True)
    provider_name = Column(String(64), nullable=True)
    model_name = Column(String(128), nullable=False, default="mock")
    input_tokens = Column(Integer, default=0, nullable=False)
    output_tokens = Column(Integer, default=0, nullable=False)
    latency_ms = Column(Integer, default=0, nullable=False)
    queue_wait_ms = Column(Integer, default=0, nullable=False)
    attempt = Column(Integer, default=1, nullable=False)
    status = Column(String(16), nullable=False, default="success", index=True)
    error_class = Column(String(32), nullable=True, index=True)
    error_msg = Column(Text, nullable=True)
    request_body = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


TASK_STATUS_PENDING = "pending"
TASK_STATUS_QUEUED = "queued"
TASK_STATUS_RUNNING = "running"
TASK_STATUS_SUCCESS = "success"
TASK_STATUS_FAILED = "failed"
TASK_STATUS_CANCELLED = "cancelled"
TASK_STATUS_DEAD_LETTER = "dead_letter"

TASK_PRIORITY_HIGH = 200
TASK_PRIORITY_NORMAL = 100
TASK_PRIORITY_LOW = 50

ERROR_CLASS_NETWORK = "network"
ERROR_CLASS_TIMEOUT = "timeout"
ERROR_CLASS_RATE_LIMIT = "rate_limit"
ERROR_CLASS_AUTH = "auth"
ERROR_CLASS_BAD_REQUEST = "bad_request"
ERROR_CLASS_PARSE = "parse"
ERROR_CLASS_PROVIDER = "provider_error"
ERROR_CLASS_CANCELLED = "cancelled"
ERROR_CLASS_UNKNOWN = "unknown"


class AiTask(Base):
    __tablename__ = "ai_tasks"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_key = Column(String(64), nullable=False, index=True)
    skill_name = Column(String(64), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    script_id = Column(Integer, ForeignKey("scripts.id"), nullable=True, index=True)
    version_id = Column(Integer, ForeignKey("script_versions.id"), nullable=True)
    provider_name = Column(String(64), nullable=True)
    provider_id = Column(Integer, ForeignKey("ai_providers.id"), nullable=True)
    model_name = Column(String(128), nullable=True)

    status = Column(String(16), nullable=False, default=TASK_STATUS_QUEUED, index=True)
    priority = Column(Integer, default=TASK_PRIORITY_NORMAL, nullable=False, index=True)
    progress = Column(Integer, default=0, nullable=False)
    phase = Column(String(64), nullable=True)

    params = Column(JSON, nullable=True)
    result_json = Column(JSON, nullable=True)
    result_text = Column(Text(length=4294967295), nullable=True)
    error_class = Column(String(32), nullable=True, index=True)
    error_msg = Column(Text, nullable=True)

    attempts = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=2, nullable=False)
    worker_id = Column(String(64), nullable=True, index=True)
    heartbeat_at = Column(DateTime, nullable=True)

    queue_wait_ms = Column(Integer, default=0, nullable=False)
    exec_ms = Column(Integer, default=0, nullable=False)
    total_ms = Column(Integer, default=0, nullable=False)
    input_tokens = Column(Integer, default=0, nullable=False)
    output_tokens = Column(Integer, default=0, nullable=False)

    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)

    events = relationship(
        "AiTaskEvent", back_populates="task",
        cascade="all, delete-orphan", order_by="AiTaskEvent.seq.asc()",
    )

    __table_args__ = (
        Index("ix_task_status_pickup", "status", "priority", "created_at"),
        Index("ix_task_user_status", "user_id", "status", "created_at"),
    )


class AiTaskEvent(Base):
    __tablename__ = "ai_task_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(BigInteger, ForeignKey("ai_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    seq = Column(Integer, nullable=False)
    event_type = Column(String(16), nullable=False, index=True)
    phase = Column(String(64), nullable=True)
    progress = Column(Integer, nullable=True)
    data = Column(Text, nullable=True)
    meta = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    task = relationship("AiTask", back_populates="events")

    __table_args__ = (
        Index("ix_event_task_seq", "task_id", "seq", unique=True),
    )
