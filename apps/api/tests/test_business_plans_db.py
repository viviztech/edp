import os
from datetime import date

import pytest
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_identity import account, auth, signed_in  # noqa: F401
from test_lms_db import learning_context

from app.modules.business_plans.models import (
    BusinessPlanReview,
    BusinessPlanRevision,
    BusinessPlanSubmission,
)
from app.modules.business_plans.service import SECTION_CODES
from app.modules.identity.models import AuditLog, Role, User, UserRole
from app.modules.mentoring.models import MentorAssignment, MentorProfile
from app.modules.programs.models import Enrollment

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)


def test_owner_draft_revision_conflict_and_db_immutability(request) -> None:
    auth_context, headers, org_id, other_id, _, enrollment_id, user_id = learning_context(request)
    client, engine, _, _ = auth_context
    root = f"/api/v1/business-plans/organizations/{org_id}"
    entry_url = root + f"/enrollments/{enrollment_id}"

    assert client.get(root + "/mine", headers=headers).json()["entries"][0]["plan"] is None
    assert (
        client.get(
            f"/api/v1/business-plans/organizations/{other_id}/mine", headers=headers
        ).status_code
        == 403
    )
    created = client.post(entry_url, headers=headers)
    assert created.status_code == 201
    assert created.json()["version"] == 1
    assert client.post(entry_url, headers=headers).status_code == 409

    saved = client.post(
        entry_url + "/sections",
        headers=headers,
        json={
            "expected_version": 1,
            "section_code": "problem",
            "body": "  Customers lack reliable access.  ",
        },
    )
    assert saved.status_code == 200
    assert saved.json()["sections"]["problem"] == "Customers lack reliable access."
    assert saved.json()["completed_sections"] == 1
    assert saved.json()["version"] == 2
    assert (
        client.post(
            entry_url + "/sections",
            headers=headers,
            json={
                "expected_version": 1,
                "section_code": "solution",
                "body": "A service model",
            },
        ).status_code
        == 409
    )
    assert (
        client.post(
            entry_url + "/sections",
            headers=headers,
            json={
                "expected_version": 2,
                "section_code": "unknown",
                "body": "Invalid",
            },
        ).status_code
        == 422
    )

    blank = client.post(
        entry_url + "/sections",
        headers=headers,
        json={
            "expected_version": 2,
            "section_code": "problem",
            "body": "",
        },
    )
    assert blank.status_code == 200
    assert blank.json()["completed_sections"] == 0
    assert len(blank.json()["revisions"]) == 2

    with Session(engine) as db:
        revision = db.scalar(
            select(BusinessPlanRevision).where(
                BusinessPlanRevision.plan_id == created.json()["id"],
                BusinessPlanRevision.version == 2,
            )
        )
        assert revision is not None
        audit = db.scalar(
            select(AuditLog).where(
                AuditLog.resource_id == created.json()["id"],
                AuditLog.action == "business_plan.section_saved",
            )
        )
        assert audit is not None
        assert "Customers" not in (audit.changed_fields or "")
        with pytest.raises(DBAPIError):
            db.execute(
                update(BusinessPlanRevision)
                .where(BusinessPlanRevision.id == revision.id)
                .values(body="tampered")
            )
        db.rollback()
        with pytest.raises(DBAPIError):
            db.execute(
                text("DELETE FROM business_plan_revisions WHERE id = :id"),
                {"id": revision.id},
            )
        db.rollback()

    incomplete = client.post(
        entry_url + "/submit",
        headers=headers,
        json={
            "expected_version": blank.json()["version"],
        },
    )
    assert incomplete.status_code == 422
    version = blank.json()["version"]
    for code in SECTION_CODES:
        response = client.post(
            entry_url + "/sections",
            headers=headers,
            json={
                "expected_version": version,
                "section_code": code,
                "body": f"Synthetic planning text for {code}.",
            },
        )
        assert response.status_code == 200
        version = response.json()["version"]
    submitted = client.post(
        entry_url + "/submit",
        headers=headers,
        json={
            "expected_version": version,
        },
    )
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "submitted"
    assert submitted.json()["submissions"][0]["number"] == 1
    assert submitted.json()["submissions"][0]["snapshot"]["problem"]
    assert (
        client.post(
            entry_url + "/sections",
            headers=headers,
            json={
                "expected_version": submitted.json()["version"],
                "section_code": "problem",
                "body": "Changed after submission",
            },
        ).status_code
        == 409
    )
    with Session(engine) as db:
        snapshot = db.scalar(
            select(BusinessPlanSubmission).where(
                BusinessPlanSubmission.plan_id == created.json()["id"]
            )
        )
        assert snapshot is not None
        with pytest.raises(DBAPIError):
            db.execute(
                update(BusinessPlanSubmission)
                .where(BusinessPlanSubmission.id == snapshot.id)
                .values(snapshot={"problem": "tampered"})
            )
        db.rollback()

    with Session(engine) as db:
        mentor_role = db.scalar(select(Role).where(Role.name == "Mentor"))
        assert mentor_role is not None
        db.add(UserRole(user_id=user_id, role_id=mentor_role.id, organization_id=org_id))
        db.commit()
    mentoring_root = f"/api/v1/mentoring/organizations/{org_id}"
    profile = client.post(
        mentoring_root + "/profiles",
        headers=headers,
        json={
            "user_id": str(user_id),
            "headline": "Synthetic mentor",
        },
    )
    assert profile.status_code == 201
    assignment = client.post(
        mentoring_root + "/assignments",
        headers=headers,
        json={
            "mentor_profile_id": profile.json()["id"],
            "enrollment_id": str(enrollment_id),
            "starts_on": date.today().isoformat(),
            "reason": "Synthetic review assignment",
        },
    )
    assert assignment.status_code == 201
    queue = client.get(root + "/assigned", headers=headers)
    assert queue.status_code == 200
    assert queue.json()["submissions"][0]["id"] == submitted.json()["submissions"][0]["id"]
    review_url = root + f"/submissions/{submitted.json()['submissions'][0]['id']}/review"
    review = client.post(
        review_url,
        headers=headers,
        json={
            "expected_version": submitted.json()["version"],
            "decision": "changes_requested",
            "reason": "Clarify the customer evidence",
            "comments": {"problem": "Add interview findings."},
        },
    )
    assert review.status_code == 200
    assert review.json()["comments"]["problem"] == "Add interview findings."
    assert (
        client.post(
            review_url,
            headers=headers,
            json={
                "expected_version": submitted.json()["version"],
                "decision": "approved",
                "reason": "Duplicate review",
            },
        ).status_code
        == 409
    )
    current = client.get(root + "/mine", headers=headers).json()["entries"][0]["plan"]
    assert current["status"] == "changes_requested"
    assert current["submissions"][0]["review"]["decision"] == "changes_requested"


