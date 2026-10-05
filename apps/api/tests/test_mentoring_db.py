import os
from datetime import date, timedelta

import pytest
from sqlalchemy import select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_identity import auth, signed_in  # noqa: F401
from test_lms_db import learning_context

from app.modules.identity.models import AuditLog, Role, UserRole, now
from app.modules.mentoring.models import MentoringFeedback, MentoringNote

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)


def test_mentoring_assignment_session_outcomes_and_privacy(request) -> None:
    auth_context, headers, org_id, other_id, _, enrollment_id, user_id = learning_context(request)
    client, engine, _, _ = auth_context
    root = f"/api/v1/mentoring/organizations/{org_id}"

    with Session(engine) as db:
        mentor_role = db.scalar(select(Role).where(Role.name == "Mentor"))
        assert mentor_role
        db.add(UserRole(user_id=user_id, role_id=mentor_role.id, organization_id=org_id))
        db.commit()

    assert (
        client.get(
            f"/api/v1/mentoring/organizations/{other_id}/workspace", headers=headers
        ).status_code
        == 403
    )

    created_profile = client.post(
        root + "/profiles",
        headers=headers,
        json={
            "user_id": str(user_id),
            "headline": "Enterprise mentor",
            "biography": "Supports founders through validation and growth.",
        },
    )
    assert created_profile.status_code == 201
    profile = created_profile.json()
    assert profile["display_name"]

    expertise = client.post(
        root + "/expertise",
        headers=headers,
        json={
            "mentor_profile_id": profile["id"],
            "code": "market-validation",
            "name_en": "Market validation",
            "name_ta": "Market validation Tamil",
        },
    )
    assert expertise.status_code == 201
    availability = client.post(
        root + "/availability",
        headers=headers,
        json={
            "mentor_profile_id": profile["id"],
            "weekday": 2,
            "starts_at": "10:00:00",
            "ends_at": "12:00:00",
            "timezone": "Asia/Kolkata",
        },
    )
    assert availability.status_code == 201
    assert (
        client.post(
            root + "/availability",
            headers=headers,
            json={
                "mentor_profile_id": profile["id"],
                "weekday": 2,
                "starts_at": "11:00:00",
                "ends_at": "13:00:00",
                "timezone": "Asia/Kolkata",
            },
        ).status_code
        == 409
    )

    assignment_response = client.post(
        root + "/assignments",
        headers=headers,
        json={
            "mentor_profile_id": profile["id"],
            "enrollment_id": str(enrollment_id),
            "starts_on": date.today().isoformat(),
            "reason": "Approved mentor match",
        },
    )
    assert assignment_response.status_code == 201
    assignment = assignment_response.json()
    assert (
        client.post(
            root + "/assignments",
            headers=headers,
            json={
                "mentor_profile_id": profile["id"],
                "enrollment_id": str(enrollment_id),
                "starts_on": date.today().isoformat(),
                "reason": "Reject duplicate active mentor",
            },
        ).status_code
        == 409
    )

    starts_at = now() + timedelta(days=1)
    ends_at = starts_at + timedelta(hours=1)
    session_response = client.post(
        root + "/sessions",
        headers=headers,
        json={
            "assignment_id": assignment["id"],
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "mode": "online",
            "location_or_link": "https://meet.example/session",
            "topic": "Customer discovery review",
        },
    )
    assert session_response.status_code == 201
    mentoring_session = session_response.json()
    assert (
        client.post(
            root + "/sessions",
            headers=headers,
            json={
                "assignment_id": assignment["id"],
                "starts_at": (starts_at + timedelta(minutes=15)).isoformat(),
                "ends_at": (ends_at + timedelta(minutes=15)).isoformat(),
                "mode": "phone",
                "topic": "Conflicting review",
            },
        ).status_code
        == 409
    )

    private_note = client.post(
        root + "/notes",
        headers=headers,
        json={
            "assignment_id": assignment["id"],
            "session_id": mentoring_session["id"],
            "visibility": "mentor_private",
            "body": "Private safeguarding observation",
        },
    )
    assert private_note.status_code == 201
    shared_note = client.post(
        root + "/notes",
        headers=headers,
        json={
            "assignment_id": assignment["id"],
            "session_id": mentoring_session["id"],
            "visibility": "shared_with_participant",
            "body": "Validate five customer interviews before the next session.",
        },
    )
    assert shared_note.status_code == 201

    goal = client.post(
        root + "/goals",
        headers=headers,
        json={
            "assignment_id": assignment["id"],
            "title": "Validate the target customer",
            "target_date": (date.today() + timedelta(days=30)).isoformat(),
        },
    ).json()
    goal_update = client.post(
        root + f"/goals/{goal['id']}/state",
        headers=headers,
        json={
            "expected_version": goal["version"],
            "progress_percent": 40,
            "target": "active",
            "reason": "Reviewed interview evidence",
        },
    )
    assert goal_update.status_code == 200
    assert goal_update.json()["progress_percent"] == 40

    action = client.post(
        root + "/action-items",
        headers=headers,
        json={
            "assignment_id": assignment["id"],
            "goal_id": goal["id"],
            "title": "Complete five interviews",
            "due_at": (now() + timedelta(days=7)).isoformat(),
        },
    ).json()
    assert (
        client.post(
            root + f"/action-items/{action['id']}/state",
            headers=headers,
            json={
                "expected_version": action["version"],
                "target": "completed",
                "reason": "Interview notes reviewed",
            },
        ).status_code
        == 200
    )

    follow_up = client.post(
        root + "/follow-ups",
        headers=headers,
        json={
            "assignment_id": assignment["id"],
            "session_id": mentoring_session["id"],
            "purpose": "Review customer evidence",
            "due_at": (now() + timedelta(days=8)).isoformat(),
        },
    )
    assert follow_up.status_code == 201

    completed = client.post(
        root + f"/sessions/{mentoring_session['id']}/state",
        headers=headers,
        json={
            "expected_version": mentoring_session["version"],
            "target": "completed",
            "reason": "Session outcomes recorded",
        },
    )
    assert completed.status_code == 200

    participant_view = client.get(root + "/my-mentoring", headers=headers)
    assert participant_view.status_code == 200
    note_bodies = {item["body"] for item in participant_view.json()["notes"]}
    assert "Validate five customer interviews before the next session." in note_bodies
    assert "Private safeguarding observation" not in note_bodies

    feedback = client.post(
        root + "/feedback",
        headers=headers,
        json={
            "session_id": mentoring_session["id"],
            "rating": 5,
            "comment": "Clear and useful guidance.",
        },
    )
    assert feedback.status_code == 201
    assert (
        client.post(
            root + "/feedback",
            headers=headers,
            json={"session_id": mentoring_session["id"], "rating": 4},
        ).status_code
        == 409
    )

    workspace = client.get(root + "/workspace", headers=headers)
    assert workspace.status_code == 200
    assert workspace.json()["feedback_count"] == 1
    assert workspace.json()["average_rating"] == 5.0
    assert {item["body"] for item in workspace.json()["notes"]} >= {
        "Private safeguarding observation",
        "Validate five customer interviews before the next session.",
    }

    with Session(engine) as db:
        note = db.scalar(select(MentoringNote).where(MentoringNote.id == private_note.json()["id"]))
        assert note
        with pytest.raises(DBAPIError):
            db.execute(update(MentoringNote).where(MentoringNote.id == note.id).values(body="x"))
            db.commit()
        db.rollback()
        with pytest.raises(DBAPIError):
            db.execute(text("DELETE FROM mentoring_feedback"))
            db.commit()
        db.rollback()
        assert db.scalar(select(MentoringFeedback.id))
        actions = set(
            db.scalars(
                select(AuditLog.action).where(
                    AuditLog.organization_id == org_id,
                    AuditLog.action.like("mentoring.%"),
                )
            )
        )
        assert actions >= {
            "mentoring.profile.created",
            "mentoring.assignment.created",
            "mentoring.session.scheduled",
            "mentoring.note.created",
            "mentoring.goal.updated",
            "mentoring.action.completed",
            "mentoring.follow_up.scheduled",
            "mentoring.session.completed",
            "mentoring.feedback.created",
        }

    ended = client.post(
        root + f"/assignments/{assignment['id']}/end",
        headers=headers,
        json={"expected_version": 1, "reason": "Mentoring engagement completed"},
    )
    assert ended.status_code == 200
    assert ended.json()["state"] == "ended"
