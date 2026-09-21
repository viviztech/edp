import hashlib
import hmac
from datetime import timedelta
from uuid import UUID

from cryptography.fernet import Fernet
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.identity.models import AuditLog, User, now
from app.modules.identity.security import AuthError, digest
from app.modules.identity.service import require_permission
from app.modules.meta.models import MetaFormMapping, MetaIntegration, MetaWebhookEvent
from app.modules.meta.schemas import (
    EventReplay,
    EventView,
    HealthView,
    IntegrationCreate,
    IntegrationEdit,
    IntegrationRotate,
    IntegrationView,
    MappingCreate,
    MappingEdit,
    MappingView,
)
from app.workers.celery_app import celery_app


def cipher() -> Fernet:
    key = get_settings().meta_secret_key
    if not key:
        raise AuthError("integration_not_configured", 503)
    return Fernet(key.get_secret_value().encode())


def integration_view(item: MetaIntegration) -> IntegrationView:
    return IntegrationView(
        id=item.id,
        name=item.name,
        page_id=item.page_id,
        status=item.status,
        version=item.version,
        created_at=item.created_at,
    )


def mapping_view(item: MetaFormMapping) -> MappingView:
    return MappingView(
        id=item.id,
        integration_id=item.integration_id,
        form_id=item.form_id,
        name=item.name,
        campaign=item.campaign,
        field_mapping=item.field_mapping,
        status=item.status,
        version=item.version,
    )


def event_view(item: MetaWebhookEvent) -> EventView:
    return EventView(
        id=item.id,
        integration_id=item.integration_id,
        mapping_id=item.mapping_id,
        meta_lead_id=item.meta_lead_id,
        page_id=item.page_id,
        form_id=item.form_id,
        state=item.state,
        attempt_count=item.attempt_count,
        version=item.version,
        error_code=item.error_code,
        lead_id=item.lead_id,
        created_at=item.created_at,
        processed_at=item.processed_at,
    )


def create_integration(
    db: Session, org: UUID, actor: User, data: IntegrationCreate, request_id: str
) -> IntegrationView:
    require_permission(db, actor, org, "meta.integration.manage")
    crypto = cipher()
    item = MetaIntegration(
        organization_id=org,
        name=data.name,
        page_id=data.page_id,
        access_token_ciphertext=crypto.encrypt(
            data.access_token.get_secret_value().encode()
        ).decode(),
        app_secret_ciphertext=crypto.encrypt(data.app_secret.get_secret_value().encode()).decode(),
        verify_token_hash=digest(data.verify_token.get_secret_value()),
    )
    db.add(item)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("integration_exists", 409) from exc
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=item.id,
            action="meta.integration.created",
            request_id=request_id,
            resource_version=1,
            changed_fields="name,page_id,status",
        )
    )
    db.commit()
    return integration_view(item)


def integrations(
    db: Session, org: UUID, actor: User, cursor: UUID | None, limit: int
) -> tuple[list[IntegrationView], UUID | None]:
    require_permission(db, actor, org, "meta.integration.view")
    query = select(MetaIntegration).where(MetaIntegration.organization_id == org)
    query = query.where(MetaIntegration.id > cursor) if cursor else query
    rows = list(db.scalars(query.order_by(MetaIntegration.id).limit(limit + 1)))
    return (
        [integration_view(item) for item in rows[:limit]],
        rows[limit - 1].id if len(rows) > limit else None,
    )


def create_mapping(
    db: Session,
    org: UUID,
    integration_id: UUID,
    actor: User,
    data: MappingCreate,
    request_id: str,
) -> MappingView:
    require_permission(db, actor, org, "meta.integration.manage")
    integration = db.scalar(
        select(MetaIntegration).where(
            MetaIntegration.id == integration_id,
            MetaIntegration.organization_id == org,
        )
    )
    if not integration:
        raise AuthError("not_found", 404)
    item = MetaFormMapping(
        organization_id=org,
        integration_id=integration.id,
        form_id=data.form_id,
        name=data.name,
        campaign=data.campaign,
        field_mapping=data.field_mapping,
    )
    db.add(item)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("mapping_exists", 409) from exc
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=item.id,
            action="meta.mapping.created",
            request_id=request_id,
            resource_version=1,
            changed_fields="form_id,name,campaign,field_mapping,status",
        )
    )
    db.commit()
    return mapping_view(item)


