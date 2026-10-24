"""Consume typed enrollment events into an isolated participant inbox."""

import sqlalchemy as sa
from alembic import op

revision = "p1f7a3b9c456"
down_revision = "o0e6f2a8b345"
branch_labels = None
depends_on = None

OUTBOX_CHECKS = {
    "domain_outbox_state": "state IN ('pending','retrying','dispatched','suppressed',"
    "'unsupported','invalid','failed','expired')",
    "domain_outbox_attempts": "version > 0 AND attempt_count BETWEEN 0 AND 10",
    "domain_outbox_settlement": "(state IN ('pending','retrying') AND next_attempt_at IS NOT NULL "
    "AND settled_at IS NULL AND NOT dispatched) OR "
    "(state = 'dispatched' AND next_attempt_at IS NULL AND settled_at IS NOT NULL "
    "AND dispatched AND dispatched_at = settled_at) OR "
    "(state IN ('suppressed','unsupported','invalid','failed','expired') "
    "AND next_attempt_at IS NULL AND settled_at IS NOT NULL AND NOT dispatched)",
    "domain_outbox_error": "(state IN ('pending','dispatched') AND error_code = '') OR "
    "(state = 'retrying' AND error_code = 'dispatch_error') OR "
    "(state = 'suppressed' AND error_code IN ('recipient_unavailable','preference_disabled')) OR "
    "(state = 'unsupported' AND error_code = 'unsupported_event') OR "
    "(state = 'invalid' AND error_code = 'invalid_payload') OR "
    "(state = 'failed' AND error_code = 'retry_exhausted') OR "
    "(state = 'expired' AND error_code = 'event_expired')",
}


