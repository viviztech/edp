import hashlib
from datetime import timedelta
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.crm.models import Lead
from app.modules.identity.models import AuditLog, now
from app.modules.meta.models import MetaFormMapping, MetaIntegration, MetaWebhookEvent
from app.modules.meta.service import cipher
from app.workers.celery_app import celery_app

settings = get_settings()
engine = create_engine(settings.database_url.get_secret_value(), pool_pre_ping=True)


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


def mark_failed(event_id: UUID, code: str, retrying: bool) -> None:
    with Session(engine) as db:
        event = db.get(MetaWebhookEvent, event_id)
        if not event or event.state == "completed":
            return
        event.state = "retrying" if retrying else "failed"
        event.error_code = code
        event.next_attempt_at = (
            now() + timedelta(minutes=min(2**event.attempt_count, 30)) if retrying else None
        )
        event.processed_at = None if retrying else now()
        db.add(
            AuditLog(
                actor_id=None,
                organization_id=event.organization_id,
                resource_id=event.id,
                action=("meta.event.retry_scheduled" if retrying else "meta.event.failed"),
                request_id=f"worker:{event.id}",
                resource_version=event.attempt_count,
                changed_fields="state,error_code,next_attempt_at",
            )
        )
        db.commit()


@celery_app.task(bind=True, name="edp.meta.process_event", max_retries=4)  # type: ignore[untyped-decorator]
def process_event(self: Any, event_id: str) -> dict[str, object]:
    identifier = UUID(event_id)
    with Session(engine) as db:
        event = db.scalar(
            select(MetaWebhookEvent).where(MetaWebhookEvent.id == identifier).with_for_update()
        )
        if not event or event.state not in {"queued", "retrying"}:
            return {"status": "ignored"}
        if event.attempt_count >= 5:
            event.state = "failed"
            event.error_code = "retry_exhausted"
            event.processed_at = now()
            db.commit()
            return {"status": "failed"}
        event.state = "processing"
        event.error_code = ""
        event.attempt_count += 1
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
            mark_failed(identifier, "configuration_unavailable", False)
            return {"status": "failed"}
        if not settings.meta_graph_api_version:
            mark_failed(identifier, "graph_version_missing", False)
            return {"status": "failed"}
        token = cipher().decrypt(integration.access_token_ciphertext.encode()).decode()
        meta_lead_id = event.meta_lead_id
        attempt_count = event.attempt_count
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
            "provider_unavailable" if retryable else "provider_rejected",
            retryable,
        )
        if not retryable:
            return {"status": "failed"}
        raise self.retry(
            exc=RuntimeError("provider_unavailable"),
            countdown=min(2**attempt_count * 30, 900),
        ) from exc
    except (httpx.RequestError, ValueError) as exc:
        mark_failed(identifier, "provider_unavailable", True)
        raise self.retry(
            exc=RuntimeError("provider_unavailable"),
            countdown=min(2**attempt_count * 30, 900),
        ) from exc

    values = mapped_fields(payload, field_mapping)
    name = values.get("name", "").strip()
    if not name:
        mark_failed(identifier, "mapped_name_missing", False)
        return {"status": "failed"}

    with Session(engine) as db:
        event = db.scalar(
            select(MetaWebhookEvent).where(MetaWebhookEvent.id == identifier).with_for_update()
        )
        if not event or event.state == "completed":
            return {"status": "ignored"}
        lead = Lead(
            organization_id=event.organization_id,
            name=name[:120],
            email=values.get("email", "")[:320],
            phone=values.get("phone", "")[:32],
            source="meta",
            campaign=campaign,
            dedupe_hash=hashlib.sha256(
                f"meta|{event.integration_id}|{event.meta_lead_id}".encode()
            ).hexdigest(),
            notes=(f"Meta page={event.page_id}; form={event.form_id}; lead={event.meta_lead_id}"),
        )
        db.add(lead)
        db.flush()
        event.lead_id = lead.id
        event.state = "completed"
        event.error_code = ""
        event.processed_at = now()
        event.next_attempt_at = None
        db.add(
            AuditLog(
                actor_id=None,
                organization_id=event.organization_id,
                resource_id=event.id,
                action="meta.event.completed",
                request_id=f"worker:{event.id}",
                resource_version=event.attempt_count,
                changed_fields="state,lead_id,processed_at",
            )
        )
        db.commit()
        return {"status": "completed", "lead_id": str(lead.id)}
