from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

@dataclass(frozen=True)
class UploadTarget:
    key: str
    url: str
    expires_seconds: int

class ObjectStorage(Protocol):
    def create_upload_target(self, organization_id: UUID, key: str, content_type: str, byte_size: int) -> UploadTarget: ...
    def public_url(self, key: str) -> str: ...

class StorageNotConfigured(RuntimeError):
    pass
