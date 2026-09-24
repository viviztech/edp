import os
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_identity import auth, signed_in  # noqa: F401

from app.modules.applications import service as application_service
from app.modules.applications.models import Application, ApplicationStatusHistory
from app.modules.applications.schemas import (
    AcknowledgementInput,
    AnswerInput,
    DefinitionCommand,
    DefinitionCreate,
    DefinitionFieldInput,
    DraftSave,
    SubmitCommand,
)
from app.modules.identity.models import Organization, Person, Role, User, UserRole, now
from app.modules.identity.security import AuthError, hasher
from app.modules.programs import service as program_service
from app.modules.programs.models import DomainOutbox, Enrollment, ParticipantStatusHistory
from app.modules.programs.schemas import (
    CenterCreate,
    CohortCreate,
    CycleCreate,
    EnrollmentConvert,
    NamedCreate,
    SessionCreate,
    StateCommand,
)
from app.modules.selection import service
from app.modules.selection.models import (
    ApplicationScore,
    InterviewPanelMember,
    ReviewAssignment,
    SelectionCriterion,
    SelectionDecision,
)
from app.modules.selection.schemas import (
    AssignmentCreate,
    ConflictCommand,
    CriterionInput,
    CycleCommand,
    DecisionCommand,
    InterviewComplete,
    InterviewCreate,
    ModerationCommand,
    PanelScoreSubmit,
    ReviewSave,
    ReviewSubmit,
    RubricCommand,
    RubricUpdate,
    ScoreInput,
    SelectionCycleCreate,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)


def definition() -> DefinitionCreate:
    return DefinitionCreate(
        title_en="Selection intake",
        title_ta="Synthetic Tamil selection intake",
        fields=[
            DefinitionFieldInput(
                key="business_idea",
                section="proposal",
                label_en="Business idea",
                label_ta="Synthetic Tamil business idea",
                field_type="textarea",
                required=True,
            )
        ],
        acknowledgements=[
            AcknowledgementInput(
                key="declaration",
                kind="declaration",
                label_en="I declare this is accurate.",
                label_ta="Synthetic Tamil declaration",
            ),
            AcknowledgementInput(
                key="consent",
                kind="consent",
                label_en="I consent to selection review.",
                label_ta="Synthetic Tamil consent",
            ),
        ],
    )


