"""S01 synthetic browser acceptance; only run through its isolated local runner."""

import os
import secrets
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

from app.modules.applications.models import Application, ApplicationForm
from app.modules.businesses.models import (
    BusinessOutcomeSnapshot,
    BusinessProfileRevision,
)
from app.modules.helpdesk.models import (
    HelpdeskAssignment,
    HelpdeskAttachment,
    HelpdeskHistory,
    HelpdeskMessage,
    HelpdeskNotice,
    HelpdeskTicket,
)
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
assert engine.url.database in {"edp_foundation_e2e", "edp_helpdesk_e2e"}
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

helpdesk_root = f"{base}/api/helpdesk/organizations/{org_id}"
business_root = f"{base}/api/businesses/organizations/{org_id}"
evidence = Path(".tool-cache/evidence")
evidence.mkdir(parents=True, exist_ok=True)
errors = []
private_text = "Synthetic private escalation note. Never visible to the participant."
private_reason = "Synthetic confidential routing rationale"
shared_text = "Synthetic shared guidance for the business owner."


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
    expect(page.get_by_text("Synthetic S01 " + key, exact=True)).to_be_visible()
    return page


def mutate(page, path, data=None, *, root=helpdesk_root):
    csrf = page.request.get(base + "/api/session/csrf").json()["csrf_token"]
    return page.request.post(
        root + path,
        data={} if data is None else data,
        headers={"Origin": base, "X-CSRF-Token": csrf},
    )


def detail(page, ticket_id):
    response = page.request.get(helpdesk_root + "/tickets/" + ticket_id)
    assert response.status == 200, response.text()
    return response.json()


def open_ticket(page, ticket):
    page.get_by_role(
        "button", name=f"{ticket['number']}: {ticket['subject']}", exact=True
    ).click()
    expect(
        page.get_by_role("region", name="Ticket details", exact=True)
    ).to_be_visible()
    expect(
        page.get_by_role("heading", name=ticket["subject"], exact=True)
    ).to_be_visible()


def create_ticket(page, subject, *, attachment=False):
    region = page.get_by_role("region", name="Create ticket", exact=True)
    expect(region).to_be_visible()
    region.locator('select[name="category"]').select_option("funding")
    region.get_by_label("Subject", exact=True).fill(subject)
    region.get_by_label("Description", exact=True).fill(
        "Synthetic owner request for local acceptance. No real personal or provider data."
    )
    region.locator('select[name="priority"]').select_option("high")
    if attachment:
        region.get_by_label("Text attachments", exact=True).set_input_files(
            {
                "name": "owner-request.txt",
                "mimeType": "text/plain",
                "buffer": "Synthetic owner attachment in English and தமிழ்.".encode(),
            }
        )
        expect(
            region.get_by_text("Selected files: owner-request.txt", exact=True)
        ).to_be_visible()
    with page.expect_response(
        lambda response: (
            response.url == helpdesk_root + "/tickets"
            and response.request.method == "POST"
        )
    ) as created:
        region.get_by_role("button", name="Create ticket", exact=True).click()
    assert created.value.status == 201, created.value.text()
    expect(page.get_by_role("heading", name=subject, exact=True)).to_be_visible()
    return created.value.json(), created.value.request.post_data_json


def refresh_ticket(page, ticket):
    page.reload()
    if "/admin/helpdesk" in page.url:
        expect(
            page.get_by_role("form", name="Ticket filters", exact=True)
        ).to_be_visible()
        if page.locator('select[name="queue"] option[value="organization"]').count():
            choose_queue(page, "organization")
    open_ticket(page, ticket)
    return detail(page, ticket["id"])


def choose_queue(page, queue):
    form = page.get_by_role("form", name="Ticket filters", exact=True)
    form.locator('select[name="queue"]').select_option(queue)
    with page.expect_response(
        lambda response: (
            "/tickets?" in response.url and "queue=" + queue in response.url
        )
    ) as listed:
        form.get_by_role("button", name="Apply filters", exact=True).click()
    assert listed.value.status == 200, listed.value.text()
    return listed.value.json()


