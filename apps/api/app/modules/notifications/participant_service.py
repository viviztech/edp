"""Atomic enrollment events and recipient-only participant inbox access."""

import json
from datetime import datetime, timedelta
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import Select, func, select, tuple_
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.modules.applications.models import Application
from app.modules.identity.models import AuditLog, RolePermission, User, UserRole, now
from app.modules.identity.security import AuthError
from app.modules.identity.service import require_permission
from app.modules.notifications.participant_models import (
    ParticipantNotice,
    ParticipantNoticePreference,
)
from app.modules.notifications.participant_schemas import (
    EnrollmentCreatedPayload,
    ParticipantMarkRead,
    ParticipantNoticeView,
    ParticipantOutboxHealth,
    ParticipantPreferenceEdit,
    ParticipantPreferenceView,
)
from app.modules.programs.models import DomainOutbox, Enrollment, Participant

TOPIC = "enrollment_created"
TEMPLATE_VERSION = "enrollment-created-v1"


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate field")
        value[key] = item
    return value


def enrollment_payload(event: DomainOutbox) -> EnrollmentCreatedPayload | None:
    try:
        value = json.loads(event.payload, object_pairs_hook=_unique_object)
        payload = EnrollmentCreatedPayload.model_validate(value)
    except (ValueError, TypeError, ValidationError):
        return None
    # The existing domain contract uses canonical UUID strings and no extra fields.
    if (
        event.aggregate_type != "enrollment"
        or event.aggregate_id != payload.enrollment_id
        or event.event_key != f"enrollment.created:{payload.enrollment_id}"
        or value != payload.model_dump(mode="json")
    ):
        return None
    return payload


def _active_actor(db: Session, actor: User, *, lock: bool = False) -> User:
    statement = select(User).where(User.id == actor.id).execution_options(populate_existing=True)
    current = db.scalar(statement.with_for_update() if lock else statement)
    if current is None or current.status != "active":
        raise AuthError("forbidden", 403)
    return current


def _require_actor(db: Session, org: UUID, actor: User, *, lock: bool = False) -> User:
    current = _active_actor(db, actor, lock=lock)
    require_permission(db, current, org, "participant.self")
    return current


def _policy_available(settings: Settings) -> None:
    if (
        settings.app_env in {"staging", "production"}
        and settings.participant_notification_retention_days is None
    ):
        raise AuthError("participant_notifications_unconfigured", 503)


def _eligible_participant(db: Session, org: UUID, actor: User) -> bool:
    return (
        db.scalar(
            select(Participant.id)
            .join(
                Enrollment,
                (Enrollment.participant_id == Participant.id)
                & (Enrollment.organization_id == Participant.organization_id),
            )
            .where(
                Participant.organization_id == org,
                Participant.person_id == actor.person_id,
                Participant.status.in_(("active", "completed")),
                Enrollment.status.in_(("active", "completed")),
            )
            .limit(1)
        )
        is not None
    )


def _require_participant_profile(db: Session, org: UUID, actor: User) -> None:
    # An administrative permission bundle does not create a recipient profile.
    # Suspended/withdrawn owners can request their own empty inbox; visibility
    # still repeats each notice's current participant/enrollment status below.
    profile = db.scalar(
        select(Participant.id).where(
            Participant.organization_id == org, Participant.person_id == actor.person_id
        )
    )
    if profile is None:
        raise AuthError("forbidden", 403)


def _audit(
    db: Session,
    org: UUID,
    resource: UUID,
    action: str,
    version: int,
    *,
    actor: UUID | None = None,
    request_id: str | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor,
            organization_id=org,
            resource_id=resource,
            action=action,
            resource_version=version,
            request_id=request_id or f"participant-notification:{resource}",
            changed_fields="state,version",
        )
    )


def preference(db: Session, org: UUID, actor: User) -> ParticipantPreferenceView:
    current = _require_actor(db, org, actor)
    if not _eligible_participant(db, org, current):
        raise AuthError("forbidden", 403)
    row = db.scalar(
        select(ParticipantNoticePreference).where(
            ParticipantNoticePreference.organization_id == org,
            ParticipantNoticePreference.user_id == current.id,
        )
    )
    return (
        ParticipantPreferenceView(enabled=row.enabled, version=row.version)
        if row
        else (ParticipantPreferenceView(enabled=True, version=0))
    )


