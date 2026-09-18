import json
import os
import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.main import create_app
from app.modules.identity.models import (
    AuditLog,
    AuthDelivery,
    AuthThrottle,
    Organization,
    RefreshSession,
    Role,
    User,
    UserRole,
    VerificationToken,
    now,
)
from app.modules.identity.service import seed_roles

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)


@pytest.fixture
def auth(monkeypatch):
    url = os.environ["AUTH_TEST_DATABASE_URL"]
    engine = create_engine(url)
    assert engine.url.database in {"edp_auth_test", "edp_test"}, (
        "Refuse to clear a non-test database"
    )
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("APP_ENV", "test")
    key = Fernet.generate_key()
    bff = secrets.token_urlsafe(32)
    monkeypatch.setenv("AUTH_DELIVERY_KEY", key.decode())
    monkeypatch.setenv("BFF_KEY", bff)
    get_settings.cache_clear()
    with engine.begin() as connection:
        connection.execute(
            text("TRUNCATE people, organizations, roles, permissions, auth_throttles CASCADE")
        )
    with Session(engine) as db:
        seed_roles(db)
    with TestClient(create_app()) as client:
        yield client, engine, key, bff
    engine.dispose()
    get_settings.cache_clear()


def challenge(auth, purpose="verify"):
    _, engine, key, _ = auth
    with Session(engine) as db:
        row = db.scalar(
            select(AuthDelivery)
            .join(VerificationToken)
            .where(VerificationToken.purpose == purpose)
            .order_by(AuthDelivery.created_at.desc())
            .limit(1)
        )
        assert row is not None
        payload = json.loads(Fernet(key).decrypt(row.encrypted_payload.encode()))
        assert payload["token"] not in row.encrypted_payload
        return payload["token"]


def account(auth, email="learner@example.com"):
    client = auth[0]
    password = secrets.token_urlsafe(24)
    data = {
        "email": email,
        "password": password,
        "display_name": "Synthetic Learner",
        "locale": "ta",
    }
    assert client.post("/api/v1/auth/register", json=data).status_code == 202
    raw = challenge(auth)
    assert client.post("/api/v1/auth/verify", json={"token": raw}).status_code == 200
    return {"email": email, "password": password}


def signed_in(auth):
    credentials = account(auth)
    response = auth[0].post("/api/v1/auth/login", json=credentials)
    assert response.status_code == 200
    tokens = response.json()
    return credentials, tokens, {"Authorization": "Bearer " + tokens["access_token"]}


def test_registration_pending_duplicate_and_no_token_leak(auth):
    client, engine, _, _ = auth
    password = secrets.token_urlsafe(24)
    data = {"email": "LEARNER@example.com", "password": password, "display_name": "Synthetic"}
    response = client.post("/api/v1/auth/register", json=data)
    assert response.status_code == 202 and response.json() == {"status": "accepted"}
    assert client.post("/api/v1/auth/register", json=data).json() == response.json()
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": data["email"], "password": password}
        ).status_code
        == 401
    )
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(User)) == 1
        user = db.scalar(select(User))
        assert user.email == "learner@example.com" and user.password_hash.startswith("$argon2id$")
        assert password not in user.password_hash
    assert (
        client.post("/api/v1/auth/register", json={**data, "role": "Super Admin"}).status_code
        == 422
    )


def test_verification_single_use_and_purpose_bound(auth):
    account(auth)
    raw = challenge(auth)
    assert auth[0].post("/api/v1/auth/verify", json={"token": raw}).status_code == 400
    assert (
        auth[0]
        .post("/api/v1/auth/reset", json={"token": raw, "password": secrets.token_urlsafe(24)})
        .status_code
        == 400
    )


def test_expired_verification_rejected(auth):
    client, engine, _, _ = auth
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "expired@example.com",
            "password": secrets.token_urlsafe(24),
            "display_name": "Expired",
        },
    )
    raw = challenge(auth)
    with Session(engine) as db:
        db.execute(update(VerificationToken).values(expires_at=now() - timedelta(seconds=1)))
        db.commit()
    assert client.post("/api/v1/auth/verify", json={"token": raw}).status_code == 400


