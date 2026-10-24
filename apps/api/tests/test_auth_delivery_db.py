import json
import os
import secrets
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_identity import auth  # noqa: F401

from app.core.config import get_settings
from app.modules.identity import delivery_service as service
from app.modules.identity import service as identity_service
from app.modules.identity.auth_mail import EDITION, MailResult, message_identity
from app.modules.identity.models import (
    AuditLog,
    AuthDelivery,
    Person,
    User,
    UserRole,
    VerificationToken,
    now,
)
from app.modules.identity.security import AuthError, digest
from app.workers import auth_deliveries

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)


@pytest.fixture
def delivery_db(request, monkeypatch):
    client, engine, key, _ = request.getfixturevalue("auth")
    values = {
        "AUTH_DELIVERY_BACKEND": "smtp",
        "AUTH_SMTP_ENABLED": "true",
        "AUTH_TEMPLATES_APPROVED": "true",
        "AUTH_CANONICAL_ORIGIN": "https://edp.example.test",
        "AUTH_SMTP_HOST": "127.0.0.1",
        "AUTH_SMTP_PORT": "465",
        "AUTH_SMTP_TLS_MODE": "implicit",
        "AUTH_SMTP_USERNAME": "synthetic-user",
        "AUTH_SMTP_PASSWORD": "synthetic-password",
        "AUTH_SMTP_FROM_ADDRESS": "edp@example.test",
        "AUTH_DELIVERY_RETENTION_DAYS": "2",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(auth_deliveries, "engine", engine)
    get_settings.cache_clear()
    yield client, engine, key, get_settings()
    get_settings.cache_clear()


def intent(delivery_db, *, purpose="verify", status=None, expires_in=1800, age_days=0):
    _, engine, key, policy = delivery_db
    raw, identity = secrets.token_urlsafe(32), uuid4()
    with Session(engine) as db:
        person = Person(display_name="Synthetic global identity", locale="ta")
        db.add(person)
        db.flush()
        user = User(
            person_id=person.id,
            email=f"auth-{identity.hex}@example.test",
            password_hash="synthetic-unused",
            status=status or ("pending" if purpose == "verify" else "active"),
        )
        db.add(user)
        db.flush()
        challenge = VerificationToken(
            user_id=user.id,
            token_hash=digest(raw),
            purpose=purpose,
            expires_at=now() + timedelta(seconds=expires_in),
        )
        db.add(challenge)
        db.flush()
        payload = (
            Fernet(key)
            .encrypt(json.dumps({"email": user.email, "purpose": purpose, "token": raw}).encode())
            .decode()
        )
        row = AuthDelivery(
            id=identity,
            token_id=challenge.id,
            encrypted_payload=payload,
            transport="smtp",
            status="queued",
            locale="ta",
            template_version=EDITION,
            message_id=message_identity(str(identity), policy),
            next_attempt_at=now(),
            created_at=now() - timedelta(days=age_days),
        )
        db.add(row)
        db.commit()
        return identity, user.id, challenge.id, raw


def claimed(delivery_db, identity, policy=None):
    with Session(delivery_db[1]) as db:
        return service.claim(db, identity, policy or delivery_db[3])


def sending(delivery_db, lease, policy=None):
    with Session(delivery_db[1]) as db:
        assert service.prepare_mail(db, lease, policy or delivery_db[3])
    with Session(delivery_db[1]) as db:
        result = service.begin_send(db, lease, policy or delivery_db[3])
        assert result
        return result


def test_configured_production_registration_queues_without_provider_or_org(
    delivery_db, monkeypatch
):
    client, engine, key, _ = delivery_db
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    provider = MagicMock(side_effect=AssertionError("request called provider"))
    monkeypatch.setattr(auth_deliveries, "SMTPProvider", provider)
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "configured@example.com",
            "password": secrets.token_urlsafe(24),
            "display_name": "Synthetic configured user",
            "locale": "ta",
        },
    )
    assert response.status_code == 202 and response.json() == {"status": "accepted"}
    provider.assert_not_called()
    with Session(engine) as db:
        row = db.scalar(select(AuthDelivery))
        assert row and row.status == "queued" and row.locale == "ta" and row.attempt_count == 0
        payload = json.loads(Fernet(key).decrypt(row.encrypted_payload.encode()))
        assert (
            payload["token"] not in response.text and payload["token"] not in row.encrypted_payload
        )
        assert db.scalar(select(func.count()).select_from(UserRole)) == 0
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.action == "auth.verify_requested")
            )
            == 1
        )


