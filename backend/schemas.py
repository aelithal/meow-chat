from pydantic import BaseModel, field_validator
from datetime import datetime


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Минимум 3 символа")
        if len(v) > 50:
            raise ValueError("Максимум 50 символов")
        if not v.isalnum():
            raise ValueError("Только буквы и цифры")
        return v

    @field_validator("password")
    @classmethod
    def password_valid(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Минимум 6 символов")
        return v


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── User ──────────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: int
    username: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Room ──────────────────────────────────────────────────────────────────────

class RoomCreate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_valid(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Минимум 2 символа")
        if len(v) > 100:
            raise ValueError("Максимум 100 символов")
        return v


class RoomOut(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Message ───────────────────────────────────────────────────────────────────

class MessageOut(BaseModel):
    id: int
    text: str
    created_at: datetime
    author: UserOut

    model_config = {"from_attributes": True}
