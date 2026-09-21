import hashlib
import hmac
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_identity import auth  # noqa: F401

from app.core.config import get_settings
from app.modules.crm.models import Lead
from app.modules.identity.models import AuditLog, Organization, Person, Role, User, UserRole, now
from app.modules.identity.security import AuthError
from app.modules.meta import service
from app.modules.meta.models import MetaFormMapping, MetaIntegration, MetaWebhookEvent
from app.modules.meta.schemas import EventReplay, IntegrationEdit, IntegrationRotate
from app.workers import meta_leads

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)


@pytest.fixture
def meta_db(request, monkeypatch):
    _, engine, _, _ = request.getfixturevalue("auth")
    key = Fernet.generate_key()
    monkeypatch.setenv("META_SECRET_KEY", key.decode())
    monkeypatch.setenv("META_EVENT_RETENTION_DAYS", "30")
    monkeypatch.setenv("META_GRAPH_API_VERSION", "v22.0")
    get_settings.cache_clear()
    monkeypatch.setattr(service.celery_app, "send_task", lambda *args, **kwargs: None)
    monkeypatch.setattr(meta_leads, "engine", engine)
    monkeypatch.setattr(meta_leads, "settings", get_settings())
    with Session(engine) as db:
        org = Organization(name="Meta test organization")
        db.add(org)
        db.flush()
        integration = MetaIntegration(
            organization_id=org.id,
            name="Test page",
            page_id="page-1",
            access_token_ciphertext=Fernet(key).encrypt(b"page-access-token").decode(),
            app_secret_ciphertext=Fernet(key).encrypt(b"test-app-secret").decode(),
            verify_token_hash="a" * 64,
        )
        db.add(integration)
        db.flush()
        mapping = MetaFormMapping(
            organization_id=org.id,
            integration_id=integration.id,
            form_id="form-1",
            name="Test form",
            campaign="Autumn",
            field_mapping={"full_name": "name", "email": "email"},
        )
        db.add(mapping)
        db.commit()
        result = (engine, org.id, integration.id, mapping.id)
    yield result
    get_settings.cache_clear()


def signed_payload() -> tuple[bytes, str]:
    body = json.dumps(
        {
            "entry": [
                {
                    "id": "page-1",
                    "changes": [
                        {
                            "field": "leadgen",
                            "value": {
                                "leadgen_id": "provider-lead-1",
                                "form_id": "form-1",
                                "page_id": "page-1",
                            },
                        }
                    ],
                }
            ],
        }
    ).encode()
    signature = "sha256=" + hmac.new(b"test-app-secret", body, hashlib.sha256).hexdigest()
    return body, signature


def test_concurrent_delivery_creates_one_inbox_and_one_lead(meta_db, monkeypatch) -> None:
    engine, org_id, integration_id, _ = meta_db
    body, signature = signed_payload()
    payload = json.loads(body)

    def deliver() -> tuple[int, int]:
        with Session(engine) as db:
            return service.ingest(db, integration_id, body, payload, signature, "test-request")

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: deliver(), range(2)))
    assert sum(accepted for accepted, _ in results) == 1
    assert sum(duplicates for _, duplicates in results) == 1

    with Session(engine) as db:
        event = db.scalar(select(MetaWebhookEvent))
        assert event is not None
        event_id = event.id
        assert db.scalar(select(func.count()).select_from(MetaWebhookEvent)) == 1

    class ProviderClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def get(self, *args, **kwargs):
            response = MagicMock()
            response.json.return_value = {
                "field_data": [
                    {"name": "full_name", "values": ["Ada Lovelace"]},
                    {"name": "email", "values": ["ada@example.test"]},
                ]
            }
            return response

    monkeypatch.setattr(meta_leads.httpx, "Client", lambda **kwargs: ProviderClient())
    assert meta_leads.process_event.run(str(event_id))["status"] == "completed"
    assert meta_leads.process_event.run(str(event_id))["status"] == "ignored"
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Lead)) == 1
        event = db.get(MetaWebhookEvent, event_id)
        assert event is not None and event.lead_id is not None
        lead = db.get(Lead, event.lead_id)
        assert lead is not None and lead.organization_id == org_id
        assert lead.source == "meta" and lead.campaign == "Autumn"


