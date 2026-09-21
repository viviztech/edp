from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

NotificationTopic = Literal["lead_assignment", "followup_due"]


class PreferenceView(BaseModel):
    topic: NotificationTopic = "lead_assignment"
    enabled: bool
    version: int


class PreferenceEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool
    expected_version: int = Field(ge=0)


class NotificationView(BaseModel):
    id: UUID
    topic: NotificationTopic
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


class FailureView(BaseModel):
    id: UUID
    topic: NotificationTopic
    state: Literal["failed"]
    attempt_count: int
    error_code: str
    created_at: datetime
    version: int


class FailureList(BaseModel):
    items: list[FailureView]
    next_cursor: UUID | None


class ReplayRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=8, max_length=500)
