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
mentor_email = "mentor-" + uuid4().hex[:12] + "@example.com"
mentor_password = secrets.token_urlsafe(24)


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


def load_business_plan_data(browser_page, endpoint, url=None):
    """Wait for the private data fetch, rather than background Next.js traffic."""
    with browser_page.expect_response(
        lambda response: response.url == endpoint and response.request.method == "GET",
        timeout=15000,
    ) as loaded:
        if url:
            browser_page.goto(url)
        else:
            browser_page.reload()
    assert loaded.value.status == 200
    return loaded.value.json()


def assert_business_plan_field_layout(controls, expected_count):
    """Catch labels beside textareas even when the document itself does not overflow."""
    expect(controls).to_have_count(expected_count)
    fields = controls.evaluate_all("""controls => controls.map(control => {
      const label = control.closest('label');
      if (!label) return { error: 'A plan control has no associated label' };
      const heading = document.createRange();
      heading.selectNodeContents(label);
      heading.setEndBefore(control);
      const title = heading.getBoundingClientRect();
      const box = control.getBoundingClientRect();
      const parent = label.getBoundingClientRect();
      const style = getComputedStyle(label);
      const insetLeft = parseFloat(style.borderLeftWidth) + parseFloat(style.paddingLeft);
      const insetRight = parseFloat(style.borderRightWidth) + parseFloat(style.paddingRight);
      return { label: heading.toString().trim(), titleBottom: title.bottom,
        titleHeight: title.height, top: box.top, bottom: box.bottom, left: box.left,
        right: box.right, width: box.width, labelTop: parent.top, labelBottom: parent.bottom,
        contentLeft: parent.left + insetLeft, contentRight: parent.right - insetRight,
        availableWidth: parent.width - insetLeft - insetRight, viewportWidth: innerWidth };
    })""")
    for field in fields:
        assert "error" not in field, field
        assert field["label"] and field["titleHeight"] > 0, field
        assert field["titleBottom"] <= field["top"] + 1, field
        assert field["top"] >= field["labelTop"] - 1, field
        assert field["bottom"] <= field["labelBottom"] + 1, field
        assert field["left"] >= field["contentLeft"] - 1, field
        assert field["right"] <= field["contentRight"] + 1, field
        assert field["width"] >= field["availableWidth"] * 0.95, field
        assert field["left"] >= 0 and field["right"] <= field["viewportWidth"], field


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        channel=os.getenv("PLAYWRIGHT_CHANNEL"), headless=True
    )
    page = browser.new_page(viewport={"width": 1280, "height": 900})
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
    organization_card = page.locator(".account-organizations > li").filter(
        has_text="Synthetic E2E Organization"
    )
    staff_link = organization_card.get_by_role("link", name="Staff workspace", exact=True)
    expect(staff_link).to_have_attribute(
        "href", f"/en/admin?organization={organization_id}"
    )
    staff_link.click()
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
    public.on("pageerror", lambda error: errors.append(str(error)))
    public_dialogs = []
    public.on(
        "dialog", lambda dialog: (public_dialogs.append(dialog.message), dialog.dismiss())
    )
    public.goto(base + "/en/pages/eligibility")
    expect(public.get_by_role("heading", name="Who can apply")).to_be_visible()
    published_article = public.get_by_role("article")
    expect(
        published_article.get_by_text(
            "Synthetic eligibility <script>alert(1)</script>", exact=True
        )
    ).to_be_visible()
    expect(published_article.locator("script")).to_have_count(0)
    assert not public_dialogs, public_dialogs
    page.screenshot(path=str(evidence / "cms-debug.png"), full_page=True)
    page.get_by_label("Content", exact=True).fill("Unpublished change")
    page.get_by_role("button", name="Save draft", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Saved")
    public.reload()
    expect(published_article).to_contain_text("Synthetic eligibility <script>alert(1)</script>")
    expect(published_article).not_to_contain_text("Unpublished change")
    expect(published_article.locator("script")).to_have_count(0)
    assert not public_dialogs, public_dialogs
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
    expect(public.get_by_role("article")).to_contain_text("Tamil synthetic content")
    page.locator("details.cms-archive > summary").click()
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
    attendance_card = page.get_by_role("article", name="Attendance check-in lab", exact=True)
    attendance_card.locator("details.attendance-policy > summary").click()
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
    page.get_by_role("link", name="Course structure", exact=True).click()
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
    expect(
        page.locator(".program-list li").filter(has_text=coordinator_email)
        .get_by_text("Revoked", exact=True)
    ).to_be_visible()
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
        assert mentor_role
        mentor_person = Person(display_name="Synthetic Mentor")
        db.add(mentor_person)
        db.flush()
        mentor_user = User(
            person_id=mentor_person.id,
            email=mentor_email,
            password_hash=hasher.hash(mentor_password),
            status="active",
        )
        db.add(mentor_user)
        db.flush()
        mentor_user_id = mentor_user.id
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
    profile_panel = page.locator(".mentor-workspace [data-slot=card].program-panel").filter(
        has=page.get_by_role("heading", name="Create mentor profile", exact=True)
    )
    profile_panel.locator('select[name="user_id"]').select_option(label="Synthetic Mentor")
    profile_panel.get_by_label("Headline").fill("Enterprise mentor")
    profile_panel.get_by_label("Biography").fill("Supports participant validation.")
    profile_panel.get_by_role("button", name="Save", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("Mentoring record saved")

    assignment_panel = page.locator(".mentor-workspace [data-slot=card].program-panel").filter(
        has=page.get_by_role("heading", name="Assign mentor", exact=True)
    )
    assignment_panel.locator('select[name="profile"]').select_option(
        label="Synthetic Mentor"
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
    schedule_panel = page.locator(".mentor-workspace [data-slot=card].program-panel").filter(
        has=page.get_by_role("heading", name="Schedule session", exact=True)
    )
    schedule_panel.locator('select[name="assignment"]').select_option(
        label="Synthetic E2E · Synthetic Mentor"
    )
    schedule_panel.get_by_label("Topic").fill("Browser customer discovery review")
    schedule_panel.get_by_label("Starts").fill(session_start.strftime("%Y-%m-%dT%H:%M"))
    schedule_panel.get_by_label("Ends").fill(session_end.strftime("%Y-%m-%dT%H:%M"))
    schedule_panel.get_by_label("Location or link").fill("https://meet.example/e2e")
    schedule_panel.get_by_role("button", name="Schedule session", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("Mentoring record saved")

    notes_panel = page.locator(".mentor-workspace [data-slot=card].program-panel").filter(
        has=page.get_by_role("heading", name="Notes", exact=True)
    )
    notes_panel.locator('select[name="assignment"]').select_option(
        label="Synthetic E2E · Synthetic Mentor"
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
    notes_panel = page.locator(".mentor-workspace [data-slot=card].program-panel").filter(
        has=page.get_by_role("heading", name="Notes", exact=True)
    )
    notes_panel.locator('select[name="assignment"]').select_option(
        label="Synthetic E2E · Synthetic Mentor"
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
        page.locator(".mentor-workspace [data-slot=card].program-panel")
        .filter(has=page.get_by_role("heading", name="Goals", exact=True))
        .first
    )
    goal_panel.locator('select[name="assignment"]').select_option(
        label="Synthetic E2E · Synthetic Mentor"
    )
    goal_panel.get_by_label("Goal").fill("Validate customer demand")
    goal_panel.get_by_role("button", name="Save", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("Mentoring record saved")

    action_panel = (
        page.locator(".mentor-workspace [data-slot=card].program-panel")
        .filter(has=page.get_by_role("heading", name="Action items", exact=True))
        .first
    )
    action_panel.locator('select[name="assignment"]').select_option(
        label="Synthetic E2E · Synthetic Mentor"
    )
    action_panel.locator('select[name="goal"]').select_option(
        label="Validate customer demand"
    )
    action_panel.get_by_label("Action").fill("Complete customer interviews")
    action_panel.get_by_role("button", name="Save", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("Mentoring record saved")

    reminder_panel = (
        page.locator(".mentor-workspace [data-slot=card].program-panel")
        .filter(has=page.get_by_role("heading", name="Follow-up reminders", exact=True))
        .first
    )
    reminder_panel.locator('select[name="assignment"]').select_option(
        label="Synthetic E2E · Synthetic Mentor"
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

    session_list = page.locator(".mentor-workspace [data-slot=card].program-panel").filter(
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

    # B01 uses a distinct Mentor-only identity so a broad staff grant cannot
    # accidentally satisfy the active assignment/participant ownership boundary.
    mentor_context = browser.new_context(viewport={"width": 1280, "height": 900})
    mentor_page = mentor_context.new_page()
    mentor_page.on("pageerror", lambda error: errors.append(str(error)))
    mentor_page.goto(base + "/en/account")
    expect(mentor_page.get_by_label("Email", exact=True)).to_be_visible()
    mentor_page.get_by_label("Email", exact=True).fill(mentor_email)
    mentor_page.get_by_label("Password", exact=True).fill(mentor_password)
    mentor_page.locator("form").get_by_role(
        "button", name="Sign in", exact=True
    ).click()
    expect(mentor_page.get_by_text("Synthetic Mentor", exact=True)).to_be_visible()
    plan_api = base + "/api/business-plans/organizations/" + str(organization_id)
    assert load_business_plan_data(
        mentor_page, plan_api + "/assigned",
        base + "/en/admin/business-plans?organization=" + str(organization_id),
    ) == {"submissions": []}
    expect(
        mentor_page.get_by_text("No submitted plans are assigned to you.", exact=True)
    ).to_be_visible()
    assert mentor_page.request.get(plan_api + "/mine").status == 403

    load_business_plan_data(
        page, plan_api + "/mine",
        base + "/en/business-plan?organization=" + str(organization_id),
    )
    expect(page.get_by_role("heading", name="My business plan", level=1)).to_be_visible()
    expect(
        page.get_by_text(
            "Financial figures are your planning assumptions, not guaranteed outcomes.",
            exact=True,
        )
    ).to_be_visible()
    with page.expect_response(
        lambda response: response.url.startswith(plan_api + "/enrollments/")
        and response.request.method == "POST"
    ) as plan_created:
        page.get_by_role("button", name="Start a plan", exact=True).click()
    assert plan_created.value.status == 201
    plan = plan_created.value.json()
    plan_id = UUID(plan["id"])
    enrollment_plan_api = plan_api + "/enrollments/" + plan["enrollment_id"]
    expect(page.get_by_text("0 / 20 sections completed", exact=True)).to_be_visible()
    submit_plan = page.get_by_role("button", name="Submit for mentor review", exact=True)
    expect(submit_plan).to_be_disabled()
    plan_headers = {
        "Origin": base,
        "X-CSRF-Token": page.request.get(base + "/api/session/csrf").json()["csrf_token"],
    }
    assert page.request.post(
        enrollment_plan_api + "/submit",
        data={"expected_version": plan["version"]},
        headers=plan_headers,
    ).status == 422

    # These are the twenty master Section 14 fields; exercise every actual editor.
    plan_sections = [
        ("executive_summary", "Executive summary"),
        ("problem", "Problem"),
        ("solution", "Solution"),
        ("product_service", "Product or service"),
        ("customer_segments", "Customer segments"),
        ("market", "Market"),
        ("competition", "Competition"),
        ("value_proposition", "Value proposition"),
        ("business_model", "Business model"),
        ("pricing", "Pricing"),
        ("sales_marketing", "Sales and marketing"),
        ("operations", "Operations"),
        ("team", "Team"),
        ("investment", "Investment"),
        ("revenue_assumptions", "Revenue assumptions"),
        ("expense_assumptions", "Expense assumptions"),
        ("break_even_inputs", "Break-even inputs"),
        ("funding_requirement", "Funding requirement"),
        ("risks", "Risks"),
        ("milestones", "Milestones"),
    ]
    expect(page.locator("textarea")).to_have_count(20)
    initial_snapshot = {}
    for number, (code, label) in enumerate(plan_sections, start=1):
        body = "Synthetic browser planning evidence for " + label.lower() + "."
        initial_snapshot[code] = body
        with page.expect_response(
            lambda response: response.url == enrollment_plan_api + "/sections"
            and response.request.method == "POST"
        ) as section_saved:
            page.get_by_role("textbox", name=label, exact=True).fill(body)
        assert section_saved.value.status == 200
        plan = section_saved.value.json()
        assert plan["sections"][code] == body
        assert plan["completed_sections"] == number
        expect(
            page.get_by_text(f"{number} / 20 sections completed", exact=True)
        ).to_be_visible()
        if number == 1:
            reloaded = load_business_plan_data(page, plan_api + "/mine")
            assert reloaded["entries"][0]["plan"]["sections"][code] == body
            # An implicit <label> contains the textarea's initial text after a
            # reload. Its accessible textbox name remains the section heading.
            expect(page.get_by_role("textbox", name=label, exact=True)).to_have_value(
                body, timeout=15000
            )
            expect(submit_plan).to_be_disabled()
            assert page.request.post(
                enrollment_plan_api + "/sections",
                data={"expected_version": 1, "section_code": code, "body": "Stale edit"},
                headers=plan_headers,
            ).status == 409
            # Even an assigned mentor sees no draft content in the review API.
            draft_queue = mentor_page.request.get(plan_api + "/assigned")
            assert draft_queue.status == 200
            assert draft_queue.json() == {"submissions": []}
            mentor_headers = {
                "Origin": base,
                "X-CSRF-Token": mentor_page.request.get(base + "/api/session/csrf")
                .json()["csrf_token"],
            }
            assert mentor_page.request.post(
                enrollment_plan_api + "/sections",
                data={"expected_version": plan["version"], "section_code": code,
                      "body": "Mentor must not edit participant draft"},
                headers=mentor_headers,
            ).status == 403

    expect(submit_plan).to_be_enabled()
    page.set_viewport_size({"width": 390, "height": 844})
    assert_business_plan_field_layout(page.locator("textarea"), 20)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.evaluate("window.scrollTo({top: 0, left: 0, behavior: 'instant'})")
    page.screenshot(path=str(evidence / "business-plan-en-mobile.png"), full_page=True)
    page.set_viewport_size({"width": 1280, "height": 900})
    with page.expect_response(
        lambda response: response.url == enrollment_plan_api + "/submit"
    ) as submitted_plan:
        submit_plan.click()
    assert submitted_plan.value.status == 200
    plan = submitted_plan.value.json()
    assert plan["status"] == "submitted"
    assert plan["submissions"][0]["snapshot"] == initial_snapshot
    first_submission_id = plan["submissions"][0]["id"]
    expect(page.get_by_role("textbox", name="Executive summary", exact=True)).to_be_disabled()
    assert page.request.post(
        enrollment_plan_api + "/sections",
        data={"expected_version": plan["version"], "section_code": "executive_summary",
              "body": "Cannot overwrite submitted evidence"},
        headers=plan_headers,
    ).status == 409
    # The participant's Super Admin setup grant does not confer mentor assignment.
    assert page.request.get(plan_api + "/assigned").json() == {"submissions": []}
    assert page.request.post(
        plan_api + "/submissions/" + first_submission_id + "/review",
        data={"expected_version": plan["version"], "decision": "approved",
              "reason": "Unassigned review must fail", "comments": {}},
        headers=plan_headers,
    ).status == 404

    assigned = load_business_plan_data(mentor_page, plan_api + "/assigned")
    assert assigned["submissions"][0]["snapshot"] == initial_snapshot
    first_review_card = mentor_page.locator(".plan-review-card").filter(
        has=mentor_page.get_by_role("heading", name="Version 1", exact=True)
    )
    expect(first_review_card).to_be_visible()
    expect(
        first_review_card.get_by_text(initial_snapshot["executive_summary"], exact=True)
    ).to_be_visible()
    expect(mentor_page.get_by_text("Browser private mentor observation")).to_have_count(0)
    first_review_card.get_by_label("Review reason", exact=True).fill(
        "Add dated customer evidence before approval."
    )
    first_review_card.get_by_text("Comments for this section", exact=True).click()
    first_review_card.get_by_label("Executive summary", exact=True).fill(
        "Include the date and findings from five customer interviews."
    )
    mentor_page.set_viewport_size({"width": 390, "height": 844})
    assert_business_plan_field_layout(first_review_card.locator("form select, form textarea"), 22)
    assert mentor_page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    mentor_page.evaluate("window.scrollTo({top: 0, left: 0, behavior: 'instant'})")
    mentor_page.screenshot(
        path=str(evidence / "business-plan-mentor-form-mobile.png"), full_page=True
    )
    mentor_page.set_viewport_size({"width": 1280, "height": 900})
    first_review_card.get_by_role("button", name="Record review", exact=True).click()
    expect(first_review_card.get_by_role("status")).to_have_text("Review saved.")
    reloaded = load_business_plan_data(page, plan_api + "/mine")
    assert reloaded["entries"][0]["plan"]["status"] == "changes_requested"
    expect(page.get_by_text("Changes requested", exact=True)).to_be_visible(timeout=15000)
    expect(page.get_by_role("textbox", name="Executive summary", exact=True)).to_be_enabled()
    first_submission = page.locator("details").filter(
        has=page.locator("summary").filter(has_text="Submitted version 1")
    )
    first_submission.locator("summary").click()
    expect(
        first_submission.get_by_text("Add dated customer evidence before approval.", exact=True)
    ).to_be_visible()
    expect(
        first_submission.get_by_text(
            "Include the date and findings from five customer interviews.", exact=False
        )
    ).to_be_visible()
    expect(page.get_by_text("Browser private mentor observation")).to_have_count(0)
    revised_summary = "Five synthetic interviews dated 2026-10-01 confirm repeated delays."
    with page.expect_response(
        lambda response: response.url == enrollment_plan_api + "/sections"
    ) as revised_plan:
        page.get_by_role("textbox", name="Executive summary", exact=True).fill(revised_summary)
    assert revised_plan.value.status == 200
    plan = revised_plan.value.json()
    assert plan["submissions"][0]["snapshot"] == initial_snapshot
    expect(submit_plan).to_be_enabled()
    with page.expect_response(
        lambda response: response.url == enrollment_plan_api + "/submit"
    ) as resubmitted_plan:
        submit_plan.click()
    assert resubmitted_plan.value.status == 200
    plan = resubmitted_plan.value.json()
    assert [item["number"] for item in plan["submissions"]] == [2, 1]
    assert plan["submissions"][1]["snapshot"] == initial_snapshot
    assert plan["submissions"][0]["snapshot"]["executive_summary"] == revised_summary

    assigned = load_business_plan_data(mentor_page, plan_api + "/assigned")
    assert [item["number"] for item in assigned["submissions"]] == [2, 1]
    second_review_card = mentor_page.locator(".plan-review-card").filter(
        has=mentor_page.get_by_role("heading", name="Version 2", exact=True)
    )
    expect(second_review_card.get_by_text(revised_summary, exact=True)).to_be_visible()
    second_review_card.get_by_role("combobox", name="Decision", exact=True).select_option(
        "approved"
    )
    second_review_card.get_by_label("Review reason", exact=True).fill(
        "Customer evidence reviewed; plan accepted for this synthetic exercise."
    )
    second_review_card.get_by_role("button", name="Record review", exact=True).click()
    expect(second_review_card.get_by_role("status")).to_have_text("Review saved.")
    mentor_page.set_viewport_size({"width": 390, "height": 844})
    assert mentor_page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    mentor_page.evaluate("window.scrollTo({top: 0, left: 0, behavior: 'instant'})")
    mentor_page.screenshot(
        path=str(evidence / "business-plan-mentor-mobile.png"), full_page=True
    )
    assert mentor_page.evaluate("Object.keys(localStorage)") == []
    mentor_context.close()

    reloaded = load_business_plan_data(page, plan_api + "/mine")
    assert reloaded["entries"][0]["plan"]["status"] == "approved"
    expect(page.get_by_text("Approved", exact=True)).to_be_visible(timeout=15000)
    expect(page.get_by_role("textbox", name="Executive summary", exact=True)).to_be_disabled()
    expect(submit_plan).to_have_count(0)
    second_submission = page.locator("details").filter(
        has=page.locator("summary").filter(has_text="Submitted version 2")
    )
    second_submission.locator("summary").click()
    expect(
        second_submission.get_by_text(
            "Customer evidence reviewed; plan accepted for this synthetic exercise.", exact=True
        )
    ).to_be_visible()
    page.get_by_text("Recent revisions", exact=True).click()
    history = page.locator("details").filter(
        has=page.get_by_text("Recent revisions", exact=True)
    )
    expect(history.get_by_text(revised_summary, exact=True)).to_be_visible()
    expect(history.get_by_text(initial_snapshot["executive_summary"], exact=True)).to_be_visible()
    assert page.evaluate("Object.keys(localStorage)") == []
    load_business_plan_data(
        page, plan_api + "/mine",
        base + "/ta/business-plan?organization=" + str(organization_id),
    )
    expect(page.get_by_role("heading", name="எனது வணிகத் திட்டம்", level=1)).to_be_visible()
    expect(page.get_by_role("textbox", name="செயல் சுருக்கம்", exact=True)).to_have_value(
        revised_summary, timeout=15000
    )
    expect(page.get_by_text("ஒப்புதல் அளிக்கப்பட்டது", exact=True)).to_be_visible()
    assert page.locator("html").get_attribute("lang") == "ta"
    page.set_viewport_size({"width": 390, "height": 844})
    assert_business_plan_field_layout(page.locator("textarea"), 20)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.evaluate("window.scrollTo({top: 0, left: 0, behavior: 'instant'})")
    page.screenshot(path=str(evidence / "business-plan-ta-mobile.png"), full_page=True)
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
            select(MentorAssignment).where(
                MentorAssignment.organization_id == organization_id
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
        assert {item.visibility for item in mentoring_notes} == {
            "mentor_private",
            "shared_with_participant",
        }
        assert mentoring_goal and mentoring_goal.state == "active"
        assert mentoring_action and mentoring_action.state == "open"
        assert mentoring_follow_up and mentoring_follow_up.state == "scheduled"
        assert mentoring_feedback and mentoring_feedback.rating == 5
        business_plan = db.get(BusinessPlan, plan_id)
        submissions = list(db.scalars(
            select(BusinessPlanSubmission)
            .where(BusinessPlanSubmission.plan_id == plan_id)
            .order_by(BusinessPlanSubmission.number)
        ))
        revisions = list(db.scalars(
            select(BusinessPlanRevision).where(BusinessPlanRevision.plan_id == plan_id)
        ))
        reviews = list(db.scalars(
            select(BusinessPlanReview).where(
                BusinessPlanReview.submission_id.in_([item.id for item in submissions])
            )
        ))
        plan_audits = list(db.scalars(
            select(AuditLog).where(AuditLog.resource_id == plan_id)
        ))
        assert business_plan and business_plan.status == "approved"
        assert business_plan.enrollment_id == enrollment.id
        assert len(submissions) == 2 and len(revisions) == 21 and len(reviews) == 2
        assert submissions[0].snapshot == initial_snapshot
        assert submissions[1].snapshot == {**initial_snapshot, "executive_summary": revised_summary}
        assert {item.reviewer_user_id for item in reviews} == {mentor_user_id}
        assert {item.decision for item in reviews} == {"changes_requested", "approved"}
        assert {item.action for item in plan_audits} == {
            "business_plan.created", "business_plan.section_saved",
            "business_plan.submitted", "business_plan.reviewed",
        }
        assert len(plan_audits) == 26
        for entry in plan_audits:
            # Business-plan audit events retain identifiers/field names, never prose.
            assert not entry.reason
            assert entry.changed_fields
            assert "Synthetic browser planning evidence" not in entry.changed_fields
            assert revised_summary not in entry.changed_fields
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
    "mentor assignment/session/private-shared notes/goals/actions/reminders/feedback, audit, "
    "business-plan 20-section autosave/conflict/privacy/immutable submission/assigned "
    "mentor feedback/revision/resubmission/approval/history and English/Tamil mobile, "
    "responsive layouts and session recovery; "
    "no JS errors"
)
