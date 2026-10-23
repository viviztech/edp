import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_identity import account, auth, signed_in  # noqa: F401
from test_knowledge_db import context as knowledge_context

from app.modules.helpdesk.models import (
    HelpdeskAssignment,
    HelpdeskAttachment,
    HelpdeskHistory,
    HelpdeskMessage,
    HelpdeskNotice,
    HelpdeskPreference,
    HelpdeskTicket,
)
from app.modules.identity.models import AuditLog, Role, User, UserRole
from app.modules.programs.models import Enrollment, Participant

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)


def context(request):
    client, engine, org, other, enrollment, owner, original_staff, peer, outsider = (
        knowledge_context(request)
    )
    auth_context = request.getfixturevalue("auth")
    staff_credentials = account(auth_context, "support-two@example.com")
    admin_credentials = account(auth_context, "helpdesk-admin@example.com")
    with Session(engine) as db:
        support = db.scalar(select(Role).where(Role.name == "Support Executive"))
        manager = db.scalar(select(Role).where(Role.name == "Program Manager"))
        original = db.scalar(select(User).where(User.email == "knowledge-staff@example.com"))
        second = db.scalar(select(User).where(User.email == staff_credentials["email"]))
        admin = db.scalar(select(User).where(User.email == admin_credentials["email"]))
        learner = db.scalar(select(User).where(User.email == "learner@example.com"))
        assert support and manager and original and second and admin and learner
        db.add_all(
            [
                UserRole(user_id=original.id, role_id=support.id, organization_id=org),
                UserRole(user_id=second.id, role_id=support.id, organization_id=org),
                UserRole(user_id=admin.id, role_id=manager.id, organization_id=org),
            ]
        )
        ids = {
            "staff": str(original.id),
            "second": str(second.id),
            "admin": str(admin.id),
            "owner": str(learner.id),
        }
        db.commit()
    logins = [
        client.post("/api/v1/auth/login", json=data)
        for data in (staff_credentials, admin_credentials)
    ]
    assert all(result.status_code == 200 for result in logins)
    second_headers, admin_headers = [
        {"Authorization": "Bearer " + result.json()["access_token"]} for result in logins
    ]
    return (
        client,
        engine,
        f"/api/v1/helpdesk/organizations/{org}",
        org,
        other,
        enrollment,
        {
            "owner": owner,
            "staff": original_staff,
            "second": second_headers,
            "admin": admin_headers,
            "peer": peer,
            "outsider": outsider,
        },
        ids,
    )


def create(client, base, headers, **overrides):
    fields = {
        "request_id": str(uuid4()),
        "category": "funding",
        "subject": "Synthetic funding request",
        "body": "Synthetic shared question",
        "priority": "normal",
        **overrides,
    }
    response = client.post(base + "/tickets", headers=headers, json=fields)
    assert response.status_code == 201, response.text
    return response.json(), fields


def command(client, path, headers, ticket, **fields):
    result = client.post(
        path, headers=headers, json={"expected_version": ticket["version"], **fields}
    )
    assert result.status_code == 200, result.text
    return result.json()