@pytest.fixture
def selection_db(request):
    _, engine, _, _ = request.getfixturevalue("auth")
    with Session(engine) as db:
        org = Organization(name="Selection organization")
        people = [
            Person(display_name="Director"),
            Person(display_name="Reviewer"),
            Person(display_name="Applicant"),
        ]
        db.add_all([org, *people])
        db.flush()
        users = [
            User(
                person_id=person.id,
                email=f"selection-{index}@example.test",
                password_hash=hasher.hash("Synthetic password 123"),
                status="active",
            )
            for index, person in enumerate(people)
        ]
        db.add_all(users)
        db.flush()
        director_role = db.scalar(select(Role).where(Role.name == "Program Director"))
        reviewer_role = db.scalar(select(Role).where(Role.name == "Selection Committee"))
        assert director_role and reviewer_role
        db.add_all(
            [
                UserRole(
                    user_id=users[0].id,
                    role_id=director_role.id,
                    organization_id=org.id,
                ),
                UserRole(
                    user_id=users[1].id,
                    role_id=reviewer_role.id,
                    organization_id=org.id,
                ),
            ]
        )
        db.commit()
        director, reviewer, applicant = (db.get(User, item.id) for item in users)
        assert director and reviewer and applicant
        form = application_service.create_definition(
            db, org.id, director, definition(), "definition-create"
        )
        form = application_service.publish_definition(
            db,
            org.id,
            form.id,
            director,
            DefinitionCommand(expected_revision=1),
            "definition-publish",
        )
        program = program_service.create_program(
            db,
            org.id,
            director,
            NamedCreate(code="enterprise", name_en="Enterprise", name_ta="Tamil"),
            "program-create",
        )
        program = program_service.transition_program(
            db,
            org.id,
            program.id,
            director,
            StateCommand(expected_version=1, target="active", reason="Approved delivery"),
            "program-activate",
        )
        center = program_service.create_center(
            db,
            org.id,
            director,
            CenterCreate(
                code="chennai",
                name_en="Chennai Center",
                name_ta="Synthetic Tamil center",
                locality="Chennai",
            ),
            "center-create",
        )
        cohort = program_service.create_cohort(
            db,
            org.id,
            director,
            CohortCreate(
                code="enterprise-batch",
                name_en="Enterprise Batch",
                name_ta="Synthetic Tamil batch",
                program_id=program.id,
                center_id=center.id,
                starts_on=date.today() - timedelta(days=30),
                ends_on=date.today() + timedelta(days=120),
                capacity=25,
            ),
            "cohort-create",
        )
        cohort = program_service.transition_cohort(
            db,
            org.id,
            cohort.id,
            director,
            StateCommand(expected_version=1, target="active", reason="Delivery ready"),
            "cohort-activate",
        )
        current = now()
        intake = program_service.create_cycle(
            db,
            org.id,
            director,
            CycleCreate(
                code="enterprise-2027",
                name_en="Enterprise intake",
                name_ta="Synthetic Tamil intake",
                program_id=program.id,
                cohort_id=cohort.id,
                form_id=form.id,
                opens_at=current - timedelta(days=1),
                closes_at=current + timedelta(days=10),
            ),
            "intake-create",
        )
        intake = program_service.transition_cycle(
            db,
            org.id,
            intake.id,
            director,
            StateCommand(expected_version=1, target="open", reason="Open intake"),
            "intake-open",
        )
        draft = application_service.create_cycle_draft(
            db, org.id, intake.id, applicant, "draft-create"
        )
        draft = application_service.save(
            db,
            org.id,
            draft.id,
            applicant,
            DraftSave(
                expected_version=draft.version,
                answers=[AnswerInput(field_id=form.fields[0].id, value="Community enterprise")],
            ),
            "draft-save",
        )
        submitted = application_service.submit(
            db,
            org.id,
            draft.id,
            applicant,
            SubmitCommand(
                expected_version=draft.version,
                accepted_acknowledgement_ids=[item.id for item in draft.form.acknowledgements],
            ),
            "application-submit",
        )
        intake = program_service.transition_cycle(
            db,
            org.id,
            intake.id,
            director,
            StateCommand(
                expected_version=intake.version,
                target="closed",
                reason="Application window completed",
            ),
            "intake-close",
        )
        yield (
            engine,
            org.id,
            director.id,
            reviewer.id,
            submitted.id,
            intake.id,
        )


def rubric() -> RubricUpdate:
    return RubricUpdate(
        expected_edit_version=1,
        criteria=[
            CriterionInput(
                key="business_idea",
                label_en="Business idea",
                label_ta="Synthetic Tamil business idea",
                weight=60,
                minimum_score=0,
                maximum_score=5,
            ),
            CriterionInput(
                key="feasibility",
                label_en="Feasibility",
                label_ta="Synthetic Tamil feasibility",
                weight=40,
                minimum_score=0,
                maximum_score=5,
            ),
        ],
    )


