"""Synthetic content lifecycle, public pagination and media-metadata acceptance."""

import os
import re
import secrets
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID, uuid4

from app.modules.cms import asset_service, editorial_service
from app.modules.cms.models import EditorialEntry
from app.modules.cms.schemas import AssetCreate, EditorialCommand, EditorialDraft
from app.modules.identity.models import (
    AuditLog,
    Organization,
    Person,
    Role,
    RolePermission,
    User,
    UserRole,
)
from app.modules.identity.security import hasher
from app.modules.identity.service import seed_roles
from playwright.sync_api import expect, sync_playwright
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

engine = create_engine(os.environ["DATABASE_URL"])
assert engine.url.database in {"edp_foundation_e2e", "edp_web_journey_e2e"}
base, api = os.environ["WEB_ORIGIN"], os.environ["API_INTERNAL_URL"]
assert urlparse(base).hostname in {"127.0.0.1", "localhost"}
assert urlparse(api).hostname in {"127.0.0.1", "localhost"}
assert urlparse(base).scheme == urlparse(api).scheme == "http"
org = UUID(os.environ["PUBLIC_ORGANIZATION_ID"])
suffix = uuid4().hex[:12]
slug = "synthetic-editorial-" + suffix
title = "Synthetic editorial title " + suffix
body = "Synthetic published body <script>alert('synthetic')</script> " + suffix
actors = {
    key: {
        "email": f"editorial-{key}-{suffix}@example.com",
        "password": secrets.token_urlsafe(24),
        "name": "Synthetic editorial " + key + " " + suffix,
    }
    for key in ("author", "viewer", "outsider")
}


def fixture_entry(
    db, actor, organization, key, *, kind="news", locale="en", publish=True, order=1000
):
    entry = editorial_service.create(
        db,
        organization,
        actor,
        EditorialDraft(
            kind=kind,
            locale=locale,
            slug=f"synthetic-{key}-{suffix}",
            title=f"Synthetic {key} {suffix}",
            body="Synthetic fixture content " + suffix,
            sort_order=order,
        ),
        "synthetic-editorial-fixture",
    )
    if publish:
        entry = editorial_service.mutate(
            db,
            organization,
            entry.id,
            actor,
            EditorialCommand(expected_version=1),
            "publish",
            "synthetic-fixture-publish",
        )
    return entry


with Session(engine) as db:
    seed_roles(db)
    assert db.get(Organization, org), (
        "Run after the applicant journey seeds the public organization"
    )
    other = Organization(name="Synthetic unrelated editorial organization " + suffix)
    viewer_role = Role(name="Synthetic editorial reader " + suffix)
    db.add_all([other, viewer_role])
    db.flush()
    db.add_all(
        [
            RolePermission(role_id=viewer_role.id, permission_code=permission)
            for permission in ("cms.editorial.view", "cms.asset.view")
        ]
    )
    manager = db.scalar(select(Role).where(Role.name == "Content Manager"))
    assert manager
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
                role_id=viewer_role.id if key == "viewer" else manager.id,
                organization_id=other.id if key == "outsider" else org,
            )
        )
    db.commit()
    other_org = other.id
    author = db.get(User, actors["author"]["id"])
    outsider = db.get(User, actors["outsider"]["id"])
    assert author and outsider
    foreign = fixture_entry(db, outsider, other_org, "foreign-news")
    wrong_kind = fixture_entry(db, author, org, "event-cursor", kind="event")
    wrong_locale = fixture_entry(db, author, org, "tamil-cursor", locale="ta")
    viewer_draft = fixture_entry(db, author, org, "viewer-draft", publish=False)
    metadata = []
    # Synthetic recorded states only: these fixtures contain no bytes and do not
    # represent a working secure upload, scanner or download implementation.
    for status in ("pending", "clean", "infected", "public"):
        asset = asset_service.create(
            db,
            org,
            author,
            AssetCreate(
                filename=f"synthetic-{status}-{suffix}.pdf",
                media_type="application/pdf",
                byte_size=1234,
                title=f"Synthetic {status} metadata {suffix}",
            ),
            "synthetic-metadata-create",
        )
        if status != "pending":
            asset = asset_service.scan_result(
                db,
                org,
                asset.id,
                status != "infected",
                "Synthetic recorded metadata fixture",
                "synthetic-recorded-status",
            )
        if status == "public":
            asset = asset_service.publish(db, org, asset.id, author, "synthetic-recorded-public")
        metadata.append(asset)

evidence = Path(".tool-cache/evidence")
evidence.mkdir(parents=True, exist_ok=True)
errors = []
dialogs = []
root = f"/api/cms/organizations/{org}/editorial"
public_root = f"{api}/api/v1/public/organizations/{org}/editorial"


