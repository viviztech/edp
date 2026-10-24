from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.files.schemas import FileView, MediaType


class DocumentRequirementInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    key: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    label_en: str = Field(min_length=1, max_length=200)
    label_ta: str = Field(min_length=1, max_length=200)
    instructions_en: str = Field(min_length=1, max_length=2000)
    instructions_ta: str = Field(min_length=1, max_length=2000)
    file_policy_id: UUID
    min_files: int = Field(ge=0, le=100)
    max_files: int = Field(ge=1, le=100)

    @model_validator(mode="after")
    def valid_counts(self) -> "DocumentRequirementInput":
        if self.min_files > self.max_files:
            raise ValueError("Minimum exceeds maximum")
        return self


class DocumentFilePolicyView(BaseModel):
    id: UUID
    edition: int
    name: str
    allowed_mime_types: list[MediaType]
    max_file_bytes: int
    max_upload_bytes: int
    max_files: int
    retention_days: int
    rejected_retention_days: int
    notice_en: str
    notice_ta: str
    allow_frozen_disposal: bool


class DocumentRequirementView(DocumentRequirementInput):
    id: UUID
    position: int
    file_policy: DocumentFilePolicyView


class DocumentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    expected_version: int = Field(ge=1)
    client_request_id: UUID
    requirement_id: UUID
    media_type: MediaType
    byte_size: int = Field(ge=1, le=104857600)
    sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    replaces_document_id: UUID | None = None

    @field_validator("sha256")
    @classmethod
    def normalized_digest(cls, value: str) -> str:
        return value.lower()


class DocumentRemove(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)


class DocumentQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cursor: UUID | None = None
    limit: int = Field(default=25, ge=1, le=100)


class DocumentEvidenceView(BaseModel):
    file_id: UUID
    file_version: int
    sha256: str
    byte_size: int
    frozen_at: datetime


class ApplicationDocumentView(BaseModel):
    id: UUID
    requirement_id: UUID
    file: FileView
    usable: bool
    removed_at: datetime | None
    replaced_by_id: UUID | None
    submitted_evidence: DocumentEvidenceView | None


class ApplicationDocumentResult(BaseModel):
    application_version: int
    document: ApplicationDocumentView


class ApplicationDocumentList(BaseModel):
    application_id: UUID
    application_version: int
    collection_enabled: bool
    max_upload_bytes: int
    document_requirements: list[DocumentRequirementView]
    items: list[ApplicationDocumentView]
    next_cursor: UUID | None
