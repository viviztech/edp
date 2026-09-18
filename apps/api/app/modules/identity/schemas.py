from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)


class EmailInput(Input):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().casefold()


class PasswordInput(Input):
    password: SecretStr = Field(min_length=12, max_length=128)


class Register(EmailInput, PasswordInput):
    display_name: str = Field(min_length=1, max_length=120)
    locale: Literal["en", "ta"] = "en"

    @field_validator("display_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Name required")
        return value.strip()


class Login(EmailInput, PasswordInput):
    device_name: str = Field(default="Device", min_length=1, max_length=80)


class TokenInput(Input):
    token: SecretStr = Field(min_length=32, max_length=256)


class Reset(TokenInput, PasswordInput):
    pass


class Message(BaseModel):
    status: str = "accepted"


class Tokens(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class BrowserTokens(BaseModel):
    browser_token: str
    csrf_token: str
    expires_in: int


class Grant(BaseModel):
    organization_id: UUID
    organization_name: str
    permissions: list[str]


class Profile(BaseModel):
    id: UUID
    display_name: str
    email: str
    locale: str
    grants: list[Grant]


class SessionView(BaseModel):
    id: UUID
    device_name: str
    channel: str
    created_at: datetime
    expires_at: datetime
    current: bool


class AuditView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    action: str
    actor_id: UUID | None
    resource_id: UUID | None
    created_at: datetime
    request_id: str


class StaffView(BaseModel):
    organization_id: UUID
    organization_name: str
