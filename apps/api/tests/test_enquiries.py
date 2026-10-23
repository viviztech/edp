import os
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_identity import auth, signed_in  # noqa: F401

from app.core.config import get_settings
from app.modules.cms.models import Enquiry
from app.modules.identity.models import AuditLog, Organization, Role, User, UserRole

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)


@pytest.fixture
def enquiries(request, monkeypatch):
    fixture_data = request.getfixturevalue("auth")
    client, engine, _, _ = fixture_data
    credentials, tokens, _ = signed_in(fixture_data)
    with Session(engine) as db:
        user = db.scalar(select(User).where(User.email == credentials["email"]))
        role = db.scalar(select(Role).where(Role.name == "Support Executive"))
        organization = Organization(name="Synthetic enquiry team")
        db.add(organization)
        db.flush()
        db.add(UserRole(user_id=user.id, role_id=role.id, organization_id=organization.id))
        db.commit()
        org = str(organization.id)
    monkeypatch.setenv("CONTACT_ENQUIRIES_ENABLED", "true")
    for locale in ("en", "ta"):
        monkeypatch.setenv(
            "CONTACT_PRIVACY_NOTICE_URL_" + locale.upper(), f"/{locale}/pages/privacy"
        )
        monkeypatch.setenv("CONTACT_CONSENT_TEXT_" + locale.upper(), "Synthetic test consent only")
    get_settings.cache_clear()
    client.headers["Authorization"] = "Bearer " + tokens["access_token"]
    return client, engine, f"/api/v1/public/organizations/{org}", f"/api/v1/cms/organizations/{org}"


def payload(index=0):
    return {
        "name": "Synthetic Enquirer",
        "email": f"enquirer{index}@example.test",
        "phone": "",
        "message": "Synthetic programme question",
        "consent_version": "v1",
    }


def test_policy_requires_bilingual_approved_configuration(enquiries, monkeypatch):
    client, _, public, _ = enquiries
    for locale in ("en", "ta"):
        policy = client.get(public + "/enquiry-policy?locale=" + locale)
        assert policy.status_code == 200
        assert policy.json()["enabled"] is True
        assert policy.headers["cache-control"] == "no-store"
    monkeypatch.setenv("CONTACT_CONSENT_TEXT_TA", "")
    get_settings.cache_clear()
    assert client.get(public + "/enquiry-policy").json() == {
        "enabled": False,
        "consent_version": "",
        "privacy_notice_url": "",
        "consent_text": "",
    }
    assert client.post(public + "/enquiries", json=payload()).status_code == 503
    monkeypatch.setenv("CONTACT_CONSENT_TEXT_TA", "Synthetic consent")
    monkeypatch.setenv("CONTACT_PRIVACY_NOTICE_URL_EN", "javascript:alert(1)")
    get_settings.cache_clear()
    assert client.get(public + "/enquiry-policy").json()["enabled"] is False


def test_public_receipt_deduplication_validation_and_limits(enquiries):
    client, engine, public, _ = enquiries
    first = client.post(public + "/enquiries", json=payload())
    second = client.post(public + "/enquiries", json=payload())
    assert first.status_code == second.status_code == 202
    assert set(first.json()) == {"accepted", "reference"}
    assert first.json()["reference"] != second.json()["reference"]
    assert "enquirer" not in first.text and "message" not in first.text
    with Session(engine) as db:
        assert len(list(db.scalars(select(Enquiry)))) == 1
    wrong = payload(1) | {"consent_version": "outdated"}
    assert client.post(public + "/enquiries", json=wrong).status_code == 422
    assert (
        client.post(public + "/enquiries", json=payload(2) | {"email": "invalid"}).status_code
        == 422
    )
    assert client.post(public + "/enquiries", content=b"x" * 262145).status_code == 413
    assert (
        client.post(public + "/enquiries", json=payload(3) | {"message": "தமிழ்" * 1000}).status_code
        == 202
    )
    assert (
        client.post(public + "/enquiries", json=payload(4) | {"message": "x" * 5001}).status_code
        == 422
    )


def test_public_rate_limit_cannot_be_bypassed_with_forwarded_headers(enquiries):
    client, _, public, _ = enquiries
    for index in range(5):
        assert (
            client.post(
                public + "/enquiries",
                json=payload(),
                headers={"X-Forwarded-For": f"192.0.2.{index}"},
            ).status_code
            == 202
        )
    blocked = client.post(
        public + "/enquiries", json=payload(), headers={"X-Forwarded-For": "192.0.2.100"}
    )
    assert blocked.status_code == 429
    assert blocked.headers["Retry-After"] == "900"