def test_refresh_rotation_replay_revokes_family(auth):
    _, original, headers = signed_in(auth)
    client = auth[0]
    rotated = client.post("/api/v1/auth/refresh", json={"token": original["refresh_token"]})
    assert rotated.status_code == 200
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    current = {"Authorization": "Bearer " + rotated.json()["access_token"]}
    assert client.get("/api/v1/auth/me", headers=current).status_code == 200
    assert (
        client.post("/api/v1/auth/refresh", json={"token": original["refresh_token"]}).status_code
        == 401
    )
    assert client.get("/api/v1/auth/me", headers=current).status_code == 401


def test_concurrent_refresh_one_success_then_family_revoked(auth):
    _, tokens, _ = signed_in(auth)

    def rotate(_):
        return auth[0].post("/api/v1/auth/refresh", json={"token": tokens["refresh_token"]})

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(rotate, range(2)))
    assert sorted(r.status_code for r in responses) == [200, 401]
    winner = next(r for r in responses if r.status_code == 200).json()
    assert (
        auth[0]
        .get("/api/v1/auth/me", headers={"Authorization": "Bearer " + winner["access_token"]})
        .status_code
        == 401
    )


def test_reset_revokes_all_sessions_and_is_single_use(auth):
    credentials, tokens, headers = signed_in(auth)
    client = auth[0]
    assert (
        client.post("/api/v1/auth/request-reset", json={"email": credentials["email"]}).status_code
        == 202
    )
    raw = challenge(auth, "reset")
    new = secrets.token_urlsafe(24)
    assert (
        client.post("/api/v1/auth/reset", json={"token": raw, "password": new}).status_code == 200
    )
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert (
        client.post("/api/v1/auth/refresh", json={"token": tokens["refresh_token"]}).status_code
        == 401
    )
    assert client.post("/api/v1/auth/login", json=credentials).status_code == 401
    assert (
        client.post("/api/v1/auth/login", json={**credentials, "password": new}).status_code == 200
    )
    assert (
        client.post("/api/v1/auth/reset", json={"token": raw, "password": new}).status_code == 400
    )


def test_reset_request_does_not_enumerate(auth):
    credentials = account(auth)
    known = auth[0].post("/api/v1/auth/request-reset", json={"email": credentials["email"]})
    unknown = auth[0].post("/api/v1/auth/request-reset", json={"email": "unknown@example.com"})
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()


def test_suspension_and_session_expiry_rechecked(auth):
    _, tokens, headers = signed_in(auth)
    client, engine, _, _ = auth
    with Session(engine) as db:
        db.execute(update(User).values(status="suspended"))
        db.commit()
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    with Session(engine) as db:
        db.execute(update(User).values(status="active"))
        db.execute(update(RefreshSession).values(expires_at=now() - timedelta(seconds=1)))
        db.commit()
    assert (
        client.post("/api/v1/auth/refresh", json={"token": tokens["refresh_token"]}).status_code
        == 401
    )


def test_browser_internal_key_and_csrf(auth):
    credentials = account(auth)
    client, _, _, bff = auth
    assert client.post("/api/v1/auth/browser/login", json=credentials).status_code == 403
    response = client.post(
        "/api/v1/auth/browser/login", json=credentials, headers={"X-BFF-Key": bff}
    )
    assert response.status_code == 200
    payload = response.json()
    assert "access_token" not in payload and "refresh_token" not in payload
    headers = {"X-BFF-Key": bff, "X-Browser-Session": payload["browser_token"]}
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 403
    assert (
        client.post(
            "/api/v1/auth/logout", headers={**headers, "X-CSRF-Token": payload["csrf_token"]}
        ).status_code
        == 200
    )
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_scoped_rbac_and_revoked_grant(auth):
    _, _, headers = signed_in(auth)
    client, engine, _, _ = auth
    with Session(engine) as db:
        user = db.scalar(select(User))
        role = db.scalar(select(Role).where(Role.name == "Super Admin"))
        org = Organization(name="Synthetic organization")
        db.add(org)
        db.flush()
        grant = UserRole(user_id=user.id, role_id=role.id, organization_id=org.id)
        db.add(grant)
        db.commit()
        org_id, grant_id = org.id, grant.id
    assert client.get(f"/api/v1/system/organizations/{org_id}/access").status_code == 401
    assert (
        client.get(f"/api/v1/system/organizations/{uuid4()}/access", headers=headers).status_code
        == 403
    )
    assert (
        client.get(f"/api/v1/system/organizations/{org_id}/access", headers=headers).status_code
        == 200
    )
    assert (
        client.get(f"/api/v1/system/organizations/{org_id}/audit", headers=headers).status_code
        == 200
    )
    with Session(engine) as db:
        db.delete(db.get(UserRole, grant_id))
        db.commit()
    assert (
        client.get(f"/api/v1/system/organizations/{org_id}/access", headers=headers).status_code
        == 403
    )


