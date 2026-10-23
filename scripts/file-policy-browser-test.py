"""Synthetic policy rules/lifecycle acceptance; no file collection or provider calls."""

import os
import re
import secrets
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID, uuid4

from app.core.config import get_settings
from app.modules.files import service
from app.modules.files.models import FileObject, FilePolicy
from app.modules.files.schemas import FilePolicyCommand, FilePolicyCreate
from app.modules.identity.models import Organization, Person, Role, RolePermission, User, UserRole
from app.modules.identity.security import hasher
from app.modules.identity.service import seed_roles
from playwright.sync_api import expect, sync_playwright
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

engine = create_engine(os.environ["DATABASE_URL"])
assert engine.url.database == "edp_file_policy_e2e"
base, api = os.environ["WEB_ORIGIN"], os.environ["API_INTERNAL_URL"]
assert urlparse(base).hostname in {"127.0.0.1", "localhost"}
assert urlparse(api).hostname in {"127.0.0.1", "localhost"}
assert urlparse(base).scheme == urlparse(api).scheme == "http"
assert not get_settings().files_enabled and not get_settings().files_maintenance_enabled
org = UUID(os.environ["PUBLIC_ORGANIZATION_ID"])
suffix = uuid4().hex[:12]
actors = {
    key: {
        "email": f"policy-{key}-{suffix}@example.com",
        "password": secrets.token_urlsafe(24),
        "name": "Synthetic policy " + key + " " + suffix,
    }
    for key in ("director", "viewer", "outsider")
}
rules = {
    "name": "Synthetic document rules " + suffix,
    "notice_en": "Synthetic policy notice only " + suffix,
    "notice_ta": "செயற்கை அறிவிப்பு மட்டும் " + suffix,
    "allowed_mime_types": ["application/pdf", "image/jpeg"],
    "max_file_bytes": 4096,
    "max_files": 2,
    "retention_days": 30,
    "rejected_retention_days": 3,
    "allow_frozen_disposal": False,
}
with Session(engine) as db:
    seed_roles(db)
    db.add(Organization(id=org, name="Synthetic policy organization " + suffix))
    other = Organization(name="Synthetic unrelated policy organization " + suffix)
    viewer_role = Role(name="Synthetic policy reader " + suffix)
    db.add_all([other, viewer_role])
    db.flush()
    db.add_all(
        [
            RolePermission(role_id=viewer_role.id, permission_code=code)
            for code in ("system.access", "files.policy.view")
        ]
    )
    director_role = db.scalar(select(Role).where(Role.name == "Program Director"))
    assert director_role
    for key, credentials in actors.items():
        person = Person(display_name=credentials["name"])
        db.add(person)
        db.flush()
        actor = User(
            person_id=person.id,
            email=credentials["email"],
            password_hash=hasher.hash(credentials["password"]),
            status="active",
        )
        db.add(actor)
        db.flush()
        credentials["id"] = actor.id
        db.add(
            UserRole(
                user_id=actor.id,
                role_id=viewer_role.id if key == "viewer" else director_role.id,
                organization_id=other.id if key == "outsider" else org,
            )
        )
    db.commit()
    other_org = other.id
    outsider = db.get(User, actors["outsider"]["id"])
    assert outsider
    foreign = service.create_policy(
        db,
        other_org,
        outsider,
        FilePolicyCreate(
            **rules,
            purpose="application_document",
            client_request_id=uuid4(),
            reason="Synthetic unrelated policy",
        ),
        "policy-browser-foreign",
    )

root = f"/api/file-policies/organizations/{org}/policies"
evidence = Path(".tool-cache/evidence")
evidence.mkdir(parents=True, exist_ok=True)
errors = []


def sign_in(browser, actor):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    page.on("pageerror", lambda error: errors.append(type(error).__name__))
    page.goto(base + "/en/account")
    page.get_by_label("Email", exact=True).fill(actors[actor]["email"])
    page.get_by_label("Password", exact=True).fill(actors[actor]["password"])
    page.locator("form").get_by_role("button", name="Sign in", exact=True).click()
    expect(page.get_by_text(actors[actor]["name"], exact=True)).to_be_visible()
    return page


def responsive(page, label):
    for width in (360, 390, 768, 1280):
        page.set_viewport_size({"width": width, "height": 900})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        page.locator("a.skip").focus()
        page.keyboard.press("Enter")
        assert page.evaluate("document.activeElement.id") == "main"
        page.screenshot(path=str(evidence / f"file-policy-{label}-{width}.png"), full_page=True)


