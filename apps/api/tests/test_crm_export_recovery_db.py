import csv
import io
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_identity import auth  # noqa: F401

from app.core.config import get_settings
from app.modules.crm import export_service as execution
from app.modules.crm import service
from app.modules.crm.models import ExportJob, Lead
from app.modules.identity.models import AuditLog, Organization, Person, Role, User, UserRole, now
from app.modules.identity.security import AuthError
from app.workers import crm_exports

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)


@pytest.fixture
def exports_db(request, monkeypatch):
    _, engine, _, _ = request.getfixturevalue("auth")
    monkeypatch.setattr(crm_exports, "engine", engine)
    with Session(engine) as db:
        org, other = Organization(name="Synthetic export scope"), Organization(name="Other scope")
        people = [Person(display_name=name) for name in ("Requester", "Peer", "Unprivileged")]
        db.add_all([org, other, *people])
        db.flush()
        users = [
            User(
                person_id=person.id,
                email=f"export-{index}@example.test",
                password_hash="synthetic-not-used",
                status="active",
            )
            for index, person in enumerate(people)
        ]
        db.add_all(users)
        db.flush()
        role = db.scalar(select(Role).where(Role.name == "CRM Executive"))
        assert role
        db.add_all(
            [
                UserRole(user_id=user.id, organization_id=org.id, role_id=role.id)
                for user in users[:2]
            ]
        )
        db.add_all(
            [
                Lead(
                    organization_id=org.id,
                    name="=SUM(A1:A2)",
                    email="=formula@example.test",
                    phone="+919999999999",
                    dedupe_hash="synthetic-export-one",
                ),
                Lead(
                    organization_id=org.id,
                    name="Ordinary, quoted name",
                    dedupe_hash="synthetic-two",
                ),
                Lead(
                    organization_id=other.id, name="Unrelated private contact", dedupe_hash="other"
                ),
            ]
        )
        db.commit()
        return engine, org.id, other.id, [user.id for user in users]


def queued(exports_db, *, expires_in=86400, created_days_ago=0):
    engine, org, _, users = exports_db
    with Session(engine) as db:
        row = ExportJob(
            organization_id=org,
            requested_by_id=users[0],
            created_at=now() - timedelta(days=created_days_ago),
            expires_at=now() + timedelta(seconds=expires_in),
        )
        db.add(row)
        db.commit()
        return row.id


def claim(exports_db, identity, policy=None):
    with Session(exports_db[0]) as db:
        return execution.claim_export(db, identity, policy)


def complete(exports_db, lease):
    assert lease
    with Session(exports_db[0]) as db:
        output = execution.generate_csv(db, lease.organization_id, 10485760)
    with Session(exports_db[0]) as db:
        return execution.complete_export(db, lease, output)


def test_committed_request_never_calls_broker_and_duplicate_execution_completes_once(
    exports_db, monkeypatch
):
    engine, org, _, users = exports_db
    sender = MagicMock(side_effect=RuntimeError("synthetic broker unavailable"))
    monkeypatch.setattr(crm_exports.celery_app, "send_task", sender)
    with Session(engine) as db:
        actor = db.get(User, users[0])
        assert actor
        result = service.request_export(db, org, actor, "synthetic-request")
        assert result.status == "queued"
    sender.assert_not_called()
    with Session(engine) as db:
        ids, settled = execution.recover_exports(db)
        assert ids == [result.id] and settled == 0
    assert crm_exports.export_leads.run(str(result.id)) == {"status": "completed"}
    assert crm_exports.export_leads.run(str(result.id)) == {"status": "ignored"}
    with Session(engine) as db:
        row = db.get(ExportJob, result.id)
        assert row and row.csv_content and row.attempt_count == 1 and row.version == 3
        values = list(csv.reader(io.StringIO(row.csv_content)))
        assert len(values) == 3
        assert any(value[1] == "'=SUM(A1:A2)" and value[2].startswith("'") for value in values[1:])
        assert "Unrelated private contact" not in row.csv_content
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(
                    AuditLog.resource_id == row.id, AuditLog.action == "crm.lead.export_completed"
                )
            )
            == 1
        )


