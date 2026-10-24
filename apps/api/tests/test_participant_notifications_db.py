import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import pytest
from participant_notification_fixtures import create_enrollment
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_identity import auth, signed_in  # noqa: F401

from app.core.config import get_settings
from app.modules.identity.models import AuditLog, Organization, Person, Role, User, UserRole, now
from app.modules.identity.security import AuthError
from app.modules.notifications import participant_service as service
from app.modules.notifications.participant_models import ParticipantNotice
from app.modules.notifications.participant_schemas import (
    ParticipantMarkRead,
    ParticipantPreferenceEdit,
)
from app.modules.programs.models import DomainOutbox, Enrollment, Participant
from app.workers import participant_notifications as worker

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)


@pytest.fixture
def notices(request, monkeypatch):
    context = request.getfixturevalue("auth")
    client, engine, _, _ = context
    _, _, headers = signed_in(context)
    monkeypatch.setenv("PARTICIPANT_NOTIFICATION_RETENTION_DAYS", "7")
    get_settings.cache_clear()
    monkeypatch.setattr(worker, "engine", engine)
    with Session(engine) as db:
        owner = db.scalar(select(User).where(User.email == "learner@example.com"))
        assert owner
        org, other = Organization(name="Participant notices"), Organization(name="Other notices")
        person = Person(display_name="Synthetic enrollment director")
        db.add_all([org, other, person])
        db.flush()
        director = User(
            person_id=person.id,
            email="notice-director@example.test",
            password_hash="synthetic-unused",
            status="active",
        )
        db.add(director)
        db.flush()
        role = db.scalar(select(Role).where(Role.name == "Super Admin"))
        assert role
        db.add(UserRole(user_id=director.id, role_id=role.id, organization_id=org.id))
        db.commit()
        converted = create_enrollment(db, org.id, director, owner, "first")
        source = db.scalar(
            select(DomainOutbox).where(DomainOutbox.aggregate_id == converted.enrollment.id)
        )
        assert source and not source.dispatched
        return {
            "client": client,
            "engine": engine,
            "org": org.id,
            "other": other.id,
            "owner": owner.id,
            "director": director.id,
            "headers": headers,
            "enrollment": converted.enrollment.id,
            "participant": converted.participant.id,
            "event": source.id,
        }


def inbox(notices):
    with Session(notices["engine"]) as db:
        actor = db.get(User, notices["owner"])
        return service.mine(db, notices["org"], actor, None, 25)[0]


def add_enrollment(notices, suffix):
    with Session(notices["engine"]) as db:
        return create_enrollment(
            db,
            notices["org"],
            db.get(User, notices["director"]),
            db.get(User, notices["owner"]),
            suffix,
        )


def test_actual_enrollment_transaction_consumes_once_and_exposes_only_typed_owner_notice(notices):
    assert worker.consume_outbox.run()["dispatched"] == 1
    assert worker.consume_outbox.run()["dispatched"] == 0
    items = inbox(notices)
    assert len(items) == 1 and items[0].enrollment_id == notices["enrollment"]
    assert items[0].topic == "enrollment_created" and items[0].action_kind == "schedule"
    assert "source_event_id" not in items[0].model_dump()
    with Session(notices["engine"]) as db:
        source = db.get(DomainOutbox, notices["event"])
        assert source.state == "dispatched" and source.dispatched and source.attempt_count == 1
        assert db.scalar(select(func.count()).select_from(ParticipantNotice)) == 1
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.action == "participant_notification.created")
            )
            == 1
        )


def test_duplicate_concurrent_consumers_create_one_notice_and_settlement(notices):
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: worker.consume_outbox.run(), range(2)))
    assert sum(result["dispatched"] for result in results) == 1
    assert len(inbox(notices)) == 1