def test_participant_cannot_access_staff_and_audit_is_append_only(auth):
    _, _, headers = signed_in(auth)
    client, engine, _, _ = auth
    assert (
        client.get(f"/api/v1/system/organizations/{uuid4()}/audit", headers=headers).status_code
        == 403
    )
    with Session(engine) as db:
        with pytest.raises(DBAPIError):
            db.execute(update(AuditLog).values(action="tampered"))
            db.commit()
        db.rollback()
        assert db.scalar(select(func.count()).select_from(AuditLog)) > 0


def test_logout_all_and_session_ownership(auth):
    credentials, _, headers = signed_in(auth)
    client = auth[0]
    second = client.post("/api/v1/auth/login", json=credentials).json()
    sessions = client.get("/api/v1/auth/sessions", headers=headers).json()
    assert len(sessions) == 2 and sum(s["current"] for s in sessions) == 1
    assert (
        client.post(f"/api/v1/auth/sessions/{uuid4()}/revoke", headers=headers).status_code == 404
    )
    assert client.post("/api/v1/auth/logout-all", headers=headers).status_code == 200
    assert (
        client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer " + second["access_token"]}
        ).status_code
        == 401
    )


def test_database_throttle_persists_failure(auth):
    client, engine, _, _ = auth
    payload = {"email": "unknown@example.com", "password": secrets.token_urlsafe(24)}
    for _ in range(10):
        assert client.post("/api/v1/auth/login", json=payload).status_code == 401
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 429 and response.headers["Retry-After"] == "900"
    with Session(engine) as db:
        assert db.scalar(select(func.max(AuthThrottle.hits))) == 11


def test_audit_failure_rolls_back_registration(auth, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("synthetic audit failure")

    monkeypatch.setattr("app.modules.identity.service.audit", fail)
    response = auth[0].post(
        "/api/v1/auth/register",
        json={
            "email": "rollback@example.com",
            "password": secrets.token_urlsafe(24),
            "display_name": "Rollback",
        },
    )
    assert response.status_code == 500
    with Session(auth[1]) as db:
        assert db.scalar(select(func.count()).select_from(User)) == 0


def test_access_expiry_can_refresh_but_refresh_is_not_access(auth):
    _, tokens, headers = signed_in(auth)
    client, engine, _, _ = auth
    assert (
        client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer " + tokens["refresh_token"]}
        ).status_code
        == 401
    )
    with Session(engine) as db:
        db.execute(update(RefreshSession).values(access_expires_at=now() - timedelta(seconds=1)))
        db.commit()
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert (
        client.post("/api/v1/auth/refresh", json={"token": tokens["refresh_token"]}).status_code
        == 200
    )


def test_cannot_revoke_another_person_session(auth):
    _, _, first_headers = signed_in(auth)
    other = account(auth, "other@example.com")
    tokens = auth[0].post("/api/v1/auth/login", json=other).json()
    other_headers = {"Authorization": "Bearer " + tokens["access_token"]}
    other_session = auth[0].get("/api/v1/auth/sessions", headers=other_headers).json()[0]["id"]
    assert (
        auth[0]
        .post(f"/api/v1/auth/sessions/{other_session}/revoke", headers=first_headers)
        .status_code
        == 404
    )
    assert auth[0].get("/api/v1/auth/me", headers=other_headers).status_code == 200


def test_validation_never_echoes_password(auth):
    marker = secrets.token_hex(3)
    response = auth[0].post(
        "/api/v1/auth/login", json={"email": "user@example.com", "password": marker}
    )
    assert response.status_code == 422
    assert marker not in response.text
    assert "input" not in response.json()["error"]["details"][0]


def test_production_delivery_is_explicitly_disabled(auth, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    response = auth[0].post(
        "/api/v1/auth/register",
        json={
            "email": "production@example.com",
            "password": secrets.token_urlsafe(24),
            "display_name": "Synthetic",
        },
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "delivery_unavailable"