def test_recovery_requeues_expired_processing_lease(meta_db, monkeypatch) -> None:
    engine, _, integration_id, mapping_id = meta_db
    body, signature = signed_payload()
    with Session(engine) as db:
        service.ingest(db, integration_id, body, json.loads(body), signature, "test-request")
        event = db.scalar(select(MetaWebhookEvent))
        assert event is not None
        event.mapping_id = mapping_id
        event.state = "processing"
        event.attempt_count = 1
        event.next_attempt_at = now() - timedelta(seconds=1)
        db.commit()
        event_id = event.id

    sent: list[UUID] = []
    monkeypatch.setattr(meta_leads, "dispatch_event", lambda db, event_id: sent.append(event_id))
    result = meta_leads.recover_events()
    assert result == {"dispatched": 1}
    assert sent == [event_id]
    with Session(engine) as db:
        event = db.get(MetaWebhookEvent, event_id)
        assert event is not None and event.state == "queued"
        assert event.attempt_count == 1
        assert event.version > 1


def test_versioned_configuration_and_scoped_replay(meta_db) -> None:
    engine, org_id, integration_id, _ = meta_db
    with Session(engine) as db:
        other = Organization(name="Other organization")
        person = Person(display_name="Marketing user")
        db.add_all([other, person])
        db.flush()
        actor = User(
            person_id=person.id,
            email="marketer@example.test",
            password_hash="test",
            status="active",
        )
        role = db.scalar(select(Role).where(Role.name == "Marketing Executive"))
        assert role is not None
        db.add(actor)
        db.flush()
        db.add(UserRole(user_id=actor.id, role_id=role.id, organization_id=org_id))
        db.commit()

        original = db.get(MetaIntegration, integration_id)
        assert original is not None
        changed = service.update_integration(
            db,
            org_id,
            integration_id,
            actor,
            IntegrationEdit(expected_version=original.version, name="New label", status="active"),
            "test-request",
        )
        assert changed.version == original.version
        with pytest.raises(AuthError) as conflict:
            service.update_integration(
                db,
                org_id,
                integration_id,
                actor,
                IntegrationEdit(expected_version=1, name="Stale", status="disabled"),
                "test-request",
            )
        assert conflict.value.status == 409
        with pytest.raises(AuthError) as forbidden:
            service.health(db, other.id, actor)
        assert forbidden.value.status == 403
        with pytest.raises(AuthError) as invalid_rotation:
            service.rotate_integration(
                db,
                org_id,
                integration_id,
                actor,
                IntegrationRotate(expected_version=changed.version),
                "test-request",
            )
        assert invalid_rotation.value.status == 400

        body, signature = signed_payload()
        service.ingest(db, integration_id, body, json.loads(body), signature, "test-request")
        event = db.scalar(select(MetaWebhookEvent))
        assert event is not None
        event.state = "failed"
        event.error_code = "provider_rejected"
        event.next_attempt_at = None
        db.commit()
        event_id, version = event.id, event.version
        with pytest.raises(AuthError) as forbidden_replay:
            service.replay_event(
                db,
                other.id,
                event_id,
                actor,
                EventReplay(expected_version=version, reason="Retry after correction"),
                "test-request",
            )
        assert forbidden_replay.value.status == 403
        replayed = service.replay_event(
            db,
            org_id,
            event_id,
            actor,
            EventReplay(expected_version=version, reason="Retry after correction"),
            "test-request",
        )
        assert replayed.state == "queued" and replayed.version == version + 1
        with pytest.raises(AuthError) as repeated:
            service.replay_event(
                db,
                org_id,
                event_id,
                actor,
                EventReplay(expected_version=version, reason="Repeat"),
                "test-request",
            )
        assert repeated.value.status == 409
        event = db.get(MetaWebhookEvent, event_id)
        assert event is not None
        event.retention_expires_at = now() - timedelta(seconds=1)
        event.state = "failed"
        db.commit()
        with pytest.raises(AuthError) as expired:
            service.replay_event(
                db,
                org_id,
                event_id,
                actor,
                EventReplay(expected_version=event.version, reason="Too late"),
                "test-request",
            )
        assert expired.value.code == "retention_expired"
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.action == "meta.event.replayed", AuditLog.resource_id == event_id)
            )
            == 1
        )