def test_source_budget_is_shared_even_with_distinct_contact_and_forwarded_addresses(enquiries):
    client, _, public, _ = enquiries
    for index in range(30):
        accepted = client.post(
            public + "/enquiries",
            json=payload(index),
            headers={"X-Forwarded-For": f"192.0.2.{index}"},
        )
        assert accepted.status_code == 202
    assert (
        client.post(
            public + "/enquiries",
            json=payload(31),
            headers={"X-Forwarded-For": "198.51.100.1"},
        ).status_code
        == 429
    )


def test_scoped_paginated_queue_status_versions_and_audit(enquiries):
    client, engine, public, staff = enquiries
    ids = [
        client.post(public + "/enquiries", json=payload(index)).json()["reference"]
        for index in range(3)
    ]
    queue = client.get(staff + "/enquiries/queue?limit=1&status=new").json()
    assert len(queue["items"]) == 1 and queue["next_cursor"]
    rest = client.get(staff + "/enquiries/queue?limit=2&cursor=" + queue["next_cursor"]).json()
    assert len(rest["items"]) == 2 and rest["next_cursor"] is None
    assert len(client.get(staff + "/enquiries").json()) == 3  # legacy array remains valid
    path = staff + "/enquiries/" + ids[0]
    assert client.get(path).json()["version"] == 1
    assert (
        client.post(path + "/status", json={"expected_version": 1, "status": "closed"}).status_code
        == 409
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: (
                    client.post(
                        path + "/status", json={"expected_version": 1, "status": "reviewed"}
                    ).status_code
                ),
                range(2),
            )
        )
    assert sorted(results) == [200, 409]
    assert (
        client.post(path + "/status", json={"expected_version": 2, "status": "closed"}).status_code
        == 200
    )
    assert (
        client.post(
            path + "/status", json={"expected_version": 3, "status": "reviewed"}
        ).status_code
        == 409
    )
    with Session(engine) as db:
        events = list(
            db.scalars(
                select(AuditLog)
                .where(AuditLog.action == "enquiry.status_changed")
                .order_by(AuditLog.resource_version)
            )
        )
        assert [event.resource_version for event in events] == [2, 3]
        assert all(event.changed_fields == "status" for event in events)
    with engine.begin() as connection:
        with pytest.raises(DBAPIError):
            connection.execute(text("UPDATE contact_enquiries SET message='tampered'"))
    other = staff.replace(staff.split("/")[-1], str(uuid4()))
    assert client.get(other + "/enquiries/queue").status_code == 403
    assert client.get(staff + "/enquiries/" + str(uuid4())).status_code == 404
    client.headers.pop("Authorization")
    assert client.get(path).status_code == 401
    assert client.get(staff + "/enquiries/queue").status_code == 401


def test_view_only_permission_and_status_audit_rollback(enquiries):
    client, engine, public, staff = enquiries
    reference = client.post(public + "/enquiries", json=payload()).json()["reference"]
    path = staff + "/enquiries/" + reference
    with patch(
        "app.modules.cms.enquiry_service.AuditLog",
        side_effect=RuntimeError("synthetic audit failure"),
    ):
        assert (
            client.post(
                path + "/status", json={"expected_version": 1, "status": "reviewed"}
            ).status_code
            == 500
        )
    assert client.get(path).json()["status"] == "new"
    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM role_permissions WHERE permission_code='enquiry.manage'")
        )
    assert client.get(path).status_code == 200
    assert (
        client.post(
            path + "/status", json={"expected_version": 1, "status": "reviewed"}
        ).status_code
        == 403
    )


def test_authorized_peer_organization_cannot_read_or_mutate_another_inbox(enquiries):
    client, engine, public, staff = enquiries
    reference = client.post(public + "/enquiries", json=payload()).json()["reference"]
    with Session(engine) as db:
        actor = db.scalar(select(User))
        role = db.scalar(select(Role).where(Role.name == "Support Executive"))
        peer = Organization(name="Another synthetic enquiry team")
        db.add(peer)
        db.flush()
        db.add(UserRole(user_id=actor.id, role_id=role.id, organization_id=peer.id))
        db.commit()
        peer_staff = staff.replace(staff.split("/")[-1], str(peer.id))
    assert client.get(peer_staff + "/enquiries/queue").json()["items"] == []
    assert client.get(peer_staff + "/enquiries/" + reference).status_code == 404
    assert (
        client.post(
            peer_staff + "/enquiries/" + reference + "/status",
            json={"expected_version": 1, "status": "reviewed"},
        ).status_code
        == 404
    )
