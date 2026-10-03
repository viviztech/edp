from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

AttendanceStatus = Literal["present", "absent", "late", "excused"]


class PolicyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cohort_id: UUID
    expected_version: int | None = Field(default=None, ge=1)
    threshold_percent: int = Field(ge=1, le=100)
    late_after_minutes: int = Field(ge=0, le=240)
    opens_before_minutes: int = Field(ge=0, le=1440)
    closes_after_minutes: int = Field(ge=0, le=1440)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        return value.strip()


class PolicyView(BaseModel):
    id: UUID
    cohort_id: UUID
    threshold_percent: int
    late_after_minutes: int
    opens_before_minutes: int
    closes_after_minutes: int
    version: int
    updated_at: datetime


class WindowCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: UUID
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        return value.strip()


class WindowClose(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        return value.strip()


class WindowView(BaseModel):
    id: UUID
    session_id: UUID
    opens_at: datetime
    closes_at: datetime
    state: Literal["active", "closed"]
    version: int
    created_at: datetime
    closed_at: datetime | None


class WindowCreatedView(WindowView):
    check_in_token: str
    qr_svg_data_url: str


class ManualMark(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enrollment_id: UUID
    status: AttendanceStatus
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        return value.strip()


class CorrectionCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    status: AttendanceStatus
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        return value.strip()


class CheckInCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=32, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")


class RecordView(BaseModel):
    id: UUID
    session_id: UUID
    enrollment_id: UUID
    status: AttendanceStatus
    source: Literal["manual", "qr"]
    marked_at: datetime
    version: int


class ParticipantAttendanceView(BaseModel):
    enrollment_id: UUID
    participant_id: UUID
    display_name: str
    record: RecordView | None


class SessionAttendanceView(BaseModel):
    session_id: UUID
    cohort_id: UUID
    title_en: str
    title_ta: str
    starts_at: datetime
    ends_at: datetime
    session_status: Literal["scheduled", "completed", "cancelled"]
    policy: PolicyView | None
    window: WindowView | None
    participants: list[ParticipantAttendanceView]


class AttendanceSummary(BaseModel):
    attended: int
    required: int
    excused: int
    percent: int
    threshold_percent: int
    low_attendance: bool


class StaffAttendanceWorkspace(BaseModel):
    sessions: list[SessionAttendanceView]


class LearnerSessionAttendance(BaseModel):
    session_id: UUID
    title_en: str
    title_ta: str
    starts_at: datetime
    ends_at: datetime
    session_status: Literal["scheduled", "completed", "cancelled"]
    record: RecordView | None


class LearnerAttendanceView(BaseModel):
    enrollment_id: UUID
    cohort_id: UUID
    cohort_name_en: str
    cohort_name_ta: str
    summary: AttendanceSummary
    sessions: list[LearnerSessionAttendance]


class MyAttendanceView(BaseModel):
    enrollments: list[LearnerAttendanceView]