def test_lifecycle_replies_private_notes_history_and_both_reopen_actors(request):
    client, engine, base, org, _, _, h, ids = context(request)
    row, fields = create(
        client,
        base,
        h["owner"],
        attachments=[{"filename": "question.txt", "content": "Public text\nதமிழ்"}],
    )
    url = base + "/tickets/" + row["id"]
    assert row["access"] == "owner" and "assignee_user_id" not in row and "owner_user_id" not in row
    assert client.post(base + "/tickets", headers=h["owner"], json=fields).json() == row
    assert (
        client.post(
            base + "/tickets", headers=h["owner"], json={**fields, "body": "Changed retry"}
        ).status_code
        == 409
    )
    assert client.get(url, headers=h["staff"]).status_code == 403
    queue = client.get(base + "/tickets?queue=unassigned", headers=h["staff"]).json()["items"]
    assert (
        queue[0]["access"] == "claim"
        and "subject" not in queue[0]
        and "owner_user_id" not in queue[0]
    )
    row = command(
        client,
        url + "/assignment",
        h["staff"],
        row,
        assignee_user_id=ids["staff"],
        reason="Claim assigned work",
    )
    assert row["status"] == "assigned"
    stale = {"expected_version": 1, "body": "Stale reply", "internal": False}
    assert client.post(url + "/messages", headers=h["staff"], json=stale).status_code == 409
    row = command(
        client,
        url + "/messages",
        h["staff"],
        row,
        body="Private diagnostic note",
        internal=True,
        attachments=[{"filename": "private.txt", "content": "Private evidence"}],
    )
    staff_messages = client.get(url + "/messages", headers=h["staff"]).json()["items"]
    hidden = staff_messages[-1]
    assert hidden["internal"] and hidden["body"] == "Private diagnostic note"
    owner_messages = client.get(url + "/messages", headers=h["owner"]).json()["items"]
    assert len(owner_messages) == 1 and "Private" not in str(owner_messages)
    assert (
        client.get(url + "/messages?cursor=" + hidden["id"], headers=h["owner"]).status_code == 422
    )
    private_url = url + "/attachments/" + hidden["attachments"][0]["id"]
    assert client.get(private_url, headers=h["owner"]).status_code == 404
    assert client.get(private_url, headers=h["staff"]).content == b"Private evidence"
    owner_history = client.get(url + "/history", headers=h["owner"]).json()["items"]
    assert [event["event"] for event in owner_history] == ["created", "assigned"]
    assert owner_history[-1]["reason"] is None
    row = command(
        client,
        url + "/priority",
        h["staff"],
        row,
        priority="urgent",
        reason="Private escalation reason",
    )
    assert client.get(url + "/history", headers=h["owner"]).json()["items"][-1]["reason"] is None
    row = command(
        client,
        url + "/status",
        h["staff"],
        row,
        status="in_progress",
        reason="Started support work",
    )
    row = command(
        client, url + "/messages", h["staff"], row, body="Shared guidance", internal=False
    )
    row = command(
        client,
        url + "/status",
        h["staff"],
        row,
        status="waiting_for_user",
        reason="Please provide the missing detail",
    )
    row = command(
        client, url + "/messages", h["owner"], row, body="Requested detail supplied", internal=False
    )
    assert row["status"] == "in_progress"
    row = command(
        client, url + "/status", h["staff"], row, status="resolved", reason="Guidance completed"
    )
    row = command(
        client, url + "/status", h["owner"], row, status="closed", reason="Resolution accepted"
    )
    assert (
        client.post(
            url + "/messages",
            headers=h["owner"],
            json={"expected_version": row["version"], "body": "Late response"},
        ).status_code
        == 409
    )
    row = command(client, url + "/reopen", h["owner"], row, reason="A related issue remains")
    assert row["status"] == "open"
    assert client.get(url, headers=h["staff"]).status_code == 403
    row = command(
        client,
        url + "/assignment",
        h["admin"],
        row,
        assignee_user_id=ids["second"],
        reason="New specialist assignment",
    )
    row = command(
        client, url + "/status", h["second"], row, status="in_progress", reason="Specialist started"
    )
    row = command(
        client, url + "/status", h["second"], row, status="resolved", reason="Specialist resolved"
    )
    assert (
        client.post(
            url + "/reopen",
            headers=h["second"],
            json={"expected_version": row["version"], "reason": "Not admin"},
        ).status_code
        == 403
    )
    row = command(client, url + "/reopen", h["admin"], row, reason="Additional support needed")
    assert row["status"] == "open" and row["assignee_user_id"] is None
    with Session(engine) as db:
        ticket_id = UUID(row["id"])
        assert db.scalar(select(func.count()).select_from(HelpdeskTicket)) == 1
        assert (
            db.scalar(
                select(func.count())
                .select_from(HelpdeskHistory)
                .where(HelpdeskHistory.ticket_id == ticket_id)
            )
            == row["version"]
        )
        audits = list(
            db.scalars(
                select(AuditLog).where(
                    AuditLog.organization_id == org, AuditLog.action.like("helpdesk.%")
                )
            )
        )
        assert audits and all(item.reason is None for item in audits)
        assert not any("Private" in str(item.changed_fields) for item in audits)


