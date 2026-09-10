from datetime import datetime
from typing import Any, Optional
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
    content: dict = Field(default_factory=dict)


class ScriptUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    cover_url: Optional[str] = None
    status: Optional[str] = None
    path_type: Optional[str] = None
    content: Optional[dict] = None


class ScriptOut(BaseModel):
    id: int
    title: str
    path_type: str
    description: Optional[str] = None
    cover_url: Optional[str] = None
    status: str
    current_version_id: Optional[int] = None
    content: dict
    owner_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScriptListItem(BaseModel):
    id: int
    title: str
    path_type: str
    description: Optional[str] = None
    status: str
    current_version_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------- Version ----------
class VersionCreate(BaseModel):
    name: Optional[str] = None
    commit_message: Optional[str] = None
    content: Optional[dict] = None


class VersionRestore(BaseModel):
    version_id: int


class VersionOut(BaseModel):
    id: int
    script_id: int
    version_number: int
    name: Optional[str] = None
    commit_message: Optional[str] = None
    content: dict
    created_at: datetime

    model_config = {"from_attributes": True}
