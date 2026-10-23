from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

FieldType = Literal["text", "textarea", "number", "date", "boolean"]
DefinitionState = Literal["draft", "published", "retired"]
AcknowledgementKind = Literal["declaration", "consent"]
ApplicationState = Literal[
    "draft",
    "submitted",
    "under_review",
    "shortlisted",
    "interview_scheduled",
    "selected",
    "waitlisted",
    "rejected",
    "enrolled",
]


class ApplicationHistoryQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cursor: UUID | None = None
    limit: int = Field(default=25, ge=1, le=100)


class ApplicationHistoryItem(BaseModel):
    id: UUID
    organization_id: UUID
    organization_name: str
    cycle_id: UUID | None
    cycle_code: str | None
    cycle_name_en: str | None
    cycle_name_ta: str | None
    state: ApplicationState
    version: int
    application_number: str | None
    submitted_at: datetime | None
    updated_at: datetime


class ApplicationHistoryList(BaseModel):
    items: list[ApplicationHistoryItem]
    next_cursor: UUID | None


class FieldView(BaseModel):
    id: UUID
    key: str
    section: str
    label_en: str
    label_ta: str
    field_type: FieldType
    required: bool
    position: int


class AcknowledgementView(BaseModel):
    id: UUID
    key: str
    kind: AcknowledgementKind
    label_en: str
    label_ta: str
    required: bool
    position: int


class FormView(BaseModel):
    id: UUID
    organization_id: UUID
    version: int
    title_en: str
    title_ta: str
    fields: list[FieldView]
    acknowledgements: list[AcknowledgementView]


class DefinitionFieldInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    section: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    label_en: str = Field(min_length=1, max_length=200)
    label_ta: str = Field(min_length=1, max_length=200)
    field_type: FieldType
    required: bool = False

    @field_validator("key", "section", "label_en", "label_ta")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class AcknowledgementInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    kind: AcknowledgementKind
    label_en: str = Field(min_length=1, max_length=1000)
    label_ta: str = Field(min_length=1, max_length=1000)
    required: bool = True

    @field_validator("key", "label_en", "label_ta")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class DefinitionContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title_en: str = Field(min_length=1, max_length=160)
    title_ta: str = Field(min_length=1, max_length=160)
    fields: list[DefinitionFieldInput] = Field(min_length=1, max_length=100)
    acknowledgements: list[AcknowledgementInput] = Field(default_factory=list, max_length=20)

    @field_validator("title_en", "title_ta")
    @classmethod
    def strip_title(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def unique_policy_keys(self) -> "DefinitionContent":
        field_keys = [item.key for item in self.fields]
        acknowledgement_keys = [item.key for item in self.acknowledgements]
        if len(field_keys) != len(set(field_keys)):
            raise ValueError("Duplicate field key")
        if len(acknowledgement_keys) != len(set(acknowledgement_keys)):
            raise ValueError("Duplicate acknowledgement key")
        return self


class DefinitionCreate(DefinitionContent):
    pass


class DefinitionUpdate(DefinitionContent):
    expected_revision: int = Field(ge=1)


class DefinitionCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)


class DefinitionView(FormView):
    state: DefinitionState
    revision: int
    published_at: datetime | None
    created_at: datetime


class DefinitionList(BaseModel):
    items: list[DefinitionView]


class AnswerInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field_id: UUID
    value: str = Field(max_length=5000)


class DraftSave(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    answers: list[AnswerInput] = Field(max_length=100)

    @field_validator("answers")
    @classmethod
    def unique_fields(cls, value: list[AnswerInput]) -> list[AnswerInput]:
        if len({item.field_id for item in value}) != len(value):
            raise ValueError("Duplicate field")
        return value


class AnswerView(BaseModel):
    field_id: UUID
    value: str


class DraftView(BaseModel):
    id: UUID
    cycle_id: UUID | None
    form: FormView
    state: Literal["draft"]
    version: int
    revision: int
    completion_percent: int
    answers: list[AnswerView]
    updated_at: datetime


class CycleOpportunityView(BaseModel):
    id: UUID
    code: str
    name_en: str
    name_ta: str
    form_id: UUID
    opens_at: datetime
    closes_at: datetime


class CycleOpportunityList(BaseModel):
    items: list[CycleOpportunityView]


class SubmitCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    accepted_acknowledgement_ids: list[UUID] = Field(min_length=1, max_length=20)

    @field_validator("accepted_acknowledgement_ids")
    @classmethod
    def unique_acknowledgements(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("Duplicate acknowledgement")
        return value


class AcceptedAcknowledgementView(BaseModel):
    definition_id: UUID
    accepted_at: datetime


class StatusHistoryView(BaseModel):
    from_state: str | None
    to_state: str
    application_version: int
    reason_code: str
    created_at: datetime


class SubmittedView(BaseModel):
    id: UUID
    cycle_id: UUID
    form: FormView
    state: Literal[
        "submitted",
        "under_review",
        "shortlisted",
        "interview_scheduled",
        "selected",
        "waitlisted",
        "rejected",
        "enrolled",
    ]
    version: int
    revision: int
    completion_percent: Literal[100]
    application_number: str
    submitted_at: datetime
    answers: list[AnswerView]
    accepted_acknowledgements: list[AcceptedAcknowledgementView]
    status_history: list[StatusHistoryView]
    updated_at: datetime