def test_versioned_rubric_assignment_and_conflict_declaration(selection_db) -> None:
    engine, org, director_id, reviewer_id, application_id, intake_id = selection_db
    with Session(engine) as db:
        director, reviewer = db.get(User, director_id), db.get(User, reviewer_id)
        assert director and reviewer
        cycle = service.create_cycle(
            db,
            org,
            director,
            SelectionCycleCreate(
                application_cycle_id=intake_id,
                code="enterprise-selection",
                name_en="Enterprise selection",
                name_ta="Synthetic Tamil selection",
            ),
            "selection-create",
        )
        workspace = service.workspace(db, org, director)
        draft_rubric = workspace.rubrics[0]
        updated = service.update_rubric(
            db, org, draft_rubric.id, director, rubric(), "rubric-update"
        )
        with pytest.raises(AuthError) as stale:
            service.publish_rubric(
                db,
                org,
                updated.id,
                director,
                RubricCommand(expected_edit_version=1),
                "stale-publish",
            )
        assert stale.value.status == 409
        published = service.publish_rubric(
            db,
            org,
            updated.id,
            director,
            RubricCommand(expected_edit_version=updated.edit_version),
            "rubric-publish",
        )
        assert published.state == "published"
        copied = service.copy_rubric(db, org, published.id, director, "rubric-copy")
        assert copied.version_number == 2 and len(copied.criteria) == 2
        replacement = service.publish_rubric(
            db,
            org,
            copied.id,
            director,
            RubricCommand(expected_edit_version=copied.edit_version),
            "rubric-republish",
        )
        assert replacement.state == "published"
        criterion = db.scalar(
            select(SelectionCriterion).where(SelectionCriterion.rubric_id == published.id)
        )
        assert criterion
        criterion.weight = 50
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()
        cycle = service.transition_cycle(
            db,
            org,
            cycle.id,
            director,
            CycleCommand(
                expected_version=cycle.version,
                target="active",
                reason="Rubric and reviewers approved",
            ),
            "selection-activate",
        )
        assignment = service.create_assignment(
            db,
            org,
            director,
            AssignmentCreate(
                selection_cycle_id=cycle.id,
                application_id=application_id,
                reviewer_user_id=reviewer.id,
            ),
            "review-assign",
        )
        assert assignment.conflict_status == "pending"
        application = db.get(Application, application_id)
        assert application and application.state == "under_review"
        applicant = db.scalar(select(User).where(User.person_id == application.person_id))
        assert applicant
        receipt = application_service.cycle_application(db, org, intake_id, applicant)
        assert receipt.state == "under_review"
        retried = application_service.submit(
            db,
            org,
            application.id,
            applicant,
            SubmitCommand(expected_version=1, accepted_acknowledgement_ids=[published.id]),
            "late-submit-retry",
        )
        assert retried.application_number == receipt.application_number
        history = db.scalar(
            select(ApplicationStatusHistory).where(
                ApplicationStatusHistory.application_id == application_id,
                ApplicationStatusHistory.to_state == "under_review",
            )
        )
        assert history and history.reason_code == "review_assigned"
        reviewer_workspace = service.workspace(db, org, reviewer)
        assert len(reviewer_workspace.assignments) == 1
        assert reviewer_workspace.applications == [] and reviewer_workspace.reviewers == []
        declared = service.declare_conflict(
            db,
            org,
            assignment.id,
            reviewer,
            ConflictCommand(expected_version=1, status="clear"),
            "conflict-clear",
        )
        assert declared.conflict_status == "clear" and declared.status == "in_review"
        stored = db.get(ReviewAssignment, assignment.id)
        assert stored and stored.version == 2
        application.application_number = "BYPASS"
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()


def test_selection_workspace_route_requires_scoped_permission(request) -> None:
    auth_context = request.getfixturevalue("auth")
    client, engine, _, _ = auth_context
    _, _, headers = signed_in(auth_context)
    with Session(engine) as db:
        user = db.scalar(select(User).where(User.email == "learner@example.com"))
        org = Organization(name="Selection route organization")
        role = db.scalar(select(Role).where(Role.name == "Selection Committee"))
        assert user and role
        db.add(org)
        db.flush()
        org_id = org.id
        role_id = role.id
        db.commit()
    root = f"/api/v1/selection/organizations/{org_id}"
    assert client.get(root + "/workspace", headers=headers).status_code == 403
    with Session(engine) as db:
        user = db.scalar(select(User).where(User.email == "learner@example.com"))
        assert user
        db.add(UserRole(user_id=user.id, role_id=role_id, organization_id=org_id))
        db.commit()
    response = client.get(root + "/workspace", headers=headers)
    assert response.status_code == 200
    assert response.json() == {
        "cycles": [],
        "rubrics": [],
        "applications": [],
        "reviewers": [],
        "assignments": [],
        "aggregates": [],
        "interviews": [],
        "decisions": [],
    }


