from uuid import uuid4

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.modules.identity.security import AuthError
from app.modules.lms.material_access import issue_access, resolve_local_material, verify_access


def settings(root: str, *, app_env: str = "test", signing_key: str | None = None) -> Settings:
    return Settings(
        app_env=app_env,
        database_url="postgresql+psycopg://localhost/unused",
        redis_url="redis://localhost/15",
        bff_key=SecretStr("b" * 32),
        lms_material_root=root,
        lms_material_signing_key=SecretStr(signing_key) if signing_key else None,
    )


def test_local_material_tokens_and_path_confinement(tmp_path):
    material = tmp_path / "course" / "guide.pdf"
    material.parent.mkdir()
    material.write_bytes(b"%PDF-1.4 synthetic")
    config = settings(str(tmp_path))

    ids = [uuid4() for _ in range(4)]
    token, expires_at = issue_access(config, *ids, "learner")
    claims = verify_access(config, token)
    assert (
        claims.organization_id,
        claims.actor_id,
        claims.course_id,
        claims.material_id,
    ) == tuple(ids)
    assert claims.expires_at == expires_at.replace(microsecond=0)

    resolved = resolve_local_material(config, "course/guide.pdf")
    assert resolved.path == material
    assert resolved.media_type == "application/pdf"

    with pytest.raises(AuthError) as traversal:
        resolve_local_material(config, "../outside.pdf")
    assert traversal.value.code == "material_object_invalid"


def test_production_requires_a_dedicated_material_signing_key(tmp_path):
    config = settings(str(tmp_path), app_env="production")
    with pytest.raises(AuthError) as missing:
        issue_access(config, uuid4(), uuid4(), uuid4(), uuid4(), "trainer")
    assert missing.value.code == "material_provider_not_configured"

    configured = settings(str(tmp_path), app_env="production", signing_key="s" * 32)
    with pytest.raises(AuthError):
        issue_access(configured, uuid4(), uuid4(), uuid4(), uuid4(), "trainer")
    with pytest.raises(AuthError):
        resolve_local_material(configured, "guide.pdf")
    # Shared storage gateways do not require a legacy local path. The domain
    # validates their typed clean pin before issuing this actor-bound token.
    token, _ = issue_access(
        configured, uuid4(), uuid4(), uuid4(), uuid4(), "trainer", require_local_root=False
    )
    assert verify_access(configured, token).mode == "trainer"
