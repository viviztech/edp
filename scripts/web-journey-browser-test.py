"""Synthetic applicant entry/history acceptance; run through the owned local runner."""

import json
import os
import re
import secrets
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from uuid import UUID, uuid4

from app.modules.applications import service as application_service
from app.modules.applications.models import (
    Application,
    ApplicationAnswer,
    ApplicationRevision,
)
from app.modules.applications.schemas import (
    AcknowledgementInput,
    DefinitionCommand,
    DefinitionCreate,
    DefinitionFieldInput,
)
from app.modules.identity.models import (
    AuthDelivery,
    Organization,
    Person,
    Role,
    User,
    UserRole,
    VerificationToken,
    now,
)
from app.modules.identity.security import hasher
from app.modules.identity.service import seed_roles
from app.modules.programs import service as program_service
from app.modules.programs.schemas import CycleCreate, NamedCreate, StateCommand
from app.modules.selection import service as selection_service
from app.modules.selection.models import SelectionRubric
from app.modules.selection.schemas import (
    AssignmentCreate,
    CriterionInput,
    CycleCommand,
    RubricCommand,
    RubricUpdate,
    SelectionCycleCreate,
)
from cryptography.fernet import Fernet
from playwright.sync_api import expect, sync_playwright
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

engine = create_engine(os.environ["DATABASE_URL"])
assert engine.url.database in {"edp_foundation_e2e", "edp_web_journey_e2e"}
base = os.environ["WEB_ORIGIN"]
api = os.environ["API_INTERNAL_URL"]
assert urlparse(base).hostname in {"127.0.0.1", "localhost"}
assert urlparse(api).hostname in {"127.0.0.1", "localhost"}
assert urlparse(base).scheme == urlparse(api).scheme == "http"
org_id = UUID(os.environ["PUBLIC_ORGANIZATION_ID"])
suffix = uuid4().hex[:12]
actors = {
    key: {
        "email": f"web-journey-{key}-{suffix}@example.com",
        "password": secrets.token_urlsafe(24),
        "name": "Synthetic web journey " + key,
    }
    for key in ("owner", "contextual", "director", "reviewer", "peer")
}

# Only staff and a peer are seeded. Both applicants register and verify through
# the real public account forms. Policy/program/intake setup uses scoped services.
with Session(engine) as db:
    seed_roles(db)
    db.add(Organization(id=org_id, name="Synthetic web journey organization " + suffix))
    db.flush()
    for key, role_name in (
        ("director", "Program Director"),
        ("reviewer", "Selection Committee"),
        ("peer", None),
    ):
        person = Person(display_name=actors[key]["name"])
        db.add(person)
        db.flush()
        user = User(
            person_id=person.id,
            email=actors[key]["email"],
            password_hash=hasher.hash(actors[key]["password"]),
            status="active",
        )
        db.add(user)
        db.flush()
        actors[key]["id"] = user.id
        if role_name:
            role = db.scalar(select(Role).where(Role.name == role_name))
            assert role
            db.add(UserRole(user_id=user.id, role_id=role.id, organization_id=org_id))
    db.commit()
    director = db.get(User, actors["director"]["id"])
    assert director
    form = application_service.create_definition(
        db,
        org_id,
        director,
        DefinitionCreate(
            title_en="Synthetic enterprise application",
            title_ta="செயற்கை தொழில் விண்ணப்பம்",
            fields=[
                DefinitionFieldInput(
                    key="business_idea",
                    section="proposal",
                    label_en="Business idea",
                    label_ta="வணிக யோசனை",
                    field_type="textarea",
                    required=True,
                )
            ],
            acknowledgements=[
                AcknowledgementInput(
                    key="declaration",
                    kind="declaration",
                    label_en="This synthetic application is accurate.",
                    label_ta="இந்த செயற்கை விண்ணப்பம் சரியானது.",
                ),
                AcknowledgementInput(
                    key="consent",
                    kind="consent",
                    label_en="I accept this synthetic application policy.",
                    label_ta="இந்த செயற்கை விண்ணப்பக் கொள்கையை ஏற்கிறேன்.",
                ),
            ],
        ),
        "synthetic-journey-policy",
    )
    form = application_service.publish_definition(
        db,
        org_id,
        form.id,
        director,
        DefinitionCommand(expected_revision=1),
        "synthetic-publish",
    )
    program = program_service.create_program(
        db,
        org_id,
        director,
        NamedCreate(
            code="journey-" + suffix,
            name_en="Synthetic enterprise",
            name_ta="செயற்கை தொழில்",
        ),
        "synthetic-program",
    )
    program = program_service.transition_program(
        db,
        org_id,
        program.id,
        director,
        StateCommand(expected_version=1, target="active", reason="Synthetic browser acceptance"),
        "synthetic-program-open",
    )
    cycles = {}
    for index, key in enumerate(("owner", "contextual"), start=1):
        cycle = program_service.create_cycle(
            db,
            org_id,
            director,
            CycleCreate(
                code="journey-" + key + "-" + suffix,
                name_en="Synthetic " + key + " intake",
                name_ta="செயற்கை சேர்க்கை " + key,
                program_id=program.id,
                cohort_id=None,
                form_id=form.id,
                opens_at=now() - timedelta(days=1),
                closes_at=now() + timedelta(days=index + 1),
            ),
            "synthetic-cycle-create",
        )
        cycles[key] = program_service.transition_cycle(
            db,
            org_id,
            cycle.id,
            director,
            StateCommand(expected_version=1, target="open", reason="Synthetic intake acceptance"),
            "synthetic-cycle-open",
        )

