from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import app
from app.workers.celery_app import probe


def test_liveness_and_generated_correlation_id() -> None:
    with TestClient(app) as client:
        response = client.get("/health", headers={"X-Request-ID": "untrusted"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert UUID(response.headers["X-Request-ID"])
    assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize("available,expected", [(True, 200), (False, 503)])
def test_readiness_does_not_disclose_internals(available: bool, expected: int) -> None:
    with patch("app.main.dependencies_ready", new=AsyncMock(return_value=available)):
        with TestClient(app) as client:
            response = client.get("/ready")
    assert response.status_code == expected
    assert response.json() == {"status": "ready" if available else "unavailable"}


def test_dependency_exception_is_sanitized() -> None:
    with TestClient(app) as client:
        with patch(
            "sqlalchemy.ext.asyncio.AsyncEngine.connect", side_effect=RuntimeError("sensitive")
        ):
            response = client.get("/ready")
    assert response.status_code == 503
    assert "sensitive" not in response.text


def test_missing_route_uses_error_contract() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/users")
    assert response.status_code == 404
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]


def test_rejects_non_postgres_and_wildcard_cors() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite:///data", redis_url="redis://localhost", cors_origins=["*"])


def test_worker_probe_has_no_business_effect() -> None:
    assert probe() == {"status": "ok"}
