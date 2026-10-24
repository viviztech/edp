"""Durable global identity challenge delivery with an explicit uncertain-send state."""

import sqlalchemy as sa
from alembic import op

revision = "o0e6f2a8b345"
down_revision = "n9d5e1f7a234"
branch_labels = None
depends_on = None

CHECKS = {
    "auth_delivery_transport": "transport IN ('development','smtp')",
    "auth_delivery_locale": "locale IN ('en','ta')",
    "auth_delivery_template": "template_version = 'auth-v1'",
    "auth_delivery_version": "version > 0 AND attempt_count BETWEEN 0 AND 10",
    "auth_delivery_status": (
        "(transport = 'development' AND status = 'development') OR "
        "(transport = 'smtp' AND status IN ('queued','preparing','sending','retrying',"
        "'accepted','failed','ambiguous','suppressed')) OR status = 'suppressed'"
    ),
    "auth_delivery_lease": (
        "(status IN ('preparing','sending') AND lease_token_digest ~ '^[0-9a-f]{64}$' "
        "AND lease_token_digest IS NOT NULL AND lease_until IS NOT NULL "
        "AND next_attempt_at IS NULL AND completed_at IS NULL) OR "
        "(status NOT IN ('preparing','sending') AND lease_token_digest IS NULL "
        "AND lease_until IS NULL)"
    ),
    "auth_delivery_schedule": (
        "(status IN ('queued','retrying') AND next_attempt_at IS NOT NULL "
        "AND completed_at IS NULL) OR "
        "(status IN ('accepted','failed','ambiguous','suppressed') "
        "AND next_attempt_at IS NULL AND completed_at IS NOT NULL) OR "
        "(status IN ('development','preparing','sending') AND next_attempt_at IS NULL "
        "AND completed_at IS NULL)"
    ),
    "auth_delivery_disposal": (
        "(disposed_at IS NULL AND length(encrypted_payload) > 0) OR "
        "(disposed_at IS NOT NULL AND encrypted_payload = '' "
        "AND status IN ('accepted','failed','ambiguous','suppressed'))"
    ),
    "auth_delivery_provider_reference": (
        "provider_reference IN ('','smtp_250','operator_accepted') "
        "AND (status <> 'accepted' OR provider_reference <> '')"
    ),
    "auth_delivery_error": (
        "error_code IN ('','challenge_expired','challenge_obsolete','account_ineligible',"
        "'payload_invalid','configuration_unavailable','message_invalid','tls_unverified',"
        "'provider_temporary','provider_rejected','connection_failed','acknowledgement_unknown',"
        "'sending_interrupted','preparation_interrupted','retry_exhausted','operator_failed')"
    ),
}


