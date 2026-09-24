"""Synthetic browser E2E; run with isolated PostgreSQL and local servers only."""

import json
import os
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from app.modules.applications.models import Application, ApplicationForm
from app.modules.identity.models import (
    AuthDelivery,
    Organization,
    Role,
    User,
    UserRole,
    VerificationToken,
)
from app.modules.identity.service import audit, seed_roles
from app.modules.programs import service as program_service
from app.modules.programs.models import (
    DomainOutbox,
    Enrollment,
    Participant,
    ProgramSession,
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
    expect(public.get_by_role("heading", name="Who can apply")).to_be_visible()
    expect(public.locator(".cms-body")).to_contain_text("<script>alert(1)</script>")
    page.screenshot(path=str(evidence / "cms-debug.png"), full_page=True)
    page.get_by_label("Content", exact=True).fill("Unpublished change")
    page.get_by_role("button", name="Save draft", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Saved")
    public.reload()
    expect(public.locator(".cms-body")).not_to_contain_text("Unpublished change")
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
    page.goto(base + "/en/participant?organization=" + str(organization_id))
    expect(page.get_by_role("heading", name="My program schedule")).to_be_visible()
    expect(page.get_by_text("Business foundations", exact=True).first).to_be_visible()
    expect(page.get_by_role("heading", name="Timeline", exact=True)).to_be_visible()

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
        program_session = db.scalar(
            select(ProgramSession).where(
                ProgramSession.organization_id == organization_id
            )
        )
        outbox = db.scalar(
            select(DomainOutbox).where(DomainOutbox.organization_id == organization_id)
        )
        assert application and application.state == "enrolled"
        assert (
            participant and enrollment and enrollment.participant_id == participant.id
        )
        assert program_session and program_session.title_en == "Business foundations"
        assert outbox and outbox.event_type == "enrollment.created"
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
    "publish/versioning, immutable application submission, selection rubric/assignment/conflict/scoring/moderation/interview/decisions/finalization, enrollment/participant/session/timeline, audit, responsive layouts and session recovery; no JS errors"
)
