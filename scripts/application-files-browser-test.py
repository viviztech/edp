"""Synthetic document UI/bytes acceptance; controlled scans are test-script calls only."""

import hashlib
import os
import secrets
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID, uuid4

from playwright.sync_api import expect, sync_playwright
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.applications import document_service as documents
from app.modules.applications import service as applications
from app.modules.applications.document_schemas import DocumentCreate
from app.modules.applications.models import (
    Application,
    ApplicationDocument,
    ApplicationDocumentEvidence,
)
from app.modules.applications.schemas import DefinitionCreate
from app.modules.files import service as files
from app.modules.files.models import FileObject
from app.modules.files.runtime import get_private_storage
from app.modules.files.scanner import ScanResult
from app.modules.files.schemas import FilePolicyCommand, FilePolicyCreate
from app.modules.identity.models import Organization, Person, Role, User, UserRole, now
from app.modules.identity.security import hasher
from app.modules.identity.service import seed_roles
from app.modules.programs.models import ApplicationCycle, Program
from app.modules.selection.models import ReviewAssignment, SelectionCycle, SelectionRubric

engine = create_engine(os.environ["DATABASE_URL"])
assert engine.url.database == "edp_application_files_e2e"
assert engine.url.host in {"127.0.0.1", "localhost"}
base, api = os.environ["WEB_ORIGIN"], os.environ["API_INTERNAL_URL"]
assert urlparse(base).hostname == urlparse(api).hostname == "127.0.0.1"
assert urlparse(base).port == 3108 and urlparse(api).port == 8108
settings = get_settings()
assert settings.files_enabled and not settings.files_maintenance_enabled
assert settings.files_storage_backend == "local" and settings.files_max_bytes == 2048
assert settings.clamav_host is None
org = UUID(os.environ["PUBLIC_ORGANIZATION_ID"])
suffix = uuid4().hex[:12]
content = b"Synthetic local application file only.\n"
digest = hashlib.sha256(content).hexdigest()
actors = {
    key: {
        "name": f"Synthetic file {key} {suffix}",
        "email": f"file-{key}-{suffix}@example.com",
        "password": secrets.token_urlsafe(24),
    }
    for key in ("director", "owner", "peer", "reviewer", "unassigned")
}
with Session(engine) as db:
    seed_roles(db)
    db.add(Organization(id=org, name="Synthetic application files " + suffix))
    other = Organization(name="Synthetic other files " + suffix)
    db.add(other)
    db.flush()
    for key, credentials in actors.items():
        person = Person(display_name=credentials["name"])
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
        credentials["id"] = user.id
        role_name = (
            "Program Director"
            if key == "director"
            else "Selection Committee"
            if key in {"reviewer", "unassigned"}
            else None
        )
        if role_name:
            role = db.scalar(select(Role).where(Role.name == role_name))
            assert role
            db.add(UserRole(user_id=user.id, role_id=role.id, organization_id=org))
    db.commit()
    director = db.get(User, actors["director"]["id"])
    assert director
    policy = files.create_policy(
        db,
        org,
        director,
        FilePolicyCreate(
            client_request_id=uuid4(),
            purpose="application_document",
            name="Synthetic application file rules " + suffix,
            notice_en="Synthetic local acceptance notice only",
            notice_ta="செயற்கை உள்ளூர் சோதனை அறிவிப்பு மட்டும்",
            allowed_mime_types=["text/plain"],
            max_file_bytes=4096,
            max_files=2,
            retention_days=30,
            rejected_retention_days=3,
            allow_frozen_disposal=False,
            reason="Synthetic test configuration",
        ),
        "browser-policy-create",
    )
    policy = files.publish_policy(
        db,
        org,
        policy.id,
        director,
        FilePolicyCommand(
            expected_version=policy.version, reason="Publish synthetic configuration only"
        ),
        "browser-policy-publish",
    )
    definition = applications.create_definition(
        db,
        org,
        director,
        DefinitionCreate(
            title_en="Synthetic file form " + suffix,
            title_ta="செயற்கைக் கோப்புப் படிவம் " + suffix,
            fields=[
                {
                    "key": "proposal",
                    "section": "general",
                    "label_en": "Synthetic proposal",
                    "label_ta": "செயற்கைத் திட்டம்",
                    "field_type": "text",
                    "required": True,
                }
            ],
            acknowledgements=[
                {
                    "key": "declaration",
                    "kind": "declaration",
                    "label_en": "Synthetic declaration only",
                    "label_ta": "செயற்கை அறிவிப்பு மட்டும்",
                    "required": True,
                },
                {
                    "key": "consent",
                    "kind": "consent",
                    "label_en": "Synthetic consent only",
                    "label_ta": "செயற்கை ஒப்புதல் மட்டும்",
                    "required": True,
                },
            ],
        ),
        "browser-definition-create",
    )
    other_org = other.id

