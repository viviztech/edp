"""Synthetic browser E2E; run with isolated PostgreSQL and local servers only."""

import json
import os
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from app.modules.applications.models import Application, ApplicationForm
from app.modules.attendance.models import AttendancePolicy, AttendanceRecord
from app.modules.business_plans.models import (
    BusinessPlan,
    BusinessPlanReview,
    BusinessPlanRevision,
    BusinessPlanSubmission,
)
from app.modules.businesses.models import BusinessProfile, BusinessProfileRevision
from app.modules.identity.models import (
    AuditLog,
    AuthDelivery,
    Organization,
    Person,
    Role,
    User,
    UserRole,
    VerificationToken,
)
from app.modules.identity.security import hasher
from app.modules.identity.service import audit, seed_roles
from app.modules.lms.models import (
    AssignmentGrade,
    AssignmentSubmission,
    Certificate,
    CertificateTemplate,
    CohortCourse,
    Course,
    CourseEnrollment,
    LessonProgress,
    QuizAttempt,
)
from app.modules.mentoring.models import (
    ActionItem,
    FollowUp,
    Goal,
    MentorAssignment,
    MentoringFeedback,
    MentoringNote,
    MentoringSession,
    MentorProfile,
)
from app.modules.programs import service as program_service
from app.modules.programs.models import (
    DomainOutbox,
    Enrollment,
    Participant,
    ProgramSession,
    ProgramStaffAssignment,
)
from app.modules.programs.schemas import (
    CenterCreate,
    CohortCreate,
    CycleCreate,
    NamedCreate,
    StateCommand,
)
from app.modules.selection.models import (
    Interview,
    ReviewAssignment,
    SelectionCycle,
    SelectionDecision,
)
from cryptography.fernet import Fernet
from playwright.sync_api import expect, sync_playwright
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

engine = create_engine(os.environ["DATABASE_URL"])
assert engine.url.database in {"edp_foundation_e2e", "edp_test"}, (
    "Isolated test DB required"
)
base = os.environ["WEB_ORIGIN"]
assert base.startswith(("http://127.0.0.1:", "http://localhost:"))
email = "synthetic-" + uuid4().hex[:12] + "@example.com"
password = secrets.token_urlsafe(24)
coordinator_email = "coordinator-" + uuid4().hex[:12] + "@example.com"
coordinator_password = secrets.token_urlsafe(24)
trainer_email = "trainer-" + uuid4().hex[:12] + "@example.com"
trainer_password = secrets.token_urlsafe(24)
plan_mentor_email = "plan-mentor-" + uuid4().hex[:12] + "@example.com"
plan_mentor_password = secrets.token_urlsafe(24)
unrelated_email = "unrelated-" + uuid4().hex[:12] + "@example.com"
unrelated_password = secrets.token_urlsafe(24)


