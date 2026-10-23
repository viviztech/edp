from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

FilePurpose = Literal[
    "application_document",
    "cms_asset",
    "assignment_submission",
    "lms_material",
    "helpdesk_attachment",
]
MediaType = Literal["application/pdf", "image/jpeg", "image/png", "image/webp", "text/plain"]
FileState = Literal[
    "pending",
    "uploading",
    "quarantined",
    "scanning",
    "clean",
    "infected",
    "rejected",
    "deleted",
]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class FilePolicyRules(Strict):
    name: str = Field(min_length=1, max_length=160)
    notice_en: str = Field(min_length=1, max_length=4000)
    notice_ta: str = Field(min_length=1, max_length=4000)
    allowed_mime_types: list[MediaType] = Field(min_length=1, max_length=5)
    max_file_bytes: int = Field(ge=1, le=104857600)
    max_files: int = Field(ge=1, le=100)
    retention_days: int = Field(ge=1, le=3650)
    rejected_retention_days: int = Field(ge=1, le=3650)
    allow_frozen_disposal: bool

    @field_validator("allowed_mime_types")
    @classmethod
    def normalized_mime_types(cls, value: list[MediaType]) -> list[MediaType]:
        if len(set(value)) != len(value):
            raise ValueError("Duplicate media type")
        return sorted(value)


class FilePolicyCreate(FilePolicyRules):
    client_request_id: UUID
    purpose: FilePurpose
    reason: str = Field(min_length=1, max_length=500)
    copy_from: UUID | None = None


class FilePolicyUpdate(FilePolicyRules):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=500)


class FilePolicyCommand(Strict):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=500)


class FilePolicyView(FilePolicyRules):
    id: UUID
    organization_id: UUID
    client_request_id: UUID
    purpose: FilePurpose
    edition: int
    version: int
    state: Literal["draft", "published", "retired"]
    copy_from: UUID | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class FilePolicyList(BaseModel):
    items: list[FilePolicyView]
    next_cursor: UUID | None


class FilePolicyQuery(Strict):
    purpose: FilePurpose | None = None
    cursor: UUID | None = None
    limit: int = Field(default=25, ge=1, le=100)


class FileCreate(Strict):
    client_request_id: UUID
    policy_id: UUID
    media_type: MediaType
    byte_size: int = Field(ge=1, le=104857600)
    sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")

    @field_validator("sha256")
    @classmethod
    def normalized_digest(cls, value: str) -> str:
        return value.lower()


class FileView(BaseModel):
    id: UUID
    organization_id: UUID
    owner_person_id: UUID
    purpose: FilePurpose
    resource_id: UUID
    policy_id: UUID
    client_request_id: UUID
    media_type: MediaType
    byte_size: int
    sha256: str
    state: FileState
    version: int
    verified_at: datetime | None
    scanned_at: datetime | None
    scan_attempts: int
    failure_code: str | None
    retention_until: datetime
    legal_hold: bool
    evidence_frozen: bool
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime
