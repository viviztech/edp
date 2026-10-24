"""ID-only authentication delivery tasks; SMTP runs outside request transactions."""

import time
from uuid import UUID

import structlog
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.identity import delivery_service as service
from app.modules.identity.auth_mail import MailResult, SMTPProvider
from app.workers.celery_app import celery_app

engine = create_engine(
    get_settings().database_url.get_secret_value(),
    pool_pre_ping=True,
    connect_args={"connect_timeout": 3, "options": "-c statement_timeout=5000"},
)
log = structlog.get_logger()


@celery_app.task(name="edp.auth.deliver_challenge")  # type: ignore[untyped-decorator]
def deliver_challenge(delivery_id: str) -> dict[str, str]:
    try:
        identity = UUID(delivery_id)
    except (ValueError, TypeError, AttributeError):
        return {"status": "ignored"}
    policy = get_settings()
    with Session(engine) as db:
        lease = service.claim(db, identity, policy)
    if lease is None:
        return {"status": "ignored"}
    with Session(engine) as db:
        message = service.prepare_mail(db, lease, policy)
    if message is None:
        return {"status": "suppressed"}
    with Session(engine) as db:
        sending = service.begin_send(db, lease, policy)
    if sending is None:
        return {"status": "suppressed"}
    try:
        result = SMTPProvider(policy).send(message)
    except Exception:
        # Unknown adapter failure after the durable send marker never auto-resends.
        result = MailResult("ambiguous", "acknowledgement_unknown")
    with Session(engine) as db:
        accepted = service.settle(db, sending, result, policy)
    return {"status": result.outcome if accepted else "stale"}


def publish_delivery(identity: UUID) -> None:
    with celery_app.connection_for_write(
        connect_timeout=2,
        transport_options={
            "socket_connect_timeout": 2,
            "socket_timeout": 2,
            "retry_on_timeout": False,
            "max_retries": 0,
            "connect_retries_timeout": 2,
        },
    ) as connection:
        celery_app.send_task(
            "edp.auth.deliver_challenge",
            args=[str(identity)],
            connection=connection,
            retry=False,
            ignore_result=True,
            expires=120,
        )


@celery_app.task(name="edp.auth.recover_deliveries")  # type: ignore[untyped-decorator]
def recover_deliveries() -> dict[str, int]:
    policy = get_settings()
    with Session(engine) as db:
        identities, settled = service.recover(db, policy)
        disposed = service.dispose(db, policy)
    published = failed = 0
    deadline = time.monotonic() + 10
    for identity in identities:
        if time.monotonic() >= deadline:
            break
        try:
            publish_delivery(identity)
            published += 1
        except Exception:
            failed += 1
            log.warning("auth_delivery_dispatch_unavailable", delivery_id=str(identity))
    return {
        "published": published,
        "dispatch_failed": failed,
        "settled": settled,
        "disposed": disposed,
    }