def test_broker_failure_leaves_due_work_discoverable_and_dispatch_is_bounded(
    exports_db, monkeypatch
):
    identity = queued(exports_db)
    publisher = MagicMock(side_effect=RuntimeError("synthetic failure"))
    monkeypatch.setattr(crm_exports, "publish_export", publisher)
    result = crm_exports.recover_exports.run()
    assert result["dispatch_failed"] == 1 and result["published"] == 0
    with Session(exports_db[0]) as db:
        row = db.get(ExportJob, identity)
        assert row and row.status == "queued" and row.attempt_count == 0 and row.version == 1
    publisher.side_effect = None
    result = crm_exports.recover_exports.run()
    assert result["published"] == 1
    assert publisher.call_args.args == (identity,)


def test_concurrent_claims_and_expired_lease_fence_late_success_and_failure(exports_db):
    identity = queued(exports_db)
    short = get_settings().model_copy(update={"crm_export_lease_seconds": 1})
    with ThreadPoolExecutor(max_workers=2) as pool:
        leases = list(pool.map(lambda _: claim(exports_db, identity, short), range(2)))
    live = [lease for lease in leases if lease]
    assert len(live) == 1
    lease = live[0]
    with Session(exports_db[0]) as db:
        assert execution.recover_exports(db, short) == ([], 0)
    time.sleep(1.05)  # Real short synthetic lease; production SQL time guards remain intact.
    with Session(exports_db[0]) as db:
        assert execution.recover_exports(db, short) == ([], 1)
        row = db.get(ExportJob, identity)
        assert row and row.status == "queued" and row.attempt_count == 1
        assert row.error_code == "recovered_lease"
        retry_version = row.version
    with Session(exports_db[0]) as db:
        assert not execution.complete_export(db, lease, execution.ExportContent("stale", 1))
        assert not execution.fail_export(db, lease, "generation_failed", retryable=True)
        row = db.get(ExportJob, identity)
        assert row and row.version == retry_version and row.csv_content is None


def test_final_attempt_crash_settles_failed_and_retry_does_not_reset_budget(exports_db):
    identity = queued(exports_db)
    policy = get_settings().model_copy(
        update={"crm_export_lease_seconds": 1, "crm_export_max_attempts": 1}
    )
    lease = claim(exports_db, identity, policy)
    assert lease
    time.sleep(1.05)
    with Session(exports_db[0]) as db:
        assert execution.recover_exports(db, policy) == ([], 1)
        row = db.get(ExportJob, identity)
        assert row and row.status == "failed" and row.error_code == "retry_exhausted"
        assert row.attempt_count == 1 and row.lease_until is None
    assert claim(exports_db, identity, policy) is None


@pytest.mark.parametrize("change", ["revoke", "suspend"])
def test_current_requester_checked_before_and_after_generation_even_with_cached_user(
    exports_db, change
):
    engine, org, _, users = exports_db
    identity = queued(exports_db)
    with Session(engine, expire_on_commit=False) as stale:
        cached = stale.get(User, users[0])
        assert cached and cached.status == "active"
        lease = execution.claim_export(stale, identity)
        assert lease
        output = execution.generate_csv(stale, org, 10485760)
        stale.commit()  # Release the read transaction, preserving its identity map.
        with Session(engine) as changed:
            if change == "revoke":
                changed.execute(delete(UserRole).where(UserRole.user_id == users[0]))
            else:
                changed.get(User, users[0]).status = "suspended"
            changed.commit()
        assert not execution.complete_export(stale, lease, output)
        row = stale.get(ExportJob, identity, populate_existing=True)
        assert row and row.status == "failed" and row.error_code == "requester_unavailable"
        assert row.csv_content is None
    fresh = queued(exports_db)
    assert claim(exports_db, fresh) is None
    with Session(engine) as db:
        assert db.get(ExportJob, fresh).error_code == "requester_unavailable"


