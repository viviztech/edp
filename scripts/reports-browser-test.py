"""I01 synthetic Chrome acceptance; run only through its isolated owned-server runner."""

import csv
import io
import os
import re
import secrets
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from app.modules.applications.models import Application, ApplicationForm
from app.modules.businesses.models import BusinessProfile
from app.modules.crm.models import Lead, LeadConversion
from app.modules.identity.models import (
    AuditLog,
    Organization,
    Person,
    Role,
    RolePermission,
    User,
    UserRole,
    now,
)
from app.modules.identity.security import hasher
from app.modules.identity.service import seed_roles
from app.modules.programs.models import (
    ApplicationCycle,
    Cohort,
    Enrollment,
    Participant,
    Program,
    TrainingCenter,
)
from app.modules.reports.models import (
    CohortImpactSnapshot,
    ImpactDefinition,
    ImpactDefinitionHistory,
    ImpactRecord,
    ReportExport,
)
from playwright.sync_api import expect, sync_playwright
from sqlalchemy import create_engine, delete, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

engine = create_engine(os.environ["DATABASE_URL"])
assert engine.url.database in {"edp_foundation_e2e", "edp_reports_e2e"}
base = os.environ["WEB_ORIGIN"]
assert base.startswith(("http://127.0.0.1:", "http://localhost:"))
org_id = UUID(os.environ["PUBLIC_ORGANIZATION_ID"])
today = now().date()
start = today - timedelta(days=7)
suffix = uuid4().hex[:12]
actors = {
    key: {
        "email": f"i01-{key}-{suffix}@example.com",
        "password": secrets.token_urlsafe(24),
    }
    for key in (
        "director",
        "manager",
        "viewer",
        "owner",
        "peer",
        "other_cohort",
        "unenrolled",
        "outsider",
    )
}

