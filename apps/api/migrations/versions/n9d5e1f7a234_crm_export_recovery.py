"""Fence CRM export execution and retain durable recovery state."""

import sqlalchemy as sa
from alembic import op

revision = "n9d5e1f7a234"
down_revision = "m8c4d0e6f123"
branch_labels = None
depends_on = None

CHECKS = {
    "crm_export_version": "version > 0 AND attempt_count BETWEEN 0 AND 10",
    "crm_export_row_count": "row_count BETWEEN 0 AND 10000",
    "crm_export_byte_count": (
        "csv_content IS NULL OR (legacy_output AND status = 'completed') "
        "OR octet_length(csv_content) BETWEEN 1 AND 20971520"
    ),
    "crm_export_lease_state": (
        "(status = 'running' AND lease_token_digest IS NOT NULL "
        "AND lease_token_digest ~ '^[0-9a-f]{64}$' AND lease_until IS NOT NULL "
        "AND next_attempt_at IS NULL AND completed_at IS NULL) OR "
        "(status <> 'running' AND lease_token_digest IS NULL AND lease_until IS NULL)"
    ),
    "crm_export_completion_state": (
        "(status = 'queued' AND next_attempt_at IS NOT NULL AND completed_at IS NULL) OR "
        "(status IN ('completed','failed') AND next_attempt_at IS NULL "
        "AND completed_at IS NOT NULL) OR (status = 'running' AND next_attempt_at IS NULL)"
    ),
    "crm_export_error_code": (
        "error_code IN ('','generation_failed','queue_unavailable','recovered_lease',"
        "'retry_exhausted','request_expired','requester_unavailable','row_limit_exceeded',"
        "'output_too_large','expired') AND (status <> 'failed' OR error_code <> '')"
    ),
    "crm_export_disposal_state": (
        "disposed_at IS NULL OR (status = 'failed' AND error_code = 'expired' "
        "AND csv_content IS NULL AND disposed_at >= expires_at)"
    ),
}