def test_sql_notice_and_dispatch_cannot_commit_separately(notices):
    with Session(notices["engine"]) as db:
        source = db.get(DomainOutbox, notices["event"])
        orphan = ParticipantNotice(
            organization_id=notices["org"],
            recipient_user_id=notices["owner"],
            enrollment_id=notices["enrollment"],
            source_event_id=source.id,
            created_at=source.created_at,
            expires_at=source.created_at + timedelta(days=7),
        )
        db.add(orphan)
        db.flush()  # A normal consumer must be allowed to insert before settling.
        with pytest.raises(DBAPIError):
            db.commit()  # The deferred constraint rejects an orphan at commit.
        db.rollback()
        assert db.scalar(select(func.count()).select_from(ParticipantNotice)) == 0
        assert db.get(DomainOutbox, notices["event"]).state == "pending"
        with pytest.raises(DBAPIError):
            db.execute(
                text(
                    "UPDATE domain_outbox SET state='dispatched',dispatched=true,"
                    "dispatched_at=statement_timestamp(),settled_at=statement_timestamp(),"
                    "next_attempt_at=NULL,attempt_count=1,version=version+1 WHERE id=:id"
                ),
                {"id": notices["event"]},
            )
            db.commit()
        db.rollback()
    assert worker.consume_outbox.run()["dispatched"] == 1
    assert len(inbox(notices)) == 1


def test_notice_creation_and_event_settlement_rollback_together_then_exhaust_bounded_retry(
    notices, monkeypatch
):
    original = service._audit

    def interrupt(db, org, resource, action, version, **kwargs):
        if action == "participant_notification.created":
            raise RuntimeError("synthetic failure after insertion; contents must never leak")
        return original(db, org, resource, action, version, **kwargs)

    monkeypatch.setattr(service, "_audit", interrupt)
    monkeypatch.setattr(service, "_retry_deadline", lambda _: now() + timedelta(milliseconds=200))
    policy = get_settings().model_copy(update={"participant_notification_max_attempts": 2})
    with Session(notices["engine"]) as db:
        assert service.consume_pending(db, policy)["retrying"] == 1
        assert db.scalar(select(func.count()).select_from(ParticipantNotice)) == 0
        assert db.get(DomainOutbox, notices["event"]).error_code == "dispatch_error"
    time.sleep(0.25)
    with Session(notices["engine"]) as db:
        assert service.consume_pending(db, policy)["failed"] == 1
        source = db.get(DomainOutbox, notices["event"])
        assert source.state == "failed" and source.attempt_count == 2 and not source.dispatched
        assert source.error_code == "retry_exhausted" and source.next_attempt_at is None
        assert service.consume_pending(db, policy)["dispatched"] == 0
        assert db.scalar(select(func.count()).select_from(ParticipantNotice)) == 0


def test_preference_suppresses_future_events_without_hiding_history_or_backfill(notices):
    assert worker.consume_outbox.run()["dispatched"] == 1
    with Session(notices["engine"]) as db:
        owner = db.get(User, notices["owner"])
        initial = service.preference(db, notices["org"], owner)
        assert initial.enabled and initial.version == 0
        disabled = service.update_preference(
            db,
            notices["org"],
            owner,
            ParticipantPreferenceEdit(enabled=False, expected_version=0),
            "opt-out",
        )
        assert not disabled.enabled and disabled.version == 1
        with pytest.raises(AuthError) as conflict:
            service.update_preference(
                db,
                notices["org"],
                owner,
                ParticipantPreferenceEdit(enabled=True, expected_version=0),
                "stale",
            )
        assert conflict.value.status == 409
        db.rollback()
    add_enrollment(notices, "suppressed")
    assert worker.consume_outbox.run()["suppressed"] == 1
    assert len(inbox(notices)) == 1
    with Session(notices["engine"]) as db:
        service.update_preference(
            db,
            notices["org"],
            db.get(User, notices["owner"]),
            ParticipantPreferenceEdit(enabled=True, expected_version=1),
            "opt-in",
        )
    assert worker.consume_outbox.run()["dispatched"] == 0
    assert len(inbox(notices)) == 1


def test_invalid_unsupported_and_expired_events_never_claim_dispatch(notices):
    with Session(notices["engine"]) as db:
        unknown = DomainOutbox(
            organization_id=notices["org"],
            event_key=f"unknown:{uuid4()}",
            event_type="unsupported.test",
            aggregate_type="other",
            aggregate_id=uuid4(),
            payload="{}",
        )
        invalid = DomainOutbox(
            organization_id=notices["org"],
            event_key=f"invalid:{uuid4()}",
            event_type="enrollment.created",
            aggregate_type="enrollment",
            aggregate_id=uuid4(),
            payload=json.dumps({"enrollment_id": str(notices["enrollment"])}),
        )
        expired_id = uuid4()
        expired = DomainOutbox(
            organization_id=notices["org"],
            event_key=f"enrollment.created:{expired_id}",
            event_type="enrollment.created",
            aggregate_type="enrollment",
            aggregate_id=expired_id,
            payload=json.dumps(
                {
                    "enrollment_id": str(expired_id),
                    "application_id": str(uuid4()),
                    "participant_id": str(uuid4()),
                }
            ),
            created_at=now() - timedelta(days=10),
        )
        db.add_all([unknown, invalid, expired])
        db.commit()
        identifiers = [unknown.id, invalid.id, expired.id]
    result = worker.consume_outbox.run()
    assert result["unsupported"] == result["invalid"] == result["expired"] == 1
    with Session(notices["engine"]) as db:
        for identity in identifiers:
            row = db.get(DomainOutbox, identity)
            assert not row.dispatched and row.dispatched_at is None and row.settled_at


