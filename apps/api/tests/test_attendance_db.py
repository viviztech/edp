import os
from datetime import timedelta

import pytest
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_identity import auth, signed_in  # noqa: F401
from test_lms_db import learning_context

from app.modules.attendance.models import AttendanceCorrection, AttendanceRecord
from app.modules.identity.models import AuditLog, Role, UserRole, now
from app.modules.programs.models import Cohort, ProgramSession, ProgramStaffAssignment

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)


def test_attendance_policy_qr_manual_correction_and_projection(request) -> None:
    auth_context, headers, org_id, other_id, cohort_id, enrollment_id, user_id = learning_context(
        request
    )
    client, engine, _, _ = auth_context
    root = f"/api/v1/attendance/organizations/{org_id}"
    with Session(engine) as db:
        qr_session = ProgramSession(
            organization_id=org_id,
            cohort_id=cohort_id,
            title_en="Customer discovery lab",
            title_ta="Synthetic Tamil session",
            starts_at=now() + timedelta(minutes=5),
            ends_at=now() + timedelta(hours=1),
            mode="in_person",
            location="Training room",
        )
        manual_session = ProgramSession(
            organization_id=org_id,
            cohort_id=cohort_id,
            title_en="Business model workshop",
            title_ta="Synthetic Tamil workshop",
            starts_at=now() + timedelta(minutes=10),
            ends_at=now() + timedelta(hours=2),
            mode="hybrid",
            location="Training room",
        )
        db.add_all([qr_session, manual_session])
        db.commit()
        qr_session_id = qr_session.id
        manual_session_id = manual_session.id

    assert (
        client.get(
            f"/api/v1/attendance/organizations/{other_id}/staff-workspace", headers=headers
        ).status_code
        == 403
    )

    policy = client.put(
        root + "/policy",
        headers=headers,
        json={
            "cohort_id": str(cohort_id),
            "threshold_percent": 80,
            "late_after_minutes": 10,
            "opens_before_minutes": 15,
            "closes_after_minutes": 30,
            "reason": "Approved cohort attendance policy",
        },
    )
    assert policy.status_code == 200
    assert policy.json()["version"] == 1
    stale = client.put(
        root + "/policy",
        headers=headers,
        json={
            "cohort_id": str(cohort_id),
            "expected_version": 9,
            "threshold_percent": 75,
            "late_after_minutes": 10,
            "opens_before_minutes": 15,
            "closes_after_minutes": 30,
            "reason": "Reject stale policy edit",
        },
    )
    assert stale.status_code == 409

    opened = client.post(
        root + "/windows",
        headers=headers,
        json={"session_id": str(qr_session_id), "reason": "Open learner check-in"},
    )
    assert opened.status_code == 201
    window = opened.json()
    assert len(window["check_in_token"]) >= 32
    assert window["qr_svg_data_url"].startswith("data:image/svg+xml;base64,")
    assert (
        client.post(
            root + "/windows",
            headers=headers,
            json={"session_id": str(qr_session_id), "reason": "Reject duplicate window"},
        ).status_code
        == 409
    )

    checked = client.post(
        root + "/check-in",
        headers=headers,
        json={"token": window["check_in_token"]},
    )
    assert checked.status_code == 201
    assert checked.json()["status"] == "present"
    assert checked.json()["source"] == "qr"
    assert (
        client.post(
            root + "/check-in",
            headers=headers,
            json={"token": window["check_in_token"]},
        ).status_code
        == 409
    )
    assert (
        client.post(root + "/check-in", headers=headers, json={"token": "x" * 43}).status_code
        == 404
    )

    marked = client.post(
        root + f"/sessions/{manual_session_id}/records",
        headers=headers,
        json={
            "enrollment_id": str(enrollment_id),
            "status": "absent",
            "reason": "Trainer completed the register",
        },
    )
    assert marked.status_code == 201
    record = marked.json()
    assert (
        client.post(
            root + f"/sessions/{manual_session_id}/records",
            headers=headers,
            json={
                "enrollment_id": str(enrollment_id),
                "status": "present",
                "reason": "Reject duplicate marking",
            },
        ).status_code
        == 409
    )

    corrected = client.post(
        root + f"/records/{record['id']}/correct",
        headers=headers,
        json={
            "expected_version": 1,
            "status": "excused",
            "reason": "Approved medical absence evidence",
        },
    )
    assert corrected.status_code == 200
    assert corrected.json()["version"] == 2
    assert corrected.json()["status"] == "excused"
    assert (
        client.post(
            root + f"/records/{record['id']}/correct",
            headers=headers,
            json={
                "expected_version": 1,
                "status": "present",
                "reason": "Reject stale correction",
            },
        ).status_code
        == 409
    )

    workspace = client.get(root + "/staff-workspace", headers=headers)
    assert workspace.status_code == 200
    sessions = {item["session_id"]: item for item in workspace.json()["sessions"]}
    assert sessions[str(qr_session_id)]["participants"][0]["record"]["source"] == "qr"
    assert sessions[str(manual_session_id)]["participants"][0]["record"]["status"] == "excused"
    learner = client.get(root + "/my-attendance", headers=headers)
    assert learner.status_code == 200
    assert learner.json()["enrollments"][0]["summary"]["threshold_percent"] == 80

    closed = client.post(
        root + f"/windows/{window['id']}/close",
        headers=headers,
        json={"expected_version": 1, "reason": "Check-in completed"},
    )
    assert closed.status_code == 200
    assert closed.json()["state"] == "closed"

    with Session(engine) as db:
        correction = db.scalar(select(AttendanceCorrection))
        assert correction and correction.reason == "Approved medical absence evidence"
        audits = list(
            db.scalars(
                select(AuditLog).where(
                    AuditLog.organization_id == org_id,
                    AuditLog.action.like("attendance.%"),
                )
            )
        )
        assert {item.action for item in audits} >= {
            "attendance.policy.created",
            "attendance.window.created",
            "attendance.checked_in",
            "attendance.marked",
            "attendance.corrected",
            "attendance.window.closed",
        }
        assert all(item.changed_fields and "token" not in item.changed_fields for item in audits)
        direct = db.scalar(select(AttendanceRecord).where(AttendanceRecord.id == record["id"]))
        assert direct
        with pytest.raises(DBAPIError):
            db.execute(
                update(AttendanceRecord)
                .where(AttendanceRecord.id == direct.id)
                .values(enrollment_id=enrollment_id)
            )
            db.commit()
        db.rollback()
        with pytest.raises(DBAPIError):
            db.execute(text("DELETE FROM attendance_corrections"))
            db.commit()

    with Session(engine) as db:
        director = db.scalar(select(Role).where(Role.name == "Program Director"))
        trainer = db.scalar(select(Role).where(Role.name == "Trainer"))
        cohort = db.get(Cohort, cohort_id)
        assert director and trainer and cohort
        db.execute(
            delete(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.organization_id == org_id,
                UserRole.role_id == director.id,
            )
        )
        db.add(UserRole(user_id=user_id, role_id=trainer.id, organization_id=org_id))
        db.commit()
        center_id = cohort.center_id
    assert client.get(root + "/staff-workspace", headers=headers).status_code == 403
    with Session(engine) as db:
        assignment = ProgramStaffAssignment(
            organization_id=org_id,
            user_id=user_id,
            center_id=center_id,
            cohort_id=cohort_id,
        )
        db.add(assignment)
        db.commit()
        assignment_id = assignment.id
    assert client.get(root + "/staff-workspace", headers=headers).status_code == 200
    with Session(engine) as db:
        assignment = db.get(ProgramStaffAssignment, assignment_id)
        assert assignment
        assignment.state = "revoked"
        assignment.revoked_at = now()
        assignment.version += 1
        assignment.updated_at = now()
        db.commit()
    assert client.get(root + "/staff-workspace", headers=headers).status_code == 403
