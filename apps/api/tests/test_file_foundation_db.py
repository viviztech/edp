import hashlib
import io
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_identity import auth  # noqa: F401

from app.modules.files import service
from app.modules.files.models import FileObject, FilePolicy
from app.modules.files.scanner import ScanResult
from app.modules.files.schemas import (
    FileCreate,
    FilePolicyCommand,
    FilePolicyCreate,
    FilePolicyUpdate,
)
from app.modules.files.storage import LocalPrivateStorage
from app.modules.identity.models import AuditLog, Organization, Person, Role, User, UserRole, now
from app.modules.identity.security import AuthError, hasher

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)
PDF = b"%PDF-1.4\nSynthetic private foundation evidence\n%%EOF"


def rules(**changes):
    return {
        "client_request_id": uuid4(),
        "purpose": "application_document",
        "name": "Synthetic file policy",
        "notice_en": "Synthetic test notice only.",
        "notice_ta": "செயற்கை சோதனை அறிவிப்பு மட்டுமே.",
        "allowed_mime_types": ["text/plain", "application/pdf"],
        "max_file_bytes": 1024,
        "max_files": 5,
        "retention_days": 1,
        "rejected_retention_days": 1,
        "allow_frozen_disposal": False,
        "reason": "Synthetic acceptance policy",
        **changes,
    }


@pytest.fixture
def files_db(request, tmp_path, monkeypatch):
    _, engine, _, _ = request.getfixturevalue("auth")
    clock = [now()]
    monkeypatch.setattr(service, "now", lambda: clock[0])
    with Session(engine) as db:
        org, other = Organization(name="Synthetic files"), Organization(name="Unrelated files")
        people = [Person(display_name=name) for name in ("Director", "Owner", "Peer")]
        db.add_all([org, other, *people])
        db.flush()
        users = [
            User(
                person_id=person.id,
                email=f"files-{index}@example.com",
                password_hash=hasher.hash("Synthetic password 123"),
                status="active",
            )
            for index, person in enumerate(people)
        ]
        db.add_all(users)
        db.flush()
        role = db.scalar(select(Role).where(Role.name == "Program Director"))
        assert role
        db.add(UserRole(user_id=users[0].id, role_id=role.id, organization_id=org.id))
        db.commit()
        policy = service.create_policy(db, org.id, users[0], FilePolicyCreate(**rules()), "create")
        policy = service.publish_policy(
            db,
            org.id,
            policy.id,
            users[0],
            FilePolicyCommand(expected_version=1, reason="Synthetic approval only"),
            "publish",
        )
        yield {
            "engine": engine,
            "org": org.id,
            "other": other.id,
            "director": users[0].id,
            "owner": users[1].id,
            "peer": users[2].id,
            "policy": policy,
            "clock": clock,
            "storage": LocalPrivateStorage(tmp_path / "private", max_bytes=1024),
        }


def context(actor, org, resource=None):
    return service.AuthorizedFileContext(
        actor.id, org, actor.person_id, "application_document", resource or uuid4()
    )


def metadata(policy_id, data=PDF, **changes):
    return FileCreate(
        **{
            "client_request_id": uuid4(),
            "policy_id": policy_id,
            "media_type": "application/pdf",
            "byte_size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            **changes,
        }
    )


def upload(db, fixture, actor, ctx, *, policy=None, created_at=None):
    if created_at is not None:
        fixture["clock"][0] = created_at
    item = service.create_file(db, ctx, actor, metadata((policy or fixture["policy"]).id), "file")
    fixture["clock"][0] = now()
    lease = service.begin_upload(db, ctx, actor, item.id, item.version, "claim")
    return service.receive_upload(
        db, ctx, actor, lease, io.BytesIO(PDF), fixture["storage"], "upload"
    )


def clean(db, fixture, item):
    lease = service.claim_scan(db, fixture["org"], item.id, "scan-claim")
    return service.finish_scan(
        db,
        fixture["org"],
        lease,
        ScanResult("clean", hashlib.sha256(PDF).hexdigest(), len(PDF), "clean"),
        "scan",
    )


