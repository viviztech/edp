"""attendance policy, records, corrections and QR windows

Revision ID: e5d1a7b9c234
Revises: d4c0f6a8b123
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e5d1a7b9c234"
down_revision: str | None = "d4c0f6a8b123"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for code in ("attendance.view", "attendance.manage"):
        op.execute(
            sa.text(
                "INSERT INTO permissions (code) VALUES (:code) ON CONFLICT DO NOTHING"
            ).bindparams(code=code)
        )
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_code)
        SELECT roles.id, permissions.code
        FROM roles CROSS JOIN permissions
        WHERE roles.name IN (
          'Super Admin','Program Director','Program Manager','Trainer',
          'Training Center Coordinator'
        )
          AND permissions.code IN ('attendance.view','attendance.manage')
        ON CONFLICT DO NOTHING
    """)

    op.create_table(
        "attendance_policies",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cohort_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("threshold_percent", sa.Integer(), nullable=False),
        sa.Column("late_after_minutes", sa.Integer(), nullable=False),
        sa.Column("opens_before_minutes", sa.Integer(), nullable=False),
        sa.Column("closes_after_minutes", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("threshold_percent BETWEEN 1 AND 100", name="attendance_threshold"),
        sa.CheckConstraint("late_after_minutes BETWEEN 0 AND 240", name="attendance_late_after"),
        sa.CheckConstraint(
            "opens_before_minutes BETWEEN 0 AND 1440", name="attendance_opens_before"
        ),
        sa.CheckConstraint(
            "closes_after_minutes BETWEEN 0 AND 1440", name="attendance_closes_after"
        ),
        sa.CheckConstraint("version > 0", name="attendance_policy_version"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["cohort_id", "organization_id"],
            ["cohorts.id", "cohorts.organization_id"],
            name="fk_attendance_policy_cohort_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cohort_id"),
        sa.UniqueConstraint("id", "organization_id"),
    )
    op.create_index(
        "ix_attendance_policies_organization_id", "attendance_policies", ["organization_id"]
    )
    op.create_index("ix_attendance_policies_cohort_id", "attendance_policies", ["cohort_id"])

    op.create_table(
        "attendance_windows",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_digest", sa.String(length=64), nullable=False),
        sa.Column("opens_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closes_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("closes_at > opens_at", name="attendance_window_range"),
        sa.CheckConstraint("state IN ('active','closed')", name="attendance_window_state"),
        sa.CheckConstraint("version > 0", name="attendance_window_version"),
        sa.CheckConstraint(
            "(state = 'active' AND closed_at IS NULL) OR "
            "(state = 'closed' AND closed_at IS NOT NULL)",
            name="attendance_window_close_evidence",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["session_id", "organization_id"],
            ["program_sessions.id", "program_sessions.organization_id"],
            name="fk_attendance_window_session_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_digest"),
        sa.UniqueConstraint("id", "organization_id"),
    )
    op.create_index(
        "ix_attendance_windows_organization_id", "attendance_windows", ["organization_id"]
    )
    op.create_index("ix_attendance_windows_session_id", "attendance_windows", ["session_id"])
    op.create_index(
        "ix_attendance_window_time", "attendance_windows", ["session_id", "opens_at", "closes_at"]
    )
    op.create_index(
        "uq_attendance_window_active_session",
        "attendance_windows",
        ["session_id"],
        unique=True,
        postgresql_where=sa.text("state = 'active'"),
    )

    op.create_table(
        "attendance_records",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enrollment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("marked_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("marked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('present','absent','late','excused')", name="attendance_record_status"
        ),
        sa.CheckConstraint("source IN ('manual','qr')", name="attendance_record_source"),
        sa.CheckConstraint("version > 0", name="attendance_record_version"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["marked_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["session_id", "organization_id"],
            ["program_sessions.id", "program_sessions.organization_id"],
            name="fk_attendance_record_session_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id", "organization_id"],
            ["enrollments.id", "enrollments.organization_id"],
            name="fk_attendance_record_enrollment_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "enrollment_id"),
        sa.UniqueConstraint("id", "organization_id"),
    )
    op.create_index(
        "ix_attendance_records_organization_id", "attendance_records", ["organization_id"]
    )
    op.create_index("ix_attendance_records_session_id", "attendance_records", ["session_id"])
    op.create_index("ix_attendance_records_enrollment_id", "attendance_records", ["enrollment_id"])
    op.create_index(
        "ix_attendance_record_enrollment_time",
        "attendance_records",
        ["enrollment_id", "created_at", "id"],
    )

    op.create_table(
        "attendance_corrections",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attendance_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_status", sa.String(length=16), nullable=False),
        sa.Column("to_status", sa.String(length=16), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "from_status IN ('present','absent','late','excused')",
            name="attendance_correction_from_status",
        ),
        sa.CheckConstraint(
            "to_status IN ('present','absent','late','excused')",
            name="attendance_correction_to_status",
        ),
        sa.CheckConstraint("from_status <> to_status", name="attendance_correction_changed"),
        sa.CheckConstraint("record_version > 1", name="attendance_correction_version"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["attendance_record_id", "organization_id"],
            ["attendance_records.id", "attendance_records.organization_id"],
            name="fk_attendance_correction_record_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("attendance_record_id", "record_version"),
    )
    op.create_index(
        "ix_attendance_corrections_organization_id", "attendance_corrections", ["organization_id"]
    )
    op.create_index(
        "ix_attendance_corrections_attendance_record_id",
        "attendance_corrections",
        ["attendance_record_id"],
    )

    op.execute("""
        CREATE FUNCTION protect_attendance_correction() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
          RAISE EXCEPTION 'attendance correction evidence is append-only';
        END $$;
        CREATE TRIGGER trg_attendance_correction_append_only
        BEFORE UPDATE OR DELETE ON attendance_corrections
        FOR EACH ROW EXECUTE FUNCTION protect_attendance_correction();

        CREATE FUNCTION protect_attendance_record() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
          IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'attendance evidence cannot be deleted';
          END IF;
          IF NEW.organization_id <> OLD.organization_id
             OR NEW.session_id <> OLD.session_id
             OR NEW.enrollment_id <> OLD.enrollment_id
             OR NEW.source <> OLD.source
             OR NEW.created_at <> OLD.created_at
             OR NEW.version <> OLD.version + 1
             OR NEW.status = OLD.status THEN
            RAISE EXCEPTION 'invalid attendance correction';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_attendance_record_protect
        BEFORE UPDATE OR DELETE ON attendance_records
        FOR EACH ROW EXECUTE FUNCTION protect_attendance_record();
    """)


def downgrade() -> None:
    op.execute("""
        DROP TRIGGER trg_attendance_record_protect ON attendance_records;
        DROP FUNCTION protect_attendance_record;
        DROP TRIGGER trg_attendance_correction_append_only ON attendance_corrections;
        DROP FUNCTION protect_attendance_correction;
    """)
    op.drop_table("attendance_corrections")
    op.drop_table("attendance_records")
    op.drop_table("attendance_windows")
    op.drop_table("attendance_policies")
    op.execute("""
        DELETE FROM role_permissions
        WHERE permission_code IN ('attendance.view','attendance.manage');
        DELETE FROM permissions
        WHERE code IN ('attendance.view','attendance.manage');
    """)
