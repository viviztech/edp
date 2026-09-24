from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CriterionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    label_en: str = Field(min_length=1, max_length=300)
    label_ta: str = Field(min_length=1, max_length=300)
    guidance_en: str | None = Field(default=None, max_length=1000)
    guidance_ta: str | None = Field(default=None, max_length=1000)
    weight: int = Field(ge=1, le=100)
    minimum_score: int = Field(default=0, ge=0, le=99)
    maximum_score: int = Field(ge=1, le=100)
    required: bool = True

    @field_validator("key", "label_en", "label_ta")
    @classmethod
    def strip_required(cls, value: str) -> str:
        return value.strip()

    @field_validator("guidance_en", "guidance_ta")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def valid_range(self) -> "CriterionInput":
        if self.maximum_score <= self.minimum_score:
            raise ValueError("Maximum score must exceed minimum score")
        return self


class CriterionView(CriterionInput):
    id: UUID
    position: int


class SelectionCycleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    application_cycle_id: UUID
    code: str = Field(min_length=1, max_length=60, pattern=r"^[a-z][a-z0-9_-]*$")
    name_en: str = Field(min_length=1, max_length=160)
    name_ta: str = Field(min_length=1, max_length=160)

    @field_validator("code", "name_en", "name_ta")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class SelectionCycleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    name_en: str = Field(min_length=1, max_length=160)
    name_ta: str = Field(min_length=1, max_length=160)

    @field_validator("name_en", "name_ta")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class CycleCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    target: Literal["active", "closed"]
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        return value.strip()


class SelectionCycleView(SelectionCycleCreate):
    id: UUID
    organization_id: UUID
    state: Literal["draft", "active", "closed"]
    version: int
    created_at: datetime
    updated_at: datetime


class RubricUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_edit_version: int = Field(ge=1)
    criteria: list[CriterionInput] = Field(min_length=1, max_length=25)

    @model_validator(mode="after")
    def unique_and_weighted(self) -> "RubricUpdate":
        keys = [item.key for item in self.criteria]
        if len(keys) != len(set(keys)):
            raise ValueError("Criterion keys must be unique")
        if sum(item.weight for item in self.criteria) != 100:
            raise ValueError("Criterion weights must total 100")
        return self


class RubricCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_edit_version: int = Field(ge=1)


class RubricView(BaseModel):
    id: UUID
    organization_id: UUID
    selection_cycle_id: UUID
    version_number: int
    state: Literal["draft", "published", "retired"]
    edit_version: int
    published_at: datetime | None
    criteria: list[CriterionView]
    created_at: datetime
    updated_at: datetime


class SubmittedApplicationSummary(BaseModel):
    id: UUID
    application_number: str
    state: Literal["submitted", "under_review"]
    submitted_at: datetime


class ReviewerView(BaseModel):
    id: UUID
    display_name: str


class AssignmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    selection_cycle_id: UUID
    application_id: UUID
    reviewer_user_id: UUID


class ConflictCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    status: Literal["clear", "conflict"]
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def conflict_requires_note(self) -> "ConflictCommand":
        self.note = self.note.strip() if self.note else None
        if self.status == "conflict" and (not self.note or len(self.note) < 3):
            raise ValueError("A conflict note is required")
        if self.status == "clear":
            self.note = None
        return self


class AssignmentView(BaseModel):
    id: UUID
    organization_id: UUID
    selection_cycle_id: UUID
    rubric_id: UUID
    application_id: UUID
    application_number: str
    reviewer_user_id: UUID
    reviewer_name: str
    status: Literal["assigned", "in_review", "completed"]
    conflict_status: Literal["pending", "clear", "conflict"]
    conflict_note: str | None
    scores: list["ScoreView"]
    internal_comment: str | None
    weighted_score: Decimal | None
    submitted_at: datetime | None
    moderation_status: Literal["included", "excluded"]
    moderation_reason: str | None
    moderated_at: datetime | None
    version: int
    created_at: datetime
    updated_at: datetime


class ScoreInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    criterion_id: UUID
    score: Decimal = Field(ge=0, le=100, max_digits=6, decimal_places=2)


class ScoreView(ScoreInput):
    pass


class ReviewSave(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    scores: list[ScoreInput] = Field(max_length=25)
    internal_comment: str | None = Field(default=None, max_length=4000)

    @field_validator("internal_comment")
    @classmethod
    def strip_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @model_validator(mode="after")
    def unique_criteria(self) -> "ReviewSave":
        ids = [item.criterion_id for item in self.scores]
        if len(ids) != len(set(ids)):
            raise ValueError("Criterion scores must be unique")
        return self


class ReviewSubmit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)


class ModerationCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    status: Literal["included", "excluded"]
    reason: str = Field(min_length=3, max_length=1000)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        return value.strip()


class ApplicationAggregateView(BaseModel):
    application_id: UUID
    application_number: str
    application_state: Literal[
        "under_review", "shortlisted", "interview_scheduled", "selected", "waitlisted", "rejected"
    ]
    application_version: int
    selection_cycle_id: UUID
    completed_reviews: int
    included_reviews: int
    excluded_reviews: int
    aggregate_score: Decimal | None


class InterviewCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    selection_cycle_id: UUID
    application_id: UUID
    starts_at: datetime
    ends_at: datetime
    mode: Literal["online", "in_person"]
    location: str | None = Field(default=None, max_length=500)
    panel_user_ids: list[UUID] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def valid_interview(self) -> "InterviewCreate":
        if self.ends_at <= self.starts_at:
            raise ValueError("Interview end must follow start")
        if len(self.panel_user_ids) != len(set(self.panel_user_ids)):
            raise ValueError("Panel members must be unique")
        self.location = self.location.strip() if self.location else None
        if self.mode == "in_person" and not self.location:
            raise ValueError("In-person interview location is required")
        return self


class PanelMemberView(BaseModel):
    id: UUID
    user_id: UUID
    display_name: str
    score: Decimal | None
    comment: str | None
    submitted_at: datetime | None
    version: int


class InterviewView(BaseModel):
    id: UUID
    organization_id: UUID
    selection_cycle_id: UUID
    application_id: UUID
    application_number: str
    starts_at: datetime
    ends_at: datetime
    mode: Literal["online", "in_person"]
    location: str | None
    status: Literal["scheduled", "completed"]
    average_score: Decimal | None
    completed_at: datetime | None
    version: int
    panel: list[PanelMemberView]
    created_at: datetime
    updated_at: datetime


class PanelScoreSubmit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    score: Decimal = Field(ge=0, le=100, max_digits=6, decimal_places=2)
    comment: str | None = Field(default=None, max_length=4000)

    @field_validator("comment")
    @classmethod
    def strip_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class InterviewComplete(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)


class DecisionCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_application_version: int = Field(ge=1)
    target: Literal["shortlisted", "selected", "waitlisted", "rejected"]
    reason: str = Field(min_length=3, max_length=1000)
    override: bool = False

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        return value.strip()


class DecisionView(BaseModel):
    id: UUID
    organization_id: UUID
    selection_cycle_id: UUID
    application_id: UUID
    application_number: str
    actor_user_id: UUID
    from_state: Literal[
        "under_review", "shortlisted", "interview_scheduled", "selected", "waitlisted", "rejected"
    ]
    to_state: Literal["shortlisted", "selected", "waitlisted", "rejected"]
    reason: str
    is_override: bool
    aggregate_score_snapshot: Decimal | None
    interview_score_snapshot: Decimal | None
    application_version: int
    created_at: datetime


class SelectionWorkspace(BaseModel):
    cycles: list[SelectionCycleView]
    rubrics: list[RubricView]
    applications: list[SubmittedApplicationSummary]
    reviewers: list[ReviewerView]
    assignments: list[AssignmentView]
    aggregates: list["ApplicationAggregateView"]
    interviews: list[InterviewView]
    decisions: list[DecisionView]
