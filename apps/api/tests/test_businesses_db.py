import os
from datetime import timedelta

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_identity import account, auth, signed_in  # noqa: F401
from test_lms_db import learning_context

from app.modules.applications.models import Application
from app.modules.businesses.models import BusinessOutcomeSnapshot, BusinessProfileRevision
from app.modules.identity.models import AuditLog, Role, RolePermission, User, UserRole, now
from app.modules.programs.models import Enrollment, Participant

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)

BUSINESS_FIELDS = {
    "name": "Synthetic bakery",
    "sector": "Food",
    "products_services": "Baked goods",
    "stage": "idea",
    "registration_info": None,
    "started_on": None,
    "team_size": 1,
    "investment_band": "under_1l",
    "funding_status": "none",
    "revenue_band": "none",
    "support_needs": "Market research",
    "public_opt_in": False,
}


def participant_context(request):
    context = learning_context(request)
    auth_context, _, org, _, _, _, owner = context
    with Session(auth_context[1]) as db:
        director = db.scalar(select(Role).where(Role.name == "Program Director"))
        assert director is not None
        db.execute(
            delete(UserRole).where(
                UserRole.user_id == owner,
                UserRole.organization_id == org,
                UserRole.role_id == director.id,
            )
        )
        db.commit()
        assert list(
            db.scalars(
                select(Role.name)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.user_id == owner, UserRole.organization_id == org)
            )
        ) == ["Participant"]
    return context


def test_participant_profile_reload_update_preserves_history(request) -> None:
    context, headers, org, _, _, enrollment, owner = participant_context(request)
    client, engine, _, _ = context
    base = f"/api/v1/businesses/organizations/{org}"
    created = client.post(
        base + "/profiles",
        headers=headers,
        json={"enrollment_id": str(enrollment), **BUSINESS_FIELDS},
    )
    assert created.status_code == 201, created.text
    reloaded = client.get(base + "/mine", headers=headers).json()["entries"][0]["profile"]
    assert reloaded == created.json()
    update_url = base + f"/profiles/{reloaded['id']}/update"

    # Read-only response metadata must remain forbidden by the request contract.
    rejected = client.post(
        update_url,
        headers=headers,
        json={**reloaded, "expected_version": reloaded["version"]},
    )
    assert rejected.status_code == 422
    update_data = {
        **{key: reloaded[key] for key in BUSINESS_FIELDS},
        "name": "Reloaded bakery",
        "support_needs": "Equipment finance",
        "team_size": 3,
        "expected_version": reloaded["version"],
    }
    saved = client.post(update_url, headers=headers, json=update_data)
    assert saved.status_code == 200, saved.text
    assert saved.json()["version"] == 2
    assert client.post(update_url, headers=headers, json=update_data).status_code == 409
    persisted = client.get(base + "/mine", headers=headers).json()["entries"][0]["profile"]
    assert persisted == saved.json()
    assert persisted["name"] == "Reloaded bakery"
    assert persisted["support_needs"] == "Equipment finance"
    assert persisted["team_size"] == 3
    assert persisted["follow_ups"] == reloaded["follow_ups"]
    assert [revision["version"] for revision in persisted["revisions"]] == [2, 1]
    assert persisted["revisions"][1]["snapshot"] == BUSINESS_FIELDS
    with Session(engine) as db:
        audit = db.scalar(
            select(AuditLog).where(
                AuditLog.resource_id == reloaded["id"],
                AuditLog.action == "business.profile_updated",
            )
        )
        assert audit is not None
        assert audit.actor_id == owner
        assert audit.resource_version == 2