evidence = Path(".tool-cache/evidence")
evidence.mkdir(parents=True, exist_ok=True)
errors = []


class ControlledScanner:
    """Only this script injects a fixed result after reading the synthetic exact bytes."""

    def __init__(self, status):
        self.status = status

    def scan(self, source, *, max_bytes):
        value = source.read(max_bytes + 1)
        assert value == content and len(value) <= max_bytes
        return ScanResult(
            self.status, hashlib.sha256(value).hexdigest(), len(value), "synthetic-test-result"
        )


def scan(file_id, status):
    with Session(engine) as db:
        row = db.get(FileObject, UUID(file_id))
        assert row and row.organization_id == org
        assert row.purpose == "application_document" and row.expected_sha256 == digest
        lease = files.claim_scan(db, org, row.id, "browser-controlled-scan")
        result = files.scan_with_lease(
            db,
            org,
            lease,
            get_private_storage(),
            ControlledScanner(status),
            "browser-controlled-result",
        )
        assert result.state == ("quarantined" if status == "error" else status)
        return result


def sign_in(browser, key):
    page = browser.new_context(viewport={"width": 1280, "height": 900}).new_page()
    page.on("pageerror", lambda error: errors.append(type(error).__name__))
    page.goto(base + "/en/account")
    page.get_by_role("textbox", name="Email", exact=True).fill(actors[key]["email"])
    page.get_by_label("Password", exact=True).fill(actors[key]["password"])
    page.locator("form").get_by_role("button", name="Sign in", exact=True).click()
    expect(page.get_by_text(actors[key]["name"], exact=True)).to_be_visible()
    return page


def responsive(page, label):
    for width in (360, 390, 768, 1280):
        page.set_viewport_size({"width": width, "height": 900})
        if not page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"):
            page.screenshot(
                path=str(evidence / f"application-files-{label}-{width}-overflow.png"),
                full_page=True,
            )
            overflowing = page.evaluate("""() => Array.from(document.querySelectorAll('main *'))
              .filter(el => el.getBoundingClientRect().right > innerWidth + 1)
              .map(el => ({tag: el.tagName, class: el.className,
                right: Math.round(el.getBoundingClientRect().right)})).slice(0, 15)""")
            raise AssertionError(f"{label} at {width}px overflows: {overflowing}")
        page.locator("a.skip").focus()
        page.keyboard.press("Enter")
        assert page.evaluate("document.activeElement.id") == "main"
        page.screenshot(
            path=str(evidence / f"application-files-{label}-{width}.png"), full_page=True
        )


def mutate(
    page, method, path, data, media="application/json", csrf=True, origin=None, version=None
):
    headers = {"Origin": origin or base, "Content-Type": media}
    if csrf:
        headers["X-CSRF-Token"] = page.request.get(base + "/api/session/csrf").json()["csrf_token"]
    if version:
        headers["If-Match"] = f'"{version}"'
    return page.request.fetch(base + path, method=method, data=data, headers=headers)


def ready(page):
    expect(page.locator(".application-workspace")).to_have_attribute("aria-busy", "false")
    expect(page.locator(".application-documents")).to_have_attribute("aria-busy", "false")


def pick(page, *, replacement=False, value=content):
    page.get_by_role(
        "button", name="Replace document" if replacement else "Upload document", exact=True
    ).click()
    page.get_by_label("Choose a file", exact=True).set_input_files(
        {"name": "synthetic-file.txt", "mimeType": "text/plain", "buffer": value}
    )


