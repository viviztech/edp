import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_file_foundation_db import rules
from test_helpdesk_db import command, context
from test_helpdesk_db import create as create_ticket
from test_identity import auth  # noqa: F401

from app.core.config import get_settings
from app.modules.files import service as core_files
from app.modules.files.models import FileObject
from app.modules.files.scanner import ScanResult
from app.modules.files.schemas import FilePolicyCommand, FilePolicyCreate
from app.modules.helpdesk import file_routes, file_service
from app.modules.helpdesk import service as helpdesk
from app.modules.helpdesk.file_models import HelpdeskFile
from app.modules.helpdesk.file_schemas import HelpdeskFileIntent
from app.modules.helpdesk.models import HelpdeskMessage, HelpdeskTicket
from app.modules.helpdesk.schemas import AssignmentChange
from app.modules.identity.models import RefreshSession, Role, User, UserRole, now
from app.modules.identity.security import AuthError

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)
PDF = b"%PDF-1.4\nSynthetic helpdesk file acceptance\n%%EOF"


@pytest.fixture
def helpdesk_files(request, tmp_path, monkeypatch):
    client, engine, base, org, other, enrollment, headers, ids = context(request)
    temp = tmp_path / "temp"
    temp.mkdir(mode=0o700)
    for name, value in {
        "FILES_ENABLED": "true",
        "FILES_STORAGE_BACKEND": "local",
        "FILES_LOCAL_ROOT": str(tmp_path / "objects"),
        "FILES_TEMP_ROOT": str(temp),
        "FILES_MAX_BYTES": "1024",
    }.items():
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()
    with Session(engine) as db:
        director = db.get(User, UUID(ids["admin"]))
        role = db.scalar(select(Role).where(Role.name == "Program Director"))
        db.add(UserRole(user_id=director.id, role_id=role.id, organization_id=org))
        db.commit()
        policy = core_files.create_policy(
            db,
            org,
            director,
            FilePolicyCreate(**rules(purpose="helpdesk_attachment", max_files=2)),
            "policy",
        )
        policy = core_files.publish_policy(
            db,
            org,
            policy.id,
            director,
            FilePolicyCommand(expected_version=1, reason="Synthetic helpdesk policy approval"),
            "publish",
        )
    ticket, _ = create_ticket(
        client,
        base,
        headers["owner"],
        attachments=[
            {
                "filename": "legacy.txt",
                "content": "Synthetic legacy TXT compatibility",
            }
        ],
    )
    url = base + "/tickets/" + ticket["id"]
    ticket = command(
        client,
        url + "/assignment",
        headers["admin"],
        ticket,
        assignee_user_id=ids["staff"],
        reason="Synthetic support assignment",
    )
    return {
        "client": client,
        "engine": engine,
        "base": base,
        "url": url,
        "files": url + "/files",
        "org": org,
        "other": other,
        "enrollment": enrollment,
        "h": headers,
        "ids": {key: UUID(value) for key, value in ids.items()},
        "ticket": ticket,
        "policy": policy,
        "temp": temp,
    }


def metadata(f, **changes):
    return {
        "client_request_id": str(uuid4()),
        "policy_id": str(f["policy"].id),
        "internal": False,
        "media_type": "application/pdf",
        "byte_size": len(PDF),
        "sha256": hashlib.sha256(PDF).hexdigest(),
        **changes,
    }


def stage(f, actor="owner", **changes):
    response = f["client"].post(f["files"], headers=f["h"][actor], json=metadata(f, **changes))
    assert response.status_code == 201, response.text
    return response.json()