evidence = Path(".tool-cache/evidence")
evidence.mkdir(parents=True, exist_ok=True)
errors = []


def new_page(browser, width=1280):
    context = browser.new_context(viewport={"width": width, "height": 900})
    page = context.new_page()
    page.on("pageerror", lambda error: errors.append(str(error)))
    return page


def intake_query(url):
    return parse_qs(urlparse(url).query)


def latest_verification(key):
    with Session(engine) as db:
        row = db.scalar(
            select(AuthDelivery)
            .join(VerificationToken)
            .join(User)
            .where(
                User.email == actors[key]["email"],
                VerificationToken.purpose == "verify",
            )
            .order_by(AuthDelivery.created_at.desc())
            .limit(1)
        )
        assert row
        return json.loads(
            Fernet(os.environ["AUTH_DELIVERY_KEY"].encode()).decrypt(row.encrypted_payload.encode())
        )["token"]


def register_verify_login(page, key):
    page.wait_for_url(re.compile(re.escape(base) + r"/en/account(?:\?|$)"))
    expect(page.get_by_role("heading", name="Your account", exact=True)).to_be_visible()
    original_url = page.url
    page.get_by_role("button", name="Create account", exact=True).click()
    page.get_by_label("Name", exact=True).fill(actors[key]["name"])
    page.get_by_label("Email", exact=True).fill(actors[key]["email"])
    page.get_by_label("Password", exact=True).fill(actors[key]["password"])
    page.locator("form").get_by_role("button", name="Create account", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("message has been queued")
    assert page.url == original_url
    page.get_by_role("button", name="Verify email", exact=True).click()
    page.get_by_label("Verification or reset code", exact=True).fill(latest_verification(key))
    page.locator("form").get_by_role("button", name="Verify email", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("You can now sign in")
    assert page.url == original_url
    page.get_by_role("button", name="Sign in", exact=True).click()
    page.get_by_label("Email", exact=True).fill(actors[key]["email"])
    page.get_by_label("Password", exact=True).fill(actors[key]["password"])
    with page.expect_response(
        lambda response: response.url.endswith("/api/session/login")
    ) as login:
        page.locator("form").get_by_role("button", name="Sign in", exact=True).click()
    assert login.value.status == 200
    expect(page.get_by_text(actors[key]["name"], exact=True)).to_be_visible()
    assert page.url == original_url
    profile = page.request.get(base + "/api/session/me").json()
    assert profile["grants"] == []
    with Session(engine) as db:
        user = db.scalar(select(User).where(User.email == actors[key]["email"]))
        assert user
        actors[key]["id"] = user.id
        assert (
            db.scalar(select(func.count()).select_from(UserRole).where(UserRole.user_id == user.id))
            == 0
        )
    return page.get_by_role("link", name="Continue application", exact=True)


def submit_intake(page, key):
    expect(page.get_by_role("heading", name="My applications", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name="Open application cycles", exact=True)).to_be_visible()
    selected = page.get_by_role("button", name=re.compile("^" + re.escape(cycles[key].name_en)))
    selected.click()
    expect(selected).to_have_attribute("aria-pressed", "true")
    page.get_by_role("button", name="Start application", exact=True).click()
    field = page.get_by_role("textbox", name="Business idea *", exact=True)
    expect(field).to_be_enabled()
    field.fill("Private synthetic enterprise idea " + key + " " + suffix)
    page.get_by_role("button", name="Save draft", exact=True).click()
    expect(page.locator(".application-message")).to_contain_text("Draft saved.")
    boxes = page.locator(".application-acknowledgements input[type=checkbox]")
    expect(boxes).to_have_count(2)
    for checkbox in boxes.all():
        checkbox.check()
    page.once("dialog", lambda dialog: dialog.accept())
    with page.expect_response(lambda response: response.url.endswith("/submit")) as submitted:
        page.get_by_role("button", name="Submit application", exact=True).click()
    assert submitted.value.status == 200
    receipt = submitted.value.json()
    assert receipt["state"] == "submitted" and receipt["cycle_id"] == str(cycles[key].id)
    expect(page.locator(".application-receipt")).to_contain_text(receipt["application_number"])
    expect(field).to_be_disabled()
    expect(page.get_by_role("button", name="Save draft", exact=True)).to_have_count(0)
    expect(page.get_by_role("button", name="Submit application", exact=True)).to_have_count(0)
    return receipt


def mutate(page, method, path, data, csrf=True):
    headers = {"Origin": base}
    if csrf:
        headers["X-CSRF-Token"] = page.request.get(base + "/api/session/csrf").json()["csrf_token"]
    return page.request.fetch(base + path, method=method, data=data, headers=headers)


def place_under_review(application_id):
    # Exercise the supported selection workflow, including immutable status history.
    with Session(engine) as db:
        director = db.get(User, actors["director"]["id"])
        assert director
        selection_cycle = selection_service.create_cycle(
            db,
            org_id,
            director,
            SelectionCycleCreate(
                application_cycle_id=cycles["owner"].id,
                code="journey-selection-" + suffix,
                name_en="Synthetic application review",
                name_ta="செயற்கை விண்ணப்ப மதிப்பாய்வு",
            ),
            "synthetic-selection-create",
        )
        rubric = db.scalar(
            select(SelectionRubric).where(SelectionRubric.selection_cycle_id == selection_cycle.id)
        )
        assert rubric
        updated = selection_service.update_rubric(
            db,
            org_id,
            rubric.id,
            director,
            RubricUpdate(
                expected_edit_version=1,
                criteria=[
                    CriterionInput(
                        key="viability",
                        label_en="Viability",
                        label_ta="சாத்தியம்",
                        weight=100,
                        maximum_score=10,
                    )
                ],
            ),
            "synthetic-rubric-update",
        )
        selection_service.publish_rubric(
            db,
            org_id,
            rubric.id,
            director,
            RubricCommand(expected_edit_version=updated.edit_version),
            "synthetic-rubric-publish",
        )
        selection_service.transition_cycle(
            db,
            org_id,
            selection_cycle.id,
            director,
            CycleCommand(
                expected_version=1,
                target="active",
                reason="Synthetic review acceptance",
            ),
            "synthetic-selection-open",
        )
        selection_service.create_assignment(
            db,
            org_id,
            director,
            AssignmentCreate(
                selection_cycle_id=selection_cycle.id,
                application_id=UUID(application_id),
                reviewer_user_id=actors["reviewer"]["id"],
            ),
            "synthetic-review-assignment",
        )


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel=os.getenv("PLAYWRIGHT_CHANNEL"), headless=True)
    try:
        owner = new_page(browser)
        owner.goto(base + "/en")
        owner.get_by_role("link", name="Apply", exact=True).click()
        expect(owner.get_by_role("heading", name="How to apply", exact=True)).to_be_visible()
        owner.get_by_role("link", name="Open your account", exact=True).click()
        continuation = register_verify_login(owner, "owner")
        assert intake_query(continuation.get_attribute("href"))["organization"] == [str(org_id)]
        continuation.click()
        owner_receipt = submit_intake(owner, "owner")

        contextual = new_page(browser, 390)
        chosen_path = f"/en/applications?organization={org_id}&cycle={cycles['contextual'].id}"
        contextual.goto(base + chosen_path)
        contextual.wait_for_url("**/en/account?**")
        assert intake_query(contextual.url) == {
            "organization": [str(org_id)],
            "cycle": [str(cycles["contextual"].id)],
        }
        continuation = register_verify_login(contextual, "contextual")
        assert intake_query(continuation.get_attribute("href")) == intake_query(contextual.url)
        continuation.click()
        context_receipt = submit_intake(contextual, "contextual")
        assert context_receipt["id"] != owner_receipt["id"]
        second_draft = mutate(
            owner,
            "POST",
            f"/api/applications/organizations/{org_id}/cycles/{cycles['contextual'].id}/draft",
            {},
        )
        assert second_draft.status == 201

        # Closing intake uses the running, scoped program API with a staff token.
        login = owner.request.post(
            api + "/api/v1/auth/login",
            data={
                "email": actors["director"]["email"],
                "password": actors["director"]["password"],
            },
        )
        assert login.status == 200
        closed = owner.request.post(
            api + f"/api/v1/programs/organizations/{org_id}/cycles/{cycles['owner'].id}/state",
            data={
                "expected_version": 2,
                "target": "closed",
                "reason": "Synthetic intake complete",
            },
            headers={"Authorization": "Bearer " + login.json()["access_token"]},
        )
        assert closed.status == 200

        owner.goto(base + f"/en/applications?organization={org_id}")
        expect(
            owner.get_by_role("heading", name="Saved and submitted applications", exact=True)
        ).to_be_visible()
        expect(owner.get_by_role("link", name="Continue draft", exact=True)).to_be_visible()
        expect(owner.get_by_text(owner_receipt["application_number"], exact=False)).to_be_visible()
        owner.get_by_role("link", name="View application", exact=True).click()
        expect(owner.locator(".application-receipt")).to_contain_text(
            owner_receipt["application_number"]
        )
        owner.reload()
        expect(owner.locator(".application-receipt")).to_contain_text(
            owner_receipt["application_number"]
        )
        place_under_review(owner_receipt["id"])
        owner.reload()
        expect(owner.get_by_role("textbox", name="Business idea *", exact=True)).to_be_disabled()
        expect(owner.get_by_role("button", name="Save draft", exact=True)).to_have_count(0)
        expect(owner.get_by_role("button", name="Submit application", exact=True)).to_have_count(0)
        root = f"/api/applications/organizations/{org_id}"
        detail = owner.request.get(base + root + f"/cycles/{cycles['owner'].id}/application")
        assert detail.status == 200 and detail.json()["state"] == "under_review"
        history = owner.request.get(base + "/api/applications/mine?limit=1")
        assert (
            history.status == 200
            and len(history.json()["items"]) == 1
            and history.json()["items"][0]["id"] == second_draft.json()["id"]
            and history.json()["next_cursor"]
        )
        older_history = owner.request.get(
            base + "/api/applications/mine?limit=1&cursor=" + history.json()["next_cursor"]
        )
        assert older_history.status == 200
        assert older_history.json()["items"][0]["state"] == "under_review"
        assert older_history.json()["items"][0]["id"] == owner_receipt["id"]
        assert older_history.json()["next_cursor"] is None
        for private in (
            "answers",
            "reason_code",
            "scores",
            "notes",
            "Private synthetic enterprise idea",
        ):
            assert private not in history.text() + older_history.text()
        assert (
            mutate(
                owner,
                "PATCH",
                root + "/draft/" + owner_receipt["id"],
                {
                    "expected_version": detail.json()["version"],
                    "answers": [],
                },
            ).status
            == 404
        )
        assert mutate(owner, "POST", root + f"/cycles/{cycles['owner'].id}/draft", {}).status == 404
        assert (
            mutate(owner, "PATCH", root + "/draft/" + owner_receipt["id"], {}, csrf=False).status
            == 403
        )

        for path in (
            "/api/applications/organizations/invalid/cycles",
            root + "/definitions",
            "/api/applications/mine/admin",
        ):
            assert owner.request.get(base + path).status == 404
        for path in (
            "/api/applications/mine?limit=101",
            "/api/applications/mine?limit=1&limit=2",
            "/api/applications/mine?cursor=invalid",
            "/api/applications/mine?person_id=" + str(actors["peer"]["id"]),
            root + "/cycles?limit=1",
        ):
            assert owner.request.get(base + path).status == 400
        assert mutate(owner, "POST", "/api/applications/mine", {}).status == 404

        peer = new_page(browser)
        peer.goto(base + "/en/account")
        peer.get_by_label("Email", exact=True).fill(actors["peer"]["email"])
        peer.get_by_label("Password", exact=True).fill(actors["peer"]["password"])
        peer.locator("form").get_by_role("button", name="Sign in", exact=True).click()
        expect(peer.get_by_text(actors["peer"]["name"], exact=True)).to_be_visible()
        peer.goto(base + f"/en/applications?organization={org_id}&cycle={cycles['owner'].id}")
        expect(peer.locator(".application-workspace")).to_have_attribute("aria-busy", "false")
        peer_history = peer.request.get(base + "/api/applications/mine")
        assert peer_history.status == 200 and peer_history.json() == {
            "items": [],
            "next_cursor": None,
        }
        assert (
            peer.request.get(base + root + f"/cycles/{cycles['owner'].id}/application").status
            == 404
        )
        assert (
            peer.request.get(
                base
                + f"/api/applications/organizations/{uuid4()}"
                + f"/cycles/{cycles['owner'].id}/application"
            ).status
            == 404
        )
        cursor = peer.request.get(base + "/api/applications/mine?cursor=" + owner_receipt["id"])
        assert cursor.status == 422 and cursor.json()["error"]["code"] == "invalid_cursor"
        assert (
            mutate(
                peer,
                "PATCH",
                root + "/draft/" + owner_receipt["id"],
                {
                    "expected_version": 1,
                    "answers": [],
                },
            ).status
            == 404
        )
        expect(peer.get_by_text(owner_receipt["application_number"], exact=False)).to_have_count(0)
        expect(peer.get_by_role("button", name="Start application", exact=True)).to_have_count(0)

        # An unavailable chosen cycle must not silently open another owned record.
        owner.goto(base + f"/en/applications?organization={org_id}&cycle={uuid4()}")
        expect(owner.locator(".application-workspace")).to_have_attribute("aria-busy", "false")
        expect(owner.get_by_role("heading", name="My applications", exact=True)).to_be_visible()
        expect(owner.get_by_role("textbox", name="Business idea *", exact=True)).to_have_count(0)
        expect(owner.get_by_role("button", name="Start application", exact=True)).to_have_count(0)

        for locale in ("en", "ta"):
            owner.goto(
                base + f"/{locale}/applications?organization={org_id}&cycle={cycles['owner'].id}"
            )
            expect(owner.locator(".application-receipt")).to_contain_text(
                owner_receipt["application_number"]
            )
            expect(owner.locator("html")).to_have_attribute("lang", locale)
            expect(owner.locator("#main")).to_have_count(1)
            if locale == "ta":
                assert re.search(r"[\u0b80-\u0bff]", owner.locator("main h1").inner_text())
                expect(
                    owner.get_by_role("textbox", name="வணிக யோசனை *", exact=True)
                ).to_be_disabled()
            for width in (360, 390, 768, 1280):
                owner.set_viewport_size({"width": width, "height": 900})
                assert owner.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                owner.locator("a.skip").focus()
                owner.keyboard.press("Enter")
                assert owner.evaluate("document.activeElement.id") == "main"
                owner.screenshot(
                    path=str(evidence / f"web-journey-{locale}-{width}.png"),
                    full_page=True,
                )
        owner.goto(
            base
            + f"/en/account?organization={org_id}&cycle={cycles['owner'].id}"
            + "&returnTo=https%3A%2F%2Fevil.example%2Fta%2Faccount"
        )
        safe_link = owner.get_by_role("link", name="Continue application", exact=True)
        expect(safe_link).to_have_attribute("href", re.compile(r"^/en/applications\?"))
        assert "evil.example" not in safe_link.get_attribute("href")

        with Session(engine) as db:
            application = db.get(Application, UUID(owner_receipt["id"]))
            assert application and application.state == "under_review"
            revision = db.get(ApplicationRevision, application.current_revision_id)
            assert revision
            answers = list(
                db.scalars(
                    select(ApplicationAnswer).where(ApplicationAnswer.revision_id == revision.id)
                )
            )
            assert (
                len(answers) == 1
                and answers[0].value == "Private synthetic enterprise idea owner " + suffix
            )
        assert not errors, errors
    finally:
        browser.close()
        engine.dispose()

print(
    "PASS: public Apply/account/no-grant registration/local verification/login; "
    "default organization and chosen-cycle preservation; draft/save/submit; "
    "closed-intake owner history and receipt; under-review immutability; "
    "peer/organization/CSRF/BFF negatives; stale-cycle recovery; "
    "English/Tamil responsive layouts and keyboard skip link; no JS errors"
)
