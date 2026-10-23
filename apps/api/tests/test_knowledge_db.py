import os
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, event, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_identity import account, auth, signed_in  # noqa: F401
from test_lms_db import learning_context

from app.modules.applications.models import Application
from app.modules.identity.models import AuditLog, Role, User, UserRole, now
from app.modules.knowledge.models import (
    FundingCase,
    FundingHistory,
    KnowledgeInterest,
    KnowledgeItem,
    KnowledgeRevision,
    KnowledgeSaved,
    KnowledgeTag,
)
from app.modules.programs.models import Enrollment, Participant

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)


def resource(kind="scheme", **overrides):
    return {
        "kind": kind,
        "locale": "en",
        "slug": "synthetic-" + kind,
        "title": "Synthetic " + kind,
        "provider": "Synthetic official provider",
        "type": "Grant" if kind == "funding" else "Development support",
        "description": "Synthetic published description",
        "eligibility": "Official criteria",
        "benefits": "Official support details",
        "sector": "Food",
        "geography": "Tamil Nadu",
        "tags": ["enterprise", "rural"],
        "application_process": "Use the official source",
        "documents": ["Business registration"],
        "official_url": "https://example.org/official",
        "opens_on": None,
        "closes_on": None,
        "last_verified_at": now().date().isoformat(),
        "visibility": "public",
        "contact": "Official contact page",
        "currency": "INR",
        "funding_amount_min": None,
        "funding_amount_max": None,
        **overrides,
    }


def context(request):
    auth_context, owner_headers, org, other, _, enrollment, owner = learning_context(request)
    client, engine, _, _ = auth_context
    staff_credentials = account(auth_context, "knowledge-staff@example.com")
    peer_credentials = account(auth_context, "knowledge-peer@example.com")
    outsider_credentials = account(auth_context, "knowledge-outsider@example.com")
    with Session(engine) as db:
        director = db.scalar(select(Role).where(Role.name == "Program Director"))
        staff_role = db.scalar(select(Role).where(Role.name == "Funding Coordinator"))
        participant_role = db.scalar(select(Role).where(Role.name == "Participant"))
        staff = db.scalar(select(User).where(User.email == staff_credentials["email"]))
        peer = db.scalar(select(User).where(User.email == peer_credentials["email"]))
        outsider = db.scalar(select(User).where(User.email == outsider_credentials["email"]))
        assert director and staff_role and participant_role and staff and peer and outsider
        db.execute(
            delete(UserRole).where(UserRole.user_id == owner, UserRole.role_id == director.id)
        )
        db.add_all(
            [
                UserRole(user_id=staff.id, role_id=staff_role.id, organization_id=org),
                UserRole(user_id=peer.id, role_id=participant_role.id, organization_id=org),
                UserRole(user_id=outsider.id, role_id=participant_role.id, organization_id=org),
            ]
        )
        original = db.get(Enrollment, enrollment)
        assert original
        application = db.get(Application, original.application_id)
        assert application
        peer_application = Application(
            organization_id=org,
            person_id=peer.person_id,
            form_id=application.form_id,
            cycle_id=application.cycle_id,
            state="enrolled",
            version=8,
            application_number="EDP-K01-PEER",
            submitted_at=now(),
        )
        peer_participant = Participant(
            organization_id=org, person_id=peer.person_id, status="active"
        )
        db.add_all([peer_application, peer_participant])
        db.flush()
        db.add(
            Enrollment(
                organization_id=org,
                participant_id=peer_participant.id,
                program_id=original.program_id,
                cohort_id=original.cohort_id,
                application_id=peer_application.id,
                status="active",
            )
        )
        db.commit()
    logins = [
        client.post("/api/v1/auth/login", json=credentials)
        for credentials in (staff_credentials, peer_credentials, outsider_credentials)
    ]
    assert all(login.status_code == 200 for login in logins)
    headers = [{"Authorization": "Bearer " + login.json()["access_token"]} for login in logins]
    return client, engine, org, other, enrollment, owner_headers, *headers