def test_owner_pagination_read_versions_peer_staff_org_and_current_access(notices):
    add_enrollment(notices, "second")
    assert worker.consume_outbox.run()["dispatched"] == 2
    with Session(notices["engine"]) as db:
        owner = db.get(User, notices["owner"])
        items, cursor = service.mine(db, notices["org"], owner, None, 1)
        assert len(items) == 1 and cursor
        remaining, end = service.mine(db, notices["org"], owner, cursor, 1)
        assert len(remaining) == 1 and remaining[0].id != items[0].id and end is None
        read = service.mark_read(
            db,
            notices["org"],
            owner,
            items[0].id,
            ParticipantMarkRead(expected_version=1),
            "read-notice",
        )
        assert read.version == 2 and read.read_at
        with pytest.raises(AuthError) as stale:
            service.mark_read(
                db,
                notices["org"],
                owner,
                items[0].id,
                ParticipantMarkRead(expected_version=1),
                "read-stale",
            )
        assert stale.value.status == 409
        db.rollback()
        with pytest.raises(AuthError):
            service.mine(db, notices["other"], owner, None, 25)
        with pytest.raises(AuthError):
            service.mine(db, notices["org"], db.get(User, notices["director"]), None, 25)
        db.rollback()
        db.execute(delete(UserRole).where(UserRole.user_id == owner.id))
        db.commit()
        with pytest.raises(AuthError) as revoked:
            service.mine(db, notices["org"], owner, None, 25)
        assert revoked.value.status == 403


@pytest.mark.parametrize(
    "resource,status",
    [("participant", "suspended"), ("enrollment", "withdrawn"), ("owner", "suspended")],
)
def test_current_revocation_before_consume_suppresses(notices, resource, status):
    model = {"participant": Participant, "enrollment": Enrollment, "owner": User}[resource]
    with Session(notices["engine"]) as db:
        row = db.get(model, notices[resource])
        row.status = status
        db.commit()
    assert worker.consume_outbox.run()["suppressed"] == 1
    with Session(notices["engine"]) as db:
        assert db.scalar(select(func.count()).select_from(ParticipantNotice)) == 0


def test_sql_rejects_forged_scope_read_rewrites_unexpired_deletion_and_outbox_changes(notices):
    assert worker.consume_outbox.run()["dispatched"] == 1
    notice = inbox(notices)[0]
    with Session(notices["engine"]) as db:
        for statement, parameters in (
            (
                "UPDATE participant_notices SET recipient_user_id=:other WHERE id=:id",
                {"id": notice.id, "other": notices["director"]},
            ),
            ("UPDATE participant_notices SET version=version+1 WHERE id=:id", {"id": notice.id}),
            ("DELETE FROM participant_notices WHERE id=:id", {"id": notice.id}),
            (
                "UPDATE domain_outbox SET payload='{}',version=version+1 WHERE id=:id",
                {"id": notices["event"]},
            ),
            (
                "UPDATE domain_outbox SET state='pending',version=version+1 WHERE id=:id",
                {"id": notices["event"]},
            ),
        ):
            with pytest.raises(DBAPIError):
                db.execute(text(statement), parameters)
                db.commit()
            db.rollback()
        owner = db.get(User, notices["owner"])
        service.mark_read(
            db,
            notices["org"],
            owner,
            notice.id,
            ParticipantMarkRead(expected_version=1),
            "immutable-read",
        )
        with pytest.raises(DBAPIError):
            db.execute(
                text("UPDATE participant_notices SET read_at=NULL,version=3 WHERE id=:id"),
                {"id": notice.id},
            )
            db.commit()
        db.rollback()