# Only synthetic pre-existing identity/intake/CRM facts are seeded. Measurement
# definitions, observations, snapshots and exports must use the running application.
with Session(engine) as db:
    seed_roles(db)
    org = Organization(id=org_id, name="Synthetic reporting organization " + suffix)
    other = Organization(name="Unrelated reporting organization " + suffix)
    db.add_all([org, other])
    db.flush()
    other_org_id = other.id
    viewer = Role(name="Synthetic report viewer " + suffix)
    db.add(viewer)
    db.flush()
    db.add_all(
        [
            RolePermission(role_id=viewer.id, permission_code="system.access"),
            RolePermission(role_id=viewer.id, permission_code="report.view"),
        ]
    )
    for key, credentials in actors.items():
        person = Person(display_name="Synthetic I01 " + key)
        db.add(person)
        db.flush()
        user = User(
            person_id=person.id,
            email=credentials["email"],
            password_hash=hasher.hash(credentials["password"]),
            status="active",
        )
        db.add(user)
        db.flush()
        credentials["user_id"] = user.id
        credentials["person_id"] = person.id
        role = (
            viewer
            if key == "viewer"
            else db.scalar(
                select(Role).where(
                    Role.name
                    == (
                        "Program Director"
                        if key in {"director", "outsider"}
                        else "Program Manager"
                        if key == "manager"
                        else "Participant"
                    )
                )
            )
        )
        assert role
        db.add(
            UserRole(
                user_id=user.id,
                role_id=role.id,
                organization_id=other.id if key == "outsider" else org.id,
            )
        )
    program = Program(
        organization_id=org.id,
        code="reports",
        name_en="Synthetic reporting program",
        name_ta="செயற்கை அறிக்கைத் திட்டம்",
        state="active",
    )
    center = TrainingCenter(
        organization_id=org.id,
        code="reports-center",
        name_en="Synthetic reporting center",
        name_ta="செயற்கை மையம்",
        locality="Synthetic locality",
    )
    form = ApplicationForm(
        organization_id=org.id,
        version=1,
        state="published",
        title_en="Synthetic reporting intake",
        title_ta="செயற்கை சேர்க்கை",
        published_at=now(),
        published_by_id=actors["director"]["user_id"],
    )
    db.add_all([program, center, form])
    db.flush()
    cohorts = []
    for index in range(2):
        cohort = Cohort(
            organization_id=org.id,
            program_id=program.id,
            center_id=center.id,
            code=f"reports-{index}",
            name_en=f"Synthetic cohort {index + 1}",
            name_ta=f"செயற்கை குழு {index + 1}",
            starts_on=today,
            ends_on=today + timedelta(days=90),
            state="active",
        )
        db.add(cohort)
        db.flush()
        cohorts.append(cohort.id)
    cycles = []
    for index, cohort_id in enumerate(cohorts):
        cycle = ApplicationCycle(
            organization_id=org.id,
            program_id=program.id,
            cohort_id=cohort_id,
            form_id=form.id,
            code=f"reports-cycle-{index}",
            name_en="Synthetic reporting cycle",
            name_ta="செயற்கை சேர்க்கை",
            opens_at=now() - timedelta(days=30),
            closes_at=now() - timedelta(days=1),
            state="closed",
        )
        db.add(cycle)
        db.flush()
        cycles.append(cycle.id)
    for key in ("owner", "peer", "other_cohort"):
        index = 1 if key == "other_cohort" else 0
        application = Application(
            organization_id=org.id,
            person_id=actors[key]["person_id"],
            form_id=form.id,
            cycle_id=cycles[index],
            state="enrolled",
            version=8,
            application_number=f"I01-{key}-{suffix}",
            submitted_at=now(),
        )
        participant = Participant(
            organization_id=org.id, person_id=actors[key]["person_id"], status="active"
        )
        db.add_all([application, participant])
        db.flush()
        actors[key]["participant_id"] = participant.id
        enrollment = Enrollment(
            organization_id=org.id,
            participant_id=participant.id,
            program_id=program.id,
            cohort_id=cohorts[index],
            application_id=application.id,
            status="active",
        )
        db.add(enrollment)
        db.flush()
        actors[key]["enrollment_id"] = enrollment.id
    # This hostile label must stay inert in both HTML and a spreadsheet export.
    dangerous_source = "=SUM(1,1)"
    for index in range(3):
        lead = Lead(
            organization_id=org.id,
            name="Synthetic confidential lead " + str(index),
            email=f"private-{index}-{suffix}@example.com",
            source=dangerous_source,
            campaign="Synthetic campaign",
            status="converted" if index == 0 else "new",
            version=2 if index == 0 else 1,
            dedupe_hash=uuid4().hex,
        )
        db.add(lead)
        db.flush()
        if index == 0:
            db.add(
                LeadConversion(
                    organization_id=org.id,
                    lead_id=lead.id,
                    person_id=actors["owner"]["person_id"],
                    actor_user_id=actors["director"]["user_id"],
                    source=lead.source,
                    campaign=lead.campaign,
                    lead_version=lead.version,
                    reason="Synthetic attributed conversion",
                )
            )
    program_id = program.id
    db.commit()

reports_root = f"{base}/api/reports/organizations/{org_id}"
impact_root = f"{base}/api/impact/organizations/{org_id}"
evidence = Path(".tool-cache/evidence")
evidence.mkdir(parents=True, exist_ok=True)
errors = []


def sign_in(browser, key):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    page.on("pageerror", lambda error: errors.append(str(error)))
    if os.getenv("REPORTS_BROWSER_DIAGNOSTICS") == "1":
        page.on(
            "requestfailed",
            lambda request: (
                print("Snapshot request failed:", request.failure)
                if request.url.endswith("/snapshots") and request.method == "POST"
                else None
            ),
        )
        page.on(
            "response",
            lambda response: (
                print("Snapshot response:", response.status)
                if response.url.endswith("/snapshots")
                and response.request.method == "POST"
                else None
            ),
        )
    page.goto(base + "/en/account")
    page.get_by_label("Email", exact=True).fill(actors[key]["email"])
    page.get_by_label("Password", exact=True).fill(actors[key]["password"])
    with page.expect_response(
        lambda response: response.url.endswith("/api/session/login")
    ) as result:
        page.locator("form").get_by_role("button", name="Sign in", exact=True).click()
    assert result.value.status == 200
    expect(page.get_by_text("Synthetic I01 " + key, exact=True)).to_be_visible()
    return page


