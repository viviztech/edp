import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class IntegrationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=120)
    page_id: str = Field(min_length=1, max_length=80, pattern=r"^[0-9A-Za-z_-]+$")
    access_token: SecretStr = Field(min_length=20, max_length=4096)
    app_secret: SecretStr = Field(min_length=16, max_length=512)
    verify_token: SecretStr = Field(min_length=24, max_length=512)


class IntegrationView(BaseModel):
    id: UUID
    name: str
    page_id: str
    status: Literal["active", "disabled"]
    version: int
    created_at: datetime


class IntegrationList(BaseModel):
    items: list[IntegrationView]
    next_cursor: UUID | None


class MappingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    form_id: str = Field(min_length=1, max_length=80, pattern=r"^[0-9A-Za-z_-]+$")
    name: str = Field(min_length=1, max_length=120)
    campaign: str = Field(default="", max_length=120)
    field_mapping: dict[str, Literal["name", "email", "phone"]]

    @field_validator("field_mapping")
    @classmethod
    def mapping_contract(
        cls, value: dict[str, Literal["name", "email", "phone"]]
    ) -> dict[str, Literal["name", "email", "phone"]]:
        if not 1 <= len(value) <= 20 or "name" not in value.values():
            raise ValueError("mapping must contain a name target")
        if any(not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", source) for source in value):
            raise ValueError("invalid provider field name")
        if len(set(value.values())) != len(value):
            raise ValueError("mapping targets must be unique")
        return value


class MappingView(BaseModel):
    id: UUID
    integration_id: UUID
    form_id: str
    name: str
    campaign: str
    field_mapping: dict[str, str]
    status: Literal["active", "disabled"]
    version: int


class MappingList(BaseModel):
    items: list[MappingView]


class EventView(BaseModel):
    id: UUID
    integration_id: UUID
    mapping_id: UUID | None
    meta_lead_id: str
    page_id: str
    form_id: str
    state: Literal["queued", "processing", "retrying", "completed", "failed"]
    attempt_count: int
    error_code: str
    lead_id: UUID | None
    created_at: datetime
    processed_at: datetime | None


class EventList(BaseModel):
    items: list[EventView]
    next_cursor: UUID | None


class WebhookAccepted(BaseModel):
    accepted: int
    duplicates: int
