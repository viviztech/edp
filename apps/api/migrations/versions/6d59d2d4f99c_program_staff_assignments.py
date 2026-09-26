"""Scoped program staff assignments."""

# ruff: noqa: E501

import sqlalchemy as sa
from alembic import op

revision = "6d59d2d4f99c"
down_revision = "5c48c1c3e88b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "INSERT INTO permissions (code) VALUES ('staff.assignment.manage') ON CONFLICT DO NOTHING"
    )
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_code)
        SELECT roles.id, permissions.code FROM roles CROSS JOIN permissions
        WHERE roles.name IN ('Super Admin', 'Program Director', 'Program Manager')
          AND permissions.code = 'staff.assignment.manage'
        ON CONFLICT DO NOTHING
    """)
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_code)
        SELECT roles.id, permissions.code FROM roles CROSS JOIN permissions
        WHERE roles.name = 'Training Center Coordinator'
          AND permissions.code IN ('cohort.manage','participant.view','participant.update','schedule.manage')
        ON CONFLICT DO NOTHING
    """)
    op.create_unique_constraint(
        "uq_cohort_center_scope",
        "cohorts",
        ["id", "center_id", "organization_id"],
    )
    op.create_table(
        "program_staff_assignments",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("center_id", sa.Uuid(), nullable=False),
        sa.Column("cohort_id", sa.Uuid(), nullable=True),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(state = 'active' AND revoked_at IS NULL) OR "
            "(state = 'revoked' AND revoked_at IS NOT NULL)",
            name="program_staff_revocation_evidence",
        ),
        sa.CheckConstraint("state IN ('active','revoked')", name="program_staff_state"),
        sa.CheckConstraint("version > 0", name="program_staff_version"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["center_id", "organization_id"],
            ["training_centers.id", "training_centers.organization_id"],
            name="fk_program_staff_center_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["cohort_id", "center_id", "organization_id"],
            ["cohorts.id", "cohorts.center_id", "cohorts.organization_id"],
            name="fk_program_staff_cohort_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id"),
    )
    op.create_index(
        op.f("ix_program_staff_assignments_organization_id"),
        "program_staff_assignments",
        ["organization_id"],
    )
    op.create_index(
        op.f("ix_program_staff_assignments_user_id"),
        "program_staff_assignments",
        ["user_id"],
    )
    op.create_index(
        op.f("ix_program_staff_assignments_center_id"),
        "program_staff_assignments",
        ["center_id"],
    )
    op.create_index(
        op.f("ix_program_staff_assignments_cohort_id"),
        "program_staff_assignments",
        ["cohort_id"],
    )
    op.create_index(
        "ix_program_staff_scope",
        "program_staff_assignments",
        ["organization_id", "center_id", "cohort_id", "state"],
    )
    op.create_index(
        "uq_program_staff_active_center",
        "program_staff_assignments",
        ["organization_id", "user_id", "center_id"],
        unique=True,
        postgresql_where=sa.text("cohort_id IS NULL AND state = 'active'"),
    )
    op.create_index(
        "uq_program_staff_active_cohort",
        "program_staff_assignments",
        ["organization_id", "user_id", "cohort_id"],
        unique=True,
        postgresql_where=sa.text("cohort_id IS NOT NULL AND state = 'active'"),
    )
    op.execute("""
        CREATE FUNCTION protect_program_staff_assignment() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'program staff assignment is immutable';
          END IF;
          IF NOT (
            OLD.state = 'active' AND NEW.state = 'revoked'
            AND NEW.version = OLD.version + 1
            AND NEW.revoked_at IS NOT NULL
            AND NEW.id = OLD.id
            AND NEW.organization_id = OLD.organization_id
            AND NEW.user_id = OLD.user_id
            AND NEW.center_id = OLD.center_id
            AND NEW.cohort_id IS NOT DISTINCT FROM OLD.cohort_id
            AND NEW.created_at = OLD.created_at
          ) THEN
            RAISE EXCEPTION 'program staff assignment evidence is immutable';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_program_staff_assignment_immutable
        BEFORE UPDATE OR DELETE ON program_staff_assignments
        FOR EACH ROW EXECUTE FUNCTION protect_program_staff_assignment();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_program_staff_assignment_immutable ON program_staff_assignments")
    op.execute("DROP FUNCTION protect_program_staff_assignment")
    op.drop_index("uq_program_staff_active_cohort", table_name="program_staff_assignments")
    op.drop_index("uq_program_staff_active_center", table_name="program_staff_assignments")
    op.drop_index("ix_program_staff_scope", table_name="program_staff_assignments")
    op.drop_index(
        op.f("ix_program_staff_assignments_cohort_id"),
        table_name="program_staff_assignments",
    )
    op.drop_index(
        op.f("ix_program_staff_assignments_center_id"),
        table_name="program_staff_assignments",
    )
    op.drop_index(
        op.f("ix_program_staff_assignments_user_id"),
        table_name="program_staff_assignments",
    )
    op.drop_index(
        op.f("ix_program_staff_assignments_organization_id"),
        table_name="program_staff_assignments",
    )
    op.drop_table("program_staff_assignments")
    op.drop_constraint("uq_cohort_center_scope", "cohorts", type_="unique")
    op.execute("""
        DELETE FROM role_permissions
        USING roles
        WHERE role_permissions.role_id = roles.id
          AND roles.name = 'Training Center Coordinator'
          AND role_permissions.permission_code IN (
            'cohort.manage','participant.view','participant.update','schedule.manage'
          )
    """)
    op.execute("DELETE FROM role_permissions WHERE permission_code = 'staff.assignment.manage'")
    op.execute("DELETE FROM permissions WHERE code = 'staff.assignment.manage'")
