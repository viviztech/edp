import hashlib
import hmac
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from app.modules.identity.security import AuthError
from app.modules.meta import service
from app.modules.meta.models import MetaIntegration
from app.modules.meta.schemas import IntegrationCreate, MappingCreate
from app.workers.meta_leads import mapped_fields


def integration(secret: str) -> MetaIntegration:
    crypto = Fernet(Fernet.generate_key())
    return MetaIntegration(
        id=uuid4(),
        organization_id=uuid4(),
        name="Lead page",
        page_id="page-1",
        access_token_ciphertext=crypto.encrypt(b"access-token").decode(),
        app_secret_ciphertext=crypto.encrypt(secret.encode()).decode(),
        verify_token_hash="a" * 64,
        status="active",
        version=1,
    )


def test_webhook_signature_requires_exact_sha256_hmac(monkeypatch) -> None:
    secret = "application-secret"
    crypto = Fernet(Fernet.generate_key())
    item = integration(secret)
    item.app_secret_ciphertext = crypto.encrypt(secret.encode()).decode()
    monkeypatch.setattr(service, "cipher", lambda: crypto)
    body = b'{"entry":[]}'

    signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    assert service.valid_signature(item, body, signature)
    assert not service.valid_signature(item, body + b" ", signature)
    assert not service.valid_signature(item, body, "sha1=invalid")


def test_mapping_contract_requires_unique_name_target() -> None:
    valid = MappingCreate(
        form_id="form-1",
        name="Primary form",
        field_mapping={"full_name": "name", "email": "email"},
    )
    assert valid.field_mapping["full_name"] == "name"

    with pytest.raises(ValidationError):
        MappingCreate(
            form_id="form-1",
            name="Invalid",
            field_mapping={"email": "email"},
        )
    with pytest.raises(ValidationError):
        MappingCreate(
            form_id="form-1",
            name="Duplicate targets",
            field_mapping={"full_name": "name", "first_name": "name"},
        )
    with pytest.raises(ValidationError):
        MappingCreate(
            form_id="form-1",
            name="Invalid provider field",
            field_mapping={"x" * 81: "name"},
        )


def test_provider_fields_are_reduced_to_configured_targets() -> None:
    payload = {
        "field_data": [
            {"name": "full_name", "values": ["Ada Lovelace"]},
            {"name": "email", "values": ["ada@example.test"]},
            {"name": "ignored", "values": ["sensitive"]},
        ]
    }

    result = mapped_fields(payload, {"full_name": "name", "email": "email"})

    assert result == {"name": "Ada Lovelace", "email": "ada@example.test"}


def test_integration_creation_encrypts_provider_secrets(monkeypatch) -> None:
    crypto = Fernet(Fernet.generate_key())
    db = MagicMock()
    actor = SimpleNamespace(id=uuid4())
    marker = object()
    monkeypatch.setattr(service, "cipher", lambda: crypto)
    monkeypatch.setattr(service, "require_permission", MagicMock())
    monkeypatch.setattr(service, "integration_view", lambda _: marker)
    data = IntegrationCreate(
        name="Lead page",
        page_id="page-1",
        access_token="access-token-that-is-long-enough",
        app_secret="application-secret-value",
        verify_token="verification-token-value-123",
    )

    result = service.create_integration(db, uuid4(), actor, data, "request-id")

    stored = db.add.call_args_list[0].args[0]
    assert isinstance(stored, MetaIntegration)
    assert "access-token-that-is-long-enough" not in stored.access_token_ciphertext
    assert "application-secret-value" not in stored.app_secret_ciphertext
    assert (
        crypto.decrypt(stored.access_token_ciphertext.encode())
        == b"access-token-that-is-long-enough"
    )
    assert stored.verify_token_hash != "verification-token-value-123"
    assert result is marker


def test_mapping_creation_rejects_integration_outside_scope(monkeypatch) -> None:
    db = MagicMock()
    db.scalar.return_value = None
    monkeypatch.setattr(service, "require_permission", MagicMock())
    data = MappingCreate(
        form_id="form-1",
        name="Lead form",
        field_mapping={"full_name": "name"},
    )

    with pytest.raises(AuthError) as error:
        service.create_mapping(
            db,
            uuid4(),
            uuid4(),
            SimpleNamespace(id=uuid4()),
            data,
            "request-id",
        )

    assert getattr(error.value, "code", None) == "not_found"
    assert getattr(error.value, "status", None) == 404
    db.add.assert_not_called()
