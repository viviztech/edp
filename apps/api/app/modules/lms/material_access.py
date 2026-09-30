import base64
import hmac
import json
import mimetypes
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Literal
from uuid import UUID

from app.core.config import Settings
from app.modules.identity.security import AuthError

AccessMode = Literal["learner", "trainer"]


@dataclass(frozen=True)
class MaterialAccessClaims:
    organization_id: UUID
    actor_id: UUID
    course_id: UUID
    material_id: UUID
    mode: AccessMode
    expires_at: datetime


@dataclass(frozen=True)
class LocalMaterial:
    path: Path
    media_type: str
    filename: str


def _secret(settings: Settings) -> bytes:
    configured = settings.lms_material_signing_key
    if not configured and settings.app_env in {"local", "test"}:
        configured = settings.bff_key
    if not configured:
        raise AuthError("material_provider_not_configured", 503)
    return configured.get_secret_value().encode()


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def issue_access(
    settings: Settings,
    organization_id: UUID,
    actor_id: UUID,
    course_id: UUID,
    material_id: UUID,
    mode: AccessMode,
) -> tuple[str, datetime]:
    if not settings.lms_material_root:
        raise AuthError("material_provider_not_configured", 503)
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.lms_material_access_seconds)
    payload = json.dumps(
        {
            "o": str(organization_id),
            "a": str(actor_id),
            "c": str(course_id),
            "m": str(material_id),
            "r": mode,
            "e": int(expires_at.timestamp()),
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    encoded = _encode(payload)
    signature = _encode(hmac.new(_secret(settings), encoded.encode(), sha256).digest())
    return encoded + "." + signature, expires_at


def verify_access(settings: Settings, token: str) -> MaterialAccessClaims:
    if len(token) > 1024 or token.count(".") != 1:
        raise AuthError("material_access_invalid", 403)
    encoded, supplied = token.split(".", 1)
    expected = _encode(hmac.new(_secret(settings), encoded.encode(), sha256).digest())
    if not hmac.compare_digest(supplied, expected):
        raise AuthError("material_access_invalid", 403)
    try:
        payload = json.loads(_decode(encoded))
        expires_at = datetime.fromtimestamp(int(payload["e"]), UTC)
        claims = MaterialAccessClaims(
            organization_id=UUID(payload["o"]),
            actor_id=UUID(payload["a"]),
            course_id=UUID(payload["c"]),
            material_id=UUID(payload["m"]),
            mode=payload["r"],
            expires_at=expires_at,
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise AuthError("material_access_invalid", 403) from exc
    if claims.mode not in {"learner", "trainer"}:
        raise AuthError("material_access_invalid", 403)
    if claims.expires_at <= datetime.now(UTC):
        raise AuthError("material_access_expired", 403)
    return claims


def resolve_local_material(settings: Settings, provider_key: str) -> LocalMaterial:
    if not settings.lms_material_root:
        raise AuthError("material_provider_not_configured", 503)
    root = Path(settings.lms_material_root).resolve()
    key = Path(provider_key)
    if key.is_absolute() or ".." in key.parts:
        raise AuthError("material_object_invalid", 409)
    target = (root / key).resolve()
    if target == root or root not in target.parents:
        raise AuthError("material_object_invalid", 409)
    if not target.is_file():
        raise AuthError("material_object_unavailable", 404)
    media_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    return LocalMaterial(path=target, media_type=media_type, filename=target.name)