def test_missing_retention_does_not_dispatch_or_dispose_and_health_is_scoped(notices, monkeypatch):
    monkeypatch.setenv("PARTICIPANT_NOTIFICATION_RETENTION_DAYS", "")
    get_settings.cache_clear()
    result = worker.consume_outbox.run()
    assert not result["retention_configured"] and result["dispatched"] == 0
    assert worker.purge_expired.run()["purged"] == 0
    with Session(notices["engine"]) as db:
        assert db.get(DomainOutbox, notices["event"]).state == "pending"
        health = service.health(db, notices["org"], db.get(User, notices["director"]))
        assert health.pending_due == 1 and not health.retention_configured
        with pytest.raises(AuthError):
            service.health(db, notices["org"], db.get(User, notices["owner"]))


def test_notice_expiry_disposal_preserves_source_and_prevents_backfill(notices):
    # Explicit synthetic three-second lifecycle; no SQL guard or clock is changed.
    policy = get_settings().model_copy(
        update={"participant_notification_retention_days": 3 / 86400}
    )
    with Session(notices["engine"]) as db:
        assert service.consume_pending(db, policy)["dispatched"] == 1
    time.sleep(3.05)
    assert inbox(notices) == []
    with Session(notices["engine"]) as db:
        assert service.purge_expired(db, policy) == 1
        assert db.get(DomainOutbox, notices["event"]).state == "dispatched"
        assert db.scalar(select(func.count()).select_from(ParticipantNotice)) == 0
        assert service.consume_pending(db, policy)["dispatched"] == 0


def test_authenticated_api_uses_participant_scope_and_versioned_mutations(notices):
    assert worker.consume_outbox.run()["dispatched"] == 1
    client, headers = notices["client"], notices["headers"]
    prefix = f"/api/v1/participant-notifications/organizations/{notices['org']}"
    response = client.get(prefix + "/mine?limit=1", headers=headers)
    assert response.status_code == 200
    notice = response.json()["items"][0]
    assert (
        client.post(
            prefix + f"/{notice['id']}/read", headers=headers, json={"expected_version": 1}
        ).json()["version"]
        == 2
    )
    assert (
        client.post(
            prefix + "/preference", headers=headers, json={"enabled": False, "expected_version": 0}
        ).json()["enabled"]
        is False
    )
    assert client.get(prefix + "/mine?limit=101", headers=headers).status_code == 422
    assert client.get(prefix + "/mine").status_code == 401


def test_enrolled_peer_cannot_read_owner_notice_or_use_owner_cursor(notices):
    with Session(notices["engine"]) as db:
        person = Person(display_name="Synthetic enrolled peer")
        db.add(person)
        db.flush()
        peer = User(
            person_id=person.id,
            email="notice-peer@example.test",
            password_hash="synthetic-unused",
            status="active",
        )
        db.add(peer)
        db.commit()
        create_enrollment(db, notices["org"], db.get(User, notices["director"]), peer, "peer")
        peer_id = peer.id
    assert worker.consume_outbox.run()["dispatched"] == 2
    owner_notice = inbox(notices)[0]
    with Session(notices["engine"]) as db:
        peer = db.get(User, peer_id)
        items, _ = service.mine(db, notices["org"], peer, None, 25)
        assert len(items) == 1 and items[0].enrollment_id != notices["enrollment"]
        with pytest.raises(AuthError) as denied:
            service.mark_read(
                db,
                notices["org"],
                peer,
                owner_notice.id,
                ParticipantMarkRead(expected_version=1),
                "peer-read",
            )
        assert denied.value.status == 404
        with pytest.raises(AuthError) as cursor:
            service.mine(db, notices["org"], peer, owner_notice.id, 25)
        assert cursor.value.code == "invalid_cursor"


def test_current_participant_status_hides_existing_notice_but_completed_history_remains(notices):
    assert worker.consume_outbox.run()["dispatched"] == 1
    notice = inbox(notices)[0]
    with Session(notices["engine"]) as db:
        participant = db.get(Participant, notices["participant"])
        participant.status = "suspended"
        db.commit()
    assert inbox(notices) == []
    with Session(notices["engine"]) as db:
        with pytest.raises(AuthError) as denied:
            service.mark_read(
                db,
                notices["org"],
                db.get(User, notices["owner"]),
                notice.id,
                ParticipantMarkRead(expected_version=1),
                "suspended-read",
            )
        assert denied.value.status == 404
        db.rollback()
        db.get(Participant, notices["participant"]).status = "completed"
        db.get(Enrollment, notices["enrollment"]).status = "completed"
        db.commit()
    assert len(inbox(notices)) == 1