def test_worker_acceptance_single_use_duplicate_and_global_identity(delivery_db, monkeypatch):
    identity, user_id, _, raw = intent(delivery_db)
    sender = MagicMock()
    sender.send.return_value = MailResult("accepted", "smtp_250")
    monkeypatch.setattr(auth_deliveries, "SMTPProvider", lambda _: sender)
    assert auth_deliveries.deliver_challenge.run(str(identity)) == {"status": "accepted"}
    assert auth_deliveries.deliver_challenge.run(str(identity)) == {"status": "ignored"}
    sender.send.assert_called_once()
    with Session(delivery_db[1]) as db:
        row = db.get(AuthDelivery, identity)
        assert row and row.status == "accepted" and row.attempt_count == 1 and row.version == 4
        assert row.provider_reference == "smtp_250" and row.lease_until is None
        identity_service.consume_challenge(db, raw, "verify", "synthetic-consumption")
        assert db.get(User, user_id).status == "active"
        with pytest.raises(AuthError):
            identity_service.consume_challenge(db, raw, "verify", "synthetic-replay")


@pytest.mark.parametrize(
    "change,reason",
    [
        ("expire", "challenge_expired"),
        ("consume", "challenge_obsolete"),
        ("suspend", "account_ineligible"),
    ],
)
def test_obsolete_or_ineligible_challenges_are_suppressed(delivery_db, monkeypatch, change, reason):
    identity, user_id, token_id, _ = intent(delivery_db)
    with Session(delivery_db[1]) as db:
        if change == "expire":
            db.get(VerificationToken, token_id).expires_at = now() - timedelta(seconds=1)
        elif change == "consume":
            db.get(VerificationToken, token_id).consumed_at = now()
        else:
            db.get(User, user_id).status = "suspended"
        db.commit()
    sender = MagicMock(side_effect=AssertionError("suppressed message sent"))
    monkeypatch.setattr(auth_deliveries, "SMTPProvider", sender)
    assert auth_deliveries.deliver_challenge.run(str(identity)) == {"status": "ignored"}
    sender.assert_not_called()
    with Session(delivery_db[1]) as db:
        row = db.get(AuthDelivery, identity)
        assert row.status == "suppressed" and row.error_code == reason and row.attempt_count == 0


def test_new_challenge_supersedes_old_without_exposing_old_secret(delivery_db):
    identity, user_id, _, _ = intent(delivery_db)
    with Session(delivery_db[1]) as db:
        user = db.get(User, user_id)
        identity_service.issue_challenge(db, user, "verify", "synthetic-new-challenge")
        db.commit()
    assert claimed(delivery_db, identity) is None
    with Session(delivery_db[1]) as db:
        assert db.get(AuthDelivery, identity).error_code == "challenge_obsolete"
        current = db.scalar(select(AuthDelivery).where(AuthDelivery.id != identity))
        assert (
            current
            and current.status == "queued"
            and current.message_id != db.get(AuthDelivery, identity).message_id
        )


def test_concurrent_claim_and_pre_send_authorization_recheck(delivery_db):
    identity, user_id, _, _ = intent(delivery_db)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: claimed(delivery_db, identity), range(2)))
    leases = [result for result in results if result]
    assert len(leases) == 1
    with Session(delivery_db[1]) as db:
        assert service.prepare_mail(db, leases[0], delivery_db[3])
        db.get(User, user_id).status = "suspended"
        db.commit()
    with Session(delivery_db[1]) as db:
        assert service.begin_send(db, leases[0], delivery_db[3]) is None
        assert db.get(AuthDelivery, identity).status == "suppressed"