def latest_token(purpose):
    with Session(engine) as db:
        row = db.scalar(
            select(AuthDelivery)
            .join(VerificationToken)
            .join(User)
            .where(User.email == email, VerificationToken.purpose == purpose)
            .order_by(AuthDelivery.created_at.desc())
            .limit(1)
        )
        assert row is not None
        return json.loads(
            Fernet(os.environ["AUTH_DELIVERY_KEY"].encode()).decrypt(
                row.encrypted_payload.encode()
            )
        )["token"]


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        channel=os.getenv("PLAYWRIGHT_CHANNEL"), headless=True
    )
    participant_context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = participant_context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    pending = set()
    page.on("request", lambda request: pending.add(request.url))
    page.on("requestfinished", lambda request: pending.discard(request.url))
    page.on("requestfailed", lambda request: pending.discard(request.url))
    page.goto(base + "/en/admin")
    page.wait_for_url("**/en/account")
    # Next.js keeps background RSC prefetch requests open in this Chrome build.
    # The first run waited for networkidle and inspected a fully hydrated form.
    # Assert actual user-visible readiness instead of using background network quiescence.
    page.wait_for_load_state("domcontentloaded")
    expect(page.get_by_label("Email", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name="Your account")).to_be_visible()
    evidence = Path(".tool-cache/evidence")
    evidence.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(evidence / "account-en.png"), full_page=True)
    page.get_by_role("button", name="Create account", exact=True).click()
    page.get_by_label("Name", exact=True).fill("Synthetic E2E")
    page.get_by_label("Email", exact=True).fill(email)
    page.get_by_label("Password", exact=True).fill(password)
    page.locator("form").get_by_role(
        "button", name="Create account", exact=True
    ).click()
    expect(page.get_by_role("status")).to_contain_text("message has been queued")
    page.get_by_role("button", name="Verify email", exact=True).click()
    page.get_by_label("Verification or reset code", exact=True).fill(
        latest_token("verify")
    )
    page.locator("form").get_by_role("button", name="Verify email", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("You can now sign in")
    page.get_by_role("button", name="Sign in", exact=True).click()
    page.get_by_label("Email", exact=True).fill(email)
    page.get_by_label("Password", exact=True).fill(password)
    with page.expect_response(
        lambda response: response.url.endswith("/api/session/login")
    ) as login_response:
        page.locator("form").get_by_role("button", name="Sign in", exact=True).click()
    assert login_response.value.json() == {"status": "signed_in"}
    expect(page.get_by_text("Synthetic E2E", exact=True)).to_be_visible()
    cookies = page.context.cookies()
    assert all(
        cookie["httpOnly"] and cookie["sameSite"] == "Strict"
        for cookie in cookies
        if cookie["name"] in {"edp_session", "edp_csrf"}
    )
    assert page.evaluate("Object.keys(localStorage)") == []
    csrf = page.request.get(base + "/api/session/csrf").json()["csrf_token"]
    assert (
        page.request.post(
            base + "/api/session/logout",
            data={},
            headers={"Origin": "https://evil.example", "X-CSRF-Token": csrf},
        ).status
        == 403
    )
    assert (
        page.request.post(
            base + "/api/session/logout", data={}, headers={"Origin": base}
        ).status
        == 403
    )
    with Session(engine) as db:
        seed_roles(db)
        user = db.scalar(select(User).where(User.email == email))
        role = db.scalar(select(Role).where(Role.name == "Super Admin"))
        organization = Organization(
            id=UUID(os.environ["PUBLIC_ORGANIZATION_ID"]),
            name="Synthetic E2E Organization",
        )
        db.add(organization)
        db.flush()
        db.add(
            UserRole(user_id=user.id, role_id=role.id, organization_id=organization.id)
        )
        coordinator_person = Person(display_name="Synthetic Coordinator")
        db.add(coordinator_person)
        db.flush()
        coordinator = User(
            person_id=coordinator_person.id,
            email=coordinator_email,
            password_hash=hasher.hash(coordinator_password),
            status="active",
        )
        db.add(coordinator)
        db.flush()
        coordinator_role = db.scalar(
            select(Role).where(Role.name == "Training Center Coordinator")
        )
        assert coordinator_role
        db.add(
            UserRole(
                user_id=coordinator.id,
                role_id=coordinator_role.id,
                organization_id=organization.id,
            )
        )
        trainer_person = Person(display_name="Synthetic Trainer")
        db.add(trainer_person)
        db.flush()
        trainer = User(
            person_id=trainer_person.id,
            email=trainer_email,
            password_hash=hasher.hash(trainer_password),
            status="active",
        )
        db.add(trainer)
        db.flush()
        trainer_role = db.scalar(select(Role).where(Role.name == "Trainer"))
        assert trainer_role
        db.add(
            UserRole(
                user_id=trainer.id,
                role_id=trainer_role.id,
                organization_id=organization.id,
            )
        )
        for display_name, actor_email, actor_password, role_names in (
            (
                "Synthetic Plan Mentor",
                plan_mentor_email,
                plan_mentor_password,
                ("Mentor",),
            ),
            (
                "Synthetic Unrelated Actor",
                unrelated_email,
                unrelated_password,
                ("Mentor", "Participant"),
            ),
        ):
            actor_person = Person(display_name=display_name)
            db.add(actor_person)
            db.flush()
            actor = User(
                person_id=actor_person.id,
                email=actor_email,
                password_hash=hasher.hash(actor_password),
                status="active",
            )
            db.add(actor)
            db.flush()
            for role_name in role_names:
                actor_role = db.scalar(select(Role).where(Role.name == role_name))
                assert actor_role
                db.add(
                    UserRole(
                        user_id=actor.id,
                        role_id=actor_role.id,
                        organization_id=organization.id,
                    )
                )
            if actor_email == plan_mentor_email:
                plan_mentor_user_id = actor.id
            else:
                unrelated_user_id = actor.id
        audit(
            db,
            "system.role_granted",
            "synthetic-e2e",
            resource=user.id,
            organization=organization.id,
        )
        db.commit()
        organization_id = organization.id
    page.reload()
    page.wait_for_load_state("domcontentloaded")
    page.get_by_role("link", name="Synthetic E2E Organization", exact=True).click()
    expect(page.get_by_role("heading", name="Staff workspace")).to_be_visible()
    expect(page.get_by_text("system.role_granted", exact=False)).to_be_visible()
    assert page.request.get(base + "/api/session/staff/" + str(uuid4())).status == 403
    page.goto(base + "/en/admin/pages")
    expect(page.get_by_role("heading", name="Publishing workspace")).to_be_visible()
    page.get_by_label("Page address", exact=True).fill("eligibility")
    page.get_by_label("Title", exact=True).fill("Who can apply")
    page.get_by_label("Content", exact=True).fill(
        "Synthetic eligibility <script>alert(1)</script>"
    )
    page.get_by_role("button", name="Save draft", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Saved")
    assert (
        page.request.get(
            os.environ["API_INTERNAL_URL"]
            + "/api/v1/public/organizations/"
            + str(organization_id)
            + "/pages/eligibility?locale=en"
        ).status
        == 404
    )
    page.get_by_role("button", name="Preview saved draft", exact=True).click()
    expect(page.locator(".cms-preview")).to_contain_text("<script>alert(1)</script>")
    page.get_by_role("button", name="Publish saved draft", exact=True).click()
    expect(page.locator(".cms-state")).to_contain_text("Published")
    public = browser.new_page()
    public.goto(base + "/en/pages/eligibility")
    assert public.request.get(base + "/cse-logo.png").status == 200
    expect(public.get_by_role("heading", name="Who can apply")).to_be_visible()
    published_article = public.get_by_role("article").filter(
        has=public.get_by_role("heading", name="Who can apply", exact=True)
    )
    expect(
        published_article.get_by_text(
            "Synthetic eligibility <script>alert(1)</script>", exact=True
        )
    ).to_be_visible()
    expect(published_article.locator("script")).to_have_count(0)
    page.screenshot(path=str(evidence / "cms-debug.png"), full_page=True)
    page.get_by_label("Content", exact=True).fill("Unpublished change")
    page.get_by_role("button", name="Save draft", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Saved")
    public.reload()
    expect(published_article).not_to_contain_text("Unpublished change")
    expect(
        published_article.get_by_text(
            "Synthetic eligibility <script>alert(1)</script>", exact=True
        )
    ).to_be_visible()
    expect(published_article.locator("script")).to_have_count(0)
    page.get_by_label("Content language").select_option("ta")
    page.get_by_label("Title", exact=True).fill("Tamil synthetic title")
    page.get_by_label("Content", exact=True).fill("Tamil synthetic content")
    page.get_by_role("button", name="Add translation", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Saved")
    assert (
        page.request.get(
            os.environ["API_INTERNAL_URL"]
            + "/api/v1/public/organizations/"
            + str(organization_id)
            + "/pages/eligibility?locale=ta"
        ).status
        == 404
    )
    page.get_by_role("button", name="Publish saved draft", exact=True).click()
    expect(page.locator(".cms-state")).to_contain_text("Published")
    public.goto(base + "/ta/pages/eligibility")
    expect(public.get_by_role("heading", name="Tamil synthetic title")).to_be_visible()
    page.get_by_label("Archive reason").fill("Synthetic archive")
    page.get_by_role("button", name="Archive", exact=True).click()
    expect(page.locator(".cms-state")).to_contain_text("Archived")
    assert (
        page.request.get(
            os.environ["API_INTERNAL_URL"]
            + "/api/v1/public/organizations/"
            + str(organization_id)
            + "/pages/eligibility?locale=ta"
        ).status
        == 404
    )
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.screenshot(path=str(evidence / "cms-mobile.png"), full_page=True)
    page.set_viewport_size({"width": 1280, "height": 900})
    public.close()
    page.goto(
        base + "/en/admin/application-definitions?organization=" + str(organization_id)
    )
    expect(
        page.get_by_role("heading", name="Application definition administration")
    ).to_be_visible()
    page.get_by_role("button", name="New definition", exact=True).click()
    page.get_by_label("English title", exact=True).fill(
        "Synthetic enterprise application"
    )
    page.get_by_label("Tamil title", exact=True).fill("Synthetic Tamil application")
    page.get_by_label("English label", exact=True).nth(0).fill(
        "Describe the business idea"
    )
    page.get_by_label("Tamil label", exact=True).nth(0).fill("Synthetic Tamil field")
    acknowledgement_labels = page.locator(".definition-fields textarea")
    while acknowledgement_labels.count() < 4:
        page.get_by_role("button", name="Add acknowledgement", exact=True).click()
    acknowledgement_labels.nth(0).fill("I declare this application is accurate.")
    acknowledgement_labels.nth(1).fill("Synthetic Tamil declaration")
    acknowledgement_labels.nth(2).fill("I consent to processing for this application.")
    acknowledgement_labels.nth(3).fill("Synthetic Tamil consent")
    page.get_by_role("button", name="Save draft", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Draft definition created.")
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Publish version", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Definition published.")
    expect(page.locator(".definition-state-published").first).to_be_visible()
    page.get_by_role("button", name="Copy as new draft", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("New draft version created.")
    expect(page.locator(".definition-state-draft").first).to_be_visible()
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.screenshot(
        path=str(evidence / "application-definitions-mobile.png"), full_page=True
    )
    page.set_viewport_size({"width": 1280, "height": 900})
    with Session(engine) as db:
        actor = db.scalar(select(User).where(User.email == email))
        form = db.scalar(
            select(ApplicationForm).where(
                ApplicationForm.organization_id == organization_id,
                ApplicationForm.state == "published",
            )
        )
        assert actor and form
        program = program_service.create_program(
            db,
            organization_id,
            actor,
            NamedCreate(
                code="e2e-program",
                name_en="E2E program",
                name_ta="Synthetic Tamil program",
            ),
            "e2e-program-create",
        )
        program = program_service.transition_program(
            db,
            organization_id,
            program.id,
            actor,
            StateCommand(
                expected_version=program.version,
                target="active",
                reason="E2E activation",
            ),
            "e2e-program-activate",
        )
        center = program_service.create_center(
            db,
            organization_id,
            actor,
            CenterCreate(
                code="e2e-center",
                name_en="E2E center",
                name_ta="Synthetic Tamil center",
                locality="Chennai",
            ),
            "e2e-center-create",
        )
        other_center = program_service.create_center(
            db,
            organization_id,
            actor,
            CenterCreate(
                code="e2e-other-center",
                name_en="E2E other center",
                name_ta="Synthetic Tamil other center",
                locality="Madurai",
            ),
            "e2e-other-center-create",
        )
        cohort = program_service.create_cohort(
            db,
            organization_id,
            actor,
            CohortCreate(
                code="e2e-cohort",
                name_en="E2E cohort",
                name_ta="Synthetic Tamil cohort",
                program_id=program.id,
                center_id=center.id,
                starts_on=datetime.now(UTC).date() - timedelta(days=7),
                ends_on=datetime.now(UTC).date() + timedelta(days=90),
                capacity=20,
            ),
            "e2e-cohort-create",
        )
        other_cohort = program_service.create_cohort(
            db,
            organization_id,
            actor,
            CohortCreate(
                code="e2e-other-cohort",
                name_en="E2E other cohort",
                name_ta="Synthetic Tamil other cohort",
                program_id=program.id,
                center_id=other_center.id,
                starts_on=datetime.now(UTC).date() - timedelta(days=7),
                ends_on=datetime.now(UTC).date() + timedelta(days=90),
                capacity=20,
            ),
            "e2e-other-cohort-create",
        )
        cohort = program_service.transition_cohort(
            db,
            organization_id,
            cohort.id,
            actor,
            StateCommand(
                expected_version=cohort.version,
                target="active",
                reason="E2E cohort activation",
            ),
            "e2e-cohort-activate",
        )
        cycle = program_service.create_cycle(
            db,
            organization_id,
            actor,
            CycleCreate(
                code="e2e-cycle",
                name_en="E2E application cycle",
                name_ta="Synthetic Tamil cycle",
                program_id=program.id,
                cohort_id=cohort.id,
                form_id=form.id,
                opens_at=datetime.now(UTC) - timedelta(hours=1),
                closes_at=datetime.now(UTC) + timedelta(days=1),
            ),
            "e2e-cycle-create",
        )
        program_service.transition_cycle(
            db,
            organization_id,
            cycle.id,
            actor,
            StateCommand(
                expected_version=cycle.version, target="open", reason="E2E intake"
            ),
            "e2e-cycle-open",
        )
    page.goto(base + "/en/applications?organization=" + str(organization_id))
    expect(page.get_by_role("heading", name="My applications")).to_be_visible()
    expect(
        page.get_by_role("heading", name="E2E application cycle", exact=True)
    ).to_be_visible()
    page.get_by_role("button", name="Start application", exact=True).click()
    page.get_by_label("Describe the business idea", exact=False).fill(
        "Synthetic repair cooperative"
    )
    page.get_by_label(
        "I declare this application is accurate. (Required)", exact=True
    ).check()
    page.get_by_label(
        "I consent to processing for this application. (Required)", exact=True
    ).check()
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Submit application", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Application submitted")
    expect(page.get_by_text("Application number:", exact=False)).to_contain_text("EDP-")
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.screenshot(
        path=str(evidence / "application-submitted-mobile.png"), full_page=True
    )
    page.set_viewport_size({"width": 1280, "height": 900})
    with Session(engine) as db:
        actor = db.scalar(select(User).where(User.email == email))
        assert actor
        program_service.transition_cycle(
            db,
            organization_id,
            cycle.id,
            actor,
            StateCommand(
                expected_version=2,
                target="closed",
                reason="E2E intake completed",
            ),
            "e2e-cycle-close",
        )
    page.goto(base + "/en/admin/selection?organization=" + str(organization_id))
    expect(page.get_by_role("heading", name="Selection administration")).to_be_visible()
    page.get_by_label("Code", exact=True).fill("e2e-selection")
    page.get_by_label("English name", exact=True).fill("E2E selection")
    page.get_by_label("Tamil name", exact=True).fill("Synthetic Tamil selection")
    page.locator('select[name="application_cycle_id"]').select_option(
        label="E2E application cycle"
    )
    page.get_by_role("button", name="Create cycle", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    page.get_by_label("Criterion key", exact=True).fill("business_idea")
    page.get_by_label("English label", exact=True).fill("Business idea")
    page.get_by_label("Tamil label", exact=True).fill("Synthetic Tamil business idea")
    page.get_by_role("button", name="Save rubric", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    page.get_by_role("button", name="Publish rubric", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    page.once("dialog", lambda dialog: dialog.accept("E2E review approved"))
    page.get_by_role("button", name="Activate review", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    assign_button = page.get_by_role("button", name="Assign reviewer", exact=True)
    assignment_form = page.locator("form").filter(has=assign_button)
    assignment_form.locator('select[name="selection_cycle_id"]').select_option(
        label="E2E selection"
    )
    application_number = (
        assignment_form.locator('select[name="application_id"]')
        .locator("option:not([value=''])")
        .first.text_content()
    )
    assert application_number and application_number.startswith("EDP-")
    assignment_form.locator('select[name="application_id"]').select_option(
        label=application_number
    )
    assignment_form.locator('select[name="reviewer_user_id"]').select_option(
        label="Synthetic E2E"
    )
    assign_button.click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    expect(
        page.get_by_text("Conflict declaration required", exact=False)
    ).to_be_visible()
    page.get_by_role("button", name="No conflict", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    expect(page.get_by_text("No conflict declared.", exact=True)).to_be_visible()
    review_editor = page.locator(".selection-review-editor")
    review_editor.locator('input[type="number"]').fill("4")
    review_editor.get_by_label("Internal reviewer comment", exact=True).fill(
        "Synthetic browser review evidence"
    )
    review_editor.get_by_role("button", name="Save review draft", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    page.locator(".selection-review-editor").get_by_role(
        "button", name="Submit review", exact=True
    ).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    expect(page.get_by_text("Weighted score: 80.00", exact=True).first).to_be_visible()
    page.once("dialog", lambda dialog: dialog.accept("Synthetic calibration exclusion"))
    page.get_by_role("button", name="Exclude from aggregate", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    expect(page.get_by_text("1 reviews excluded", exact=True)).to_be_visible()
    page.once("dialog", lambda dialog: dialog.accept("Synthetic calibration restored"))
    page.get_by_role("button", name="Restore to aggregate", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    expect(page.get_by_text("Aggregate score: 80.00", exact=True)).to_be_visible()
    page.once("dialog", lambda dialog: dialog.accept("Synthetic shortlist evidence"))
    page.get_by_role("button", name="Shortlist", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    interview_form = page.locator(".selection-interview-form")
    interview_form.locator('select[name="application_id"]').select_option(
        label=application_number
    )
    interview_form.locator('select[name="selection_cycle_id"]').select_option(
        label="E2E selection"
    )
    interview_form.locator('input[name="starts_at"]').fill("2027-01-15T10:00")
    interview_form.locator('input[name="ends_at"]').fill("2027-01-15T11:00")
    interview_form.locator('select[name="panel_user_ids"]').select_option(
        label="Synthetic E2E"
    )
    interview_form.get_by_role("button", name="Schedule interview", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    score_button = page.get_by_role("button", name="Submit interview score", exact=True)
    score_form = page.locator("form").filter(has=score_button)
    score_form.locator('input[name="score"]').fill("84")
    score_form.locator('textarea[name="comment"]').fill("Synthetic panel evidence")
    score_button.click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    page.get_by_role("button", name="Complete interview", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    expect(page.get_by_text("Interview score: 84.00", exact=True).first).to_be_visible()
    page.once("dialog", lambda dialog: dialog.accept("Synthetic final selection"))
    page.get_by_role("button", name="Select", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    page.once("dialog", lambda dialog: dialog.accept("Synthetic capacity override"))
    page.get_by_role("button", name="Override to waitlist", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    page.once("dialog", lambda dialog: dialog.accept("Synthetic capacity restored"))
    page.get_by_role("button", name="Override to selected", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    page.once("dialog", lambda dialog: dialog.accept("Synthetic cycle finalized"))
    page.get_by_role("button", name="Finalize selection", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    page.goto(base + "/en/admin/programs?organization=" + str(organization_id))
    expect(
        page.get_by_role("heading", name="Selected applicants ready for enrollment")
    ).to_be_visible()
    page.once("dialog", lambda dialog: dialog.accept("Synthetic enrollment approval"))
    page.get_by_role("button", name="Create enrollment", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    schedule_button = page.get_by_role("button", name="Schedule session", exact=True)
    schedule_form = page.locator("form").filter(has=schedule_button)
    schedule_form.locator('select[name="cohort_id"]').select_option(label="E2E cohort")
    schedule_form.locator('input[name="title_en"]').fill("Business foundations")
    schedule_form.locator('input[name="title_ta"]').fill("Synthetic Tamil session")
    session_start = datetime.now(UTC) + timedelta(days=1)
    schedule_form.locator('input[name="starts_at"]').fill(
        session_start.strftime("%Y-%m-%dT%H:%M")
    )
    schedule_form.locator('input[name="ends_at"]').fill(
        (session_start + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M")
    )
    schedule_form.locator('input[name="location"]').fill("E2E training room")
    schedule_button.click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    expect(page.get_by_text("Business foundations", exact=True)).to_be_visible()

    with Session(engine) as db:
        attendance_session = ProgramSession(
            organization_id=organization_id,
            cohort_id=cohort.id,
            title_en="Attendance check-in lab",
            title_ta="Synthetic Tamil attendance session",
            starts_at=datetime.now(UTC) + timedelta(minutes=5),
            ends_at=datetime.now(UTC) + timedelta(hours=1),
            mode="in_person",
            location="E2E training room",
        )
        db.add(attendance_session)
        db.commit()
        attendance_session_id = attendance_session.id

    page.goto(base + "/en/admin/attendance?organization=" + str(organization_id))
    expect(
        page.get_by_role("heading", name="Attendance control", exact=True)
    ).to_be_visible()
    attendance_card = page.locator("article").filter(
        has=page.get_by_role("heading", name="Attendance check-in lab", exact=True)
    )
    policy_form = attendance_card.locator("form").first
    policy_form.locator('input[name="threshold_percent"]').fill("80")
    policy_form.locator('input[name="late_after_minutes"]').fill("10")
    policy_form.locator('input[name="opens_before_minutes"]').fill("15")
    policy_form.locator('input[name="closes_after_minutes"]').fill("30")
    policy_form.locator('input[name="reason"]').fill(
        "Synthetic approved attendance policy"
    )
    policy_form.get_by_role("button", name="Save policy", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Attendance saved.")
    attendance_card.get_by_role("button", name="Open QR check-in", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Attendance saved.")
    qr_url = attendance_card.locator('object[type="image/svg+xml"]').get_attribute(
        "data"
    )
    assert qr_url and qr_url.startswith("data:image/svg+xml;base64,")
    check_in_token = attendance_card.locator("[data-check-in-token]").text_content()
    assert check_in_token

    page.goto(base + "/en/attendance?organization=" + str(organization_id))
    expect(
        page.get_by_role("heading", name="My attendance", exact=True)
    ).to_be_visible()
    page.get_by_label("Check-in code", exact=True).fill(check_in_token)
    page.get_by_role("button", name="Check in", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Attendance saved.")
    expect(page.get_by_text("Present", exact=True)).to_be_visible()
    expect(page.get_by_text("Attendance is on track", exact=True)).to_be_visible()
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.screenshot(path=str(evidence / "attendance-mobile.png"), full_page=True)
    page.set_viewport_size({"width": 1280, "height": 900})

    page.goto(base + "/en/admin/learning?organization=" + str(organization_id))
    expect(
        page.get_by_role("heading", name="Course studio", exact=True)
    ).to_be_visible()
    course_form = page.locator("form").filter(
        has=page.get_by_role("heading", name="Create course", exact=True)
    )
    course_form.locator('input[name="code"]').fill("e2e-foundations")
    course_form.locator('input[name="title_en"]').fill("Enterprise foundations")
    course_form.locator('input[name="title_ta"]').fill("Synthetic Tamil course")
    course_form.locator('textarea[name="description_en"]').fill(
        "A practical introduction to understanding customers."
    )
    course_form.locator('textarea[name="description_ta"]').fill(
        "Synthetic Tamil course description."
    )
    course_form.get_by_role("button", name="Create", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")

    module_form = page.locator("form").filter(
        has=page.get_by_role("heading", name="Add module", exact=True)
    )
    module_form.locator('select[name="course_id"]').select_option(
        label="Enterprise foundations"
    )
    module_form.locator('input[name="position"]').fill("1")
    module_form.locator('input[name="title_en"]').fill("Know the customer")
    module_form.locator('input[name="title_ta"]').fill("Synthetic Tamil module")
    module_form.get_by_role("button", name="Create", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")

    lesson_form = page.locator("form").filter(
        has=page.get_by_role("heading", name="Add lesson", exact=True)
    )
    lesson_form.locator('select[name="module_key"]').select_option(
        label="Enterprise foundations / Know the customer"
    )
    lesson_form.locator('input[name="position"]').fill("1")
    lesson_form.locator('input[name="duration_minutes"]').fill("20")
    lesson_form.locator('input[name="title_en"]').fill("Customer problem")
    lesson_form.locator('input[name="title_ta"]').fill("Synthetic Tamil lesson")
    lesson_form.locator('textarea[name="body_en"]').fill(
        "Describe the customer problem in observable terms."
    )
    lesson_form.locator('textarea[name="body_ta"]').fill("Synthetic Tamil lesson body.")
    lesson_form.get_by_role("button", name="Create", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")

    material_form = page.locator("form").filter(
        has=page.get_by_role(
            "heading", name="Add private material reference", exact=True
        )
    )
    material_form.locator('select[name="lesson_key"]').select_option(
        label="Enterprise foundations / Know the customer / Customer problem"
    )
    material_form.locator('input[name="position"]').fill("1")
    material_form.locator('input[name="label_en"]').fill("Customer worksheet")
    material_form.locator('input[name="label_ta"]').fill("Synthetic Tamil worksheet")
    material_form.locator('input[name="provider_key"]').fill(
        "private/e2e/customer-worksheet.pdf"
    )
    material_form.get_by_role("button", name="Create", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")

    assignment_form = page.locator("form").filter(
        has=page.get_by_role("heading", name="Add assignment", exact=True)
    )
    assignment_form.locator('select[name="lesson_key"]').select_option(
        label="Enterprise foundations / Know the customer / Customer problem"
    )
    assignment_form.locator('input[name="position"]').fill("1")
    assignment_form.locator('input[name="title_en"]').fill("Customer evidence")
    assignment_form.locator('input[name="title_ta"]').fill("Synthetic Tamil assignment")
    assignment_form.locator('textarea[name="instructions_en"]').fill(
        "Summarize one customer interview."
    )
    assignment_form.locator('textarea[name="instructions_ta"]').fill(
        "Synthetic Tamil assignment instructions."
    )
    assignment_form.locator('input[name="maximum_points"]').fill("20")
    assignment_form.locator('input[name="passing_points"]').fill("12")
    assignment_form.locator('input[name="max_submissions"]').fill("2")
    assignment_form.get_by_role("button", name="Create", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")

    quiz_form = page.locator("form").filter(
        has=page.get_by_role("heading", name="Add quiz", exact=True)
    )
    quiz_form.locator('select[name="lesson_key"]').select_option(
        label="Enterprise foundations / Know the customer / Customer problem"
    )
    quiz_form.locator('input[name="position"]').fill("1")
    quiz_form.locator('input[name="title_en"]').fill("Customer check")
    quiz_form.locator('input[name="title_ta"]').fill("Synthetic Tamil quiz")
    quiz_form.locator('textarea[name="instructions_en"]').fill(
        "Choose the strongest customer statement."
    )
    quiz_form.locator('textarea[name="instructions_ta"]').fill(
        "Synthetic Tamil quiz instructions."
    )
    quiz_form.locator('input[name="passing_percent"]').fill("60")
    quiz_form.locator('input[name="max_attempts"]').fill("2")
    quiz_form.get_by_role("button", name="Create", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")

    question_form = page.locator("form").filter(
        has=page.get_by_role("heading", name="Add question", exact=True)
    )
    question_form.locator('select[name="quiz_key"]').select_option(
        label="Enterprise foundations / Customer problem / Customer check"
    )
    question_form.locator('input[name="position"]').fill("1")
    question_form.locator('textarea[name="prompt_en"]').fill(
        "Which statement is observable?"
    )
    question_form.locator('textarea[name="prompt_ta"]').fill("Synthetic Tamil question")
    question_form.locator('input[name="points"]').fill("10")
    question_form.get_by_role("button", name="Create", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")

    choice_form = page.locator("form").filter(
        has=page.get_by_role("heading", name="Add answer choice", exact=True)
    )
    choice_form.locator('select[name="question_key"]').select_option(
        label="Enterprise foundations / Customer check / Which statement is observable?"
    )
    choice_form.locator('input[name="position"]').fill("1")
    choice_form.locator('input[name="label_en"]').fill("Customers probably want it.")
    choice_form.locator('input[name="label_ta"]').fill("Synthetic Tamil wrong choice")
    choice_form.get_by_role("button", name="Create", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")

    choice_form.locator('select[name="question_key"]').select_option(
        label="Enterprise foundations / Customer check / Which statement is observable?"
    )
    choice_form.locator('input[name="position"]').fill("2")
    choice_form.locator('input[name="label_en"]').fill(
        "Five customers reported the same problem."
    )
    choice_form.locator('input[name="label_ta"]').fill("Synthetic Tamil correct choice")
    choice_form.locator('input[name="is_correct"]').check()
    choice_form.get_by_role("button", name="Create", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")

    page.once("dialog", lambda dialog: dialog.accept("E2E content approved"))
    page.get_by_role("button", name="Publish course", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    template_button = page.get_by_role(
        "button", name="Create certificate template", exact=True
    )
    template_form = page.locator("form").filter(has=template_button)
    template_form.locator('select[name="course_id"]').select_option(
        label="Enterprise foundations"
    )
    template_form.locator('input[name="code"]').fill("e2e-completion")
    template_form.locator('input[name="title_en"]').fill("Certificate of Completion")
    template_form.locator('input[name="title_ta"]').fill("Synthetic Tamil certificate")
    template_form.locator('textarea[name="statement_en"]').fill(
        "has completed the Enterprise foundations course"
    )
    template_form.locator('textarea[name="statement_ta"]').fill(
        "Synthetic Tamil certificate statement"
    )
    template_form.locator('input[name="issuer_name"]').fill(
        "Center for Social Justice and Equity"
    )
    template_button.click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    page.once("dialog", lambda dialog: dialog.accept("E2E certificate approved"))
    page.get_by_role("button", name="Publish template", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    pathway_button = page.get_by_role("button", name="Add to cohort", exact=True)
    pathway_form = page.locator("form").filter(has=pathway_button)
    pathway_form.locator('select[name="course_id"]').select_option(
        label="Enterprise foundations"
    )
    pathway_form.locator('select[name="cohort_id"]').select_option(label="E2E cohort")
    pathway_form.locator('input[name="position"]').fill("1")
    pathway_form.locator('input[name="reason"]').fill("E2E cohort pathway approved")
    pathway_button.click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    expect(page.get_by_text("Enterprise foundations", exact=True).first).to_be_visible()

    page.goto(base + "/en/admin/programs?organization=" + str(organization_id))
    expect(
        page.get_by_role("heading", name="Program administration", exact=True)
    ).to_be_visible()
    assign_button = page.get_by_role("button", name="Assign delivery staff", exact=True)
    assignment_form = page.locator("form").filter(has=assign_button)
    assignment_form.locator('input[name="email"]').fill(coordinator_email)
    assignment_form.locator('select[name="center_id"]').select_option(
        label="E2E center"
    )
    assignment_form.get_by_label("Assignment reason", exact=True).fill(
        "Own E2E center delivery"
    )
    assign_button.click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    expect(page.get_by_text(coordinator_email, exact=False)).to_be_visible()

    assignment_form.locator('input[name="email"]').fill(trainer_email)
    assignment_form.locator('select[name="center_id"]').select_option(
        label="E2E center"
    )
    assignment_form.locator('select[name="cohort_id"]').select_option(
        label="E2E cohort"
    )
    assignment_form.get_by_label("Assignment reason", exact=True).fill(
        "Own E2E cohort learning delivery"
    )
    assign_button.click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    expect(page.get_by_text(trainer_email, exact=False)).to_be_visible()

    trainer_context = browser.new_context(viewport={"width": 1280, "height": 900})
    trainer_page = trainer_context.new_page()
    trainer_errors = []
    trainer_page.on("pageerror", lambda error: trainer_errors.append(str(error)))
    trainer_page.goto(base + "/en/account")
    trainer_page.wait_for_load_state("domcontentloaded")
    trainer_page.get_by_label("Email", exact=True).fill(trainer_email)
    trainer_page.get_by_label("Password", exact=True).fill(trainer_password)
    trainer_page.locator("form").get_by_role(
        "button", name="Sign in", exact=True
    ).click()
    expect(trainer_page.get_by_text("Synthetic Trainer", exact=True)).to_be_visible()
    trainer_page.goto(base + "/en/admin/learning?organization=" + str(organization_id))
    expect(
        trainer_page.get_by_role("heading", name="Trainer delivery", exact=True)
    ).to_be_visible()
    expect(
        trainer_page.get_by_text("Enterprise foundations", exact=True)
    ).to_be_visible()
    expect(trainer_page.get_by_text("Synthetic E2E", exact=True)).to_be_visible()
    expect(trainer_page.get_by_text("Not started", exact=True)).to_be_visible()
    expect(trainer_page.get_by_text("Not attempted", exact=False)).to_be_visible()
    with trainer_page.expect_download() as trainer_download:
        trainer_page.get_by_role("button", name="Open material", exact=True).click()
    assert trainer_download.value.suggested_filename == "customer-worksheet.pdf"
    assert Path(trainer_download.value.path()).read_bytes().startswith(b"%PDF-1.4")
    assert not trainer_errors, trainer_errors
    trainer_context.close()

    coordinator_context = browser.new_context(viewport={"width": 1280, "height": 900})
    coordinator_page = coordinator_context.new_page()
    coordinator_errors = []
    coordinator_page.on(
        "pageerror", lambda error: coordinator_errors.append(str(error))
    )
    coordinator_page.goto(base + "/en/account")
    coordinator_page.wait_for_load_state("domcontentloaded")
    coordinator_page.get_by_label("Email", exact=True).fill(coordinator_email)
    coordinator_page.get_by_label("Password", exact=True).fill(coordinator_password)
    coordinator_page.locator("form").get_by_role(
        "button", name="Sign in", exact=True
    ).click()
    expect(
        coordinator_page.get_by_text("Synthetic Coordinator", exact=True)
    ).to_be_visible()
    coordinator_page.goto(
        base + "/en/admin/programs?organization=" + str(organization_id)
    )
    expect(
        coordinator_page.get_by_role(
            "heading", name="Program administration", exact=True
        )
    ).to_be_visible()
    expect(
        coordinator_page.locator(".program-list strong", has_text="E2E center").first
    ).to_be_visible()
    expect(
        coordinator_page.locator(".program-list strong", has_text="E2E other center")
    ).not_to_be_visible()
    expect(
        coordinator_page.locator(".program-list strong", has_text="E2E cohort").first
    ).to_be_visible()
    expect(
        coordinator_page.locator(".program-list strong", has_text="E2E other cohort")
    ).not_to_be_visible()

    scoped_schedule_button = coordinator_page.get_by_role(
        "button", name="Schedule session", exact=True
    )
    scoped_schedule_form = coordinator_page.locator("form").filter(
        has=scoped_schedule_button
    )
    scoped_schedule_form.locator('select[name="cohort_id"]').select_option(
        label="E2E cohort"
    )
    scoped_schedule_form.locator('input[name="title_en"]').fill("Coordinator session")
    scoped_schedule_form.locator('input[name="title_ta"]').fill(
        "Synthetic Tamil coordinator session"
    )
    scoped_start = datetime.now(UTC) + timedelta(days=2)
    scoped_schedule_form.locator('input[name="starts_at"]').fill(
        scoped_start.strftime("%Y-%m-%dT%H:%M")
    )
    scoped_schedule_form.locator('input[name="ends_at"]').fill(
        (scoped_start + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
    )
    scoped_schedule_form.locator('select[name="mode"]').select_option("online")
    scoped_schedule_button.click()
    expect(coordinator_page.get_by_role("status")).to_have_text("Change saved.")
    expect(
        coordinator_page.get_by_text("Coordinator session", exact=True)
    ).to_be_visible()

    coordinator_csrf = coordinator_page.request.get(base + "/api/session/csrf").json()[
        "csrf_token"
    ]
    denied_session = coordinator_page.request.post(
        base + "/api/programs/organizations/" + str(organization_id) + "/sessions",
        data={
            "cohort_id": str(other_cohort.id),
            "title_en": "Denied coordinator session",
            "title_ta": "Synthetic Tamil denied session",
            "starts_at": scoped_start.isoformat(),
            "ends_at": (scoped_start + timedelta(hours=1)).isoformat(),
            "mode": "online",
            "location": None,
        },
        headers={
            "Origin": base,
            "X-CSRF-Token": coordinator_csrf,
        },
    )
    assert denied_session.status == 403

    coordinator_page.set_viewport_size({"width": 390, "height": 844})
    assert coordinator_page.evaluate(
        "document.documentElement.scrollWidth <= window.innerWidth"
    )
    coordinator_page.screenshot(
        path=str(evidence / "coordinator-scope-mobile.png"), full_page=True
    )
    coordinator_page.set_viewport_size({"width": 1280, "height": 900})

    page.once("dialog", lambda dialog: dialog.accept("E2E assignment ended"))
    page.locator(".program-list li").filter(has_text=coordinator_email).get_by_role(
        "button", name="Revoke", exact=True
    ).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    expect(page.get_by_text("revoked", exact=True)).to_be_visible()
    coordinator_page.reload()
    expect(coordinator_page.locator(".program-message")).to_have_text(
        "The request could not be completed. Check your details and try again."
    )
    assert not coordinator_errors, coordinator_errors
    coordinator_context.close()

    page.goto(base + "/en/learning?organization=" + str(organization_id))
    expect(
        page.get_by_role("heading", name="My learning path", exact=True)
    ).to_be_visible()
    expect(page.get_by_text("Enterprise foundations", exact=True)).to_be_visible()
    expect(page.get_by_text("Customer problem", exact=True)).to_be_visible()
    expect(
        page.get_by_text("private/e2e/customer-worksheet.pdf", exact=True)
    ).not_to_be_visible()
    page.get_by_role("button", name="Start course", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    expect(page.get_by_text("In progress", exact=True)).to_be_visible()
    with page.expect_download() as learner_download:
        page.get_by_role("button", name="Open material", exact=True).click()
    assert learner_download.value.suggested_filename == "customer-worksheet.pdf"
    assert Path(learner_download.value.path()).read_bytes().startswith(b"%PDF-1.4")
    expect(page.get_by_text("Customer evidence", exact=True)).to_be_visible()
    assignment_card = page.locator("form.learning-private").filter(
        has=page.get_by_text("Customer evidence", exact=True)
    )
    assignment_card.locator('textarea[name="response_text"]').fill(
        "Five interviews showed repeated payment delays."
    )
    assignment_card.get_by_role("button", name="Submit assignment", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    expect(page.get_by_text("Awaiting trainer review.", exact=True)).to_be_visible()

    grading_context = browser.new_context(viewport={"width": 1280, "height": 900})
    grading_page = grading_context.new_page()
    grading_page.goto(base + "/en/account")
    grading_page.wait_for_load_state("domcontentloaded")
    grading_page.get_by_label("Email", exact=True).fill(trainer_email)
    grading_page.get_by_label("Password", exact=True).fill(trainer_password)
    grading_page.locator("form").get_by_role(
        "button", name="Sign in", exact=True
    ).click()
    expect(grading_page.get_by_text("Synthetic Trainer", exact=True)).to_be_visible()
    grading_page.goto(base + "/en/admin/learning?organization=" + str(organization_id))
    expect(
        grading_page.get_by_text(
            "Five interviews showed repeated payment delays.", exact=True
        )
    ).to_be_visible()
    grade_form = grading_page.locator("form").filter(
        has=grading_page.get_by_role("button", name="Save grade", exact=True)
    )
    grade_form.locator('input[name="score_points"]').fill("15")
    grade_form.locator('textarea[name="feedback"]').fill(
        "Clear evidence; add interview dates next time."
    )
    grade_form.get_by_role("button", name="Save grade", exact=True).click()
    expect(grading_page.get_by_role("status")).to_have_text("Change saved.")
    grading_context.close()

    page.reload()
    expect(
        page.get_by_text("Clear evidence; add interview dates next time.", exact=False)
    ).to_be_visible()
    expect(page.get_by_text("Customer check", exact=True)).to_be_visible()
    page.get_by_label("Customers probably want it.", exact=True).check()
    page.get_by_role("button", name="Submit quiz", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    expect(page.get_by_text("Best score: 0%", exact=False)).to_be_visible()
    page.get_by_label("Five customers reported the same problem.", exact=True).check()
    page.get_by_role("button", name="Submit quiz", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    expect(page.get_by_text("Passed", exact=True)).to_be_visible()
    expect(page.get_by_text("Best score: 100%", exact=False)).to_be_visible()
    page.get_by_role("button", name="Mark lesson complete", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    expect(page.get_by_text("Completed", exact=True).first).to_be_visible()
    expect(page.get_by_text("100%", exact=True).first).to_be_visible()
    expect(page.get_by_text("Eligible for certificate", exact=True)).to_be_visible()
    page.goto(base + "/en/admin/learning?organization=" + str(organization_id))
    expect(
        page.get_by_text("Eligible for certificate", exact=False).last
    ).to_be_visible()
    page.once("dialog", lambda dialog: dialog.accept("E2E completion verified"))
    page.get_by_role("button", name="Issue certificate", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Change saved.")
    expect(
        page.get_by_text("Certificate status: valid", exact=False).first
    ).to_be_visible()
    page.goto(base + "/en/learning?organization=" + str(organization_id))
    verify_link = page.get_by_role("link", name="Verify certificate", exact=True)
    expect(verify_link).to_be_visible()
    verification_href = verify_link.get_attribute("href")
    assert verification_href
    public_context = browser.new_context(viewport={"width": 1280, "height": 900})
    public_page = public_context.new_page()
    public_page.goto(base + verification_href)
    expect(
        public_page.get_by_role("heading", name="Certificate of Completion", exact=True)
    ).to_be_visible()
    expect(
        public_page.get_by_text("Certificate status: Valid", exact=True)
    ).to_be_visible()
    public_context.close()
    verify_link.click()
    expect(
        page.get_by_role("heading", name="Certificate of Completion", exact=True)
    ).to_be_visible()
    expect(page.get_by_text("Certificate status: Valid", exact=True)).to_be_visible()
    expect(
        page.get_by_alt_text("Certificate verification QR code", exact=True)
    ).to_be_visible()
    page.goto(base + "/en/learning?organization=" + str(organization_id))
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.screenshot(path=str(evidence / "learning-mobile.png"), full_page=True)
    page.set_viewport_size({"width": 1280, "height": 900})

    page.goto(base + "/en/participant?organization=" + str(organization_id))
    expect(page.get_by_role("heading", name="My program schedule")).to_be_visible()
    expect(page.get_by_text("Business foundations", exact=True).first).to_be_visible()
    expect(page.get_by_role("heading", name="Timeline", exact=True)).to_be_visible()

    with Session(engine) as db:
        mentor_role = db.scalar(select(Role).where(Role.name == "Mentor"))
        mentor_user = db.scalar(select(User).where(User.email == email))
        assert mentor_role and mentor_user
        db.add(
            UserRole(
                user_id=mentor_user.id,
                role_id=mentor_role.id,
                organization_id=organization_id,
            )
        )
        db.commit()

    page.goto(base + "/en/admin/mentoring?organization=" + str(organization_id))
    expect(page.get_by_role("heading", name="Mentoring workspace")).to_be_visible()
    profile_panel = page.locator("section.program-panel").filter(
        has=page.get_by_role("heading", name="Create mentor profile", exact=True)
    )
    profile_panel.locator('select[name="user_id"]').select_option(label="Synthetic E2E")
    profile_panel.get_by_label("Headline").fill("Enterprise mentor")
    profile_panel.get_by_label("Biography").fill("Supports participant validation.")
    profile_panel.get_by_role("button", name="Save", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("Mentoring record saved")

    assignment_panel = page.locator("section.program-panel").filter(
        has=page.get_by_role("heading", name="Assign mentor", exact=True)
    )
    assignment_panel.locator('select[name="profile"]').select_option(
        label="Synthetic E2E"
    )
    assignment_panel.locator('select[name="enrollment"]').select_option(
        label="Synthetic E2E"
    )
    assignment_panel.get_by_label("Starts").fill(datetime.now(UTC).date().isoformat())
    assignment_panel.get_by_label("Reason").fill("Approved browser mentor match")
    assignment_panel.get_by_role("button", name="Assign mentor", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("Mentoring record saved")

    session_start = datetime.now(UTC) + timedelta(days=2)
    session_end = session_start + timedelta(hours=1)
    schedule_panel = page.locator("section.program-panel").filter(
        has=page.get_by_role("heading", name="Schedule session", exact=True)
    )
    schedule_panel.locator('select[name="assignment"]').select_option(
        label="Synthetic E2E · Synthetic E2E"
    )
    schedule_panel.get_by_label("Topic").fill("Browser customer discovery review")
    schedule_panel.get_by_label("Starts").fill(session_start.strftime("%Y-%m-%dT%H:%M"))
    schedule_panel.get_by_label("Ends").fill(session_end.strftime("%Y-%m-%dT%H:%M"))
    schedule_panel.get_by_label("Location or link").fill("https://meet.example/e2e")
    schedule_panel.get_by_role("button", name="Schedule session", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("Mentoring record saved")

    notes_panel = page.locator("section.program-panel").filter(
        has=page.get_by_role("heading", name="Notes", exact=True)
    )
    notes_panel.locator('select[name="assignment"]').select_option(
        label="Synthetic E2E · Synthetic E2E"
    )
    notes_panel.locator('select[name="session"]').select_option(
        label="Browser customer discovery review"
    )
    notes_panel.locator('select[name="visibility"]').select_option("mentor_private")
    notes_panel.locator('textarea[name="body"]').fill(
        "Browser private mentor observation"
    )
    notes_panel.get_by_role("button", name="Save", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("Mentoring record saved")
    notes_panel = page.locator("section.program-panel").filter(
        has=page.get_by_role("heading", name="Notes", exact=True)
    )
    notes_panel.locator('select[name="assignment"]').select_option(
        label="Synthetic E2E · Synthetic E2E"
    )
    notes_panel.locator('select[name="session"]').select_option(
        label="Browser customer discovery review"
    )
    notes_panel.locator('select[name="visibility"]').select_option(
        "shared_with_participant"
    )
    notes_panel.locator('textarea[name="body"]').fill(
        "Interview five customers before follow-up."
    )
    notes_panel.get_by_role("button", name="Save", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("Mentoring record saved")

    goal_panel = (
        page.locator("section.program-panel")
        .filter(has=page.get_by_role("heading", name="Goals", exact=True))
        .first
    )
    goal_panel.locator('select[name="assignment"]').select_option(
        label="Synthetic E2E · Synthetic E2E"
    )
    goal_panel.get_by_label("Goal").fill("Validate customer demand")
    goal_panel.get_by_role("button", name="Save", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("Mentoring record saved")

    action_panel = (
        page.locator("section.program-panel")
        .filter(has=page.get_by_role("heading", name="Action items", exact=True))
        .first
    )
    action_panel.locator('select[name="assignment"]').select_option(
        label="Synthetic E2E · Synthetic E2E"
    )
    action_panel.locator('select[name="goal"]').select_option(
        label="Validate customer demand"
    )
    action_panel.get_by_label("Action").fill("Complete customer interviews")
    action_panel.get_by_role("button", name="Save", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("Mentoring record saved")

    reminder_panel = (
        page.locator("section.program-panel")
        .filter(has=page.get_by_role("heading", name="Follow-up reminders", exact=True))
        .first
    )
    reminder_panel.locator('select[name="assignment"]').select_option(
        label="Synthetic E2E · Synthetic E2E"
    )
    reminder_panel.locator('select[name="session"]').select_option(
        label="Browser customer discovery review"
    )
    reminder_panel.get_by_label("Purpose").fill("Review interview evidence")
    reminder_panel.get_by_label("Due").fill(
        (session_end + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
    )
    reminder_panel.get_by_role("button", name="Save", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("Mentoring record saved")

    session_list = page.locator("section.program-panel").filter(
        has=page.get_by_role("heading", name="Sessions", exact=True)
    )
    session_list.get_by_role("button", name="Complete", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("Mentoring record saved")

    page.goto(base + "/en/mentoring?organization=" + str(organization_id))
    expect(page.get_by_role("heading", name="My mentoring", exact=True)).to_be_visible()
    expect(
        page.get_by_text("Interview five customers before follow-up.")
    ).to_be_visible()
    expect(page.get_by_text("Browser private mentor observation")).to_have_count(0)
    feedback_form = page.locator('form:has(select[name="rating"])')
    feedback_form.locator('select[name="rating"]').select_option("5")
    feedback_form.locator('textarea[name="comment"]').fill(
        "Clear browser-tested guidance."
    )
    feedback_form.get_by_role("button", name="Save", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("Mentoring record saved")
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.screenshot(path=str(evidence / "mentoring-mobile.png"), full_page=True)
    page.set_viewport_size({"width": 1280, "height": 900})

    plan_url = base + "/en/business-plan?organization=" + str(organization_id)
    page.goto(plan_url)
    expect(
        page.get_by_role("heading", name="My business plan", exact=True, level=1)
    ).to_be_visible()
    plan_panel = page.locator("section.program-panel")
    with page.expect_response(
        lambda response: response.request.method == "POST"
        and "/api/business-plans/" in response.url
    ) as create_plan_response:
        plan_panel.get_by_role("button", name="Start a plan", exact=True).click()
    assert create_plan_response.value.status == 201
    plan_api = create_plan_response.value.url
    plan_id = UUID(create_plan_response.value.json()["id"])
    plan_section_api = plan_api + "/sections"
    plan_summary = plan_panel.get_by_role(
        "textbox", name="Executive summary", exact=True
    )
    with page.expect_response(
        lambda response: response.url == plan_section_api
    ) as first_plan_save:
        plan_summary.fill("Browser baseline business plan")
    assert first_plan_save.value.status == 200
    assert first_plan_save.value.json()["version"] == 2
    expect(plan_panel.get_by_role("status")).to_have_text("Saved")

    # A second authenticated tab deliberately retains the acknowledged v2 snapshot.
    other_plan_page = participant_context.new_page()
    other_plan_page.on("pageerror", lambda error: errors.append(str(error)))
    other_plan_page.goto(plan_url)
    other_plan_panel = other_plan_page.locator("section.program-panel")
    other_summary = other_plan_panel.get_by_role(
        "textbox", name="Executive summary", exact=True
    )
    expect(other_summary).to_have_value("Browser baseline business plan")
    with page.expect_response(
        lambda response: response.url == plan_section_api
    ) as remote_plan_save:
        plan_summary.fill("Browser remotely saved business plan")
    assert remote_plan_save.value.status == 200
    assert remote_plan_save.value.json()["version"] == 3
    expect(plan_panel.get_by_role("status")).to_have_text("Saved")
    with other_plan_page.expect_response(
        lambda response: response.url == plan_section_api
    ) as stale_plan_save:
        other_summary.fill("Browser preserved local business plan")
    assert stale_plan_save.value.status == 409
    assert stale_plan_save.value.request.post_data_json["expected_version"] == 2
    expect(
        other_plan_panel.get_by_role("heading", name="Review conflicting edits")
    ).to_be_visible()
    expect(other_summary).to_have_value("Browser preserved local business plan")
    expect(other_plan_panel.get_by_text("Saved version", exact=True)).to_be_visible()
    expect(other_plan_panel.get_by_text("Your edits", exact=True)).to_be_visible()
    expect(other_plan_panel.locator("pre")).to_have_text(
        ["Browser remotely saved business plan", "Browser preserved local business plan"]
    )
    expect(
        other_plan_panel.get_by_role("button", name="Submit for mentor review")
    ).to_be_disabled()
    with other_plan_page.expect_response(
        lambda response: response.url == plan_section_api
    ) as recovered_plan_save:
        other_plan_panel.get_by_role("button", name="Keep my edits", exact=True).click()
    assert recovered_plan_save.value.status == 200
    assert recovered_plan_save.value.request.post_data_json == {
        "expected_version": 3,
        "section_code": "executive_summary",
        "body": "Browser preserved local business plan",
    }
    assert recovered_plan_save.value.json()["version"] == 4
    expect(other_plan_panel.get_by_role("status")).to_have_text("Saved")
    other_plan_page.reload()
    expect(other_summary).to_have_value("Browser preserved local business plan")

    # Independent edits still conflict globally, then reconcile without replacing
    # either section or requiring an overwrite decision from the participant.
    page.reload()
    expect(plan_summary).to_have_value("Browser preserved local business plan")
    with page.expect_response(
        lambda response: response.url == plan_section_api
    ) as problem_plan_save:
        plan_panel.get_by_role("textbox", name="Problem", exact=True).fill(
            "Browser remotely saved customer problem"
        )
    assert problem_plan_save.value.status == 200
    assert problem_plan_save.value.json()["version"] == 5
    expect(plan_panel.get_by_role("status")).to_have_text("Saved")
    with (
        other_plan_page.expect_response(
            lambda response: response.url == plan_section_api and response.status == 409
        ) as independent_conflict,
        other_plan_page.expect_response(
            lambda response: response.url == plan_section_api and response.status == 200
        ) as independent_recovery,
    ):
        other_plan_panel.get_by_role("textbox", name="Solution", exact=True).fill(
            "Browser independently saved repair solution"
        )
    assert independent_conflict.value.request.post_data_json["expected_version"] == 4
    assert independent_recovery.value.request.post_data_json["expected_version"] == 5
    assert independent_recovery.value.json()["version"] == 6
    expect(other_plan_panel.get_by_role("status")).to_have_text("Saved")
    expect(
        other_plan_panel.get_by_role("textbox", name="Problem", exact=True)
    ).to_have_value("Browser remotely saved customer problem")
    other_plan_page.reload()
    expect(other_summary).to_have_value("Browser preserved local business plan")
    expect(
        other_plan_panel.get_by_role("textbox", name="Solution", exact=True)
    ).to_have_value("Browser independently saved repair solution")

    # Leave a real overlapping conflict paused so navigation warnings cannot race
    # the autosave debounce. Canceling warnings must keep the unsaved text intact.
    with other_plan_page.expect_response(
        lambda response: response.url == plan_section_api
    ) as navigation_plan_save:
        other_summary.fill("Browser saved navigation comparison")
    assert navigation_plan_save.value.status == 200
    assert navigation_plan_save.value.json()["version"] == 7
    expect(other_plan_panel.get_by_role("status")).to_have_text("Saved")
    with page.expect_response(
        lambda response: response.url == plan_section_api
    ) as navigation_plan_conflict:
        plan_summary.fill("Browser unsaved navigation draft")
    assert navigation_plan_conflict.value.status == 409
    expect(
        plan_panel.get_by_role("heading", name="Review conflicting edits")
    ).to_be_visible()
    page.once("dialog", lambda dialog: dialog.dismiss())
    with page.expect_event("dialog") as link_warning:
        page.get_by_role("link", name="Your account", exact=True).click()
    assert link_warning.value.type == "confirm"
    expect(page).to_have_url(plan_url)
    expect(plan_summary).to_have_value("Browser unsaved navigation draft")
    page.once("dialog", lambda dialog: dialog.dismiss())
    with page.expect_event("dialog") as reload_warning:
        page.evaluate("window.location.reload()")
    assert reload_warning.value.type == "beforeunload"
    expect(plan_summary).to_have_value("Browser unsaved navigation draft")
    page.once("dialog", lambda dialog: dialog.dismiss())
    with page.expect_event("dialog") as discard_warning:
        plan_panel.get_by_role("button", name="Load saved version", exact=True).click()
    assert discard_warning.value.type == "confirm"
    expect(plan_summary).to_have_value("Browser unsaved navigation draft")
    page.once("dialog", lambda dialog: dialog.accept())
    plan_panel.get_by_role("button", name="Load saved version", exact=True).click()
    expect(plan_summary).to_have_value("Browser saved navigation comparison")
    expect(
        plan_panel.get_by_role("heading", name="Review conflicting edits")
    ).to_have_count(0)
    page.reload()
    expect(plan_summary).to_have_value("Browser saved navigation comparison")
    expect(plan_panel.get_by_role("textbox", name="Problem", exact=True)).to_have_value(
        "Browser remotely saved customer problem"
    )
    expect(plan_panel.get_by_role("textbox", name="Solution", exact=True)).to_have_value(
        "Browser independently saved repair solution"
    )
    assert page.evaluate("Object.keys(localStorage)") == []
    assert page.evaluate("Object.keys(sessionStorage)") == []
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.screenshot(path=str(evidence / "business-plan-mobile.png"), full_page=True)
    page.set_viewport_size({"width": 1280, "height": 900})
    other_plan_page.close()

    # Hand off the M01 assignment through the staff interface. The B01 reviewer
    # has a separate browser session and only Mentor permissions, with no plan
    # ownership or Super Admin grant to mask authorization failures.
    page.goto(base + "/en/admin/mentoring?organization=" + str(organization_id))
    page.get_by_role("button", name="End assignment", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("Mentoring record saved")
    profile_panel.locator('select[name="user_id"]').select_option(
        label="Synthetic Plan Mentor"
    )
    profile_panel.get_by_label("Headline").fill("Independent business-plan mentor")
    profile_panel.get_by_label("Biography").fill("Reviews synthetic plan evidence.")
    profile_panel.get_by_role("button", name="Save", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("Mentoring record saved")
    assignment_panel.locator('select[name="profile"]').select_option(
        label="Synthetic Plan Mentor"
    )
    assignment_panel.locator('select[name="enrollment"]').select_option(
        label="Synthetic E2E"
    )
    assignment_panel.get_by_label("Starts").fill(datetime.now(UTC).date().isoformat())
    assignment_panel.get_by_label("Reason").fill("Independent B01 review handoff")
    assignment_panel.get_by_role("button", name="Assign mentor", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("Mentoring record saved")

    plan_mentor_context = browser.new_context(viewport={"width": 1280, "height": 900})
    plan_mentor_page = plan_mentor_context.new_page()
    plan_mentor_page.on("pageerror", lambda error: errors.append(str(error)))
    plan_mentor_page.goto(base + "/en/account")
    plan_mentor_page.get_by_label("Email", exact=True).fill(plan_mentor_email)
    plan_mentor_page.get_by_label("Password", exact=True).fill(plan_mentor_password)
    plan_mentor_page.locator("form").get_by_role(
        "button", name="Sign in", exact=True
    ).click()
    expect(
        plan_mentor_page.get_by_text("Synthetic Plan Mentor", exact=True)
    ).to_be_visible()
    plan_review_url = base + "/en/admin/business-plans?organization=" + str(organization_id)
    plan_root = base + "/api/business-plans/organizations/" + str(organization_id)
    plan_mentor_page.goto(plan_review_url)
    expect(
        plan_mentor_page.get_by_text("No submitted plans are assigned to you.", exact=True)
    ).to_be_visible()
    assert plan_mentor_page.request.get(plan_root + "/mine").status == 403
    mentor_csrf = plan_mentor_page.request.get(base + "/api/session/csrf").json()[
        "csrf_token"
    ]
    mentor_headers = {"Origin": base, "X-CSRF-Token": mentor_csrf}
    assert plan_mentor_page.request.post(
        plan_section_api,
        data={"expected_version": 7, "section_code": "problem", "body": "Unauthorized"},
        headers=mentor_headers,
    ).status == 403

    unrelated_context = browser.new_context(viewport={"width": 1280, "height": 900})
    unrelated_page = unrelated_context.new_page()
    unrelated_page.on("pageerror", lambda error: errors.append(str(error)))
    unrelated_page.goto(base + "/en/account")
    unrelated_page.get_by_label("Email", exact=True).fill(unrelated_email)
    unrelated_page.get_by_label("Password", exact=True).fill(unrelated_password)
    unrelated_page.locator("form").get_by_role(
        "button", name="Sign in", exact=True
    ).click()
    expect(
        unrelated_page.get_by_text("Synthetic Unrelated Actor", exact=True)
    ).to_be_visible()
    unrelated_page.goto(plan_url)
    expect(
        unrelated_page.get_by_text("No active enrollment is available.", exact=True)
    ).to_be_visible()
    assert unrelated_page.request.get(plan_root + "/mine").json() == {"entries": []}
    unrelated_csrf = unrelated_page.request.get(base + "/api/session/csrf").json()[
        "csrf_token"
    ]
    unrelated_headers = {"Origin": base, "X-CSRF-Token": unrelated_csrf}
    assert unrelated_page.request.post(plan_api, data={}, headers=unrelated_headers).status == 404
    assert unrelated_page.request.post(
        plan_section_api,
        data={"expected_version": 7, "section_code": "problem", "body": "Unauthorized"},
        headers=unrelated_headers,
    ).status == 404
    assert unrelated_page.request.get(
        base + "/api/business-plans/organizations/" + str(uuid4()) + "/mine"
    ).status == 403
    unrelated_page.goto(plan_review_url)
    expect(
        unrelated_page.get_by_text("No submitted plans are assigned to you.", exact=True)
    ).to_be_visible()

    page.goto(plan_url)
    section_labels = {
        "executive_summary": "Executive summary",
        "problem": "Problem",
        "solution": "Solution",
        "product_service": "Product or service",
        "customer_segments": "Customer segments",
        "market": "Market",
        "competition": "Competition",
        "value_proposition": "Value proposition",
        "business_model": "Business model",
        "pricing": "Pricing",
        "sales_marketing": "Sales and marketing",
        "operations": "Operations",
        "team": "Team",
        "investment": "Investment",
        "revenue_assumptions": "Revenue assumptions",
        "expense_assumptions": "Expense assumptions",
        "break_even_inputs": "Break-even inputs",
        "funding_requirement": "Funding requirement",
        "risks": "Risks",
        "milestones": "Milestones",
    }
    submitted_plan_snapshot = {
        code: f"Browser complete planning evidence for {code}." for code in section_labels
    }
    plan_version = 7
    for code, section_label in section_labels.items():
        with page.expect_response(
            lambda response: response.url == plan_section_api
        ) as complete_section_save:
            plan_panel.get_by_role("textbox", name=section_label, exact=True).fill(
                submitted_plan_snapshot[code]
            )
        assert complete_section_save.value.status == 200
        assert (
            complete_section_save.value.request.post_data_json["expected_version"] == plan_version
        )
        plan_version += 1
        assert complete_section_save.value.json()["version"] == plan_version
        expect(plan_panel.get_by_role("status")).to_have_text("Saved")
    expect(plan_panel.get_by_text("20 / 20 sections completed", exact=True)).to_be_visible()
    expect(
        plan_panel.get_by_text(
            "Financial figures are your planning assumptions, not guaranteed outcomes.",
            exact=True,
        )
    ).to_be_visible()
    with page.expect_response(
        lambda response: response.url == plan_api + "/submit"
    ) as first_submission_response:
        plan_panel.get_by_role("button", name="Submit for mentor review", exact=True).click()
    assert first_submission_response.value.status == 200
    first_submission_plan = first_submission_response.value.json()
    plan_version += 1
    assert first_submission_plan["version"] == plan_version
    first_submission = first_submission_plan["submissions"][0]
    assert first_submission["number"] == 1
    assert first_submission["snapshot"] == submitted_plan_snapshot
    first_review_api = plan_root + "/submissions/" + first_submission["id"] + "/review"
    page.reload()
    expect(plan_panel.get_by_text("Submitted for review", exact=True)).to_be_visible()
    for code, section_label in section_labels.items():
        expect(plan_panel.get_by_role("textbox", name=section_label, exact=True)).to_have_value(
            submitted_plan_snapshot[code]
        )
        expect(plan_panel.get_by_role("textbox", name=section_label, exact=True)).to_have_attribute(
            "readonly", ""
        )
    assert page.request.post(
        plan_section_api,
        data={"expected_version": plan_version, "section_code": "problem", "body": "Locked"},
        headers={"Origin": base, "X-CSRF-Token": csrf},
    ).status == 409
    forbidden_review = {
        "expected_version": plan_version,
        "decision": "approved",
        "reason": "Unassigned reviewer attempt",
        "comments": {},
    }
    assert unrelated_page.request.get(plan_root + "/assigned").json() == {"submissions": []}
    assert unrelated_page.request.post(
        first_review_api, data=forbidden_review, headers=unrelated_headers
    ).status == 404
    # Even the former assigned mentor, who also has Super Admin and owns the
    # plan, cannot review it after the assignment has ended.
    assert page.request.get(plan_root + "/assigned").json() == {"submissions": []}
    assert page.request.post(
        first_review_api,
        data=forbidden_review,
        headers={"Origin": base, "X-CSRF-Token": csrf},
    ).status == 404

    plan_mentor_page.reload()
    first_review_card = plan_mentor_page.locator("section.program-panel").filter(
        has=plan_mentor_page.get_by_role("heading", name="Submitted version 1", exact=True)
    )
    expect(first_review_card).to_be_visible()
    for body in submitted_plan_snapshot.values():
        expect(first_review_card.get_by_text(body, exact=True)).to_be_visible()
    expect(plan_mentor_page.get_by_text("Browser private mentor observation")).to_have_count(0)
    first_review_reason = "Clarify the customer evidence before approval."
    first_review_comment = "Add the findings from five customer interviews."
    expect(
        first_review_card.get_by_role("button", name="Record review", exact=True)
    ).to_be_visible()
    first_review_card.locator('select[name="decision"]').select_option("changes_requested")
    first_review_card.get_by_label("Review reason", exact=True).fill(first_review_reason)
    first_review_card.get_by_text("Comments for this section", exact=True).click()
    first_review_card.get_by_role("textbox", name="Executive summary", exact=True).fill(
        first_review_comment
    )
    with plan_mentor_page.expect_response(
        lambda response: response.url == first_review_api
    ) as changes_requested_response:
        first_review_card.get_by_role("button", name="Record review", exact=True).click()
    assert changes_requested_response.value.status == 200
    assert changes_requested_response.value.json()["decision"] == "changes_requested"
    plan_version += 1
    expect(first_review_card.get_by_text(first_review_reason, exact=True)).to_be_visible()
    expect(first_review_card.get_by_text(first_review_comment, exact=False)).to_be_visible()
    plan_mentor_page.reload()
    expect(first_review_card.get_by_text(first_review_reason, exact=True)).to_be_visible()
    assert plan_mentor_page.request.post(
        first_review_api,
        data={**forbidden_review, "expected_version": plan_version},
        headers=mentor_headers,
    ).status == 409

    page.reload()
    expect(plan_panel.get_by_text("Changes requested", exact=True)).to_be_visible()
    first_participant_snapshot = plan_panel.locator("details").filter(
        has=page.locator("summary").filter(has_text="Submitted version 1")
    )
    first_participant_snapshot.locator("summary").click()
    expect(first_participant_snapshot.get_by_text(first_review_reason, exact=True)).to_be_visible()
    expect(
        first_participant_snapshot.get_by_text(first_review_comment, exact=False)
    ).to_be_visible()
    expect(page.get_by_text("Browser private mentor observation")).to_have_count(0)
    revised_summary = "Browser revised plan incorporates five customer interview findings."
    expect(plan_summary).not_to_have_attribute("readonly", "")
    with page.expect_response(
        lambda response: response.url == plan_section_api
    ) as revised_section_response:
        plan_summary.fill(revised_summary)
    assert revised_section_response.value.status == 200
    assert revised_section_response.value.request.post_data_json["expected_version"] == plan_version
    plan_version += 1
    assert revised_section_response.value.json()["version"] == plan_version
    expect(plan_panel.get_by_role("status")).to_have_text("Saved")
    expect(
        first_participant_snapshot.get_by_text(
            submitted_plan_snapshot["executive_summary"], exact=True
        )
    ).to_be_visible()
    with page.expect_response(
        lambda response: response.url == plan_api + "/submit"
    ) as second_submission_response:
        plan_panel.get_by_role("button", name="Submit for mentor review", exact=True).click()
    assert second_submission_response.value.status == 200
    plan_version += 1
    second_submission_plan = second_submission_response.value.json()
    assert second_submission_plan["version"] == plan_version
    second_submission = second_submission_plan["submissions"][0]
    revised_plan_snapshot = {**submitted_plan_snapshot, "executive_summary": revised_summary}
    assert second_submission["number"] == 2
    assert second_submission["snapshot"] == revised_plan_snapshot
    assert second_submission_plan["submissions"][1]["snapshot"] == submitted_plan_snapshot

    plan_mentor_page.reload()
    second_review_card = plan_mentor_page.locator("section.program-panel").filter(
        has=plan_mentor_page.get_by_role("heading", name="Submitted version 2", exact=True)
    )
    expect(second_review_card.get_by_text(revised_summary, exact=True)).to_be_visible()
    expect(
        first_review_card.get_by_text(submitted_plan_snapshot["executive_summary"], exact=True)
    ).to_be_visible()
    expect(first_review_card.get_by_text(first_review_reason, exact=True)).to_be_visible()
    second_review_reason = "Customer evidence is clear and the revised plan is approved."
    expect(
        second_review_card.get_by_role("button", name="Record review", exact=True)
    ).to_be_visible()
    second_review_card.locator('select[name="decision"]').select_option("approved")
    second_review_card.get_by_label("Review reason", exact=True).fill(second_review_reason)
    second_review_api = plan_root + "/submissions/" + second_submission["id"] + "/review"
    with plan_mentor_page.expect_response(
        lambda response: response.url == second_review_api
    ) as approval_response:
        second_review_card.get_by_role("button", name="Record review", exact=True).click()
    assert approval_response.value.status == 200
    assert approval_response.value.json()["decision"] == "approved"
    plan_version += 1
    expect(second_review_card.get_by_text(second_review_reason, exact=True)).to_be_visible()
    plan_mentor_page.reload()
    expect(second_review_card.get_by_text(second_review_reason, exact=True)).to_be_visible()
    expect(first_review_card.get_by_text(first_review_reason, exact=True)).to_be_visible()
    assert plan_mentor_page.evaluate("Object.keys(localStorage)") == []
    assert plan_mentor_page.evaluate("Object.keys(sessionStorage)") == []
    plan_mentor_page.set_viewport_size({"width": 390, "height": 844})
    assert plan_mentor_page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    plan_mentor_page.screenshot(
        path=str(evidence / "business-plan-review-mobile.png"), full_page=True
    )

    page.reload()
    expect(plan_panel.get_by_text("Approved", exact=True)).to_be_visible()
    expect(plan_summary).to_have_value(revised_summary)
    expect(plan_summary).to_have_attribute("readonly", "")
    expect(
        plan_panel.get_by_role("button", name="Submit for mentor review", exact=True)
    ).to_have_count(0)
    participant_submissions = plan_panel.locator("details").filter(
        has=page.locator("summary").filter(has_text="Submitted version")
    )
    expect(participant_submissions).to_have_count(2)
    for snapshot_details in participant_submissions.all():
        snapshot_details.locator("summary").click()
    expect(first_participant_snapshot.get_by_text(first_review_reason, exact=True)).to_be_visible()
    expect(
        first_participant_snapshot.get_by_text(
            submitted_plan_snapshot["executive_summary"], exact=True
        )
    ).to_be_visible()
    expect(plan_panel.get_by_text(second_review_reason, exact=True)).to_be_visible()
    assert page.request.post(
        plan_section_api,
        data={"expected_version": plan_version, "section_code": "problem", "body": "Locked"},
        headers={"Origin": base, "X-CSRF-Token": csrf},
    ).status == 409
    assert page.request.post(
        plan_api + "/submit",
        data={"expected_version": plan_version},
        headers={"Origin": base, "X-CSRF-Token": csrf},
    ).status == 409
    assert plan_mentor_page.request.post(
        second_review_api,
        data={**forbidden_review, "expected_version": plan_version},
        headers=mentor_headers,
    ).status == 409
    plan_mentor_context.close()
    unrelated_context.close()

    page.goto(base + "/en/businesses?organization=" + str(organization_id))
    expect(
        page.get_by_role("heading", name="My business", exact=True, level=1)
    ).to_be_visible()
    business_panel = page.locator("section.program-panel")
    business_panel.get_by_label("Business name", exact=True).fill(
        "Browser repair workshop"
    )
    business_panel.get_by_label("Sector", exact=True).fill("Repair services")
    business_panel.get_by_role("textbox", name="Products and services", exact=True).fill(
        "Synthetic bicycle repair services"
    )
    business_panel.get_by_role("button", name="Save business", exact=True).click()
    expect(business_panel.get_by_role("status")).to_have_text("Saved.")
    business_panel.get_by_text("Profile versions", exact=True).click()
    expect(
        business_panel.locator("details").last.get_by_role("listitem")
    ).to_have_count(1)

    page.reload()
    expect(business_panel.get_by_label("Business name", exact=True)).to_have_value(
        "Browser repair workshop"
    )
    business_panel.get_by_label("Business name", exact=True).fill(
        "Browser expanded repair workshop"
    )
    business_panel.get_by_role("textbox", name="Support needed", exact=True).fill(
        "Synthetic equipment advice"
    )
    business_panel.get_by_role("button", name="Save business", exact=True).click()
    expect(business_panel.get_by_role("status")).to_have_text("Saved.")

    page.reload()
    expect(business_panel.get_by_label("Business name", exact=True)).to_have_value(
        "Browser expanded repair workshop"
    )
    expect(
        business_panel.get_by_role("textbox", name="Support needed", exact=True)
    ).to_have_value(
        "Synthetic equipment advice"
    )
    business_panel.get_by_text("Profile versions", exact=True).click()
    expect(
        business_panel.locator("details").last.get_by_role("listitem")
    ).to_have_count(2)
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.screenshot(path=str(evidence / "business-tracking-mobile.png"), full_page=True)
    page.set_viewport_size({"width": 1280, "height": 900})

    with Session(engine) as db:
        assignment = db.scalar(
            select(ReviewAssignment).where(
                ReviewAssignment.organization_id == organization_id
            )
        )
        assert assignment and assignment.conflict_status == "clear"
        assert assignment.status == "completed"
        assert float(assignment.weighted_score or 0) == 80
        assert assignment.moderation_status == "included"
        application = db.scalar(
            select(Application).where(Application.organization_id == organization_id)
        )
        interview = db.scalar(
            select(Interview).where(Interview.organization_id == organization_id)
        )
        selection_cycle = db.scalar(
            select(SelectionCycle).where(
                SelectionCycle.organization_id == organization_id
            )
        )
        decisions = list(
            db.scalars(
                select(SelectionDecision).where(
                    SelectionDecision.organization_id == organization_id
                )
            )
        )
        participant = db.scalar(
            select(Participant).where(Participant.organization_id == organization_id)
        )
        enrollment = db.scalar(
            select(Enrollment).where(Enrollment.organization_id == organization_id)
        )
        program_sessions = list(
            db.scalars(
                select(ProgramSession).where(
                    ProgramSession.organization_id == organization_id
                )
            )
        )
        staff_assignment = db.scalar(
            select(ProgramStaffAssignment)
            .join(User, User.id == ProgramStaffAssignment.user_id)
            .where(
                ProgramStaffAssignment.organization_id == organization_id,
                User.email == coordinator_email,
            )
        )
        trainer_assignment = db.scalar(
            select(ProgramStaffAssignment)
            .join(User, User.id == ProgramStaffAssignment.user_id)
            .where(
                ProgramStaffAssignment.organization_id == organization_id,
                User.email == trainer_email,
            )
        )
        outbox = db.scalar(
            select(DomainOutbox).where(DomainOutbox.organization_id == organization_id)
        )
        course = db.scalar(
            select(Course).where(Course.organization_id == organization_id)
        )
        cohort_course = db.scalar(
            select(CohortCourse).where(CohortCourse.organization_id == organization_id)
        )
        course_enrollment = db.scalar(
            select(CourseEnrollment).where(
                CourseEnrollment.organization_id == organization_id
            )
        )
        assert application and application.state == "enrolled"
        assert (
            participant and enrollment and enrollment.participant_id == participant.id
        )
        assert {item.title_en for item in program_sessions} == {
            "Business foundations",
            "Coordinator session",
            "Attendance check-in lab",
        }
        assert staff_assignment and staff_assignment.state == "revoked"
        assert staff_assignment.revoked_at is not None
        assert trainer_assignment and trainer_assignment.state == "active"
        assert outbox and outbox.event_type == "enrollment.created"
        assert course and course.state == "published"
        assert cohort_course and cohort_course.course_id == course.id
        assert course_enrollment and course_enrollment.course_id == course.id
        assert course_enrollment.enrollment_id == enrollment.id
        assert course_enrollment.status == "completed"
        assert course_enrollment.completed_at is not None
        assignment_submissions = list(
            db.scalars(
                select(AssignmentSubmission).where(
                    AssignmentSubmission.course_enrollment_id == course_enrollment.id
                )
            )
        )
        assert len(assignment_submissions) == 1
        assignment_grade = db.scalar(
            select(AssignmentGrade).where(
                AssignmentGrade.submission_id == assignment_submissions[0].id
            )
        )
        assert assignment_grade and assignment_grade.score_points == 15
        assert assignment_grade.passed is True
        quiz_attempts = list(
            db.scalars(
                select(QuizAttempt).where(
                    QuizAttempt.course_enrollment_id == course_enrollment.id
                )
            )
        )
        assert len(quiz_attempts) == 2
        assert [attempt.percent for attempt in quiz_attempts] == [0, 100]
        assert quiz_attempts[-1].passed is True
        lesson_progress = db.scalar(
            select(LessonProgress).where(
                LessonProgress.course_enrollment_id == course_enrollment.id
            )
        )
        assert lesson_progress is not None
        certificate_template = db.scalar(
            select(CertificateTemplate).where(
                CertificateTemplate.organization_id == organization_id
            )
        )
        certificate = db.scalar(
            select(Certificate).where(Certificate.organization_id == organization_id)
        )
        attendance_policy = db.scalar(
            select(AttendancePolicy).where(
                AttendancePolicy.organization_id == organization_id
            )
        )
        attendance_record = db.scalar(
            select(AttendanceRecord).where(
                AttendanceRecord.organization_id == organization_id,
                AttendanceRecord.session_id == attendance_session_id,
            )
        )
        mentor_assignment = db.scalar(
            select(MentorAssignment)
            .join(MentorProfile, MentorProfile.id == MentorAssignment.mentor_profile_id)
            .where(
                MentorAssignment.organization_id == organization_id,
                MentorProfile.user_id == plan_mentor_user_id,
            )
        )
        mentoring_session = db.scalar(
            select(MentoringSession).where(
                MentoringSession.organization_id == organization_id
            )
        )
        mentoring_notes = list(
            db.scalars(
                select(MentoringNote).where(
                    MentoringNote.organization_id == organization_id
                )
            )
        )
        mentoring_goal = db.scalar(
            select(Goal).where(Goal.organization_id == organization_id)
        )
        mentoring_action = db.scalar(
            select(ActionItem).where(ActionItem.organization_id == organization_id)
        )
        mentoring_follow_up = db.scalar(
            select(FollowUp).where(FollowUp.organization_id == organization_id)
        )
        mentoring_feedback = db.scalar(
            select(MentoringFeedback).where(
                MentoringFeedback.organization_id == organization_id
            )
        )
        assert certificate_template and certificate_template.state == "published"
        assert certificate and certificate.status == "valid"
        assert certificate.course_enrollment_id == course_enrollment.id
        assert attendance_policy and attendance_policy.threshold_percent == 80
        assert attendance_record and attendance_record.source == "qr"
        assert attendance_record.status == "present"
        assert mentor_assignment and mentor_assignment.state == "active"
        assert mentoring_session and mentoring_session.status == "completed"
        original_mentor_assignment = db.get(MentorAssignment, mentoring_session.assignment_id)
        assert original_mentor_assignment and original_mentor_assignment.state == "ended"
        assert original_mentor_assignment.ended_at is not None
        assert {item.visibility for item in mentoring_notes} == {
            "mentor_private",
            "shared_with_participant",
        }
        assert mentoring_goal and mentoring_goal.state == "active"
        assert mentoring_action and mentoring_action.state == "open"
        assert mentoring_follow_up and mentoring_follow_up.state == "scheduled"
        assert mentoring_feedback and mentoring_feedback.rating == 5
        business_plan = db.get(BusinessPlan, plan_id)
        assert business_plan and business_plan.organization_id == organization_id
        assert business_plan.enrollment_id == enrollment.id
        assert business_plan.status == "approved" and business_plan.version == plan_version == 32
        plan_revisions = list(
            db.scalars(
                select(BusinessPlanRevision)
                .where(BusinessPlanRevision.plan_id == plan_id)
                .order_by(BusinessPlanRevision.version)
            )
        )
        assert [
            (revision.version, revision.section_code, revision.body)
            for revision in plan_revisions[:6]
        ] == [
            (2, "executive_summary", "Browser baseline business plan"),
            (3, "executive_summary", "Browser remotely saved business plan"),
            (4, "executive_summary", "Browser preserved local business plan"),
            (5, "problem", "Browser remotely saved customer problem"),
            (6, "solution", "Browser independently saved repair solution"),
            (7, "executive_summary", "Browser saved navigation comparison"),
        ]
        assert [
            (revision.version, revision.section_code, revision.body)
            for revision in plan_revisions[6:26]
        ] == [
            (number, code, submitted_plan_snapshot[code])
            for number, code in enumerate(section_labels, start=8)
        ]
        assert len(plan_revisions) == 27
        assert plan_revisions[-1].version == 30
        assert plan_revisions[-1].section_code == "executive_summary"
        assert plan_revisions[-1].body == revised_summary
        plan_submissions = list(
            db.scalars(
                select(BusinessPlanSubmission)
                .where(BusinessPlanSubmission.plan_id == plan_id)
                .order_by(BusinessPlanSubmission.number)
            )
        )
        assert [item.number for item in plan_submissions] == [1, 2]
        assert [str(item.id) for item in plan_submissions] == [
            first_submission["id"], second_submission["id"]
        ]
        assert [item.snapshot for item in plan_submissions] == [
            submitted_plan_snapshot, revised_plan_snapshot
        ]
        plan_reviews = list(
            db.scalars(
                select(BusinessPlanReview)
                .join(
                    BusinessPlanSubmission,
                    BusinessPlanSubmission.id == BusinessPlanReview.submission_id,
                )
                .where(BusinessPlanSubmission.plan_id == plan_id)
                .order_by(BusinessPlanSubmission.number)
            )
        )
        assert [item.decision for item in plan_reviews] == ["changes_requested", "approved"]
        assert [item.reason for item in plan_reviews] == [first_review_reason, second_review_reason]
        assert [item.comments for item in plan_reviews] == [
            {"executive_summary": first_review_comment}, {}
        ]
        assert {item.reviewer_user_id for item in plan_reviews} == {plan_mentor_user_id}
        plan_owner = db.scalar(select(User).where(User.email == email))
        assert plan_owner
        assert {item.submitted_by_user_id for item in plan_submissions} == {plan_owner.id}
        assert {item.author_user_id for item in plan_revisions} == {plan_owner.id}
        plan_audit = list(
            db.scalars(
                select(AuditLog)
                .where(AuditLog.organization_id == organization_id, AuditLog.resource_id == plan_id)
                .order_by(AuditLog.resource_version)
            )
        )
        assert [item.resource_version for item in plan_audit] == list(range(1, 33))
        assert [item.action for item in plan_audit] == (
            ["business_plan.created"]
            + ["business_plan.section_saved"] * 26
            + ["business_plan.submitted", "business_plan.reviewed", "business_plan.section_saved",
               "business_plan.submitted", "business_plan.reviewed"]
        )
        for item in plan_audit:
            assert item.request_id and item.reason is None
            assert item.actor_id != unrelated_user_id
            if item.action == "business_plan.reviewed":
                assert item.actor_id == plan_mentor_user_id
                assert item.changed_fields == "status,review"
            else:
                assert item.actor_id == plan_owner.id
                assert item.changed_fields in {
                    "enrollment_id", "status,submission_number", *section_labels
                }
        business_profile = db.scalar(
            select(BusinessProfile).where(
                BusinessProfile.organization_id == organization_id
            )
        )
        assert business_profile
        assert business_profile.name == "Browser expanded repair workshop"
        assert business_profile.version == 2
        business_revisions = list(
            db.scalars(
                select(BusinessProfileRevision)
                .where(BusinessProfileRevision.profile_id == business_profile.id)
                .order_by(BusinessProfileRevision.version)
            )
        )
        assert [revision.version for revision in business_revisions] == [1, 2]
        assert business_revisions[0].snapshot["name"] == "Browser repair workshop"
        assert business_revisions[1].snapshot["name"] == "Browser expanded repair workshop"
        assert interview and interview.status == "completed"
        assert float(interview.average_score or 0) == 84
        assert selection_cycle and selection_cycle.state == "closed"
        assert len(decisions) == 4 and sum(item.is_override for item in decisions) == 2
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.screenshot(path=str(evidence / "selection-mobile.png"), full_page=True)
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(base + "/en/admin?organization=" + str(uuid4()))
    expect(
        page.get_by_text("You do not have access to this workspace.")
    ).to_be_visible()
    page.goto(base + "/en/account")
    page.wait_for_load_state("domcontentloaded")
    page.get_by_role("button", name="Sign out all devices", exact=True).click()
    expect(page.get_by_label("Email", exact=True)).to_be_visible()
    assert page.request.get(base + "/api/session/me").status == 401
    page.get_by_role("button", name="Forgot password", exact=True).click()
    page.get_by_label("Email", exact=True).fill(email)
    page.locator("form").get_by_role(
        "button", name="Forgot password", exact=True
    ).click()
    expect(page.get_by_role("status")).to_contain_text("message has been queued")
    page.get_by_role("button", name="Reset password", exact=True).click()
    page.get_by_label("Verification or reset code", exact=True).fill(
        latest_token("reset")
    )
    new_password = secrets.token_urlsafe(24)
    page.get_by_label("Password", exact=True).fill(new_password)
    page.locator("form").get_by_role(
        "button", name="Reset password", exact=True
    ).click()
    expect(page.get_by_role("status")).to_contain_text("You can now sign in")
    page.get_by_role("button", name="Sign in", exact=True).click()
    page.get_by_label("Email", exact=True).fill(email)
    page.get_by_label("Password", exact=True).fill(new_password)
    page.locator("form").get_by_role("button", name="Sign in", exact=True).click()
    expect(page.get_by_text("Synthetic E2E", exact=True)).to_be_visible()
    page.get_by_role("button", name="Sign out", exact=True).click()
    expect(page.get_by_label("Email", exact=True)).to_be_visible()
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(base + "/ta/account")
    page.wait_for_load_state("domcontentloaded")
    assert page.locator("html").get_attribute("lang") == "ta"
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.screenshot(path=str(evidence / "account-ta-mobile.png"), full_page=True)
    assert not errors, errors
    participant_context.close()
    browser.close()
engine.dispose()
print(
    "Browser E2E passed: identity, CSRF, scoped CMS, application policy "
    "publish/versioning, immutable application submission, selection rubric/assignment/"
    "conflict/scoring/moderation/interview/decisions/finalization, enrollment/participant/"
    "session/timeline, center-scoped coordinator assignment/revocation, trainer-scoped "
    "delivery, learner/trainer private-material downloads, learning authoring/publication/"
    "cohort access/start/quiz grading/assignment grading and feedback/completion/"
    "certificate eligibility/issuance/public QR verification, attendance policy/QR check-in, "
    "mentor assignment/session/private-shared notes/goals/actions/reminders/feedback, "
    "business plan autosave/two-tab reconciliation/explicit conflict recovery/"
    "navigation warnings/confirmed discard/all20sections/independent assigned mentor/"
    "changes requested/feedback/revision/resubmission/approval/locked snapshots/"
    "authorization negatives and immutable revisions/submissions/reviews/audit, "
    "business profile create/reload/update and immutable revision history, audit, "
    "responsive layouts and session recovery; "
    "no JS errors"
)