def mappings(db: Session, org: UUID, integration_id: UUID, actor: User) -> list[MappingView]:
    require_permission(db, actor, org, "meta.integration.view")
    if not db.scalar(
        select(MetaIntegration.id).where(
            MetaIntegration.id == integration_id,
            MetaIntegration.organization_id == org,
        )
    ):
        raise AuthError("not_found", 404)
    return [
        mapping_view(item)
        for item in db.scalars(
            select(MetaFormMapping)
            .where(
                MetaFormMapping.organization_id == org,
                MetaFormMapping.integration_id == integration_id,
            )
            .order_by(MetaFormMapping.form_id)
            .limit(100)
        )
    ]


def verify_challenge(
    db: Session, integration_id: UUID, mode: str, verify_token: str, challenge: str
) -> str:
    item = db.get(MetaIntegration, integration_id)
    if (
        not item
        or item.status != "active"
        or mode != "subscribe"
        or not hmac.compare_digest(item.verify_token_hash, digest(verify_token))
    ):
        raise AuthError("webhook_verification_failed", 403)
    return challenge


def valid_signature(item: MetaIntegration, body: bytes, supplied: str) -> bool:
    if not supplied.startswith("sha256=") or len(supplied) != 71:
        return False
    secret = cipher().decrypt(item.app_secret_ciphertext.encode())
    expected = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, supplied)


def ingest(
    db: Session,
    integration_id: UUID,
    body: bytes,
    payload: dict[str, object],
    signature: str,
    request_id: str,
) -> tuple[int, int]:
    integration = db.get(MetaIntegration, integration_id)
    if (
        not integration
        or integration.status != "active"
        or not valid_signature(integration, body, signature)
    ):
        raise AuthError("invalid_webhook_signature", 403)
    retention_days = get_settings().meta_event_retention_days
    if retention_days is None:
        raise AuthError("retention_policy_not_configured", 503)
    accepted = duplicates = 0
    queued: list[UUID] = []
    entries = payload.get("entry")
    if not isinstance(entries, list) or len(entries) > 100:
        raise AuthError("invalid_webhook_payload", 400)
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        changes = entry.get("changes")
        if not isinstance(changes, list) or len(changes) > 100:
            continue
        for change in changes:
            if not isinstance(change, dict) or change.get("field") != "leadgen":
                continue
            value = change.get("value")
            if not isinstance(value, dict):
                continue
            lead_id = str(value.get("leadgen_id", ""))
            form_id = str(value.get("form_id", ""))
            page_id = str(value.get("page_id") or entry.get("id") or "")
            if (
                not lead_id
                or len(lead_id) > 120
                or not form_id
                or len(form_id) > 80
                or page_id != integration.page_id
            ):
                continue
            mapping = db.scalar(
                select(MetaFormMapping).where(
                    MetaFormMapping.integration_id == integration.id,
                    MetaFormMapping.organization_id == integration.organization_id,
                    MetaFormMapping.form_id == form_id,
                    MetaFormMapping.status == "active",
                )
            )
            event = MetaWebhookEvent(
                organization_id=integration.organization_id,
                integration_id=integration.id,
                mapping_id=mapping.id if mapping else None,
                provider_event_id=lead_id,
                meta_lead_id=lead_id,
                page_id=page_id,
                form_id=form_id,
                state="queued" if mapping else "failed",
                error_code="" if mapping else "unmapped_form",
                metadata_json={
                    "entry_id": str(entry.get("id", ""))[:120],
                    "change_field": "leadgen",
                },
                retention_expires_at=now() + timedelta(days=retention_days),
                next_attempt_at=now() + timedelta(minutes=1) if mapping else None,
            )
            try:
                with db.begin_nested():
                    db.add(event)
                    db.flush()
            except IntegrityError:
                duplicates += 1
                continue
            accepted += 1
            db.add(
                AuditLog(
                    actor_id=None,
                    organization_id=integration.organization_id,
                    resource_id=event.id,
                    action="meta.webhook.accepted",
                    request_id=request_id,
                    resource_version=1,
                    changed_fields="state,page_id,form_id",
                )
            )
            if mapping:
                queued.append(event.id)
    db.commit()
    for event_id in queued:
        dispatch_event(db, event_id)
    return accepted, duplicates