def test_review_scoring_submission_moderation_and_aggregation(selection_db) -> None:
    engine, org, director_id, reviewer_id, application_id, intake_id = selection_db
    with Session(engine) as db:
        director, reviewer = db.get(User, director_id), db.get(User, reviewer_id)
        assert director and reviewer
        cycle = service.create_cycle(
            db,
            org,
            director,
            SelectionCycleCreate(
                application_cycle_id=intake_id,
                code="scored-selection",
                name_en="Scored selection",
                name_ta="Synthetic Tamil scored selection",
            ),
            "scored-cycle",
        )
        draft = service.workspace(db, org, director).rubrics[0]
        updated = service.update_rubric(db, org, draft.id, director, rubric(), "scored-rubric")
        published = service.publish_rubric(
            db,
            org,
            updated.id,
            director,
            RubricCommand(expected_edit_version=updated.edit_version),
            "scored-rubric-publish",
        )
        cycle = service.transition_cycle(
            db,
            org,
            cycle.id,
            director,
            CycleCommand(
                expected_version=cycle.version,
                target="active",
                reason="Scoring can begin",
            ),
            "scored-cycle-activate",
        )
        assignment = service.create_assignment(
            db,
            org,
            director,
            AssignmentCreate(
                selection_cycle_id=cycle.id,
                application_id=application_id,
                reviewer_user_id=reviewer.id,
            ),
            "scored-assignment",
        )
        assignment = service.declare_conflict(
            db,
            org,
            assignment.id,
            reviewer,
            ConflictCommand(expected_version=assignment.version, status="clear"),
            "scored-conflict",
        )
        first, second = published.criteria
        with pytest.raises(AuthError) as invalid:
            service.save_review(
                db,
                org,
                assignment.id,
                reviewer,
                ReviewSave(
                    expected_version=assignment.version,
                    scores=[ScoreInput(criterion_id=first.id, score=Decimal("6"))],
                ),
                "invalid-score",
            )
        assert invalid.value.status == 422
        saved = service.save_review(
            db,
            org,
            assignment.id,
            reviewer,
            ReviewSave(
                expected_version=assignment.version,
                scores=[
                    ScoreInput(criterion_id=first.id, score=Decimal("4")),
                    ScoreInput(criterion_id=second.id, score=Decimal("3")),
                ],
                internal_comment="Strong evidence with a manageable delivery risk.",
            ),
            "review-save",
        )
        assert saved.internal_comment and len(saved.scores) == 2
        submitted = service.submit_review(
            db,
            org,
            assignment.id,
            reviewer,
            ReviewSubmit(expected_version=saved.version),
            "review-submit",
        )
        assert submitted.status == "completed"
        assert submitted.weighted_score == Decimal("72.0000")
        with pytest.raises(AuthError) as immutable:
            service.save_review(
                db,
                org,
                assignment.id,
                reviewer,
                ReviewSave(expected_version=submitted.version, scores=[]),
                "late-edit",
            )
        assert immutable.value.status == 409
        stored_score = db.scalar(
            select(ApplicationScore).where(ApplicationScore.assignment_id == assignment.id)
        )
        assert stored_score
        stored_score.score = 1
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()
        completed_assignment = db.get(ReviewAssignment, assignment.id)
        assert completed_assignment
        db.delete(completed_assignment)
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()
        with pytest.raises(AuthError) as forbidden:
            service.moderate_review(
                db,
                org,
                assignment.id,
                reviewer,
                ModerationCommand(
                    expected_version=submitted.version,
                    status="excluded",
                    reason="Independent moderation required",
                ),
                "reviewer-moderation",
            )
        assert forbidden.value.status == 403
        excluded = service.moderate_review(
            db,
            org,
            assignment.id,
            director,
            ModerationCommand(
                expected_version=submitted.version,
                status="excluded",
                reason="Calibration outlier confirmed by moderation",
            ),
            "exclude-review",
        )
        workspace = service.workspace(db, org, director)
        aggregate = workspace.aggregates[0]
        assert aggregate.completed_reviews == 1
        assert aggregate.included_reviews == 0
        assert aggregate.excluded_reviews == 1
        assert aggregate.aggregate_score is None
        restored = service.moderate_review(
            db,
            org,
            assignment.id,
            director,
            ModerationCommand(
                expected_version=excluded.version,
                status="included",
                reason="Calibration review completed and score restored",
            ),
            "restore-review",
        )
        assert restored.moderation_status == "included"
        aggregate = service.workspace(db, org, director).aggregates[0]
        assert aggregate.aggregate_score == Decimal("72.00")
        reviewer_workspace = service.workspace(db, org, reviewer)
        assert reviewer_workspace.aggregates == []


