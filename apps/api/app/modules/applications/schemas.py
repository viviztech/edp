from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

FieldType = Literal["text", "textarea", "number", "date", "boolean"]
DefinitionState = Literal["draft", "published", "retired"]


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


class DefinitionContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title_en: str = Field(min_length=1, max_length=160)
    title_ta: str = Field(min_length=1, max_length=160)
    fields: list[DefinitionFieldInput] = Field(min_length=1, max_length=100)

    @field_validator("title_en", "title_ta")
    @classmethod
    def strip_title(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def unique_fields(self) -> "DefinitionContent":
        keys = [item.key for item in self.fields]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate field key")
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
    form: FormView
    state: Literal["draft"]
    version: int
    revision: int
    completion_percent: int
    answers: list[AnswerView]
    updated_at: datetime
