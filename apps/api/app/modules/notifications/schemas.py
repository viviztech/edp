from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PreferenceView(BaseModel):
    topic: Literal["lead_assignment"] = "lead_assignment"
    enabled: bool
    version: int


class PreferenceEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool
    expected_version: int = Field(ge=0)


class NotificationView(BaseModel):
    id: UUID
    topic: Literal["lead_assignment"]
    resource_id: UUID
    created_at: datetime
    read_at: datetime | None
    version: int


class NotificationList(BaseModel):
    items: list[NotificationView]
    next_cursor: UUID | None


class MarkRead(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