def events(
    db: Session, org: UUID, actor: User, cursor: UUID | None, limit: int
) -> tuple[list[EventView], UUID | None]:
    require_permission(db, actor, org, "meta.integration.view")
    query = select(MetaWebhookEvent).where(
        MetaWebhookEvent.organization_id == org, MetaWebhookEvent.retention_expires_at > now()
    )
    query = query.where(MetaWebhookEvent.id > cursor) if cursor else query
    rows = list(db.scalars(query.order_by(MetaWebhookEvent.id).limit(limit + 1)))
    return (
        [event_view(item) for item in rows[:limit]],
        rows[limit - 1].id if len(rows) > limit else None,
    )


def update_integration(
    db: Session,
    org: UUID,
    integration_id: UUID,
    actor: User,
    data: IntegrationEdit,
    request_id: str,
) -> IntegrationView:
    require_permission(db, actor, org, "meta.integration.manage")
    item = db.scalar(
        select(MetaIntegration)
        .where(MetaIntegration.id == integration_id, MetaIntegration.organization_id == org)
        .with_for_update()
    )
    if not item:
        raise AuthError("not_found", 404)
    if item.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    item.name, item.status = data.name, data.status
    item.version += 1
    item.updated_at = now()
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=item.id,
            action="meta.integration.updated",
            request_id=request_id,
            resource_version=item.version,
            changed_fields="name,status",
        )
    )
    db.commit()
    return integration_view(item)


def rotate_integration(
    db: Session,
    org: UUID,
    integration_id: UUID,
    actor: User,
    data: IntegrationRotate,
    request_id: str,
) -> IntegrationView:
    require_permission(db, actor, org, "meta.integration.manage")
    if not any((data.access_token, data.app_secret, data.verify_token)):
        raise AuthError("invalid_request", 400)
    item = db.scalar(
        select(MetaIntegration)
        .where(MetaIntegration.id == integration_id, MetaIntegration.organization_id == org)
        .with_for_update()
    )
    if not item:
        raise AuthError("not_found", 404)
    if item.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    crypto = cipher()
    changed: list[str] = []
    if data.access_token:
        item.access_token_ciphertext = crypto.encrypt(
            data.access_token.get_secret_value().encode()
        ).decode()
        changed.append("access_token")
    if data.app_secret:
        item.app_secret_ciphertext = crypto.encrypt(
            data.app_secret.get_secret_value().encode()
        ).decode()
        changed.append("app_secret")
    if data.verify_token:
        item.verify_token_hash = digest(data.verify_token.get_secret_value())
        changed.append("verify_token")
    item.version += 1
    item.updated_at = now()
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=item.id,
            action="meta.integration.credentials_rotated",
            request_id=request_id,
            resource_version=item.version,
            changed_fields=",".join(changed),
        )
    )
    db.commit()
    return integration_view(item)


def update_mapping(
    db: Session,
    org: UUID,
    integration_id: UUID,
    mapping_id: UUID,
    actor: User,
    data: MappingEdit,
    request_id: str,
) -> MappingView:
    require_permission(db, actor, org, "meta.integration.manage")
    item = db.scalar(
        select(MetaFormMapping)
        .where(
            MetaFormMapping.id == mapping_id,
            MetaFormMapping.integration_id == integration_id,
            MetaFormMapping.organization_id == org,
        )
        .with_for_update()
    )
    if not item:
        raise AuthError("not_found", 404)
    if item.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    item.name = data.name
    item.form_id = data.form_id
    item.campaign = data.campaign
    item.field_mapping = dict(data.field_mapping)
    item.status = data.status
    item.version += 1
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("mapping_exists", 409) from exc
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=item.id,
            action="meta.mapping.updated",
            request_id=request_id,
            resource_version=item.version,
            changed_fields="form_id,name,campaign,field_mapping,status",
        )
    )
    db.commit()
    return mapping_view(item)


