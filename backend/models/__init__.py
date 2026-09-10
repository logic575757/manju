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


class AiCall(Base):
    __tablename__ = "ai_calls"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    script_id = Column(Integer, ForeignKey("scripts.id"), index=True, nullable=True)
    version_id = Column(Integer, ForeignKey("script_versions.id"), nullable=True)
    task_key = Column(String(64), nullable=False, index=True)
    provider_id = Column(Integer, ForeignKey("ai_providers.id"), nullable=True)
    model_name = Column(String(128), nullable=False, default="mock")
    input_tokens = Column(Integer, default=0, nullable=False)
    output_tokens = Column(Integer, default=0, nullable=False)
    latency_ms = Column(Integer, default=0, nullable=False)
    status = Column(String(16), nullable=False, default="success")
    error_msg = Column(Text, nullable=True)
    request_body = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class AiTask(Base):
    __tablename__ = "ai_tasks"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_key = Column(String(64), nullable=False, index=True)
    script_id = Column(Integer, ForeignKey("scripts.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(16), nullable=False, default="pending", index=True)
    progress = Column(Integer, default=0, nullable=False)
    params = Column(JSON, nullable=True)
    result_ref = Column(String(255), nullable=True)
    error_msg = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