def test_business_profile_owner_scope_staff_and_withdrawal(request) -> None:
    context, owner_headers, org, other, _, enrollment, _ = participant_context(request)
    client, engine, _, _ = context
    base = f"/api/v1/businesses/organizations/{org}"
    peer_credentials = account(context, "business-peer@example.com")
    staff_credentials = account(context, "business-viewer@example.com")
    with Session(engine) as db:
        peer = db.scalar(select(User).where(User.email == peer_credentials["email"]))
        staff = db.scalar(select(User).where(User.email == staff_credentials["email"]))
        participant = db.scalar(select(Role).where(Role.name == "Participant"))
        assert peer is not None and staff is not None and participant is not None
        viewer = Role(name="Business tracking viewer")
        db.add(viewer)
        db.flush()
        db.add_all(
            [
                RolePermission(role_id=viewer.id, permission_code="system.access"),
                RolePermission(role_id=viewer.id, permission_code="business.track.view"),
                UserRole(user_id=peer.id, role_id=participant.id, organization_id=org),
                UserRole(user_id=staff.id, role_id=viewer.id, organization_id=org),
            ]
        )
        db.commit()
    peer_login = client.post("/api/v1/auth/login", json=peer_credentials)
    staff_login = client.post("/api/v1/auth/login", json=staff_credentials)
    assert peer_login.status_code == staff_login.status_code == 200
    peer_headers = {"Authorization": "Bearer " + peer_login.json()["access_token"]}
    staff_headers = {"Authorization": "Bearer " + staff_login.json()["access_token"]}
    created = client.post(
        base + "/profiles",
        headers=owner_headers,
        json={"enrollment_id": str(enrollment), **BUSINESS_FIELDS},
    )
    assert created.status_code == 201, created.text
    profile = created.json()
    update_url = base + f"/profiles/{profile['id']}/update"
    update_data = {**BUSINESS_FIELDS, "expected_version": profile["version"]}
    outcome_url = base + f"/follow-ups/{profile['follow_ups'][0]['id']}/outcome"
    outcome_data = {
        "reported_on": now().date().isoformat(),
        "business_started": False,
        "business_active": False,
        "jobs_created": 0,
        "funding_band": "none",
        "revenue_band": "none",
    }
    assert client.get(base + "/mine", headers=peer_headers).json()["entries"] == []
    assert client.get(base + "/staff", headers=owner_headers).status_code == 403
    assert client.get(base + "/staff", headers=peer_headers).status_code == 403
    for headers, status in [(peer_headers, 404), (staff_headers, 403)]:
        assert client.post(update_url, headers=headers, json=update_data).status_code == status
        assert client.post(outcome_url, headers=headers, json=outcome_data).status_code == status
        assert (
            client.post(
                base + "/profiles",
                headers=headers,
                json={"enrollment_id": str(enrollment), **BUSINESS_FIELDS},
            ).status_code
            == status
        )
    staff_view = client.get(base + "/staff", headers=staff_headers)
    assert staff_view.status_code == 200
    assert staff_view.json()["profiles"][0]["profile_id"] == profile["id"]
    assert client.get(base + "/mine", headers=staff_headers).status_code == 403
    assert (
        client.post(
            base + "/policy",
            headers=staff_headers,
            json={"expected_version": 0, "day_offsets": [10], "reason": "Denied change"},
        ).status_code
        == 403
    )
    other_base = f"/api/v1/businesses/organizations/{other}"
    assert client.get(other_base + "/staff", headers=staff_headers).status_code == 403
    assert client.get(other_base + "/mine", headers=owner_headers).status_code == 403
    assert (
        client.post(
            other_base + f"/profiles/{profile['id']}/update",
            headers=owner_headers,
            json=update_data,
        ).status_code
        == 404
    )
    with Session(engine) as db:
        db.execute(update(Enrollment).where(Enrollment.id == enrollment).values(status="withdrawn"))
        db.commit()
    assert client.get(base + "/mine", headers=owner_headers).json()["entries"] == []
    assert client.post(update_url, headers=owner_headers, json=update_data).status_code == 404
    assert client.post(outcome_url, headers=owner_headers, json=outcome_data).status_code == 404
    assert (
        client.post(
            base + "/profiles",
            headers=owner_headers,
            json={"enrollment_id": str(enrollment), **BUSINESS_FIELDS},
        ).status_code
        == 404
    )
    assert client.get(base + "/staff", headers=staff_headers).json() == staff_view.json()