def test_access_expiry_before_claim_or_completion_cannot_be_extended(exports_db):
    past = queued(exports_db, expires_in=-1)
    assert claim(exports_db, past) is None
    identity = queued(exports_db, expires_in=1)
    lease = claim(exports_db, identity)
    assert lease
    time.sleep(1.05)
    assert not complete(exports_db, lease)
    with Session(exports_db[0]) as db:
        for key in (past, identity):
            row = db.get(ExportJob, key)
            assert row and row.status == "failed" and row.error_code == "request_expired"
            assert row.csv_content is None


def test_retryable_generation_failure_and_explicit_limits(exports_db, monkeypatch):
    identity = queued(exports_db)
    original = execution.generate_csv
    monkeypatch.setattr(
        execution, "generate_csv", MagicMock(side_effect=RuntimeError("private diagnostic"))
    )
    assert crm_exports.export_leads.run(str(identity)) == {"status": "settled"}
    with Session(exports_db[0]) as db:
        row = db.get(ExportJob, identity)
        assert row and row.status == "queued" and row.error_code == "generation_failed"
        assert row.next_attempt_at > now() and row.attempt_count == 1
        assert execution.recover_exports(db)[0] == []
    limited = queued(exports_db)
    monkeypatch.setattr(
        execution,
        "generate_csv",
        MagicMock(side_effect=execution.ExportLimitError("output_too_large")),
    )
    assert crm_exports.export_leads.run(str(limited)) == {"status": "settled"}
    with Session(exports_db[0]) as db:
        row = db.get(ExportJob, limited)
        assert row and row.status == "failed" and row.error_code == "output_too_large"
    monkeypatch.setattr(execution, "generate_csv", original)
    with Session(exports_db[0]) as db:
        with pytest.raises(execution.ExportLimitError) as error:
            execution.generate_csv(db, exports_db[1], 10)
        assert error.value.code == "output_too_large"
        monkeypatch.setattr(execution, "MAX_EXPORT_ROWS", 1)
        with pytest.raises(execution.ExportLimitError) as error:
            execution.generate_csv(db, exports_db[1], 10485760)
        assert error.value.code == "row_limit_exceeded"


def test_only_current_owner_can_download_and_approved_disposal_retains_metadata(exports_db):
    engine, org, other, users = exports_db
    identity = queued(exports_db, expires_in=1, created_days_ago=2)
    assert complete(exports_db, claim(exports_db, identity))
    with Session(engine) as db:
        policy = get_settings().model_copy(update={"crm_export_retention_days": 1})
        assert execution.dispose_expired(db, policy) == 0
        owner, peer = db.get(User, users[0]), db.get(User, users[1])
        assert service.download_export(db, org, identity, owner, "synthetic-download")
        for actor, scope in ((peer, org), (owner, other)):
            with pytest.raises(AuthError):
                service.get_export(db, scope, identity, actor)
            db.rollback()
    time.sleep(1.05)
    with Session(engine) as db:
        assert execution.dispose_expired(db) == 0  # No invented retention default.
        owner = db.get(User, users[0])
        with pytest.raises(AuthError) as error:
            service.get_export(db, org, identity, owner)
        assert error.value.status == 404
        row = db.get(ExportJob, identity)
        assert row and row.csv_content is not None
        policy = get_settings().model_copy(update={"crm_export_retention_days": 1})
        assert execution.dispose_expired(db, policy) == 1
        row = db.get(ExportJob, identity, populate_existing=True)
        assert row and row.status == "failed" and row.error_code == "expired"
        assert row.csv_content is None and row.disposed_at and row.row_count == 2
        assert execution.dispose_expired(db, policy) == 0
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(
                    AuditLog.resource_id == identity, AuditLog.action == "crm.lead.export_disposed"
                )
            )
            == 1
        )


