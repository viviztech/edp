"""Synthetic CMS bytes acceptance; scanner results are script-only service injections."""

import hashlib
import os
import secrets
from collections import deque
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID, uuid4

from PIL import Image, PngImagePlugin
from playwright.sync_api import expect, sync_playwright
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.cms.models import Asset
from app.modules.files import service as files
from app.modules.files.models import FileObject
from app.modules.files.runtime import get_private_storage
from app.modules.files.scanner import ScanResult
from app.modules.files.schemas import FilePolicyCommand, FilePolicyCreate
from app.modules.identity.models import (
    Organization,
    Person,
    Role,
    RolePermission,
    User,
    UserRole,
)
from app.modules.identity.security import hasher
from app.modules.identity.service import seed_roles

engine = create_engine(os.environ["DATABASE_URL"])
assert engine.url.database == "edp_cms_files_e2e"
assert engine.url.host in {"127.0.0.1", "localhost"}
base, api = os.environ["WEB_ORIGIN"], os.environ["API_INTERNAL_URL"]
assert urlparse(base).hostname == urlparse(api).hostname == "127.0.0.1"
assert urlparse(base).port == 3111 and urlparse(api).port == 8111
settings = get_settings()
assert settings.files_enabled and not settings.files_maintenance_enabled
assert settings.files_storage_backend == "local" and settings.files_max_bytes == 4096
assert settings.clamav_host is None
org, suffix = UUID(os.environ["PUBLIC_ORGANIZATION_ID"]), uuid4().hex[:12]
pdf = b"%PDF-1.4\n% Synthetic local acceptance document only\n%%EOF\n"
image_output = BytesIO()
metadata = PngImagePlugin.PngInfo()
metadata.add_text("SyntheticPrivateMetadata", "Synthetic original metadata must not be public")
with Image.new("RGB", (24, 18), "#165a90") as original:
    original.save(image_output, format="PNG", pnginfo=metadata)
png = image_output.getvalue()
assert len(png) < 4096
actors = {
    key: {
        "name": f"Synthetic CMS {key} {suffix}",
        "email": f"cms-{key}-{suffix}@example.com",
        "password": secrets.token_urlsafe(24),
    }
    for key in ("manager", "reader", "create_only", "outsider")
}
with Session(engine) as db:
    seed_roles(db)
    db.add(Organization(id=org, name="Synthetic CMS file organization " + suffix))
    other = Organization(name="Synthetic other CMS organization " + suffix)
    db.add(other)
    db.flush()
    read_role = Role(name="Synthetic CMS reader " + suffix)
    create_role = Role(name="Synthetic CMS create without view " + suffix)
    db.add_all([read_role, create_role])
    db.flush()
    db.add_all(
        [
            RolePermission(role_id=read_role.id, permission_code="cms.asset.view"),
            RolePermission(role_id=create_role.id, permission_code="cms.asset.create"),
        ]
    )
    manager_role = db.scalar(select(Role).where(Role.name == "Content Manager"))
    assert manager_role
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
        role = (
            read_role if key == "reader" else create_role if key == "create_only" else manager_role
        )
        db.add(
            UserRole(
                user_id=actor.id,
                role_id=role.id,
                organization_id=other.id if key == "outsider" else org,
            )
        )
    # Historical flags deliberately contain no typed backing file or byte authority.
    legacy = Asset(
        organization_id=org,
        storage_key="synthetic-legacy/" + suffix,
        filename="historical.pdf",
        media_type="application/pdf",
        byte_size=12,
        title="Synthetic historical metadata " + suffix,
        scan_status="clean",
        visibility="public",
    )
    db.add(legacy)
    db.commit()
    director_role = db.scalar(select(Role).where(Role.name == "Program Director"))
    assert director_role
    manager = db.get(User, actors["manager"]["id"])
    assert manager
    # This fixture's manager temporarily has the policy-authoring role only for seeding.
    policy_grant = UserRole(user_id=manager.id, role_id=director_role.id, organization_id=org)
    db.add(policy_grant)
    db.commit()
    policy = files.create_policy(
        db,
        org,
        manager,
        FilePolicyCreate(
            client_request_id=uuid4(),
            purpose="cms_asset",
            name="Synthetic CMS policy " + suffix,
            notice_en="Synthetic local CMS collection notice only",
            notice_ta="செயற்கை உள்ளூர் ஊடகச் சேகரிப்பு அறிவிப்பு மட்டும்",
            allowed_mime_types=["application/pdf", "image/png"],
            max_file_bytes=8192,
            max_files=2,
            retention_days=30,
            rejected_retention_days=3,
            allow_frozen_disposal=False,
            reason="Synthetic CMS acceptance configuration",
        ),
        "browser-cms-policy-create",
    )
    files.publish_policy(
        db,
        org,
        policy.id,
        manager,
        FilePolicyCommand(expected_version=policy.version, reason="Synthetic policy publication"),
        "browser-cms-policy-publish",
    )
    db.delete(policy_grant)
    db.commit()
    other_org, legacy_id = other.id, legacy.id