def upload(f, item, actor="owner"):
    response = f["client"].put(
        f["files"] + f"/{item['id']}/content",
        content=PDF,
        headers={
            **f["h"][actor],
            "Content-Type": "application/pdf",
            "If-Match": f'"{item["file"]["version"]}"',
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def scan(f, item, status="clean"):
    with Session(f["engine"]) as db:
        lease = core_files.claim_scan(db, f["org"], UUID(item["file"]["id"]), "claim-scan")
        core_files.finish_scan(
            db,
            f["org"],
            lease,
            ScanResult(
                status,
                hashlib.sha256(PDF).hexdigest(),
                len(PDF),
                status,
            ),
            "scan",
        )
    return item


def ready(f, actor="owner", **changes):
    return scan(f, upload(f, stage(f, actor, **changes), actor))


def reply(f, items, actor="owner", internal=False):
    current = f["client"].get(f["url"], headers=f["h"][actor]).json()
    return f["client"].post(
        f["url"] + "/messages",
        headers=f["h"][actor],
        json={
            "expected_version": current["version"],
            "body": "Synthetic file-backed message",
            "internal": internal,
            "file_ids": [item["id"] for item in items],
        },
    )


def test_shared_file_freezes_with_reply_and_legacy_txt_survives(helpdesk_files):
    f = helpdesk_files
    item = ready(f)
    assert f["client"].get(f["url"], headers=f["h"]["owner"]).json()["version"] == 2
    response = reply(f, [item])
    assert response.status_code == 200, response.text
    messages = f["client"].get(f["url"] + "/messages", headers=f["h"]["owner"]).json()["items"]
    assert messages[0]["files"] == []
    legacy = messages[0]["attachments"][0]
    assert (
        f["client"].get(f["url"] + "/attachments/" + legacy["id"], headers=f["h"]["owner"]).content
        == b"Synthetic legacy TXT compatibility"
    )
    posted = messages[-1]["files"][0]
    assert posted["state"] == "posted" and posted["usable"] and posted["evidence"]
    assert "storage_version" not in str(posted) and "object_key" not in str(posted)
    downloaded = f["client"].get(f["files"] + f"/{item['id']}/content", headers=f["h"]["staff"])
    assert downloaded.status_code == 200 and downloaded.content == PDF
    assert downloaded.headers["cache-control"] == "private, no-store"
    with Session(f["engine"]) as db:
        row = db.get(HelpdeskFile, UUID(item["id"]))
        file = db.get(FileObject, row.file_id)
        assert row.frozen_storage_version == file.storage_version and file.evidence_frozen
        assert row.frozen_sha256 == hashlib.sha256(PDF).hexdigest()
    assert (
        f["client"]
        .request(
            "DELETE",
            f["files"] + f"/{item['id']}",
            headers=f["h"]["owner"],
            json={"expected_version": posted["version"]},
        )
        .status_code
        == 409
    )


def test_private_note_and_current_assignment_control_metadata_and_bytes(
    helpdesk_files, monkeypatch
):
    f = helpdesk_files
    item = ready(f, "staff", internal=True)
    path = f["files"] + f"/{item['id']}"
    for actor in ("owner", "admin"):
        # Even an administrator cannot inspect another person's staged file.
        assert f["client"].get(path, headers=f["h"][actor]).status_code == 404
    response = reply(f, [item], "staff", internal=True)
    assert response.status_code == 200, response.text
    for suffix in ("", "/content"):
        assert f["client"].get(path + suffix, headers=f["h"]["owner"]).status_code == 404
    assert f["client"].get(path, headers=f["h"]["admin"]).status_code == 200
    owner_messages = f["client"].get(f["url"] + "/messages", headers=f["h"]["owner"]).json()
    assert len(owner_messages["items"]) == 1 and item["id"] not in str(owner_messages)
    assert (
        f["client"].get(f["files"] + "?cursor=" + item["id"], headers=f["h"]["owner"]).status_code
        == 400
    )
    for actor in ("peer", "outsider", "second"):
        assert f["client"].get(path, headers=f["h"][actor]).status_code == 403
    assert (
        f["client"]
        .get(path.replace(str(f["org"]), str(f["other"])), headers=f["h"]["admin"])
        .status_code
        == 404
    )
    original = file_routes.private_download

    def snapshot_then_handover(*args, **kwargs):
        result = original(*args, **kwargs)
        with Session(f["engine"]) as db:
            ticket = db.get(HelpdeskTicket, UUID(f["ticket"]["id"]))
            helpdesk.assign(
                db,
                f["org"],
                ticket.id,
                db.get(User, f["ids"]["admin"]),
                AssignmentChange(
                    expected_version=ticket.version,
                    assignee_user_id=f["ids"]["second"],
                    reason="Synthetic provider-time handover",
                ),
                "handover",
            )
        return result

    monkeypatch.setattr(file_routes, "private_download", snapshot_then_handover)
    assert f["client"].get(path + "/content", headers=f["h"]["staff"]).status_code == 403
    assert not list(f["temp"].iterdir())
    monkeypatch.setattr(file_routes, "private_download", original)
    assert f["client"].get(path + "/content", headers=f["h"]["second"]).status_code == 200


def test_pending_infected_and_wrong_visibility_cannot_post(helpdesk_files):
    f = helpdesk_files
    pending = stage(f)
    assert reply(f, [pending]).status_code == 409
    scan(f, upload(f, pending), status="infected")
    assert reply(f, [pending]).status_code == 409
    assert (
        f["client"]
        .get(f["files"] + f"/{pending['id']}/content", headers=f["h"]["owner"])
        .status_code
        == 409
    )
    private = ready(f, "staff", internal=True)
    assert reply(f, [private], "staff", internal=False).status_code == 409
    assert f["client"].get(f["url"], headers=f["h"]["owner"]).json()["version"] == 2
    with Session(f["engine"]) as db:
        assert db.scalar(select(func.count()).select_from(HelpdeskMessage)) == 1


def test_freeze_failure_rolls_back_whole_message(helpdesk_files, monkeypatch):
    f = helpdesk_files
    one, two = ready(f), ready(f)
    original, calls = core_files.freeze_evidence, []

    def fail_second(*args, **kwargs):
        calls.append(True)
        if len(calls) == 2:
            raise AuthError("synthetic_freeze_failure", 503)
        return original(*args, **kwargs)

    monkeypatch.setattr(core_files, "freeze_evidence", fail_second)
    response = reply(f, [one, two])
    assert response.status_code == 503, response.text
    with Session(f["engine"]) as db:
        assert db.scalar(select(func.count()).select_from(HelpdeskMessage)) == 1
        assert db.get(HelpdeskTicket, UUID(f["ticket"]["id"])).version == 2
        assert list(db.scalars(select(HelpdeskFile.state))) == ["staged", "staged"]
        assert not any(db.scalars(select(FileObject.evidence_frozen)))


def test_message_selection_and_frozen_binding_cannot_be_extended(helpdesk_files):
    f = helpdesk_files
    one, two = ready(f), ready(f)
    response = reply(f, [one])
    assert response.status_code == 200, response.text
    with Session(f["engine"]) as db:
        posted = db.get(HelpdeskFile, UUID(one["id"]))
        message = db.get(HelpdeskMessage, posted.message_id)
        message.shared_file_ids = [UUID(one["id"]), UUID(two["id"])]
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()
        second = db.get(HelpdeskFile, UUID(two["id"]))
        actor = db.get(User, f["ids"]["owner"])
        file = db.get(FileObject, second.file_id)
        core_files.freeze_evidence(
            db,
            file_service.file_context(second, actor),
            actor,
            file.id,
            file.version,
            "illegal-append",
            commit=False,
        )
        second.state, second.version, second.message_id = "posted", 2, message.id
        second.frozen_file_version, second.frozen_storage_version = (
            file.version,
            file.storage_version,
        )
        second.frozen_sha256, second.frozen_byte_size, second.frozen_at = (
            file.stored_sha256,
            file.stored_byte_size,
            now(),
        )
        with pytest.raises(DBAPIError, match="selected exact clean"):
            db.commit()
        db.rollback()
        assert db.get(HelpdeskFile, UUID(two["id"])).state == "staged"
        # A forged message selection cannot commit without the atomic freeze/bind.
        ticket = db.get(HelpdeskTicket, UUID(f["ticket"]["id"]))
        ticket.version += 1
        helpdesk.add_message(
            db, ticket, actor, "Synthetic missing freeze", False, [], [UUID(two["id"])]
        )
        helpdesk.evidence(db, ticket, actor, "shared_reply", "", "forged-no-freeze")
        with pytest.raises(DBAPIError, match="selected files require immutable"):
            db.commit()
        db.rollback()


def test_metadata_replay_count_remove_and_concurrent_recovery(helpdesk_files):
    f = helpdesk_files
    data = HelpdeskFileIntent(**metadata(f))

    def attempt():
        with Session(f["engine"]) as db:
            return file_service.create(
                db,
                f["org"],
                UUID(f["ticket"]["id"]),
                db.get(User, f["ids"]["owner"]),
                data,
                "concurrent",
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert results[0].id == results[1].id
    response = f["client"].post(
        f["files"],
        headers=f["h"]["owner"],
        json={**data.model_dump(mode="json"), "byte_size": len(PDF) + 1},
    )
    assert response.status_code == 409
    stage(f)
    assert (
        f["client"].post(f["files"], headers=f["h"]["owner"], json=metadata(f)).status_code == 409
    )
    item = results[0]
    removed = f["client"].request(
        "DELETE",
        f["files"] + f"/{item.id}",
        headers=f["h"]["owner"],
        json={"expected_version": item.version},
    )
    assert removed.status_code == 200 and removed.json()["state"] == "removed"
    assert f["client"].get(f["files"] + f"/{item.id}", headers=f["h"]["owner"]).status_code == 200
    assert stage(f)


@pytest.mark.parametrize("change,expected_status", [("revoked", 401), ("handover", 403)])
def test_upload_reauth_after_body_and_private_buffer_cleanup(
    helpdesk_files,
    monkeypatch,
    change,
    expected_status,
):
    f = helpdesk_files
    item = stage(f, "staff", internal=True)
    original = file_routes.bounded_upload

    @asynccontextmanager
    async def interrupted(*args, **kwargs):
        async with original(*args, **kwargs) as source:
            with Session(f["engine"]) as db:
                if change == "revoked":
                    for family in db.scalars(
                        select(RefreshSession).where(RefreshSession.user_id == f["ids"]["staff"])
                    ):
                        family.revoked_at = now()
                    db.commit()
                else:
                    ticket = db.get(HelpdeskTicket, UUID(f["ticket"]["id"]))
                    helpdesk.assign(
                        db,
                        f["org"],
                        ticket.id,
                        db.get(User, f["ids"]["admin"]),
                        AssignmentChange(
                            expected_version=ticket.version,
                            assignee_user_id=f["ids"]["second"],
                            reason="Synthetic concurrent handover",
                        ),
                        "handover",
                    )
            yield source

    monkeypatch.setattr(file_routes, "bounded_upload", interrupted)
    response = f["client"].put(
        f["files"] + f"/{item['id']}/content",
        content=PDF,
        headers={
            **f["h"]["staff"],
            "Content-Type": "application/pdf",
            "If-Match": '"1"',
        },
    )
    assert response.status_code == expected_status, response.text
    with Session(f["engine"]) as db:
        assert db.get(FileObject, UUID(item["file"]["id"])).state == "pending"
    assert not list(f["temp"].iterdir())


def test_collection_off_and_expired_clean_remain_unavailable(helpdesk_files, monkeypatch):
    f = helpdesk_files
    item = ready(f)
    monkeypatch.setattr(file_service, "now", lambda: now() + timedelta(days=2))
    detail = f["client"].get(f["files"] + f"/{item['id']}", headers=f["h"]["owner"])
    assert detail.json()["usable"] is False
    assert reply(f, [item]).status_code == 409
    monkeypatch.setenv("FILES_ENABLED", "false")
    get_settings.cache_clear()
    assert (
        f["client"].get(f["files"], headers=f["h"]["owner"]).json()["collection_enabled"] is False
    )
    assert (
        f["client"].post(f["files"], headers=f["h"]["owner"], json=metadata(f)).status_code == 503
    )
    assert (
        f["client"].get(f["files"] + f"/{item['id']}/content", headers=f["h"]["owner"]).status_code
        == 503
    )
    # Text-only replies and the existing bounded TXT path remain available.
    assert reply(f, []).status_code == 200
