import os
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_identity import auth, signed_in  # noqa: F401

from app.modules.applications.models import Application, ApplicationForm
from app.modules.identity.models import AuditLog, Organization, Role, User, UserRole, now
from app.modules.lms.models import CourseEnrollment, CourseModule, LessonProgress
from app.modules.programs.models import (
    ApplicationCycle,
    Cohort,
    Enrollment,
    Participant,
    Program,
    TrainingCenter,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)


def learning_context(request):
    auth_context = request.getfixturevalue("auth")
    client, engine, _, _ = auth_context
    _, _, headers = signed_in(auth_context)
    with Session(engine) as db:
        user = db.scalar(select(User).where(User.email == "learner@example.com"))
        director = db.scalar(select(Role).where(Role.name == "Program Director"))
        participant_role = db.scalar(select(Role).where(Role.name == "Participant"))
        assert user and director and participant_role
        org = Organization(name="Learning organization")
        other = Organization(name="Other learning organization")
        db.add_all([org, other])
        db.flush()
        db.add_all(
            [
                UserRole(user_id=user.id, role_id=director.id, organization_id=org.id),
                UserRole(user_id=user.id, role_id=participant_role.id, organization_id=org.id),
            ]
        )
        program = Program(
            organization_id=org.id,
            code="enterprise",
            name_en="Enterprise",
            name_ta="Synthetic Tamil program",
            state="active",
        )
        center = TrainingCenter(
            organization_id=org.id,
            code="learning-center",
            name_en="Learning center",
            name_ta="Synthetic Tamil center",
            locality="Chennai",
        )
        form = ApplicationForm(
            organization_id=org.id,
            version=1,
            state="published",
            title_en="Learning intake",
            title_ta="Synthetic Tamil intake",
            published_at=now(),
            published_by_id=user.id,
        )
        db.add_all([program, center, form])
        db.flush()
        cohort = Cohort(
            organization_id=org.id,
            program_id=program.id,
            center_id=center.id,
            code="learning-01",
            name_en="Learning cohort",
            name_ta="Synthetic Tamil cohort",
            starts_on=now().date(),
            ends_on=(now() + timedelta(days=90)).date(),
            capacity=30,
            state="active",
        )
        db.add(cohort)
        db.flush()
        cycle = ApplicationCycle(
            organization_id=org.id,
            program_id=program.id,
            cohort_id=cohort.id,
            form_id=form.id,
            code="learning-cycle",
            name_en="Learning cycle",
            name_ta="Synthetic Tamil cycle",
            opens_at=now() - timedelta(days=30),
            closes_at=now() - timedelta(days=1),
            state="closed",
        )
        db.add(cycle)
        db.flush()
        application = Application(
            organization_id=org.id,
            person_id=user.person_id,
            form_id=form.id,
            cycle_id=cycle.id,
            state="enrolled",
            version=8,
            application_number="EDP-LMS-0001",
            submitted_at=now() - timedelta(days=20),
        )
        participant = Participant(
            organization_id=org.id,
            person_id=user.person_id,
            status="active",
        )
        db.add_all([application, participant])
        db.flush()
        enrollment = Enrollment(
            organization_id=org.id,
            participant_id=participant.id,
            program_id=program.id,
            cohort_id=cohort.id,
            application_id=application.id,
            status="active",
        )
        db.add(enrollment)
        db.commit()
        return (
            auth_context,
            headers,
            org.id,
            other.id,
            cohort.id,
            enrollment.id,
            user.id,
        )