def upgrade() -> None:
    for name, length, default in (
        ("transport", 16, "development"),
        ("locale", 2, "en"),
        ("template_version", 24, "auth-v1"),
        ("message_id", 320, ""),
        ("error_code", 40, ""),
        ("provider_reference", 40, ""),
    ):
        op.add_column(
            "auth_deliveries",
            sa.Column(name, sa.String(length), nullable=False, server_default=default),
        )
    for name, default in (("version", "1"), ("attempt_count", "0")):
        op.add_column(
            "auth_deliveries", sa.Column(name, sa.Integer(), nullable=False, server_default=default)
        )
    op.add_column("auth_deliveries", sa.Column("lease_token_digest", sa.String(64), nullable=True))
    for name in ("lease_until", "next_attempt_at", "completed_at", "disposed_at"):
        op.add_column("auth_deliveries", sa.Column(name, sa.DateTime(timezone=True), nullable=True))
    # Historical rows are local encrypted messages, never evidence of SMTP delivery.
    op.execute("""
      UPDATE auth_deliveries d SET status='development',
        message_id='<auth-' || d.id::text || '@development.invalid>', locale=p.locale
      FROM verification_tokens t JOIN users u ON u.id=t.user_id
      JOIN people p ON p.id=u.person_id WHERE d.token_id=t.id
    """)
    for name, expression in CHECKS.items():
        op.create_check_constraint(name, "auth_deliveries", expression)
    op.create_unique_constraint("uq_auth_deliveries_message_id", "auth_deliveries", ["message_id"])
    op.create_index("ix_auth_delivery_due", "auth_deliveries", ["status", "next_attempt_at", "id"])
    op.create_index("ix_auth_delivery_lease", "auth_deliveries", ["status", "lease_until", "id"])
    op.create_index("ix_auth_delivery_retention", "auth_deliveries", ["created_at", "id"])
    for name in (
        "transport",
        "locale",
        "template_version",
        "message_id",
        "error_code",
        "provider_reference",
        "version",
        "attempt_count",
    ):
        op.alter_column("auth_deliveries", name, server_default=None)
    op.execute("""
    CREATE FUNCTION guard_auth_delivery() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP='DELETE' THEN RAISE EXCEPTION 'auth delivery metadata is retained'; END IF;
      IF TG_OP='INSERT' THEN
        IF NEW.status NOT IN ('development','queued') OR NEW.version<>1
           OR NEW.attempt_count<>0 OR NEW.disposed_at IS NOT NULL
           OR NEW.error_code<>'' OR NEW.provider_reference<>'' THEN
          RAISE EXCEPTION 'auth delivery must begin with a new intent';
        END IF;
        RETURN NEW;
      END IF;
      IF (NEW.id,NEW.token_id,NEW.created_at,NEW.transport,NEW.locale,
          NEW.template_version,NEW.message_id)
         IS DISTINCT FROM
         (OLD.id,OLD.token_id,OLD.created_at,OLD.transport,OLD.locale,OLD.template_version,OLD.message_id)
         OR NEW.version<>OLD.version+1 THEN
        RAISE EXCEPTION 'auth delivery identity and version are protected';
      END IF;
      IF NEW.disposed_at IS DISTINCT FROM OLD.disposed_at THEN
        IF OLD.disposed_at IS NOT NULL OR NEW.disposed_at IS NULL
           OR NEW.encrypted_payload<>'' OR NEW.status<>OLD.status
           OR NEW.status NOT IN ('accepted','failed','ambiguous','suppressed')
           OR NEW.attempt_count<>OLD.attempt_count
           OR NEW.completed_at IS DISTINCT FROM OLD.completed_at
           OR NEW.error_code<>OLD.error_code OR NEW.provider_reference<>OLD.provider_reference
           OR (SELECT expires_at FROM verification_tokens WHERE id=OLD.token_id)
              >clock_timestamp() THEN
          RAISE EXCEPTION 'auth payload disposal requires expired terminal work';
        END IF;
        RETURN NEW;
      END IF;
      IF NEW.encrypted_payload IS DISTINCT FROM OLD.encrypted_payload
         OR OLD.disposed_at IS NOT NULL THEN
        RAISE EXCEPTION 'auth encrypted payload is immutable';
      END IF;
      IF OLD.status IN ('queued','retrying') AND NEW.status='preparing' THEN
        IF NEW.attempt_count<>OLD.attempt_count+1 OR OLD.next_attempt_at>clock_timestamp()
           OR NEW.lease_until<=clock_timestamp()
           OR NEW.lease_until>clock_timestamp()+interval '900 seconds'
           OR (SELECT expires_at FROM verification_tokens WHERE id=OLD.token_id)
              <=clock_timestamp() THEN
          RAISE EXCEPTION 'auth claim requires current due work';
        END IF;
      ELSE
        IF NEW.attempt_count<>OLD.attempt_count THEN
          RAISE EXCEPTION 'auth settlement cannot change attempts';
        END IF;
        IF OLD.status='preparing' AND NEW.status='sending' THEN
          IF OLD.lease_until<=clock_timestamp() OR NEW.lease_until<>OLD.lease_until
             OR NEW.lease_token_digest<>OLD.lease_token_digest THEN
            RAISE EXCEPTION 'auth send requires a current fenced lease';
          END IF;
        ELSIF OLD.status='preparing' AND NEW.status IN ('retrying','failed','suppressed') THEN
          NULL;
        ELSIF OLD.status='sending'
          AND NEW.status IN ('accepted','retrying','failed','ambiguous','suppressed') THEN
          IF OLD.lease_until<=clock_timestamp() AND NEW.status<>'ambiguous' THEN
            RAISE EXCEPTION 'expired sends require operator review';
          END IF;
        ELSIF OLD.status IN ('queued','retrying','development') AND NEW.status='suppressed' THEN
          NULL;
        ELSIF OLD.status IN ('queued','retrying') AND NEW.status='failed' THEN
          NULL;
        ELSIF OLD.status='failed' AND NEW.status='queued' THEN
          IF OLD.error_code='operator_failed' OR NEW.attempt_count>=10
             OR NEW.next_attempt_at IS NULL THEN
            RAISE EXCEPTION 'auth retry remains bounded';
          END IF;
        ELSIF OLD.status='ambiguous' AND NEW.status IN ('accepted','failed') THEN
          IF (NEW.status='accepted' AND
              (NEW.provider_reference<>'operator_accepted' OR NEW.error_code<>''))
             OR (NEW.status='failed' AND
              (NEW.provider_reference<>'' OR NEW.error_code<>'operator_failed')) THEN
            RAISE EXCEPTION 'auth uncertain settlement requires operator evidence';
          END IF;
        ELSE RAISE EXCEPTION 'invalid auth delivery transition';
        END IF;
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER trg_auth_delivery BEFORE INSERT OR UPDATE OR DELETE ON auth_deliveries
      FOR EACH ROW EXECUTE FUNCTION guard_auth_delivery();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_auth_delivery ON auth_deliveries")
    op.execute("DROP FUNCTION guard_auth_delivery()")
    for name in ("ix_auth_delivery_due", "ix_auth_delivery_lease", "ix_auth_delivery_retention"):
        op.drop_index(name, table_name="auth_deliveries")
    op.drop_constraint("uq_auth_deliveries_message_id", "auth_deliveries", type_="unique")
    for name in CHECKS:
        op.drop_constraint(name, "auth_deliveries", type_="check")
    for name in (
        "transport",
        "locale",
        "template_version",
        "message_id",
        "error_code",
        "provider_reference",
        "version",
        "attempt_count",
        "lease_token_digest",
        "lease_until",
        "next_attempt_at",
        "completed_at",
        "disposed_at",
    ):
        op.drop_column("auth_deliveries", name)
