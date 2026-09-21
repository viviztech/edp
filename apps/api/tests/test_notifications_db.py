import os
from datetime import timedelta
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_identity import auth  # noqa: F401

from app.modules.crm import service as crm_service
from app.modules.crm.models import Lead
from app.modules.crm.schemas import LeadCreate, LeadEdit
from app.modules.identity.models import AuditLog, Organization, Person, Role, User, UserRole, now
from app.modules.identity.security import AuthError
from app.modules.notifications import service
from app.modules.notifications.models import NotificationIntent
from app.modules.notifications.schemas import MarkRead, PreferenceEdit
from app.workers import notifications as worker

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)


@pytest.fixture
def notification_db(request, monkeypatch):
    _, engine, _, _ = request.getfixturevalue("auth")
    monkeypatch.setattr(worker, "engine", engine)
    with Session(engine) as db:
        org = Organization(name="Notice test organization")
        other = Organization(name="Other organization")
        people = [
            Person(display_name="Assigning staff"),
            Person(display_name="Recipient"),
            Person(display_name="Other staff"),
        ]
        db.add_all([org, other, *people])
        db.flush()
        users = [
            User(
                person_id=person.id,
                email=f"staff-{index}@example.test",
                password_hash="test",
                status="active",
            )
            for index, person in enumerate(people)
        ]
        db.add_all(users)
        db.flush()
        role = db.scalar(select(Role).where(Role.name == "CRM Executive"))
        assert role is not None
        for user in users:
            db.add(UserRole(user_id=user.id, role_id=role.id, organization_id=org.id))
        db.commit()
        yield engine, org.id, other.id, users[0].id, users[1].id, users[2].id


def assign(db: Session, org: UUID, actor: User, recipient: UUID) -> Lead:
    created = crm_service.create(
        db, org, actor, LeadCreate(name="Ada", email="ada@example.test"), "test-request"
    )
    updated = crm_service.mutate(
        db,
        org,
        created.id,
        actor,
        LeadEdit(status="new", assigned_user_id=recipient, notes="", expected_version=1),
        "test-request",
    )
    assert updated.assigned_user_id == recipient
    lead = db.get(Lead, created.id)
    assert lead is not None
    return lead


def test_assignment_delivers_once_to_scoped_recipient(notification_db) -> None:
    engine, org, other, actor_id, recipient_id, other_user_id = notification_db
    with Session(engine) as db:
        actor = db.get(User, actor_id)
        recipient = db.get(User, recipient_id)
        other_user = db.get(User, other_user_id)
        assert actor and recipient and other_user
        lead = assign(db, org, actor, recipient_id)
        intent = db.scalar(select(NotificationIntent))
        assert intent is not None and intent.state == "pending"
        assert db.scalar(select(func.count()).select_from(NotificationIntent)) == 1
        with pytest.raises(AuthError) as stale:
            crm_service.mutate(
                db,
                org,
                lead.id,
                actor,
                LeadEdit(
                    status="new",
                    assigned_user_id=recipient_id,
                    notes="",
                    expected_version=1,
                ),
                "test-request",
            )
        assert stale.value.status == 409
        assert db.scalar(select(func.count()).select_from(NotificationIntent)) == 1
    assert worker.deliver_in_app.run() == {"delivered": 1, "suppressed": 0}
    assert worker.deliver_in_app.run() == {"delivered": 0, "suppressed": 0}
    with Session(engine) as db:
        recipient = db.get(User, recipient_id)
        other_user = db.get(User, other_user_id)
        assert recipient and other_user
        items, cursor = service.mine(db, org, recipient, None, 25)
        assert cursor is None and len(items) == 1
        assert items[0].resource_id == lead.id and items[0].read_at is None
        assert service.mine(db, org, other_user, None, 25)[0] == []
        with pytest.raises(AuthError) as wrong_org:
            service.mine(db, other, recipient, None, 25)
        assert wrong_org.value.status == 403
        with pytest.raises(AuthError) as wrong_reader:
            service.mark_read(
                db,
                org,
                other_user,
                items[0].id,
                MarkRead(expected_version=items[0].version),
                "test-request",
            )
        assert wrong_reader.value.status == 404
        read = service.mark_read(
            db,
            org,
            recipient,
            items[0].id,
            MarkRead(expected_version=items[0].version),
            "test-request",
        )
        assert read.read_at is not None and read.version == items[0].version + 1
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.action == "notification.read", AuditLog.resource_id == read.id)
            )
            == 1
        )


def test_opt_out_suppresses_pending_intent_and_requires_version(notification_db) -> None:
    engine, org, _, actor_id, recipient_id, _ = notification_db
    with Session(engine) as db:
        actor = db.get(User, actor_id)
        recipient = db.get(User, recipient_id)
        assert actor and recipient
        lead = assign(db, org, actor, recipient_id)
        lead_id = lead.id
        assert service.preference(db, org, recipient).enabled
        setting = service.update_preference(
            db, org, recipient, PreferenceEdit(enabled=False, expected_version=0), "test-request"
        )
        assert setting.version == 1 and not setting.enabled
        with pytest.raises(AuthError) as stale:
            service.update_preference(
                db, org, recipient, PreferenceEdit(enabled=True, expected_version=0), "test-request"
            )
        assert stale.value.status == 409
    assert worker.deliver_in_app.run() == {"delivered": 0, "suppressed": 1}
    with Session(engine) as db:
        recipient = db.get(User, recipient_id)
        assert recipient is not None
        assert service.mine(db, org, recipient, None, 25)[0] == []
        intent = db.scalar(select(NotificationIntent))
        assert intent is not None and intent.state == "suppressed" and intent.resource_id == lead_id
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(
                    AuditLog.action == "notification.suppressed", AuditLog.resource_id == intent.id
                )
            )
            == 1
        )