def test_real_collection_requires_configured_retention_and_blank_is_none(exports_db, monkeypatch):
    engine, org, _, users = exports_db
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CRM_EXPORT_RETENTION_DAYS", "")
    get_settings.cache_clear()
    try:
        policy = get_settings()
        assert policy.crm_export_retention_days is None
        with Session(engine) as db:
            actor = db.get(User, users[0])
            with pytest.raises(AuthError) as error:
                service.request_export(db, org, actor, "synthetic-policy-gate")
            assert error.value.code == "export_retention_unconfigured"
            assert error.value.status == 503
        identity = queued(exports_db)
        assert claim(exports_db, identity, policy) is None
    finally:
        get_settings.cache_clear()


def test_database_rejects_identity_invalid_leases_terminal_rewrites_and_version_regression(
    exports_db,
):
    engine, _, _, users = exports_db
    identity = queued(exports_db)
    statements = [
        "UPDATE crm_export_jobs SET requested_by_id=:peer,version=version+1 WHERE id=:id",
        "UPDATE crm_export_jobs SET expires_at=expires_at+interval '1 day',"
        "version=version+1 WHERE id=:id",
        "UPDATE crm_export_jobs SET version=version-1 WHERE id=:id",
        "UPDATE crm_export_jobs SET status='running',version=version+1 WHERE id=:id",
        "UPDATE crm_export_jobs SET attempt_count=1,version=version+1 WHERE id=:id",
        "UPDATE crm_export_jobs SET status='completed',csv_content='forged',"
        "completed_at=now(),next_attempt_at=NULL,version=version+1 WHERE id=:id",
    ]
    for statement in statements:
        with Session(engine) as db:
            with pytest.raises(DBAPIError):
                db.execute(text(statement), {"id": identity, "peer": users[1]})
                db.commit()
            db.rollback()
    assert complete(exports_db, claim(exports_db, identity))
    for statement in (
        "UPDATE crm_export_jobs SET csv_content='overwritten',version=version+1 WHERE id=:id",
        "UPDATE crm_export_jobs SET status='queued',csv_content=NULL,completed_at=NULL,"
        "next_attempt_at=now(),version=version+1 WHERE id=:id",
        "DELETE FROM crm_export_jobs WHERE id=:id",
    ):
        with Session(engine) as db:
            with pytest.raises(DBAPIError):
                db.execute(text(statement), {"id": identity})
                db.commit()
            db.rollback()


def test_history_is_owner_scoped_paginated_newest_and_rechecks_current_permission(exports_db):
    engine, org, other, users = exports_db
    older = queued(exports_db, created_days_ago=1)
    newer = queued(exports_db)
    expired = queued(exports_db, expires_in=-1)
    with Session(engine) as db:
        actor, peer = db.get(User, users[0]), db.get(User, users[1])
        first = service.list_exports(db, org, actor, limit=1)
        assert [item.id for item in first.items] == [newer] and first.next_cursor == newer
        second = service.list_exports(db, org, actor, first.next_cursor, 1)
        assert [item.id for item in second.items] == [older] and second.next_cursor is None
        assert first.items[0].created_at
        assert service.list_exports(db, org, peer).items == []
        for cursor in (older, newer, expired):
            with pytest.raises(AuthError):
                service.list_exports(db, org, peer, cursor)
        with pytest.raises(AuthError):
            service.list_exports(db, other, actor)
        db.execute(delete(UserRole).where(UserRole.user_id == users[0]))
        db.commit()
        with pytest.raises(AuthError):
            service.list_exports(db, org, actor)
        with pytest.raises(AuthError):
            service.get_export(db, org, newer, actor)