def test_policy_editions_replay_scope_and_published_immutability(files_db):
    f = files_db
    with Session(f["engine"]) as db:
        director, peer = db.get(User, f["director"]), db.get(User, f["peer"])
        assert director and peer
        data = FilePolicyCreate(**rules(copy_from=f["policy"].id))
        created = service.create_policy(db, f["org"], director, data, "next")
        assert created.edition == 2
        assert (
            db.scalar(
                select(AuditLog.reason).where(
                    AuditLog.resource_id == created.id,
                    AuditLog.action == "files.policy.created",
                )
            )
            == data.reason
        )
        assert service.create_policy(db, f["org"], director, data, "retry").id == created.id
        with pytest.raises(AuthError) as changed:
            service.create_policy(
                db, f["org"], director, data.model_copy(update={"name": "Changed reuse"}), "changed"
            )
        assert changed.value.code == "idempotency_conflict"
        with pytest.raises(AuthError) as denied:
            service.list_policies(db, f["org"], peer)
        assert denied.value.status == 403
        with pytest.raises(AuthError):
            service.get_policy(db, f["other"], created.id, director)
        updated = service.update_policy(
            db,
            f["org"],
            created.id,
            director,
            FilePolicyUpdate(
                **{
                    key: value
                    for key, value in rules().items()
                    if key not in {"client_request_id", "purpose"}
                },
                expected_version=1,
            ),
            "update",
        )
        with pytest.raises(AuthError) as stale:
            service.publish_policy(
                db,
                f["org"],
                created.id,
                director,
                FilePolicyCommand(expected_version=1, reason="Stale"),
                "stale",
            )
        assert stale.value.code == "version_conflict"
        published = service.publish_policy(
            db,
            f["org"],
            created.id,
            director,
            FilePolicyCommand(expected_version=updated.version, reason="Synthetic"),
            "publish",
        )
        assert published.state == "published"
        assert db.get(FilePolicy, f["policy"].id).state == "retired"
        row = db.get(FilePolicy, published.id)
        row.max_file_bytes = 999
        row.version += 1
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()
        with pytest.raises(AuthError) as cursor:
            service.list_policies(db, f["org"], director, cursor=uuid4())
        assert cursor.value.code == "invalid_cursor"


def test_normalized_file_replay_scope_bounds_and_concurrent_creation(files_db):
    f = files_db
    with Session(f["engine"]) as db:
        actor, peer = db.get(User, f["owner"]), db.get(User, f["peer"])
        assert actor and peer
        ctx = context(actor, f["org"])
        data = metadata(f["policy"].id)
        first = service.create_file(db, ctx, actor, data, "create")
        replay = FileCreate(**{**data.model_dump(), "sha256": data.sha256.upper()})
        assert service.create_file(db, ctx, actor, replay, "retry").id == first.id
        assert (
            "object_key" not in first.model_dump() and "storage_version" not in first.model_dump()
        )
        with pytest.raises(AuthError) as conflict:
            service.create_file(
                db, ctx, actor, data.model_copy(update={"byte_size": 99}), "changed"
            )
        assert conflict.value.code == "idempotency_conflict"
        with pytest.raises(AuthError) as hidden:
            service.get_file(db, context(peer, f["org"], ctx.resource_id), peer, first.id)
        assert hidden.value.status == 404
        with pytest.raises(AuthError):
            service.get_file(db, replace(ctx, actor_user_id=peer.id), actor, first.id)
        with pytest.raises(AuthError) as invalid:
            service.create_file(
                db,
                replace(ctx, resource_id=uuid4()),
                actor,
                metadata(f["policy"].id, byte_size=1025),
                "size",
            )
        assert invalid.value.code == "file_policy_rejected"
        concurrent_data = metadata(f["policy"].id)
        actor_id = actor.id

    def create_once(_):
        with Session(f["engine"]) as db:
            actor = db.get(User, actor_id)
            return service.create_file(db, ctx, actor, concurrent_data, "parallel").id

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(create_once, range(2)))
    assert ids[0] == ids[1]


def test_upload_verifies_real_type_size_hash_and_never_accepts_unverified_clean(files_db):
    f = files_db
    with Session(f["engine"]) as db:
        actor = db.get(User, f["owner"])
        assert actor
        for contents, overrides in (
            (b"not a PDF", {}),
            (PDF, {"byte_size": len(PDF) - 1}),
            (PDF, {"sha256": "0" * 64}),
        ):
            ctx = context(actor, f["org"])
            item = service.create_file(
                db, ctx, actor, metadata(f["policy"].id, data=contents, **overrides), "create"
            )
            lease = service.begin_upload(db, ctx, actor, item.id, item.version, "claim")
            with pytest.raises(AuthError) as rejected:
                service.receive_upload(
                    db, ctx, actor, lease, io.BytesIO(contents), f["storage"], "bad"
                )
            assert rejected.value.code == "file_upload_failed"
            row = db.get(FileObject, item.id)
            assert row.state == "rejected" and row.verified_at is None
        ctx = context(actor, f["org"])
        pending = service.create_file(db, ctx, actor, metadata(f["policy"].id), "pending")
        row = db.get(FileObject, pending.id)
        row.state = "clean"
        row.version += 1
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()


