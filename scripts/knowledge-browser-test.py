"""K01 synthetic browser acceptance; only run through its isolated local runner."""

import os
import secrets
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

from app.modules.applications.models import Application, ApplicationForm
from app.modules.identity.models import (
    AuditLog,
    Organization,
    Person,
    Role,
    User,
    UserRole,
    now,
)
from app.modules.identity.security import hasher
from app.modules.identity.service import seed_roles
from app.modules.knowledge.models import (
    FundingCase,
    FundingHistory,
    KnowledgeInterest,
    KnowledgeItem,
    KnowledgeRevision,
    KnowledgeSaved,
)
from app.modules.programs.models import (
    ApplicationCycle,
    Cohort,
    Enrollment,
    Participant,
    Program,
    TrainingCenter,
)
from playwright.sync_api import expect, sync_playwright
from sqlalchemy import create_engine, delete, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

engine = create_engine(os.environ["DATABASE_URL"])
assert engine.url.database in {"edp_foundation_e2e", "edp_knowledge_e2e", "edp_test"}
base = os.environ["WEB_ORIGIN"]
api = os.environ["API_INTERNAL_URL"]
assert base.startswith(("http://127.0.0.1:", "http://localhost:"))
assert api.startswith(("http://127.0.0.1:", "http://localhost:"))
org_id = UUID(os.environ["PUBLIC_ORGANIZATION_ID"])
suffix = uuid4().hex[:12]
today = now().date()
actors = {
    key: {"email": f"k01-{key}-{suffix}@example.com", "password": secrets.token_urlsafe(24)}
    for key in ("staff", "owner", "peer", "unenrolled", "outsider")
}