def attach(page):
    page.on("pageerror", lambda error: errors.append(type(error).__name__))
    page.on("dialog", lambda dialog: (dialogs.append(dialog.type), dialog.dismiss()))
    return page


def sign_in(browser, key):
    page = attach(browser.new_context(viewport={"width": 1280, "height": 900}).new_page())
    page.goto(base + "/en/account")
    page.get_by_label("Email", exact=True).fill(actors[key]["email"])
    page.get_by_label("Password", exact=True).fill(actors[key]["password"])
    page.locator("form").get_by_role("button", name="Sign in", exact=True).click()
    expect(page.get_by_text(actors[key]["name"], exact=True)).to_be_visible()
    return page


def mutate(page, method, path, data):
    csrf = page.request.get(base + "/api/session/csrf").json()["csrf_token"]
    return page.request.fetch(
        base + path,
        method=method,
        data=data,
        headers={
            "Origin": base,
            "X-CSRF-Token": csrf,
        },
    )


def select_entry(page, entry_title):
    page.get_by_role("complementary", name="Content entries").get_by_role(
        "button", name=re.compile("^" + re.escape(entry_title))
    ).click()
    expect(page.get_by_label("Title", exact=True)).to_have_value(entry_title)


def ui_write(page, button, ending, method="POST"):
    with page.expect_response(
        lambda response: response.url.endswith(ending) and response.request.method == method
    ) as result:
        page.get_by_role("button", name=button, exact=True).click()
    assert result.value.status in {200, 201}, result.value.status
    expect(page.get_by_role("status")).to_have_text("Saved.")
    return result.value.json()