def upload(page, *, replacement=False):
    pick(page, replacement=replacement)
    with page.expect_response(
        lambda response: response.request.method == "PUT" and response.url.endswith("/content")
    ) as completed:
        page.get_by_role("button", name="Upload selected file", exact=True).click()
    assert completed.value.status == 200
    ready(page)
    return completed.value.json()["document"]


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel=os.getenv("PLAYWRIGHT_CHANNEL"), headless=True)
    try:
        director = sign_in(browser, "director")
        definitions = f"/api/application-definitions/organizations/{org}/definitions"
        director.goto(base + f"/en/admin/application-definitions?organization={org}")
        expect(director.locator(".definition-workspace")).to_have_attribute("aria-busy", "false")
        director.get_by_role("button", name="Add document requirement", exact=True).click()
        for name in ("Minimum files", "Maximum files"):
            expect(director.get_by_role("spinbutton", name=name, exact=True)).to_have_value("")
        for name, value in (
            ("English document label", "Synthetic supporting evidence"),
            ("Tamil document label", "செயற்கை ஆதார ஆவணம்"),
            ("English instructions", "Synthetic local document instructions only"),
            ("Tamil instructions", "செயற்கை உள்ளூர் ஆவண வழிமுறைகள் மட்டும்"),
        ):
            director.get_by_role("textbox", name=name, exact=True).fill(value)
        director.get_by_role(
            "combobox", name="Published file policy edition", exact=True
        ).select_option(str(policy.id))
        director.get_by_role("spinbutton", name="Minimum files", exact=True).fill("1")
        director.get_by_role("spinbutton", name="Maximum files", exact=True).fill("2")
        responsive(director, "definition-en")
        director.get_by_role("button", name="Save draft", exact=True).click()
        expect(director.get_by_role("status")).to_have_text("Draft saved.")
        director.goto(base + f"/ta/admin/application-definitions?organization={org}")
        expect(director.locator("html")).to_have_attribute("lang", "ta")
        expect(director.get_by_role("textbox", name="தமிழ் ஆவணப் பெயர்", exact=True)).to_have_value(
            "செயற்கை ஆதார ஆவணம்"
        )
        responsive(director, "definition-ta")
        director.goto(base + f"/en/admin/application-definitions?organization={org}")
        expect(director.locator(".definition-workspace")).to_have_attribute("aria-busy", "false")
        director.once("dialog", lambda dialog: dialog.accept())
        director.get_by_role("button", name="Publish version", exact=True).click()
        expect(director.get_by_role("status")).to_have_text("Definition published.")
        published = director.request.get(base + definitions + "/" + str(definition.id)).json()
        assert (
            published["state"] == "published"
            and published["document_requirements"][0]["min_files"] == 1
        )
        rule = published["document_requirements"][0]
        assert (
            rule["file_policy"]["max_upload_bytes"] == 2048
            and published["max_upload_bytes"] == 2048
        )
        with Session(engine) as db:
            program = Program(
                organization_id=org,
                code="files-" + suffix,
                name_en="Synthetic file program",
                name_ta="செயற்கைக் கோப்புத் திட்டம்",
                state="active",
            )
            db.add(program)
            db.flush()
            cycle = ApplicationCycle(
                organization_id=org,
                program_id=program.id,
                form_id=definition.id,
                code="files-" + suffix,
                name_en="Synthetic file intake",
                name_ta="செயற்கைக் கோப்புச் சேர்க்கை",
                state="open",
                opens_at=now() - timedelta(days=1),
                closes_at=now() + timedelta(days=10),
            )
            db.add(cycle)
            db.commit()
            cycle_id = cycle.id
        owner = sign_in(browser, "owner")
        destination = f"/en/applications?organization={org}&cycle={cycle_id}"
        owner.goto(base + destination)
        owner.get_by_role("button", name="Start application", exact=True).click()
        expect(
            owner.get_by_role("textbox", name="Synthetic proposal *", exact=True)
        ).to_be_visible()
        owner.get_by_role("textbox", name="Synthetic proposal *", exact=True).fill(
            "Synthetic proposal retained through file changes"
        )
        expect(owner.get_by_role("button", name="Upload document", exact=True)).to_be_disabled()
        owner.get_by_role("button", name="Save draft", exact=True).click()
        expect(owner.locator(".application-message")).to_have_text("Draft saved.")
        ready(owner)
        current = owner.request.get(
            base + f"/api/applications/organizations/{org}/cycles/{cycle_id}/application"
        ).json()
        app_id = current["id"]
        docs = f"/api/applications/organizations/{org}/applications/{app_id}/documents"
        expect(owner.locator(".application-documents")).to_contain_text("2048")
        pick(owner, value=b"a" * 2049)
        owner.get_by_role("button", name="Upload selected file", exact=True).click()
        expect(owner.locator(".application-documents [role=status]")).to_have_text(
            "Choose a nonempty file in an allowed format and within the displayed size limit."
        )
        assert owner.request.get(base + docs).json()["items"] == []
        creations, registered, puts = [], [], []

        def lost_registration(route):
            if route.request.method != "POST":
                route.continue_()
                return
            creations.append(route.request.post_data_json)
            response = route.fetch()
            assert response.status == 201
            registered.append(response.json())
            if len(creations) == 1:
                route.abort()
            else:
                route.fulfill(response=response)

        owner.context.route(base + docs, lost_registration)
        pick(owner)
        owner.get_by_role("button", name="Upload selected file", exact=True).click()
        owner.get_by_role(
            "button", name="Recover the same document registration", exact=True
        ).click()
        expect(
            owner.get_by_role("button", name="Continue this registered upload", exact=True)
        ).to_be_visible()
        assert len(creations) == 2 and creations[0] == creations[1]
        assert registered[0]["document"]["id"] == registered[1]["document"]["id"]
        assert "name" not in creations[0] and creations[0]["sha256"] == digest
        owner.context.unroute(base + docs, lost_registration)
        with owner.expect_response(
            lambda response: response.request.method == "PUT" and response.url.endswith("/content")
        ) as completed:
            owner.get_by_role("button", name="Continue this registered upload", exact=True).click()
        assert completed.value.status == 200
        first = completed.value.json()["document"]
        ready(owner)
        expect(owner.locator(".application-documents")).to_contain_text("Awaiting scan")
        expect(owner.get_by_role("button", name="Submit application", exact=True)).to_be_disabled()
        assert owner.request.get(base + docs + "/" + first["id"] + "/content").status == 409
        assert scan(first["file"]["id"], "error").failure_code == "scan_unavailable"
        owner.get_by_role("button", name="Refresh document status", exact=True).click()
        ready(owner)
        expect(owner.locator(".application-documents")).to_contain_text("Awaiting scan")
        infected = upload(owner, replacement=True)
        scan(infected["file"]["id"], "infected")
        owner.get_by_role("button", name="Refresh document status", exact=True).click()
        ready(owner)
        expect(owner.locator(".application-documents")).to_contain_text("Unsafe file")
        expect(owner.locator(".application-documents a[download]")).to_have_count(0)
        owner.once("dialog", lambda dialog: dialog.accept())
        owner.get_by_role("button", name="Remove document", exact=True).click()
        ready(owner)
        expect(owner.locator(".application-documents li")).to_have_count(0)

        def lost_upload(route):
            if route.request.method != "PUT":
                route.continue_()
                return
            response = route.fetch()
            assert response.status == 200
            puts.append(response.json())
            route.abort()

        owner.context.route(base + docs + "/*/content", lost_upload)
        pick(owner)
        owner.get_by_role("button", name="Upload selected file", exact=True).click()
        owner.get_by_role("button", name="Read current document", exact=True).click()
        ready(owner)
        assert len(puts) == 1
        active = puts[0]["document"]
        owner.context.unroute(base + docs + "/*/content", lost_upload)
        scan(active["file"]["id"], "clean")
        owner.get_by_role("button", name="Refresh document status", exact=True).click()
        ready(owner)
        expect(owner.locator(".application-documents")).to_contain_text("Verified clean")
        source = owner.request.get(base + docs + "/" + active["id"] + "/content")
        assert source.status == 200 and source.body() == content
        assert source.headers["cache-control"] == "private, no-store"
        assert source.headers["content-disposition"].startswith("attachment;")
        assert source.headers["x-content-type-options"] == "nosniff"
        assert "storage_key" not in owner.request.get(base + docs).text()
        # Historical expiry is seeded at creation, never by rewriting protected retention.
        # This script-only clock controls the new fixture's initial timestamp; the API
        # process clock and all immutable identity/lease/evidence guards remain unchanged.
        with Session(engine) as db:
            actor = db.get(User, actors["owner"]["id"])
            assert actor
            app = db.get(Application, UUID(app_id))
            assert app
            real_file_now = files.now
            try:
                files.now = lambda: now() - timedelta(days=31)
                expired = documents.create_document(
                    db,
                    org,
                    app.id,
                    actor,
                    DocumentCreate(
                        expected_version=app.version,
                        client_request_id=uuid4(),
                        requirement_id=UUID(rule["id"]),
                        media_type="text/plain",
                        byte_size=len(content),
                        sha256=digest,
                        replaces_document_id=UUID(active["id"]),
                    ),
                    "browser-historical-expiry-intent",
                ).document
            finally:
                files.now = real_file_now
            context = files.AuthorizedFileContext(
                actor.id, org, actor.person_id, "application_document", expired.id
            )
            lease = files.begin_upload(
                db,
                context,
                actor,
                expired.file.id,
                expired.file.version,
                "browser-historical-upload",
            )
            files.receive_upload(
                db,
                context,
                actor,
                lease,
                BytesIO(content),
                get_private_storage(),
                "browser-historical-upload-result",
            )
            assert expired.file.retention_until < now()
        scan(str(expired.file.id), "clean")
        active = {"id": str(expired.id)}
        owner.reload()
        ready(owner)
        expect(owner.locator(".application-documents")).to_contain_text(
            "This evidence is unavailable under the current retention or file rules."
        )
        expect(owner.get_by_role("button", name="Submit application", exact=True)).to_be_disabled()
        assert owner.request.get(base + docs + "/" + active["id"] + "/content").status == 409
        app = owner.request.get(
            base + f"/api/applications/organizations/{org}/cycles/{cycle_id}/application"
        ).json()
        assert (
            mutate(
                owner,
                "POST",
                f"/api/applications/organizations/{org}/draft/{app_id}/submit",
                {
                    "expected_version": app["version"],
                    "accepted_acknowledgement_ids": [
                        item["id"] for item in app["form"]["acknowledgements"]
                    ],
                },
            ).status
            == 422
        )
        final = upload(owner, replacement=True)
        scan(final["file"]["id"], "clean")
        owner.get_by_role("button", name="Refresh document status", exact=True).click()
        ready(owner)
        expect(owner.locator(".application-documents")).to_contain_text("Verified clean")
        expect(owner.get_by_role("textbox", name="Synthetic proposal *", exact=True)).to_have_value(
            "Synthetic proposal retained through file changes"
        )
        responsive(owner, "applicant-en")
        owner.get_by_role("button", name="Submit application", exact=True).click()
        expect(owner.locator(".application-message")).to_have_text(
            "Accept the required declarations and consent before submitting."
        )
        for name in ("Synthetic declaration only", "Synthetic consent only"):
            owner.get_by_role("checkbox", name=name + " (Required)", exact=True).check()
        owner.once("dialog", lambda dialog: dialog.accept())
        owner.get_by_role("button", name="Submit application", exact=True).click()
        expect(owner.locator(".application-receipt")).to_contain_text("Application number")
        receipt = owner.request.get(base + docs).json()
        assert len(receipt["items"]) == 1
        saved = receipt["items"][0]
        assert saved["submitted_evidence"]["sha256"] == digest and saved["usable"]
        assert (
            mutate(
                owner,
                "POST",
                docs,
                {
                    **creations[0],
                    "client_request_id": str(uuid4()),
                    "expected_version": receipt["application_version"],
                },
            ).status
            == 409
        )
        assert (
            mutate(
                owner,
                "PUT",
                docs + "/" + saved["id"] + "/content",
                content,
                media="text/plain",
                version=saved["file"]["version"],
            ).status
            == 409
        )
        owner.goto(base + destination.replace("/en/", "/ta/"))
        expect(owner.locator("html")).to_have_attribute("lang", "ta")
        expect(owner.get_by_role("heading", name="செயற்கை ஆதார ஆவணம்", exact=True)).to_be_visible()
        expect(owner.locator(".application-documents input[type=file]")).to_have_count(0)
        responsive(owner, "receipt-ta")
        peer = sign_in(browser, "peer")
        assert peer.request.get(base + docs).status == 404
        assert peer.request.get(base + docs + "/" + saved["id"] + "/content").status == 404
        assert owner.request.get(base + docs.replace(str(org), str(other_org))).status == 404
        assert owner.request.get(base + docs + "?owner=other").status == 400
        assert (
            owner.request.get(base + docs + "/" + saved["id"] + "/content?version=1").status == 400
        )
        assert mutate(owner, "POST", docs + "/" + saved["id"] + "/scan", {}).status == 404
        assert (
            mutate(
                owner,
                "PUT",
                docs + "/" + saved["id"] + "/content",
                content,
                media="text/plain",
                version=1,
                csrf=False,
            ).status
            == 403
        )
        assert (
            mutate(
                owner,
                "PUT",
                docs + "/" + saved["id"] + "/content",
                content,
                media="text/plain",
                version=1,
                origin="https://unrelated.example",
            ).status
            == 403
        )
        with Session(engine) as db:
            selection = SelectionCycle(
                organization_id=org,
                application_cycle_id=cycle_id,
                code="review-" + suffix,
                name_en="Synthetic file review",
                name_ta="செயற்கைக் கோப்பு மதிப்பாய்வு",
                state="active",
            )
            db.add(selection)
            db.flush()
            rubric = SelectionRubric(
                organization_id=org,
                selection_cycle_id=selection.id,
                version_number=1,
                state="published",
                published_at=now(),
            )
            db.add(rubric)
            db.flush()
            assignment = ReviewAssignment(
                organization_id=org,
                selection_cycle_id=selection.id,
                rubric_id=rubric.id,
                application_id=UUID(app_id),
                reviewer_user_id=actors["reviewer"]["id"],
                status="in_review",
                conflict_status="clear",
            )
            db.add(assignment)
            db.commit()
            assignment_id = assignment.id
        reviewer = sign_in(browser, "reviewer")
        reviewer.goto(base + f"/en/admin/selection?organization={org}")
        reviewer.get_by_role(
            "button", name="Read assigned application documents", exact=True
        ).click()
        expect(reviewer.locator(".reviewer-documents")).to_contain_text(
            "Synthetic supporting evidence"
        )
        review_path = f"/api/selection/organizations/{org}/assignments/{assignment_id}/documents"
        delivered = reviewer.request.get(base + review_path + "/" + saved["id"] + "/content")
        assert delivered.status == 200 and delivered.body() == content
        assert "Synthetic proposal retained" not in reviewer.request.get(base + review_path).text()
        responsive(reviewer, "reviewer-en")
        reviewer.goto(base + f"/ta/admin/selection?organization={org}")
        reviewer.get_by_role("button", name="ஒதுக்கப்பட்ட விண்ணப்ப ஆவணங்களைப் படி", exact=True).click()
        expect(reviewer.locator(".reviewer-documents")).to_contain_text("செயற்கை ஆதார ஆவணம்")
        responsive(reviewer, "reviewer-ta")
        unassigned = sign_in(browser, "unassigned")
        assert unassigned.request.get(base + review_path).status == 404
        with Session(engine) as db:
            row = db.get(ReviewAssignment, assignment_id)
            assert row
            row.conflict_status = "conflict"
            row.conflict_note = "Synthetic access revocation"
            row.version += 1
            db.commit()
        assert (
            reviewer.request.get(base + review_path + "/" + saved["id"] + "/content").status == 404
        )
        reviewer.get_by_role("button", name="ஆவண நிலையைப் புதுப்பி", exact=True).click()
        expect(reviewer.locator(".reviewer-documents a")).to_have_count(0)
        with Session(engine) as db:
            row = db.get(ReviewAssignment, assignment_id)
            assert row
            row.conflict_status = "clear"
            row.conflict_note = None
            row.version += 1
            grant = db.scalar(
                select(UserRole).where(
                    UserRole.user_id == actors["reviewer"]["id"], UserRole.organization_id == org
                )
            )
            assert grant
            db.delete(grant)
            db.commit()
        assert reviewer.request.get(base + review_path).status == 403
        with Session(engine) as db:
            app = db.get(Application, UUID(app_id))
            assert app and app.state == "submitted"
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(ApplicationDocumentEvidence)
                    .where(ApplicationDocumentEvidence.application_id == app.id)
                )
                == 1
            )
            historical = list(
                db.scalars(
                    select(ApplicationDocument).where(ApplicationDocument.application_id == app.id)
                )
            )
            assert len(historical) == 5 and sum(item.removed_at is None for item in historical) == 1
        assert not errors, errors
    finally:
        browser.close()
        engine.dispose()

print(
    "PASS: explicit EN/TA document requirements; operational limit; "
    "exact lost-registration recovery; verified upload; unavailable/infected/expired negatives; "
    "immutable replacement/removal; lost-PUT read reconciliation; frozen submission receipt; "
    "owner/peer/org/reviewer/revoked access; CSRF and closed BFF; "
    "EN/TA four-width keyboard/responsive acceptance; no JS errors. "
    "Scans used controlled test-script adapters, not live ClamAV."
)