def mutate(page, path, data=None, *, root=reports_root):
    csrf = page.request.get(base + "/api/session/csrf").json()["csrf_token"]
    return page.request.post(
        root + path,
        data={} if data is None else data,
        headers={"Origin": base, "X-CSRF-Token": csrf},
    )


def report(page, **filters):
    response = page.request.get(
        reports_root + "/dashboard",
        params={
            "from_date": start.isoformat(),
            "through_date": today.isoformat(),
            **filters,
        },
    )
    assert response.status == 200, response.text()
    return response.json()


def metric(dashboard, key):
    return next(item for item in dashboard["metrics"] if item["key"] == key)


def definition_ui(page, *, edition=1, title="=Synthetic enterprise measures"):
    form = page.get_by_role("form", name="Create definition edition", exact=True)
    form.get_by_label("English title", exact=True).fill(title)
    form.get_by_label("Tamil title", exact=True).fill("செயற்கை தொழில் அளவீடுகள்")
    form.get_by_label("English definition", exact=True).fill(
        "Synthetic self-reported business-started, active-business and jobs measures. "
        "Jobs are an enrollment observation, not independently verified causal impact."
    )
    form.get_by_label("Tamil definition", exact=True).fill(
        "தொழில் தொடக்கம், செயல்பாடு மற்றும் வேலைவாய்ப்புகளின் செயற்கை சுய அறிக்கை அளவீடுகள்."
    )
    form.get_by_label("Reason for definition change", exact=True).fill(
        "Synthetic local policy review"
    )
    with page.expect_response(
        lambda r: r.url.endswith("/definitions") and r.request.method == "POST"
    ) as result:
        form.get_by_role("button", name="Create definition edition", exact=True).click()
    assert result.value.status == 201, result.value.text()
    item = result.value.json()
    assert item["edition"] == edition and item["state"] == "draft"
    return definition_command_ui(page, item, "publish")


def definition_command_ui(page, definition, action):
    form = page.get_by_role(
        "form", name=f"Measurement definition {definition['edition']}", exact=True
    )
    form.get_by_label("Reason for definition change", exact=True).fill(
        "Synthetic reasoned " + action
    )
    with page.expect_response(
        lambda r: (
            r.url.endswith(f"/{definition['id']}/{action}")
            and r.request.method == "POST"
        )
    ) as result:
        form.get_by_role(
            "button",
            name="Publish definition" if action == "publish" else "Archive definition",
            exact=True,
        ).click()
    assert result.value.status == 200, result.value.text()
    return result.value.json()


def observation_ui(
    page, definition, *, stage, observed_on, jobs, reason, correcting=False
):
    if not correcting:
        cancel = page.get_by_role("button", name="Start a new observation", exact=True)
        if cancel.count():
            cancel.click()
    form = page.get_by_role("form", name="Business impact evidence", exact=True)
    if not correcting:
        form.locator('select[name="enrollment_id"]').select_option(
            str(actors["owner"]["enrollment_id"])
        )
        form.locator('select[name="definition_id"]').select_option(definition["id"])
        form.locator('select[name="stage"]').select_option(stage)
        form.get_by_label("Observed on", exact=True).fill(observed_on.isoformat())
    form.get_by_label("Business has started", exact=True).set_checked(
        stage == "outcome"
    )
    form.get_by_label("Business is active", exact=True).set_checked(stage == "outcome")
    form.get_by_label("Jobs created", exact=True).fill(str(jobs))
    form.get_by_label("Reason for this observation or correction", exact=True).fill(
        reason
    )
    with page.expect_response(
        lambda r: r.url.endswith("/records") and r.request.method == "POST"
    ) as result:
        form.get_by_role("button", name="Record observation", exact=True).click()
    assert result.value.status == 201, result.value.text()
    item = result.value.json()
    expect(page.locator("article").get_by_text(reason, exact=True)).to_be_visible()
    return item