def test_scope_assignment_eligibility_alumni_and_invalid_lifecycle(request):
    client, engine, base, org, other, enrollment, h, ids = context(request)
    row, _ = create(client, base, h["owner"])
    url = base + "/tickets/" + row["id"]
    for suffix in ("", "/messages", "/history"):
        assert client.get(url + suffix, headers=h["peer"]).status_code == 403
        assert (
            client.get(url.replace(str(org), str(other)) + suffix, headers=h["admin"]).status_code
            == 404
        )
    assert client.get(base + "/assignees", headers=h["owner"]).status_code == 403
    assert client.get(base + "/tickets?queue=organization", headers=h["staff"]).status_code == 403
    assert client.get(base + "/tickets?queue=unassigned", headers=h["peer"]).status_code == 403
    assert (
        client.post(
            base + "/tickets",
            headers=h["outsider"],
            json={
                "request_id": str(uuid4()),
                "category": "general",
                "subject": "No enrollment",
                "body": "Question",
            },
        ).status_code
        == 403
    )
    assignees = client.get(base + "/assignees", headers=h["admin"]).json()["items"]
    assert {entry["id"] for entry in assignees} == {ids["staff"], ids["second"], ids["admin"]}
    invalid = {
        "expected_version": 1,
        "assignee_user_id": ids["owner"],
        "reason": "Invalid assignment",
    }
    assert client.post(url + "/assignment", headers=h["admin"], json=invalid).status_code == 422
    assert (
        client.post(
            url + "/assignment",
            headers=h["staff"],
            json={**invalid, "assignee_user_id": ids["second"]},
        ).status_code
        == 403
    )
    assert (
        client.post(
            url + "/status",
            headers=h["owner"],
            json={"expected_version": 1, "status": "closed", "reason": "Skip entire workflow"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            url + "/messages",
            headers=h["owner"],
            json={"expected_version": 1, "body": "Hidden note", "internal": True},
        ).status_code
        == 403
    )
    row = command(
        client,
        url + "/assignment",
        h["admin"],
        row,
        assignee_user_id=ids["staff"],
        reason="Assigned to support",
    )
    assert client.get(url, headers=h["second"]).status_code == 403
    row = command(
        client,
        url + "/assignment",
        h["staff"],
        row,
        assignee_user_id=ids["second"],
        reason="Hand over to support",
    )
    assert client.get(url, headers=h["staff"]).status_code == 403
    assert (
        client.post(
            url + "/messages",
            headers=h["staff"],
            json={"expected_version": row["version"], "body": "Former staff reply"},
        ).status_code
        == 403
    )
    with Session(engine) as db:
        current = db.get(Enrollment, enrollment)
        assert current
        owner_participant = db.get(Participant, current.participant_id)
        assert owner_participant
        current.status = "completed"
        current.version += 1
        owner_participant.status = "completed"
        owner_participant.version += 1
        db.commit()
    assert client.get(url, headers=h["owner"]).status_code == 200
    create(client, base, h["owner"], subject="Alumni support remains available")
    with Session(engine) as db:
        current = db.get(Enrollment, enrollment)
        assert current
        current.status = "withdrawn"
        current.version += 1
        db.commit()
    assert client.get(url, headers=h["owner"]).status_code == 403
    assert client.get(base + "/notices", headers=h["owner"]).status_code == 403
    assert client.get(base + "/preference", headers=h["owner"]).status_code == 403


def test_notices_recipient_scope_current_assignment_opt_out_and_exact_versions(request):
    client, engine, base, _, _, _, h, ids = context(request)
    row, _ = create(client, base, h["owner"])
    url = base + "/tickets/" + row["id"]
    row = command(
        client,
        url + "/assignment",
        h["admin"],
        row,
        assignee_user_id=ids["staff"],
        reason="Assign support",
    )
    staff_notices = client.get(base + "/notices", headers=h["staff"]).json()["items"]
    assert len(staff_notices) == 1 and staff_notices[0]["event"] == "assigned"
    notice = staff_notices[0]
    read_url = base + "/notices/" + notice["id"] + "/read"
    assert client.post(read_url, headers=h["peer"], json={"expected_version": 1}).status_code == 404
    read = client.post(read_url, headers=h["staff"], json={"expected_version": 1})
    assert read.status_code == 200 and read.json()["version"] == 2 and read.json()["read_at"]
    assert (
        client.post(read_url, headers=h["staff"], json={"expected_version": 1}).status_code == 409
    )
    row = command(client, url + "/messages", h["staff"], row, body="Internal only", internal=True)
    assert client.get(base + "/notices", headers=h["owner"]).json()["items"] == []
    row = command(
        client, url + "/messages", h["staff"], row, body="Shared reply for owner", internal=False
    )
    owner_notices = client.get(base + "/notices", headers=h["owner"]).json()["items"]
    assert len(owner_notices) == 1 and set(owner_notices[0]) == {
        "id",
        "ticket_id",
        "event",
        "ticket_version",
        "version",
        "read_at",
        "created_at",
    }
    pref = client.get(base + "/preference", headers=h["owner"]).json()
    assert pref == {"enabled": True, "version": 1}
    changed = client.post(
        base + "/preference", headers=h["owner"], json={"enabled": False, "expected_version": 1}
    )
    assert changed.status_code == 200 and changed.json() == {"enabled": False, "version": 2}
    assert (
        client.post(
            base + "/preference", headers=h["owner"], json={"enabled": True, "expected_version": 1}
        ).status_code
        == 409
    )
    row = command(
        client, url + "/messages", h["staff"], row, body="Reply while opted out", internal=False
    )
    assert len(client.get(base + "/notices", headers=h["owner"]).json()["items"]) == 1
    row = command(client, url + "/messages", h["owner"], row, body="Owner reply", internal=False)
    assert len(client.get(base + "/notices", headers=h["staff"]).json()["items"]) == 2
    row = command(
        client,
        url + "/assignment",
        h["admin"],
        row,
        assignee_user_id=ids["second"],
        reason="Move responsibility",
    )
    assert client.get(base + "/notices", headers=h["staff"]).json()["items"] == []
    assert (
        client.post(read_url, headers=h["staff"], json={"expected_version": 2}).status_code == 404
    )
    with Session(engine) as db:
        notices = list(db.scalars(select(HelpdeskNotice)))
        assert len(notices) == len(
            {(n.ticket_id, n.recipient_user_id, n.event, n.ticket_version) for n in notices}
        )
        assert db.scalar(select(func.count()).select_from(HelpdeskPreference)) == 1
        actions = set(db.scalars(select(AuditLog.action).where(AuditLog.action.like("helpdesk.%"))))
        assert {"helpdesk.preference_update", "helpdesk.notice_read"} <= actions


def test_attachments_bounded_pagination_and_database_immutability(request):
    client, engine, base, org, other, _, h, ids = context(request)
    fields = {
        "request_id": str(uuid4()),
        "category": "general",
        "subject": "Text attachment",
        "body": "Body",
    }
    for attachments in (
        [{"filename": "test.pdf", "content": "Text"}],
        [{"filename": "x.html.txt", "content": "Text"}],
        [{"filename": "test.txt", "content": "<script>alert(1)</script>"}],
        [{"filename": "test.txt", "content": "\u0000binary"}],
        [{"filename": "test.txt", "content": "a\u007fb"}],
        [{"filename": "test.txt", "content": "தமிழ்" * 5000}],
        [{"filename": "test.txt", "content": "Text"}] * 4,
    ):
        assert (
            client.post(
                base + "/tickets", headers=h["owner"], json={**fields, "attachments": attachments}
            ).status_code
            == 422
        )
    row, _ = create(
        client, base, h["owner"], attachments=[{"filename": "notes.txt", "content": "a" * 32768}]
    )
    second, _ = create(client, base, h["owner"], subject="Second request")
    url = base + "/tickets/" + row["id"]
    assert client.get(base + "/tickets?queue=mine&limit=0", headers=h["owner"]).status_code == 422
    page = client.get(base + "/tickets?queue=mine&limit=1", headers=h["owner"]).json()
    assert len(page["items"]) == 1 and page["next_cursor"]
    page2 = client.get(
        base + "/tickets?queue=mine&limit=1&cursor=" + page["next_cursor"], headers=h["owner"]
    ).json()
    assert (
        len(page2["items"]) == 1
        and page2["items"][0]["id"] != page["items"][0]["id"]
        and page2["next_cursor"] is None
    )
    assert (
        client.get(url + "/history?cursor=" + str(uuid4()), headers=h["owner"]).status_code == 422
    )
    message = client.get(url + "/messages", headers=h["owner"]).json()["items"][0]
    download_url = url + "/attachments/" + message["attachments"][0]["id"]
    result = client.get(download_url, headers=h["owner"])
    assert result.status_code == 200 and len(result.content) == 32768
    assert (
        result.headers["cache-control"] == "no-store"
        and result.headers["x-content-type-options"] == "nosniff"
    )
    assert result.headers["content-disposition"] == 'attachment; filename="helpdesk-attachment.txt"'
    assert client.get(download_url, headers=h["peer"]).status_code == 403
    row = command(
        client,
        url + "/assignment",
        h["admin"],
        row,
        assignee_user_id=ids["staff"],
        reason="Immutable assignment",
    )
    row = command(
        client, url + "/messages", h["staff"], row, body="Shared pagination reply", internal=False
    )
    first = client.get(url + "/messages?limit=1", headers=h["owner"]).json()
    assert first["next_cursor"] == message["id"]
    last = client.get(
        url + "/messages?limit=1&cursor=" + first["next_cursor"], headers=h["owner"]
    ).json()
    assert last["next_cursor"] is None and last["items"][0]["body"] == "Shared pagination reply"
    with Session(engine) as db:
        models = (HelpdeskMessage, HelpdeskAttachment, HelpdeskHistory, HelpdeskAssignment)
        for model in models:
            ident = db.scalar(select(model.id))
            assert ident
            with pytest.raises(DBAPIError):
                db.execute(delete(model).where(model.id == ident))
                db.commit()
            db.rollback()
            with pytest.raises(DBAPIError):
                db.execute(update(model).where(model.id == ident).values(created_at=func.now()))
                db.commit()
            db.rollback()
        for values in (
            {"status": "closed", "version": row["version"] + 1},
            {"version": row["version"]},
            {"subject": "Changed subject", "version": row["version"] + 1},
            {"organization_id": other, "version": row["version"] + 1},
        ):
            with pytest.raises(DBAPIError):
                db.execute(
                    update(HelpdeskTicket)
                    .where(HelpdeskTicket.id == UUID(row["id"]))
                    .values(**values)
                )
                db.commit()
            db.rollback()
        # Even a syntactically valid increment cannot commit without matching immutable history.
        with pytest.raises(DBAPIError):
            db.execute(
                update(HelpdeskTicket)
                .where(HelpdeskTicket.id == UUID(row["id"]))
                .values(version=row["version"] + 1)
            )
            db.commit()
        db.rollback()
        assert db.scalar(
            select(AuditLog.id).where(
                AuditLog.organization_id == org, AuditLog.action == "helpdesk.attachment_download"
            )
        )
