import json
import os
from datetime import UTC, datetime, time, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.orm import Session
from test_identity import auth  # noqa: F401
from test_lms_db import learning_context

from app.modules.applications.models import Application, ApplicationForm
from app.modules.attendance.models import AttendanceRecord
from app.modules.business_plans.models import (
    BusinessPlan,
    BusinessPlanReview,
    BusinessPlanSubmission,
)
from app.modules.businesses.models import BusinessFollowUp, BusinessOutcomeSnapshot, BusinessProfile
from app.modules.crm.models import Lead, LeadConversion
from app.modules.helpdesk.models import HelpdeskHistory, HelpdeskTicket
from app.modules.identity.models import Person, User, now
from app.modules.knowledge.models import FundingCase, FundingHistory, KnowledgeItem
from app.modules.lms.models import (
    AssignmentGrade,
    AssignmentSubmission,
    Certificate,
    CertificateTemplate,
    Course,
    CourseEnrollment,
    CourseModule,
    LearningAssignment,
    Lesson,
    LessonProgress,
    Quiz,
    QuizAttempt,
)
from app.modules.mentoring.models import FollowUp, MentorAssignment, MentoringSession, MentorProfile
from app.modules.programs.models import (
    ApplicationCycle,
    Cohort,
    Enrollment,
    Program,
    ProgramSession,
)
from app.modules.reports.definitions import operational_metric_definitions
from app.modules.reports.metrics import APPLICATION_SQL, LATEST_BUSINESS_SQL, SCOPE_SQL
from app.modules.reports.metrics import build_operational_metrics as build

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)