def update_preference(
    db: Session, org: UUID, actor: User, data: ParticipantPreferenceEdit, request_id: str
) -> ParticipantPreferenceView:
    # The user lock also serializes first preference insertion with event consumption.
    current = _require_actor(db, org, actor, lock=True)
    if not _eligible_participant(db, org, current):
        raise AuthError("forbidden", 403)
    row = db.scalar(
        select(ParticipantNoticePreference)
        .where(
            ParticipantNoticePreference.organization_id == org,
            ParticipantNoticePreference.user_id == current.id,
        )
        .with_for_update()
    )
    if row is None:
        if data.expected_version != 0:
            raise AuthError("version_conflict", 409)
        row = ParticipantNoticePreference(
            organization_id=org,
            user_id=current.id,
            enabled=data.enabled,
        )
        db.add(row)
        db.flush()
    else:
        if data.expected_version != row.version:
            raise AuthError("version_conflict", 409)
        row.enabled = data.enabled
        row.version += 1
        row.updated_at = now()
    _audit(
        db,
        org,
        row.id,
        "participant_notification.preference_updated",
        row.version,
        actor=current.id,
        request_id=request_id,
    )
    db.commit()
    return ParticipantPreferenceView(enabled=row.enabled, version=row.version)


def view(row: ParticipantNotice) -> ParticipantNoticeView:
    return ParticipantNoticeView(
        id=row.id,
        enrollment_id=row.enrollment_id,
        created_at=row.created_at,
        expires_at=row.expires_at,
        read_at=row.read_at,
        version=row.version,
    )


def _visible(org: UUID, actor: User) -> Select[tuple[ParticipantNotice]]:
    return (
        select(ParticipantNotice)
        .join(
            Enrollment,
            (Enrollment.id == ParticipantNotice.enrollment_id)
            & (Enrollment.organization_id == ParticipantNotice.organization_id),
        )
        .join(
            Participant,
            (Participant.id == Enrollment.participant_id)
            & (Participant.organization_id == Enrollment.organization_id),
        )
        .join(
            Application,
            (Application.id == Enrollment.application_id)
            & (Application.organization_id == Enrollment.organization_id),
        )
        .where(
            ParticipantNotice.organization_id == org,
            ParticipantNotice.recipient_user_id == actor.id,
            ParticipantNotice.expires_at > now(),
            Participant.person_id == actor.person_id,
            Application.person_id == Participant.person_id,
            Application.state == "enrolled",
            Participant.status.in_(("active", "completed")),
            Enrollment.status.in_(("active", "completed")),
        )
        .execution_options(populate_existing=True)
    )


def mine(
    db: Session, org: UUID, actor: User, cursor: UUID | None, limit: int
) -> tuple[list[ParticipantNoticeView], UUID | None]:
    current = _require_actor(db, org, actor)
    _require_participant_profile(db, org, current)
    _policy_available(get_settings())
    if not 1 <= limit <= 100:
        raise AuthError("invalid_limit", 422)
    statement = _visible(org, current)
    if cursor is not None:
        anchor = db.scalar(statement.where(ParticipantNotice.id == cursor))
        if anchor is None:
            raise AuthError("invalid_cursor", 422)
        statement = statement.where(
            tuple_(ParticipantNotice.created_at, ParticipantNotice.id)
            < (anchor.created_at, anchor.id)
        )
    rows = list(
        db.scalars(
            statement.order_by(
                ParticipantNotice.created_at.desc(), ParticipantNotice.id.desc()
            ).limit(limit + 1)
        )
    )
    return [view(row) for row in rows[:limit]], rows[limit - 1].id if len(rows) > limit else None