def replay_event(
    db: Session,
    org: UUID,
    event_id: UUID,
    actor: User,
    data: EventReplay,
    request_id: str,
) -> EventView:
    require_permission(db, actor, org, "meta.integration.replay")
    event = db.scalar(
        select(MetaWebhookEvent)
        .where(MetaWebhookEvent.id == event_id, MetaWebhookEvent.organization_id == org)
        .with_for_update()
    )
    if not event:
        raise AuthError("not_found", 404)
    if event.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if event.retention_expires_at <= now():
        raise AuthError("retention_expired", 409)
    if event.state != "failed" or event.lead_id is not None:
        raise AuthError("invalid_transition", 409)
    integration = db.scalar(
        select(MetaIntegration).where(
            MetaIntegration.id == event.integration_id,
            MetaIntegration.organization_id == org,
            MetaIntegration.status == "active",
        )
    )
    mapping = db.scalar(
        select(MetaFormMapping).where(
            MetaFormMapping.organization_id == org,
            MetaFormMapping.integration_id == event.integration_id,
            MetaFormMapping.form_id == event.form_id,
            MetaFormMapping.status == "active",
        )
    )
    if not integration or not mapping:
        raise AuthError("configuration_unavailable", 409)
    event.mapping_id = mapping.id
    event.state = "queued"
    event.attempt_count = 0
    event.error_code = ""
    event.next_attempt_at = now()
    event.processed_at = None
    event.version += 1
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=event.id,
            action="meta.event.replayed",
            request_id=request_id,
            resource_version=event.version,
            reason=data.reason,
            changed_fields="state,mapping_id,attempt_count",
        )
    )
    db.commit()
    dispatch_event(db, event.id)
    return event_view(event)


def dispatch_event(db: Session, event_id: UUID) -> None:
    try:
        celery_app.send_task("edp.meta.process_event", args=[str(event_id)])
    except Exception:
        event = db.get(MetaWebhookEvent, event_id)
        if event and event.state == "queued":
            event.state = "retrying"
            event.error_code = "queue_unavailable"
            event.next_attempt_at = now() + timedelta(minutes=5)
            event.version += 1
            db.commit()


def health(db: Session, org: UUID, actor: User) -> HealthView:
    require_permission(db, actor, org, "meta.integration.view")
    current = now()
    counts: dict[str, int] = {
        state: count
        for state, count in db.execute(
            select(MetaWebhookEvent.state, func.count())
            .where(
                MetaWebhookEvent.organization_id == org,
                MetaWebhookEvent.retention_expires_at > current,
            )
            .group_by(MetaWebhookEvent.state)
        ).all()
    }
    expired_count = (
        db.scalar(
            select(func.count())
            .select_from(MetaWebhookEvent)
            .where(
                MetaWebhookEvent.organization_id == org,
                MetaWebhookEvent.retention_expires_at <= current,
            )
        )
        or 0
    )
    integrations_count = (
        db.scalar(
            select(func.count())
            .select_from(MetaIntegration)
            .where(MetaIntegration.organization_id == org)
        )
        or 0
    )
    active_count = (
        db.scalar(
            select(func.count())
            .select_from(MetaIntegration)
            .where(
                MetaIntegration.organization_id == org,
                MetaIntegration.status == "active",
            )
        )
        or 0
    )
    return HealthView(
        integrations=integrations_count,
        active_integrations=active_count,
        queued=counts.get("queued", 0),
        processing=counts.get("processing", 0),
        retrying=counts.get("retrying", 0),
        failed=counts.get("failed", 0),
        completed=counts.get("completed", 0),
        expired=expired_count,
    )