def facts(request):
    context, headers, org, other, cohort_id, enrollment_id, owner = learning_context(request)
    engine = context[1]
    anchor = datetime.combine(now().date() - timedelta(days=10), time(12), UTC)
    with Session(engine) as db:
        enrollment = db.get(Enrollment, enrollment_id)
        user = db.get(User, owner)
        cohort = db.get(Cohort, cohort_id)
        assert enrollment and user and cohort
        enrollment.enrolled_at = anchor
        cycle = db.get(ApplicationCycle, db.get(Application, enrollment.application_id).cycle_id)
        second = Cohort(
            organization_id=org,
            program_id=cohort.program_id,
            center_id=cohort.center_id,
            code="report-second",
            name_en="Second cohort",
            name_ta="இரண்டாம் குழு",
            starts_on=anchor.date(),
            ends_on=now().date(),
            state="completed",
        )
        db.add(second)
        db.flush()
        cycle_two = ApplicationCycle(
            organization_id=org,
            program_id=cohort.program_id,
            cohort_id=second.id,
            form_id=cycle.form_id,
            code="report-cycle",
            name_en="Second intake",
            name_ta="இரண்டாம் சேர்க்கை",
            opens_at=anchor - timedelta(days=5),
            closes_at=anchor + timedelta(days=5),
            state="closed",
        )
        peer = Person(display_name="Synthetic second person")
        no_application = Person(display_name="Converted without an application")
        db.add_all([cycle_two, peer, no_application])
        db.flush()
        apps = []
        for index, (person_id, state, cycle_id) in enumerate(
            [
                (user.person_id, "enrolled", cycle_two.id),
                (peer.id, "selected", cycle.id),
                (no_application.id, "rejected", cycle.id),
            ]
        ):
            app = Application(
                organization_id=org,
                person_id=person_id,
                form_id=cycle.form_id,
                cycle_id=cycle_id,
                state=state,
                application_number=f"REPORT-{index}",
                submitted_at=anchor,
            )
            db.add(app)
            apps.append(app)
        db.flush()
        second_enrollment = Enrollment(
            organization_id=org,
            participant_id=enrollment.participant_id,
            program_id=cohort.program_id,
            cohort_id=second.id,
            application_id=apps[0].id,
            status="completed",
            enrolled_at=anchor,
        )
        db.add(second_enrollment)
        # Two lead links to the same registered person must not duplicate registrations.
        unlinked = Person(display_name="No submitted application")
        db.add(unlinked)
        db.flush()
        foreign_program = Program(
            organization_id=other,
            code="foreign-report",
            name_en="Foreign program",
            name_ta="வேறு திட்டம்",
        )
        foreign_form = ApplicationForm(
            organization_id=other,
            version=1,
            title_en="Foreign form",
            title_ta="வேறு படிவம்",
        )
        db.add_all([foreign_program, foreign_form])
        db.flush()
        foreign_cycle = ApplicationCycle(
            organization_id=other,
            program_id=foreign_program.id,
            form_id=foreign_form.id,
            code="foreign-cycle",
            name_en="Foreign cycle",
            name_ta="வேறு சுற்று",
            opens_at=anchor - timedelta(days=5),
            closes_at=anchor + timedelta(days=5),
            state="closed",
        )
        db.add(foreign_cycle)
        db.flush()
        db.add(
            Application(
                organization_id=other,
                person_id=unlinked.id,
                form_id=foreign_form.id,
                cycle_id=foreign_cycle.id,
                state="submitted",
                application_number="FOREIGN-REPORT",
                submitted_at=anchor,
            )
        )
        leads = []
        for index in range(5):
            lead = Lead(
                organization_id=org,
                name=f"Synthetic lead {index}",
                dedupe_hash=f"{index:064}",
                source="web" if index < 3 else "event",
                campaign="Synthetic campaign",
                status="converted" if index < 4 else "new",
                created_at=anchor,
            )
            db.add(lead)
            leads.append(lead)
        db.flush()
        for index, person in enumerate([user.person_id, user.person_id, unlinked.id]):
            db.add(
                LeadConversion(
                    organization_id=org,
                    lead_id=leads[index].id,
                    person_id=person,
                    actor_user_id=owner,
                    source="web",
                    campaign="Synthetic campaign",
                    lead_version=1,
                    reason="Synthetic conversion evidence",
                    created_at=anchor,
                )
            )
        merged = Lead(
            organization_id=org,
            name="Merged excluded",
            dedupe_hash="z" * 64,
            status="merged",
            merged_into_id=leads[0].id,
            created_at=anchor,
        )
        old = Lead(
            organization_id=org,
            name="Old excluded",
            dedupe_hash="y" * 64,
            created_at=anchor - timedelta(days=40),
        )
        db.add_all([merged, old])

        course = Course(
            organization_id=org,
            code="reports-course",
            title_en="Synthetic course",
            title_ta="செயற்கை பாடம்",
            description_en="Synthetic",
            description_ta="செயற்கை",
        )
        db.add(course)
        db.flush()
        module = CourseModule(
            organization_id=org,
            course_id=course.id,
            position=1,
            title_en="Module",
            title_ta="பகுதி",
        )
        ce = CourseEnrollment(
            organization_id=org,
            course_id=course.id,
            enrollment_id=enrollment_id,
            started_at=anchor,
            completed_at=anchor + timedelta(hours=1),
            status="completed",
        )
        db.add_all([module, ce])
        db.flush()
        lesson = Lesson(
            organization_id=org,
            course_id=course.id,
            module_id=module.id,
            position=1,
            title_en="Lesson",
            title_ta="பாடம்",
            body_en="Synthetic",
            body_ta="செயற்கை",
        )
        db.add(lesson)
        db.flush()
        quiz = Quiz(
            organization_id=org,
            course_id=course.id,
            lesson_id=lesson.id,
            position=1,
            title_en="Quiz",
            title_ta="வினா",
            instructions_en="Synthetic",
            instructions_ta="செயற்கை",
            passing_percent=50,
            max_attempts=3,
        )
        assignment = LearningAssignment(
            organization_id=org,
            course_id=course.id,
            lesson_id=lesson.id,
            position=1,
            title_en="Assignment",
            title_ta="ஒப்படைப்பு",
            instructions_en="Synthetic",
            instructions_ta="செயற்கை",
            maximum_points=10,
            passing_points=5,
            max_submissions=3,
        )
        template = CertificateTemplate(
            organization_id=org,
            course_id=course.id,
            code="reports-certificate",
            title_en="Certificate",
            title_ta="சான்று",
            statement_en="Synthetic",
            statement_ta="செயற்கை",
            issuer_name="Synthetic issuer",
        )
        db.add_all([quiz, assignment, template])
        db.flush()
        db.add(
            LessonProgress(
                organization_id=org,
                course_id=course.id,
                course_enrollment_id=ce.id,
                lesson_id=lesson.id,
                completed_at=anchor,
            )
        )
        for number, score in enumerate([40, 80], 1):
            db.add(
                QuizAttempt(
                    organization_id=org,
                    course_id=course.id,
                    course_enrollment_id=ce.id,
                    quiz_id=quiz.id,
                    attempt_number=number,
                    score_points=score,
                    maximum_points=100,
                    percent=score,
                    passed=score >= 50,
                    submitted_at=anchor,
                )
            )
        for revision in (1, 2):
            submission = AssignmentSubmission(
                organization_id=org,
                course_id=course.id,
                course_enrollment_id=ce.id,
                assignment_id=assignment.id,
                revision=revision,
                response_text="Synthetic work",
                submitted_at=anchor,
            )
            db.add(submission)
            db.flush()
            if revision == 1:
                db.add(
                    AssignmentGrade(
                        organization_id=org,
                        course_id=course.id,
                        assignment_id=assignment.id,
                        submission_id=submission.id,
                        grader_user_id=owner,
                        score_points=8,
                        passed=True,
                        feedback="Synthetic feedback",
                        graded_at=anchor,
                    )
                )
        db.add(
            Certificate(
                organization_id=org,
                course_id=course.id,
                course_enrollment_id=ce.id,
                template_id=template.id,
                issued_by_user_id=owner,
                verification_code="report-synthetic",
                recipient_name="Synthetic",
                course_title_en="Course",
                course_title_ta="பாடம்",
                certificate_title_en="Certificate",
                certificate_title_ta="சான்று",
                statement_en="Synthetic",
                statement_ta="செயற்கை",
                issuer_name="Synthetic",
                template_version=1,
                issued_at=anchor,
            )
        )
        for number, status in enumerate(["present", "late", "absent", "excused", None]):
            session = ProgramSession(
                organization_id=org,
                cohort_id=cohort_id,
                title_en=f"Session {number}",
                title_ta="அமர்வு",
                starts_at=anchor,
                ends_at=anchor + timedelta(hours=1),
                mode="online",
            )
            db.add(session)
            db.flush()
            if status:
                db.add(
                    AttendanceRecord(
                        organization_id=org,
                        session_id=session.id,
                        enrollment_id=enrollment_id,
                        status=status,
                        source="manual",
                        marked_by_user_id=owner,
                        marked_at=anchor,
                    )
                )
        profile = BusinessProfile(
            organization_id=org,
            enrollment_id=enrollment_id,
            name="Synthetic enterprise",
            sector="Food",
            products_services="Synthetic",
            stage="idea",
            team_size=1,
            investment_band="none",
            funding_status="none",
            revenue_band="none",
            created_at=anchor,
        )
        plan = BusinessPlan(organization_id=org, enrollment_id=enrollment_id)
        db.add_all([profile, plan])
        db.flush()
        for number, jobs in enumerate([9, 3], 1):
            followup = BusinessFollowUp(
                organization_id=org,
                profile_id=profile.id,
                offset_days=number,
                due_on=anchor.date() + timedelta(days=number),
                status="completed",
                completed_at=anchor,
            )
            submission = BusinessPlanSubmission(
                organization_id=org,
                plan_id=plan.id,
                number=number,
                snapshot={"overview": "Synthetic"},
                submitted_by_user_id=owner,
                created_at=anchor,
            )
            db.add_all([followup, submission])
            db.flush()
            db.add(
                BusinessOutcomeSnapshot(
                    organization_id=org,
                    follow_up_id=followup.id,
                    author_user_id=owner,
                    reported_on=anchor.date() + timedelta(days=number),
                    business_started=True,
                    business_active=number == 2,
                    jobs_created=jobs,
                    funding_band="none",
                    revenue_band="none",
                )
            )
            db.add(
                BusinessPlanReview(
                    organization_id=org,
                    submission_id=submission.id,
                    reviewer_user_id=owner,
                    decision="approved",
                    comments={},
                    reason="Synthetic approval",
                    created_at=anchor,
                )
            )
        item = KnowledgeItem(
            organization_id=org,
            kind="funding",
            locale="en",
            slug="report-funding",
            title="Synthetic funding",
            provider="Synthetic",
            type="Synthetic",
            description="Synthetic",
            eligibility="Synthetic",
            sector="All",
            geography="All",
            application_process="Synthetic",
            official_url="https://example.invalid/funding",
            last_verified_at=anchor.date(),
        )
        mentor = MentorProfile(
            organization_id=org,
            user_id=owner,
            headline="Synthetic mentor",
        )
        db.add_all([item, mentor])
        db.flush()
        funding = FundingCase(
            organization_id=org,
            participant_id=enrollment.participant_id,
            item_id=item.id,
            item_title=item.title,
            locale="en",
            source={"title": "Synthetic"},
            created_at=anchor,
        )
        assignment_row = MentorAssignment(
            organization_id=org,
            mentor_profile_id=mentor.id,
            enrollment_id=enrollment_id,
            starts_on=anchor.date(),
            assigned_by_user_id=owner,
        )
        db.add_all([funding, assignment_row])
        db.flush()
        for version, status in enumerate(
            [
                "interested",
                "eligibility_check",
                "document_preparation",
                "applied",
                "under_review",
                "approved",
                "disbursed",
            ],
            1,
        ):
            if version > 1:
                funding.status = status
                funding.version = version
                db.flush()
            db.add(
                FundingHistory(
                    organization_id=org,
                    case_id=funding.id,
                    version=version,
                    status=status,
                    reason="Synthetic evidence",
                    actor_user_id=owner,
                    created_at=anchor,
                )
            )
        db.add_all(
            [
                MentoringSession(
                    organization_id=org,
                    assignment_id=assignment_row.id,
                    starts_at=anchor,
                    ends_at=anchor + timedelta(hours=1),
                    mode="phone",
                    topic="Synthetic",
                    status="completed",
                    completed_at=anchor + timedelta(hours=1),
                ),
                FollowUp(
                    organization_id=org,
                    assignment_id=assignment_row.id,
                    purpose="Synthetic",
                    due_at=anchor,
                    state="completed",
                    completed_at=anchor,
                ),
            ]
        )
        ticket = HelpdeskTicket(
            organization_id=org,
            owner_participant_id=enrollment.participant_id,
            owner_user_id=owner,
            request_id=uuid4(),
            request_digest="a" * 64,
            number="REPORT-TICKET",
            category="general",
            subject="Synthetic ticket",
            created_at=anchor,
        )
        db.add(ticket)
        db.flush()
        states = [
            "open",
            "assigned",
            "in_progress",
            "resolved",
            "open",
            "assigned",
            "in_progress",
            "resolved",
        ]
        for version, status in enumerate(states, 1):
            if version > 1:
                ticket.version = version
                ticket.status = status
                ticket.assignee_user_id = None if status == "open" else owner
                db.flush()
            db.add(
                HelpdeskHistory(
                    organization_id=org,
                    ticket_id=ticket.id,
                    version=version,
                    event="status",
                    status=status,
                    priority="normal",
                    reason="Synthetic evidence",
                    actor_user_id=owner,
                    created_at=anchor + timedelta(hours=version - 1),
                )
            )
        db.commit()
        return engine, org, other, cohort.program_id, cohort_id, second.id, anchor