def change_status(page, ticket_id, status, reason):
    region = page.get_by_role("region", name="Ticket details", exact=True)
    region.get_by_role("form", name="Update status", exact=True).locator(
        "select"
    ).select_option(status)
    region.get_by_label("Status reason", exact=True).fill(reason)
    with page.expect_response(
        lambda response: response.url.endswith(f"/tickets/{ticket_id}/status")
    ) as changed:
        region.get_by_role("button", name="Update status", exact=True).click()
    assert changed.value.status == 200, changed.value.text()
    assert changed.value.json()["status"] == status
    return changed.value.json()


def reply(page, ticket_id, body, *, internal=False, filename=None):
    region = page.get_by_role("region", name="Ticket details", exact=True)
    region.get_by_role("textbox", name="Reply", exact=True).fill(body)
    if region.get_by_label("Internal note", exact=True).count():
        region.get_by_label("Internal note", exact=True).set_checked(internal)
    if filename:
        region.get_by_label("Text attachments", exact=True).set_input_files(
            {"name": filename, "mimeType": "text/plain", "buffer": body.encode()}
        )
        expect(
            region.get_by_text("Selected files: " + filename, exact=True)
        ).to_be_visible()
    with page.expect_response(
        lambda response: (
            response.url.endswith(f"/tickets/{ticket_id}/messages")
            and response.request.method == "POST"
        )
    ) as sent:
        region.get_by_role(
            "button",
            name="Save internal note" if internal else "Send reply",
            exact=True,
        ).click()
    assert sent.value.status == 200, sent.value.text()
    expect(region.get_by_text(body, exact=True)).to_be_visible()
    return detail(page, ticket_id)


def assign(page, ticket_id, key, reason=private_reason):
    region = page.get_by_role("region", name="Ticket details", exact=True)
    region.get_by_role("form", name="Assign ticket", exact=True).locator(
        "select"
    ).select_option(str(actors[key]["user_id"]))
    region.get_by_label("Assignment reason", exact=True).fill(reason)
    with page.expect_response(
        lambda response: response.url.endswith(f"/tickets/{ticket_id}/assignment")
    ) as changed:
        region.get_by_role("button", name="Assign ticket", exact=True).click()
    assert changed.value.status == 200, changed.value.text()
    assert changed.value.json()["assignee_user_id"] == str(actors[key]["user_id"])
    return changed.value.json()


