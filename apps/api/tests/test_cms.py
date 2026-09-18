import os
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_identity import auth, signed_in  # noqa: F401

from app.modules.identity.models import AuditLog, Organization, Role, User, UserRole

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)


@pytest.fixture
def cms(request):
    fixture_data = request.getfixturevalue("auth")
    client, engine, _, _ = fixture_data
    credentials, tokens, _ = signed_in(fixture_data)
    with Session(engine) as db:
        user = db.scalar(select(User).where(User.email == credentials["email"]))
        role = db.scalar(select(Role).where(Role.name == "Content Manager"))
        org = Organization(name="Synthetic content team")
        db.add(org)
        db.flush()
        db.add(UserRole(user_id=user.id, role_id=role.id, organization_id=org.id))
        db.commit()
        org_id = str(org.id)
    client.headers["Authorization"] = "Bearer " + tokens["access_token"]
    return (
        client,
        engine,
        "/api/v1/cms/organizations/" + org_id + "/pages",
        "/api/v1/public/organizations/" + org_id + "/pages",
    )


def draft(client, base):
    response = client.post(
        base,
        json={
            "slug": "eligibility",
            "locale": "en",
            "title": "Eligibility",
            "body": "Public information",
        },
    )
    assert response.status_code == 201, response.text
    page = response.json()
    return base + "/" + page["id"] + "/translations/en", page


def test_publication_isolated_drafts_locales_and_archive(cms):
    client, _, base, public = cms
    path, page = draft(client, base)
    assert client.get(public + "/eligibility").status_code == 404
    assert client.post(path + "/publish", json={"expected_version": 1}).status_code == 200
    live = client.get(public + "/eligibility")
    assert live.json()["body"] == "Public information"
    assert "draft" not in live.text
    assert (
        client.get(
            public + "/eligibility", headers={"If-None-Match": live.headers["etag"]}
        ).status_code
        == 304
    )
    assert (
        client.patch(
            path, json={"expected_version": 2, "title": "Changed", "body": "Private draft"}
        ).status_code
        == 200
    )
    assert client.get(public + "/eligibility").json()["body"] == "Public information"
    assert client.get(public + "/eligibility?locale=ta").status_code == 404
    assert (
        client.post(
            base + "/" + page["id"] + "/translations",
            json={"locale": "ta", "title": "Tamil", "body": "Tamil draft"},
        ).status_code
        == 201
    )
    assert client.post(path + "/publish", json={"expected_version": 2}).status_code == 409
    assert (
        client.post(
            path + "/archive", json={"expected_version": 3, "reason": "Superseded"}
        ).status_code
        == 200
    )
    assert (
        client.get(
            public + "/eligibility", headers={"If-None-Match": live.headers["etag"]}
        ).status_code
        == 404
    )
    assert client.post(path + "/publish", json={"expected_version": 4}).status_code == 409
    assert client.post(path + "/restore", json={"expected_version": 4}).status_code == 200
    assert client.get(public + "/eligibility").status_code == 404


def test_duplicate_size_validation_and_scopes(cms):
    client, _, base, _ = cms
    path, _ = draft(client, base)
    assert (
        client.post(
            base, json={"slug": "eligibility", "locale": "en", "title": "Duplicate", "body": "x"}
        ).status_code
        == 409
    )
    assert (
        client.patch(
            path, json={"expected_version": 1, "title": "Bad", "body": "x", "state": "published"}
        ).status_code
        == 422
    )
    assert (
        client.patch(
            path, json={"expected_version": 1, "title": "Bad", "body": "x" * 50001}
        ).status_code
        == 422
    )
    assert client.post(base, content=b"x" * 262145).status_code == 413
    wrong = base.replace(base.split("/")[-2], str(uuid4()))
    assert client.get(wrong).status_code == 403
    client.headers.pop("Authorization")
    assert client.get(base).status_code == 401


def test_revision_immutable_and_audit_transaction(cms):
    client, engine, base, _ = cms
    path, page = draft(client, base)
    assert client.post(path + "/publish", json={"expected_version": 1}).status_code == 200
    history = client.get(path + "/revisions").json()
    assert len(history["items"]) == 1
    with engine.begin() as conn:
        with pytest.raises(DBAPIError):
            conn.execute(text("UPDATE cms_page_revisions SET body='changed'"))
    with patch("app.modules.cms.service.record", side_effect=RuntimeError("synthetic failure")):
        assert (
            client.patch(
                path, json={"expected_version": 2, "title": "No", "body": "No"}
            ).status_code
            == 500
        )
    assert client.get(base + "/" + page["id"]).json()["translations"][0]["version"] == 2
    with Session(engine) as db:
        event = db.scalar(select(AuditLog).where(AuditLog.action == "cms.page.published"))
        assert event.resource_version == 2
        assert event.changed_fields == "state,published_revision_id"


def test_concurrent_publish_and_revoked_permission(cms):
    client, engine, base, _ = cms
    path, _ = draft(client, base)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: client.post(path + "/publish", json={"expected_version": 1}).status_code,
                range(2),
            )
        )
    assert sorted(results) == [200, 409]
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM user_roles"))
    assert client.get(base).status_code == 403


def test_preview_and_public_pagination(cms):
    client, _, base, public = cms
    path, _ = draft(client, base)
    preview = client.get(path + "/preview")
    assert preview.status_code == 200
    assert preview.headers["Cache-Control"] == "no-store"
    assert "noindex" in preview.headers["X-Robots-Tag"]
    assert client.get(public).json()["items"] == []
    assert client.post(path + "/publish", json={"expected_version": 1}).status_code == 200
    assert len(client.get(public + "?limit=1").json()["items"]) == 1
    assert client.get(public + "?locale=xx").status_code == 422


def test_view_only_cannot_publish_and_wrong_object_is_hidden(cms):
    client, engine, base, public = cms
    path, _ = draft(client, base)
    assert client.get(base + "/" + str(uuid4())).status_code == 404
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM role_permissions WHERE permission_code='cms.page.publish'"))
    assert client.post(path + "/publish", json={"expected_version": 1}).status_code == 403
    assert client.get(public).json()["items"] == []
    with engine.begin() as conn:
        conn.execute(text("UPDATE users SET status='suspended'"))
    assert client.get(base).status_code == 401


def test_wrong_translation_pointer_rejected(cms):
    client, engine, base, _ = cms
    path, page = draft(client, base)
    assert client.post(path + "/publish", json={"expected_version": 1}).status_code == 200
    assert (
        client.post(
            base + "/" + page["id"] + "/translations",
            json={"locale": "ta", "title": "Tamil", "body": "Tamil"},
        ).status_code
        == 201
    )
    with engine.begin() as conn:
        with pytest.raises(DBAPIError):
            conn.execute(
                text(
                    "UPDATE cms_page_translations SET state='published', published_revision_id="
                    "(SELECT id FROM cms_page_revisions LIMIT 1) WHERE locale='ta'"
                )
            )


def test_browser_cms_csrf_enforced(request):
    fixture_data = request.getfixturevalue("auth")
    client = fixture_data[0]
    _, tokens, _ = signed_in(fixture_data)
    # A bearer credential cannot be reused as a browser session without the server key.
    response = client.post(
        "/api/v1/cms/organizations/" + str(uuid4()) + "/pages",
        json={"slug": "x", "locale": "en", "title": "X", "body": "X"},
        headers={"X-Browser-Session": tokens["access_token"]},
    )
    assert response.status_code == 403
