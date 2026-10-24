from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.files.schemas import FileView, MediaType


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LearningFileIntent(Strict):
    client_request_id: UUID
    media_type: MediaType
    byte_size: int = Field(ge=1, le=104857600)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class AssignmentFileIntent(LearningFileIntent):
    expected_revision: int = Field(ge=1, le=10)


class AssignmentFileRuleCommand(Strict):
    policy_id: UUID
    minimum_files: int = Field(ge=0, le=100)
    maximum_files: int = Field(ge=1, le=100)
    expected_version: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def counts(self) -> Self:
        if self.minimum_files > self.maximum_files:
            raise ValueError("minimum_files exceeds maximum_files")
        return self


class AssignmentFileRuleView(BaseModel):
    policy_id: UUID
    minimum_files: int
    maximum_files: int
    version: int
    allowed_mime_types: list[MediaType]
    max_file_bytes: int
    notice_en: str
    notice_ta: str


class LearningFileEvidence(BaseModel):
    file_id: UUID
    file_version: int
    sha256: str
    byte_size: int
    frozen_at: datetime


class AssignmentFileView(BaseModel):
    id: UUID
    target_revision: int
    state: Literal["active", "removed", "submitted"]
    version: int
    file: FileView
    submission_id: UUID | None
    evidence: LearningFileEvidence | None
    usable: bool


class AssignmentFileList(BaseModel):
    collection_enabled: bool
    max_upload_bytes: int
    next_revision: int
    rule: AssignmentFileRuleView | None
    items: list[AssignmentFileView]


class LearningFileRemove(Strict):
    expected_version: int = Field(ge=1)


class MaterialFileIntent(LearningFileIntent):
    policy_id: UUID
    course_id: UUID
    lesson_id: UUID
    position: int = Field(ge=1)
    label_en: str = Field(min_length=1, max_length=200)
    label_ta: str = Field(min_length=1, max_length=200)

    @field_validator("label_en", "label_ta", mode="before")
    @classmethod
    def strip_labels(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class MaterialFileView(BaseModel):
    material_id: UUID
    state: Literal["active", "removed"]
    version: int
    file: FileView
    evidence: LearningFileEvidence | None
    usable: bool


class MaterialFileList(BaseModel):
    collection_enabled: bool
    max_upload_bytes: int
    items: list[MaterialFileView]
    next_cursor: UUID | None = None
