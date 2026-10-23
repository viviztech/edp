from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

BusinessStage = Literal["idea", "starting", "operating", "paused", "closed"]
FundingStatus = Literal["none", "seeking", "applied", "approved", "disbursed"]
MoneyBand = Literal["none", "under_1l", "1l_to_5l", "5l_to_25l", "over_25l", "undisclosed"]
RevenueBand = Literal["none", "under_10k", "10k_to_50k", "50k_to_2l", "over_2l", "undisclosed"]


class ProfileFields(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=160)
    sector: str = Field(min_length=2, max_length=120)
    products_services: str = Field(min_length=1, max_length=4000)
    stage: BusinessStage
    registration_info: str | None = Field(default=None, max_length=240)
    started_on: date | None = None
    team_size: int = Field(ge=0, le=100000)
    investment_band: MoneyBand
    funding_status: FundingStatus
    revenue_band: RevenueBand
    support_needs: str | None = Field(default=None, max_length=4000)
    public_opt_in: bool = False

    @field_validator("name", "sector", "products_services", mode="before")
    @classmethod
    def strip_required_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_stage(self) -> "ProfileFields":
        if self.stage in {"operating", "paused", "closed"} and self.started_on is None:
            raise ValueError("A started business needs a start date")
        return self


class CreateProfile(ProfileFields):
    enrollment_id: UUID


class UpdateProfile(ProfileFields):
    expected_version: int = Field(ge=1)


class OutcomeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reported_on: date
    business_started: bool
    business_active: bool
    jobs_created: int = Field(ge=0, le=100000)
    funding_band: MoneyBand
    revenue_band: RevenueBand
    challenges: str | None = Field(default=None, max_length=4000)
    support_requested: str | None = Field(default=None, max_length=4000)
    mentor_interventions: str | None = Field(default=None, max_length=4000)
    outcomes: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_activity(self) -> "OutcomeCreate":
        if self.business_active and not self.business_started:
            raise ValueError("An active business must have started")
        return self


class OutcomeView(OutcomeCreate):
    id: UUID
    created_at: datetime


class FollowUpView(BaseModel):
    id: UUID
    offset_days: int
    due_on: date
    status: Literal["pending", "completed"]
    outcome: OutcomeView | None


class RevisionView(BaseModel):
    id: UUID
    version: int
    snapshot: dict[str, object]
    created_at: datetime


class ProfileView(ProfileFields):
    id: UUID
    enrollment_id: UUID
    version: int
    created_at: datetime
    updated_at: datetime
    revisions: list[RevisionView]
    follow_ups: list[FollowUpView]


class EnrollmentEntry(BaseModel):
    enrollment_id: UUID
    program_id: UUID
    profile: ProfileView | None


class MyBusinesses(BaseModel):
    entries: list[EnrollmentEntry]


class PolicyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=0)
    day_offsets: list[int] = Field(min_length=1, max_length=12)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def strip_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_offsets(self) -> "PolicyUpdate":
        if self.day_offsets != sorted(set(self.day_offsets)) or any(
            day < 1 or day > 3650 for day in self.day_offsets
        ):
            raise ValueError("Follow-up days must be unique, ascending and within ten years")
        return self


class PolicyView(BaseModel):
    day_offsets: list[int]
    version: int


class StaffBusinessSummary(BaseModel):
    profile_id: UUID
    enrollment_id: UUID
    name: str
    stage: BusinessStage
    due_count: int
    completed_count: int


class StaffDashboard(BaseModel):
    policy: PolicyView
    profiles: list[StaffBusinessSummary]