def test_interview_decisions_override_and_cycle_finalization(selection_db) -> None:
    engine, org, director_id, reviewer_id, application_id, intake_id = selection_db
    with Session(engine) as db:
        director, reviewer = db.get(User, director_id), db.get(User, reviewer_id)
        assert director and reviewer
        cycle = service.create_cycle(
            db,
            org,
            director,
            SelectionCycleCreate(
                application_cycle_id=intake_id,
                code="final-selection",
                name_en="Final selection",
                name_ta="Synthetic Tamil final selection",
            ),
            "final-cycle",
        )
        draft = service.workspace(db, org, director).rubrics[0]
        updated = service.update_rubric(db, org, draft.id, director, rubric(), "final-rubric")
        published = service.publish_rubric(
            db,
            org,
            updated.id,
            director,
            RubricCommand(expected_edit_version=updated.edit_version),
            "final-publish",
        )
        cycle = service.transition_cycle(
            db,
            org,
            cycle.id,
            director,
            CycleCommand(
                expected_version=cycle.version, target="active", reason="Begin final review"
            ),
            "final-activate",
        )
        with pytest.raises(AuthError) as empty_finalization:
            service.transition_cycle(
                db,
                org,
                cycle.id,
                director,
                CycleCommand(
                    expected_version=cycle.version,
                    target="closed",
                    reason="Cannot finalize an empty cycle",
                ),
                "empty-finalize",
            )
        assert empty_finalization.value.status == 422
        assignment = service.create_assignment(
            db,
            org,
            director,
            AssignmentCreate(
                selection_cycle_id=cycle.id,
                application_id=application_id,
                reviewer_user_id=reviewer.id,
            ),
            "final-assign",
        )
        assignment = service.declare_conflict(
            db,
            org,
            assignment.id,
            reviewer,
            ConflictCommand(expected_version=assignment.version, status="clear"),
            "final-conflict",
        )
        first, second = published.criteria
        assignment = service.save_review(
            db,
            org,
            assignment.id,
            reviewer,
            ReviewSave(
                expected_version=assignment.version,
                scores=[
                    ScoreInput(criterion_id=first.id, score=Decimal("4")),
                    ScoreInput(criterion_id=second.id, score=Decimal("3")),
                ],
                internal_comment="Proceed to panel interview.",
            ),
            "final-review-save",
        )
        service.submit_review(
            db,
            org,
            assignment.id,
            reviewer,
            ReviewSubmit(expected_version=assignment.version),
            "final-review-submit",
        )
        application = db.get(Application, application_id)
        assert application
        with pytest.raises(AuthError) as reviewer_decision:
            service.record_decision(
                db,
                org,
                cycle.id,
                application.id,
                reviewer,
                DecisionCommand(
                    expected_application_version=application.version,
                    target="shortlisted",
                    reason="Unauthorized shortlist",
                ),
                "reviewer-shortlist",
            )
        assert reviewer_decision.value.status == 403
        shortlisted = service.record_decision(
            db,
            org,
            cycle.id,
            application.id,
            director,
            DecisionCommand(
                expected_application_version=application.version,
                target="shortlisted",
                reason="Review evidence meets interview threshold",
            ),
            "shortlist",
        )
        assert shortlisted.to_state == "shortlisted"
        application = db.get(Application, application_id)
        assert application and application.state == "shortlisted"
        start = datetime.now(UTC) + timedelta(days=1)
        interview = service.create_interview(
            db,
            org,
            director,
            InterviewCreate(
                selection_cycle_id=cycle.id,
                application_id=application.id,
                starts_at=start,
                ends_at=start + timedelta(hours=1),
                mode="online",
                panel_user_ids=[reviewer.id],
            ),
            "interview-schedule",
        )
        assert len(interview.panel) == 1
        application = db.get(Application, application_id)
        assert application and application.state == "interview_scheduled"
        with pytest.raises(AuthError) as premature:
            service.record_decision(
                db,
                org,
                cycle.id,
                application.id,
                director,
                DecisionCommand(
                    expected_application_version=application.version,
                    target="selected",
                    reason="Premature decision",
                ),
                "premature-decision",
            )
        assert premature.value.status == 422
        scored = service.submit_interview_score(
            db,
            org,
            interview.id,
            reviewer,
            PanelScoreSubmit(
                expected_version=interview.panel[0].version,
                score=Decimal("84"),
                comment="Strong panel response.",
            ),
            "panel-score",
        )
        with pytest.raises(AuthError) as repeated:
            service.submit_interview_score(
                db,
                org,
                interview.id,
                reviewer,
                PanelScoreSubmit(
                    expected_version=scored.panel[0].version,
                    score=Decimal("85"),
                    comment="Attempted change",
                ),
                "panel-score-repeat",
            )
        assert repeated.value.status == 409
        panel_row = db.get(InterviewPanelMember, scored.panel[0].id)
        assert panel_row
        panel_row.score = 1
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()
        completed = service.complete_interview(
            db,
            org,
            interview.id,
            director,
            InterviewComplete(expected_version=interview.version),
            "interview-complete",
        )
        assert completed.average_score == Decimal("84.0000")
        application = db.get(Application, application_id)
        assert application
        selected = service.record_decision(
            db,
            org,
            cycle.id,
            application.id,
            director,
            DecisionCommand(
                expected_application_version=application.version,
                target="selected",
                reason="Review and interview evidence approved",
            ),
            "select",
        )
        assert selected.aggregate_score_snapshot == Decimal("72.00")
        assert selected.interview_score_snapshot == Decimal("84.00")
        application = db.get(Application, application_id)
        assert application
        with pytest.raises(AuthError) as unchanged:
            service.record_decision(
                db,
                org,
                cycle.id,
                application.id,
                director,
                DecisionCommand(
                    expected_application_version=application.version,
                    target="selected",
                    reason="No actual change",
                    override=True,
                ),
                "unchanged-override",
            )
        assert unchanged.value.status == 409
        application = db.get(Application, application_id)
        assert application
        overridden = service.record_decision(
            db,
            org,
            cycle.id,
            application.id,
            director,
            DecisionCommand(
                expected_application_version=application.version,
                target="waitlisted",
                reason="Capacity correction after final review",
                override=True,
            ),
            "override-waitlist",
        )
        assert overridden.is_override and overridden.to_state == "waitlisted"
        application = db.get(Application, application_id)
        assert application
        restored = service.record_decision(
            db,
            org,
            cycle.id,
            application.id,
            director,
            DecisionCommand(
                expected_application_version=application.version,
                target="selected",
                reason="Capacity restored by authorized director",
                override=True,
            ),
            "override-restore",
        )
        assert restored.is_override and restored.to_state == "selected"
        decision_row = db.get(SelectionDecision, restored.id)
        assert decision_row
        decision_row.reason = "Tampered"
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()
        cycle = service.transition_cycle(
            db,
            org,
            cycle.id,
            director,
            CycleCommand(
                expected_version=cycle.version,
                target="closed",
                reason="All assigned applications finalized",
            ),
            "cycle-finalize",
        )
        assert cycle.state == "closed"
        workspace = service.workspace(db, org, director)
        assert workspace.interviews[0].status == "completed"
        assert len(workspace.decisions) == 4
        reviewer_workspace = service.workspace(db, org, reviewer)
        assert len(reviewer_workspace.interviews) == 1
        assert reviewer_workspace.decisions == []
        application = db.get(Application, application_id)
        assert application and application.state == "selected"
        applicant = db.scalar(select(User).where(User.person_id == application.person_id))
        assert applicant
        receipt = application_service.cycle_application(db, org, intake_id, applicant)
        assert receipt.state == "selected"
        catalog = program_service.catalog(db, org, director)
        assert len(catalog.enrollment_candidates) == 1
        with pytest.raises(AuthError) as unauthorized_conversion:
            program_service.convert_enrollment(
                db,
                org,
                reviewer,
                EnrollmentConvert(
                    application_id=application.id,
                    expected_application_version=application.version,
                    reason="Unauthorized enrollment attempt",
                ),
                "enrollment-forbidden",
            )
        assert unauthorized_conversion.value.status == 403
        converted = program_service.convert_enrollment(
            db,
            org,
            director,
            EnrollmentConvert(
                application_id=application.id,
                expected_application_version=application.version,
                reason="Final selection approved for enrollment",
            ),
            "enrollment-convert",
        )
        assert converted.participant.person_id == applicant.person_id
        assert converted.enrollment.application_id == application.id
        assert db.scalar(
            select(DomainOutbox).where(DomainOutbox.aggregate_id == converted.enrollment.id)
        )
        application = db.get(Application, application.id)
        assert application and application.state == "enrolled"
        with pytest.raises(AuthError) as duplicate:
            program_service.convert_enrollment(
                db,
                org,
                director,
                EnrollmentConvert(
                    application_id=application.id,
                    expected_application_version=application.version,
                    reason="Duplicate conversion attempt",
                ),
                "enrollment-duplicate",
            )
        assert duplicate.value.status == 409
        enrollment = db.get(Enrollment, converted.enrollment.id)
        assert enrollment
        cohort = program_service._cohort(db, org, enrollment.cohort_id)
        starts = datetime.combine(cohort.starts_on + timedelta(days=2), datetime.min.time(), UTC)
        session = program_service.create_session(
            db,
            org,
            director,
            SessionCreate(
                cohort_id=cohort.id,
                title_en="Business foundations",
                title_ta="Synthetic Tamil session",
                starts_at=starts,
                ends_at=starts + timedelta(hours=2),
                mode="in_person",
                location="Training room 1",
            ),
            "session-create",
        )
        timeline = program_service.my_timeline(db, org, applicant)
        participant_role = db.scalar(select(Role).where(Role.name == "Participant"))
        assert participant_role
        db.add(
            UserRole(
                user_id=reviewer.id,
                role_id=participant_role.id,
                organization_id=org,
            )
        )
        db.commit()
        with pytest.raises(AuthError) as wrong_owner:
            program_service.my_timeline(db, org, reviewer)
        assert wrong_owner.value.status == 404
        assert timeline.sessions[0].id == session.id
        assert {event.kind for event in timeline.events} == {
            "application",
            "selection",
            "enrollment",
            "session",
        }
        assert [event.occurred_at for event in timeline.events] == sorted(
            event.occurred_at for event in timeline.events
        )
        history = db.scalar(
            select(ParticipantStatusHistory).where(
                ParticipantStatusHistory.participant_id == converted.participant.id
            )
        )
        assert history
        history.reason = "Tampered"
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()
        enrolled_receipt = application_service.cycle_application(db, org, intake_id, applicant)
        assert enrolled_receipt.state == "enrolled"