evidence = Path(".tool-cache/evidence")
evidence.mkdir(parents=True, exist_ok=True)
errors = []
responses = deque(maxlen=20)


class ControlledScanner:
    """No API hook or runtime configuration can enable these controlled results."""

    def __init__(self, status, expected_digest, expected_size, *, sanitized=False):
        self.status, self.expected_digest, self.expected_size = (
            status,
            expected_digest,
            expected_size,
        )
        self.sanitized = sanitized

    def scan(self, source, *, max_bytes):
        value = source.read(max_bytes + 1)
        assert len(value) == self.expected_size <= max_bytes
        assert hashlib.sha256(value).hexdigest() == self.expected_digest
        if self.sanitized:
            with Image.open(BytesIO(value)) as image:
                assert image.size == (24, 18)
                assert not image.info.get("SyntheticPrivateMetadata")
                assert not image.info.get("exif") and not image.info.get("icc_profile")
            assert value != png
        return ScanResult(self.status, self.expected_digest, len(value), "synthetic-test-result")


def scan(file_id, status="clean", *, sanitized=False):
    with Session(engine) as db:
        row = db.get(FileObject, UUID(file_id))
        assert row and row.organization_id == org and row.purpose == "cms_asset"
        adapter = ControlledScanner(
            status, row.expected_sha256, row.expected_byte_size, sanitized=sanitized
        )
        lease = files.claim_scan(db, org, row.id, "browser-cms-controlled-claim")
        result = files.scan_with_lease(
            db, org, lease, get_private_storage(), adapter, "browser-cms-controlled-result"
        )
        assert result.state == ("quarantined" if status == "error" else status)
        return result


def sign_in(browser, key):
    page = browser.new_context(viewport={"width": 1280, "height": 900}).new_page()
    page.on("pageerror", lambda error: errors.append(type(error).__name__))
    page.on(
        "response",
        lambda response: (
            responses.append(
                (response.request.method, urlparse(response.url).path, response.status)
            )
            if response.url.startswith(base + "/api/")
            else None
        ),
    )
    page.goto(base + "/en/account")
    page.get_by_role("textbox", name="Email", exact=True).fill(actors[key]["email"])
    page.get_by_label("Password", exact=True).fill(actors[key]["password"])
    page.locator("form").get_by_role("button", name="Sign in", exact=True).click()
    expect(page.get_by_text(actors[key]["name"], exact=True)).to_be_visible()
    return page


def responsive(page, label):
    for width in (360, 390, 768, 1280):
        page.set_viewport_size({"width": width, "height": 900})
        page.screenshot(path=str(evidence / f"cms-files-{label}-{width}.png"), full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), (
            label,
            width,
        )
        page.locator("a.skip").focus()
        page.keyboard.press("Enter")
        assert page.evaluate("document.activeElement.id") == "main"


def mutate(page, path, data, *, method="POST", media="application/json", version=None, csrf=True):
    headers = {"Origin": base, "Content-Type": media}
    if csrf:
        headers["X-CSRF-Token"] = page.request.get(base + "/api/session/csrf").json()["csrf_token"]
    if version:
        headers["If-Match"] = f'"{version}"'
    return page.request.fetch(base + path, method=method, data=data, headers=headers)