def test_expired_upload_and_scan_leases_fence_stale_workers(files_db):
    f = files_db
    with Session(f["engine"]) as db:
        actor = db.get(User, f["owner"])
        assert actor
        ctx = context(actor, f["org"])
        item = service.create_file(db, ctx, actor, metadata(f["policy"].id), "pending")
        first = service.begin_upload(db, ctx, actor, item.id, item.version, "first", 10)
        f["clock"][0] += timedelta(seconds=11)
        second = service.begin_upload(db, ctx, actor, item.id, first.version, "second", 10)
        with pytest.raises(AuthError) as stale:
            service.receive_upload(db, ctx, actor, first, io.BytesIO(PDF), f["storage"], "stale")
        assert stale.value.code == "file_lease_lost"
        item = service.receive_upload(
            db, ctx, actor, second, io.BytesIO(PDF), f["storage"], "current"
        )
        old_scan = service.claim_scan(db, f["org"], item.id, "scan-first", 10)
        f["clock"][0] += timedelta(seconds=11)
        new_scan = service.claim_scan(db, f["org"], item.id, "scan-second", 10)
        result = ScanResult("clean", item.sha256, item.byte_size, "clean")
        with pytest.raises(AuthError) as old:
            service.finish_scan(db, f["org"], old_scan, result, "stale-scan")
        assert old.value.code == "file_lease_lost"
        assert service.finish_scan(db, f["org"], new_scan, result, "current-scan").state == "clean"
        row = db.get(FileObject, item.id)
        row.storage_version = "changed-version"
        row.version += 1
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()


def test_scanner_mismatch_unavailable_and_corrupt_read_fail_closed(files_db):
    f = files_db
    with Session(f["engine"]) as db:
        actor = db.get(User, f["owner"])
        assert actor
        item = upload(db, f, actor, context(actor, f["org"]))
        lease = service.claim_scan(db, f["org"], item.id, "mismatch")
        rejected = service.finish_scan(
            db, f["org"], lease, ScanResult("clean", "f" * 64, item.byte_size, "clean"), "mismatch"
        )
        assert rejected.state == "rejected" and rejected.failure_code == "scan_integrity_mismatch"
        item = upload(db, f, actor, context(actor, f["org"]))
        for attempt in range(3):
            lease = service.claim_scan(db, f["org"], item.id, "error")
            item = service.finish_scan(
                db,
                f["org"],
                lease,
                ScanResult("error", "", 0, "Untrusted provider diagnostic"),
                "error",
            )
            assert item.state == ("rejected" if attempt == 2 else "quarantined")
            assert item.failure_code == "scan_unavailable"
            f["clock"][0] += timedelta(seconds=300)
        assert "Untrusted provider diagnostic" not in item.model_dump_json()


def test_cleanup_obeys_legal_hold_and_published_frozen_disposal_policy(files_db):
    f = files_db
    with Session(f["engine"]) as db:
        actor, director = db.get(User, f["owner"]), db.get(User, f["director"])
        assert actor and director
        ctx = context(actor, f["org"])
        item = clean(db, f, upload(db, f, actor, ctx, created_at=now() - timedelta(days=3)))
        item = service.freeze_evidence(db, ctx, actor, item.id, item.version, "freeze")
        held = service.set_legal_hold(db, ctx, actor, item.id, item.version, True, "hold")
        with pytest.raises(AuthError) as hold:
            service.cleanup_file(db, f["org"], held.id, held.version, f["storage"], "cleanup")
        assert hold.value.code == "file_disposal_denied"
        item = service.set_legal_hold(db, ctx, actor, item.id, held.version, False, "release")
        with pytest.raises(AuthError):
            service.cleanup_file(db, f["org"], item.id, item.version, f["storage"], "frozen")
        authorized = service.create_policy(
            db,
            f["org"],
            director,
            FilePolicyCreate(**rules(allow_frozen_disposal=True)),
            "new-policy",
        )
        authorized = service.publish_policy(
            db,
            f["org"],
            authorized.id,
            director,
            FilePolicyCommand(expected_version=1, reason="Synthetic disposal rule"),
            "publish",
        )
        ctx = context(actor, f["org"])
        disposable = clean(
            db,
            f,
            upload(db, f, actor, ctx, policy=authorized, created_at=now() - timedelta(days=3)),
        )
        disposable = service.freeze_evidence(
            db, ctx, actor, disposable.id, disposable.version, "freeze"
        )
        assert (f["org"], disposable.id, disposable.version) in service.cleanup_candidates(db)
        disposed = service.cleanup_file(
            db, f["org"], disposable.id, disposable.version, f["storage"], "cleanup"
        )
        assert disposed.state == "deleted" and disposed.deleted_at
        assert db.scalar(select(func.count()).select_from(FileObject)) == 2
        audit = list(db.scalars(select(AuditLog).where(AuditLog.resource_id == disposed.id)))
        assert all(
            "quarantine/" not in str(row.changed_fields)
            and "Synthetic private" not in str(row.reason)
            for row in audit
        )