def test_database_does_not_recover_active_lease_or_complete_an_expired_lease(exports_db):
    identity = queued(exports_db)
    policy = get_settings().model_copy(update={"crm_export_lease_seconds": 1})
    assert claim(exports_db, identity, policy)
    retry = (
        "UPDATE crm_export_jobs SET status='queued',lease_until=NULL,lease_token_digest=NULL,"
        "next_attempt_at=clock_timestamp()+interval '10 seconds',error_code='recovered_lease',"
        "version=version+1 WHERE id=:id"
    )
    with Session(exports_db[0]) as db:
        with pytest.raises(DBAPIError):
            db.execute(text(retry), {"id": identity})
            db.commit()
        db.rollback()

    time.sleep(1.05)
    with Session(exports_db[0]) as db:
        with pytest.raises(DBAPIError):
            db.execute(
                text(
                    "UPDATE crm_export_jobs SET status='completed',lease_until=NULL,"
                    "lease_token_digest=NULL,csv_content='forged',completed_at=clock_timestamp(),"
                    "version=version+1 WHERE id=:id"
                ),
                {"id": identity},
            )
            db.commit()
        db.rollback()


def test_late_attempt_cannot_settle_a_new_execution_lease(exports_db):
    identity = queued(exports_db)
    policy = get_settings().model_copy(update={"crm_export_lease_seconds": 1})
    old = claim(exports_db, identity, policy)
    assert old
    time.sleep(1.05)
    with Session(exports_db[0]) as db:
        assert execution.recover_exports(db, policy) == ([], 1)
    # Honor the actual bounded retry deadline; do not mutate guarded state or clock.
    time.sleep(10.05)
    current = claim(exports_db, identity)
    assert current and current.attempt == old.attempt + 1
    with Session(exports_db[0]) as db:
        assert not execution.complete_export(db, old, execution.ExportContent("stale", 1))
        assert not execution.fail_export(db, old, "generation_failed", retryable=True)
        row = db.get(ExportJob, identity)
        assert row and row.status == "running" and row.version == current.version
        assert row.lease_token_digest == execution._digest(current.token)
    assert complete(exports_db, current)


def test_migration_preserves_oversized_legacy_csv_without_allowing_new_exemptions(exports_db):
    engine, org, _, users = exports_db
    assert (
        engine.url.database == "edp_test"
    )  # This regression alone rolls back the local n9 revision.
    configuration = Config("alembic.ini")
    command.downgrade(configuration, "m8c4d0e6f123")
    identity = uuid4()
    # Old workers bounded rows, rather than UTF-8 bytes. Preserve this exact artifact.
    oversized = "அ" * (20971520 // 3 + 1)
    assert len(oversized.encode("utf-8")) > 20971520
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO crm_export_jobs(id,created_at,organization_id,requested_by_id,"
                    "status,row_count,csv_content,error_code,completed_at,expires_at) "
                    "VALUES(:id,:stamp,:org,:user,'completed',1,:csv,'',:stamp,:expires)"
                ),
                {
                    "id": identity,
                    "stamp": now(),
                    "org": org,
                    "user": users[0],
                    "csv": oversized,
                    "expires": now() + timedelta(hours=24),
                },
            )
    finally:
        command.upgrade(configuration, "head")
    with Session(engine) as db:
        legacy = db.get(ExportJob, identity)
        assert legacy and legacy.status == "completed" and legacy.legacy_output
        assert legacy.csv_content == oversized and legacy.row_count == 1
        assert legacy.disposed_at is None
        for mutation in ("legacy_output=false", "csv_content='replacement'"):
            with pytest.raises(DBAPIError):
                db.execute(
                    text(
                        "UPDATE crm_export_jobs SET " + mutation + ",version=version+1 WHERE id=:id"
                    ),
                    {"id": identity},
                )
                db.commit()
            db.rollback()
        forged = ExportJob(
            organization_id=org,
            requested_by_id=users[0],
            expires_at=now() + timedelta(hours=24),
            legacy_output=True,
        )
        db.add(forged)
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()
    fresh = queued(exports_db)
    lease = claim(exports_db, fresh)
    assert lease
    with Session(engine) as db:
        with pytest.raises(DBAPIError):
            execution.complete_export(db, lease, execution.ExportContent(oversized, 1))
        db.rollback()
        current = db.get(ExportJob, fresh)
        assert current and not current.legacy_output and current.status == "running"
    assert complete(exports_db, lease)
