from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

FieldType = Literal["text", "textarea", "number", "date", "boolean"]


class FieldView(BaseModel):
    id: UUID
    key: str
    section: str
    label_en: str
    label_ta: str
    field_type: FieldType
    required: bool
    position: int


class FormView(BaseModel):
    id: UUID
    organization_id: UUID
    version: int
    title_en: str
    title_ta: str
    fields: list[FieldView]


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
    form: FormView
    state: Literal["draft"]
    version: int
    revision: int
    completion_percent: int
    answers: list[AnswerView]
    updated_at: datetime