def test_preparing_crash_is_retryable_and_final_claim_exhaustion_visible(delivery_db):
    policy = delivery_db[3].model_copy(update={"auth_delivery_lease_seconds": 1})
    first = intent(delivery_db)[0]
    final = intent(delivery_db)[0]
    assert claimed(delivery_db, first, policy)
    assert claimed(delivery_db, final, policy)
    time.sleep(1.05)
    with Session(delivery_db[1]) as db:
        # A bound of one means both claims are exhausted; no implicit attempt reset.
        exhausted = policy.model_copy(update={"auth_delivery_max_attempts": 1})
        assert service.recover(db, exhausted) == ([], 2)
        for identity in (first, final):
            row = db.get(AuthDelivery, identity)
            assert row.status == "failed" and row.error_code == "retry_exhausted"
    retry = intent(delivery_db)[0]
    assert claimed(delivery_db, retry, policy)
    time.sleep(1.05)
    with Session(delivery_db[1]) as db:
        assert service.recover(db, policy) == ([], 1)
        row = db.get(AuthDelivery, retry)
        assert row.status == "retrying" and row.error_code == "preparation_interrupted"
        assert row.next_attempt_at > now() and row.attempt_count == 1


def test_sending_crash_never_auto_resends_and_late_result_is_fenced(delivery_db):
    policy = delivery_db[3].model_copy(update={"auth_delivery_lease_seconds": 1})
    identity = intent(delivery_db)[0]
    lease = sending(delivery_db, claimed(delivery_db, identity, policy), policy)
    time.sleep(1.05)
    with Session(delivery_db[1]) as db:
        assert service.recover(db, policy) == ([], 1)
        row = db.get(AuthDelivery, identity)
        assert row.status == "ambiguous" and row.error_code == "sending_interrupted"
        assert service.recover(db, policy) == ([], 0)
        assert not service.settle(db, lease, MailResult("accepted", "smtp_250"), policy)
        with pytest.raises(AuthError):
            service.operator_recover(
                db,
                identity,
                row.version,
                "retry",
                "Synthetic review cannot deduplicate SMTP",
                policy,
            )
        db.rollback()
        service.operator_recover(
            db,
            identity,
            row.version,
            "accepted",
            "Synthetic provider acceptance independently confirmed",
            policy,
        )
        db.refresh(row)
        assert row.status == "accepted" and row.provider_reference == "operator_accepted"


@pytest.mark.parametrize(
    "outcome,code,status",
    [
        ("transient", "provider_temporary", "retrying"),
        ("permanent", "provider_rejected", "failed"),
        ("ambiguous", "acknowledgement_unknown", "ambiguous"),
    ],
)
def test_truthful_worker_outcomes_and_safe_health(delivery_db, monkeypatch, outcome, code, status):
    identity, _, _, raw = intent(delivery_db)
    sender = MagicMock()
    sender.send.return_value = MailResult(outcome, code)
    monkeypatch.setattr(auth_deliveries, "SMTPProvider", lambda _: sender)
    assert auth_deliveries.deliver_challenge.run(str(identity)) == {"status": outcome}
    with Session(delivery_db[1]) as db:
        row = db.get(AuthDelivery, identity)
        assert row.status == status and row.error_code == code and row.provider_reference == ""
        safe = json.dumps(service.health(db, delivery_db[3]))
        assert raw not in safe and "@example.test" not in safe and "encrypted_payload" not in safe


def test_broker_failure_keeps_durable_intent_discoverable(delivery_db, monkeypatch):
    identity = intent(delivery_db)[0]
    publish = MagicMock(side_effect=RuntimeError("Synthetic broker failure"))
    monkeypatch.setattr(auth_deliveries, "publish_delivery", publish)
    assert auth_deliveries.recover_deliveries.run()["dispatch_failed"] == 1
    with Session(delivery_db[1]) as db:
        row = db.get(AuthDelivery, identity)
        assert row.status == "queued" and row.version == 1 and row.attempt_count == 0
        assert service.recover(db, delivery_db[3]) == ([identity], 0)