staff = f"/api/cms/organizations/{org}/assets"
public_root = f"/api/public-media/organizations/{org}/assets"
public_api = api + f"/api/v1/public/organizations/{org}/assets"


def current(page, asset_id):
    response = page.request.get(base + staff + "/" + str(asset_id))
    assert response.status == 200
    assert all(
        value not in response.text() for value in ("storage_key", "object_key", "token_digest")
    )
    return response.json()


def ready(page):
    expect(page.locator("main > section")).to_have_attribute("aria-busy", "false")


def inspect(page, title):
    page.get_by_role("button", name="Inspect media: " + title, exact=True).click()
    ready(page)


def upload(page, title, value=pdf, media="application/pdf"):
    page.get_by_role("textbox", name="Media title", exact=True).fill(title)
    page.get_by_label("Source file", exact=True).set_input_files(
        {
            "name": "synthetic-image.png" if media == "image/png" else "synthetic.pdf",
            "mimeType": media,
            "buffer": value,
        }
    )
    with page.expect_response(
        lambda response: (
            response.request.method == "PUT" and response.url.endswith("/source/content")
        )
    ) as completed:
        page.get_by_role("button", name="Register and upload", exact=True).click()
    ready(page)
    result = completed.value
    if result.status == 200:
        expect(page.get_by_label("Source file", exact=True)).to_have_value("")
        assert (
            page.get_by_label("Source file", exact=True).evaluate("input => input.files.length")
            == 0
        )
    return result


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel=os.getenv("PLAYWRIGHT_CHANNEL"), headless=True)
    try:
        page = sign_in(browser, "manager")
        page.goto(base + f"/en/admin/media?organization={org}")
        ready(page)
        configuration = page.request.get(base + staff + "/policy").json()
        assert configuration["enabled"] and configuration["max_upload_bytes"] == 4096
        assert configuration["policy"]["max_file_bytes"] == 8192
        inspect(page, "Synthetic historical metadata " + suffix)
        expect(page.get_by_text("Metadata only — no verified bytes", exact=True)).to_be_visible()
        assert current(page, legacy_id)["public_url"] is None
        assert page.request.get(base + public_root + f"/{legacy_id}/content").status == 404
        assert page.request.get(public_api).json()["items"] == []
        assert mutate(page, staff + f"/{legacy_id}/scan", {"clean": True}).status == 404
        retired = page.request.post(
            api + f"/api/v1/internal/cms/organizations/{org}/assets/{legacy_id}/scan",
            data={"clean": True},
            headers={"X-BFF-Key": os.environ["BFF_KEY"]},
        )
        assert retired.status == 410
        page.get_by_role("textbox", name="Media title", exact=True).fill("Too large synthetic")
        page.get_by_label("Source file", exact=True).set_input_files(
            {"name": "oversize.pdf", "mimeType": "application/pdf", "buffer": b"x" * 4097}
        )
        page.get_by_role("button", name="Register and upload", exact=True).click()
        expect(page.locator("main > section > [role=status]")).to_have_text(
            "Choose a supported file within the published policy and upload limits."
        )
        unavailable = upload(page, "Synthetic unavailable scanner " + suffix)
        assert unavailable.status == 200
        unavailable_asset = unavailable.json()
        scan(unavailable_asset["source"]["id"], "error")
        page.get_by_role("button", name="Refresh status", exact=True).click()
        ready(page)
        expect(
            page.get_by_text("The scanner is unavailable. This file remains private.", exact=True)
        ).to_be_visible()
        expect(page.get_by_role("button", name="Publish media", exact=True)).to_have_count(0)
        assert (
            page.request.get(base + staff + f"/{unavailable_asset['id']}/source/content").status
            == 409
        )

        def corrupt_upload(route):
            if route.request.method == "PUT":
                corrupted = bytes([pdf[0] ^ 1]) + pdf[1:]
                route.fulfill(response=route.fetch(post_data=corrupted))
            else:
                route.continue_()

        page.context.route(base + staff + "/*/source/content", corrupt_upload)
        rejected = upload(page, "Synthetic rejected checksum " + suffix)
        assert rejected.status == 422
        page.context.unroute(base + staff + "/*/source/content", corrupt_upload)
        failed = page.request.get(base + staff).json()["items"]
        rejected_asset = next(
            item for item in failed if item["title"] == "Synthetic rejected checksum " + suffix
        )
        assert rejected_asset["source"]["state"] == "rejected"
        assert rejected_asset["source"]["failure_code"] == "upload_verification_failed"
        page.get_by_role("button", name="Refresh status", exact=True).click()
        ready(page)
        expect(page.get_by_text("Private source: Rejected", exact=True)).to_be_visible()
        expect(page.get_by_role("button", name="Publish media", exact=True)).to_have_count(0)
        assert (
            page.request.get(base + staff + f"/{rejected_asset['id']}/source/content").status == 409
        )
        assert (
            page.request.get(base + public_root + f"/{rejected_asset['id']}/content").status == 404
        )
        page.get_by_role("button", name="Start a new registration", exact=True).click()
        expect(page.get_by_label("Source file", exact=True)).to_have_value("")

        metadata_requests, metadata_results, put_results, actual_puts = [], [], [], []
        page.on(
            "request",
            lambda request: (
                actual_puts.append(request.url)
                if request.method == "PUT" and request.url.endswith("/source/content")
                else None
            ),
        )

        def lose_metadata(route):
            if route.request.method != "POST":
                route.continue_()
                return
            metadata_requests.append(route.request.post_data_json)
            response = route.fetch()
            assert response.status == 201
            metadata_results.append(response.json())
            if len(metadata_requests) == 1:
                route.abort()
            else:
                route.fulfill(response=response)

        def lose_put(route):
            if route.request.method != "PUT":
                route.continue_()
                return
            response = route.fetch()
            assert response.status == 200
            put_results.append(response.json())
            route.abort()

        page.context.route(base + staff, lose_metadata)
        page.context.route(base + staff + "/*/source/content", lose_put)
        image_title = "Synthetic sanitized image " + suffix
        page.get_by_role("textbox", name="Media title", exact=True).fill(image_title)
        page.get_by_label("Source file", exact=True).set_input_files(
            {"name": "synthetic-original.png", "mimeType": "image/png", "buffer": png}
        )
        page.get_by_role("button", name="Register and upload", exact=True).click()
        ready(page)
        assert (
            page.get_by_label("Source file", exact=True).evaluate("input => input.files.length")
            == 1
        )
        page.get_by_role("button", name="Retry this registration or upload", exact=True).click()
        ready(page)
        assert len(metadata_requests) == 2 and metadata_requests[0] == metadata_requests[1]
        assert metadata_results[0]["id"] == metadata_results[1]["id"]
        assert len(put_results) == len(actual_puts) == 1
        assert (
            page.get_by_label("Source file", exact=True).evaluate("input => input.files.length")
            == 1
        )
        page.context.unroute(base + staff, lose_metadata)
        page.context.unroute(base + staff + "/*/source/content", lose_put)
        page.get_by_role("button", name="Retry this registration or upload", exact=True).click()
        ready(page)
        assert len(put_results) == len(actual_puts) == 1
        expect(page.get_by_label("Source file", exact=True)).to_have_value("")
        assert (
            page.get_by_label("Source file", exact=True).evaluate("input => input.files.length")
            == 0
        )
        page.get_by_role("textbox", name="Media title", exact=True).fill("Same original file again")
        page.get_by_label("Source file", exact=True).set_input_files(
            {"name": "synthetic-original.png", "mimeType": "image/png", "buffer": png}
        )
        expect(page.get_by_role("button", name="Register and upload", exact=True)).to_be_enabled()
        page.get_by_label("Source file", exact=True).set_input_files([])
        page.get_by_role("textbox", name="Media title", exact=True).fill("")
        image_asset = current(page, metadata_results[0]["id"])
        assert image_asset["source"]["state"] == "quarantined" and image_asset["prepared"] is None
        scan(image_asset["source"]["id"])
        page.get_by_role("button", name="Refresh status", exact=True).click()
        ready(page)
        source = page.request.get(base + staff + f"/{image_asset['id']}/source/content")
        assert source.status == 200 and source.body() == png
        assert source.headers["content-disposition"].startswith("attachment;")
        assert source.headers["cache-control"] == "private, no-store"
        assert source.headers["x-content-type-options"] == "nosniff"
        page.get_by_role(
            "textbox", name="Reason for preparation, publication or revocation", exact=True
        ).fill("Prepare synthetic public copy")
        with page.expect_response(lambda response: response.url.endswith("/prepare")) as prepared:
            page.get_by_role("button", name="Prepare public image", exact=True).click()
        ready(page)
        assert prepared.value.status == 200
        image_asset = prepared.value.json()
        assert image_asset["prepared"]["id"] != image_asset["source"]["id"]
        assert image_asset["prepared"]["state"] == "quarantined" and not image_asset["can_publish"]
        assert page.request.get(base + public_root + f"/{image_asset['id']}/content").status == 404
        candidate = {
            "expected_version": image_asset["version"],
            "expected_file_version": image_asset["prepared"]["version"],
            "reason": "Synthetic direct negative",
        }
        assert mutate(page, staff + f"/{image_asset['id']}/publish", candidate).status == 409
        scan(image_asset["prepared"]["id"], sanitized=True)
        page.get_by_role("button", name="Refresh status", exact=True).click()
        ready(page)
        image_asset = current(page, image_asset["id"])
        reason = page.get_by_role(
            "textbox", name="Reason for preparation, publication or revocation", exact=True
        )
        reason.fill("Keep this reason after stale publication")
        candidate = {
            "expected_version": image_asset["version"],
            "expected_file_version": image_asset["prepared"]["version"],
            "reason": "Synthetic concurrent publication",
        }
        assert mutate(page, staff + f"/{image_asset['id']}/publish", candidate).status == 200
        page.get_by_role("button", name="Publish media", exact=True).click()
        ready(page)
        expect(reason).to_have_value("Keep this reason after stale publication")
        expect(page.locator("main > section > [role=status]")).to_have_text(
            "The record changed. Refresh status and review it before trying again."
        )
        page.get_by_role("button", name="Refresh status", exact=True).click()
        ready(page)
        public_url = base + public_root + f"/{image_asset['id']}/content"
        public_bytes = page.request.get(public_url)
        assert public_bytes.status == 200 and public_bytes.body() != png
        assert public_bytes.headers["content-type"] == "image/png"
        assert public_bytes.headers["content-disposition"].startswith("inline;")
        assert public_bytes.headers["x-content-type-options"] == "nosniff"
        assert "no-store" in public_bytes.headers["cache-control"]
        with Image.open(BytesIO(public_bytes.body())) as sanitized:
            assert sanitized.size == (24, 18) and not sanitized.info.get("SyntheticPrivateMetadata")
        public_context = browser.new_context()
        assert public_context.request.get(public_url).status == 200
        discovered = public_context.request.get(public_api).json()["items"]
        assert len(discovered) == 1 and discovered[0]["id"] == image_asset["id"]
        assert discovered[0]["source"] is None and discovered[0]["prepared"] is None
        responsive(page, "media-en")
        reason.fill("Revoke synthetic publication")
        page.get_by_role("button", name="Revoke public access", exact=True).click()
        ready(page)
        assert public_context.request.get(public_url).status == 404
        assert public_context.request.get(public_api).json()["items"] == []
        assert page.request.get(base + staff + f"/{image_asset['id']}/source/content").status == 200
        page.goto(base + f"/ta/admin/media?organization={org}")
        ready(page)
        expect(page.locator("html")).to_have_attribute("lang", "ta")
        page.get_by_role("button", name="ஊடகத்தைப் பார்க்க: " + image_title, exact=True).click()
        ready(page)
        responsive(page, "media-ta")

        page.goto(base + f"/en/admin/media?organization={org}")
        ready(page)
        clean_pdf = upload(page, "Synthetic clean PDF " + suffix)
        assert clean_pdf.status == 200
        pdf_asset = clean_pdf.json()
        scan(pdf_asset["source"]["id"])
        page.get_by_role("button", name="Refresh status", exact=True).click()
        ready(page)
        reason = page.get_by_role(
            "textbox", name="Reason for preparation, publication or revocation", exact=True
        )
        reason.fill("Publish synthetic PDF download")
        page.get_by_role("button", name="Publish media", exact=True).click()
        ready(page)
        download = public_context.request.get(base + public_root + f"/{pdf_asset['id']}/content")
        assert download.status == 200 and download.body() == pdf
        assert download.headers["content-disposition"].startswith("attachment;")
        assert not any(
            key in download.headers for key in ("set-cookie", "x-bff-key", "authorization")
        )
        assert (
            page.request.get(base + public_root + f"/{pdf_asset['id']}/content?version=1").status
            == 404
        )
        assert page.request.get(base + staff + "?owner=other").status == 400
        assert page.request.get(base + staff.replace(str(org), str(other_org))).status == 403
        assert mutate(page, staff + f"/{pdf_asset['id']}/publish", {}, csrf=False).status == 403
        assert (
            mutate(
                page,
                staff + f"/{pdf_asset['id']}/source/content",
                pdf,
                method="PUT",
                media="application/pdf",
                version=1,
                csrf=False,
            ).status
            == 403
        )
        reader = sign_in(browser, "reader")
        reader.goto(base + f"/en/admin/media?organization={org}")
        ready(reader)
        expect(reader.get_by_role("button", name="Register and upload", exact=True)).to_have_count(
            0
        )
        inspect(reader, "Synthetic clean PDF " + suffix)
        expect(reader.get_by_role("button", name="Revoke public access", exact=True)).to_have_count(
            0
        )
        assert (
            mutate(
                reader,
                staff + f"/{pdf_asset['id']}/revoke",
                {
                    "expected_version": current(reader, pdf_asset["id"])["version"],
                    "reason": "Denied view-only command",
                },
            ).status
            == 403
        )
        no_view = sign_in(browser, "create_only")
        assert no_view.request.get(base + staff).status == 403
        assert (
            mutate(
                no_view,
                staff,
                {
                    "filename": "no-view.pdf",
                    "title": "Denied",
                    "media_type": "application/pdf",
                    "byte_size": len(pdf),
                    "client_request_id": str(uuid4()),
                },
            ).status
            == 403
        )
        outsider = sign_in(browser, "outsider")
        assert (
            outsider.request.get(base + staff + f"/{pdf_asset['id']}/source/content").status == 403
        )
        with Session(engine) as db:
            grant = db.scalar(
                select(UserRole).where(
                    UserRole.user_id == actors["manager"]["id"], UserRole.organization_id == org
                )
            )
            assert grant
            db.delete(grant)
            db.commit()
        assert page.request.get(base + staff + f"/{pdf_asset['id']}/source/content").status == 403
        assert not errors, errors
    except Exception:
        # Synthetic UI only; do not print tokens, request bodies or response headers.
        print("Recent same-origin request outcomes:", list(responses), flush=True)
        for index, context in enumerate(browser.contexts):
            for page_index, failed_page in enumerate(context.pages):
                try:
                    failed_page.screenshot(
                        path=str(evidence / f"cms-files-failure-{index}-{page_index}.png"),
                        full_page=True,
                    )
                except Exception:
                    pass
        raise
    finally:
        browser.close()
        engine.dispose()

print(
    "PASS: CMS real synthetic PDF/image uploads; quarantine/unavailable/checksum rejection; "
    "exact lost metadata and lost PUT recovery; independent sanitized derivative scan; "
    "explicit PDF/image publication, stale reason preservation and public revocation; "
    "unbacked legacy/retired callback; permission/org/CSRF/closed BFF negatives; "
    "EN/TA four-width keyboard/responsive acceptance; no JS errors. "
    "Scanner results were script-only adapters, not live ClamAV."
)