def test_separate_owner_mentor_revision_approval_scope_and_immutable_evidence(request) -> None:
    context, owner_headers, org, other, _, enrollment, owner = learning_context(request)
    client, engine, _, _ = context
    credentials = {
        name: account(context, f"b01-{name}@example.com")
        for name in ("mentor", "unassigned", "peer", "staff")
    }
    actors = {}
    with Session(engine) as db:
        roles = {role.name: role for role in db.scalars(select(Role))}
        db.execute(
            delete(UserRole).where(
                UserRole.user_id == owner,
                UserRole.organization_id == org,
                UserRole.role_id == roles["Program Director"].id,
            )
        )
        db.add(UserRole(user_id=owner, role_id=roles["Participant"].id, organization_id=other))
        for name, role in (
            ("mentor", "Mentor"),
            ("unassigned", "Mentor"),
            ("peer", "Participant"),
            ("staff", "Program Director"),
        ):
            actor = db.scalar(select(User).where(User.email == credentials[name]["email"]))
            assert actor is not None
            actors[name] = actor.id
            db.add(UserRole(user_id=actor.id, role_id=roles[role].id, organization_id=org))
        db.add(
            UserRole(user_id=actors["mentor"], role_id=roles["Mentor"].id, organization_id=other)
        )
        profile = MentorProfile(
            organization_id=org,
            user_id=actors["mentor"],
            headline="Synthetic assigned mentor",
        )
        db.add(profile)
        db.flush()
        assignment = MentorAssignment(
            organization_id=org,
            mentor_profile_id=profile.id,
            enrollment_id=enrollment,
            starts_on=date.today(),
            assigned_by_user_id=actors["staff"],
        )
        db.add(assignment)
        db.commit()
        assignment_id, profile_id = assignment.id, profile.id
        for name, actor in {"owner": owner, **actors}.items():
            actual = list(
                db.scalars(
                    select(Role.name)
                    .join(UserRole, UserRole.role_id == Role.id)
                    .where(UserRole.user_id == actor, UserRole.organization_id == org)
                )
            )
            assert actual == [
                {
                    "owner": "Participant",
                    "mentor": "Mentor",
                    "unassigned": "Mentor",
                    "peer": "Participant",
                    "staff": "Program Director",
                }[name]
            ]
    headers = {}
    for name, login in credentials.items():
        response = client.post("/api/v1/auth/login", json=login)
        assert response.status_code == 200
        headers[name] = {"Authorization": "Bearer " + response.json()["access_token"]}

    root = f"/api/v1/business-plans/organizations/{org}"
    other_root = f"/api/v1/business-plans/organizations/{other}"
    entry = root + f"/enrollments/{enrollment}"
    expected_audits = []

    def accepted(response, action, actor, version, changed, status=200):
        assert response.status_code == status, response.text
        expected_audits.append((version, action, actor, changed, response.headers["x-request-id"]))
        return response.json()

    def current_plan():
        response = client.get(root + "/mine", headers=owner_headers)
        assert response.status_code == 200
        return response.json()["entries"][0]["plan"]

    # Roles never substitute for owning an active enrollment, including privileged staff.
    for name, status in (("peer", 404), ("mentor", 403), ("staff", 403)):
        assert client.post(entry, headers=headers[name]).status_code == status
    assert client.get(root + "/mine", headers=headers["peer"]).json()["entries"] == []
    for name in ("mentor", "staff"):
        assert client.get(root + "/mine", headers=headers[name]).status_code == 403
    plan = accepted(
        client.post(entry, headers=owner_headers),
        "business_plan.created",
        owner,
        1,
        "enrollment_id",
        201,
    )
    plan_id = plan["id"]
    for name, status in (("peer", 404), ("mentor", 403), ("staff", 403)):
        assert (
            client.post(
                entry + "/sections",
                headers=headers[name],
                json={"expected_version": 1, "section_code": "problem", "body": "Denied"},
            ).status_code
            == status
        )
        assert (
            client.post(
                entry + "/submit", headers=headers[name], json={"expected_version": 1}
            ).status_code
            == status
        )
    assert client.get(other_root + "/mine", headers=owner_headers).json()["entries"] == []
    other_entry = other_root + f"/enrollments/{enrollment}"
    assert client.post(other_entry, headers=owner_headers).status_code == 404
    assert (
        client.post(
            other_entry + "/sections",
            headers=owner_headers,
            json={"expected_version": 1, "section_code": "problem", "body": "Denied"},
        ).status_code
        == 404
    )
    assert (
        client.post(
            other_entry + "/submit", headers=owner_headers, json={"expected_version": 1}
        ).status_code
        == 404
    )
    with Session(engine) as db:
        db.execute(update(Enrollment).where(Enrollment.id == enrollment).values(status="withdrawn"))
        db.commit()
    assert client.get(root + "/mine", headers=owner_headers).json()["entries"] == []
    assert client.post(entry, headers=owner_headers).status_code == 404
    assert (
        client.post(
            entry + "/sections",
            headers=owner_headers,
            json={"expected_version": 1, "section_code": "problem", "body": "Denied"},
        ).status_code
        == 404
    )
    assert (
        client.post(
            entry + "/submit", headers=owner_headers, json={"expected_version": 1}
        ).status_code
        == 404
    )
    with Session(engine) as db:
        db.execute(update(Enrollment).where(Enrollment.id == enrollment).values(status="active"))
        db.commit()
    assert current_plan() == plan
    assert client.get(root + "/assigned", headers=headers["mentor"]).json() == {"submissions": []}

    original = {code: f"B01 confidential original {code}." for code in SECTION_CODES}
    for version, (code, body) in enumerate(original.items(), start=2):
        plan = accepted(
            client.post(
                entry + "/sections",
                headers=owner_headers,
                json={"expected_version": version - 1, "section_code": code, "body": body},
            ),
            "business_plan.section_saved",
            owner,
            version,
            code,
        )
    assert plan["completed_sections"] == plan["total_sections"] == 20
    plan = accepted(
        client.post(entry + "/submit", headers=owner_headers, json={"expected_version": 21}),
        "business_plan.submitted",
        owner,
        22,
        "status,submission_number",
    )
    assert plan["status"] == "submitted"
    first = plan["submissions"][0]
    assert first["number"] == 1 and first["snapshot"] == original and first["review"] is None
    review_url = root + f"/submissions/{first['id']}/review"
    reason = "B01 confidential customer evidence needed."
    comment = "B01 confidential interview findings."
    review_data = {
        "expected_version": 22,
        "decision": "changes_requested",
        "reason": f"  {reason}  ",
        "comments": {"problem": f"  {comment}  "},
    }
    assert client.get(root + "/assigned", headers=owner_headers).status_code == 403
    for name in ("unassigned", "staff"):
        assert client.get(root + "/assigned", headers=headers[name]).json()["submissions"] == []
        assert client.post(review_url, headers=headers[name], json=review_data).status_code == 404
    for denied in (owner_headers, headers["peer"]):
        assert client.post(review_url, headers=denied, json=review_data).status_code == 403
    assert client.get(other_root + "/assigned", headers=headers["mentor"]).json() == {
        "submissions": []
    }
    assert (
        client.post(
            other_root + f"/submissions/{first['id']}/review",
            headers=headers["mentor"],
            json=review_data,
        ).status_code
        == 404
    )
    ended = client.post(
        f"/api/v1/mentoring/organizations/{org}/assignments/{assignment_id}/end",
        headers=headers["staff"],
        json={"expected_version": 1, "reason": "Synthetic assignment closure"},
    )
    assert ended.status_code == 200
    assert client.get(root + "/assigned", headers=headers["mentor"]).json()["submissions"] == []
    assert client.post(review_url, headers=headers["mentor"], json=review_data).status_code == 404
    assert current_plan() == plan
    with Session(engine) as db:
        db.add(
            MentorAssignment(
                organization_id=org,
                mentor_profile_id=profile_id,
                enrollment_id=enrollment,
                starts_on=date.today(),
                assigned_by_user_id=actors["staff"],
            )
        )
        db.commit()
    queue = client.get(root + "/assigned", headers=headers["mentor"])
    assert queue.status_code == 200
    assert queue.json()["submissions"] == [first]
    for invalid_reason in ("   ", " a ", " ab "):
        invalid = client.post(
            review_url,
            headers=headers["mentor"],
            json={**review_data, "reason": invalid_reason},
        )
        assert invalid.status_code == 422
        assert current_plan() == plan
    assert (
        client.post(
            review_url,
            headers=headers["mentor"],
            json={**review_data, "expected_version": 21},
        ).status_code
        == 409
    )
    review = accepted(
        client.post(review_url, headers=headers["mentor"], json=review_data),
        "business_plan.reviewed",
        actors["mentor"],
        23,
        "status,review",
    )
    assert review["reason"] == reason and review["comments"] == {"problem": comment}
    for expected_version in (22, 23):
        assert (
            client.post(
                review_url,
                headers=headers["mentor"],
                json={**review_data, "expected_version": expected_version},
            ).status_code
            == 409
        )
    plan = current_plan()
    assert plan["status"] == "changes_requested" and plan["version"] == 23
    assert plan["submissions"][0]["review"] == review
    revised = {**original, "problem": "B01 confidential revised customer evidence."}
    plan = accepted(
        client.post(
            entry + "/sections",
            headers=owner_headers,
            json={
                "expected_version": 23,
                "section_code": "problem",
                "body": revised["problem"],
            },
        ),
        "business_plan.section_saved",
        owner,
        24,
        "problem",
    )
    assert plan["submissions"][0]["snapshot"] == original
    plan = accepted(
        client.post(entry + "/submit", headers=owner_headers, json={"expected_version": 24}),
        "business_plan.submitted",
        owner,
        25,
        "status,submission_number",
    )
    assert plan["status"] == "submitted"
    assert [item["number"] for item in plan["submissions"]] == [2, 1]
    second = plan["submissions"][0]
    assert second["snapshot"] == revised and second["review"] is None
    assert plan["submissions"][1]["snapshot"] == original
    assert plan["submissions"][1]["review"] == review
    assert (
        client.post(
            review_url,
            headers=headers["mentor"],
            json={**review_data, "expected_version": 25},
        ).status_code
        == 409
    )
    approval_url = root + f"/submissions/{second['id']}/review"
    approval_reason = "B01 confidential approval rationale."
    approval_data = {
        "expected_version": 25,
        "decision": "approved",
        "reason": approval_reason,
        "comments": {"problem": "B01 confidential evidence accepted."},
    }
    assert (
        client.post(
            approval_url,
            headers=headers["mentor"],
            json={**approval_data, "expected_version": 24},
        ).status_code
        == 409
    )
    approval = accepted(
        client.post(approval_url, headers=headers["mentor"], json=approval_data),
        "business_plan.reviewed",
        actors["mentor"],
        26,
        "status,review",
    )
    plan = current_plan()
    assert plan["status"] == "approved" and plan["version"] == 26
    assert plan["sections"] == revised
    assert plan["submissions"][0]["review"] == approval
    assert plan["submissions"][1]["snapshot"] == original
    assert plan["submissions"][1]["review"] == review
    assert (
        client.post(
            entry + "/sections",
            headers=owner_headers,
            json={"expected_version": 26, "section_code": "problem", "body": "Denied"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            entry + "/submit", headers=owner_headers, json={"expected_version": 26}
        ).status_code
        == 409
    )
    assert (
        client.post(
            approval_url,
            headers=headers["mentor"],
            json={**approval_data, "expected_version": 26},
        ).status_code
        == 409
    )
    queue = client.get(root + "/assigned", headers=headers["mentor"])
    assert queue.status_code == 200
    assert {item["id"] for item in queue.json()["submissions"]} == {first["id"], second["id"]}
    assert current_plan() == plan

    with Session(engine) as db:
        revisions = list(
            db.scalars(
                select(BusinessPlanRevision)
                .where(BusinessPlanRevision.plan_id == plan_id)
                .order_by(BusinessPlanRevision.version)
            )
        )
        submissions = list(
            db.scalars(
                select(BusinessPlanSubmission)
                .where(BusinessPlanSubmission.plan_id == plan_id)
                .order_by(BusinessPlanSubmission.number)
            )
        )
        reviews = list(
            db.scalars(
                select(BusinessPlanReview).where(
                    BusinessPlanReview.submission_id.in_([item.id for item in submissions])
                )
            )
        )
        assert [item.version for item in revisions] == [*range(2, 22), 24]
        assert len(submissions) == len(reviews) == 2
        assert [item.snapshot for item in submissions] == [original, revised]
        assert all(
            item.organization_id == org and item.author_user_id == owner for item in revisions
        )
        assert all(
            item.organization_id == org and item.submitted_by_user_id == owner
            for item in submissions
        )
        assert all(
            item.organization_id == org and item.reviewer_user_id == actors["mentor"]
            for item in reviews
        )
        # Test both mutation operations for every immutable evidence table, then verify rollback.
        revision_id, submission_id, review_id = revisions[0].id, submissions[0].id, reviews[0].id
        for model, row_id, changed in (
            (BusinessPlanRevision, revision_id, {"body": "tampered"}),
            (BusinessPlanSubmission, submission_id, {"snapshot": {"problem": "tampered"}}),
            (BusinessPlanReview, review_id, {"reason": "tampered"}),
        ):
            with pytest.raises(DBAPIError):
                db.execute(update(model).where(model.id == row_id).values(**changed))
            db.rollback()
            with pytest.raises(DBAPIError):
                db.execute(delete(model).where(model.id == row_id))
            db.rollback()
        audit = list(
            db.scalars(
                select(AuditLog)
                .where(AuditLog.resource_id == plan_id, AuditLog.action.like("business_plan.%"))
                .order_by(AuditLog.resource_version)
            )
        )
        assert [
            (
                item.resource_version,
                item.action,
                item.actor_id,
                item.changed_fields,
                item.request_id,
            )
            for item in audit
        ] == expected_audits
        assert len(audit) == 26
        assert all(item.organization_id == org and item.reason is None for item in audit)
        assert all(
            "B01 confidential" not in value
            for item in audit
            for value in (item.action, item.changed_fields or "", item.request_id)
        )
    assert current_plan() == plan