def publish(client, base, headers, fields):
    created = client.post(base + "/items", headers=headers, json=fields)
    assert created.status_code == 201, created.text
    published = client.post(
        base + f"/items/{created.json()['id']}/publish",
        headers=headers,
        json={"expected_version": 1, "reason": "Verified against official source"},
    )
    assert published.status_code == 200, published.text
    return published.json()


def test_editorial_lifecycle_bilingual_filters_validation_and_history(request):
    client, engine, org, other, _, owner, staff, _, _ = context(request)
    base = f"/api/v1/knowledge/organizations/{org}"
    public = f"/api/v1/public/organizations/{org}/knowledge"
    fields = resource()
    bad_values = [
        {"official_url": "javascript:alert(1)"},
        {"official_url": "https://user:pass@example.org"},
        {"official_url": "https://bad host/path"},
        {"official_url": "https://example.org:bad"},
        {"last_verified_at": (now().date() + timedelta(days=1)).isoformat()},
        {"opens_on": "2026-02-02", "closes_on": "2026-02-01"},
        {"funding_amount_min": "2"},
        {"documents": [""]},
        {"tags": ["x"] * 21},
    ]
    for invalid in bad_values:
        assert (
            client.post(base + "/items", headers=staff, json={**fields, **invalid}).status_code
            == 422
        )
    assert (
        client.post(
            base + "/items",
            headers=staff,
            json=resource("funding", funding_amount_min="200", funding_amount_max="100"),
        ).status_code
        == 422
    )
    draft = client.post(base + "/items", headers=staff, json=fields)
    assert draft.status_code == 201, draft.text
    row = draft.json()
    assert client.get(public).json()["items"] == []
    assert client.get(public + f"/{row['id']}").status_code == 404
    edited = client.patch(
        base + f"/items/{row['id']}",
        headers=staff,
        json={
            **fields,
            "title": "Updated synthetic scheme",
            "tags": ["updated"],
            "expected_version": 1,
            "reason": "Official source changed",
        },
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["version"] == 2 and edited.json()["tags"] == ["updated"]
    assert (
        client.patch(
            base + f"/items/{row['id']}",
            headers=staff,
            json={**fields, "expected_version": 1, "reason": "Stale edit"},
        ).status_code
        == 409
    )
    command = {"expected_version": 2, "reason": "Publish verified content"}
    live = client.post(base + f"/items/{row['id']}/publish", headers=staff, json=command)
    assert live.status_code == 200, live.text
    assert (
        client.patch(
            base + f"/items/{row['id']}",
            headers=staff,
            json={**fields, "expected_version": 3, "reason": "No direct live edits"},
        ).status_code
        == 409
    )
    tamil = publish(client, base, staff, resource(locale="ta", title="தமிழ் திட்டம்"))
    private = publish(client, base, staff, resource(slug="private", visibility="participants"))
    expired = publish(
        client,
        base,
        staff,
        resource(slug="expired", closes_on=(now().date() - timedelta(days=1)).isoformat()),
    )
    upcoming = publish(
        client,
        base,
        staff,
        resource(slug="upcoming", opens_on=(now().date() + timedelta(days=1)).isoformat()),
    )
    statements = []

    def record_statement(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(Engine, "before_cursor_execute", record_statement)
    try:
        assert len(client.get(public).json()["items"]) == 2
    finally:
        event.remove(Engine, "before_cursor_execute", record_statement)
    # Catalog reads remain constant as a page grows: resources plus one batched tag query.
    assert len(statements) == 2
    assert client.get(public, params={"locale": "ta"}).json()["items"][0]["id"] == tamil["id"]
    assert client.get(public + f"/{private['id']}").status_code == 404
    assert client.get(base + "/catalog/" + private["id"], headers=owner).status_code == 200
    assert (
        client.get(public, params={"availability": "closed"}).json()["items"][0]["id"]
        == expired["id"]
    )
    assert (
        client.get(public, params={"availability": "upcoming"}).json()["items"][0]["id"]
        == upcoming["id"]
    )
    filtered = client.get(
        public,
        params={"q": "Updated", "sector": "Food", "geography": "Tamil Nadu", "tag": "updated"},
    )
    assert [entry["id"] for entry in filtered.json()["items"]] == [row["id"]]
    assert client.get(public, params={"q": "%"}).json()["items"] == []
    page = client.get(public, params={"limit": 1}).json()
    assert page["next_cursor"] is not None
    assert (
        client.get(public, params={"cursor": page["next_cursor"], "limit": 1}).json()["items"][0][
            "id"
        ]
        != page["items"][0]["id"]
    )
    assert client.get(public, params={"limit": 101}).status_code == 422
    assert client.get(f"/api/v1/public/organizations/{other}/knowledge").json()["items"] == []
    assert (
        client.get(f"/api/v1/public/organizations/{other}/knowledge/{row['id']}").status_code == 404
    )
    history = client.get(base + f"/items/{row['id']}/history", headers=staff).json()["items"]
    assert sorted(entry["version"] for entry in history) == [1, 2, 3]
    assert {entry["action"] for entry in history} == {"created", "updated", "published"}
    first_history = client.get(
        base + f"/items/{row['id']}/history", headers=staff, params={"limit": 1}
    ).json()
    assert first_history["items"][0]["version"] == 1
    next_history = client.get(
        base + f"/items/{row['id']}/history",
        headers=staff,
        params={"cursor": first_history["next_cursor"], "limit": 1},
    ).json()
    assert next_history["items"][0]["version"] == 2
    assert (
        client.get(
            base + f"/items/{row['id']}/history", headers=staff, params={"cursor": str(uuid4())}
        ).status_code
        == 422
    )
    assert (
        client.post(
            base + f"/items/{row['id']}/archive",
            headers=staff,
            json={"expected_version": 3, "reason": " "},
        ).status_code
        == 422
    )
    archived = client.post(
        base + f"/items/{row['id']}/archive",
        headers=staff,
        json={"expected_version": 3, "reason": "Source withdrawn"},
    )
    assert archived.status_code == 200
    assert client.get(public + f"/{row['id']}").status_code == 404
    restored = client.post(
        base + f"/items/{row['id']}/draft",
        headers=staff,
        json={"expected_version": 4, "reason": "Prepare verified replacement"},
    )
    assert restored.status_code == 200 and restored.json()["state"] == "draft"
    with Session(engine) as db:
        audit = list(db.scalars(select(AuditLog).where(AuditLog.action.like("knowledge.%"))))
        assert audit and all(entry.reason is None for entry in audit)
        assert all(
            "Synthetic published description" not in (entry.changed_fields or "") for entry in audit
        )
        updated = next(entry for entry in audit if entry.action == "knowledge.updated")
        assert set(updated.changed_fields.split(",")) == {"version", "title", "tags"}


def test_saved_interest_case_idempotency_availability_source_and_scope(request):
    client, engine, org, other, enrollment, owner, staff, peer, outsider = context(request)
    base = f"/api/v1/knowledge/organizations/{org}"
    scheme = publish(client, base, staff, resource())
    opportunity = publish(client, base, staff, resource("opportunity"))
    funding = publish(
        client,
        base,
        staff,
        resource(
            "funding",
            visibility="participants",
            funding_amount_min="10000.00",
            funding_amount_max="50000.00",
        ),
    )
    closed = publish(
        client,
        base,
        staff,
        resource(
            "funding", slug="closed", closes_on=(now().date() - timedelta(days=1)).isoformat()
        ),
    )
    closed_opportunity = publish(
        client,
        base,
        staff,
        resource(
            "opportunity",
            slug="closed-event",
            closes_on=(now().date() - timedelta(days=1)).isoformat(),
        ),
    )
    assert (
        client.post(base + f"/interests/{closed_opportunity['id']}", headers=owner).status_code
        == 409
    )
    for headers in (owner, peer):
        assert client.get(base + "/funding-cases", headers=headers).status_code == 403
        assert client.get(base + "/items", headers=headers).status_code == 403
    assert client.get(base + "/catalog", headers=outsider).status_code == 403
    assert client.get(base + "/catalog", headers=staff).status_code == 403
    assert client.get(base + "/mine", headers=staff).status_code == 403
    assert (
        client.get(f"/api/v1/knowledge/organizations/{other}/catalog", headers=owner).status_code
        == 403
    )
    assert client.post(base + f"/saved/{scheme['id']}", headers=owner).status_code == 200
    assert client.post(base + f"/saved/{scheme['id']}", headers=owner).status_code == 200
    assert client.post(base + f"/saved/{opportunity['id']}", headers=owner).status_code == 200
    assert client.post(base + f"/interests/{scheme['id']}", headers=owner).status_code == 422
    interests = [
        client.post(base + f"/interests/{opportunity['id']}", headers=owner) for _ in range(2)
    ]
    assert interests[0].status_code == interests[1].status_code == 201
    assert interests[0].json() == interests[1].json()
    assert (
        client.post(
            base + "/funding-cases", headers=owner, json={"item_id": closed["id"]}
        ).status_code
        == 409
    )
    created = client.post(base + "/funding-cases", headers=owner, json={"item_id": funding["id"]})
    assert created.status_code == 201, created.text
    case = created.json()
    assert (
        client.post(base + "/funding-cases", headers=owner, json={"item_id": funding["id"]}).json()
        == case
    )
    assert case["source"]["funding_amount_min"] == "10000.00"
    assert len(case["history"]) == 1
    status_url = base + f"/funding-cases/{case['id']}/status"
    command = {
        "expected_version": 1,
        "status": "eligibility_check",
        "reason": "Self-reported check",
    }
    assert client.post(status_url, headers=peer, json=command).status_code == 404
    assert client.post(status_url, headers=staff, json=command).status_code == 403
    assert client.get(base + "/mine", headers=peer).json()["funding_cases"] == []
    page = client.get(base + "/mine", headers=owner, params={"limit": 1}).json()
    assert page["next_saved_cursor"]
    second_page = client.get(
        base + "/mine",
        headers=owner,
        params={"limit": 1, "saved_cursor": page["next_saved_cursor"]},
    ).json()
    assert second_page["saved_items"][0]["item_id"] != page["saved_items"][0]["item_id"]
    assert (
        client.get(base + "/funding-cases", headers=staff, params={"limit": 101}).status_code == 422
    )
    assert (
        client.get(
            f"/api/v1/knowledge/organizations/{other}/funding-cases", headers=staff
        ).status_code
        == 403
    )
    assert client.get(base + "/funding-cases", headers=staff).json()["items"][0]["id"] == case["id"]
    for resource_row in (scheme, funding):
        archived = client.post(
            base + f"/items/{resource_row['id']}/archive",
            headers=staff,
            json={"expected_version": 2, "reason": "Official source expired"},
        )
        assert archived.status_code == 200, archived.text
    mine = client.get(base + "/mine", headers=owner).json()
    assert (
        next(entry for entry in mine["saved_items"] if entry["item_id"] == scheme["id"])["item"]
        is None
    )
    assert mine["funding_cases"][0]["source"] == case["source"]
    assert client.post(base + f"/saved/{scheme['id']}", headers=owner).status_code == 404
    assert client.delete(base + f"/saved/{scheme['id']}", headers=peer).status_code == 204
    assert len(client.get(base + "/mine", headers=owner).json()["saved_items"]) == 2
    assert client.delete(base + f"/saved/{scheme['id']}", headers=owner).status_code == 204
    assert client.delete(base + f"/saved/{scheme['id']}", headers=owner).status_code == 204
    assert client.post(status_url, headers=owner, json=command).status_code == 200
    with Session(engine) as db:
        db.execute(update(Enrollment).where(Enrollment.id == enrollment).values(status="withdrawn"))
        db.commit()
    assert client.get(base + "/mine", headers=owner).status_code == 403
    assert client.get(base + "/funding-cases", headers=staff).status_code == 200


@pytest.mark.parametrize("decision", ["approved", "rejected"])
def test_funding_strict_progression_conflicts_and_immutable_evidence(request, decision):
    client, engine, org, other, _, owner, staff, _, _ = context(request)
    base = f"/api/v1/knowledge/organizations/{org}"
    funding = publish(client, base, staff, resource("funding"))
    opportunity = publish(client, base, staff, resource("opportunity"))
    client.post(base + f"/interests/{opportunity['id']}", headers=owner)
    case = client.post(
        base + "/funding-cases", headers=owner, json={"item_id": funding["id"]}
    ).json()
    status_url = base + f"/funding-cases/{case['id']}/status"
    assert (
        client.post(
            status_url,
            headers=owner,
            json={"expected_version": 1, "status": "applied", "reason": "Must not skip steps"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            status_url,
            headers=owner,
            json={"expected_version": 1, "status": "eligibility_check", "reason": " "},
        ).status_code
        == 422
    )
    statuses = ["eligibility_check", "document_preparation", "applied", "under_review", decision]
    for index, status in enumerate(statuses, 1):
        data = {"expected_version": index, "status": status, "reason": "Self-reported " + status}
        response = client.post(status_url, headers=owner, json=data)
        assert response.status_code == 200, response.text
        assert response.json()["version"] == index + 1
        assert len(response.json()["history"]) == index + 1
        assert client.post(status_url, headers=owner, json=data).status_code == 409
    final = client.post(
        status_url,
        headers=owner,
        json={"expected_version": 6, "status": "disbursed", "reason": "Self-reported receipt"},
    )
    assert final.status_code == (200 if decision == "approved" else 409)
    persisted = client.get(base + "/mine", headers=owner).json()["funding_cases"][0]
    assert persisted["status"] == ("disbursed" if decision == "approved" else "rejected")
    with Session(engine) as db:
        row = db.get(FundingCase, UUID(case["id"]))
        assert row
        for statement in [
            update(FundingCase).where(FundingCase.id == row.id).values(source={}),
            update(FundingCase)
            .where(FundingCase.id == row.id)
            .values(status="approved", version=row.version + 1),
            delete(FundingCase).where(FundingCase.id == row.id),
            update(FundingHistory).where(FundingHistory.case_id == row.id).values(reason="Tamper"),
            delete(FundingHistory).where(FundingHistory.case_id == row.id),
            update(KnowledgeRevision)
            .where(KnowledgeRevision.item_id == UUID(funding["id"]))
            .values(reason="Tamper"),
            delete(KnowledgeRevision).where(KnowledgeRevision.item_id == UUID(funding["id"])),
            delete(KnowledgeInterest),
            update(KnowledgeInterest).values(item_title="Tamper"),
            update(KnowledgeItem)
            .where(KnowledgeItem.id == UUID(funding["id"]))
            .values(title="Tamper", version=3),
            update(KnowledgeTag)
            .where(KnowledgeTag.item_id == UUID(funding["id"]))
            .values(item_id=uuid4()),
        ]:
            with pytest.raises(DBAPIError):
                db.execute(statement)
                db.commit()
            db.rollback()
        db.add(
            KnowledgeSaved(
                organization_id=other,
                participant_id=row.participant_id,
                item_id=UUID(funding["id"]),
            )
        )
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()
        audits = list(
            db.scalars(select(AuditLog).where(AuditLog.action == "funding.status_changed"))
        )
        assert len(audits) == (6 if decision == "approved" else 5)
        assert all(
            entry.changed_fields == "status,version" and entry.reason is None for entry in audits
        )