def immutable(db, model, row):
    row_id = row.id
    for operation in (
        update(model).where(model.id == row_id).values(created_at=now()),
        delete(model).where(model.id == row_id),
    ):
        try:
            db.execute(operation)
        except DBAPIError:
            db.rollback()
        else:
            db.rollback()
            raise AssertionError("Expected append-only evidence to reject mutation")


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        channel=os.getenv("PLAYWRIGHT_CHANNEL"), headless=True
    )
    owner = sign_in(browser, "owner")
    owner.goto(base + f"/en/helpdesk?organization={org_id}")
    ticket, creation = create_ticket(
        owner, "Synthetic funding support request", attachment=True
    )
    ticket_id = ticket["id"]
    replay = mutate(owner, "/tickets", creation)
    assert replay.status == 201 and replay.json()["id"] == ticket_id
    assert (
        mutate(
            owner, "/tickets", {**creation, "subject": "Changed replay subject"}
        ).status
        == 409
    )
    for bad_attachment in (
        {"filename": "script.txt", "content": "<script>alert(1)</script>"},
        {"filename": "binary.txt", "content": "Bad\u0000bytes"},
        {"filename": "misleading.html", "content": "plain text"},
        {"filename": "large.txt", "content": "x" * 32769},
    ):
        assert (
            mutate(
                owner,
                "/tickets",
                {
                    **creation,
                    "request_id": str(uuid4()),
                    "attachments": [bad_attachment],
                },
            ).status
            == 422
        )
    peer = sign_in(browser, "peer")
    unassigned = sign_in(browser, "unassigned")
    unenrolled = sign_in(browser, "unenrolled")
    outsider = sign_in(browser, "outsider")
    staff = sign_in(browser, "staff")
    admin = sign_in(browser, "admin")
    assert peer.request.get(helpdesk_root + "/tickets/" + ticket_id).status == 403
    assert peer.request.get(helpdesk_root + "/tickets").json()["items"] == []
    assert unassigned.request.get(helpdesk_root + "/tickets/" + ticket_id).status == 403
    assert outsider.request.get(helpdesk_root + "/tickets").status == 403
    assert unenrolled.request.get(helpdesk_root + "/tickets").status == 403
    assert (
        mutate(unenrolled, "/tickets", {**creation, "request_id": str(uuid4())}).status
        == 403
    )
    assert owner.request.get(helpdesk_root + "/assignees").status == 403
    assignees = admin.request.get(helpdesk_root + "/assignees").json()["items"]
    assert {item["id"] for item in assignees} == {
        str(actors[key]["user_id"]) for key in ("admin", "staff", "unassigned")
    }
    assert (
        outsider.request.get(
            f"{base}/api/helpdesk/organizations/{other_org_id}/tickets/{ticket_id}"
        ).status
        == 404
    )
    assert (
        mutate(
            owner,
            "/tickets",
            {**creation, "request_id": str(uuid4()), "priority": "urgent"},
        ).status
        == 422
    )
    assert (
        owner.request.get(helpdesk_root + "/tickets?queue=organization").status == 403
    )
    staff.goto(base + f"/en/admin/helpdesk?organization={org_id}")
    claim_list = choose_queue(staff, "unassigned")
    claim_entry = next(item for item in claim_list["items"] if item["id"] == ticket_id)
    assert claim_entry["access"] == "claim" and "subject" not in claim_entry
    assert (
        not {"owner_user_id", "owner_participant_id", "assignee_user_id"}
        & claim_entry.keys()
    )
    queue = staff.get_by_role("region", name="Helpdesk queue", exact=True)
    queue.get_by_label("Assignment reason", exact=True).fill(private_reason)
    with staff.expect_response(
        lambda response: response.url.endswith(f"/tickets/{ticket_id}/assignment")
    ) as claimed:
        queue.get_by_role(
            "button", name="Claim ticket: " + ticket["number"], exact=True
        ).click()
    assert claimed.value.status == 200, claimed.value.text()
    ticket = claimed.value.json()
    assert ticket["status"] == "assigned"
    expect(
        staff.get_by_role("heading", name=ticket["subject"], exact=True)
    ).to_be_visible()
    admin.goto(base + f"/en/admin/helpdesk?organization={org_id}")
    choose_queue(admin, "organization")
    open_ticket(admin, ticket)
    for key in ("owner", "outsider"):
        assert (
            mutate(
                admin,
                f"/tickets/{ticket_id}/assignment",
                {
                    "expected_version": ticket["version"],
                    "assignee_user_id": str(actors[key]["user_id"]),
                    "reason": "Synthetic ineligible assignment denied",
                },
            ).status
            == 422
        )
    assert (
        mutate(
            admin,
            f"/tickets/{ticket_id}/status",
            {
                "expected_version": ticket["version"],
                "status": "resolved",
                "reason": "Invalid lifecycle skip",
            },
        ).status
        == 409
    )
    ticket = change_status(
        staff, ticket_id, "in_progress", "Synthetic support work started"
    )
    staff_notices = staff.request.get(helpdesk_root + "/notices").json()["items"]
    assert staff_notices == []  # Self-claim does not notify the actor.
    owner_notices_before_private = owner.request.get(helpdesk_root + "/notices").json()[
        "items"
    ]
    ticket = reply(
        staff, ticket_id, private_text, internal=True, filename="private-note.txt"
    )
    private_version = ticket["version"]
    assert (
        owner.request.get(helpdesk_root + "/notices").json()["items"]
        == owner_notices_before_private
    )
    staff_messages = staff.request.get(
        helpdesk_root + f"/tickets/{ticket_id}/messages"
    ).json()
    private_message = next(item for item in staff_messages["items"] if item["internal"])
    private_attachment = private_message["attachments"][0]
    owner_messages = owner.request.get(
        helpdesk_root + f"/tickets/{ticket_id}/messages"
    ).json()
    assert all(not item["internal"] for item in owner_messages["items"])
    assert private_text not in str(owner_messages) and "private-note.txt" not in str(
        owner_messages
    )
    assert (
        owner.request.get(
            helpdesk_root
            + f"/tickets/{ticket_id}/attachments/{private_attachment['id']}"
        ).status
        == 404
    )
    assert (
        staff.request.get(
            helpdesk_root
            + f"/tickets/{ticket_id}/attachments/{private_attachment['id']}"
        ).text()
        == private_text
    )
    ticket = reply(staff, ticket_id, shared_text, filename="shared-guidance.txt")
    owner_history = owner.request.get(
        helpdesk_root + f"/tickets/{ticket_id}/history"
    ).json()
    assert private_text not in str(owner_history) and private_reason not in str(
        owner_history
    )
    owner_ticket = detail(owner, ticket_id)
    assert owner_ticket["access"] == "owner"
    assert (
        not {"assignee_user_id", "owner_user_id", "owner_participant_id"}
        & owner_ticket.keys()
    )
    owner.goto(base + f"/en/helpdesk?organization={org_id}")
    open_ticket(owner, ticket)
    expect(owner.get_by_text(private_text, exact=True)).to_have_count(0)
    shared_link = owner.get_by_role("link", name="shared-guidance.txt", exact=False)
    with owner.expect_download() as downloaded:
        shared_link.click()
    assert downloaded.value.suggested_filename == "helpdesk-attachment.txt"
    assert Path(downloaded.value.path()).read_text(encoding="utf-8") == shared_text
    shared_messages = owner.request.get(
        helpdesk_root + f"/tickets/{ticket_id}/messages"
    ).json()
    shared_message = next(
        item for item in shared_messages["items"] if item["body"] == shared_text
    )
    attachment_url = helpdesk_root + (
        f"/tickets/{ticket_id}/attachments/{shared_message['attachments'][0]['id']}"
    )
    attachment_response = owner.request.get(attachment_url)
    assert attachment_response.status == 200
    assert attachment_response.headers["x-content-type-options"] == "nosniff"
    assert "no-store" in attachment_response.headers["cache-control"]
    assert attachment_response.headers["content-disposition"].startswith("attachment;")
    assert peer.request.get(attachment_url).status == 403
    assert unassigned.request.get(attachment_url).status == 403
    assert outsider.request.get(attachment_url).status == 403
    assert (
        mutate(
            owner,
            f"/tickets/{ticket_id}/messages",
            {
                "expected_version": ticket["version"],
                "body": "Forbidden private note",
                "internal": True,
            },
        ).status
        == 403
    )
    assert (
        mutate(
            staff,
            f"/tickets/{ticket_id}/status",
            {
                "expected_version": 1,
                "status": "resolved",
                "reason": "Stale support version",
            },
        ).status
        == 409
    )
    # A real concurrent edit pauses the owner UI and preserves the unsent response.
    unsent = (
        "Synthetic preserved owner response after a concurrent staff priority change."
    )
    owner.get_by_role("textbox", name="Reply", exact=True).fill(unsent)
    priority_form = staff.get_by_role("form", name="Update priority", exact=True)
    priority_form.locator("select").select_option("urgent")
    priority_form.get_by_label("Priority reason", exact=True).fill(
        "Synthetic confidential escalation reason"
    )
    with staff.expect_response(
        lambda response: response.url.endswith(f"/tickets/{ticket_id}/priority")
    ) as urgent:
        priority_form.get_by_role("button", name="Update priority", exact=True).click()
    assert urgent.value.status == 200 and urgent.value.json()["priority"] == "urgent"
    with owner.expect_response(
        lambda response: (
            response.url.endswith(f"/tickets/{ticket_id}/messages")
            and response.request.method == "POST"
        )
    ) as stale_reply:
        owner.get_by_role("button", name="Send reply", exact=True).click()
    assert stale_reply.value.status == 409
    expect(owner.get_by_role("textbox", name="Reply", exact=True)).to_have_value(unsent)
    expect(owner.get_by_role("button", name="Send reply", exact=True)).to_be_disabled()
    owner.get_by_role("button", name="Refresh ticket", exact=True).click()
    expect(owner.get_by_role("button", name="Send reply", exact=True)).to_be_enabled()
    expect(owner.get_by_role("textbox", name="Reply", exact=True)).to_have_value(unsent)
    ticket = reply(owner, ticket_id, unsent)
    assert "Synthetic confidential escalation reason" not in str(
        owner.request.get(helpdesk_root + f"/tickets/{ticket_id}/history").json()
    )
    refresh_ticket(staff, ticket)
    ticket = change_status(
        staff, ticket_id, "waiting_for_user", "Synthetic owner evidence needed"
    )
    owner_ticket = refresh_ticket(owner, ticket)
    ticket = reply(
        owner, ticket_id, "Synthetic owner supplies the requested business evidence."
    )
    assert ticket["status"] == "in_progress"
    staff_notices = staff.request.get(helpdesk_root + "/notices").json()["items"]
    assert any(notice["ticket_id"] == ticket_id for notice in staff_notices)
    # Shared owner responses resume work while preserving the waiting-state evidence.
    staff_ticket = refresh_ticket(staff, ticket)
    if staff_ticket["status"] == "waiting_for_user":
        ticket = change_status(
            staff, ticket_id, "in_progress", "Synthetic owner response reviewed"
        )
    ticket = change_status(
        staff, ticket_id, "resolved", "Synthetic shared guidance resolved request"
    )
    assert (
        mutate(
            staff,
            f"/tickets/{ticket_id}/reopen",
            {
                "expected_version": ticket["version"],
                "reason": "Assigned staff cannot reopen",
            },
        ).status
        == 403
    )
    owner_ticket = refresh_ticket(owner, ticket)
    owner.get_by_label("Status reason", exact=True).fill(
        "Synthetic owner accepts the resolution"
    )
    with owner.expect_response(
        lambda response: response.url.endswith(f"/tickets/{ticket_id}/status")
    ) as closed:
        owner.get_by_role("button", name="Close ticket", exact=True).click()
    assert closed.value.status == 200, closed.value.text()
    ticket = closed.value.json()
    assert ticket["status"] == "closed"
    region = owner.get_by_role("region", name="Ticket details", exact=True)
    region.get_by_label("Reopen reason", exact=True).fill(
        "Synthetic additional owner question"
    )
    with owner.expect_response(
        lambda response: response.url.endswith(f"/tickets/{ticket_id}/reopen")
    ) as reopened:
        region.get_by_role("button", name="Reopen ticket", exact=True).click()
    assert reopened.value.status == 200, reopened.value.text()
    ticket = reopened.value.json()
    assert ticket["status"] == "open"
    assert staff.request.get(helpdesk_root + "/tickets/" + ticket_id).status == 403
    assert staff.request.get(attachment_url).status == 403
    assert all(
        notice["ticket_id"] != ticket_id
        for notice in staff.request.get(helpdesk_root + "/notices").json()["items"]
    )
    old_notice = next(
        notice for notice in staff_notices if notice["ticket_id"] == ticket_id
    )
    assert (
        mutate(
            staff,
            f"/notices/{old_notice['id']}/read",
            {"expected_version": old_notice["version"]},
        ).status
        == 404
    )
    admin_ticket = refresh_ticket(admin, ticket)
    ticket = assign(
        admin, ticket_id, "unassigned", "Synthetic new specialist assignment"
    )
    assert staff.request.get(helpdesk_root + "/tickets/" + ticket_id).status == 403
    unassigned.goto(base + f"/en/admin/helpdesk?organization={org_id}")
    assert any(
        notice["ticket_id"] == ticket_id
        for notice in unassigned.request.get(helpdesk_root + "/notices").json()["items"]
    )
    open_ticket(unassigned, ticket)
    ticket = change_status(
        unassigned, ticket_id, "in_progress", "Synthetic reassigned work started"
    )
    ticket = change_status(
        unassigned, ticket_id, "resolved", "Synthetic follow-up request resolved"
    )
    admin_ticket = refresh_ticket(admin, ticket)
    admin.get_by_label("Reopen reason", exact=True).fill(
        "Synthetic administrator review requested"
    )
    with admin.expect_response(
        lambda response: response.url.endswith(f"/tickets/{ticket_id}/reopen")
    ) as admin_reopened:
        admin.get_by_role("button", name="Reopen ticket", exact=True).click()
    assert admin_reopened.value.status == 200
    ticket = admin_reopened.value.json()
    assert ticket["status"] == "open" and ticket["assignee_user_id"] is None
    assert unassigned.request.get(helpdesk_root + "/tickets/" + ticket_id).status == 403

    # In-app notices are recipient-only, body-free and can be opted out transactionally.
    owner.goto(base + f"/en/helpdesk?organization={org_id}")
    notice_region = owner.get_by_role("region", name="My notices", exact=True)
    expect(
        notice_region.get_by_role("button", name="Mark read", exact=True).first
    ).to_be_visible()
    notices_before_read = owner.request.get(helpdesk_root + "/notices").json()["items"]
    assert notices_before_read
    assert shared_text not in str(notices_before_read) and private_text not in str(
        notices_before_read
    )
    assert all(
        "subject" not in notice and "body" not in notice
        for notice in notices_before_read
    )
    with owner.expect_response(
        lambda response: "/notices/" in response.url and response.url.endswith("/read")
    ) as read:
        notice_region.get_by_role("button", name="Mark read", exact=True).first.click()
    assert read.value.status == 200
    assert read.value.json()["read_at"] is not None
    assert (
        mutate(
            owner, f"/notices/{read.value.json()['id']}/read", {"expected_version": 1}
        ).status
        == 409
    )
    assert (
        mutate(
            peer, f"/notices/{read.value.json()['id']}/read", {"expected_version": 1}
        ).status
        == 404
    )
    owner.get_by_label("Receive in-app notices", exact=True).uncheck()
    with owner.expect_response(
        lambda response: (
            response.url.endswith("/preference") and response.request.method == "POST"
        )
    ) as preference:
        owner.get_by_role("button", name="Save preference", exact=True).click()
    assert preference.value.status == 200 and not preference.value.json()["enabled"]
    assert (
        mutate(
            owner,
            "/preference",
            {
                "expected_version": preference.value.json()["version"] - 1,
                "enabled": True,
            },
        ).status
        == 409
    )
    before_optout_reply = owner.request.get(helpdesk_root + "/notices").json()["items"]
    ticket = assign(admin, ticket_id, "staff", "Synthetic return to support desk")
    staff.goto(base + f"/en/admin/helpdesk?organization={org_id}")
    open_ticket(staff, ticket)
    ticket = reply(
        staff, ticket_id, "Synthetic reply after owner opted out of notices."
    )
    assert (
        owner.request.get(helpdesk_root + "/notices").json()["items"]
        == before_optout_reply
    )
    csrf = owner.request.get(base + "/api/session/csrf").json()["csrf_token"]
    assert (
        owner.request.post(
            helpdesk_root + "/preference",
            data={
                "enabled": True,
                "expected_version": preference.value.json()["version"],
            },
            headers={"Origin": "https://evil.example", "X-CSRF-Token": csrf},
        ).status
        == 403
    )
    assert (
        owner.request.post(
            helpdesk_root + "/preference",
            data={
                "enabled": True,
                "expected_version": preference.value.json()["version"],
            },
            headers={"Origin": base},
        ).status
        == 403
    )
    assert owner.request.get(helpdesk_root + "/not-an-allowed-operation").status == 404
    assert owner.request.get(helpdesk_root + "/tickets?limit=1000").status == 400
    assert (
        owner.request.get(helpdesk_root + "/tickets?status=open&status=closed").status
        == 400
    )
    assert (
        owner.request.get(
            helpdesk_root + "/tickets?organization=" + str(other_org_id)
        ).status
        == 400
    )

    # Recheck the complete B02 workflow with two separate owners and a policy change.
    admin.goto(base + f"/en/admin/businesses?organization={org_id}")
    expect(
        admin.get_by_role("heading", name="Business follow-ups", level=1)
    ).to_be_visible()
    admin.get_by_label("Follow-up days", exact=True).fill("5, 30")
    admin.get_by_label("Reason for change", exact=True).fill(
        "Synthetic first follow-up cadence"
    )
    with admin.expect_response(
        lambda response: response.url == business_root + "/policy"
    ) as policy:
        admin.get_by_role("button", name="Save schedule", exact=True).click()
    assert policy.value.status == 200
    owner.goto(base + f"/en/businesses?organization={org_id}")
    owner.get_by_label("Business name", exact=True).fill("Synthetic growing bakery")
    owner.get_by_label("Sector", exact=True).fill("Food")
    owner.get_by_label("Products and services", exact=True).fill(
        "Synthetic baked products"
    )
    owner.get_by_label("Support needed", exact=True).fill("Synthetic equipment funding")
    with owner.expect_response(
        lambda response: (
            response.url == business_root + "/profiles"
            and response.request.method == "POST"
        )
    ) as created_business:
        owner.get_by_role("button", name="Save business", exact=True).click()
    assert created_business.value.status == 201
    business = created_business.value.json()
    assert [item["offset_days"] for item in business["follow_ups"]] == [5, 30]
    frozen_dates = [item["due_on"] for item in business["follow_ups"]]
    owner.reload()
    owner.get_by_label("Business name", exact=True).fill("Synthetic operating bakery")
    owner.get_by_label("Team size", exact=True).fill("3")
    with owner.expect_response(
        lambda response: response.url.endswith(f"/profiles/{business['id']}/update")
    ) as updated_business:
        owner.get_by_role("button", name="Save business", exact=True).click()
    assert updated_business.value.status == 200
    business = updated_business.value.json()
    assert business["version"] == 2 and business["team_size"] == 3
    assert [item["due_on"] for item in business["follow_ups"]] == frozen_dates
    assert len(business["revisions"]) == 2
    admin.get_by_label("Follow-up days", exact=True).fill("7, 45")
    admin.get_by_label("Reason for change", exact=True).fill(
        "Synthetic second intake cadence"
    )
    with admin.expect_response(
        lambda response: response.url == business_root + "/policy"
    ) as revised:
        admin.get_by_role("button", name="Save schedule", exact=True).click()
    assert revised.value.status == 200
    peer.goto(base + f"/en/businesses?organization={org_id}")
    peer.get_by_label("Business name", exact=True).fill("Synthetic peer workshop")
    peer.get_by_label("Sector", exact=True).fill("Manufacturing")
    peer.get_by_label("Products and services", exact=True).fill(
        "Synthetic workshop services"
    )
    with peer.expect_response(
        lambda response: (
            response.url == business_root + "/profiles"
            and response.request.method == "POST"
        )
    ) as peer_business:
        peer.get_by_role("button", name="Save business", exact=True).click()
    assert peer_business.value.status == 201
    assert [
        item["offset_days"] for item in peer_business.value.json()["follow_ups"]
    ] == [7, 45]
    owner.reload()
    followup = owner.locator("ol.program-list > li").first
    followup.locator("summary").click()
    followup.get_by_label("Business started", exact=True).check()
    followup.get_by_label("Business active", exact=True).check()
    followup.get_by_label("Jobs created", exact=True).fill("2")
    followup.get_by_label("Challenges", exact=True).fill(
        "Synthetic supply planning challenge"
    )
    followup.get_by_label("Support requested", exact=True).fill(
        "Synthetic packaging mentoring"
    )
    followup.get_by_label("Outcomes", exact=True).fill(
        "Synthetic first trading milestone"
    )
    with owner.expect_response(
        lambda response: (
            "/follow-ups/" in response.url and response.url.endswith("/outcome")
        )
    ) as outcome:
        followup.get_by_role("button", name="Report outcome", exact=True).click()
    assert outcome.value.status == 201
    expect(followup.get_by_text("Jobs created: 2", exact=True)).to_be_visible()
    outcome_path = f"/follow-ups/{business['follow_ups'][0]['id']}/outcome"
    outcome_data = outcome.value.request.post_data_json
    assert mutate(owner, outcome_path, outcome_data, root=business_root).status == 409
    assert mutate(peer, outcome_path, outcome_data, root=business_root).status == 404
    assert mutate(admin, outcome_path, outcome_data, root=business_root).status == 403
    business_mine = owner.request.get(business_root + "/mine").json()["entries"][0][
        "profile"
    ]
    assert [item["due_on"] for item in business_mine["follow_ups"]] == frozen_dates
    assert business_mine["follow_ups"][0]["outcome"]["jobs_created"] == 2
    admin.reload()
    expect(admin.get_by_text("Completed: 1", exact=False)).to_be_visible()
    admin.screenshot(path=str(evidence / "post-training-staff-en.png"), full_page=True)
    owner.goto(base + f"/ta/businesses?organization={org_id}")
    expect(owner.get_by_role("heading", name="எனது தொழில்", level=1)).to_be_visible()
    expect(owner.get_by_label("தொழில் பெயர்", exact=True)).to_have_value(
        "Synthetic operating bakery"
    )
    owner.set_viewport_size({"width": 390, "height": 844})
    assert owner.evaluate(
        "document.documentElement.scrollWidth <= window.innerWidth + 1"
    )
    owner.screenshot(
        path=str(evidence / "post-training-owner-ta-mobile.png"), full_page=True
    )
    owner.goto(base + f"/ta/helpdesk?organization={org_id}")
    owner.get_by_role(
        "button", name=f"{ticket['number']}: {ticket['subject']}", exact=True
    ).click()
    expect(
        owner.get_by_role("region", name="கோரிக்கை விவரம்", exact=True)
    ).to_be_visible()
    expect(owner.get_by_text(private_text, exact=True)).to_have_count(0)
    assert owner.evaluate(
        "document.documentElement.scrollWidth <= window.innerWidth + 1"
    )
    owner.screenshot(
        path=str(evidence / "helpdesk-owner-ta-mobile.png"), full_page=True
    )
    staff.goto(base + f"/ta/admin/helpdesk?organization={org_id}")
    staff.get_by_role(
        "button", name=f"{ticket['number']}: {ticket['subject']}", exact=True
    ).click()
    expect(
        staff.get_by_role("region", name="கோரிக்கை விவரம்", exact=True)
    ).to_be_visible()
    expect(staff.get_by_text(private_text, exact=True)).to_be_visible()
    staff.set_viewport_size({"width": 390, "height": 844})
    assert staff.evaluate(
        "document.documentElement.scrollWidth <= window.innerWidth + 1"
    )
    staff.screenshot(
        path=str(evidence / "helpdesk-staff-ta-mobile.png"), full_page=True
    )
    assert owner.evaluate("Object.keys(localStorage)") == []

    with Session(engine) as db:
        assert (
            len(
                list(
                    db.scalars(
                        select(HelpdeskTicket).where(
                            HelpdeskTicket.organization_id == org_id
                        )
                    )
                )
            )
            == 1
        )
        persisted = db.get(HelpdeskTicket, UUID(ticket_id))
        assert persisted and persisted.version == ticket["version"]
        assert persisted.owner_user_id == actors["owner"]["user_id"]
        messages = list(
            db.scalars(
                select(HelpdeskMessage).where(HelpdeskMessage.ticket_id == persisted.id)
            )
        )
        assert sum(message.internal for message in messages) == 1
        assert sum(message.body == unsent for message in messages) == 1
        assert (
            next(message for message in messages if message.internal).body
            == private_text
        )
        history = list(
            db.scalars(
                select(HelpdeskHistory)
                .where(HelpdeskHistory.ticket_id == persisted.id)
                .order_by(HelpdeskHistory.version)
            )
        )
        assert [item.version for item in history] == list(
            range(1, persisted.version + 1)
        )
        assignments = list(
            db.scalars(
                select(HelpdeskAssignment).where(
                    HelpdeskAssignment.ticket_id == persisted.id
                )
            )
        )
        assert len(assignments) == 5  # Three assignments and two reopen clearances.
        attachments = list(
            db.scalars(
                select(HelpdeskAttachment).where(
                    HelpdeskAttachment.ticket_id == persisted.id
                )
            )
        )
        assert len(attachments) == 3
        notices = list(
            db.scalars(
                select(HelpdeskNotice).where(HelpdeskNotice.ticket_id == persisted.id)
            )
        )
        assert all(notice.ticket_version != private_version for notice in notices)
        for model, row in (
            (HelpdeskMessage, messages[0]),
            (HelpdeskHistory, history[0]),
            (HelpdeskAssignment, assignments[0]),
            (HelpdeskAttachment, attachments[0]),
        ):
            immutable(db, model, row)
        revisions = list(
            db.scalars(
                select(BusinessProfileRevision).where(
                    BusinessProfileRevision.profile_id == UUID(business["id"])
                )
            )
        )
        snapshots = list(
            db.scalars(
                select(BusinessOutcomeSnapshot).where(
                    BusinessOutcomeSnapshot.organization_id == org_id
                )
            )
        )
        assert len(revisions) == 2 and len(snapshots) == 1
        assert snapshots[0].author_user_id == actors["owner"]["user_id"]
        immutable(db, BusinessProfileRevision, revisions[0])
        immutable(db, BusinessOutcomeSnapshot, snapshots[0])
        audits = list(
            db.scalars(
                select(AuditLog).where(
                    AuditLog.organization_id == org_id,
                    AuditLog.action.like("helpdesk.%"),
                )
            )
        )
        assert audits
        assert all(not row.reason for row in audits)
        assert all("Synthetic" not in (row.changed_fields or "") for row in audits)
    assert not errors, "Unexpected browser JavaScript errors: " + "; ".join(errors)
    browser.close()

print(
    "Phase 9 Chrome acceptance passed: helpdesk lifecycle, privacy, attachments, notices, "
    "reassignment/reopen authorization and B02 frozen schedules/outcomes, English/Tamil mobile layouts."
)