def test_retention_purge_preserves_lead_and_later_delivery_dedupes(meta_db, monkeypatch) -> None:
    engine, org_id, integration_id, mapping_id = meta_db
    body, signature = signed_payload()
    with Session(engine) as db:
        assert service.ingest(
            db, integration_id, body, json.loads(body), signature, "test-request"
        ) == (1, 0)
        expired = db.scalar(select(MetaWebhookEvent))
        assert expired is not None
        lead = Lead(
            organization_id=org_id,
            name="Ada Lovelace",
            source="meta",
            dedupe_hash=hashlib.sha256(
                f"meta|{integration_id}|provider-lead-1".encode()
            ).hexdigest(),
        )
        db.add(lead)
        db.flush()
        expired.lead_id = lead.id
        expired.state = "completed"
        expired.next_attempt_at = None
        expired.retention_expires_at = now() - timedelta(seconds=1)
        fresh = MetaWebhookEvent(
            organization_id=org_id,
            integration_id=integration_id,
            mapping_id=mapping_id,
            provider_event_id="fresh-lead",
            meta_lead_id="fresh-lead",
            page_id="page-1",
            form_id="form-1",
            state="failed",
            metadata_json={},
            retention_expires_at=now() + timedelta(days=1),
        )
        db.add(fresh)
        db.commit()
        expired_id, fresh_id, lead_id = expired.id, fresh.id, lead.id

    assert meta_leads.purge_expired_events.run() == {"purged": 1}
    assert meta_leads.purge_expired_events.run() == {"purged": 0}
    with Session(engine) as db:
        assert db.get(MetaWebhookEvent, expired_id) is None
        assert db.get(MetaWebhookEvent, fresh_id) is not None
        assert db.get(Lead, lead_id) is not None
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(
                    AuditLog.action == "meta.event.retention_purged",
                    AuditLog.resource_id == expired_id,
                )
            )
            == 1
        )
        assert service.ingest(
            db, integration_id, body, json.loads(body), signature, "test-request"
        ) == (1, 0)
        replacement = db.scalar(
            select(MetaWebhookEvent).where(MetaWebhookEvent.provider_event_id == "provider-lead-1")
        )
        assert replacement is not None
        replacement_id = replacement.id

    class ProviderClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def get(self, *args, **kwargs):
            response = MagicMock()
            response.json.return_value = {
                "field_data": [{"name": "full_name", "values": ["Ada Lovelace"]}]
            }
            return response

    monkeypatch.setattr(meta_leads.httpx, "Client", lambda **kwargs: ProviderClient())
    assert meta_leads.process_event.run(str(replacement_id))["status"] == "completed"
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Lead)) == 1
        replacement = db.get(MetaWebhookEvent, replacement_id)
        assert replacement is not None and replacement.lead_id == lead_id


def test_expired_queued_event_is_not_claimed_or_recovered(meta_db, monkeypatch) -> None:
    engine, org_id, integration_id, _ = meta_db
    body, signature = signed_payload()
    with Session(engine) as db:
        service.ingest(db, integration_id, body, json.loads(body), signature, "test-request")
        event = db.scalar(select(MetaWebhookEvent))
        assert event is not None
        event.retention_expires_at = now() - timedelta(seconds=1)
        event.next_attempt_at = now() - timedelta(seconds=1)
        db.commit()
        event_id = event.id
    monkeypatch.setattr(meta_leads.httpx, "Client", lambda **kwargs: pytest.fail("provider called"))
    assert meta_leads.process_event.run(str(event_id)) == {"status": "ignored"}
    assert meta_leads.recover_events.run() == {"dispatched": 0}
    monkeypatch.setattr(service, "require_permission", lambda *_: None)
    with Session(engine) as db:
        event = db.get(MetaWebhookEvent, event_id)
        assert event is not None and event.attempt_count == 0
        visible, _ = service.events(db, org_id, MagicMock(), None, 25)
        assert visible == []
        pulse = service.health(db, org_id, MagicMock())
        assert pulse.queued == 0 and pulse.expired == 1
    assert meta_leads.purge_expired_events.run() == {"purged": 1}
    with Session(engine) as db:
        assert service.health(db, org_id, MagicMock()).expired == 0


def test_event_expiring_during_provider_fetch_cannot_create_lead(meta_db, monkeypatch) -> None:
    engine, _, integration_id, _ = meta_db
    body, signature = signed_payload()
    with Session(engine) as db:
        service.ingest(db, integration_id, body, json.loads(body), signature, "test-request")
        event = db.scalar(select(MetaWebhookEvent))
        assert event is not None
        event_id = event.id

    class ProviderClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def get(self, *args, **kwargs):
            with Session(engine) as db:
                event = db.get(MetaWebhookEvent, event_id)
                assert event is not None
                event.retention_expires_at = now() - timedelta(seconds=1)
                db.commit()
            response = MagicMock()
            response.json.return_value = {
                "field_data": [{"name": "full_name", "values": ["Ada Lovelace"]}]
            }
            return response

    monkeypatch.setattr(meta_leads.httpx, "Client", lambda **kwargs: ProviderClient())
    assert meta_leads.process_event.run(str(event_id)) == {"status": "ignored"}
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Lead)) == 0
        event = db.get(MetaWebhookEvent, event_id)
        assert event is not None and event.state == "processing"
    assert meta_leads.purge_expired_events.run() == {"purged": 1}
