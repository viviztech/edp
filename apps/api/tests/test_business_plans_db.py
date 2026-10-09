import os
from datetime import date

import pytest
from sqlalchemy import select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_identity import auth, signed_in  # noqa: F401
from test_lms_db import learning_context

from app.modules.business_plans.models import BusinessPlanRevision, BusinessPlanSubmission
from app.modules.business_plans.service import SECTION_CODES
from app.modules.identity.models import AuditLog, Role, UserRole

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)


def test_owner_draft_revision_conflict_and_db_immutability(request) -> None:
    auth_context, headers, org_id, other_id, _, enrollment_id, user_id = learning_context(request)
    client, engine, _, _ = auth_context
    root = f"/api/v1/business-plans/organizations/{org_id}"
    entry_url = root + f"/enrollments/{enrollment_id}"

    assert client.get(root + "/mine", headers=headers).json()["entries"][0]["plan"] is None
    assert client.get(
        f"/api/v1/business-plans/organizations/{other_id}/mine", headers=headers
    ).status_code == 403
    created = client.post(entry_url, headers=headers)
    assert created.status_code == 201
    assert created.json()["version"] == 1
    assert client.post(entry_url, headers=headers).status_code == 409

    saved = client.post(entry_url + "/sections", headers=headers, json={
        "expected_version": 1,
        "section_code": "problem",
        "body": "  Customers lack reliable access.  ",
    })
    assert saved.status_code == 200
    assert saved.json()["sections"]["problem"] == "Customers lack reliable access."
    assert saved.json()["completed_sections"] == 1
    assert saved.json()["version"] == 2
    assert client.post(entry_url + "/sections", headers=headers, json={
        "expected_version": 1, "section_code": "solution", "body": "A service model",
    }).status_code == 409
    assert client.post(entry_url + "/sections", headers=headers, json={
        "expected_version": 2, "section_code": "unknown", "body": "Invalid",
    }).status_code == 422

    blank = client.post(entry_url + "/sections", headers=headers, json={
        "expected_version": 2, "section_code": "problem", "body": "",
    })
    assert blank.status_code == 200
    assert blank.json()["completed_sections"] == 0
    assert len(blank.json()["revisions"]) == 2

    with Session(engine) as db:
        revision = db.scalar(select(BusinessPlanRevision).where(
            BusinessPlanRevision.plan_id == created.json()["id"],
            BusinessPlanRevision.version == 2,
        ))
        assert revision is not None
        audit = db.scalar(select(AuditLog).where(
            AuditLog.resource_id == created.json()["id"],
            AuditLog.action == "business_plan.section_saved",
        ))
        assert audit is not None
        assert "Customers" not in (audit.changed_fields or "")
        with pytest.raises(DBAPIError):
            db.execute(update(BusinessPlanRevision).where(
                BusinessPlanRevision.id == revision.id
            ).values(body="tampered"))
        db.rollback()
        with pytest.raises(DBAPIError):
            db.execute(
                text("DELETE FROM business_plan_revisions WHERE id = :id"),
                {"id": revision.id},
            )
        db.rollback()

    incomplete = client.post(entry_url + "/submit", headers=headers, json={
        "expected_version": blank.json()["version"],
    })
    assert incomplete.status_code == 422
    version = blank.json()["version"]
    for code in SECTION_CODES:
        response = client.post(entry_url + "/sections", headers=headers, json={
            "expected_version": version,
            "section_code": code,
            "body": f"Synthetic planning text for {code}.",
        })
        assert response.status_code == 200
        version = response.json()["version"]
    submitted = client.post(entry_url + "/submit", headers=headers, json={
        "expected_version": version,
    })
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "submitted"
    assert submitted.json()["submissions"][0]["number"] == 1
    assert submitted.json()["submissions"][0]["snapshot"]["problem"]
    assert client.post(entry_url + "/sections", headers=headers, json={
        "expected_version": submitted.json()["version"],
        "section_code": "problem", "body": "Changed after submission",
    }).status_code == 409
    with Session(engine) as db:
        snapshot = db.scalar(select(BusinessPlanSubmission).where(
            BusinessPlanSubmission.plan_id == created.json()["id"]
        ))
        assert snapshot is not None
        with pytest.raises(DBAPIError):
            db.execute(update(BusinessPlanSubmission).where(
                BusinessPlanSubmission.id == snapshot.id
            ).values(snapshot={"problem": "tampered"}))
        db.rollback()

    with Session(engine) as db:
        mentor_role = db.scalar(select(Role).where(Role.name == "Mentor"))
        assert mentor_role is not None
        db.add(UserRole(user_id=user_id, role_id=mentor_role.id, organization_id=org_id))
        db.commit()
    mentoring_root = f"/api/v1/mentoring/organizations/{org_id}"
    profile = client.post(mentoring_root + "/profiles", headers=headers, json={
        "user_id": str(user_id), "headline": "Synthetic mentor",
    })
    assert profile.status_code == 201
    assignment = client.post(mentoring_root + "/assignments", headers=headers, json={
        "mentor_profile_id": profile.json()["id"],
        "enrollment_id": str(enrollment_id),
        "starts_on": date.today().isoformat(),
        "reason": "Synthetic review assignment",
    })
    assert assignment.status_code == 201
    queue = client.get(root + "/assigned", headers=headers)
    assert queue.status_code == 200
    assert queue.json()["submissions"][0]["id"] == submitted.json()["submissions"][0]["id"]
    review_url = root + f"/submissions/{submitted.json()['submissions'][0]['id']}/review"
    review = client.post(review_url, headers=headers, json={
        "expected_version": submitted.json()["version"],
        "decision": "changes_requested",
        "reason": "Clarify the customer evidence",
        "comments": {"problem": "Add interview findings."},
    })
    assert review.status_code == 200
    assert review.json()["comments"]["problem"] == "Add interview findings."
    assert client.post(review_url, headers=headers, json={
        "expected_version": submitted.json()["version"],
        "decision": "approved", "reason": "Duplicate review",
    }).status_code == 409
    current = client.get(root + "/mine", headers=headers).json()["entries"][0]["plan"]
    assert current["status"] == "changes_requested"
    assert current["submissions"][0]["review"]["decision"] == "changes_requested"
