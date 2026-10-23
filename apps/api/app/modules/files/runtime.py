"""Lazy server-side adapters. Policy administration never opens a provider connection."""

import os
import stat
from collections.abc import Callable
from pathlib import Path
from typing import cast

import boto3
from botocore.config import Config
from botocore.session import Session as BotocoreSession

from app.core.config import Settings, get_settings
from app.modules.files.scanner import ClamAVScanner, FileScanner
from app.modules.files.storage import (
    LocalPrivateStorage,
    PrivateStorage,
    S3Client,
    S3PrivateStorage,
)
from app.modules.identity.security import AuthError


def require_files_enabled(settings: Settings | None = None) -> Settings:
    value = settings or get_settings()
    if not value.files_enabled:
        raise AuthError("file_collection_disabled", 503)
    return value


def private_temp_root(settings: Settings | None = None) -> Path:
    value = settings or get_settings()
    if not value.files_temp_root:
        raise AuthError("file_runtime_unavailable", 503)
    root = Path(value.files_temp_root)
    try:
        if not root.is_absolute() or not root.is_dir():
            raise ValueError
        # Deployment creates this directory. Do not silently accept a symlink/junction
        # or create a directory with inherited public permissions during a request.
        for path in (root, *root.parents):
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise ValueError
        if os.name != "nt":
            info = root.stat()
            get_euid = cast(Callable[[], int], getattr(os, "geteuid"))  # noqa: B009
            if info.st_mode & 0o077 or info.st_uid != get_euid():
                raise ValueError
    except (OSError, ValueError):
        raise AuthError("file_runtime_unavailable", 503) from None
    return root


def get_private_storage(
    settings: Settings | None = None, *, allow_disabled: bool = False
) -> PrivateStorage:
    """allow_disabled is reserved for expiry/hold-aware maintenance, never byte routes."""
    value = settings or get_settings()
    if not allow_disabled:
        require_files_enabled(value)
    temp_root = private_temp_root(value)
    if value.files_storage_backend == "local":
        if (
            value.app_env not in {"local", "test"}
            or not value.files_local_root
            or not Path(value.files_local_root).is_absolute()
        ):
            raise AuthError("file_runtime_unavailable", 503)
        return LocalPrivateStorage(
            Path(value.files_local_root), max_bytes=value.files_max_bytes, temp_root=temp_root
        )
    if (
        value.files_storage_backend != "s3"
        or not value.files_s3_bucket
        or not value.files_s3_region
        or not value.files_s3_encryption
        or (value.files_s3_use_iam_role and value.files_s3_access_key_id)
    ):
        raise AuthError("file_runtime_unavailable", 503)
    try:
        if value.files_s3_use_iam_role:
            # Explicitly opt into workload identity only. A developer's environment
            # or shared AWS profile must not silently select this application's account.
            session = BotocoreSession()
            providers = session.get_component("credential_provider")
            allowed = {"iam-role", "container-role", "assume-role-with-web-identity"}
            for provider in list(providers.providers):
                if provider.METHOD not in allowed:
                    providers.remove(provider.METHOD)
            sdk = boto3.Session(botocore_session=session)
        elif value.files_s3_access_key_id and value.files_s3_secret_access_key:
            sdk = boto3.Session(
                aws_access_key_id=value.files_s3_access_key_id.get_secret_value(),
                aws_secret_access_key=value.files_s3_secret_access_key.get_secret_value(),
                aws_session_token=(
                    value.files_s3_session_token.get_secret_value()
                    if value.files_s3_session_token
                    else None
                ),
            )
        else:
            raise AuthError("file_runtime_unavailable", 503)
        client = sdk.client(
            "s3",
            region_name=value.files_s3_region,
            endpoint_url=value.files_s3_endpoint_url,
            config=Config(
                connect_timeout=3,
                read_timeout=10,
                retries={"total_max_attempts": 1},
                signature_version="s3v4",
                s3={"addressing_style": "path"} if value.files_s3_endpoint_url else {},
            ),
        )
        return S3PrivateStorage(
            # The injected protocol deliberately accepts dicts for alternate S3
            # implementations; SDK TypedDict responses implement that contract.
            cast(S3Client, client),
            bucket=value.files_s3_bucket,
            max_bytes=value.files_max_bytes,
            server_side_encryption=value.files_s3_encryption,
            kms_key_id=value.files_s3_kms_key_id,
            temp_root=temp_root,
        )
    except AuthError:
        raise
    except Exception:
        raise AuthError("file_runtime_unavailable", 503) from None


def get_file_scanner(settings: Settings | None = None) -> FileScanner:
    value = require_files_enabled(settings)
    if not value.clamav_host or value.files_scan_lease_seconds < value.clamav_timeout_seconds + 60:
        raise AuthError("file_runtime_unavailable", 503)
    try:
        return ClamAVScanner(
            value.clamav_host,
            value.clamav_port,
            timeout_seconds=value.clamav_timeout_seconds,
            max_reply_bytes=value.clamav_max_reply_bytes,
            max_signature_age_seconds=value.clamav_max_signature_age_seconds,
        )
    except ValueError:
        raise AuthError("file_runtime_unavailable", 503) from None