def test_concurrent_upload_claims_have_one_winner_and_abandoned_rows_retain_metadata(files_db):
    f = files_db
    with Session(f["engine"]) as db:
        actor = db.get(User, f["owner"])
        assert actor
        ctx = context(actor, f["org"])
        item = service.create_file(db, ctx, actor, metadata(f["policy"].id), "create")

    def claim_once(_):
        with Session(f["engine"]) as db:
            actor = db.get(User, f["owner"])
            try:
                return service.begin_upload(db, ctx, actor, item.id, 1, "parallel")
            except AuthError as error:
                return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(claim_once, range(2)))
    assert sum(isinstance(result, service.FileLease) for result in results) == 1
    assert "version_conflict" in results
    with Session(f["engine"]) as db:
        actor = db.get(User, f["owner"])
        f["clock"][0] = now() - timedelta(days=3)
        abandoned = service.create_file(
            db, context(actor, f["org"]), actor, metadata(f["policy"].id), "abandoned"
        )
        f["clock"][0] = now()
        assert (f["org"], abandoned.id, 1) in service.abandoned_candidates(db)
        rejected = service.reject_abandoned(
            db, f["org"], abandoned.id, 1, "reject", storage=f["storage"]
        )
        assert rejected.failure_code == "upload_abandoned"
        assert db.get(FileObject, abandoned.id).object_key


def test_scan_worker_reads_exact_version_and_provider_errors_never_become_clean(files_db):
    class DigestScanner:
        def scan(self, source, *, max_bytes):
            contents = source.read(max_bytes + 1)
            return ScanResult("clean", hashlib.sha256(contents).hexdigest(), len(contents), "clean")

    class UnavailableScanner:
        def scan(self, source, *, max_bytes):
            raise OSError("Provider detail must never escape")

    f = files_db
    with Session(f["engine"]) as db:
        actor = db.get(User, f["owner"])
        item = upload(db, f, actor, context(actor, f["org"]))
        lease = service.claim_scan(db, f["org"], item.id, "claim")
        assert (
            service.scan_with_lease(
                db, f["org"], lease, f["storage"], DigestScanner(), "worker"
            ).state
            == "clean"
        )
        item = upload(db, f, actor, context(actor, f["org"]))
        lease = service.claim_scan(db, f["org"], item.id, "claim")
        failed = service.scan_with_lease(
            db, f["org"], lease, f["storage"], UnavailableScanner(), "worker"
        )
        assert failed.state == "quarantined" and failed.failure_code == "scan_unavailable"
        assert "Provider detail" not in failed.model_dump_json()


def test_abandoned_and_late_upload_bytes_are_recovered_before_disposal(files_db):
    f = files_db
    with Session(f["engine"]) as db:
        actor = db.get(User, f["owner"])
        for late in (False, True):
            created_at = now() - timedelta(days=3)
            f["clock"][0] = created_at
            ctx = context(actor, f["org"])
            item = service.create_file(db, ctx, actor, metadata(f["policy"].id), "create")
            lease = service.begin_upload(db, ctx, actor, item.id, item.version, "claim", 10)
            row = db.get(FileObject, item.id)
            key = row.object_key
            if not late:
                # Process died after immutable bytes committed but before finalization.
                f["storage"].put(key, io.BytesIO(PDF), item.media_type, item.byte_size, item.sha256)
            f["clock"][0] = created_at + timedelta(days=1, seconds=1)
            rejected = service.reject_abandoned(
                db, f["org"], item.id, lease.version, "abandoned", storage=f["storage"]
            )
            assert rejected.state == "rejected"
            assert bool(db.get(FileObject, item.id).storage_version) is (not late)
            if late:
                # A stale completion after rejection still cannot escape the later
                # cleanup recovery check, or become accessible as clean evidence.
                f["storage"].put(key, io.BytesIO(PDF), item.media_type, item.byte_size, item.sha256)
            f["clock"][0] = now()
            disposed = service.cleanup_file(
                db, f["org"], item.id, rejected.version, f["storage"], "cleanup"
            )
            assert disposed.state == "deleted" and db.get(FileObject, item.id).storage_version
            assert f["storage"].recover(key, item.media_type, item.byte_size, item.sha256) is None
