from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ProgramState = Literal["draft", "active", "archived"]
CenterState = Literal["active", "inactive"]
CohortState = Literal["planned", "active", "completed", "cancelled"]
CycleState = Literal["draft", "open", "closed", "cancelled"]


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


class CatalogView(BaseModel):
    programs: list[ProgramView]
    centers: list[CenterView]
    cohorts: list[CohortView]
    cycles: list[CycleView]