def test_revoked_recipient_is_suppressed(notification_db) -> None:
    engine, org, _, actor_id, recipient_id, _ = notification_db
    with Session(engine) as db:
        actor = db.get(User, actor_id)
        recipient = db.get(User, recipient_id)
        assert actor and recipient
        assign(db, org, actor, recipient_id)
        recipient.status = "suspended"
        db.commit()
    assert worker.deliver_in_app.run() == {"delivered": 0, "suppressed": 1}


def test_reassignment_suppresses_stale_recipient(notification_db) -> None:
    engine, org, _, actor_id, first_id, second_id = notification_db
    with Session(engine) as db:
        actor = db.get(User, actor_id)
        assert actor is not None
        lead = assign(db, org, actor, first_id)
        crm_service.mutate(
            db,
            org,
            lead.id,
            actor,
            LeadEdit(
                status="new",
                assigned_user_id=second_id,
                notes="",
                expected_version=lead.version,
            ),
            "test-request",
        )
        assert db.scalar(select(func.count()).select_from(NotificationIntent)) == 2
    assert worker.deliver_in_app.run() == {"delivered": 1, "suppressed": 1}
    with Session(engine) as db:
        first = db.get(User, first_id)
        second = db.get(User, second_id)
        assert first and second
        assert service.mine(db, org, first, None, 25)[0] == []
        assert len(service.mine(db, org, second, None, 25)[0]) == 1


def test_retention_hides_then_purges_expired_notice(notification_db, monkeypatch) -> None:
    engine, org, _, actor_id, recipient_id, _ = notification_db
    monkeypatch.setattr(service.get_settings(), "notification_retention_days", 1)
    with Session(engine) as db:
        actor = db.get(User, actor_id)
        recipient = db.get(User, recipient_id)
        assert actor and recipient
        lead = assign(db, org, actor, recipient_id)
        lead_id = lead.id
        old = db.scalar(select(NotificationIntent))
        assert old is not None
        old_id = old.id
        old.created_at = now() - timedelta(days=2)
        db.commit()
        assert service.mine(db, org, recipient, None, 25)[0] == []
    assert worker.deliver_in_app.run() == {"delivered": 0, "suppressed": 0}
    assert worker.purge_expired.run() == {"purged": 1}
    assert worker.purge_expired.run() == {"purged": 0}
    with Session(engine) as db:
        assert db.get(Lead, lead_id) is not None
        assert db.get(NotificationIntent, old_id) is None
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(
                    AuditLog.action == "notification.retention_purged",
                    AuditLog.resource_id == old_id,
                )
            )
            == 1
        )


def test_expired_delivered_notice_cannot_be_read(notification_db, monkeypatch) -> None:
    engine, org, _, actor_id, recipient_id, _ = notification_db
    monkeypatch.setattr(service.get_settings(), "notification_retention_days", 1)
    with Session(engine) as db:
        actor = db.get(User, actor_id)
        recipient = db.get(User, recipient_id)
        assert actor and recipient
        assign(db, org, actor, recipient_id)
    assert worker.deliver_in_app.run() == {"delivered": 1, "suppressed": 0}
    with Session(engine) as db:
        recipient = db.get(User, recipient_id)
        row = db.scalar(select(NotificationIntent))
        assert recipient and row
        row.created_at = now() - timedelta(days=2)
        db.commit()
        assert service.mine(db, org, recipient, None, 25)[0] == []
        with pytest.raises(AuthError) as expired:
            service.mark_read(
                db, org, recipient, row.id, MarkRead(expected_version=row.version), "test-request"
            )
        assert expired.value.status == 404
    assert worker.purge_expired.run() == {"purged": 1}


def test_retention_purge_is_bounded(notification_db, monkeypatch) -> None:
    engine, org, _, _, recipient_id, _ = notification_db
    monkeypatch.setattr(service.get_settings(), "notification_retention_days", 1)
    with Session(engine) as db:
        old = now() - timedelta(days=2)
        lead = Lead(
            organization_id=org,
            name="Batch lead",
            dedupe_hash="batch-retention-test",
        )
        db.add(lead)
        db.flush()
        lead_id = lead.id
        db.add_all(
            NotificationIntent(
                organization_id=org,
                recipient_user_id=recipient_id,
                topic="lead_assignment",
                resource_id=lead.id,
                event_key=f"batch:{index}",
                state="suppressed",
                created_at=old,
            )
            for index in range(101)
        )
        db.commit()
    assert worker.purge_expired.run() == {"purged": 100}
    assert worker.purge_expired.run() == {"purged": 1}
    assert worker.purge_expired.run() == {"purged": 0}
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(NotificationIntent)) == 0
        assert db.get(Lead, lead_id) is not None


def test_production_assignment_requires_retention_policy(notification_db, monkeypatch) -> None:
    engine, org, _, actor_id, recipient_id, _ = notification_db
    settings = service.get_settings()
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "notification_retention_days", None)
    with Session(engine) as db:
        actor = db.get(User, actor_id)
        assert actor is not None
        created = crm_service.create(
            db,
            org,
            actor,
            LeadCreate(name="No policy", email="policy@example.test"),
            "test-request",
        )
        with pytest.raises(AuthError) as missing:
            crm_service.mutate(
                db,
                org,
                created.id,
                actor,
                LeadEdit(status="new", assigned_user_id=recipient_id, notes="", expected_version=1),
                "test-request",
            )
        assert missing.value.status == 503
        db.rollback()
        lead = db.get(Lead, created.id)
        assert lead is not None and lead.assigned_user_id is None and lead.version == 1
        assert db.scalar(select(func.count()).select_from(NotificationIntent)) == 0
