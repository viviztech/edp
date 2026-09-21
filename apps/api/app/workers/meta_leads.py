import hashlib
from datetime import timedelta
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import and_, create_engine, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.crm.models import Lead
from app.modules.identity.models import AuditLog, now
from app.modules.meta.models import MetaFormMapping, MetaIntegration, MetaWebhookEvent
from app.modules.meta.service import cipher, dispatch_event
from app.workers.celery_app import celery_app

settings = get_settings()
engine = create_engine(settings.database_url.get_secret_value(), pool_pre_ping=True)
MAX_ATTEMPTS = 5
LEASE_SECONDS = 90


def mapped_fields(payload: dict[str, Any], mapping: dict[str, str]) -> dict[str, str]:
    provider_values: dict[str, str] = {}
    rows = payload.get("field_data")
    if not isinstance(rows, list):
        return {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("name"), str):
            continue
        values = row.get("values")
        if isinstance(values, list) and values:
            provider_values[row["name"]] = str(values[0]).strip()
    return {
        target: provider_values[source]
        for source, target in mapping.items()
        if provider_values.get(source)
    }


def mark_failed(event_id: UUID, attempt: int, code: str, retrying: bool) -> None:
    with Session(engine) as db:
        event = db.scalar(
            select(MetaWebhookEvent).where(MetaWebhookEvent.id == event_id).with_for_update()
        )
        if not event or event.state != "processing" or event.attempt_count != attempt:
            return
        retrying = retrying and attempt < MAX_ATTEMPTS
        event.state = "retrying" if retrying else "failed"
        event.error_code = code if retrying or code != "provider_unavailable" else "retry_exhausted"
        event.next_attempt_at = (
            now() + timedelta(seconds=min(2**attempt * 30, 900)) if retrying else None
        )
        event.processed_at = None if retrying else now()
        event.version += 1
        db.add(
            AuditLog(
                actor_id=None,
                organization_id=event.organization_id,
                resource_id=event.id,
                action="meta.event.retry_scheduled" if retrying else "meta.event.failed",
                request_id=f"worker:{event.id}",
                resource_version=event.version,
                changed_fields="state,error_code,next_attempt_at",
            )
        )
        db.commit()


@celery_app.task(bind=True, name="edp.meta.process_event")  # type: ignore[untyped-decorator]
def process_event(self: Any, event_id: str) -> dict[str, object]:
    identifier = UUID(event_id)
    with Session(engine) as db:
        event = db.scalar(
            select(MetaWebhookEvent).where(MetaWebhookEvent.id == identifier).with_for_update()
        )
        if not event or event.state != "queued" or event.retention_expires_at <= now():
            return {"status": "ignored"}
        if event.attempt_count >= MAX_ATTEMPTS:
            event.state = "failed"
            event.error_code = "retry_exhausted"
            event.processed_at = now()
            event.version += 1
            db.commit()
            return {"status": "failed"}
        event.state = "processing"
        event.error_code = ""
        event.attempt_count += 1
        event.version += 1
        event.next_attempt_at = now() + timedelta(seconds=LEASE_SECONDS)
        attempt = event.attempt_count
        db.commit()

        integration = db.scalar(
            select(MetaIntegration).where(
                MetaIntegration.id == event.integration_id,
                MetaIntegration.organization_id == event.organization_id,
                MetaIntegration.status == "active",
            )
        )
        mapping = db.scalar(
            select(MetaFormMapping).where(
                MetaFormMapping.id == event.mapping_id,
                MetaFormMapping.organization_id == event.organization_id,
                MetaFormMapping.status == "active",
            )
        )
        if not integration or not mapping:
            mark_failed(identifier, attempt, "configuration_unavailable", False)
            return {"status": "failed"}
        if not settings.meta_graph_api_version:
            mark_failed(identifier, attempt, "graph_version_missing", False)
            return {"status": "failed"}
        token = cipher().decrypt(integration.access_token_ciphertext.encode()).decode()
        meta_lead_id = event.meta_lead_id
        field_mapping = dict(mapping.field_mapping)
        campaign = mapping.campaign

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                (
                    f"{settings.meta_graph_base_url.rstrip('/')}/"
                    f"{settings.meta_graph_api_version}/{meta_lead_id}"
                ),
                params={"fields": "created_time,field_data"},
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPStatusError as exc:
        retryable = exc.response.status_code == 429 or exc.response.status_code >= 500
        mark_failed(
            identifier,
            attempt,
            "provider_unavailable" if retryable else "provider_rejected",
            retryable,
        )
        return {"status": "retrying" if retryable and attempt < MAX_ATTEMPTS else "failed"}
    except (httpx.RequestError, ValueError):
        mark_failed(identifier, attempt, "provider_unavailable", True)
        return {"status": "retrying" if attempt < MAX_ATTEMPTS else "failed"}

    if not isinstance(payload, dict):
        mark_failed(identifier, attempt, "provider_invalid_payload", False)
        return {"status": "failed"}

    values = mapped_fields(payload, field_mapping)
    name = values.get("name", "").strip()
    if not name:
        mark_failed(identifier, attempt, "mapped_name_missing", False)
        return {"status": "failed"}

    with Session(engine) as db:
        event = db.scalar(
            select(MetaWebhookEvent).where(MetaWebhookEvent.id == identifier).with_for_update()
        )
        if (
            not event
            or event.state != "processing"
            or event.attempt_count != attempt
            or event.retention_expires_at <= now()
        ):
            return {"status": "ignored"}
        dedupe_hash = hashlib.sha256(
            f"meta|{event.integration_id}|{event.meta_lead_id}".encode()
        ).hexdigest()
        existing = db.scalar(
            select(Lead).where(
                Lead.organization_id == event.organization_id,
                Lead.dedupe_hash == dedupe_hash,
            )
        )
        if existing:
            lead = existing
        else:
            lead = Lead(
                organization_id=event.organization_id,
                name=name[:120],
                email=values.get("email", "")[:320],
                phone=values.get("phone", "")[:32],
                source="meta",
                campaign=campaign,
                dedupe_hash=dedupe_hash,
                notes=(
                    f"Meta page={event.page_id}; form={event.form_id}; lead={event.meta_lead_id}"
                ),
            )
            db.add(lead)
            db.flush()
        event.lead_id = lead.id
        event.state = "completed"
        event.error_code = ""
        event.processed_at = now()
        event.next_attempt_at = None
        event.version += 1
        db.add(
            AuditLog(
                actor_id=None,
                organization_id=event.organization_id,
                resource_id=event.id,
                action="meta.event.completed",
                request_id=f"worker:{event.id}",
                resource_version=event.version,
                changed_fields="state,lead_id,processed_at",
            )
        )
        if event.retention_expires_at <= now():
            db.rollback()
            return {"status": "ignored"}
        db.commit()
        return {"status": "completed", "lead_id": str(lead.id)}