def filters_ui(page, cohort_id=None):
    form = page.get_by_role("form", name="Report filters", exact=True)
    form.get_by_label("From date", exact=True).fill(start.isoformat())
    form.get_by_label("Through date", exact=True).fill(today.isoformat())
    form.locator('select[name="program_id"]').select_option("")
    if cohort_id:
        form.locator('select[name="cohort_id"]').select_option(str(cohort_id))
    with page.expect_response(
        lambda r: "/dashboard?" in r.url and start.isoformat() in r.url
    ) as result:
        form.get_by_role("button", name="Apply report filters", exact=True).click()
    assert result.value.status == 200, result.value.text()
    return result.value.json()


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        channel=os.getenv("PLAYWRIGHT_CHANNEL"), headless=True
    )
    director = sign_in(browser, "director")
    manager = sign_in(browser, "manager")
    owner = sign_in(browser, "owner")
    peer = sign_in(browser, "peer")
    viewer_page = sign_in(browser, "viewer")
    outsider = sign_in(browser, "outsider")
    unenrolled = sign_in(browser, "unenrolled")
    director.goto(f"{base}/en/admin/reports?organization={org_id}")
    expect(
        director.get_by_role("heading", name="Reporting and impact", exact=True)
    ).to_be_visible()
    expect(director.get_by_role("region", name="Marketing", exact=True)).to_be_visible()
    empty = report(director)
    assert metric(empty, "leads")["value"] == 3
    assert metric(empty, "registrations")["value"] == 1
    assert metric(empty, "lead_to_application_percent")["numerator"] == 1
    assert metric(empty, "lead_to_application_percent")["denominator"] == 3
    assert metric(empty, "enrollments")["value"] == 3
    assert metric(empty, "funding_facilitated_amount")["value"] is None
    assert empty["impact_coverage"] == 0 and empty["eligible_impact_enrollments"] == 3
    assert "Synthetic confidential lead" not in str(
        empty
    ) and "@example.com" not in str(empty)
    definition_one = definition_ui(director)
    owner.goto(f"{base}/en/impact?organization={org_id}")
    expect(
        owner.get_by_role("heading", name="Business impact evidence", exact=True)
    ).to_be_visible()
    baseline = observation_ui(
        owner,
        definition_one,
        stage="baseline",
        observed_on=today - timedelta(days=1),
        jobs=0,
        reason="Synthetic owner baseline",
    )
    outcome = observation_ui(
        owner,
        definition_one,
        stage="outcome",
        observed_on=today,
        jobs=2,
        reason="Synthetic owner outcome",
    )
    article = owner.locator("article").filter(
        has=owner.get_by_text(outcome["reason"], exact=True)
    )
    article.get_by_role("button", name="Correct this observation", exact=True).click()
    corrected = observation_ui(
        owner,
        definition_one,
        stage="outcome",
        observed_on=today,
        jobs=3,
        reason="Synthetic corrected owner outcome",
        correcting=True,
    )
    assert corrected["revision"] == 2
    mine = owner.request.get(impact_root + "/mine").json()
    assert len(mine["records"]) == 3
    first_key = {
        "enrollment_id": str(actors["owner"]["enrollment_id"]),
        "definition_id": definition_one["id"],
        "stage": "outcome",
        "observed_on": today.isoformat(),
        "business_started": True,
        "business_active": True,
        "jobs_created": 3,
        "expected_revision": 1,
        "reason": corrected["reason"],
        "request_id": corrected["request_id"],
    }
    assert (
        mutate(owner, "/records", first_key, root=impact_root).json()["id"]
        == corrected["id"]
    )
    assert (
        mutate(
            owner, "/records", {**first_key, "jobs_created": 99}, root=impact_root
        ).status
        == 409
    )
    assert (
        mutate(
            peer,
            "/records",
            {**first_key, "request_id": str(uuid4())},
            root=impact_root,
        ).status
        == 403
    )
    assert (
        mutate(
            manager,
            "/records",
            {**first_key, "request_id": str(uuid4())},
            root=impact_root,
        ).status
        == 403
    )
    assert unenrolled.request.get(impact_root + "/mine").status == 403
    assert (
        owner.request.get(
            reports_root + "/dashboard",
            params={"from_date": start.isoformat(), "through_date": today.isoformat()},
        ).status
        == 403
    )
    assert (
        outsider.request.get(
            reports_root + "/dashboard",
            params={"from_date": start.isoformat(), "through_date": today.isoformat()},
        ).status
        == 403
    )
    assert (
        owner.request.post(
            impact_root + "/records",
            data=first_key,
            headers={"Origin": "https://unrelated.example"},
        ).status
        == 403
    )
    assert director.request.get(reports_root + "/auth").status == 404
    assert director.request.get(reports_root + "/dashboard?owner=someone").status == 400
    scoped = filters_ui(director, cohorts[0])
    assert (
        metric(scoped, "leads")["value"] is None
        and metric(scoped, "enrollments")["value"] == 2
    )
    assert (
        scoped["impact_coverage"] == 50
        and scoped["impact"][0]["matched_jobs_change"] == 3
    )
    assert scoped["impact"][0]["outcome_jobs"] == 3
    expect(
        director.get_by_role("region", name="Impact", exact=True).get_by_text(
            "50%", exact=True
        )
    ).to_be_visible()
    with director.expect_response(
        lambda r: r.url.endswith("/snapshots") and r.request.method == "POST"
    ) as result:
        director.get_by_role(
            "button", name="Create snapshot of applied filters", exact=True
        ).click()
    assert result.value.status == 201, result.value.text()
    frozen = result.value.json()
    replay_snapshot = {
        **frozen["dashboard"]["filters"],
        "request_id": frozen["request_id"],
    }
    assert mutate(director, "/snapshots", replay_snapshot).json()["id"] == frozen["id"]
    assert frozen["dashboard"]["impact"][0]["outcome_jobs"] == 3
    definition_one = definition_command_ui(director, definition_one, "archive")
    owner.reload()
    article = owner.locator("article").filter(
        has=owner.get_by_text(corrected["reason"], exact=True)
    )
    article.get_by_role("button", name="Correct this observation", exact=True).click()
    last = observation_ui(
        owner,
        definition_one,
        stage="outcome",
        observed_on=today,
        jobs=5,
        reason="Synthetic correction after definition archive",
        correcting=True,
    )
    assert last["revision"] == 3
    live = report(director, cohort_id=str(cohorts[0]))
    assert live["impact"][0]["outcome_jobs"] == 5
    assert (
        director.request.get(reports_root + f"/snapshots/{frozen['id']}").json()[
            "dashboard"
        ]
        == frozen["dashboard"]
    )
    # Freeze the changed source and compare editions through the real controls.
    with director.expect_response(
        lambda r: r.url.endswith("/snapshots") and r.request.method == "POST"
    ) as result:
        director.get_by_role(
            "button", name="Create snapshot of applied filters", exact=True
        ).click()
    assert result.value.status == 201, result.value.text()
    newer_snapshot = result.value.json()
    assert newer_snapshot["dashboard"]["impact"][0]["outcome_jobs"] == 5
    director.get_by_role(
        "combobox", name=re.compile("^Compare with snapshot")
    ).select_option(frozen["id"])
    comparison = director.get_by_role(
        "heading", name="Snapshot comparison", exact=True
    ).locator("..")
    comparison_row = comparison.get_by_role("row").filter(
        has=director.get_by_role("rowheader", name="Matched outcome jobs", exact=True)
    )
    expect(comparison_row.get_by_role("cell")).to_have_text(["5", "3", "2"])
    director.get_by_role("combobox", name=re.compile("^View snapshot")).select_option(
        frozen["id"]
    )
    expect(comparison_row.get_by_role("cell")).to_have_text(["3", "3", "0"])
    export_form = director.get_by_role("form", name="Aggregate CSV exports", exact=True)
    export_form.get_by_label("Reason for aggregate export", exact=True).fill(
        "Synthetic aggregate evidence review"
    )
    with director.expect_response(
        lambda r: r.url.endswith("/exports") and r.request.method == "POST"
    ) as result:
        export_form.get_by_role(
            "button", name="Create CSV export for selected snapshot", exact=True
        ).click()
    assert result.value.status == 201, result.value.text()
    job = result.value.json()
    assert "csv_content" not in job and "token" not in job
    replay_export = {
        "snapshot_id": frozen["id"],
        "request_id": job["request_id"],
        "reason": "Synthetic aggregate evidence review",
    }
    assert mutate(director, "/exports", replay_export).json()["id"] == job["id"]
    with director.expect_download() as download:
        director.get_by_role("button", name="Download CSV", exact=True).click()
    csv_path = evidence / f"reports-aggregate-{suffix}.csv"
    download.value.save_as(csv_path)
    content = csv_path.read_text(encoding="utf-8")
    rows = list(csv.reader(io.StringIO(content)))
    assert len(rows) == job["row_count"] <= 500 and len(content.encode()) <= 262144
    assert any("'=Synthetic enterprise measures" in row for row in rows)
    assert "@example.com" not in content and "Synthetic owner baseline" not in content
    access = mutate(director, f"/exports/{job['id']}/access").json()
    download_url = reports_root + f"/exports/{job['id']}/download/{access['token']}"
    response = director.request.get(download_url)
    assert (
        response.status == 200 and response.headers["referrer-policy"] == "no-referrer"
    )
    assert (
        "attachment" in response.headers["content-disposition"]
        and "no-store" in response.headers["cache-control"]
    )
    assert manager.request.get(download_url).status == 403
    assert outsider.request.get(download_url).status == 403
    assert (
        director.request.get(
            download_url[:-1] + ("A" if download_url[-1] != "A" else "B")
        ).status
        == 404
    )
    manager.goto(f"{base}/en/admin/reports?organization={org_id}")
    expect(
        manager.get_by_text(
            "Your role can view reports but cannot export them.", exact=True
        )
    ).to_be_visible()
    assert (
        manager.get_by_role(
            "button", name="Create CSV export for selected snapshot", exact=True
        ).count()
        == 0
    )
    assert (
        mutate(
            manager, "/exports", {**replay_export, "request_id": str(uuid4())}
        ).status
        == 403
    )
    viewer_page.goto(f"{base}/en/admin/reports?organization={org_id}")
    expect(
        viewer_page.get_by_role("region", name="Marketing", exact=True)
    ).to_be_visible()
    assert (
        viewer_page.get_by_role(
            "form", name="Create definition edition", exact=True
        ).count()
        == 0
    )
    assert (
        mutate(
            viewer_page,
            "/definitions",
            {
                "title_en": "Denied definition",
                "title_ta": "அனுமதியற்ற அளவீடு",
                "definition_en": "Synthetic denied policy",
                "definition_ta": "செயற்கை கொள்கை",
                "reason": "Denied authoring attempt",
            },
            root=impact_root,
        ).status
        == 403
    )
    director.set_viewport_size({"width": 390, "height": 844})
    director.goto(f"{base}/ta/admin/reports?organization={org_id}")
    expect(
        director.get_by_role("heading", name="அறிக்கைகள் மற்றும் தாக்கம்", exact=True)
    ).to_be_visible()
    expect(director.get_by_role("region", name="தாக்கம்", exact=True)).to_be_visible()
    assert director.evaluate(
        "document.documentElement.scrollWidth <= window.innerWidth"
    )
    assert director.evaluate("""() => [...document.querySelectorAll('.impact-table tbody tr')]
      .every(row => {
        const cell = row.querySelector('td');
        if (!cell || !/^[0-9,.% -]+$/.test(cell.textContent.trim())) return true;
        const range = document.createRange(); range.selectNodeContents(cell);
        return new Set([...range.getClientRects()].map(rect => Math.round(rect.top))).size <= 1;
      })"""), "Mobile metric values must remain on one line"
    director.screenshot(path=str(evidence / "reports-ta-mobile.png"), full_page=True)
    director.locator("form").first.screenshot(
        path=str(evidence / "reports-ta-mobile-qa-filters.png")
    )
    director.locator(".impact-table tbody tr").first.screenshot(
        path=str(evidence / "reports-ta-mobile-qa-metrics.png")
    )
    owner.set_viewport_size({"width": 390, "height": 844})
    owner.goto(f"{base}/ta/impact?organization={org_id}")
    expect(
        owner.get_by_role("heading", name="வணிகத் தாக்கச் சான்றுகள்", exact=True)
    ).to_be_visible()
    expect(owner.get_by_text(last["reason"], exact=True)).to_be_visible()
    assert owner.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    owner.screenshot(path=str(evidence / "impact-owner-ta-mobile.png"), full_page=True)
    owner.locator("form").first.screenshot(
        path=str(evidence / "impact-owner-ta-mobile-qa-controls.png")
    )
    # Revoking the role must invalidate even a previously issued download capability.
    with Session(engine) as db:
        db.execute(
            delete(UserRole).where(
                UserRole.user_id == actors["director"]["user_id"],
                UserRole.organization_id == org_id,
            )
        )
        db.commit()
    assert director.request.get(download_url).status == 403
    with Session(engine) as db:
        assert (
            db.scalar(
                select(BusinessProfile.id).where(
                    BusinessProfile.organization_id == org_id
                )
            )
            is None
        ), "Impact evidence must work without a B02 business profile"
        assert db.scalar(
            select(ImpactRecord.id)
            .where(ImpactRecord.enrollment_id == actors["owner"]["enrollment_id"])
            .limit(1)
        )
        assert db.scalar(
            select(AuditLog.id).where(
                AuditLog.organization_id == org_id,
                AuditLog.action == "report.export.download",
            )
        )
        for model, fields in (
            (ImpactDefinition, {"title_en": "Tampered definition"}),
            (ImpactDefinitionHistory, {"reason": "Tampered reason"}),
            (ImpactRecord, {"jobs_created": 999}),
            (CohortImpactSnapshot, {"dictionary_version": "tampered"}),
            (ReportExport, {"reason": "Tampered export"}),
        ):
            row = db.scalar(
                select(model).where(model.organization_id == org_id).limit(1)
            )
            assert row
            with pytest.raises(DBAPIError):
                db.execute(update(model).where(model.id == row.id).values(**fields))
            db.rollback()
            with pytest.raises(DBAPIError):
                db.execute(delete(model).where(model.id == row.id))
            db.rollback()
        assert (
            len(
                list(
                    db.scalars(
                        select(ImpactRecord).where(
                            ImpactRecord.organization_id == org_id
                        )
                    )
                )
            )
            == 4
        )
    assert not errors, errors
    browser.close()
print(
    "Phase 10 Chrome acceptance passed: defined metrics, scoped dashboards, baseline/outcome corrections, immutable snapshots, authorized formula-safe CSV, privacy and responsive Tamil screens; no JavaScript errors."
)
