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