@celery_app.task(name="edp.meta.recover_events")  # type: ignore[untyped-decorator]
def recover_events() -> dict[str, int]:
    current = now()
    with Session(engine) as db:
        rows = list(
            db.scalars(
                select(MetaWebhookEvent)
                .where(
                    MetaWebhookEvent.attempt_count < MAX_ATTEMPTS,
                    MetaWebhookEvent.retention_expires_at > current,
                    or_(
                        and_(
                            MetaWebhookEvent.state.in_(("queued", "retrying")),
                            MetaWebhookEvent.next_attempt_at <= current,
                        ),
                        and_(
                            MetaWebhookEvent.state == "processing",
                            MetaWebhookEvent.next_attempt_at <= current,
                        ),
                    ),
                )
                .order_by(MetaWebhookEvent.next_attempt_at, MetaWebhookEvent.id)
                .limit(100)
                .with_for_update(skip_locked=True)
            )
        )
        ids = [event.id for event in rows]
        for event in rows:
            event.state = "queued"
            event.next_attempt_at = current + timedelta(seconds=LEASE_SECONDS)
            event.version += 1
        db.commit()
        for event_id in ids:
            dispatch_event(db, event_id)
        return {"dispatched": len(ids)}


@celery_app.task(name="edp.meta.purge_expired_events")  # type: ignore[untyped-decorator]
def purge_expired_events() -> dict[str, int]:
    """Dispose of expired provider metadata without removing attributed CRM leads."""
    current = now()
    with Session(engine) as db:
        rows = list(
            db.scalars(
                select(MetaWebhookEvent)
                .where(MetaWebhookEvent.retention_expires_at <= current)
                .order_by(MetaWebhookEvent.retention_expires_at, MetaWebhookEvent.id)
                .limit(100)
                .with_for_update(skip_locked=True)
            )
        )
        for event in rows:
            db.add(
                AuditLog(
                    actor_id=None,
                    organization_id=event.organization_id,
                    resource_id=event.id,
                    action="meta.event.retention_purged",
                    request_id=f"retention:{event.id}",
                    resource_version=event.version,
                    reason="Configured Meta event retention expired",
                    changed_fields="event_deleted",
                )
            )
            db.delete(event)
        db.commit()
        return {"purged": len(rows)}
