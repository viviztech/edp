import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import app


def test_public_mobile_policy_is_disabled_and_no_store_by_default(monkeypatch):
    configuration = Settings(
        database_url="postgresql+psycopg://localhost/edp_unit_unused",
        redis_url="redis://localhost/15",
        _env_file=None,
    )
    monkeypatch.setattr("app.modules.system.mobile.get_settings", lambda: configuration)
    with TestClient(app) as client:
        for platform in ("android", "ios", "web"):
            response = client.get("/api/v1/public/mobile-policy", params={"platform": platform})
            assert response.status_code == 200
            assert response.headers["cache-control"] == "no-store"
            assert response.json() == {
                "platform": platform,
                "updates_enabled": False,
                "minimum_version": "0.1.0",
                "latest_version": "0.1.0",
                "download_url": None,
            }
        assert client.get("/api/v1/public/mobile-policy?platform=unknown").status_code == 422


def test_configured_mobile_policy_has_platform_specific_approved_links(monkeypatch):
    configuration = Settings(
        database_url="postgresql+psycopg://localhost/edp_unit_unused",
        redis_url="redis://localhost/15",
        mobile_updates_enabled=True,
        mobile_minimum_version="1.0.0",
        mobile_latest_version="1.2.0",
        mobile_android_download_url="https://play.google.com/store/apps/details?id=example.synthetic",
        mobile_ios_download_url="https://apps.apple.com/app/example-synthetic",
        _env_file=None,
    )
    monkeypatch.setattr("app.modules.system.mobile.get_settings", lambda: configuration)
    with TestClient(app) as client:
        android = client.get("/api/v1/public/mobile-policy?platform=android").json()
        assert android["updates_enabled"] is True and android["minimum_version"] == "1.0.0"
        assert android["download_url"].startswith("https://play.google.com/")
        web = client.get("/api/v1/public/mobile-policy?platform=web").json()
        assert web["updates_enabled"] is False and web["download_url"] is None


@pytest.mark.parametrize(
    "fields",
    [
        {"mobile_minimum_version": "v1"},
        {"mobile_minimum_version": "1.0.0", "mobile_latest_version": "0.9.0"},
        {"mobile_updates_enabled": True},
        {"mobile_android_download_url": "javascript:alert(1)"},
        {"mobile_android_download_url": "https://user:secret@example.com/app"},
        {"mobile_android_download_url": "https://example.com/\nsecret"},
    ],
)
def test_invalid_mobile_policy_is_rejected(fields):
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql+psycopg://localhost/edp_unit_unused",
            redis_url="redis://localhost/15",
            _env_file=None,
            **fields,
        )