def test_profile_policy_followup_and_immutable_snapshots(request) -> None:
    context, headers, org, other, _, enrollment, _ = learning_context(request)
    client, engine, _, _ = context
    base = f"/api/v1/businesses/organizations/{org}"
    assert client.get(base + "/mine", headers=headers).json()["entries"][0]["profile"] is None
    assert (
        client.get(f"/api/v1/businesses/organizations/{other}/mine", headers=headers).status_code
        == 403
    )
    policy = client.post(
        base + "/policy",
        headers=headers,
        json={
            "expected_version": 0,
            "day_offsets": [5, 30],
            "reason": "Program follow-up schedule",
        },
    )
    assert policy.status_code == 200, policy.text
    assert (
        client.post(
            base + "/policy",
            headers=headers,
            json={
                "expected_version": 0,
                "day_offsets": [7],
                "reason": "Stale request",
            },
        ).status_code
        == 409
    )
    fields = {
        "name": "Synthetic bakery",
        "sector": "Food",
        "products_services": "Baked goods",
        "stage": "idea",
        "team_size": 1,
        "investment_band": "under_1l",
        "funding_status": "none",
        "revenue_band": "none",
        "public_opt_in": False,
    }
    created = client.post(
        base + "/profiles", headers=headers, json={"enrollment_id": str(enrollment), **fields}
    )
    assert created.status_code == 201, created.text
    profile = created.json()
    assert [f["offset_days"] for f in profile["follow_ups"]] == [5, 30]
    frozen_followups = profile["follow_ups"]
    revised_policy = client.post(
        base + "/policy",
        headers=headers,
        json={"expected_version": 1, "day_offsets": [7, 45], "reason": "New intake cadence"},
    )
    assert revised_policy.status_code == 200, revised_policy.text
    assert revised_policy.json() == {"version": 2, "day_offsets": [7, 45]}
    assert (
        client.get(base + "/mine", headers=headers).json()["entries"][0]["profile"]["follow_ups"]
        == frozen_followups
    )
    assert (
        client.post(
            base + "/policy",
            headers=headers,
            json={"expected_version": 1, "day_offsets": [9], "reason": "Stale schedule change"},
        ).status_code
        == 409
    )
    # A different enrolled owner receives the new policy while old dates stay frozen.
    peer_credentials = account(context, "business-new-cadence@example.com")
    with Session(engine) as db:
        peer = db.scalar(select(User).where(User.email == peer_credentials["email"]))
        participant_role = db.scalar(select(Role).where(Role.name == "Participant"))
        original_enrollment = db.get(Enrollment, enrollment)
        assert peer and participant_role and original_enrollment
        original_application = db.get(Application, original_enrollment.application_id)
        assert original_application
        participant = Participant(organization_id=org, person_id=peer.person_id, status="active")
        application = Application(
            organization_id=org,
            person_id=peer.person_id,
            form_id=original_application.form_id,
            cycle_id=original_application.cycle_id,
            state="enrolled",
            version=8,
            application_number="EDP-BUSINESS-NEW-CADENCE",
            submitted_at=now() - timedelta(days=20),
        )
        db.add_all([participant, application])
        db.flush()
        peer_enrollment = Enrollment(
            organization_id=org,
            participant_id=participant.id,
            program_id=original_enrollment.program_id,
            cohort_id=original_enrollment.cohort_id,
            application_id=application.id,
            status="active",
        )
        db.add_all(
            [
                peer_enrollment,
                UserRole(user_id=peer.id, role_id=participant_role.id, organization_id=org),
            ]
        )
        db.commit()
        peer_enrollment_id = peer_enrollment.id
    peer_login = client.post("/api/v1/auth/login", json=peer_credentials)
    assert peer_login.status_code == 200
    peer_headers = {"Authorization": "Bearer " + peer_login.json()["access_token"]}
    peer_profile = client.post(
        base + "/profiles",
        headers=peer_headers,
        json={"enrollment_id": str(peer_enrollment_id), **fields},
    )
    assert peer_profile.status_code == 201, peer_profile.text
    assert [f["offset_days"] for f in peer_profile.json()["follow_ups"]] == [7, 45]
    assert [f["due_on"] for f in peer_profile.json()["follow_ups"]] == [
        (now().date() + timedelta(days=offset)).isoformat() for offset in [7, 45]
    ]
    assert (
        client.post(
            base + "/profiles", headers=headers, json={"enrollment_id": str(enrollment), **fields}
        ).status_code
        == 409
    )
    assert (
        client.post(
            base + f"/profiles/{profile['id']}/update",
            headers=headers,
            json={"expected_version": 0, **fields},
        ).status_code
        == 422
    )
    changed = client.post(
        base + f"/profiles/{profile['id']}/update",
        headers=headers,
        json={"expected_version": 1, **{**fields, "name": "New bakery"}},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["version"] == 2
    assert len(changed.json()["revisions"]) == 2
    assert changed.json()["follow_ups"] == frozen_followups
    assert (
        client.post(
            base + f"/profiles/{profile['id']}/update",
            headers=headers,
            json={"expected_version": 1, **fields},
        ).status_code
        == 409
    )
    outcome_url = base + f"/follow-ups/{profile['follow_ups'][0]['id']}/outcome"
    outcome_data = {
        "reported_on": now().date().isoformat(),
        "business_started": True,
        "business_active": True,
        "jobs_created": 2,
        "funding_band": "none",
        "revenue_band": "under_10k",
        "challenges": "Synthetic challenge",
    }
    assert (
        client.post(
            outcome_url,
            headers=headers,
            json={**outcome_data, "reported_on": (now().date() + timedelta(days=1)).isoformat()},
        ).status_code
        == 422
    )
    outcome = client.post(outcome_url, headers=headers, json=outcome_data)
    assert outcome.status_code == 201, outcome.text
    assert client.post(outcome_url, headers=headers, json=outcome_data).status_code == 409
    queue = client.get(base + "/staff", headers=headers)
    assert queue.status_code == 200
    assert (
        next(row for row in queue.json()["profiles"] if row["profile_id"] == profile["id"])[
            "completed_count"
        ]
        == 1
    )
    assert queue.json()["policy"]["day_offsets"] == [7, 45]
    with Session(engine) as db:
        revision = db.scalar(
            select(BusinessProfileRevision).where(
                BusinessProfileRevision.profile_id == profile["id"],
                BusinessProfileRevision.version == 1,
            )
        )
        snapshot = db.scalar(
            select(BusinessOutcomeSnapshot).where(
                BusinessOutcomeSnapshot.id == outcome.json()["id"]
            )
        )
        assert revision and snapshot
        with pytest.raises(DBAPIError):
            db.execute(
                update(BusinessProfileRevision)
                .where(BusinessProfileRevision.id == revision.id)
                .values(snapshot={"name": "tampered"})
            )
        db.rollback()
        with pytest.raises(DBAPIError):
            db.execute(
                update(BusinessOutcomeSnapshot)
                .where(BusinessOutcomeSnapshot.id == snapshot.id)
                .values(jobs_created=999)
            )
        db.rollback()
        for model, row in [
            (BusinessProfileRevision, revision),
            (BusinessOutcomeSnapshot, snapshot),
        ]:
            with pytest.raises(DBAPIError):
                db.execute(delete(model).where(model.id == row.id))
            db.rollback()


@pytest.mark.parametrize("status", ["suspended", "withdrawn"])
def test_business_access_requires_eligible_participant_even_with_active_enrollment(
    request, status
) -> None:
    context, headers, org, _, _, enrollment, _ = participant_context(request)
    client, engine, _, _ = context
    base = f"/api/v1/businesses/organizations/{org}"
    created = client.post(
        base + "/profiles",
        headers=headers,
        json={"enrollment_id": str(enrollment), **BUSINESS_FIELDS},
    )
    assert created.status_code == 201, created.text
    profile = created.json()
    with Session(engine) as db:
        enrollment_row = db.get(Enrollment, enrollment)
        assert enrollment_row and enrollment_row.status == "active"
        db.execute(
            update(Participant)
            .where(Participant.id == enrollment_row.participant_id)
            .values(status=status)
        )
        db.commit()
    assert client.get(base + "/mine", headers=headers).json()["entries"] == []
    assert (
        client.post(
            base + f"/profiles/{profile['id']}/update",
            headers=headers,
            json={**BUSINESS_FIELDS, "expected_version": 1},
        ).status_code
        == 404
    )
    assert (
        client.post(
            base + f"/follow-ups/{profile['follow_ups'][0]['id']}/outcome",
            headers=headers,
            json={
                "reported_on": now().date().isoformat(),
                "business_started": False,
                "business_active": False,
                "jobs_created": 0,
                "funding_band": "none",
                "revenue_band": "none",
            },
        ).status_code
        == 404
    )