def upgrade() -> None:
    op.add_column(
        "crm_export_jobs", sa.Column("version", sa.Integer(), nullable=False, server_default="1")
    )
    op.add_column(
        "crm_export_jobs",
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("crm_export_jobs", sa.Column("lease_token_digest", sa.String(64), nullable=True))
    for name in ("lease_until", "next_attempt_at", "disposed_at"):
        op.add_column("crm_export_jobs", sa.Column(name, sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "crm_export_jobs",
        sa.Column("legacy_output", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # Old running rows have no owner that can safely complete under the new fence.
    # Their synthetic, already expired lease is settled through ordinary recovery.
    op.execute("""
        UPDATE crm_export_jobs SET
          legacy_output = (status = 'completed' AND octet_length(csv_content) > 20971520),
          attempt_count = CASE WHEN status = 'queued' THEN 0 ELSE 1 END,
          next_attempt_at = CASE WHEN status = 'queued' THEN created_at ELSE NULL END,
          lease_token_digest = CASE WHEN status = 'running' THEN repeat('0',64) ELSE NULL END,
          lease_until = CASE WHEN status = 'running'
            THEN LEAST(created_at,clock_timestamp() - interval '1 second') ELSE NULL END,
          completed_at = CASE WHEN status IN ('completed','failed')
            THEN COALESCE(completed_at,created_at) ELSE NULL END,
          row_count = CASE WHEN status = 'completed' THEN row_count ELSE 0 END,
          error_code = CASE WHEN status = 'failed'
            THEN CASE WHEN error_code IN ('generation_failed','queue_unavailable','expired')
              THEN error_code ELSE 'generation_failed' END ELSE '' END
    """)
    for name, expression in CHECKS.items():
        op.create_check_constraint(name, "crm_export_jobs", expression)
    op.create_index("ix_crm_export_due", "crm_export_jobs", ["status", "next_attempt_at", "id"])
    op.create_index("ix_crm_export_lease", "crm_export_jobs", ["status", "lease_until", "id"])
    op.alter_column("crm_export_jobs", "version", server_default=None)
    op.alter_column("crm_export_jobs", "attempt_count", server_default=None)
    op.alter_column("crm_export_jobs", "legacy_output", server_default=None)
    op.execute("""
    CREATE FUNCTION guard_crm_export_job() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'export job metadata is retained';
      END IF;
      IF TG_OP = 'INSERT' THEN
        IF NEW.status <> 'queued' OR NEW.version <> 1 OR NEW.attempt_count <> 0
            OR NEW.row_count <> 0 OR NEW.error_code <> '' OR NEW.disposed_at IS NOT NULL
            OR NEW.legacy_output THEN
          RAISE EXCEPTION 'export job must begin queued';
        END IF;
        RETURN NEW;
      END IF;
      IF (NEW.id,NEW.organization_id,NEW.requested_by_id,NEW.created_at,
          NEW.expires_at,NEW.legacy_output)
          IS DISTINCT FROM
          (OLD.id,OLD.organization_id,OLD.requested_by_id,OLD.created_at,
          OLD.expires_at,OLD.legacy_output)
          OR NEW.version <> OLD.version + 1 THEN
        RAISE EXCEPTION 'export job identity and version are protected';
      END IF;
      IF OLD.status = 'completed' THEN
        IF NEW.status <> 'failed' OR NEW.error_code <> 'expired'
            OR NEW.disposed_at IS NULL OR NEW.disposed_at < OLD.expires_at
            OR OLD.expires_at > clock_timestamp() OR NEW.csv_content IS NOT NULL
            OR NEW.completed_at IS DISTINCT FROM OLD.completed_at
            OR NEW.attempt_count <> OLD.attempt_count OR NEW.row_count <> OLD.row_count THEN
          RAISE EXCEPTION 'completed export only permits expired output disposal';
        END IF;
        RETURN NEW;
      END IF;
      IF OLD.status = 'failed' OR NEW.disposed_at IS NOT NULL THEN
        RAISE EXCEPTION 'terminal export is immutable';
      END IF;
      IF OLD.status = 'queued' AND NEW.status = 'running' THEN
        IF NEW.attempt_count <> OLD.attempt_count + 1
            OR OLD.next_attempt_at > clock_timestamp() OR OLD.expires_at <= clock_timestamp()
            OR NEW.lease_until <= clock_timestamp()
            OR NEW.lease_until > clock_timestamp() + interval '900 seconds' OR NEW.error_code <> ''
            OR NEW.row_count <> 0 THEN
          RAISE EXCEPTION 'export claim requires current due work';
        END IF;
      ELSIF OLD.status = 'running' AND NEW.status IN ('queued','completed','failed') THEN
        IF NEW.attempt_count <> OLD.attempt_count THEN
          RAISE EXCEPTION 'export settlement cannot change attempt';
        END IF;
        IF NEW.status = 'completed' AND (OLD.lease_until <= clock_timestamp()
            OR OLD.expires_at <= clock_timestamp() OR NEW.error_code <> '') THEN
          RAISE EXCEPTION 'export completion requires unexpired lease and access';
        END IF;
        IF NEW.status = 'queued' AND (NEW.next_attempt_at <= clock_timestamp()
            OR NEW.row_count <> 0
            OR NEW.error_code NOT IN ('generation_failed','recovered_lease')
            OR (NEW.error_code = 'recovered_lease' AND OLD.lease_until > clock_timestamp())
            OR (NEW.error_code = 'generation_failed' AND OLD.lease_until <= clock_timestamp())) THEN
          RAISE EXCEPTION 'export retry requires bounded future work';
        END IF;
      ELSIF OLD.status = 'queued' AND NEW.status = 'failed' THEN
        IF NEW.attempt_count <> OLD.attempt_count THEN
          RAISE EXCEPTION 'export failure cannot change attempt';
        END IF;
      ELSE
        RAISE EXCEPTION 'invalid export job transition';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER trg_crm_export_job BEFORE INSERT OR UPDATE OR DELETE ON crm_export_jobs
      FOR EACH ROW EXECUTE FUNCTION guard_crm_export_job();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_crm_export_job ON crm_export_jobs")
    op.execute("DROP FUNCTION guard_crm_export_job()")
    op.drop_index("ix_crm_export_lease", table_name="crm_export_jobs")
    op.drop_index("ix_crm_export_due", table_name="crm_export_jobs")
    for name in CHECKS:
        op.drop_constraint(name, "crm_export_jobs", type_="check")
    # Also supports rolling back the locally tested pre-review draft of this
    # uncheckpointed revision, which did not yet include the legacy marker.
    op.execute("ALTER TABLE crm_export_jobs DROP COLUMN IF EXISTS legacy_output")
    for name in (
        "disposed_at",
        "next_attempt_at",
        "lease_until",
        "lease_token_digest",
        "attempt_count",
        "version",
    ):
        op.drop_column("crm_export_jobs", name)