def mutate(page, method, path, data, origin=None, csrf=True):
    headers = {"Origin": origin or base}
    if csrf:
        headers["X-CSRF-Token"] = page.request.get(base + "/api/session/csrf").json()["csrf_token"]
    return page.request.fetch(base + path, method=method, data=data, headers=headers)


def write(page, button, path, method="POST"):
    with page.expect_response(
        lambda response: response.request.method == method and response.url == base + path
    ) as result:
        page.get_by_role("button", name=button, exact=True).click()
    response = result.value
    assert response.status in {200, 201}, response.status
    expect(page.locator(".file-policy-grid")).to_have_attribute("aria-busy", "false")
    return response.json()


def select_policy(page, name):
    page.get_by_role("button", name=re.compile("^" + re.escape(name))).click()
    expect(page.get_by_role("textbox", name="Policy name", exact=True)).to_have_value(name)
    expect(page.locator(".file-policy-grid")).to_have_attribute("aria-busy", "false")


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel=os.getenv("PLAYWRIGHT_CHANNEL"), headless=True)
    try:
        page = sign_in(browser, "director")
        page.goto(base + f"/en/admin?organization={org}")
        page.get_by_role("link", name="File policies", exact=False).click()
        expect(page.get_by_role("heading", name="File policies", exact=True)).to_be_visible()
        expect(
            page.get_by_text("Publishing configures a policy edition.", exact=False)
        ).to_be_visible()
        expect(page.locator(".file-policy-grid")).to_have_attribute("aria-busy", "false")
        page.get_by_role("button", name="New policy draft", exact=True).click()
        for label in (
            "Policy name",
            "English notice",
            "Tamil notice",
            "Maximum file size (bytes)",
            "Maximum files",
            "Retention (days)",
            "Rejected-file retention (days)",
        ):
            role = (
                "spinbutton"
                if label.startswith(("Maximum", "Retention", "Rejected"))
                else "textbox"
            )
            expect(page.get_by_role(role, name=label, exact=True)).to_have_value("")
        for label in ("File purpose", "Disposal of frozen evidence"):
            expect(page.get_by_role("combobox", name=label, exact=True)).to_have_value("")
        expect(page.get_by_label("application/pdf", exact=True)).not_to_be_checked()
        page.get_by_role("combobox", name="File purpose", exact=True).select_option(
            "application_document"
        )
        for label, key in (
            ("Policy name", "name"),
            ("English notice", "notice_en"),
            ("Tamil notice", "notice_ta"),
            ("Maximum file size (bytes)", "max_file_bytes"),
            ("Maximum files", "max_files"),
            ("Retention (days)", "retention_days"),
            ("Rejected-file retention (days)", "rejected_retention_days"),
        ):
            role = (
                "spinbutton"
                if label.startswith(("Maximum", "Retention", "Rejected"))
                else "textbox"
            )
            page.get_by_role(role, name=label, exact=True).fill(str(rules[key]))
        for mime in rules["allowed_mime_types"]:
            page.get_by_label(mime, exact=True).check()
        page.get_by_role("combobox", name="Disposal of frozen evidence", exact=True).select_option(
            "false"
        )
        page.get_by_role("textbox", name="Change reason", exact=True).fill(
            "Synthetic draft configuration"
        )
        responsive(page, "editor-en")

        creations = []
        created = []

        def lost_create(route):
            if route.request.method != "POST":
                route.continue_()
                return
            creations.append(route.request.post_data_json)
            response = route.fetch()
            assert response.status == 201
            created.append(response.json())
            if len(creations) == 1:
                route.abort()
            else:
                route.fulfill(response=response)

        page.context.route(base + root, lost_create)
        page.get_by_role("button", name="Save draft", exact=True).click()
        expect(page.get_by_role("status")).to_contain_text("Draft creation could not be confirmed")
        expect(page.get_by_role("textbox", name="Policy name", exact=True)).to_be_disabled()
        assert len(creations) == 1
        page.get_by_role("button", name="Retry the same draft request", exact=True).click()
        expect(page.get_by_role("status")).to_contain_text("Saved.")
        expect(page.locator(".file-policy-grid")).to_have_attribute("aria-busy", "false")
        assert len(creations) == 2 and creations[0] == creations[1]
        assert created[0]["id"] == created[1]["id"] and created[1]["state"] == "draft"
        first = created[1]
        page.context.unroute(base + root, lost_create)
        page.get_by_role("textbox", name="English notice", exact=True).fill(
            rules["notice_en"] + " revised"
        )
        page.get_by_role("textbox", name="Change reason", exact=True).fill(
            "Synthetic revised notice"
        )
        updated = write(page, "Save draft", root + "/" + first["id"], "PATCH")
        assert updated["version"] == 2
        page.get_by_role("textbox", name="Change reason", exact=True).fill(
            "Publish synthetic edition one"
        )
        published = write(page, "Publish policy edition", root + "/" + first["id"] + "/publish")
        assert published["version"] == 3 and published["state"] == "published"
        expect(page.get_by_role("textbox", name="Policy name", exact=True)).to_be_disabled()
        expect(page.locator("main input[type=file], main a[download]")).to_have_count(0)

        page.get_by_role("button", name="Copy displayed rules to a new edition", exact=True).click()
        expect(page.get_by_role("combobox", name="File purpose", exact=True)).to_be_disabled()
        expect(page.get_by_role("textbox", name="Change reason", exact=True)).to_have_value("")
        copied_name = "Synthetic revised edition " + suffix
        page.get_by_role("textbox", name="Policy name", exact=True).fill(copied_name)
        page.get_by_role("textbox", name="Change reason", exact=True).fill(
            "Synthetic new policy edition"
        )
        second = write(page, "Save draft", root)
        assert (
            second["copy_from"] == first["id"]
            and second["edition"] == 2
            and second["state"] == "draft"
        )
        stale = page.context.new_page()
        stale.on("pageerror", lambda error: errors.append(type(error).__name__))
        stale.goto(base + f"/en/admin/file-policies?organization={org}")
        select_policy(stale, copied_name)
        page.get_by_role("spinbutton", name="Maximum files", exact=True).fill("3")
        page.get_by_role("textbox", name="Change reason", exact=True).fill(
            "Synthetic concurrent rule update"
        )
        write(page, "Save draft", root + "/" + second["id"], "PATCH")
        retained_notice = "செயற்கை பாதுகாக்கப்பட்ட உள்ளூர் அறிவிப்பு " + suffix
        stale.get_by_role("textbox", name="Tamil notice", exact=True).fill(retained_notice)
        stale.get_by_role("textbox", name="Change reason", exact=True).fill(
            "Synthetic retained rule reconciliation"
        )
        with stale.expect_response(
            lambda response: (
                response.request.method == "PATCH" and response.url.endswith(second["id"])
            )
        ) as conflict:
            stale.get_by_role("button", name="Save draft", exact=True).click()
        assert conflict.value.status == 409
        expect(stale.get_by_role("status")).to_contain_text("This edition changed")
        stale.get_by_role("button", name="Load current saved edition", exact=True).click()
        expect(
            stale.get_by_role("heading", name="Current saved edition", exact=True)
        ).to_be_visible()
        expect(stale.get_by_role("textbox", name="Tamil notice", exact=True)).to_have_value(
            retained_notice
        )
        stale.get_by_role(
            "button", name="Use current version and keep entered rules", exact=True
        ).click()
        stale.get_by_role("spinbutton", name="Maximum files", exact=True).fill("3")
        reconciled = write(stale, "Save draft", root + "/" + second["id"], "PATCH")
        assert reconciled["version"] == 3 and reconciled["notice_ta"] == retained_notice
        publications = []

        def lost_publish(route):
            response = route.fetch()
            assert response.status == 200
            publications.append(response.json())
            route.abort()

        publish_path = base + root + "/" + second["id"] + "/publish"
        page.context.route(publish_path, lost_publish)
        stale.get_by_role("textbox", name="Change reason", exact=True).fill(
            "Publish synthetic revised rules"
        )
        stale.get_by_role("button", name="Publish policy edition", exact=True).click()
        expect(stale.get_by_role("status")).to_contain_text("The change could not be confirmed")
        assert len(publications) == 1 and publications[0]["version"] == 4
        stale.get_by_role("button", name="Load current saved edition", exact=True).click()
        expect(stale.locator(".file-policy-conflict")).to_contain_text("Published")
        stale.get_by_role(
            "button", name="Use current version and keep entered rules", exact=True
        ).click()
        expect(
            stale.get_by_role("button", name="Publish policy edition", exact=True)
        ).to_have_count(0)
        expect(stale.get_by_role("textbox", name="Policy name", exact=True)).to_be_disabled()
        page.context.unroute(publish_path, lost_publish)
        stale.get_by_role("textbox", name="Change reason", exact=True).fill(
            "Retire synthetic edition"
        )
        retired = write(stale, "Retire policy edition", root + "/" + second["id"] + "/retire")
        assert retired["state"] == "retired" and retired["version"] == 5
        assert not get_settings().files_enabled

        viewer = sign_in(browser, "viewer")
        viewer.goto(base + f"/en/admin/file-policies?organization={org}")
        select_policy(viewer, copied_name)
        expect(viewer.get_by_role("button", name="New policy draft", exact=True)).to_be_disabled()
        expect(viewer.get_by_role("textbox", name="Policy name", exact=True)).to_be_disabled()
        for action in (
            "Publish policy edition",
            "Retire policy edition",
            "Copy displayed rules to a new edition",
        ):
            expect(viewer.get_by_role("button", name=action, exact=True)).to_have_count(0)
        denied_create = rules | {
            "purpose": "application_document",
            "client_request_id": str(uuid4()),
            "reason": "Synthetic denied creation",
        }
        assert mutate(viewer, "POST", root, denied_create).status == 403
        assert (
            mutate(
                viewer,
                "POST",
                root + "/" + second["id"] + "/retire",
                {"expected_version": 5, "reason": "Denied"},
            ).status
            == 403
        )
        assert (
            page.request.get(base + f"/api/file-policies/organizations/{other_org}/policies").status
            == 403
        )
        assert page.request.get(base + root + "/" + str(foreign.id)).status == 404
        assert page.request.get(base + root + "?cursor=" + str(foreign.id)).status == 422
        for path in (root + "/" + first["id"] + "/upload", root + "/" + first["id"] + "/activate"):
            assert mutate(page, "POST", path, {}).status == 404
        assert (
            page.request.get(
                base + f"/api/file-policies/organizations/{org}/files/{first['id']}/download"
            ).status
            == 404
        )
        assert mutate(page, "POST", root, denied_create, csrf=False).status == 403
        assert (
            mutate(page, "POST", root, denied_create, origin="https://unrelated.example").status
            == 403
        )
        for query in (
            "limit=101",
            "purpose=cms_asset&purpose=lms_material",
            "collection_enabled=true",
        ):
            assert page.request.get(base + root + "?" + query).status == 400
        response = page.request.get(base + root)
        assert response.status == 200 and "storage_key" not in response.text()
        assert os.environ["BFF_KEY"] not in page.content()

        with Session(engine) as db:
            director = db.get(User, actors["director"]["id"])
            assert director
            paging = []
            for index in range(26):
                value = service.create_policy(
                    db,
                    org,
                    director,
                    FilePolicyCreate(
                        **(rules | {"name": f"Synthetic paging {index:02d} {suffix}"}),
                        purpose="application_document",
                        client_request_id=uuid4(),
                        reason="Synthetic pagination setup",
                    ),
                    "policy-browser-pagination",
                )
                service.retire_policy(
                    db,
                    org,
                    value.id,
                    director,
                    FilePolicyCommand(
                        expected_version=1, reason="Synthetic retired paging fixture"
                    ),
                    "policy-browser-pagination-retire",
                )
                paging.append(value.name)
            assert db.get(FilePolicy, UUID(first["id"])).state == "retired"
            assert db.get(FilePolicy, UUID(second["id"])).version == 5
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(FileObject)
                    .where(FileObject.organization_id == org)
                )
                == 0
            )
        page.goto(base + f"/en/admin/file-policies?organization={org}")
        expect(page.locator(".file-policy-grid")).to_have_attribute("aria-busy", "false")
        expect(page.locator(".file-policy-grid aside li")).to_have_count(25)
        page.get_by_role("button", name="Load more", exact=True).click()
        expect(page.locator(".file-policy-grid aside li")).to_have_count(28)
        names = page.locator(".file-policy-grid aside li button").evaluate_all(
            "items => items.map(item => item.firstChild.textContent)"
        )
        assert set(names) == {rules["name"], copied_name, *paging} and len(set(names)) == 28
        page.goto(base + f"/ta/admin/file-policies?organization={org}")
        expect(page.locator("html")).to_have_attribute("lang", "ta")
        expect(page.get_by_role("heading", name="கோப்புக் கொள்கைகள்", exact=True)).to_be_visible()
        expect(page.locator(".file-policy-grid")).to_have_attribute("aria-busy", "false")
        page.get_by_role("button", name="புதிய கொள்கை வரைவு", exact=True).click()
        expect(page.get_by_role("textbox", name="தமிழ் அறிவிப்பு", exact=True)).to_have_value("")
        responsive(page, "editor-ta")
        assert not get_settings().files_enabled and not errors, errors
    finally:
        browser.close()
        engine.dispose()

print(
    "PASS: explicit bilingual policy rules; idempotent lost-create recovery; "
    "versioned update/publication/copy/retirement; two-tab conflict and lost-publication "
    "reconciliation; narrow-reader/org/CSRF/BFF/cursor negatives; bounded 28-edition pagination; "
    "no generic byte or activation routes; collection remains disabled; "
    "English/Tamil responsive keyboard checks; no JS errors"
)