# Seed only identity and a real active enrollment. All knowledge content and
# participant actions below go through the running application, not SQL fixtures.
with Session(engine) as db:
    seed_roles(db)
    org = Organization(id=org_id, name="Synthetic knowledge organization " + suffix)
    other = Organization(name="Synthetic unrelated knowledge organization " + suffix)
    db.add_all([org, other])
    db.flush()
    other_org_id = other.id
    for key, credentials in actors.items():
        person = Person(display_name="Synthetic K01 " + key)
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
        role = db.scalar(
            select(Role).where(
                Role.name
                == ("Funding Coordinator" if key in {"staff", "outsider"} else "Participant")
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
        code="knowledge",
        name_en="Synthetic knowledge program",
        name_ta="செயற்கை அறிவு திட்டம்",
        state="active",
    )
    center = TrainingCenter(
        organization_id=org.id,
        code="knowledge-center",
        name_en="Synthetic knowledge center",
        name_ta="செயற்கை பயிற்சி மையம்",
        locality="Synthetic locality",
    )
    form = ApplicationForm(
        organization_id=org.id,
        version=1,
        state="published",
        title_en="Synthetic knowledge intake",
        title_ta="செயற்கை சேர்க்கை",
        published_at=now(),
        published_by_id=actors["staff"]["user_id"],
    )
    db.add_all([program, center, form])
    db.flush()
    cohort = Cohort(
        organization_id=org.id,
        program_id=program.id,
        center_id=center.id,
        code="knowledge-cohort",
        name_en="Synthetic knowledge cohort",
        name_ta="செயற்கை பயிற்சி குழு",
        starts_on=today,
        ends_on=today + timedelta(days=90),
        state="active",
    )
    db.add(cohort)
    db.flush()
    cycle = ApplicationCycle(
        organization_id=org.id,
        program_id=program.id,
        cohort_id=cohort.id,
        form_id=form.id,
        code="knowledge-cycle",
        name_en="Synthetic knowledge cycle",
        name_ta="செயற்கை சேர்க்கை சுற்று",
        opens_at=now() - timedelta(days=30),
        closes_at=now() - timedelta(days=1),
        state="closed",
    )
    db.add(cycle)
    db.flush()
    for key in ("owner", "peer"):
        application = Application(
            organization_id=org.id,
            person_id=actors[key]["person_id"],
            form_id=form.id,
            cycle_id=cycle.id,
            state="enrolled",
            version=8,
            application_number=f"K01-{key}-{suffix}",
            submitted_at=now() - timedelta(days=20),
        )
        participant = Participant(
            organization_id=org.id, person_id=actors[key]["person_id"], status="active"
        )
        db.add_all([application, participant])
        db.flush()
        actors[key]["participant_id"] = participant.id
        db.add(
            Enrollment(
                organization_id=org.id,
                participant_id=participant.id,
                program_id=program.id,
                cohort_id=cohort.id,
                application_id=application.id,
                status="active",
            )
        )
    db.commit()

knowledge_root = f"{base}/api/knowledge/organizations/{org_id}"
public_root = f"{api}/api/v1/public/organizations/{org_id}/knowledge"
evidence = Path(".tool-cache/evidence")
evidence.mkdir(parents=True, exist_ok=True)
errors = []


def sign_in(browser, key):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(base + "/en/account")
    page.get_by_label("Email", exact=True).fill(actors[key]["email"])
    page.get_by_label("Password", exact=True).fill(actors[key]["password"])
    with page.expect_response(
        lambda response: response.url.endswith("/api/session/login")
    ) as result:
        page.locator("form").get_by_role("button", name="Sign in", exact=True).click()
    assert result.value.status == 200
    expect(page.get_by_text("Synthetic K01 " + key, exact=True)).to_be_visible()
    return page


def mutate(page, path, data=None, method="POST"):
    csrf = page.request.get(base + "/api/session/csrf").json()["csrf_token"]
    return page.request.fetch(
        knowledge_root + path,
        method=method,
        data={} if data is None else data,
        headers={"Origin": base, "X-CSRF-Token": csrf},
    )


def author(
    page,
    *,
    kind,
    slug,
    title,
    locale="en",
    visibility="public",
    publish=True,
    opens=None,
    closes=None,
):
    page.get_by_role("button", name="New resource", exact=True).click()
    form = page.get_by_role("form", name="Resource editor", exact=True)
    expect(form).to_be_visible()
    expect(form.get_by_role("button", name="Create draft", exact=True)).to_be_enabled()
    form.locator('select[name="kind"]').select_option(kind)
    form.locator('select[name="locale"]').select_option(locale)
    for label, value in (
        ("Slug", slug),
        ("Title", title),
        ("Provider", "Synthetic official provider"),
        ("Type", "Synthetic " + kind),
        ("Description", "Synthetic information for browser acceptance. No real offer."),
        ("Eligibility", "Synthetic participants meeting the official example criteria."),
        ("Benefits", "Synthetic benefits for acceptance only."),
        ("Sector", "manufacturing"),
        ("Geography", "Tamil Nadu"),
        ("Application process", "Check the official example source before taking any action."),
        ("Required documents (one per line)", "Synthetic identity reference\nSynthetic proposal"),
        ("Tags (comma separated)", "enterprise, synthetic"),
        ("Official source URL", "https://example.invalid/official/" + slug),
        ("Opens", (opens or today - timedelta(days=2)).isoformat()),
        ("Closes", (closes or today + timedelta(days=30)).isoformat()),
        ("Last verified", today.isoformat()),
        ("Contact or reference", "Synthetic provider reference"),
    ):
        form.get_by_label(label, exact=True).fill(value)
    form.locator('select[name="visibility"]').select_option(visibility)
    if kind == "funding":
        form.get_by_label("Official minimum", exact=True).fill("10000")
        form.get_by_label("Official maximum", exact=True).fill("50000")
    with page.expect_response(
        lambda response: (
            response.url == knowledge_root + "/items" and response.request.method == "POST"
        )
    ) as created:
        form.get_by_role("button", name="Create draft", exact=True).click()
    assert created.value.status == 201
    item = created.value.json()
    expect(page.get_by_role("status")).to_have_text("Saved.")
    if publish:
        form = page.get_by_role("form", name="Resource editor", exact=True)
        form.get_by_role("textbox", name="Reason for change", exact=True).fill(
            "Synthetic source verification complete"
        )
        with page.expect_response(
            lambda response: response.url.endswith(f"/items/{item['id']}/publish")
        ) as published:
            page.get_by_role("button", name="Publish resource", exact=True).click()
        assert published.value.status == 200
        item = published.value.json()
        expect(page.get_by_role("status")).to_have_text("Saved.")
    return item


def progress(page, title, labels):
    tracker = page.get_by_role("region", name="My funding tracker", exact=True)
    case = tracker.get_by_role("article", name=title, exact=True)
    result = None
    for status, label in labels:
        expect(case).to_be_visible()
        expect(case.locator('select[name="status"]')).to_be_enabled()
        case.locator('select[name="status"]').select_option(status)
        reason = "Synthetic participant evidence for " + label
        case.get_by_role("textbox", name="Reason for change", exact=True).fill(reason)
        with page.expect_response(
            lambda response: (
                "/funding-cases/" in response.url
                and response.url.endswith("/status")
                and response.request.method == "POST"
            )
        ) as changed:
            case.get_by_role("button", name="Record progress", exact=True).click()
        assert changed.value.status == 200
        result = changed.value.json()
        assert result["status"] == status
        expect(page.get_by_role("status")).to_have_text("Saved.")
        expect(case.get_by_text(label, exact=True).first).to_be_visible()
    return result


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel=os.getenv("PLAYWRIGHT_CHANNEL"), headless=True)
    staff = sign_in(browser, "staff")
    staff.goto(base + f"/en/admin/knowledge?organization={org_id}")
    expect(
        staff.get_by_role("heading", name="Resource publishing and funding", exact=True)
    ).to_be_visible()
    expect(staff.get_by_role("button", name="New resource", exact=True)).to_be_enabled()
    scheme = author(
        staff, kind="scheme", slug="synthetic-scheme", title="Synthetic enterprise scheme"
    )
    funding = author(
        staff, kind="funding", slug="synthetic-funding", title="Synthetic funding program"
    )
    opportunity = author(
        staff, kind="opportunity", slug="synthetic-opportunity", title="Synthetic trade opportunity"
    )
    tamil = author(
        staff, kind="opportunity", slug="synthetic-tamil", title="செயற்கை தொழில் வாய்ப்பு", locale="ta"
    )
    draft = author(
        staff,
        kind="scheme",
        slug="synthetic-draft",
        title="Confidential synthetic draft",
        publish=False,
    )
    private = author(
        staff,
        kind="scheme",
        slug="synthetic-private",
        title="Participant-only synthetic scheme",
        visibility="participants",
    )
    closed = author(
        staff,
        kind="opportunity",
        slug="synthetic-closed",
        title="Closed synthetic opportunity",
        closes=today - timedelta(days=1),
    )
    upcoming = author(
        staff,
        kind="scheme",
        slug="synthetic-upcoming",
        title="Upcoming synthetic scheme",
        opens=today + timedelta(days=10),
    )
    staff.screenshot(path=str(evidence / "knowledge-staff-en.png"), full_page=True)

    anonymous_context = browser.new_context(viewport={"width": 1280, "height": 900})
    anonymous = anonymous_context.new_page()
    anonymous.on("pageerror", lambda error: errors.append(str(error)))
    anonymous.goto(base + "/en/resources")
    for resource in (scheme, funding, opportunity, upcoming):
        expect(anonymous.get_by_role("article", name=resource["title"], exact=True)).to_be_visible()
    for resource in (draft, private, closed, tamil):
        expect(anonymous.get_by_role("article", name=resource["title"], exact=True)).to_have_count(
            0
        )
    card = anonymous.get_by_role("article", name=scheme["title"], exact=True)
    expect(card.get_by_role("link", name="Official source", exact=True)).to_have_attribute(
        "href", scheme["official_url"]
    )
    expect(card.locator("time")).to_have_attribute("datetime", today.isoformat())
    expect(card.get_by_text("Open", exact=True)).to_be_visible()
    expect(
        anonymous.get_by_role("article", name=upcoming["title"], exact=True).get_by_text(
            "Upcoming", exact=True
        )
    ).to_be_visible()
    assert anonymous.request.get(public_root + "/" + private["id"]).status == 404
    assert anonymous.request.get(public_root + "/" + draft["id"]).status == 404
    assert anonymous.request.get(knowledge_root + "/mine").status == 401
    public_data = anonymous.request.get(public_root).json()
    assert all(
        "participant_id" not in item and "history" not in item for item in public_data["items"]
    )
    filters = anonymous.get_by_role("form", name="Resource filters", exact=True)
    expect(filters).to_be_visible()
    filters.locator('select[name="kind"]').select_option("funding")
    filters.get_by_label("Search resources", exact=True).fill("Synthetic funding")
    filters.get_by_label("Sector", exact=True).fill("manufacturing")
    filters.get_by_label("Geography", exact=True).fill("Tamil Nadu")
    filters.get_by_label("Tag", exact=True).fill("enterprise")
    filters.get_by_role("button", name="Apply filters", exact=True).click()
    expect(anonymous.get_by_role("article")).to_have_count(1)
    expect(anonymous.get_by_role("article", name=funding["title"], exact=True)).to_be_visible()
    anonymous.goto(base + "/en/resources?availability=closed")
    expect(
        anonymous.get_by_role("article", name=closed["title"], exact=True).get_by_text(
            "Closed", exact=True
        )
    ).to_be_visible()
    expect(anonymous.get_by_role("article", name=opportunity["title"], exact=True)).to_have_count(0)
    anonymous.goto(base + "/ta/resources")
    expect(anonymous.get_by_role("article", name=tamil["title"], exact=True)).to_be_visible()
    expect(anonymous.get_by_role("article", name=opportunity["title"], exact=True)).to_have_count(0)
    anonymous.set_viewport_size({"width": 390, "height": 844})
    assert anonymous.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
    anonymous.screenshot(path=str(evidence / "knowledge-public-ta-mobile.png"), full_page=True)

    owner = sign_in(browser, "owner")
    owner.goto(base + f"/en/knowledge?organization={org_id}")
    catalog = owner.get_by_role("region", name="Schemes, funding and opportunities", exact=True)
    expect(catalog.get_by_role("article", name=private["title"], exact=True)).to_be_visible()
    expect(catalog.get_by_role("article", name=draft["title"], exact=True)).to_have_count(0)
    scheme_card = catalog.get_by_role("article", name=scheme["title"], exact=True)
    scheme_card.get_by_role("button", name="Save resource", exact=True).click()
    expect(
        scheme_card.get_by_role("button", name="Remove saved resource", exact=True)
    ).to_be_enabled()
    scheme_card.get_by_role("button", name="Remove saved resource", exact=True).click()
    expect(scheme_card.get_by_role("button", name="Save resource", exact=True)).to_be_enabled()
    scheme_card.get_by_role("button", name="Save resource", exact=True).click()
    expect(
        scheme_card.get_by_role("button", name="Remove saved resource", exact=True)
    ).to_be_enabled()
    repeat_save = mutate(owner, "/saved/" + scheme["id"])
    assert repeat_save.status == 200
    opportunity_card = catalog.get_by_role("article", name=opportunity["title"], exact=True)
    opportunity_card.get_by_role("button", name="Express interest", exact=True).click()
    expect(
        opportunity_card.get_by_role("button", name="Interest recorded", exact=True)
    ).to_be_disabled()
    interest = mutate(owner, "/interests/" + opportunity["id"])
    assert interest.status == 201
    assert mutate(owner, "/interests/" + closed["id"]).status == 409
    funding_card = catalog.get_by_role("article", name=funding["title"], exact=True)
    funding_card.get_by_role("button", name="Save resource", exact=True).click()
    expect(
        funding_card.get_by_role("button", name="Remove saved resource", exact=True)
    ).to_be_enabled()
    with owner.expect_response(
        lambda response: (
            response.url == knowledge_root + "/funding-cases" and response.request.method == "POST"
        )
    ) as started:
        funding_card.get_by_role("button", name="Start funding tracker", exact=True).click()
    assert started.value.status == 201
    owner_case = started.value.json()
    repeat_case = mutate(owner, "/funding-cases", {"item_id": funding["id"]})
    assert repeat_case.status == 201 and repeat_case.json()["id"] == owner_case["id"]
    assert (
        mutate(
            owner,
            "/funding-cases/" + owner_case["id"] + "/status",
            {"expected_version": 1, "status": "approved", "reason": "Invalid skipped status"},
        ).status
        == 409
    )
    owner_case = progress(
        owner,
        funding["title"],
        [
            ("eligibility_check", "Eligibility check"),
            ("document_preparation", "Document preparation"),
            ("applied", "Applied"),
            ("under_review", "Under review"),
            ("approved", "Approved"),
        ],
    )
    assert owner_case["version"] == 6
    assert (
        mutate(
            owner,
            "/funding-cases/" + owner_case["id"] + "/status",
            {
                "expected_version": 1,
                "status": "eligibility_check",
                "reason": "Stale participant version",
            },
        ).status
        == 409
    )

    peer = sign_in(browser, "peer")
    peer.goto(base + f"/en/knowledge?organization={org_id}")
    peer_catalog = peer.get_by_role("region", name="Schemes, funding and opportunities", exact=True)
    expect(peer.get_by_text("No funding cases yet.", exact=True)).to_be_visible()
    assert (
        mutate(
            peer,
            "/funding-cases/" + owner_case["id"] + "/status",
            {"expected_version": 6, "status": "disbursed", "reason": "Wrong participant attempt"},
        ).status
        == 404
    )
    with peer.expect_response(
        lambda response: (
            response.url == knowledge_root + "/funding-cases" and response.request.method == "POST"
        )
    ) as peer_started:
        peer_catalog.get_by_role("article", name=funding["title"], exact=True).get_by_role(
            "button", name="Start funding tracker", exact=True
        ).click()
    assert peer_started.value.status == 201
    peer_case = progress(
        peer,
        funding["title"],
        [
            ("eligibility_check", "Eligibility check"),
            ("document_preparation", "Document preparation"),
            ("applied", "Applied"),
            ("under_review", "Under review"),
            ("rejected", "Rejected"),
        ],
    )
    assert peer_case["version"] == 6
    assert (
        mutate(
            peer,
            "/funding-cases/" + peer_case["id"] + "/status",
            {"expected_version": 6, "status": "applied", "reason": "Terminal case cannot reopen"},
        ).status
        == 409
    )
    assert peer.request.get(knowledge_root + "/items").status == 403
    assert peer.request.get(knowledge_root + "/funding-cases").status == 403
    assert (
        peer.request.get(f"{base}/api/knowledge/organizations/{other_org_id}/catalog").status == 403
    )

    # Keep the original evidence while staff withdraw, edit and expire the live entry.
    staff.get_by_role("article", name=funding["title"], exact=True).get_by_role(
        "button", name="Edit resource", exact=True
    ).click()
    editor = staff.get_by_role("form", name="Resource editor", exact=True)
    editor.get_by_role("textbox", name="Reason for change", exact=True).fill(
        "Synthetic provider correction"
    )
    with staff.expect_response(
        lambda response: response.url.endswith(f"/items/{funding['id']}/draft")
    ) as withdrawn:
        staff.get_by_role("button", name="Return to draft", exact=True).click()
    assert withdrawn.value.status == 200
    withdrawn_mine = owner.request.get(knowledge_root + "/mine").json()
    assert (
        next(saved for saved in withdrawn_mine["saved_items"] if saved["item_id"] == funding["id"])[
            "item"
        ]
        is None
    )
    assert withdrawn_mine["funding_cases"][0]["source"] == owner_case["source"]
    assert owner.request.get(knowledge_root + "/catalog/" + funding["id"]).status == 404
    assert anonymous.request.get(public_root + "/" + funding["id"]).status == 404
    owner.reload()
    expect(
        owner.get_by_text("This saved resource is no longer available.", exact=True)
    ).to_be_visible()
    expect(
        owner.get_by_role("region", name="My funding tracker", exact=True).get_by_role(
            "heading", name=funding["title"], level=3, exact=True
        )
    ).to_be_visible()
    editor.get_by_label("Title", exact=True).fill("Expired revised synthetic funding")
    editor.get_by_role("textbox", name="Description", exact=True).fill(
        "Updated source text must not replace the original case snapshot."
    )
    editor.get_by_label("Closes", exact=True).fill((today - timedelta(days=1)).isoformat())
    editor.get_by_role("textbox", name="Reason for change", exact=True).fill(
        "Synthetic official closure confirmed"
    )
    with staff.expect_response(
        lambda response: (
            response.url.endswith(f"/items/{funding['id']}") and response.request.method == "PATCH"
        )
    ) as edited:
        editor.get_by_role("button", name="Save draft", exact=True).click()
    assert edited.value.status == 200
    editor.get_by_role("textbox", name="Reason for change", exact=True).fill(
        "Publish corrected closed reference"
    )
    with staff.expect_response(
        lambda response: response.url.endswith(f"/items/{funding['id']}/publish")
    ) as republished:
        staff.get_by_role("button", name="Publish resource", exact=True).click()
    assert republished.value.status == 200
    assert republished.value.json()["availability"] == "closed"
    owner.reload()
    expect(
        owner.get_by_role("region", name="My funding tracker", exact=True).get_by_role(
            "heading", name=funding["title"], level=3, exact=True
        )
    ).to_be_visible()
    owner_case = progress(owner, funding["title"], [("disbursed", "Disbursed")])
    assert owner_case["version"] == 7 and owner_case["source"]["title"] == funding["title"]
    tracker = owner.get_by_role("region", name="My funding tracker", exact=True)
    tracker.get_by_text("Progress history", exact=True).click()
    expect(tracker.locator("ol > li")).to_have_count(7)
    tracker.get_by_text("Source recorded when tracking began", exact=True).click()
    expect(tracker.get_by_role("link", name="Official source", exact=True)).to_have_attribute(
        "href", funding["official_url"]
    )
    owner.set_viewport_size({"width": 390, "height": 844})
    assert owner.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
    owner.screenshot(path=str(evidence / "knowledge-funding-mobile.png"), full_page=True)
    assert owner.evaluate("Object.keys(localStorage)") == []
    assert (
        mutate(
            owner,
            "/funding-cases/" + owner_case["id"] + "/status",
            {
                "expected_version": 7,
                "status": "approved",
                "reason": "Terminal case cannot move back",
            },
        ).status
        == 409
    )

    unenrolled = sign_in(browser, "unenrolled")
    assert unenrolled.request.get(knowledge_root + "/catalog").status == 403
    assert mutate(unenrolled, "/saved/" + scheme["id"]).status == 403
    outsider = sign_in(browser, "outsider")
    assert outsider.request.get(knowledge_root + "/items").status == 403
    assert outsider.request.get(knowledge_root + "/funding-cases").status == 403
    assert (
        mutate(
            outsider,
            "/items/" + scheme["id"] + "/archive",
            {"expected_version": scheme["version"], "reason": "Wrong organization attempt"},
        ).status
        == 403
    )
    assert (
        mutate(
            staff,
            "/funding-cases/" + owner_case["id"] + "/status",
            {
                "expected_version": 7,
                "status": "approved",
                "reason": "Staff cannot impersonate the owner",
            },
        ).status
        == 403
    )
    csrf = owner.request.get(base + "/api/session/csrf").json()["csrf_token"]
    assert (
        owner.request.post(
            knowledge_root + "/saved/" + scheme["id"],
            data={},
            headers={"Origin": "https://evil.example", "X-CSRF-Token": csrf},
        ).status
        == 403
    )
    assert (
        owner.request.post(
            knowledge_root + "/saved/" + scheme["id"], data={}, headers={"Origin": base}
        ).status
        == 403
    )
    assert owner.request.get(knowledge_root + "/not-an-allowed-operation").status == 404
    assert owner.request.get(knowledge_root + "/catalog?limit=1000").status == 400
    assert owner.request.get(knowledge_root + "/catalog?locale=en&locale=ta").status == 400
    assert (
        owner.request.get(knowledge_root + "/catalog?organization=" + str(other_org_id)).status
        == 400
    )
    staff.reload()
    queue = staff.get_by_role("region", name="Participant funding cases", exact=True)
    expect(queue.get_by_text("Disbursed", exact=False).first).to_be_visible()
    expect(queue.get_by_text("Rejected", exact=False).first).to_be_visible()
    staff.goto(base + f"/ta/admin/knowledge?organization={org_id}")
    staff_catalog = staff.get_by_role("region", name="திட்டங்கள், நிதி மற்றும் வாய்ப்புகள்", exact=True)
    expect(staff_catalog.get_by_role("article", name=tamil["title"], exact=True)).to_be_visible()
    expect(staff_catalog.get_by_role("article", name=scheme["title"], exact=True)).to_have_count(0)
    staff.screenshot(path=str(evidence / "knowledge-staff-ta.png"), full_page=True)

    with Session(engine) as db:
        resources = list(
            db.scalars(select(KnowledgeItem).where(KnowledgeItem.organization_id == org_id))
        )
        assert len(resources) == 8
        assert {item.kind for item in resources} == {"scheme", "funding", "opportunity"}
        assert {item.locale for item in resources} == {"en", "ta"}
        saved = list(
            db.scalars(select(KnowledgeSaved).where(KnowledgeSaved.organization_id == org_id))
        )
        assert len(saved) == 2 and all(
            row.participant_id == actors["owner"]["participant_id"] for row in saved
        )
        interests = list(
            db.scalars(select(KnowledgeInterest).where(KnowledgeInterest.organization_id == org_id))
        )
        assert len(interests) == 1 and str(interests[0].id) == interest.json()["id"]
        cases = list(db.scalars(select(FundingCase).where(FundingCase.organization_id == org_id)))
        assert len(cases) == 2
        owner_row = next(row for row in cases if str(row.id) == owner_case["id"])
        assert owner_row.status == "disbursed" and owner_row.version == 7
        assert owner_row.source == owner_case["source"]
        histories = list(
            db.scalars(
                select(FundingHistory)
                .where(FundingHistory.case_id == owner_row.id)
                .order_by(FundingHistory.version)
            )
        )
        assert [row.status for row in histories] == [
            "interested",
            "eligibility_check",
            "document_preparation",
            "applied",
            "under_review",
            "approved",
            "disbursed",
        ]
        assert all(row.actor_user_id == actors["owner"]["user_id"] for row in histories)
        revisions = list(
            db.scalars(
                select(KnowledgeRevision)
                .where(KnowledgeRevision.item_id == UUID(funding["id"]))
                .order_by(KnowledgeRevision.version)
            )
        )
        assert [row.action for row in revisions] == [
            "created",
            "published",
            "draft",
            "updated",
            "published",
        ]
        assert revisions[1].snapshot["title"] == funding["title"]
        logs = list(db.scalars(select(AuditLog).where(AuditLog.organization_id == org_id)))
        assert any(row.action == "funding.status_changed" for row in logs)
        assert all(not row.reason for row in logs)
        assert all("Synthetic" not in (row.changed_fields or "") for row in logs)
        for model, row in (
            (KnowledgeRevision, revisions[0]),
            (FundingHistory, histories[0]),
            (KnowledgeInterest, interests[0]),
        ):
            for operation in (
                update(model).where(model.id == row.id).values(created_at=now()),
                delete(model).where(model.id == row.id),
            ):
                try:
                    db.execute(operation)
                except DBAPIError:
                    db.rollback()
                else:
                    db.rollback()
                    raise AssertionError("Expected append-only evidence to reject mutation")
        try:
            db.execute(update(FundingCase).where(FundingCase.id == owner_row.id).values(source={}))
        except DBAPIError:
            db.rollback()
        else:
            db.rollback()
            raise AssertionError("Expected the original funding source to remain immutable")
    assert not errors, "Unexpected browser JavaScript errors: " + "; ".join(errors)
    browser.close()

print(
    "K01 Chrome acceptance passed: staff publication, bilingual discovery, ownership, preferences, "
    "funding approval/disbursement and rejection, immutable evidence, responsive layouts."
)
