from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.files.schemas import FileView, MediaType


class HelpdeskFileIntent(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    client_request_id: UUID
    policy_id: UUID
    internal: bool
    media_type: MediaType
    byte_size: int = Field(ge=1, le=104857600)
    sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")

    @field_validator("sha256")
    @classmethod
    def normalize_digest(cls, value: str) -> str:
        return value.lower()


class HelpdeskFileRemove(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)


class HelpdeskFileQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cursor: UUID | None = None
    limit: int = Field(default=25, ge=1, le=100)


class HelpdeskFilePolicyView(BaseModel):
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


class HelpdeskFileEvidence(BaseModel):
    file_id: UUID
    file_version: int
    sha256: str
    byte_size: int
    frozen_at: datetime


class HelpdeskFileView(BaseModel):
    id: UUID
    message_id: UUID | None
    internal: bool
    state: Literal["staged", "removed", "posted"]
    version: int
    file: FileView
    policy: HelpdeskFilePolicyView
    usable: bool
    evidence: HelpdeskFileEvidence | None


class HelpdeskFileList(BaseModel):
    collection_enabled: bool
    max_upload_bytes: int
    policy: HelpdeskFilePolicyView | None
    items: list[HelpdeskFileView]
    next_cursor: UUID | None
