from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal, Self
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    field_validator,
    model_validator,
)

KnowledgeKind = Literal["scheme", "funding", "opportunity"]
KnowledgeLocale = Literal["en", "ta"]
KnowledgeState = Literal["draft", "published", "archived"]
KnowledgeAvailability = Literal["upcoming", "open", "closed"]
FundingStatus = Literal[
    "interested",
    "eligibility_check",
    "document_preparation",
    "applied",
    "under_review",
    "approved",
    "rejected",
    "disbursed",
]


class KnowledgeDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    kind: KnowledgeKind
    locale: KnowledgeLocale
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    title: str = Field(min_length=1, max_length=200)
    provider: str = Field(min_length=1, max_length=200)
    type: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=10000)
    eligibility: str = Field(min_length=1, max_length=5000)
    benefits: str = Field(default="", max_length=5000)
    sector: str = Field(min_length=1, max_length=120)
    geography: str = Field(min_length=1, max_length=120)
    tags: list[str] = Field(default_factory=list, max_length=20)
    application_process: str = Field(min_length=1, max_length=5000)
    documents: list[str] = Field(default_factory=list, max_length=30)
    official_url: str = Field(min_length=1, max_length=2000)
    opens_on: date | None = None
    closes_on: date | None = None
    last_verified_at: date
    visibility: Literal["public", "participants"] = "public"
    contact: str = Field(default="", max_length=1000)
    funding_amount_min: Decimal | None = Field(default=None, ge=0, max_digits=16, decimal_places=2)
    funding_amount_max: Decimal | None = Field(default=None, ge=0, max_digits=16, decimal_places=2)
    currency: Literal["INR"] = "INR"

    @field_validator("official_url")
    @classmethod
    def official_http(cls, value: str) -> str:
        TypeAdapter(AnyHttpUrl).validate_python(value)
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            raise ValueError("An official HTTP(S) URL without credentials is required")
        return value

    @field_validator("tags", "documents")
    @classmethod
    def bounded_labels(cls, values: list[str]) -> list[str]:
        if any(not value.strip() or len(value.strip()) > 200 for value in values):
            raise ValueError("Each label must contain 1 to 200 characters")
        return list(dict.fromkeys(value.strip() for value in values))

    @model_validator(mode="after")
    def coherent_dates_and_amounts(self) -> Self:
        if self.opens_on and self.closes_on and self.opens_on > self.closes_on:
            raise ValueError("Closing date must not precede opening date")
        if self.last_verified_at > datetime.now(UTC).date():
            raise ValueError("Verification date cannot be in the future")
        amounts = (self.funding_amount_min, self.funding_amount_max)
        if any(value is not None for value in amounts):
            if self.kind != "funding":
                raise ValueError("Official funding amounts are only valid for funding entries")
            if all(value is not None for value in amounts):
                assert self.funding_amount_min is not None and self.funding_amount_max is not None
                if self.funding_amount_min > self.funding_amount_max:
                    raise ValueError("Funding maximum must not be less than minimum")
        return self


class KnowledgeCreate(KnowledgeDraft):
    pass


class KnowledgeEdit(KnowledgeDraft):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=500)


class KnowledgeCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=500)


class KnowledgeView(KnowledgeDraft):
    id: UUID
    state: KnowledgeState
    version: int
    published_at: datetime | None
    updated_at: datetime
    availability: KnowledgeAvailability


class KnowledgeList(BaseModel):
    items: list[KnowledgeView]
    next_cursor: UUID | None


class KnowledgeFilters(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    locale: KnowledgeLocale = "en"
    kind: KnowledgeKind | None = None
    q: str | None = Field(default=None, max_length=120)
    sector: str | None = Field(default=None, max_length=120)
    geography: str | None = Field(default=None, max_length=120)
    tag: str | None = Field(default=None, max_length=200)
    availability: Literal["active", "all", "upcoming", "open", "closed"] = "active"
    state: KnowledgeState | None = None
    cursor: UUID | None = None
    limit: int = Field(default=25, ge=1, le=100)


class KnowledgeRevisionView(BaseModel):
    id: UUID
    version: int
    action: str
    reason: str
    snapshot: KnowledgeView
    created_at: datetime


class KnowledgeHistory(BaseModel):
    items: list[KnowledgeRevisionView]
    next_cursor: UUID | None


class KnowledgeSavedView(BaseModel):
    item_id: UUID
    item: KnowledgeView | None
    created_at: datetime


class KnowledgeInterestView(BaseModel):
    id: UUID
    item_id: UUID
    item_title: str
    locale: KnowledgeLocale
    created_at: datetime


class FundingHistoryView(BaseModel):
    id: UUID
    status: FundingStatus
    reason: str
    created_at: datetime


class FundingCaseView(BaseModel):
    id: UUID
    item_id: UUID
    item_title: str
    locale: KnowledgeLocale
    participant_id: UUID
    status: FundingStatus
    version: int
    created_at: datetime
    source: KnowledgeView
    history: list[FundingHistoryView]


class FundingCaseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_id: UUID


class FundingStatusChange(KnowledgeCommand):
    status: FundingStatus


class FundingCaseList(BaseModel):
    items: list[FundingCaseView]
    next_cursor: UUID | None


class KnowledgeMine(BaseModel):
    saved_items: list[KnowledgeSavedView]
    interests: list[KnowledgeInterestView]
    funding_cases: list[FundingCaseView]
    next_saved_cursor: UUID | None
    next_interest_cursor: UUID | None
    next_case_cursor: UUID | None
