import os
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_identity import account, auth, signed_in  # noqa: F401

from app.core.config import get_settings
from app.modules.applications.models import Application, ApplicationForm
from app.modules.identity.models import AuditLog, Organization, Role, User, UserRole, now
from app.modules.lms.models import (
    AssignmentGrade,
    AssignmentSubmission,
    CourseEnrollment,
    CourseModule,
    LessonProgress,
    QuizAttempt,
)
from app.modules.programs.models import (
    ApplicationCycle,
    Cohort,
    Enrollment,
    Participant,
    Program,
    ProgramStaffAssignment,
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


def test_lms_author_publish_assign_and_enrollment_scoped_access(request, tmp_path) -> None:
    auth_context, headers, org_id, other_id, cohort_id, enrollment_id, user_id = learning_context(
        request
    )
    client, engine, _, _ = auth_context
    material_root = tmp_path / "lms-materials"
    material_file = material_root / "private" / "lms" / "customer-worksheet.pdf"
    material_file.parent.mkdir(parents=True)
    material_file.write_bytes(b"%PDF-1.4 synthetic LMS material")
    get_settings().lms_material_root = str(material_root)
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

    learning_assignment = client.post(
        root + "/assignments",
        headers=headers,
        json={
            "course_id": course["id"],
            "lesson_id": lesson_data["id"],
            "position": 1,
            "title_en": "Customer evidence",
            "title_ta": "Synthetic Tamil assignment",
            "instructions_en": "Summarize one customer interview.",
            "instructions_ta": "Synthetic Tamil assignment instructions.",
            "maximum_points": 20,
            "passing_points": 12,
            "max_submissions": 2,
        },
    )
    assert learning_assignment.status_code == 201

    quiz = client.post(
        root + "/quizzes",
        headers=headers,
        json={
            "course_id": course["id"],
            "lesson_id": lesson_data["id"],
            "position": 1,
            "title_en": "Customer check",
            "title_ta": "Synthetic Tamil quiz",
            "instructions_en": "Choose the strongest customer statement.",
            "instructions_ta": "Synthetic Tamil quiz instructions.",
            "passing_percent": 60,
            "max_attempts": 2,
        },
    )
    assert quiz.status_code == 201
    question = client.post(
        root + "/quiz-questions",
        headers=headers,
        json={
            "course_id": course["id"],
            "quiz_id": quiz.json()["id"],
            "position": 1,
            "prompt_en": "Which statement is observable?",
            "prompt_ta": "Synthetic Tamil question",
            "points": 10,
        },
    )
    assert question.status_code == 201
    wrong_choice = client.post(
        root + "/quiz-choices",
        headers=headers,
        json={
            "course_id": course["id"],
            "quiz_id": quiz.json()["id"],
            "question_id": question.json()["id"],
            "position": 1,
            "label_en": "Customers probably want it.",
            "label_ta": "Synthetic Tamil wrong choice",
            "is_correct": False,
        },
    )
    assert wrong_choice.status_code == 201
    incomplete_quiz = client.post(
        root + f"/{course['id']}/publish",
        headers=headers,
        json={"expected_version": 2, "reason": "Reject incomplete assessment"},
    )
    assert incomplete_quiz.status_code == 422
    assert incomplete_quiz.json()["error"]["code"] == "quiz_structure_incomplete"
    correct_choice = client.post(
        root + "/quiz-choices",
        headers=headers,
        json={
            "course_id": course["id"],
            "quiz_id": quiz.json()["id"],
            "question_id": question.json()["id"],
            "position": 2,
            "label_en": "Five customers reported the same problem.",
            "label_ta": "Synthetic Tamil correct choice",
            "is_correct": True,
        },
    )
    assert correct_choice.status_code == 201

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

    trainer_credentials = account(auth_context, "trainer@example.com")
    with Session(engine) as db:
        trainer = db.scalar(select(User).where(User.email == "trainer@example.com"))
        trainer_role = db.scalar(select(Role).where(Role.name == "Trainer"))
        cohort = db.get(Cohort, cohort_id)
        assert trainer and trainer_role and cohort
        db.add(UserRole(user_id=trainer.id, role_id=trainer_role.id, organization_id=org_id))
        db.commit()
    trainer_login = client.post("/api/v1/auth/login", json=trainer_credentials)
    assert trainer_login.status_code == 200
    trainer_headers = {"Authorization": "Bearer " + trainer_login.json()["access_token"]}
    unscoped = client.get(root + "/trainer-delivery", headers=trainer_headers)
    assert unscoped.status_code == 403
    assert unscoped.json()["error"]["code"] == "staff_scope_required"
    with Session(engine) as db:
        trainer = db.scalar(select(User).where(User.email == "trainer@example.com"))
        cohort = db.get(Cohort, cohort_id)
        assert trainer and cohort
        trainer_assignment = ProgramStaffAssignment(
            organization_id=org_id,
            user_id=trainer.id,
            center_id=cohort.center_id,
            cohort_id=cohort.id,
        )
        db.add(trainer_assignment)
        db.commit()
        trainer_assignment_id = trainer_assignment.id

    trainer_delivery = client.get(root + "/trainer-delivery", headers=trainer_headers)
    assert trainer_delivery.status_code == 200
    trainer_course = trainer_delivery.json()["courses"][0]
    assert trainer_course["course_id"] == course["id"]
    assert trainer_course["learners"][0]["display_name"] == "Synthetic Learner"
    trainer_material = trainer_course["modules"][0]["lessons"][0]["materials"][0]
    assert trainer_material["available"] is True
    assert "provider_key" not in trainer_material
    assert trainer_course["learners"][0]["quiz_results"][0]["attempt_count"] == 0
    assert trainer_course["learners"][0]["assignment_submissions"] == []
    trainer_access = client.post(
        root + f"/trainer-delivery/{course['id']}/materials/{material.json()['id']}/access",
        headers=trainer_headers,
    )
    assert trainer_access.status_code == 200
    trainer_delivery_path = trainer_access.json()["url"].replace(
        "/api/courses/", "/api/v1/courses/"
    )
    trainer_file = client.get(trainer_delivery_path, headers=trainer_headers)
    assert trainer_file.status_code == 200
    assert trainer_file.content.startswith(b"%PDF-1.4")

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
    started_learning = client.get(root + "/my-learning", headers=headers).json()["courses"][0]
    assert started_learning["modules"][0]["lessons"][0]["materials"][0]["available"] is True
    learner_quiz = started_learning["modules"][0]["lessons"][0]["quizzes"][0]
    assert learner_quiz["available"] is True
    assert learner_quiz["remaining_attempts"] == 2
    assert "is_correct" not in learner_quiz["questions"][0]["choices"][0]
    first_attempt = client.post(
        root + f"/my-learning/{course['id']}/quizzes/{quiz.json()['id']}/attempts",
        headers=headers,
        json={
            "answers": [
                {
                    "question_id": question.json()["id"],
                    "choice_id": wrong_choice.json()["id"],
                }
            ]
        },
    )
    assert first_attempt.status_code == 201
    assert first_attempt.json()["attempt_number"] == 1
    assert first_attempt.json()["percent"] == 0
    assert first_attempt.json()["passed"] is False
    second_attempt = client.post(
        root + f"/my-learning/{course['id']}/quizzes/{quiz.json()['id']}/attempts",
        headers=headers,
        json={
            "answers": [
                {
                    "question_id": question.json()["id"],
                    "choice_id": correct_choice.json()["id"],
                }
            ]
        },
    )
    assert second_attempt.status_code == 201
    assert second_attempt.json()["attempt_number"] == 2
    assert second_attempt.json()["percent"] == 100
    assert second_attempt.json()["passed"] is True
    passed_learning = client.get(root + "/my-learning", headers=headers).json()["courses"][0]
    passed_quiz = passed_learning["modules"][0]["lessons"][0]["quizzes"][0]
    assert passed_quiz["attempt_count"] == 2
    assert passed_quiz["remaining_attempts"] == 0
    assert passed_quiz["best_percent"] == 100
    assert passed_quiz["passed"] is True
    repeated_attempt = client.post(
        root + f"/my-learning/{course['id']}/quizzes/{quiz.json()['id']}/attempts",
        headers=headers,
        json={
            "answers": [
                {
                    "question_id": question.json()["id"],
                    "choice_id": correct_choice.json()["id"],
                }
            ]
        },
    )
    assert repeated_attempt.status_code == 409
    assert repeated_attempt.json()["error"]["code"] == "quiz_already_passed"
    learner_assignment = started_learning["modules"][0]["lessons"][0]["assignments"][0]
    assert learner_assignment["available"] is True
    assert learner_assignment["remaining_submissions"] == 2
    submission = client.post(
        root
        + f"/my-learning/{course['id']}/assignments/{learning_assignment.json()['id']}/submissions",
        headers=headers,
        json={"response_text": "Five interviews showed repeated payment delays."},
    )
    assert submission.status_code == 201
    assert submission.json()["revision"] == 1
    assert submission.json()["grade"] is None
    pending_retry = client.post(
        root
        + f"/my-learning/{course['id']}/assignments/{learning_assignment.json()['id']}/submissions",
        headers=headers,
        json={"response_text": "A premature second revision."},
    )
    assert pending_retry.status_code == 409
    assert pending_retry.json()["error"]["code"] == "assignment_review_pending"
    graded = client.post(
        root
        + f"/trainer-delivery/{course['id']}/assignment-submissions/"
        + f"{submission.json()['id']}/grade",
        headers=trainer_headers,
        json={"score_points": 15, "feedback": "Clear evidence; add interview dates next time."},
    )
    assert graded.status_code == 201
    assert graded.json()["score_points"] == 15
    assert graded.json()["passed"] is True
    graded_learning = client.get(root + "/my-learning", headers=headers).json()["courses"][0]
    graded_assignment = graded_learning["modules"][0]["lessons"][0]["assignments"][0]
    assert graded_assignment["submissions"][0]["grade"]["feedback"].startswith("Clear evidence")
    resubmission = client.post(
        root
        + f"/my-learning/{course['id']}/assignments/{learning_assignment.json()['id']}/submissions",
        headers=headers,
        json={"response_text": "Five dated interviews confirmed payment delays."},
    )
    assert resubmission.status_code == 201
    assert resubmission.json()["revision"] == 2
    exhausted = client.post(
        root
        + f"/my-learning/{course['id']}/assignments/{learning_assignment.json()['id']}/submissions",
        headers=headers,
        json={"response_text": "Third revision must be rejected."},
    )
    assert exhausted.status_code == 409
    assert exhausted.json()["error"]["code"] == "assignment_submission_limit_reached"

    learner_access = client.post(
        root + f"/my-learning/{course['id']}/materials/{material.json()['id']}/access",
        headers=headers,
    )
    assert learner_access.status_code == 200
    assert "private/lms" not in learner_access.text
    learner_delivery_path = learner_access.json()["url"].replace(
        "/api/courses/", "/api/v1/courses/"
    )
    learner_file = client.get(learner_delivery_path, headers=headers)
    assert learner_file.status_code == 200
    assert learner_file.content.startswith(b"%PDF-1.4")
    tampered = learner_delivery_path[:-1] + ("A" if learner_delivery_path[-1] != "A" else "B")
    assert client.get(tampered, headers=headers).status_code == 403

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
    second_grade = client.post(
        root
        + f"/trainer-delivery/{course['id']}/assignment-submissions/"
        + f"{resubmission.json()['id']}/grade",
        headers=trainer_headers,
        json={"score_points": 18, "feedback": "The dated evidence meets the assignment standard."},
    )
    assert second_grade.status_code == 201
    assert second_grade.json()["passed"] is True
    graded_delivery = client.get(root + "/trainer-delivery", headers=trainer_headers).json()
    graded_result = graded_delivery["courses"][0]["learners"][0]["quiz_results"][0]
    assert graded_result["attempt_count"] == 2
    assert graded_result["best_percent"] == 100
    assert graded_result["passed"] is True
    assignment_results = graded_delivery["courses"][0]["learners"][0]["assignment_submissions"]
    assert len(assignment_results) == 2
    assert assignment_results[-1]["grade"]["score_points"] == 18

    with Session(engine) as db:
        trainer_assignment = db.get(ProgramStaffAssignment, trainer_assignment_id)
        assert trainer_assignment
        trainer_assignment.state = "revoked"
        trainer_assignment.version += 1
        trainer_assignment.revoked_at = now()
        trainer_assignment.updated_at = trainer_assignment.revoked_at
        db.commit()
    revoked_delivery = client.get(root + "/trainer-delivery", headers=trainer_headers)
    assert revoked_delivery.status_code == 403
    assert revoked_delivery.json()["error"]["code"] == "staff_scope_required"

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
        assert db.scalar(
            select(AuditLog.id).where(
                AuditLog.actor_id == user_id,
                AuditLog.action == "lms.quiz.attempt_submitted",
            )
        )
        attempt = db.scalar(
            select(QuizAttempt).where(QuizAttempt.id == second_attempt.json()["id"])
        )
        assert attempt
        attempt.percent = 50
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()
        assignment_submission = db.scalar(
            select(AssignmentSubmission).where(AssignmentSubmission.id == submission.json()["id"])
        )
        assert assignment_submission
        assignment_submission.response_text = "Forbidden rewrite"
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()
        db.add(
            AssignmentSubmission(
                organization_id=assignment_submission.organization_id,
                course_id=assignment_submission.course_id,
                course_enrollment_id=assignment_submission.course_enrollment_id,
                assignment_id=assignment_submission.assignment_id,
                revision=3,
                response_text="A direct third revision must be rejected by PostgreSQL.",
            )
        )
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()
        assignment_grade = db.scalar(
            select(AssignmentGrade).where(AssignmentGrade.id == graded.json()["id"])
        )
        assert assignment_grade
        assignment_grade.feedback = "Forbidden feedback rewrite"
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()
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