def test_operational_arithmetic_scopes_distinct_facts_and_query_budget(request, tmp_path):
    engine, org, other, program, cohort, second, anchor = facts(request)
    start = now().date() - timedelta(days=30)
    end = now().date() - timedelta(days=1)
    statements = []

    def collect(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith(("SELECT", "WITH")):
            statements.append(statement)

    event.listen(engine, "before_cursor_execute", collect)
    try:
        with Session(engine) as db:
            items = build(db, org, from_date=start, through_date=end)
    finally:
        event.remove(engine, "before_cursor_execute", collect)
    assert len(statements) == 18
    organization_select_count = len(statements)
    metrics = {m.key: m for m in items}
    expected = {
        "leads": 5,
        "registrations": 2,
        "applications": 4,
        "selected_applications": 3,
        "lead_to_application_percent": 40,
        "application_to_selection_percent": 75,
        "selection_to_enrollment_percent": 66.6667,
        "enrollments": 2,
        "active_participants": 1,
        "completed_enrollments": 1,
        "withdrawn_enrollments": 0,
        "valid_certificates": 1,
        "course_starts": 1,
        "course_completions": 1,
        "lesson_completions": 1,
        "quiz_attempts": 2,
        "quiz_pass_percent": 50,
        "quiz_mean_percent": 60,
        "assignment_submissions": 2,
        "assignment_grades": 1,
        "assignment_pass_percent": 100,
        "attendance_recorded": 3,
        "attendance_percent": 66.6667,
        "idea_profiles": 1,
        "submitted_plans": 1,
        "approved_plans": 1,
        "business_outcome_reports": 1,
        "businesses_started": 1,
        "businesses_active": 1,
        "jobs_created": 3,
        "funding_applied_cases": 1,
        "funding_approved_cases": 1,
        "funding_disbursed_cases": 1,
        "tickets_created": 1,
        "tickets_resolved": 1,
        "ticket_resolution_hours": 3,
        "mentor_sessions": 1,
        "mentor_follow_ups": 1,
        "business_follow_ups": 2,
    }
    assert {key: metrics[key].value for key in expected} == expected
    assert metrics["funding_facilitated_amount"].value is None
    assert metrics["attendance_percent"].numerator == 2
    assert metrics["attendance_percent"].denominator == 3
    assert metrics["ticket_resolution_hours"].denominator == 1
    assert (
        sum(b.count for b in metrics["registrations"].breakdown if b.key.startswith("source:")) == 2
    )
    assert metrics["mentor_follow_ups"].breakdown[0].key == "completed"
    with Session(engine) as db:
        statements.clear()
        event.listen(engine, "before_cursor_execute", collect)
        try:
            scoped = {
                m.key: m
                for m in build(db, org, from_date=start, through_date=end, cohort_id=second)
            }
        finally:
            event.remove(engine, "before_cursor_execute", collect)
        assert len(statements) == 15
        filtered_select_count = len(statements)
        assert scoped["applications"].value == scoped["enrollments"].value == 1
        assert scoped["completed_enrollments"].value == 1
        assert scoped["active_participants"].value == 0
        assert scoped["course_starts"].value == scoped["jobs_created"].value == 0
        # Participant-level funding/support belongs to both memberships, once per fact.
        assert scoped["funding_disbursed_cases"].value == scoped["tickets_created"].value == 1
        assert scoped["leads"].value is scoped["registrations"].value is None
        assert "membership" in scoped["tickets_created"].caveat_en
        by_program = {
            m.key: m for m in build(db, org, from_date=start, through_date=end, program_id=program)
        }
        assert by_program["applications"].value == 4
        assert by_program["funding_applied_cases"].value == 1
        foreign = build(db, other, from_date=start, through_date=end)
        assert next(m.value for m in foreign if m.key == "applications") == 1
        assert all(m.value in (0, None) for m in foreign if m.key != "applications")
        earlier = {m.key: m for m in build(db, org, from_date=start, through_date=anchor.date())}
        assert earlier["jobs_created"].value == 0
        assert earlier["funding_applied_cases"].value == 1
        # Inclusive UTC day includes noon, and a later day excludes it.
        later = {
            m.key: m
            for m in build(db, org, from_date=anchor.date() + timedelta(days=1), through_date=end)
        }
        assert later["course_starts"].value == 0
        assert later["jobs_created"].value == 3
        evidence = {}
        params = {
            "organization_id": org,
            "program_id": program,
            "cohort_id": cohort,
            "start_at": datetime.combine(start, time.min, UTC),
            "end_at": datetime.combine(end + timedelta(days=1), time.min, UTC),
            "from_date": start,
            "through_date": end,
        }
        for name, sql in (
            ("application_funnel", APPLICATION_SQL),
            ("latest_business", LATEST_BUSINESS_SQL),
        ):
            plan = db.execute(
                text("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + SCOPE_SQL + sql), params
            ).scalar_one()
            evidence[name] = plan
            assert plan[0]["Plan"]["Actual Rows"] == 1
        (tmp_path / "operational-query-evidence.json").write_text(
            json.dumps(
                {
                    "select_count": organization_select_count,
                    "filtered_select_count": filtered_select_count,
                    "plans": evidence,
                },
                indent=2,
            ),
            encoding="utf-8",
        )


def test_zero_denominators_missing_data_dictionary_and_bounded_breakdowns(request):
    context, _, org, other, _, _, _ = learning_context(request)
    engine = context[1]
    current = now().date()
    with Session(engine) as db:
        for index in range(12):
            db.add(
                Lead(
                    organization_id=org,
                    name="Synthetic",
                    dedupe_hash=f"{index:064x}",
                    source=f"source-{index}",
                    campaign=f"campaign-{index}",
                )
            )
        db.commit()
        metrics = {m.key: m for m in build(db, org, from_date=current, through_date=current)}
        assert metrics["leads"].value == 12
        assert metrics["lead_to_application_percent"].value == 0
        assert metrics["lead_to_application_percent"].denominator == 12
        for dimension in ("source", "campaign"):
            entries = [b for b in metrics["leads"].breakdown if b.key.startswith(dimension + ":")]
            assert len(entries) == 9
            assert sum(b.count for b in entries) == 12
            assert next(b.count for b in entries if b.key == dimension + ":Other") == 4
        for key in (
            "application_to_selection_percent",
            "selection_to_enrollment_percent",
            "attendance_percent",
            "quiz_pass_percent",
            "quiz_mean_percent",
            "assignment_pass_percent",
            "ticket_resolution_hours",
        ):
            assert metrics[key].value is None
            assert metrics[key].denominator == 0
        assert metrics["funding_facilitated_amount"].value is None
        assert metrics["funding_facilitated_amount"].numerator is None
        assert metrics["funding_facilitated_amount"].unit == "INR"
        assert all(
            m.value in (0, None) for m in build(db, other, from_date=current, through_date=current)
        )
    definitions = operational_metric_definitions()
    assert len({m.key for m in definitions}) == len(definitions) == 40
    assert {m.group for m in definitions} == {
        "marketing",
        "program",
        "learning",
        "entrepreneurship",
        "funding",
        "support",
    }
    for definition in definitions:
        assert definition.label_en and definition.label_ta
        assert definition.definition_en and definition.definition_ta
        assert definition.source and definition.temporal_basis and definition.unit
        assert definition.caveat_en and definition.caveat_ta
        assert definition.value is definition.numerator is definition.denominator is None


def test_metric_dates_are_inclusive_utc_days_not_database_local_dates(request):
    context, _, org, _, _, _, _ = learning_context(request)
    start = now().date() - timedelta(days=4)
    end = start + timedelta(days=1)
    first = datetime.combine(start, time.min, UTC)
    following = datetime.combine(end + timedelta(days=1), time.min, UTC)
    with Session(context[1]) as db:
        for index, stamp in enumerate(
            [
                first - timedelta(microseconds=1),
                first,
                following - timedelta(microseconds=1),
                following,
            ]
        ):
            db.add(
                Lead(
                    organization_id=org,
                    name="Synthetic UTC boundary",
                    dedupe_hash=f"{index:064x}",
                    created_at=stamp,
                )
            )
        db.commit()
        # A non-UTC database session must not change an explicitly UTC calendar window.
        db.execute(text("SET LOCAL TIME ZONE 'Asia/Kolkata'"))
        metric = {m.key: m for m in build(db, org, from_date=start, through_date=end)}
        assert metric["leads"].value == 2
        assert metric["lead_to_application_percent"].denominator == 2
        assert metric["lead_to_application_percent"].value == 0
