from datetime import UTC, date, datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ImpactTextInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("*", mode="before")
    @classmethod
    def safe_text(cls, value: object) -> object:
        if isinstance(value, str):
            if any(ord(char) < 32 and char not in "\n\r\t" for char in value):
                raise ValueError("Control characters are not permitted")
            try:
                value.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise ValueError("Valid UTF-8 text is required") from exc
        return value


class ReportFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    from_date: date
    through_date: date
    program_id: UUID | None = None
    cohort_id: UUID | None = None

    @model_validator(mode="after")
    def valid_window(self) -> Self:
        if self.from_date > self.through_date:
            raise ValueError("Start date must not follow end date")
        if self.through_date > datetime.now(UTC).date():
            raise ValueError("Report dates cannot be in the future")
        if (self.through_date - self.from_date).days > 365:
            raise ValueError("Report windows are limited to 366 inclusive days")
        return self


class ReportBreakdown(BaseModel):
    key: str
    label: str
    count: int = Field(ge=0)


class ReportMetric(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    key: str
    group: str
    label_en: str
    label_ta: str
    definition_en: str
    definition_ta: str
    source: str
    temporal_basis: str
    unit: str
    numerator: float | None = None
    denominator: float | None = None
    value: float | None = None
    caveat_en: str = ""
    caveat_ta: str = ""
    breakdown: list[ReportBreakdown] = Field(default_factory=list)


class ImpactDefinitionCreate(ImpactTextInput):
    title_en: str = Field(min_length=3, max_length=200)
    title_ta: str = Field(min_length=3, max_length=200)
    definition_en: str = Field(min_length=3, max_length=5000)
    definition_ta: str = Field(min_length=3, max_length=5000)
    reason: str = Field(min_length=3, max_length=500)


class ImpactDefinitionCommand(ImpactTextInput):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=500)


class ImpactDefinitionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    edition: int
    title_en: str
    title_ta: str
    definition_en: str
    definition_ta: str
    measures: list[str] = ["business_started", "business_active", "jobs_created"]
    state: Literal["draft", "published", "archived"]
    version: int
    created_at: datetime
    published_at: datetime | None


class ImpactDefinitionList(BaseModel):
    items: list[ImpactDefinitionView]
    next_cursor: UUID | None


class ImpactRecordCreate(ImpactTextInput):
    enrollment_id: UUID
    definition_id: UUID
    stage: Literal["baseline", "outcome"]
    observed_on: date
    business_started: bool
    business_active: bool
    jobs_created: int = Field(ge=0, le=100000)
    expected_revision: int = Field(ge=0)
    reason: str = Field(min_length=3, max_length=500)
    request_id: UUID

    @model_validator(mode="after")
    def valid_evidence(self) -> Self:
        if self.observed_on > datetime.now(UTC).date():
            raise ValueError("Observation date cannot be in the future")
        if self.business_active and not self.business_started:
            raise ValueError("An active business must have started")
        return self


class ImpactRecordView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    enrollment_id: UUID
    definition_id: UUID
    stage: Literal["baseline", "outcome"]
    observed_on: date
    business_started: bool
    business_active: bool
    jobs_created: int
    revision: int
    reason: str
    request_id: UUID
    created_at: datetime


class ImpactEnrollmentView(BaseModel):
    id: UUID
    program_id: UUID
    cohort_id: UUID
    name_en: str
    name_ta: str
    status: str


class ImpactMine(BaseModel):
    enrollments: list[ImpactEnrollmentView]
    definitions: list[ImpactDefinitionView]
    records: list[ImpactRecordView]
    enrollment_next_cursor: UUID | None
    definition_next_cursor: UUID | None
    record_next_cursor: UUID | None


class ReportChoice(BaseModel):
    id: UUID
    name_en: str
    name_ta: str
    program_id: UUID | None = None


class ReportOptions(BaseModel):
    programs: list[ReportChoice]
    cohorts: list[ReportChoice]
    program_next_cursor: UUID | None
    cohort_next_cursor: UUID | None


class ImpactAggregate(BaseModel):
    definition: ImpactDefinitionView
    eligible_enrollments: int
    baseline_reported: int
    outcome_reported: int
    matched_sample: int
    baseline_jobs: int
    outcome_jobs: int
    matched_baseline_jobs: int
    matched_outcome_jobs: int
    matched_jobs_change: int | None
    outcome_started: int
    outcome_active: int
    caveat_en: str
    caveat_ta: str


class ReportDashboard(BaseModel):
    filters: ReportFilters
    generated_at: datetime
    dictionary_version: str
    metrics: list[ReportMetric]
    impact: list[ImpactAggregate]
    eligible_impact_enrollments: int
    impact_reported_enrollments: int
    impact_coverage: float | None
    caveat_en: str
    caveat_ta: str


class ReportDefinitions(BaseModel):
    dictionary_version: str
    metrics: list[ReportMetric]
    impact_definitions: list[ImpactDefinitionView]
    next_cursor: UUID | None


class ReportSnapshotCreate(ReportFilters):
    request_id: UUID


class ReportSnapshotView(BaseModel):
    id: UUID
    created_at: datetime
    request_id: UUID
    dashboard: ReportDashboard


class ReportSnapshotSummary(BaseModel):
    id: UUID
    created_at: datetime
    request_id: UUID
    filters: ReportFilters
    dictionary_version: str
    generated_at: datetime


class ReportSnapshotList(BaseModel):
    items: list[ReportSnapshotSummary]
    next_cursor: UUID | None


class ReportExportCreate(ImpactTextInput):
    snapshot_id: UUID
    request_id: UUID
    reason: str = Field(min_length=3, max_length=500)


class ReportExportView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    snapshot_id: UUID
    request_id: UUID
    created_at: datetime
    expires_at: datetime
    status: Literal["completed"] = "completed"
    row_count: int
    byte_count: int


class ReportExportList(BaseModel):
    items: list[ReportExportView]
    next_cursor: UUID | None


class ReportExportAccess(BaseModel):
    token: str
    expires_at: datetime
