from functools import lru_cache
from typing import Literal

from cryptography.fernet import Fernet
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["local", "test", "staging", "production"] = "local"
    database_url: SecretStr
    redis_url: SecretStr
    bff_key: SecretStr | None = Field(default=None, min_length=32)
    auth_delivery_key: SecretStr | None = None
    asset_scanner_key: SecretStr | None = Field(default=None, min_length=16)
    access_token_seconds: int = Field(default=600, ge=60, le=1800)
    session_seconds: int = Field(default=1209600, ge=3600, le=2592000)
    cors_origins: list[str] = Field(default_factory=list)

    @field_validator("bff_key", "auth_delivery_key", "asset_scanner_key", mode="before")
    @classmethod
    def empty_secret(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("auth_delivery_key")
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
