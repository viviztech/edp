from functools import lru_cache
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

from cryptography.fernet import Fernet
from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["local", "test", "staging", "production"] = "local"
    database_url: SecretStr
    redis_url: SecretStr
    bff_key: SecretStr | None = Field(default=None, min_length=32)
    auth_delivery_key: SecretStr | None = None
    asset_scanner_key: SecretStr | None = Field(default=None, min_length=16)
    lms_material_root: str | None = None
    lms_material_signing_key: SecretStr | None = Field(default=None, min_length=32)
    lms_material_access_seconds: int = Field(default=300, ge=60, le=900)
    meta_secret_key: SecretStr | None = None
    meta_graph_api_version: str | None = Field(default=None, pattern=r"^v[0-9]{1,2}\.[0-9]{1,2}$")
    meta_graph_base_url: Literal["https://graph.facebook.com"] = "https://graph.facebook.com"
    meta_event_retention_days: int | None = Field(default=None, ge=1, le=3650)
    notification_retention_days: int | None = Field(default=None, ge=1, le=3650)
    crm_export_lease_seconds: int = Field(default=120, ge=60, le=900)
    crm_export_max_attempts: int = Field(default=3, ge=1, le=10)
    crm_export_recovery_batch_size: int = Field(default=25, ge=1, le=100)
    crm_export_max_bytes: int = Field(default=10485760, ge=1024, le=20971520)
    crm_export_retention_days: int | None = Field(default=None, ge=1, le=3650)
    contact_privacy_version: str = Field(default="v1", min_length=1, max_length=40)
    contact_enquiries_enabled: bool = False
    contact_privacy_notice_url_en: str = Field(default="", max_length=2048)
    contact_privacy_notice_url_ta: str = Field(default="", max_length=2048)
    contact_consent_text_en: str = Field(default="", max_length=2000)
    contact_consent_text_ta: str = Field(default="", max_length=2000)
    files_enabled: bool = False
    files_maintenance_enabled: bool = False
    files_storage_backend: Literal["local", "s3"] | None = None
    files_local_root: str | None = None
    files_temp_root: str | None = None
    files_max_bytes: int = Field(default=10485760, ge=1, le=10485760)
    files_upload_lease_seconds: int = Field(default=120, ge=30, le=900)
    files_scan_lease_seconds: int = Field(default=120, ge=30, le=900)
    files_scan_max_attempts: int = Field(default=3, ge=1, le=10)
    files_cleanup_batch_size: int = Field(default=25, ge=1, le=100)
    files_intent_limit_per_window: int = Field(default=60, ge=1, le=600)
    files_s3_bucket: str | None = Field(
        default=None, min_length=3, max_length=63, pattern=r"^[a-z0-9][a-z0-9.-]*[a-z0-9]$"
    )
    files_s3_endpoint_url: str | None = Field(default=None, max_length=2048)
    files_s3_region: str | None = Field(default=None, min_length=1, max_length=80)
    files_s3_access_key_id: SecretStr | None = Field(default=None, min_length=1, max_length=256)
    files_s3_secret_access_key: SecretStr | None = Field(
        default=None, min_length=1, max_length=4096
    )
    files_s3_session_token: SecretStr | None = Field(default=None, min_length=1, max_length=8192)
    files_s3_use_iam_role: bool = False
    files_s3_encryption: Literal["AES256", "aws:kms"] | None = None
    files_s3_kms_key_id: str | None = Field(default=None, min_length=1, max_length=2048)
    clamav_host: str | None = Field(default=None, min_length=1, max_length=253)
    clamav_port: int = Field(default=3310, ge=1, le=65535)
    clamav_timeout_seconds: int = Field(default=30, ge=1, le=120)
    clamav_max_reply_bytes: int = Field(default=4096, ge=256, le=16384)
    clamav_max_signature_age_seconds: int | None = Field(default=None, ge=3600, le=604800)
    access_token_seconds: int = Field(default=600, ge=60, le=1800)
    session_seconds: int = Field(default=1209600, ge=3600, le=2592000)
    cors_origins: list[str] = Field(default_factory=list)

    @field_validator(
        "bff_key",
        "auth_delivery_key",
        "asset_scanner_key",
        "lms_material_root",
        "lms_material_signing_key",
        "meta_secret_key",
        "meta_graph_api_version",
        "meta_event_retention_days",
        "notification_retention_days",
        "crm_export_retention_days",
        "files_storage_backend",
        "files_local_root",
        "files_temp_root",
        "files_s3_bucket",
        "files_s3_endpoint_url",
        "files_s3_region",
        "files_s3_access_key_id",
        "files_s3_secret_access_key",
        "files_s3_session_token",
        "files_s3_encryption",
        "files_s3_kms_key_id",
        "clamav_host",
        "clamav_max_signature_age_seconds",
        mode="before",
    )
    @classmethod
    def empty_secret(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("auth_delivery_key", "meta_secret_key")
    @classmethod
    def delivery_key_format(cls, value: SecretStr | None) -> SecretStr | None:
        if value:
            Fernet(value.get_secret_value().encode())
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().startswith("postgresql+psycopg://"):
            raise ValueError("A PostgreSQL psycopg URL is required")
        return value

    @field_validator("redis_url")
    @classmethod
    def validate_redis(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().startswith(("redis://", "rediss://")):
            raise ValueError("A Redis URL is required")
        return value

    @field_validator("cors_origins")
    @classmethod
    def validate_origins(cls, values: list[str]) -> list[str]:
        if any(value == "*" or not value.startswith(("http://", "https://")) for value in values):
            raise ValueError("Explicit HTTP origins required")
        return values

    @field_validator("files_s3_endpoint_url")
    @classmethod
    def private_storage_endpoint(cls, value: str | None) -> str | None:
        if value is not None:
            url = urlsplit(value)
            # Accessing port also rejects malformed and out-of-range ports.
            _ = url.port
            if (
                url.scheme not in {"http", "https"}
                or not url.hostname
                or url.username is not None
                or url.password is not None
                or url.query
                or url.fragment
                or url.path not in {"", "/"}
            ):
                raise ValueError("A server-configured HTTP storage endpoint is required")
        return value

    @model_validator(mode="after")
    def enabled_file_runtime(self) -> Self:
        if not (self.files_enabled or self.files_maintenance_enabled):
            return self
        if self.files_s3_use_iam_role and (
            self.files_s3_access_key_id or self.files_s3_secret_access_key
        ):
            raise ValueError("Choose one server credential source for file storage")
        if self.files_s3_encryption == "aws:kms" and not self.files_s3_kms_key_id:
            raise ValueError("The configured file encryption key reference is required")
        if self.app_env in {"staging", "production"}:
            if (
                self.files_storage_backend != "s3"
                or not self.files_s3_bucket
                or not self.files_s3_region
                or not self.files_s3_encryption
                or not self.files_temp_root
                or not Path(self.files_temp_root).is_absolute()
                or (
                    self.files_enabled
                    and (
                        not self.clamav_host
                        or self.clamav_max_signature_age_seconds is None
                        or self.files_scan_lease_seconds < self.clamav_timeout_seconds + 60
                    )
                )
            ):
                raise ValueError("Private file runtime requires explicit production configuration")
            if self.files_s3_endpoint_url and not self.files_s3_endpoint_url.startswith("https://"):
                raise ValueError("Production file storage requires HTTPS")
            if not self.files_s3_use_iam_role and not (
                self.files_s3_access_key_id and self.files_s3_secret_access_key
            ):
                raise ValueError("A server credential source is required for file storage")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