def mark_read(
    db: Session, org: UUID, actor: User, notice_id: UUID, data: ParticipantMarkRead, request_id: str
) -> ParticipantNoticeView:
    current = _require_actor(db, org, actor)
    _policy_available(get_settings())
    row = db.scalar(
        _visible(org, current)
        .where(ParticipantNotice.id == notice_id)
        .with_for_update(of=(ParticipantNotice, Enrollment, Participant, Application))
    )
    if row is None:
        raise AuthError("not_found", 404)
    if row.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if row.read_at is None:
        row.read_at = now()
        row.version += 1
        _audit(
            db,
            org,
            row.id,
            "participant_notification.read",
            row.version,
            actor=current.id,
            request_id=request_id,
        )
        db.commit()
    return view(row)


def _settle(
    db: Session, event: DomainOutbox, state: str, code: str = "", *, consume_attempt: bool = True
) -> str:
    event.state, event.error_code = state, code
    event.attempt_count += int(consume_attempt)
    event.version += 1
    event.next_attempt_at = None
    event.settled_at = now()
    event.dispatched = state == "dispatched"
    event.dispatched_at = event.settled_at if event.dispatched else None
    _audit(db, event.organization_id, event.id, f"participant_outbox.{state}", event.version)
    return state


def _retry_deadline(attempt: int) -> datetime:
    return now() + timedelta(seconds=min(300, 5 * 2**attempt))


def _process(db: Session, event: DomainOutbox, settings: Settings) -> str:
    if event.attempt_count >= settings.participant_notification_max_attempts:
        return _settle(db, event, "failed", "retry_exhausted", consume_attempt=False)
    if event.event_type != "enrollment.created":
        return _settle(db, event, "unsupported", "unsupported_event")
    payload = enrollment_payload(event)
    if payload is None:
        return _settle(db, event, "invalid", "invalid_payload")
    days = settings.participant_notification_retention_days
    assert days is not None
    expires = event.created_at + timedelta(days=days)
    if expires <= now():
        return _settle(db, event, "expired", "event_expired")
    context = db.execute(
        select(Enrollment, Participant, Application)
        .join(
            Participant,
            (Participant.id == Enrollment.participant_id)
            & (Participant.organization_id == Enrollment.organization_id),
        )
        .join(
            Application,
            (Application.id == Enrollment.application_id)
            & (Application.organization_id == Enrollment.organization_id),
        )
        .where(
            Enrollment.id == payload.enrollment_id,
            Enrollment.organization_id == event.organization_id,
            Enrollment.participant_id == payload.participant_id,
            Enrollment.application_id == payload.application_id,
            Application.person_id == Participant.person_id,
            Application.state == "enrolled",
        )
        .execution_options(populate_existing=True)
        .with_for_update(of=(Enrollment, Participant, Application))
    ).one_or_none()
    if context is None:
        return _settle(db, event, "invalid", "invalid_payload")
    enrollment, participant, _ = context
    user = db.scalar(
        select(User)
        .where(User.person_id == participant.person_id)
        .execution_options(populate_existing=True)
        .with_for_update()
    )
    if (
        enrollment.status not in {"active", "completed"}
        or participant.status not in {"active", "completed"}
        or user is None
        or user.status != "active"
    ):
        return _settle(db, event, "suppressed", "recipient_unavailable")
    grant = db.scalar(
        select(UserRole.id)
        .join(RolePermission, RolePermission.role_id == UserRole.role_id)
        .where(
            UserRole.user_id == user.id,
            UserRole.organization_id == event.organization_id,
            RolePermission.permission_code == "participant.self",
        )
        .order_by(UserRole.id)
        .limit(1)
        .with_for_update(of=(UserRole, RolePermission))
    )
    if grant is None:
        return _settle(db, event, "suppressed", "recipient_unavailable")
    pref = db.scalar(
        select(ParticipantNoticePreference)
        .where(
            ParticipantNoticePreference.organization_id == event.organization_id,
            ParticipantNoticePreference.user_id == user.id,
        )
        .with_for_update()
    )
    if pref is not None and not pref.enabled:
        return _settle(db, event, "suppressed", "preference_disabled")
    notice = ParticipantNotice(
        organization_id=event.organization_id,
        recipient_user_id=user.id,
        enrollment_id=enrollment.id,
        source_event_id=event.id,
        created_at=event.created_at,
        expires_at=expires,
    )
    db.add(notice)
    # The event's SQL settlement guard requires the accepted notice to exist first.
    db.flush([notice])
    _audit(db, event.organization_id, notice.id, "participant_notification.created", 1)
    return _settle(db, event, "dispatched")