def responsive(page, label):
    expect(page.locator("#main")).to_have_count(1)
    for width in (360, 768, 1280):
        page.set_viewport_size({"width": width, "height": 900})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        page.locator("a.skip").focus()
        page.keyboard.press("Enter")
        assert page.evaluate("document.activeElement.id") == "main"
        page.screenshot(path=str(evidence / f"editorial-{label}-{width}.png"), full_page=True)


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel=os.getenv("PLAYWRIGHT_CHANNEL"), headless=True)
    try:
        page = sign_in(browser, "author")
        page.goto(base + f"/en/admin/content?organization={org}")
        expect(page.get_by_role("heading", name="Content studio", exact=True)).to_be_visible()
        page.get_by_role("button", name="New entry", exact=True).click()
        page.get_by_label("Content address", exact=True).fill(slug)
        page.get_by_label("Title", exact=True).fill(title)
        page.get_by_role("textbox", name="Content", exact=True).fill(body)
        page.get_by_label("Display order", exact=True).fill("10")
        created = ui_write(page, "Save draft", "/editorial")
        entry_id = created["id"]
        assert created["state"] == "draft" and created["version"] == 1
        public = attach(browser.new_context(viewport={"width": 1280, "height": 900}).new_page())
        public_url = public_root + f"/news/{slug}?locale=en"
        assert public.request.get(public_url).status == 404
        published = ui_write(page, "Publish saved draft", "/publish")
        assert published["version"] == 2 and published["state"] == "published"
        expect(page.get_by_label("Title", exact=True)).to_be_disabled()
        expect(page.get_by_role("textbox", name="Content", exact=True)).to_be_disabled()
        public.goto(base + f"/en/content/news/{slug}")
        expect(public.get_by_role("heading", name=title, exact=True)).to_be_visible()
        expect(public.locator(".content-body")).to_have_text(body)
        expect(public.locator("main script")).to_have_count(0)
        rejected = mutate(
            page,
            "PATCH",
            root + "/" + entry_id,
            {
                "expected_version": 2,
                "title": title,
                "body": "Rejected published edit",
                "starts_at": None,
                "ends_at": None,
                "sort_order": 10,
            },
        )
        assert (
            rejected.status == 409
            and rejected.json()["error"]["code"] == "published_entry_read_only"
        )
        assert public.request.get(public_url).json()["body"] == body
        page.get_by_label("Archive reason", exact=True).fill("Synthetic acceptance archive")
        archived = ui_write(page, "Archive", "/archive")
        assert archived["version"] == 3 and archived["state"] == "archived"
        assert public.request.get(public_url).status == 404
        restored = ui_write(page, "Restore draft", "/restore")
        assert restored["version"] == 4 and restored["state"] == "draft"
        expect(page.get_by_role("textbox", name="Content", exact=True)).to_be_enabled()
        assert public.request.get(public_url).status == 404

        stale = attach(page.context.new_page())
        stale.goto(base + f"/en/admin/content?organization={org}")
        select_entry(stale, title)
        local_body = "Synthetic reviewed local changes " + suffix
        stale.get_by_role("textbox", name="Content", exact=True).fill(local_body)
        server_body = "Synthetic concurrently saved content " + suffix
        page.get_by_role("textbox", name="Content", exact=True).fill(server_body)
        updated = ui_write(page, "Save draft", "/" + entry_id, "PATCH")
        assert updated["version"] == 5
        with stale.expect_response(
            lambda response: (
                response.url.endswith("/" + entry_id) and response.request.method == "PATCH"
            )
        ) as conflict:
            stale.get_by_role("button", name="Save draft", exact=True).click()
        assert conflict.value.status == 409
        expect(stale.get_by_role("status")).to_contain_text("Your local draft has been kept")
        expect(stale.get_by_role("textbox", name="Content", exact=True)).to_have_value(local_body)
        stale.get_by_role("button", name="Load latest values", exact=True).click()
        expect(stale.locator(".content-conflict")).to_contain_text(server_body)
        stale.get_by_role(
            "button", name="Use latest version and keep my changes", exact=True
        ).click()
        reconciled = ui_write(stale, "Save draft", "/" + entry_id, "PATCH")
        assert reconciled["version"] == 6 and reconciled["body"] == local_body
        republished = ui_write(stale, "Publish saved draft", "/publish")
        assert republished["version"] == 7
        public.reload()
        expect(public.locator(".content-body")).to_have_text(local_body)
        responsive(stale, "studio-en")

        # Each locale has an independent edition, even when the address is shared.
        stale.get_by_role("combobox", name="Content language", exact=True).select_option("ta")
        stale.get_by_role("button", name="New entry", exact=True).click()
        stale.get_by_label("Content address", exact=True).fill(slug)
        stale.get_by_label("Title", exact=True).fill("செயற்கை தமிழ் செய்தி " + suffix)
        stale.get_by_role("textbox", name="Content", exact=True).fill(
            "செயற்கை தமிழ் உள்ளடக்கம் " + suffix
        )
        tamil = ui_write(stale, "Save draft", "/editorial")
        assert tamil["locale"] == "ta" and tamil["id"] != entry_id
        ui_write(stale, "Publish saved draft", "/publish")
        public.goto(base + f"/ta/content/news/{slug}")
        expect(
            public.get_by_role("heading", name="செயற்கை தமிழ் செய்தி " + suffix, exact=True)
        ).to_be_visible()
        assert public.request.get(public_url).json()["body"] == local_body

        viewer = sign_in(browser, "viewer")
        viewer.goto(base + f"/en/admin/content?organization={org}")
        expect(viewer.get_by_role("button", name="New entry", exact=True)).to_be_disabled()
        select_entry(viewer, viewer_draft.title)
        expect(viewer.get_by_role("textbox", name="Content", exact=True)).to_be_disabled()
        expect(viewer.get_by_role("button", name="Publish saved draft", exact=True)).to_have_count(
            0
        )
        for method, path, data in (
            (
                "POST",
                root,
                {
                    "kind": "news",
                    "locale": "en",
                    "slug": "denied-" + suffix,
                    "title": "Denied",
                    "body": "Denied",
                },
            ),
            (
                "PATCH",
                root + "/" + str(viewer_draft.id),
                {"expected_version": 1, "title": "Denied", "body": "Denied"},
            ),
            (
                "POST",
                root + "/" + str(viewer_draft.id) + "/publish",
                {"expected_version": 1},
            ),
        ):
            assert mutate(viewer, method, path, data).status == 403
        assert (
            page.request.get(base + f"/api/cms/organizations/{other_org}/editorial").status == 403
        )
        assert page.request.get(base + root + "/" + str(foreign.id)).status == 404
        assert public.request.get(base + root).status == 401

        page.goto(base + f"/en/admin/media?organization={org}")
        expect(page.get_by_role("heading", name="Media metadata", exact=True)).to_be_visible()
        expect(
            page.get_by_text(
                "Secure file upload, storage, scanning and authorized byte delivery are pending.",
                exact=False,
            )
        ).to_be_visible()
        for asset in metadata:
            item = page.locator(".media-metadata-list li").filter(
                has=page.get_by_role("heading", name=asset.title, exact=True)
            )
            expect(item).to_contain_text(asset.filename)
            expect(item).to_contain_text(asset.scan_status.capitalize())
            expect(item).to_contain_text(asset.visibility.capitalize())
        expect(page.locator("main input[type=file], main a[download]")).to_have_count(0)
        expect(page.locator(".media-metadata-list a, .media-metadata-list button")).to_have_count(0)
        for asset in metadata:
            assert page.locator(f"main a[href*='{asset.id}']").count() == 0
        assets_path = f"/api/cms/organizations/{org}/assets"
        asset_response = page.request.get(base + assets_path)
        assert asset_response.status == 200 and "storage_key" not in asset_response.text()
        assert mutate(page, "POST", assets_path, {}).status == 404
        assert (
            mutate(page, "POST", assets_path + "/" + str(metadata[-1].id) + "/publish", {}).status
            == 404
        )
        assert page.request.get(base + f"/api/cms/organizations/{other_org}/assets").status == 403
        responsive(page, "metadata-en")
        page.goto(base + f"/ta/admin/media?organization={org}")
        expect(page.locator("html")).to_have_attribute("lang", "ta")
        expect(page.locator(".media-metadata-list li")).to_have_count(4)
        responsive(page, "metadata-ta")

        with Session(engine) as db:
            author = db.get(User, actors["author"]["id"])
            assert author
            paging = [
                fixture_entry(db, author, org, f"pagination-{index:02d}", order=1000 + index)
                for index in range(26)
            ]
        public.goto(base + "/en/content/news")
        expect(public.locator(".editorial-public-grid h2")).to_have_count(25)
        first_titles = public.locator(".editorial-public-grid h2").all_text_contents()
        assert len(first_titles) == 25 and title in first_titles
        public.get_by_role("link", name="Next page", exact=True).click()
        expect(public.locator(".editorial-public-grid h2")).to_have_count(2)
        second_titles = public.locator(".editorial-public-grid h2").all_text_contents()
        assert len(second_titles) == 2 and not set(first_titles) & set(second_titles)
        assert set(first_titles + second_titles) == {
            title,
            *(entry.title for entry in paging),
        }
        expect(public.get_by_role("link", name="Next page", exact=True)).to_have_count(0)
        public.get_by_role("link", name="First page", exact=True).click()
        expect(public.locator(".editorial-public-grid h2")).to_have_count(25)
        responsive(public, "public-news-en")

        for cursor in (
            foreign.id,
            wrong_kind.id,
            wrong_locale.id,
            viewer_draft.id,
            uuid4(),
        ):
            invalid = public.request.get(
                public_root + f"?kind=news&locale=en&limit=25&cursor={cursor}"
            )
            assert invalid.status == 400 and invalid.json()["error"]["code"] == "invalid_cursor"
        public.goto(base + f"/en/content/news?cursor={foreign.id}")
        expect(public.get_by_role("main").get_by_role("alert")).to_contain_text(
            "Content could not be loaded"
        )
        expect(public.locator(".editorial-public-grid h2")).to_have_count(0)
        for query in (
            "cursor=invalid",
            "limit=100",
            f"cursor={entry_id}&cursor={entry_id}",
        ):
            # Next.js streams a 200 after the loading boundary, then renders its
            # not-found UI with noindex; a pre-stream not-found returns 404.
            rejected = public.goto(base + "/en/content/news?" + query)
            assert rejected and rejected.status in {200, 404}
            expect(public.get_by_role("heading", name="404", exact=True)).to_be_visible()
            expect(public.locator('meta[name="robots"]').first).to_have_attribute(
                "content", re.compile("noindex")
            )
            expect(public.locator(".editorial-public-grid h2")).to_have_count(0)
        public.goto(base + "/ta/content/news")
        expect(
            public.get_by_role("heading", name="செயற்கை தமிழ் செய்தி " + suffix, exact=True)
        ).to_be_visible()
        responsive(public, "public-news-ta")
        page.goto(base + f"/ta/admin/content?organization={org}")
        expect(page.locator("html")).to_have_attribute("lang", "ta")
        expect(page.get_by_role("heading", name="உள்ளடக்கப் பகுதி", exact=True)).to_be_visible()
        expect(page.get_by_role("combobox", name="உள்ளடக்க மொழி", exact=True)).to_have_value("ta")
        expect(page.locator(".content-admin-list")).to_contain_text("செயற்கை தமிழ் செய்தி " + suffix)
        expect(page.locator(".content-admin-grid")).to_have_attribute("aria-busy", "false")
        responsive(page, "studio-ta")
        with Session(engine) as db:
            saved = db.get(EditorialEntry, UUID(entry_id))
            assert saved and saved.state == "published" and saved.version == 7
            audit = list(
                db.scalars(
                    select(AuditLog)
                    .where(AuditLog.resource_id == saved.id)
                    .order_by(AuditLog.resource_version)
                )
            )
            assert [item.resource_version for item in audit] == list(range(1, 8))
            assert all(
                local_body not in (item.changed_fields or "") and body not in (item.reason or "")
                for item in audit
            )
        assert not errors, errors
        assert not dialogs, dialogs
    finally:
        browser.close()
        engine.dispose()

print(
    "PASS: scoped content creation/publication/archive/restore; published read-only enforcement; "
    "two-tab conflict review and republication; independent English/Tamil editions; "
    "public list pagination and scope-bound cursors; narrow-reader/org/BFF negatives; "
    "read-only media metadata boundaries; responsive keyboard acceptance; no JS errors"
)
