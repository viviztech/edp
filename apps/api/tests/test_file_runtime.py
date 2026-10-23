import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.core.config import Settings
from app.modules.files import runtime
from app.modules.files.storage import LocalPrivateStorage, S3PrivateStorage
from app.modules.identity.security import AuthError


@pytest.fixture(autouse=True)
def isolated_file_settings(monkeypatch):
    for key in list(os.environ):
        if key.startswith(("FILES_", "CLAMAV_")):
            monkeypatch.delenv(key)


def settings(**overrides):
    return Settings(
        _env_file=None,
        database_url="postgresql+psycopg://unused@localhost/edp_test",
        redis_url="redis://localhost/15",
        **overrides,
    )


def configured(tmp_path):
    root = tmp_path / "private-temp"
    root.mkdir(mode=0o700)
    return {
        "app_env": "test",
        "files_enabled": True,
        "files_storage_backend": "local",
        "files_local_root": str(tmp_path / "objects"),
        "files_temp_root": str(root),
        "clamav_host": "localhost",
        "clamav_max_signature_age_seconds": 86400,
    }


def test_disabled_factories_do_not_construct_adapters(monkeypatch):
    sdk = MagicMock(side_effect=AssertionError("provider construction"))
    monkeypatch.setattr(runtime.boto3, "Session", sdk)
    for factory in (runtime.get_private_storage, runtime.get_file_scanner):
        with pytest.raises(AuthError) as error:
            factory(settings())
        assert error.value.code == "file_collection_disabled"
    sdk.assert_not_called()


def test_local_factories_require_explicit_private_roots_and_scanner(tmp_path):
    values = configured(tmp_path)
    storage = runtime.get_private_storage(settings(**values))
    assert isinstance(storage, LocalPrivateStorage)
    assert storage.root == tmp_path / "objects"
    assert not storage.root.exists()  # No request-time write or provider probe.
    scanner = runtime.get_file_scanner(settings(**values))
    assert scanner.host == "localhost"
    assert scanner.max_signature_age_seconds == 86400
    for override in (
        {"files_temp_root": None},
        {"files_temp_root": "relative"},
        {"files_temp_root": str(tmp_path / "absent")},
        {"files_local_root": "relative"},
        {"files_storage_backend": None},
    ):
        with pytest.raises(AuthError) as error:
            runtime.get_private_storage(settings(**(values | override)))
        assert error.value.code == "file_runtime_unavailable"
    for override in ({"clamav_host": None}, {"files_scan_lease_seconds": 30}):
        with pytest.raises(AuthError):
            runtime.get_file_scanner(settings(**(values | override)))


@pytest.mark.skipif(os.name == "nt", reason="POSIX directory mode and symlink checks")
def test_temp_root_rejects_shared_permissions_and_symlinks(tmp_path):
    values = configured(tmp_path)
    root = Path(values["files_temp_root"])
    root.chmod(0o755)
    with pytest.raises(AuthError):
        runtime.private_temp_root(settings(**values))
    root.chmod(0o700)
    link = tmp_path / "linked-temp"
    link.symlink_to(root, target_is_directory=True)
    with pytest.raises(AuthError):
        runtime.private_temp_root(settings(**(values | {"files_temp_root": str(link)})))


def test_s3_factory_uses_only_explicit_server_credentials(tmp_path, monkeypatch):
    values = configured(tmp_path) | {
        "files_storage_backend": "s3",
        "files_s3_bucket": "synthetic-files",
        "files_s3_region": "us-east-1",
        "files_s3_encryption": "aws:kms",
        "files_s3_kms_key_id": "synthetic-key-reference",
        "files_s3_access_key_id": "synthetic-access-id",
        "files_s3_secret_access_key": "synthetic-secret-only",
        "files_s3_session_token": "synthetic-session-only",
    }
    sdk = MagicMock()
    constructor = MagicMock(return_value=sdk)
    monkeypatch.setattr(runtime.boto3, "Session", constructor)
    storage = runtime.get_private_storage(settings(**values))
    assert isinstance(storage, S3PrivateStorage)
    assert storage.encryption == "aws:kms"
    constructor.assert_called_once_with(
        aws_access_key_id="synthetic-access-id",
        aws_secret_access_key="synthetic-secret-only",
        aws_session_token="synthetic-session-only",
    )
    sdk.client.assert_called_once()
    sdk.client.return_value.get_bucket_versioning.assert_not_called()
    sdk.client.return_value.put_object.assert_not_called()
    constructor.reset_mock()
    with pytest.raises(AuthError):
        runtime.get_private_storage(settings(**(values | {"files_s3_secret_access_key": None})))
    constructor.assert_not_called()


def test_workload_identity_factory_excludes_ambient_profiles(tmp_path, monkeypatch):
    values = configured(tmp_path) | {
        "files_storage_backend": "s3",
        "files_s3_bucket": "synthetic-files",
        "files_s3_region": "us-east-1",
        "files_s3_encryption": "AES256",
        "files_s3_use_iam_role": True,
    }
    chain = MagicMock()
    names = ["env", "shared-credentials-file", "iam-role", "container-role"]
    chain.providers = [type("Provider", (), {"METHOD": name})() for name in names]
    core = MagicMock()
    core.get_component.return_value = chain
    monkeypatch.setattr(runtime, "BotocoreSession", MagicMock(return_value=core))
    constructor = MagicMock()
    monkeypatch.setattr(runtime.boto3, "Session", constructor)
    runtime.get_private_storage(settings(**values))
    assert [call.args[0] for call in chain.remove.call_args_list] == [
        "env",
        "shared-credentials-file",
    ]
    constructor.assert_called_once_with(botocore_session=core)


def test_provider_failure_is_sanitized_and_disabled_maintenance_is_explicit(tmp_path, monkeypatch):
    values = configured(tmp_path)
    disabled = settings(**(values | {"files_enabled": False}))
    assert isinstance(
        runtime.get_private_storage(disabled, allow_disabled=True), LocalPrivateStorage
    )
    monkeypatch.setattr(
        runtime.boto3, "Session", MagicMock(side_effect=RuntimeError("synthetic-secret-only"))
    )
    values |= {
        "files_storage_backend": "s3",
        "files_s3_bucket": "synthetic-files",
        "files_s3_region": "us-east-1",
        "files_s3_encryption": "AES256",
        "files_s3_access_key_id": "synthetic-access-id",
        "files_s3_secret_access_key": "synthetic-secret-only",
    }
    with pytest.raises(AuthError) as error:
        runtime.get_private_storage(settings(**values))
    assert error.value.code == "file_runtime_unavailable"
    assert "synthetic-secret-only" not in str(error.value)