def test_explicit_retention_disposes_only_expired_payload_preserving_metadata(delivery_db):
    identity, _, token_id, _ = intent(delivery_db, expires_in=-1, age_days=3)
    with Session(delivery_db[1]) as db:
        assert (
            service.dispose(
                db, delivery_db[3].model_copy(update={"auth_delivery_retention_days": None})
            )
            == 0
        )
        assert service.recover(db, delivery_db[3]) == ([], 1)
        assert service.dispose(db, delivery_db[3]) == 1
        row = db.get(AuthDelivery, identity)
        assert row.encrypted_payload == "" and row.disposed_at and row.token_id == token_id
        assert row.status == "suppressed" and row.version == 3
        assert service.dispose(db, delivery_db[3]) == 0
        assert (
            db.scalar(
                select(func.count()).select_from(AuditLog).where(AuditLog.resource_id == identity)
            )
            == 2
        )


def test_sql_guards_reject_identity_payload_version_and_unknown_retry(delivery_db):
    identity = intent(delivery_db)[0]
    mutations = (
        "UPDATE auth_deliveries SET message_id='forged',version=version+1 WHERE id=:id",
        "UPDATE auth_deliveries SET encrypted_payload='replacement',version=version+1 WHERE id=:id",
        "UPDATE auth_deliveries SET version=version-1 WHERE id=:id",
        "UPDATE auth_deliveries SET status='sending',version=version+1 WHERE id=:id",
        "DELETE FROM auth_deliveries WHERE id=:id",
    )
    for statement in mutations:
        with Session(delivery_db[1]) as db:
            with pytest.raises(DBAPIError):
                db.execute(text(statement), {"id": identity})
                db.commit()
            db.rollback()
    policy = delivery_db[3].model_copy(update={"auth_delivery_lease_seconds": 1})
    sending(delivery_db, claimed(delivery_db, identity, policy), policy)
    time.sleep(1.05)
    with Session(delivery_db[1]) as db:
        with pytest.raises(DBAPIError):
            db.execute(
                text(
                    "UPDATE auth_deliveries SET status='retrying',lease_until=NULL,"
                    "lease_token_digest=NULL,"
                    "next_attempt_at=clock_timestamp()+interval '10 seconds',"
                    "version=version+1 WHERE id=:id"
                ),
                {"id": identity},
            )
            db.commit()
        db.rollback()


def test_auth_intent_and_challenge_rollback_with_registration_audit(delivery_db, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("Synthetic audit interruption")

    monkeypatch.setattr(identity_service, "audit", fail)
    response = delivery_db[0].post(
        "/api/v1/auth/register",
        json={
            "email": "rollback-smtp@example.com",
            "password": secrets.token_urlsafe(24),
            "display_name": "Synthetic rollback",
        },
    )
    assert response.status_code == 500
    with Session(delivery_db[1]) as db:
        assert db.scalar(select(func.count()).select_from(AuthDelivery)) == 0
        assert db.scalar(select(func.count()).select_from(VerificationToken)) == 0
        assert db.scalar(select(func.count()).select_from(User)) == 0


def test_sql_cannot_disguise_ambiguous_send_as_retryable_failure(delivery_db):
    identity = intent(delivery_db)[0]
    lease = sending(delivery_db, claimed(delivery_db, identity))
    with Session(delivery_db[1]) as db:
        assert service.settle(
            db, lease, MailResult("ambiguous", "acknowledgement_unknown"), delivery_db[3]
        )
        with pytest.raises(DBAPIError):
            db.execute(
                text(
                    "UPDATE auth_deliveries SET status='failed',error_code='provider_rejected',"
                    "provider_reference='',version=version+1 WHERE id=:id"
                ),
                {"id": identity},
            )
            db.commit()
        db.rollback()
        # Even an explicit reasoned failure settlement cannot make uncertain SMTP
        # work eligible for a resend under its unchanged message identity.
        row = db.get(AuthDelivery, identity)
        service.operator_recover(
            db,
            identity,
            row.version,
            "failed",
            "Synthetic uncertain send closed without resend",
            delivery_db[3],
        )
        with pytest.raises(DBAPIError):
            db.execute(
                text(
                    "UPDATE auth_deliveries SET status='queued',error_code='',completed_at=NULL,"
                    "next_attempt_at=clock_timestamp(),version=version+1 WHERE id=:id"
                ),
                {"id": identity},
            )
            db.commit()
        db.rollback()
