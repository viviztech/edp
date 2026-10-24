"""Secure helpdesk synthetic acceptance; controlled fixture scans only, no provider activation."""

import hashlib
import os
import secrets
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID, uuid4

from playwright.sync_api import expect, sync_playwright
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.applications.models import Application, ApplicationForm
from app.modules.files import service as files
from app.modules.files.runtime import get_private_storage
from app.modules.files.scanner import ScanResult
from app.modules.files.schemas import FilePolicyCommand, FilePolicyCreate
from app.modules.helpdesk.file_models import HelpdeskFile
from app.modules.identity.models import (
    Organization,
    Person,
    Role,
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

engine = create_engine(os.environ["DATABASE_URL"])
assert engine.url.database == "edp_helpdesk_files_e2e"
assert engine.url.host in {"127.0.0.1", "localhost"}
base = os.environ["WEB_ORIGIN"]
api = os.environ["API_INTERNAL_URL"]
assert base.startswith(("http://127.0.0.1:", "http://localhost:"))
assert api.startswith(("http://127.0.0.1:", "http://localhost:"))
org_id = UUID(os.environ["PUBLIC_ORGANIZATION_ID"])
suffix = uuid4().hex[:12]
today = now().date()
actors = {
    key: {
        "email": f"s01-{key}-{suffix}@example.com",
        "password": secrets.token_urlsafe(24),
    }
    for key in (
        "staff",
        "admin",
        "owner",
        "peer",
        "unassigned",
        "unenrolled",
        "outsider",
    )
}

# Seed only identity and a real active enrollment. All helpdesk content and
# participant actions below go through the running application, not SQL fixtures.
with Session(engine) as db:
    seed_roles(db)
    org = Organization(id=org_id, name="Synthetic helpdesk organization " + suffix)
    other = Organization(name="Synthetic unrelated helpdesk organization " + suffix)
    db.add_all([org, other])
    db.flush()
    other_org_id = other.id
    for key, credentials in actors.items():
        person = Person(display_name="Synthetic S01 " + key)
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
                == (
                    "Program Manager"
                    if key == "admin"
                    else "Support Executive"
                    if key in {"staff", "unassigned", "outsider"}
                    else "Participant"
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
        code="helpdesk",
        name_en="Synthetic helpdesk program",
        name_ta="செயற்கை அறிவு திட்டம்",
        state="active",
    )
    center = TrainingCenter(
        organization_id=org.id,
        code="helpdesk-center",
        name_en="Synthetic helpdesk center",
        name_ta="செயற்கை பயிற்சி மையம்",
        locality="Synthetic locality",
    )
    form = ApplicationForm(
        organization_id=org.id,
        version=1,
        state="published",
        title_en="Synthetic helpdesk intake",
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
        code="helpdesk-cohort",
        name_en="Synthetic helpdesk cohort",
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
        code="helpdesk-cycle",
        name_en="Synthetic helpdesk cycle",
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
            application_number=f"S01-{key}-{suffix}",
            submitted_at=now() - timedelta(days=20),
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
            cohort_id=cohort.id,
            application_id=application.id,
            status="active",
        )
        db.add(enrollment)
        db.flush()
        actors[key]["enrollment_id"] = enrollment.id
    db.commit()

# Only this guarded synthetic child supplies a controlled scan verdict. The
# running API has no fake-clean mode, scanner connection or provider activation.
settings = get_settings()
assert settings.files_enabled and not settings.files_maintenance_enabled
assert settings.files_storage_backend == "local" and settings.files_max_bytes == 2048
assert settings.clamav_host is None
assert urlparse(base).port == 3109 and urlparse(api).port == 8109
with Session(engine) as db:
    administrator = db.get(User, actors["admin"]["user_id"])
    director = db.scalar(select(Role).where(Role.name == "Program Director"))
    db.add(UserRole(user_id=administrator.id, role_id=director.id, organization_id=org_id))
    db.commit()
    policy = files.create_policy(
        db,
        org_id,
        administrator,
        FilePolicyCreate(
            client_request_id=uuid4(),
            purpose="helpdesk_attachment",
            name="Synthetic secure support policy",
            notice_en="Synthetic support files only. No real personal information.",
            notice_ta="செயற்கை உதவிக் கோப்புகள் மட்டும். உண்மையான தனிப்பட்ட தகவல்கள் வேண்டாம்.",
            allowed_mime_types=["application/pdf", "text/plain"],
            max_file_bytes=1024,
            max_files=3,
            retention_days=1,
            rejected_retention_days=1,
            allow_frozen_disposal=False,
            reason="Synthetic acceptance fixture",
        ),
        "browser-policy",
    )
    files.publish_policy(
        db,
        org_id,
        policy.id,
        administrator,
        FilePolicyCommand(expected_version=1, reason="Synthetic fixture only"),
        "browser-policy-publish",
    )

helpdesk_root = f"{base}/api/helpdesk/organizations/{org_id}"
content = b"%PDF-1.4\nSynthetic secure helpdesk evidence only.\n%%EOF"
private_content = b"%PDF-1.4\nSynthetic staff-only escalation evidence.\n%%EOF"
errors = []
evidence = Path(".tool-cache/evidence")
evidence.mkdir(parents=True, exist_ok=True)


def sign_in(browser, key):
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(base + "/en/account")
    page.get_by_label("Email", exact=True).fill(actors[key]["email"])
    page.get_by_label("Password", exact=True).fill(actors[key]["password"])
    with page.expect_response(
        lambda response: response.url.endswith("/api/session/login")
    ) as result:
        page.locator("form").get_by_role("button", name="Sign in", exact=True).click()
    assert result.value.status == 200
    expect(page.get_by_text("Synthetic S01 " + key, exact=True)).to_be_visible()
    return page


def mutate(page, path, data):
    csrf = page.request.get(base + "/api/session/csrf").json()["csrf_token"]
    return page.request.post(
        helpdesk_root + path, data=data, headers={"Origin": base, "X-CSRF-Token": csrf}
    )


def detail(page, ticket_id):
    response = page.request.get(helpdesk_root + "/tickets/" + ticket_id)
    assert response.status == 200, response.text()
    return response.json()


def open_ticket(page, ticket):
    page.get_by_role("button", name=f"{ticket['number']}: {ticket['subject']}", exact=True).click()
    return page.get_by_role("region", name="Ticket details", exact=True)


class SyntheticScanner:
    def scan(self, source, *, max_bytes):
        data = source.read(max_bytes + 1)
        assert data in {content, private_content}
        return ScanResult(
            "clean",
            hashlib.sha256(data).hexdigest(),
            len(data),
            "synthetic_browser_fixture",
        )


def clean(binding_id):
    with Session(engine) as db:
        binding = db.get(HelpdeskFile, UUID(binding_id))
        assert binding.organization_id == org_id
        lease = files.claim_scan(db, org_id, binding.file_id, "synthetic-browser-claim")
        result = files.scan_with_lease(
            db,
            org_id,
            lease,
            get_private_storage(),
            SyntheticScanner(),
            "synthetic-browser-scan",
        )
        assert result.state == "clean"


def current_files(page, ticket):
    response = page.request.get(helpdesk_root + f"/tickets/{ticket['id']}/files?limit=25")
    assert response.status == 200, response.text()
    assert "object_key" not in response.text() and "storage_version" not in response.text()
    return response.json()["items"]


def upload(page, region, data, name):
    region.get_by_label("Choose a secure file", exact=True).set_input_files(
        {"name": name, "mimeType": "application/pdf", "buffer": data}
    )
    with page.expect_response(
        lambda response: (
            "/files/" in response.url
            and response.url.endswith("/content")
            and response.request.method == "PUT"
        )
    ) as result:
        region.get_by_role("button", name="Upload private file", exact=True).click()
    assert result.value.status == 200, result.value.text()
    expect(region.get_by_text("Quarantined", exact=False)).to_be_visible()


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel=os.getenv("PLAYWRIGHT_CHANNEL"), headless=True)
    owner = sign_in(browser, "owner")
    admin = sign_in(browser, "admin")
    owner.goto(base + f"/en/helpdesk?organization={org_id}")
    create = owner.get_by_role("region", name="Create ticket", exact=True)
    create.get_by_label("Subject", exact=True).fill("Synthetic secure file support " + suffix)
    create.get_by_label("Description", exact=True).fill(
        "Synthetic helpdesk acceptance, no real personal details."
    )
    create.get_by_label("Text attachments", exact=True).set_input_files(
        {
            "name": "legacy.txt",
            "mimeType": "text/plain",
            "buffer": b"Synthetic legacy text compatibility.",
        }
    )
    expect(create.get_by_text("Selected files: legacy.txt", exact=True)).to_be_visible()
    with owner.expect_response(
        lambda response: (
            response.url == helpdesk_root + "/tickets" and response.request.method == "POST"
        )
    ) as created:
        create.get_by_role("button", name="Create ticket", exact=True).click()
    assert created.value.status == 201, created.value.text()
    ticket = created.value.json()
    ticket_path = f"/tickets/{ticket['id']}"
    owner_detail = owner.get_by_role("region", name="Ticket details", exact=True)
    secure = owner_detail.get_by_role("region", name="Secure attachments", exact=True)
    expect(
        secure.get_by_text(
            "Synthetic support files only. No real personal information.", exact=False
        )
    ).to_be_visible()
    upload(owner, secure, content, "owner-evidence.pdf")
    staged = current_files(owner, ticket)[0]
    assert (
        not staged["internal"] and not staged["usable"] and staged["file"]["state"] == "quarantined"
    )
    binding = staged["id"]
    file_url = helpdesk_root + ticket_path + f"/files/{binding}/content"
    assert owner.request.get(file_url).status == 409
    expect(
        secure.get_by_role("checkbox", name="Attach this clean file 1", exact=True)
    ).to_be_disabled()
    denied = mutate(
        owner,
        ticket_path + "/files",
        {
            "client_request_id": str(uuid4()),
            "policy_id": staged["policy"]["id"],
            "internal": True,
            "media_type": "application/pdf",
            "byte_size": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        },
    )
    assert denied.status == 403
    clean(binding)
    secure.get_by_role("button", name="Refresh file status", exact=True).click()
    selection = secure.get_by_role("checkbox", name="Attach this clean file 1", exact=True)
    expect(selection).to_be_enabled()
    selection.check()
    # A legitimate concurrent assignment advances the ticket version. Reply text
    # and the staged clean selection must survive the explicit refresh/review.
    assigned = mutate(
        admin,
        ticket_path + "/assignment",
        {
            "expected_version": ticket["version"],
            "assignee_user_id": str(actors["staff"]["user_id"]),
            "reason": "Synthetic support routing",
        },
    )
    assert assigned.status == 200, assigned.text()
    reply = owner_detail.get_by_role("form", name="Reply", exact=True)
    owner.get_by_role("textbox", name="Reply", exact=True).fill(
        "Synthetic shared reply with exact clean evidence."
    )
    with owner.expect_response(
        lambda response: (
            response.url.endswith(ticket_path + "/messages") and response.request.method == "POST"
        )
    ) as stale:
        reply.get_by_role("button", name="Send reply", exact=True).click()
    assert stale.value.status == 409
    expect(owner.get_by_role("textbox", name="Reply", exact=True)).to_have_value(
        "Synthetic shared reply with exact clean evidence."
    )
    owner_detail.get_by_role("button", name="Refresh ticket", exact=True).click()
    expect(
        owner.get_by_text(
            "Latest ticket loaded. Review the conversation before submitting.",
            exact=True,
        )
    ).to_be_visible()
    expect(
        secure.get_by_role("checkbox", name="Attach this clean file 1", exact=True)
    ).to_be_checked()
    with owner.expect_response(
        lambda response: (
            response.url.endswith(ticket_path + "/messages") and response.request.method == "POST"
        )
    ) as posted:
        reply.get_by_role("button", name="Send reply", exact=True).click()
    assert posted.value.status == 200, posted.value.text()
    assert posted.value.request.post_data_json["file_ids"] == [binding]
    conversation = owner_detail.get_by_role("region", name="Conversation", exact=True)
    with owner.expect_download() as download:
        conversation.get_by_role("link", name="Download attached file 1", exact=True).click()
    assert Path(download.value.path()).read_bytes() == content
    with owner.expect_download() as download:
        conversation.get_by_role("link", name="Download: legacy.txt", exact=True).click()
    assert Path(download.value.path()).read_bytes() == b"Synthetic legacy text compatibility."

    staff = sign_in(browser, "staff")
    staff.goto(base + f"/en/admin/helpdesk?organization={org_id}")
    staff_detail = open_ticket(staff, ticket)
    staff_reply = staff_detail.get_by_role("form", name="Reply", exact=True)
    staff_reply.get_by_label("Internal note", exact=True).check()
    private_region = staff_reply.get_by_role("region", name="Secure attachments", exact=True)
    pattern = f"**/api/helpdesk/organizations/{org_id}/tickets/{ticket['id']}/files/*/content"
    put_count = [0]

    def lost_response(route):
        if route.request.method != "PUT":
            route.continue_()
            return
        put_count[0] += 1
        response = route.fetch()
        assert response.status == 200, response.text()
        route.abort("failed")

    staff.route(pattern, lost_response)
    private_region.get_by_label("Choose a secure file", exact=True).set_input_files(
        {
            "name": "private-escalation.pdf",
            "mimeType": "application/pdf",
            "buffer": private_content,
        }
    )
    private_region.get_by_role("button", name="Upload private file", exact=True).click()
    retry = private_region.get_by_role("button", name="Retry the same upload", exact=True)
    expect(retry).to_be_enabled()
    expect(
        private_region.get_by_text(
            f"private-escalation.pdf ({len(private_content)} bytes)", exact=True
        )
    ).to_be_visible()
    staff.unroute(pattern, lost_response)
    retry.click()
    expect(private_region.get_by_text("Quarantined", exact=False)).to_be_visible()
    assert put_count[0] == 1
    private = next(
        row for row in current_files(staff, ticket) if row["state"] == "staged" and row["internal"]
    )
    private_url = helpdesk_root + ticket_path + f"/files/{private['id']}/content"
    assert owner.request.get(private_url).status == 404
    clean(private["id"])
    private_region.get_by_role("button", name="Refresh file status", exact=True).click()
    private_region.get_by_role("checkbox", name="Attach this clean file 1", exact=True).check()
    private_text = "Synthetic staff-only evidence review."
    staff.get_by_role("textbox", name="Reply", exact=True).fill(private_text)
    with staff.expect_response(
        lambda response: (
            response.url.endswith(ticket_path + "/messages") and response.request.method == "POST"
        )
    ) as noted:
        staff_reply.get_by_role("button", name="Save internal note", exact=True).click()
    assert noted.value.status == 200, noted.value.text()
    assert noted.value.request.post_data_json["internal"] is True
    owner.reload()
    owner_detail = open_ticket(owner, ticket)
    expect(owner_detail.get_by_text(private_text, exact=True)).to_have_count(0)
    assert owner.request.get(private_url).status == 404
    peer = sign_in(browser, "peer")
    assert peer.request.get(file_url).status in {403, 404}
    current = detail(admin, ticket["id"])
    handed = mutate(
        admin,
        ticket_path + "/assignment",
        {
            "expected_version": current["version"],
            "assignee_user_id": str(actors["unassigned"]["user_id"]),
            "reason": "Synthetic handover",
        },
    )
    assert handed.status == 200, handed.text()
    assert staff.request.get(private_url).status in {403, 404}
    next_staff = sign_in(browser, "unassigned")
    assert next_staff.request.get(private_url).body() == private_content

    owner.goto(base + f"/ta/helpdesk?organization={org_id}")
    owner.get_by_role("button", name=f"{ticket['number']}: {ticket['subject']}", exact=True).click()
    expect(owner.get_by_role("region", name="பாதுகாப்பான இணைப்புகள்", exact=True)).to_be_visible()
    next_staff.goto(base + f"/en/admin/helpdesk?organization={org_id}")
    open_ticket(next_staff, ticket)
    for page, audience, file_label in (
        (owner, "owner", "பாதுகாப்பான கோப்பைத் தேர்ந்தெடுக்க"),
        (next_staff, "staff", "Choose a secure file"),
    ):
        file_input = page.get_by_label(file_label, exact=True)
        file_input.focus()
        expect(file_input).to_be_focused()
        page.keyboard.press("Tab")
        assert page.evaluate(
            "document.activeElement instanceof HTMLElement && "
            "document.activeElement !== document.body && "
            "document.activeElement.closest('form') !== null"
        ), "Keyboard focus must continue through the reply form"
        for width in (390, 768, 1024, 1440):
            page.set_viewport_size({"width": width, "height": 900})
            page.screenshot(
                path=str(evidence / f"helpdesk-files-{audience}-{width}.png"),
                full_page=True,
            )
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), (
                f"Secure helpdesk {audience} overflows at {width}px"
            )
    assert not errors, errors
    browser.close()
print(
    "Helpdesk secure files Chrome acceptance passed: typed upload, scan gating, "
    "stale/lost recovery, immutable private/shared evidence, TXT compatibility, "
    "handover and Tamil/mobile."
)
