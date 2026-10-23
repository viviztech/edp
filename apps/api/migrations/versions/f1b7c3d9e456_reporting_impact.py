"""reporting_impact"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f1b7c3d9e456"
down_revision = "e0a6b2c8d345"
branch_labels = None
depends_on = None


def install_guards() -> None:
    op.execute("""
        CREATE FUNCTION report_evidence_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'report and impact evidence is append-only'; END $$;
        CREATE TRIGGER impact_history_immutable BEFORE UPDATE OR DELETE ON impact_definition_history
          FOR EACH ROW EXECUTE FUNCTION report_evidence_immutable();
        CREATE TRIGGER impact_records_immutable BEFORE UPDATE OR DELETE ON impact_records
          FOR EACH ROW EXECUTE FUNCTION report_evidence_immutable();
        CREATE TRIGGER impact_snapshot_immutable BEFORE UPDATE OR DELETE ON cohort_impact_snapshots
          FOR EACH ROW EXECUTE FUNCTION report_evidence_immutable();
        CREATE TRIGGER report_export_immutable BEFORE UPDATE OR DELETE ON report_exports
          FOR EACH ROW EXECUTE FUNCTION report_evidence_immutable();
        CREATE TRIGGER report_capability_immutable BEFORE UPDATE OR DELETE
          ON report_export_capabilities
          FOR EACH ROW EXECUTE FUNCTION report_evidence_immutable();

        CREATE FUNCTION impact_definition_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE latest_edition integer;
        BEGIN
          IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'impact definitions cannot be deleted'; END IF;
          IF TG_OP = 'INSERT' THEN
            PERFORM id FROM organizations WHERE id = NEW.organization_id FOR UPDATE;
            SELECT COALESCE(MAX(edition),0) INTO latest_edition FROM impact_definitions
              WHERE organization_id = NEW.organization_id;
            IF NEW.state <> 'draft' OR NEW.version <> 1 OR NEW.published_at IS NOT NULL
               OR NEW.edition <> latest_edition + 1 THEN
              RAISE EXCEPTION 'impact definitions require sequential draft editions'; END IF;
          ELSE
            IF (to_jsonb(NEW) - ARRAY['state','version','published_at']) IS DISTINCT FROM
               (to_jsonb(OLD) - ARRAY['state','version','published_at']) THEN
              RAISE EXCEPTION 'impact measurement content is immutable'; END IF;
            IF NEW.version <> OLD.version + 1 OR NOT (
                 (OLD.state = 'draft' AND NEW.state IN ('published','archived')) OR
                 (OLD.state = 'published' AND NEW.state = 'archived')) THEN
              RAISE EXCEPTION 'invalid impact definition lifecycle'; END IF;
            IF OLD.state = 'published' AND NEW.published_at IS DISTINCT FROM OLD.published_at THEN
              RAISE EXCEPTION 'impact publication time is immutable'; END IF;
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER impact_definition_evidence BEFORE INSERT OR UPDATE OR DELETE
          ON impact_definitions
          FOR EACH ROW EXECUTE FUNCTION impact_definition_guard();

        CREATE FUNCTION impact_definition_history_required() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM impact_definition_history h
              WHERE h.definition_id = NEW.id AND h.organization_id = NEW.organization_id
                AND h.version = NEW.version AND h.state = NEW.state) THEN
            RAISE EXCEPTION 'impact definition change requires decision evidence'; END IF;
          RETURN NULL;
        END $$;
        CREATE CONSTRAINT TRIGGER impact_definition_history_required
          AFTER INSERT OR UPDATE ON impact_definitions DEFERRABLE INITIALLY DEFERRED
          FOR EACH ROW EXECUTE FUNCTION impact_definition_history_required();

        CREATE FUNCTION impact_record_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE previous impact_records%ROWTYPE; source_state text;
        BEGIN
          PERFORM id FROM enrollments WHERE id = NEW.enrollment_id FOR UPDATE;
          IF NOT EXISTS (SELECT 1 FROM enrollments e JOIN participants p ON p.id = e.participant_id
              JOIN users u ON u.person_id = p.person_id
              WHERE e.id = NEW.enrollment_id AND e.organization_id = NEW.organization_id
                AND p.id = NEW.participant_id AND p.organization_id = NEW.organization_id
                AND u.id = NEW.actor_user_id AND u.status = 'active'
                AND p.status IN ('active','completed') AND e.status IN ('active','completed')
                AND EXISTS (SELECT 1 FROM user_roles ur
                  JOIN role_permissions rp ON rp.role_id = ur.role_id
                  WHERE ur.user_id = u.id AND ur.organization_id = NEW.organization_id
                    AND rp.permission_code = 'participant.self')) THEN
            RAISE EXCEPTION 'impact evidence requires an eligible owned enrollment'; END IF;
          IF NEW.observed_on > (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')::date THEN
            RAISE EXCEPTION 'future impact observations are invalid'; END IF;
          SELECT * INTO previous FROM impact_records WHERE enrollment_id = NEW.enrollment_id
            AND stage = NEW.stage AND observed_on = NEW.observed_on ORDER BY revision DESC LIMIT 1;
          IF NEW.revision <> COALESCE(previous.revision,0) + 1 THEN
            RAISE EXCEPTION 'impact evidence requires sequential revisions'; END IF;
          IF previous.id IS NOT NULL AND NEW.definition_id <> previous.definition_id THEN
            RAISE EXCEPTION 'impact measurement edition is pinned'; END IF;
          SELECT state INTO source_state FROM impact_definitions WHERE id = NEW.definition_id
            AND organization_id = NEW.organization_id FOR SHARE;
          IF source_state IS NULL OR (source_state <> 'published' AND NOT (
              previous.id IS NOT NULL AND source_state = 'archived')) THEN
            RAISE EXCEPTION 'impact evidence requires published measurement edition'; END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER impact_record_scope BEFORE INSERT ON impact_records
          FOR EACH ROW EXECUTE FUNCTION impact_record_guard();

        CREATE FUNCTION report_capability_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE job_expiry timestamptz;
        BEGIN
          SELECT expires_at INTO job_expiry FROM report_exports WHERE id = NEW.export_id
            AND organization_id = NEW.organization_id AND requester_user_id = NEW.requester_user_id;
          IF job_expiry IS NULL OR NEW.expires_at > job_expiry OR
             NEW.expires_at > NEW.created_at + interval '5 minutes' OR
             NEW.token_hash !~ '^[0-9a-f]{64}$' THEN
            RAISE EXCEPTION 'invalid report export capability'; END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER report_capability_scope BEFORE INSERT ON report_export_capabilities
          FOR EACH ROW EXECUTE FUNCTION report_capability_guard();

        INSERT INTO permissions(code) VALUES ('report.view'), ('report.export'), ('impact.manage')
          ON CONFLICT DO NOTHING;
        INSERT INTO role_permissions(role_id, permission_code)
          SELECT id, permission FROM roles CROSS JOIN
            (VALUES ('report.view'),('report.export'),('impact.manage')) AS grants(permission)
          WHERE name IN ('Super Admin','Program Director') ON CONFLICT DO NOTHING;
        INSERT INTO role_permissions(role_id, permission_code)
          SELECT id, permission FROM roles CROSS JOIN
            (VALUES ('report.view'),('impact.manage')) AS grants(permission)
          WHERE name = 'Program Manager' ON CONFLICT DO NOTHING;
    """)


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "impact_definitions",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("edition", sa.Integer(), nullable=False),
        sa.Column("title_en", sa.String(length=200), nullable=False),
        sa.Column("title_ta", sa.String(length=200), nullable=False),
        sa.Column("definition_en", sa.Text(), nullable=False),
        sa.Column("definition_ta", sa.Text(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(state = 'draft' AND published_at IS NULL) OR "
            "(state = 'published' AND published_at IS NOT NULL) OR state = 'archived'",
            name="impact_definition_publication",
        ),
        sa.CheckConstraint(
            "state IN ('draft','published','archived')", name="impact_definition_state"
        ),
        sa.CheckConstraint("edition > 0 AND version > 0", name="impact_definition_numbers"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id"),
        sa.UniqueConstraint("organization_id", "edition"),
    )
    op.create_index(
        "ix_impact_definition_scope",
        "impact_definitions",
        ["organization_id", "state", "id"],
        unique=False,
    )
    op.create_table(
        "cohort_impact_snapshots",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("requester_user_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("request_digest", sa.String(length=64), nullable=False),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("dictionary_version", sa.String(length=40), nullable=False),
        sa.Column("definition_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("dashboard", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "octet_length(dashboard::text) <= 1048576", name="impact_snapshot_bytes"
        ),
        sa.CheckConstraint(
            "dashboard->'filters' = filters "
            "AND dashboard->>'dictionary_version' = dictionary_version",
            name="impact_snapshot_consistency",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requester_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id"),
        sa.UniqueConstraint("organization_id", "requester_user_id", "request_id"),
    )
    op.create_index(
        "ix_impact_snapshot_scope",
        "cohort_impact_snapshots",
        ["organization_id", "id"],
        unique=False,
    )
    op.create_table(
        "impact_definition_history",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("definition_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("version > 0", name="impact_definition_history_version"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["definition_id", "organization_id"],
            ["impact_definitions.id", "impact_definitions.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("definition_id", "version"),
    )
    op.create_table(
        "report_exports",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("requester_user_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("request_digest", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("csv_content", sa.Text(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("byte_count", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "byte_count BETWEEN 1 AND 262144 AND octet_length(csv_content) = byte_count",
            name="report_export_bytes",
        ),
        sa.CheckConstraint("expires_at > created_at", name="report_export_expiry"),
        sa.CheckConstraint("row_count BETWEEN 1 AND 500", name="report_export_rows"),
        sa.ForeignKeyConstraint(["requester_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["snapshot_id", "organization_id"],
            ["cohort_impact_snapshots.id", "cohort_impact_snapshots.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id", "requester_user_id"),
        sa.UniqueConstraint("organization_id", "requester_user_id", "request_id"),
    )
    op.create_index(
        "ix_report_export_owner",
        "report_exports",
        ["organization_id", "requester_user_id", "id"],
        unique=False,
    )
    op.create_table(
        "report_export_capabilities",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("export_id", sa.Uuid(), nullable=False),
        sa.Column("requester_user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("expires_at > created_at", name="report_capability_expiry"),
        sa.ForeignKeyConstraint(
            ["export_id", "organization_id", "requester_user_id"],
            [
                "report_exports.id",
                "report_exports.organization_id",
                "report_exports.requester_user_id",
            ],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "ix_report_capability_job",
        "report_export_capabilities",
        ["organization_id", "export_id", "requester_user_id"],
        unique=False,
    )
    op.create_table(
        "impact_records",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("definition_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("stage", sa.String(length=16), nullable=False),
        sa.Column("observed_on", sa.Date(), nullable=False),
        sa.Column("business_started", sa.Boolean(), nullable=False),
        sa.Column("business_active", sa.Boolean(), nullable=False),
        sa.Column("jobs_created", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("request_digest", sa.String(length=64), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("stage IN ('baseline','outcome')", name="impact_record_stage"),
        sa.CheckConstraint("NOT business_active OR business_started", name="impact_record_active"),
        sa.CheckConstraint("jobs_created BETWEEN 0 AND 100000", name="impact_record_jobs"),
        sa.CheckConstraint("revision > 0", name="impact_record_revision"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["definition_id", "organization_id"],
            ["impact_definitions.id", "impact_definitions.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id", "organization_id"],
            ["enrollments.id", "enrollments.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["participant_id", "organization_id"],
            ["participants.id", "participants.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("enrollment_id", "stage", "observed_on", "revision"),
        sa.UniqueConstraint("organization_id", "actor_user_id", "request_id"),
    )
    op.create_index(
        "ix_impact_record_latest",
        "impact_records",
        ["organization_id", "enrollment_id", "stage", "observed_on", "revision"],
        unique=False,
    )
    op.create_index(
        "ix_impact_record_owner",
        "impact_records",
        ["organization_id", "participant_id", "id"],
        unique=False,
    )
    # ### end Alembic commands ###
    install_guards()


def downgrade() -> None:
    op.execute("""
        DELETE FROM role_permissions WHERE permission_code IN
          ('report.view','report.export','impact.manage');
        DELETE FROM permissions WHERE code IN ('report.view','report.export','impact.manage');
    """)
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index("ix_impact_record_owner", table_name="impact_records")
    op.drop_index("ix_impact_record_latest", table_name="impact_records")
    op.drop_table("impact_records")
    op.drop_index("ix_report_capability_job", table_name="report_export_capabilities")
    op.drop_table("report_export_capabilities")
    op.drop_index("ix_report_export_owner", table_name="report_exports")
    op.drop_table("report_exports")
    op.drop_table("impact_definition_history")
    op.drop_index("ix_impact_snapshot_scope", table_name="cohort_impact_snapshots")
    op.drop_table("cohort_impact_snapshots")
    op.drop_index("ix_impact_definition_scope", table_name="impact_definitions")
    op.drop_table("impact_definitions")
    op.execute("""
        DROP FUNCTION report_capability_guard();
        DROP FUNCTION impact_record_guard();
        DROP FUNCTION impact_definition_history_required();
        DROP FUNCTION impact_definition_guard();
        DROP FUNCTION report_evidence_immutable();
    """)
    # ### end Alembic commands ###