def consume_pending(db: Session, settings: Settings | None = None) -> dict[str, int | bool]:
    policy = settings or get_settings()
    counts: dict[str, int | bool] = {
        key: 0
        for key in (
            "dispatched",
            "suppressed",
            "unsupported",
            "invalid",
            "retrying",
            "failed",
            "expired",
        )
    }
    counts["retention_configured"] = policy.participant_notification_retention_days is not None
    if policy.participant_notification_retention_days is None:
        return counts
    events = list(
        db.scalars(
            select(DomainOutbox)
            .where(
                DomainOutbox.state.in_(("pending", "retrying")),
                DomainOutbox.next_attempt_at <= now(),
            )
            .order_by(DomainOutbox.created_at, DomainOutbox.id)
            .limit(policy.participant_notification_batch_size)
            .execution_options(populate_existing=True)
            .with_for_update(skip_locked=True)
        )
    )
    for event in events:
        try:
            with db.begin_nested():
                state = _process(db, event, policy)
                db.flush()
        except Exception:
            # Savepoint rollback discards any partially inserted notice and audit.
            db.refresh(event)
            if event.attempt_count >= policy.participant_notification_max_attempts - 1:
                state = _settle(db, event, "failed", "retry_exhausted")
            else:
                event.attempt_count += 1
                event.version += 1
                event.state, event.error_code = "retrying", "dispatch_error"
                event.next_attempt_at = _retry_deadline(event.attempt_count)
                _audit(
                    db,
                    event.organization_id,
                    event.id,
                    "participant_outbox.retrying",
                    event.version,
                )
                state = "retrying"
        counts[state] = int(counts[state]) + 1
        db.flush()
    db.commit()
    return counts


def purge_expired(db: Session, settings: Settings | None = None) -> int:
    policy = settings or get_settings()
    if policy.participant_notification_retention_days is None:
        return 0
    rows = list(
        db.scalars(
            select(ParticipantNotice)
            .where(ParticipantNotice.expires_at <= now())
            .order_by(ParticipantNotice.expires_at, ParticipantNotice.id)
            .limit(policy.participant_notification_batch_size)
            .with_for_update(skip_locked=True)
        )
    )
    for row in rows:
        _audit(
            db,
            row.organization_id,
            row.id,
            "participant_notification.expired_disposal",
            row.version,
        )
        db.delete(row)
    db.commit()
    return len(rows)


def health(db: Session, org: UUID, actor: User) -> ParticipantOutboxHealth:
    current = _active_actor(db, actor)
    require_permission(db, current, org, "notification.operations.view")
    totals: dict[str, int] = {
        state: count
        for state, count in db.execute(
            select(DomainOutbox.state, func.count())
            .where(DomainOutbox.organization_id == org)
            .group_by(DomainOutbox.state)
        ).all()
    }
    due_count, oldest = db.execute(
        select(func.count(), func.min(DomainOutbox.created_at)).where(
            DomainOutbox.organization_id == org,
            DomainOutbox.state.in_(("pending", "retrying")),
            DomainOutbox.next_attempt_at <= now(),
        )
    ).one()
    return ParticipantOutboxHealth(
        pending_due=int(due_count),
        oldest_due_seconds=max(0.0, (now() - oldest).total_seconds()) if oldest else None,
        retrying=totals.get("retrying", 0),
        dispatched=totals.get("dispatched", 0),
        suppressed=totals.get("suppressed", 0),
        unsupported=totals.get("unsupported", 0),
        invalid=totals.get("invalid", 0),
        failed=totals.get("failed", 0),
        expired=totals.get("expired", 0),
        retention_configured=get_settings().participant_notification_retention_days is not None,
    )
