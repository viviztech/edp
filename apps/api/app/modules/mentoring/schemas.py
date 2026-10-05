from datetime import date, datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

ProfileState = Literal["active", "inactive"]
AssignmentState = Literal["active", "ended"]
SessionState = Literal["scheduled", "completed", "cancelled"]
ItemState = Literal["open", "completed", "cancelled"]


class ProfileCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: UUID
    headline: str = Field(min_length=2, max_length=160)
    biography: str | None = Field(default=None, max_length=4000)


class ProfileView(ProfileCreate):
    id: UUID
    display_name: str
    state: ProfileState
    version: int


class ExpertiseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mentor_profile_id: UUID
    code: str = Field(min_length=1, max_length=60, pattern=r"^[a-z][a-z0-9_-]*$")
    name_en: str = Field(min_length=1, max_length=120)
    name_ta: str = Field(min_length=1, max_length=120)


class ExpertiseView(ExpertiseCreate):
    id: UUID


class AvailabilityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mentor_profile_id: UUID
    weekday: int = Field(ge=0, le=6)
    starts_at: time
    ends_at: time
    timezone: str = Field(default="Asia/Kolkata", min_length=3, max_length=64)

    @model_validator(mode="after")
    def valid_range(self) -> "AvailabilityCreate":
        if self.ends_at <= self.starts_at:
            raise ValueError("Availability end must follow start")
        return self


class AvailabilityView(AvailabilityCreate):
    id: UUID


class AssignmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mentor_profile_id: UUID
    enrollment_id: UUID
    starts_on: date
    ends_on: date | None = None
    reason: str = Field(min_length=3, max_length=500)

    @model_validator(mode="after")
    def valid_dates(self) -> "AssignmentCreate":
        if self.ends_on and self.ends_on < self.starts_on:
            raise ValueError("Assignment end must not precede start")
        return self


class AssignmentEnd(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=500)


class MentorAssignmentView(BaseModel):
    id: UUID
    mentor_profile_id: UUID
    mentor_name: str
    enrollment_id: UUID
    participant_id: UUID
    participant_name: str
    program_id: UUID
    starts_on: date
    ends_on: date | None
    state: AssignmentState
    version: int


class SessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assignment_id: UUID
    starts_at: datetime
    ends_at: datetime
    mode: Literal["in_person", "online", "phone"]
    location_or_link: str | None = Field(default=None, max_length=500)
    topic: str = Field(min_length=2, max_length=240)

    @model_validator(mode="after")
    def valid_range(self) -> "SessionCreate":
        if self.ends_at <= self.starts_at:
            raise ValueError("Session end must follow start")
        return self


class StateCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    target: str
    reason: str = Field(min_length=3, max_length=500)


class SessionView(BaseModel):
    id: UUID
    assignment_id: UUID
    starts_at: datetime
    ends_at: datetime
    mode: str
    location_or_link: str | None
    topic: str
    status: SessionState
    version: int


class NoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assignment_id: UUID
    session_id: UUID | None = None
    visibility: Literal["mentor_private", "shared_with_participant"]
    body: str = Field(min_length=1, max_length=10000)


class NoteView(BaseModel):
    id: UUID
    assignment_id: UUID
    session_id: UUID | None
    visibility: str
    body: str
    created_at: datetime


class GoalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assignment_id: UUID
    title: str = Field(min_length=2, max_length=240)
    description: str | None = Field(default=None, max_length=4000)
    target_date: date | None = None


class GoalUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    progress_percent: int = Field(ge=0, le=100)
    target: Literal["active", "completed", "cancelled"]
    reason: str = Field(min_length=3, max_length=500)


class GoalView(BaseModel):
    id: UUID
    assignment_id: UUID
    title: str
    description: str | None
    target_date: date | None
    progress_percent: int
    state: str
    version: int


class ActionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assignment_id: UUID
    goal_id: UUID | None = None
    title: str = Field(min_length=2, max_length=240)
    due_at: datetime | None = None


class ActionView(BaseModel):
    id: UUID
    assignment_id: UUID
    goal_id: UUID | None
    title: str
    due_at: datetime | None
    state: str
    version: int


class FollowUpCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assignment_id: UUID
    session_id: UUID | None = None
    purpose: str = Field(min_length=2, max_length=240)
    due_at: datetime


class FollowUpView(BaseModel):
    id: UUID
    assignment_id: UUID
    session_id: UUID | None
    purpose: str
    due_at: datetime
    state: str
    overdue: bool
    version: int


class FeedbackCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: UUID
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class FeedbackView(FeedbackCreate):
    id: UUID
    created_at: datetime


class MentorCandidateView(BaseModel):
    user_id: UUID
    display_name: str
    has_profile: bool


class EnrollmentCandidateView(BaseModel):
    enrollment_id: UUID
    participant_name: str
    program_id: UUID
    has_active_assignment: bool


class Workspace(BaseModel):
    mentor_candidates: list[MentorCandidateView]
    enrollment_candidates: list[EnrollmentCandidateView]
    profiles: list[ProfileView]
    expertise: list[ExpertiseView]
    availability: list[AvailabilityView]
    assignments: list[MentorAssignmentView]
    sessions: list[SessionView]
    notes: list[NoteView]
    goals: list[GoalView]
    action_items: list[ActionView]
    follow_ups: list[FollowUpView]
    feedback_count: int
    average_rating: float | None


class MyMentoring(BaseModel):
    assignments: list[MentorAssignmentView]
    sessions: list[SessionView]
    notes: list[NoteView]
    goals: list[GoalView]
    action_items: list[ActionView]
    follow_ups: list[FollowUpView]
    feedback: list[FeedbackView]
