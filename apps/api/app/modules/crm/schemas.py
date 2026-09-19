from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

LeadStatus = Literal[
    "new",
    "contacted",
    "interested",
    "registration_started",
    "converted",
    "not_interested",
    "merged",
]


class LeadCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(default="", max_length=320)
    phone: str = Field(default="", max_length=32)
    source: str = Field(default="manual", max_length=80)
    campaign: str = Field(default="", max_length=120)
    notes: str = Field(default="", max_length=5000)


class LeadEdit(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    status: LeadStatus
    assigned_user_id: UUID | None = None
    notes: str = Field(default="", max_length=5000)
    expected_version: int = Field(ge=1)


class LeadView(BaseModel):
    id: UUID
    name: str
    email: str
    phone: str
    source: str
    campaign: str
    status: LeadStatus
    assigned_user_id: UUID | None
    merged_into_id: UUID | None
    notes: str
    version: int


class LeadList(BaseModel):
    items: list[LeadView]
    next_cursor: UUID | None


class ActivityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    activity_type: Literal["call", "email", "meeting", "task", "note"]
    note: str = Field(min_length=1, max_length=5000)
    due_at: datetime | None = None


class ActivityView(ActivityCreate):
    id: UUID
    lead_id: UUID
    actor_user_id: UUID
    completed_at: datetime | None


class ActivityList(BaseModel):
    items: list[ActivityView]


class DuplicateReviewCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lead_a_id: UUID
    lead_b_id: UUID


class DuplicateResolve(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    action: Literal["merge", "reject"]
    survivor_id: UUID | None = None
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=500)


class DuplicateReviewView(BaseModel):
    id: UUID
    lead_a_id: UUID
    lead_b_id: UUID
    state: Literal["pending", "merged", "rejected"]
    version: int
    reason: str
    resolved_by_id: UUID | None


class DuplicateReviewList(BaseModel):
    items: list[DuplicateReviewView]
    next_cursor: UUID | None


class ExportJobView(BaseModel):
    id: UUID
    status: Literal["queued", "running", "completed", "failed"]
    row_count: int
    error_code: str
    completed_at: datetime | None
    expires_at: datetime


class LeadConversionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    person_id: UUID
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=500)


class LeadConversionView(BaseModel):
    id: UUID
    lead_id: UUID
    person_id: UUID
    source: str
    campaign: str
    lead_version: int
    reason: str
    created_at: datetime
