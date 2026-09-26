from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ProgramState = Literal["draft", "active", "archived"]
CenterState = Literal["active", "inactive"]
CohortState = Literal["planned", "active", "completed", "cancelled"]
CycleState = Literal["draft", "open", "closed", "cancelled"]
ParticipantState = Literal["active", "suspended", "completed", "withdrawn"]
EnrollmentState = Literal["active", "completed", "withdrawn"]
SessionState = Literal["scheduled", "completed", "cancelled"]
SessionMode = Literal["in_person", "online", "hybrid"]
StaffAssignmentState = Literal["active", "revoked"]


class NamedCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=1, max_length=60, pattern=r"^[a-z][a-z0-9_-]*$")
    name_en: str = Field(min_length=1, max_length=160)
    name_ta: str = Field(min_length=1, max_length=160)

    @field_validator("code", "name_en", "name_ta")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class NamedUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    name_en: str = Field(min_length=1, max_length=160)
    name_ta: str = Field(min_length=1, max_length=160)

    @field_validator("name_en", "name_ta")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class StateCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    target: str
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        return value.strip()


class ProgramView(NamedCreate):
    id: UUID
    organization_id: UUID
    state: ProgramState
    version: int
    created_at: datetime
    updated_at: datetime


class CenterCreate(NamedCreate):
    locality: str = Field(min_length=1, max_length=160)

    @field_validator("locality")
    @classmethod
    def strip_locality(cls, value: str) -> str:
        return value.strip()


class CenterUpdate(NamedUpdate):
    locality: str = Field(min_length=1, max_length=160)

    @field_validator("locality")
    @classmethod
    def strip_locality(cls, value: str) -> str:
        return value.strip()


class CenterView(CenterCreate):
    id: UUID
    organization_id: UUID
    state: CenterState
    version: int
    created_at: datetime
    updated_at: datetime


class CohortCreate(NamedCreate):
    program_id: UUID
    center_id: UUID
    starts_on: date
    ends_on: date
    capacity: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def valid_dates(self) -> "CohortCreate":
        if self.ends_on < self.starts_on:
            raise ValueError("Cohort end must not precede start")
        return self


class CohortUpdate(NamedUpdate):
    program_id: UUID
    center_id: UUID
    starts_on: date
    ends_on: date
    capacity: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def valid_dates(self) -> "CohortUpdate":
        if self.ends_on < self.starts_on:
            raise ValueError("Cohort end must not precede start")
        return self


class CohortView(CohortCreate):
    id: UUID
    organization_id: UUID
    state: CohortState
    version: int
    created_at: datetime
    updated_at: datetime


class CycleCreate(NamedCreate):
    program_id: UUID
    cohort_id: UUID | None = None
    form_id: UUID
    opens_at: datetime
    closes_at: datetime

    @model_validator(mode="after")
    def valid_dates(self) -> "CycleCreate":
        if self.closes_at <= self.opens_at:
            raise ValueError("Cycle close must follow open")
        return self


class CycleUpdate(NamedUpdate):
    program_id: UUID
    cohort_id: UUID | None = None
    form_id: UUID
    opens_at: datetime
    closes_at: datetime

    @model_validator(mode="after")
    def valid_dates(self) -> "CycleUpdate":
        if self.closes_at <= self.opens_at:
            raise ValueError("Cycle close must follow open")
        return self


class CycleView(CycleCreate):
    id: UUID
    organization_id: UUID
    state: CycleState
    version: int
    created_at: datetime
    updated_at: datetime


class StaffAssignmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=254)
    center_id: UUID
    cohort_id: UUID | None = None
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("email", "reason")
    @classmethod
    def strip_assignment_text(cls, value: str) -> str:
        return value.strip()


class StaffAssignmentRevoke(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_revoke_reason(cls, value: str) -> str:
        return value.strip()


class StaffAssignmentView(BaseModel):
    id: UUID
    organization_id: UUID
    user_id: UUID
    email: str
    display_name: str
    center_id: UUID
    cohort_id: UUID | None
    state: StaffAssignmentState
    version: int
    created_at: datetime
    updated_at: datetime
    revoked_at: datetime | None


class EnrollmentCandidateView(BaseModel):
    application_id: UUID
    application_number: str
    application_version: int
    person_id: UUID
    display_name: str
    program_id: UUID
    cohort_id: UUID
    selection_cycle_id: UUID


class ParticipantView(BaseModel):
    id: UUID
    organization_id: UUID
    person_id: UUID
    display_name: str
    status: ParticipantState
    version: int
    created_at: datetime
    updated_at: datetime


class EnrollmentView(BaseModel):
    id: UUID
    organization_id: UUID
    participant_id: UUID
    program_id: UUID
    cohort_id: UUID
    application_id: UUID
    status: EnrollmentState
    enrolled_at: datetime
    version: int
    created_at: datetime
    updated_at: datetime


class EnrollmentConvert(BaseModel):
    model_config = ConfigDict(extra="forbid")
    application_id: UUID
    expected_application_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_conversion_reason(cls, value: str) -> str:
        return value.strip()


class EnrollmentConversionView(BaseModel):
    participant: ParticipantView
    enrollment: EnrollmentView


class ParticipantStateCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    target: ParticipantState
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_participant_reason(cls, value: str) -> str:
        return value.strip()


class SessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cohort_id: UUID
    title_en: str = Field(min_length=1, max_length=200)
    title_ta: str = Field(min_length=1, max_length=200)
    starts_at: datetime
    ends_at: datetime
    mode: SessionMode
    location: str | None = Field(default=None, max_length=500)

    @field_validator("title_en", "title_ta")
    @classmethod
    def strip_session_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("location")
    @classmethod
    def strip_location(cls, value: str | None) -> str | None:
        return value.strip() if value else None

    @model_validator(mode="after")
    def valid_session(self) -> "SessionCreate":
        if self.ends_at <= self.starts_at:
            raise ValueError("Session end must follow start")
        if self.mode != "online" and not self.location:
            raise ValueError("Location is required for in-person and hybrid sessions")
        return self


class SessionView(SessionCreate):
    id: UUID
    organization_id: UUID
    status: SessionState
    version: int
    created_at: datetime
    updated_at: datetime


class SessionStateCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    target: Literal["completed", "cancelled"]
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_session_reason(cls, value: str) -> str:
        return value.strip()


class TimelineEvent(BaseModel):
    occurred_at: datetime
    kind: Literal["application", "selection", "enrollment", "session"]
    state: str
    title_en: str
    title_ta: str
    resource_id: UUID


class ParticipantTimeline(BaseModel):
    participant: ParticipantView
    enrollments: list[EnrollmentView]
    sessions: list[SessionView]
    events: list[TimelineEvent]


class CatalogView(BaseModel):
    programs: list[ProgramView]
    centers: list[CenterView]
    cohorts: list[CohortView]
    cycles: list[CycleView]
    enrollment_candidates: list[EnrollmentCandidateView] = []
    participants: list[ParticipantView] = []
    enrollments: list[EnrollmentView] = []
    sessions: list[SessionView] = []
    staff_assignments: list[StaffAssignmentView] = []
