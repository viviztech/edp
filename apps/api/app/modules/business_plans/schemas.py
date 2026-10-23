from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

SectionCode = Literal[
    "executive_summary",
    "problem",
    "solution",
    "product_service",
    "customer_segments",
    "market",
    "competition",
    "value_proposition",
    "business_model",
    "pricing",
    "sales_marketing",
    "operations",
    "team",
    "investment",
    "revenue_assumptions",
    "expense_assumptions",
    "break_even_inputs",
    "funding_requirement",
    "risks",
    "milestones",
]


class SaveSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    section_code: SectionCode
    body: str = Field(max_length=10000)


class SubmitPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)


class ReviewPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    decision: Literal["changes_requested", "approved"]
    reason: str = Field(min_length=3, max_length=500)
    comments: dict[SectionCode, str] = Field(default_factory=dict, max_length=20)

    @model_validator(mode="after")
    def validate_comments(self) -> "ReviewPlan":
        self.reason = self.reason.strip()
        if len(self.reason) < 3:
            raise ValueError("Review reason must contain at least 3 meaningful characters")
        if any(not text.strip() or len(text) > 2000 for text in self.comments.values()):
            raise ValueError("Comments must contain 1 to 2000 characters")
        return self


class ReviewView(BaseModel):
    id: UUID
    decision: Literal["changes_requested", "approved"]
    reason: str
    comments: dict[SectionCode, str]
    created_at: datetime


class SubmissionView(BaseModel):
    id: UUID
    enrollment_id: UUID
    plan_version: int
    number: int
    snapshot: dict[SectionCode, str]
    created_at: datetime
    review: ReviewView | None


class RevisionView(BaseModel):
    id: UUID
    version: int
    section_code: SectionCode
    body: str
    created_at: datetime


class PlanView(BaseModel):
    id: UUID
    enrollment_id: UUID
    status: Literal["draft", "submitted", "changes_requested", "approved"]
    version: int
    completed_sections: int
    total_sections: int
    sections: dict[SectionCode, str]
    revisions: list[RevisionView]
    submissions: list[SubmissionView]


class PlanEntry(BaseModel):
    enrollment_id: UUID
    program_id: UUID
    plan: PlanView | None


class MyPlans(BaseModel):
    entries: list[PlanEntry]


class MentorPlans(BaseModel):
    submissions: list[SubmissionView]
