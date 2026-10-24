from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EnrollmentCreatedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enrollment_id: UUID
    application_id: UUID
    participant_id: UUID


class ParticipantNoticeView(BaseModel):
    id: UUID
    enrollment_id: UUID
    topic: Literal["enrollment_created"] = "enrollment_created"
    template_version: Literal["enrollment-created-v1"] = "enrollment-created-v1"
    action_kind: Literal["schedule"] = "schedule"
    created_at: datetime
    expires_at: datetime
    read_at: datetime | None
    version: int


class ParticipantNoticeList(BaseModel):
    items: list[ParticipantNoticeView]
    next_cursor: UUID | None


class ParticipantPreferenceView(BaseModel):
    topic: Literal["enrollment_created"] = "enrollment_created"
    enabled: bool
    version: int


class ParticipantPreferenceEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool
    expected_version: int = Field(ge=0)


class ParticipantMarkRead(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)


class ParticipantOutboxHealth(BaseModel):
    pending_due: int
    oldest_due_seconds: float | None
    retrying: int
    dispatched: int
    suppressed: int
    unsupported: int
    invalid: int
    failed: int
    expired: int
    retention_configured: bool