def upgrade() -> None:
    for name, default in (("state", "pending"), ("error_code", "")):
        op.add_column(
            "domain_outbox",
            sa.Column(
                name,
                sa.String(16 if name == "state" else 40),
                nullable=False,
                server_default=default,
            ),
        )
    for name, default in (("version", "1"), ("attempt_count", "0")):
        op.add_column(
            "domain_outbox",
            sa.Column(
                name,
                sa.Integer(),
                nullable=False,
                server_default=default,
            ),
        )
    for name in ("next_attempt_at", "settled_at"):
        op.add_column("domain_outbox", sa.Column(name, sa.DateTime(timezone=True), nullable=True))
    # Preserve previously recorded dispatches without manufacturing inbox history.
    op.execute("""
        UPDATE domain_outbox SET
          state = CASE WHEN dispatched THEN 'dispatched' ELSE 'pending' END,
          attempt_count = CASE WHEN dispatched THEN 1 ELSE 0 END,
          next_attempt_at = CASE WHEN dispatched THEN NULL ELSE created_at END,
          settled_at = CASE WHEN dispatched THEN dispatched_at ELSE NULL END
    """)
    for name, expression in OUTBOX_CHECKS.items():
        op.create_check_constraint(name, "domain_outbox", expression)
    op.create_unique_constraint(
        "uq_domain_outbox_scope", "domain_outbox", ["id", "organization_id"]
    )
    op.create_index("ix_domain_outbox_due", "domain_outbox", ["state", "next_attempt_at", "id"])
    for name in ("state", "error_code", "version", "attempt_count"):
        op.alter_column("domain_outbox", name, server_default=None)
    op.create_table(
        "participant_notices",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_user_id", sa.Uuid(), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("source_event_id", sa.Uuid(), nullable=False),
        sa.Column("topic", sa.String(40), nullable=False),
        sa.Column("template_version", sa.String(60), nullable=False),
        sa.Column("action_kind", sa.String(16), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["enrollment_id", "organization_id"],
            ["enrollments.id", "enrollments.organization_id"],
            name="fk_participant_notice_enrollment_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_event_id", "organization_id"],
            ["domain_outbox.id", "domain_outbox.organization_id"],
            name="fk_participant_notice_event_scope",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "source_event_id", "recipient_user_id", "topic", name="uq_participant_notice_source"
        ),
        sa.CheckConstraint(
            "topic = 'enrollment_created' AND template_version = 'enrollment-created-v1' "
            "AND action_kind = 'schedule'",
            name="participant_notice_contract",
        ),
        sa.CheckConstraint(
            "expires_at > created_at AND expires_at <= created_at + interval '3650 days'",
            name="participant_notice_expiry",
        ),
        sa.CheckConstraint(
            "(read_at IS NULL AND version = 1) OR (read_at IS NOT NULL AND read_at >= created_at "
            "AND read_at < expires_at AND version = 2)",
            name="participant_notice_read_state",
        ),
    )
    op.create_index(
        "ix_participant_notice_owner",
        "participant_notices",
        ["organization_id", "recipient_user_id", "created_at", "id"],
    )
    op.create_index("ix_participant_notice_expiry", "participant_notices", ["expires_at", "id"])
    op.create_table(
        "participant_notice_preferences",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("topic", sa.String(40), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "organization_id", "user_id", "topic", name="uq_participant_notice_preference"
        ),
        sa.CheckConstraint(
            "topic = 'enrollment_created'", name="participant_notice_preference_topic"
        ),
        sa.CheckConstraint("version > 0", name="participant_notice_preference_version"),
    )
    op.execute("""
    CREATE FUNCTION participant_notice_scope_matches(target_org uuid, target_user uuid,
                                                      target_enrollment uuid)
    RETURNS boolean LANGUAGE sql STABLE AS $$
      SELECT EXISTS (
        SELECT 1 FROM users u
        JOIN participants p ON p.person_id=u.person_id AND p.organization_id=target_org
        JOIN enrollments e ON e.participant_id=p.id AND e.organization_id=p.organization_id
        JOIN applications a ON a.id=e.application_id AND a.organization_id=e.organization_id
        WHERE u.id=target_user AND u.status='active'
          AND p.status IN ('active','completed') AND e.status IN ('active','completed')
          AND a.person_id=p.person_id AND a.state='enrolled'
          AND (target_enrollment IS NULL OR e.id=target_enrollment)
          AND EXISTS (SELECT 1 FROM user_roles ur JOIN role_permissions rp ON rp.role_id=ur.role_id
                      WHERE ur.user_id=u.id AND ur.organization_id=target_org
                        AND rp.permission_code='participant.self')
      )
    $$;
    CREATE FUNCTION guard_participant_notice() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE source domain_outbox%ROWTYPE; enrollment enrollments%ROWTYPE;
    BEGIN
      IF TG_OP='DELETE' THEN
        IF OLD.expires_at > clock_timestamp() THEN
          RAISE EXCEPTION 'unexpired participant notice is retained';
        END IF;
        RETURN OLD;
      END IF;
      IF NOT participant_notice_scope_matches(NEW.organization_id,NEW.recipient_user_id,
                                              NEW.enrollment_id) THEN
        RAISE EXCEPTION 'participant notice recipient scope is unavailable';
      END IF;
      IF TG_OP='INSERT' THEN
        SELECT * INTO source FROM domain_outbox WHERE id=NEW.source_event_id;
        SELECT * INTO enrollment FROM enrollments WHERE id=NEW.enrollment_id;
        IF source.id IS NULL OR source.organization_id<>NEW.organization_id
          OR source.state NOT IN ('pending','retrying') OR source.event_type<>'enrollment.created'
          OR source.aggregate_type<>'enrollment' OR source.aggregate_id<>NEW.enrollment_id
          OR source.event_key<>'enrollment.created:'||NEW.enrollment_id::text
          OR source.payload::jsonb <> jsonb_build_object(
              'enrollment_id',NEW.enrollment_id::text,
              'application_id',enrollment.application_id::text,
              'participant_id',enrollment.participant_id::text)
          OR NEW.created_at<>source.created_at OR NEW.expires_at<=clock_timestamp()
          OR NEW.read_at IS NOT NULL OR NEW.version<>1
          OR EXISTS (SELECT 1 FROM participant_notice_preferences pref
                     WHERE pref.organization_id=NEW.organization_id
                       AND pref.user_id=NEW.recipient_user_id AND NOT pref.enabled) THEN
          RAISE EXCEPTION 'participant notice must match its typed source and preference';
        END IF;
      ELSE
        IF (NEW.id,NEW.organization_id,NEW.recipient_user_id,NEW.enrollment_id,NEW.source_event_id,
            NEW.topic,NEW.template_version,NEW.action_kind,NEW.created_at,NEW.expires_at)
          IS DISTINCT FROM
           (OLD.id,OLD.organization_id,OLD.recipient_user_id,OLD.enrollment_id,OLD.source_event_id,
            OLD.topic,OLD.template_version,OLD.action_kind,OLD.created_at,OLD.expires_at)
          OR OLD.read_at IS NOT NULL OR NEW.read_at IS NULL OR NEW.version<>OLD.version+1
          OR NEW.read_at>clock_timestamp() OR NEW.expires_at<=clock_timestamp() THEN
          RAISE EXCEPTION 'participant notice identity and read evidence are immutable';
        END IF;
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER trg_participant_notice BEFORE INSERT OR UPDATE OR DELETE ON participant_notices
      FOR EACH ROW EXECUTE FUNCTION guard_participant_notice();
    CREATE FUNCTION require_participant_notice_settlement() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      -- The immediate source guard proves that dispatch has an accepted notice;
      -- this deferred half prevents committing a notice without that dispatch.
      -- Expiry disposal in a later transaction leaves source evidence intact.
      IF EXISTS (SELECT 1 FROM participant_notices WHERE id=NEW.id)
        AND NOT EXISTS (SELECT 1 FROM domain_outbox source
          WHERE source.id=NEW.source_event_id AND source.organization_id=NEW.organization_id
            AND source.aggregate_id=NEW.enrollment_id AND source.state='dispatched'
            AND source.dispatched) THEN
        RAISE EXCEPTION 'participant notice and source dispatch must commit together';
      END IF;
      RETURN NULL;
    END $$;
    CREATE CONSTRAINT TRIGGER trg_participant_notice_settlement
      AFTER INSERT ON participant_notices DEFERRABLE INITIALLY DEFERRED
      FOR EACH ROW EXECUTE FUNCTION require_participant_notice_settlement();
    CREATE FUNCTION guard_participant_notice_preference() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP='DELETE' THEN
        RAISE EXCEPTION 'participant preference history is retained';
      END IF;
      IF NOT participant_notice_scope_matches(NEW.organization_id,NEW.user_id,NULL) THEN
        RAISE EXCEPTION 'participant preference requires current recipient scope';
      END IF;
      IF TG_OP='INSERT' THEN
        IF NEW.version<>1 THEN
          RAISE EXCEPTION 'participant preference begins at version one';
        END IF;
      ELSIF (NEW.id,NEW.organization_id,NEW.user_id,NEW.topic,NEW.created_at)
          IS DISTINCT FROM (OLD.id,OLD.organization_id,OLD.user_id,OLD.topic,OLD.created_at)
          OR NEW.version<>OLD.version+1 OR NEW.updated_at<OLD.updated_at THEN
        RAISE EXCEPTION 'participant preference identity and version are protected';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER trg_participant_notice_preference BEFORE INSERT OR UPDATE OR DELETE
      ON participant_notice_preferences
      FOR EACH ROW EXECUTE FUNCTION guard_participant_notice_preference();
    CREATE OR REPLACE FUNCTION protect_domain_outbox() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP='DELETE' THEN RAISE EXCEPTION 'domain outbox evidence is retained'; END IF;
      IF TG_OP='INSERT' THEN
        IF NEW.state<>'pending' OR NEW.version<>1 OR NEW.attempt_count<>0 THEN
          RAISE EXCEPTION 'domain outbox must begin pending';
        END IF;
        RETURN NEW;
      END IF;
      IF (NEW.id,NEW.event_key,NEW.event_type,NEW.aggregate_type,NEW.aggregate_id,
          NEW.organization_id,NEW.payload,NEW.created_at)
          IS DISTINCT FROM (OLD.id,OLD.event_key,OLD.event_type,OLD.aggregate_type,OLD.aggregate_id,
                            OLD.organization_id,OLD.payload,OLD.created_at)
          OR NEW.version<>OLD.version+1 OR OLD.state NOT IN ('pending','retrying')
          OR OLD.next_attempt_at>clock_timestamp() OR NEW.state='pending'
          OR NOT (NEW.attempt_count=OLD.attempt_count+1 OR
             (NEW.state='failed' AND NEW.error_code='retry_exhausted'
              AND NEW.attempt_count=OLD.attempt_count AND OLD.attempt_count>0)) THEN
        RAISE EXCEPTION 'domain outbox identity and bounded transition are protected';
      END IF;
      IF NEW.state='retrying' AND (NEW.next_attempt_at<=clock_timestamp()
          OR NEW.next_attempt_at>clock_timestamp()+interval '300 seconds') THEN
        RAISE EXCEPTION 'domain outbox retry requires bounded future work';
      END IF;
      IF NEW.state='dispatched' THEN
        IF NOT EXISTS (SELECT 1 FROM participant_notices n WHERE n.source_event_id=NEW.id
            AND n.organization_id=NEW.organization_id AND n.enrollment_id=NEW.aggregate_id) THEN
          RAISE EXCEPTION 'domain outbox dispatch requires an accepted participant notice';
        END IF;
      ELSIF EXISTS (SELECT 1 FROM participant_notices n WHERE n.source_event_id=NEW.id) THEN
        RAISE EXCEPTION 'participant notice and source must settle atomically';
      END IF;
      RETURN NEW;
    END $$;
    DROP TRIGGER trg_domain_outbox_immutable ON domain_outbox;
    CREATE TRIGGER trg_domain_outbox_immutable BEFORE INSERT OR UPDATE OR DELETE ON domain_outbox
      FOR EACH ROW EXECUTE FUNCTION protect_domain_outbox();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_participant_notice_settlement ON participant_notices")
    op.execute("DROP FUNCTION require_participant_notice_settlement()")
    op.execute("DROP TRIGGER trg_participant_notice ON participant_notices")
    op.execute("DROP FUNCTION guard_participant_notice()")
    op.execute("DROP TRIGGER trg_participant_notice_preference ON participant_notice_preferences")
    op.execute("DROP FUNCTION guard_participant_notice_preference()")
    op.execute("DROP FUNCTION participant_notice_scope_matches(uuid,uuid,uuid)")
    op.execute("DROP TRIGGER trg_domain_outbox_immutable ON domain_outbox")
    op.execute("""
      CREATE OR REPLACE FUNCTION protect_domain_outbox() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN
        IF TG_OP='DELETE' OR NEW.event_key<>OLD.event_key OR NEW.event_type<>OLD.event_type
          OR NEW.aggregate_type<>OLD.aggregate_type OR NEW.aggregate_id<>OLD.aggregate_id
          OR NEW.organization_id<>OLD.organization_id OR NEW.payload<>OLD.payload
          OR NEW.created_at<>OLD.created_at THEN
          RAISE EXCEPTION 'domain outbox evidence is immutable';
        END IF;
        RETURN NEW;
      END $$;
      CREATE TRIGGER trg_domain_outbox_immutable BEFORE UPDATE OR DELETE ON domain_outbox
        FOR EACH ROW EXECUTE FUNCTION protect_domain_outbox();
    """)
    op.drop_table("participant_notices")
    op.drop_table("participant_notice_preferences")
    op.drop_index("ix_domain_outbox_due", table_name="domain_outbox")
    op.drop_constraint("uq_domain_outbox_scope", "domain_outbox", type_="unique")
    for name in OUTBOX_CHECKS:
        op.drop_constraint(name, "domain_outbox", type_="check")
    for name in (
        "settled_at",
        "next_attempt_at",
        "attempt_count",
        "version",
        "error_code",
        "state",
    ):
        op.drop_column("domain_outbox", name)
