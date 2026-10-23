import os

import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.fixture(autouse=True)
def isolated_file_settings(monkeypatch):
    for key in os.environ:
        if key.startswith(("FILES_", "CLAMAV_")):
            monkeypatch.delenv(key)


def settings(**overrides):
    return Settings(
        _env_file=None,
        database_url="postgresql+psycopg://unused@localhost/edp_test",
        redis_url="redis://localhost/15",
        **overrides,
    )


def production(tmp_path):
    return {
        "app_env": "production",
        "files_enabled": True,
        "files_storage_backend": "s3",
        "files_temp_root": str(tmp_path.resolve()),
        "files_s3_bucket": "synthetic-files",
        "files_s3_region": "us-east-1",
        "files_s3_encryption": "AES256",
        "files_s3_access_key_id": "synthetic-access-id",
        "files_s3_secret_access_key": "synthetic-secret-only",
        "clamav_host": "clamav.internal",
        "clamav_max_signature_age_seconds": 86400,
    }


def test_files_default_disabled_without_provider_or_policy_defaults():
    value = settings(app_env="production")
    assert not value.files_enabled
    assert value.files_storage_backend is None
    assert value.files_local_root is None
    assert value.files_s3_bucket is None
    assert value.clamav_host is None
    assert value.clamav_max_signature_age_seconds is None


@pytest.mark.parametrize(
    "missing",
    [
        "files_storage_backend",
        "files_temp_root",
        "files_s3_bucket",
        "files_s3_region",
        "files_s3_encryption",
        "files_s3_secret_access_key",
        "clamav_host",
        "clamav_max_signature_age_seconds",
    ],
)
def test_production_collection_requires_explicit_runtime_configuration(tmp_path, missing):
    values = production(tmp_path)
    values[missing] = None
    with pytest.raises(ValidationError):
        settings(**values)


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_local_storage_cannot_enable_real_collection(tmp_path, environment):
    values = production(tmp_path) | {"app_env": environment, "files_storage_backend": "local"}
    with pytest.raises(ValidationError):
        settings(**values)


@pytest.mark.parametrize(
    "endpoint",
    [
        "file:///tmp/files",
        "https://name:credential@example.invalid",
        "https://example.invalid/?credential=anything",
        "https://example.invalid/#fragment",
        "https://example.invalid/another/path",
    ],
)
def test_storage_endpoint_rejects_nonservice_or_embedded_credential_urls(endpoint):
    with pytest.raises(ValidationError):
        settings(files_s3_endpoint_url=endpoint)


def test_production_requires_tls_and_unambiguous_credentials(tmp_path):
    values = production(tmp_path)
    with pytest.raises(ValidationError):
        settings(**(values | {"files_s3_endpoint_url": "http://object-store.internal:9000"}))
    with pytest.raises(ValidationError):
        settings(**(values | {"files_s3_use_iam_role": True}))
    with pytest.raises(ValidationError):
        settings(**(values | {"files_s3_encryption": "aws:kms"}))


def test_explicit_private_runtime_configuration_does_not_connect_to_providers(tmp_path):
    value = settings(**production(tmp_path))
    assert value.files_enabled and value.files_storage_backend == "s3"
    assert "synthetic-secret-only" not in repr(value)
    iam = production(tmp_path) | {
        "files_s3_access_key_id": None,
        "files_s3_secret_access_key": None,
        "files_s3_use_iam_role": True,
    }
    assert settings(**iam).files_s3_use_iam_role