def test_lms_author_publish_assign_and_enrollment_scoped_access(request) -> None:
    auth_context, headers, org_id, other_id, cohort_id, enrollment_id, user_id = learning_context(
        request
    )
    client, engine, _, _ = auth_context
    root = f"/api/v1/courses/organizations/{org_id}"

    assert (
        client.get(f"/api/v1/courses/organizations/{other_id}/catalog", headers=headers).status_code
        == 403
    )

    created = client.post(
        root,
        headers=headers,
        json={
            "code": "business-foundations",
            "title_en": "Business foundations",
            "title_ta": "Synthetic Tamil course",
            "description_en": "Build a practical foundation for an enterprise.",
            "description_ta": "Synthetic Tamil course description.",
        },
    )
    assert created.status_code == 201
    course = created.json()

    incomplete = client.post(
        root + f"/{course['id']}/publish",
        headers=headers,
        json={"expected_version": 1, "reason": "Content review complete"},
    )
    assert incomplete.status_code == 422
    assert incomplete.json()["error"]["code"] == "course_structure_incomplete"

    module = client.post(
        root + "/modules",
        headers=headers,
        json={
            "course_id": course["id"],
            "position": 1,
            "title_en": "Know the customer",
            "title_ta": "Synthetic Tamil module",
        },
    )
    assert module.status_code == 201
    module_data = module.json()

    lesson = client.post(
        root + "/lessons",
        headers=headers,
        json={
            "course_id": course["id"],
            "module_id": module_data["id"],
            "position": 1,
            "title_en": "Customer problem",
            "title_ta": "Synthetic Tamil lesson",
            "body_en": "Describe the customer and the problem in observable terms.",
            "body_ta": "Synthetic Tamil lesson body.",
            "duration_minutes": 20,
        },
    )
    assert lesson.status_code == 201
    lesson_data = lesson.json()

    second_lesson = client.post(
        root + "/lessons",
        headers=headers,
        json={
            "course_id": course["id"],
            "module_id": module_data["id"],
            "position": 2,
            "title_en": "Validate the customer problem",
            "title_ta": "Synthetic Tamil second lesson",
            "body_en": "Validate the problem after defining it.",
            "body_ta": "Synthetic Tamil second lesson body.",
            "duration_minutes": 15,
        },
    )
    assert second_lesson.status_code == 201
    second_lesson_data = second_lesson.json()
    prerequisite = client.post(
        root + "/prerequisites",
        headers=headers,
        json={
            "course_id": course["id"],
            "lesson_id": second_lesson_data["id"],
            "prerequisite_lesson_id": lesson_data["id"],
            "reason": "The definition must precede validation",
        },
    )
    assert prerequisite.status_code == 201
    invalid_prerequisite = client.post(
        root + "/prerequisites",
        headers=headers,
        json={
            "course_id": course["id"],
            "lesson_id": lesson_data["id"],
            "prerequisite_lesson_id": second_lesson_data["id"],
            "reason": "Reject reverse ordering",
        },
    )
    assert invalid_prerequisite.status_code == 422
    assert invalid_prerequisite.json()["error"]["code"] == "prerequisite_must_precede_lesson"

    rule = client.post(
        root + f"/{course['id']}/completion-rule",
        headers=headers,
        json={
            "completion_rule": "minimum_lessons",
            "minimum_lessons": 2,
            "expected_version": 1,
            "reason": "Require both approved lessons",
        },
    )
    assert rule.status_code == 200
    assert rule.json()["version"] == 2

    material = client.post(
        root + "/materials",
        headers=headers,
        json={
            "course_id": course["id"],
            "lesson_id": lesson_data["id"],
            "position": 1,
            "kind": "document",
            "label_en": "Customer worksheet",
            "label_ta": "Synthetic Tamil worksheet",
            "provider_key": "private/lms/customer-worksheet.pdf",
        },
    )
    assert material.status_code == 201
    assert material.json()["provider_key"].startswith("private/")

    published = client.post(
        root + f"/{course['id']}/publish",
        headers=headers,
        json={"expected_version": 2, "reason": "Content review complete"},
    )
    assert published.status_code == 200
    assert published.json()["state"] == "published"
    assert published.json()["version"] == 3
    frozen_rule = client.post(
        root + f"/{course['id']}/completion-rule",
        headers=headers,
        json={
            "completion_rule": "all_lessons",
            "minimum_lessons": None,
            "expected_version": 3,
            "reason": "Published rules are frozen",
        },
    )
    assert frozen_rule.status_code == 409
    assert frozen_rule.json()["error"]["code"] == "course_structure_frozen"

    assignment = client.post(
        root + "/cohort-assignments",
        headers=headers,
        json={
            "course_id": course["id"],
            "cohort_id": str(cohort_id),
            "position": 1,
            "reason": "Approved cohort learning plan",
        },
    )
    assert assignment.status_code == 201
    assert (
        client.post(
            root + "/cohort-assignments",
            headers=headers,
            json={
                "course_id": course["id"],
                "cohort_id": str(cohort_id),
                "position": 1,
                "reason": "Duplicate assignment check",
            },
        ).status_code
        == 409
    )

    learning = client.get(root + "/my-learning", headers=headers)
    assert learning.status_code == 200
    learner_course = learning.json()["courses"][0]
    assert learner_course["id"] == course["id"]
    assert learner_course["course_enrollment"] is None
    learner_material = learner_course["modules"][0]["lessons"][0]["materials"][0]
    assert learner_material["available"] is False
    assert "provider_key" not in learner_material

    started = client.post(root + f"/my-learning/{course['id']}/start", headers=headers)
    repeated = client.post(root + f"/my-learning/{course['id']}/start", headers=headers)
    assert started.status_code == 200
    assert repeated.status_code == 200
    assert started.json()["id"] == repeated.json()["id"]
    assert started.json()["enrollment_id"] == str(enrollment_id)
    assert client.post(root + f"/my-learning/{uuid4()}/start", headers=headers).status_code == 403

    blocked = client.post(
        root + f"/my-learning/{course['id']}/lessons/{second_lesson_data['id']}/complete",
        headers=headers,
        json={"expected_course_enrollment_version": 1},
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "lesson_prerequisite_incomplete"

    first_complete = client.post(
        root + f"/my-learning/{course['id']}/lessons/{lesson_data['id']}/complete",
        headers=headers,
        json={"expected_course_enrollment_version": 1},
    )
    assert first_complete.status_code == 200
    assert first_complete.json()["progress"]["percent"] == 50
    assert first_complete.json()["progress"]["status"] == "in_progress"
    repeated_complete = client.post(
        root + f"/my-learning/{course['id']}/lessons/{lesson_data['id']}/complete",
        headers=headers,
        json={"expected_course_enrollment_version": 1},
    )
    assert repeated_complete.status_code == 200
    assert repeated_complete.json()["id"] == first_complete.json()["id"]

    final_complete = client.post(
        root + f"/my-learning/{course['id']}/lessons/{second_lesson_data['id']}/complete",
        headers=headers,
        json={"expected_course_enrollment_version": 2},
    )
    assert final_complete.status_code == 200
    assert final_complete.json()["progress"]["percent"] == 100
    assert final_complete.json()["progress"]["status"] == "completed"
    assert final_complete.json()["course_enrollment"]["status"] == "completed"

    completed_learning = client.get(root + "/my-learning", headers=headers).json()["courses"][0]
    assert completed_learning["progress"]["completed_lessons"] == 2
    assert all(
        lesson["completed"]
        for module in completed_learning["modules"]
        for lesson in module["lessons"]
    )
    staff_catalog = client.get(root + "/catalog", headers=headers).json()
    summary = staff_catalog["progress_summaries"][0]
    assert summary["started_learners"] == 1
    assert summary["completed_learners"] == 1
    assert summary["average_percent"] == 100

    with Session(engine) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(CourseEnrollment)
                .where(CourseEnrollment.enrollment_id == enrollment_id)
            )
            == 1
        )
        assert db.scalar(
            select(AuditLog.id).where(
                AuditLog.actor_id == user_id,
                AuditLog.action == "lms.course.started",
            )
        )
        db.add(
            CourseModule(
                organization_id=org_id,
                course_id=course["id"],
                position=2,
                title_en="Forbidden edit",
                title_ta="Synthetic Tamil",
            )
        )
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()
        progress = db.scalar(
            select(LessonProgress).where(LessonProgress.lesson_id == lesson_data["id"])
        )
        assert progress
        progress.completed_at = now() + timedelta(days=1)
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()
