"""Add organization-scoped program delivery foundation."""

import sqlalchemy as sa
from alembic import op

revision = "d5a6b7c8d9e0"
down_revision = "c4f5a6b7c8d9"
branch_labels = None
depends_on = None


def record_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_application_form_scope", "application_forms", ["id", "organization_id"]
    )
    op.create_table(
        "programs",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(60), nullable=False),
        sa.Column("name_en", sa.String(160), nullable=False),
        sa.Column("name_ta", sa.String(160), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        *record_columns(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "code"),
        sa.UniqueConstraint("id", "organization_id"),
        sa.CheckConstraint("state IN ('draft','active','archived')", name="program_state"),
        sa.CheckConstraint("version > 0", name="program_version"),
    )
    op.create_index("ix_programs_organization_id", "programs", ["organization_id"])
    op.create_index("ix_program_scope_state", "programs", ["organization_id", "state", "id"])
    op.create_table(
        "training_centers",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(60), nullable=False),
        sa.Column("name_en", sa.String(160), nullable=False),
        sa.Column("name_ta", sa.String(160), nullable=False),
        sa.Column("locality", sa.String(160), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        *record_columns(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "code"),
        sa.UniqueConstraint("id", "organization_id"),
        sa.CheckConstraint("state IN ('active','inactive')", name="training_center_state"),
        sa.CheckConstraint("version > 0", name="training_center_version"),
    )
    op.create_index("ix_training_centers_organization_id", "training_centers", ["organization_id"])
    op.create_index(
        "ix_training_center_scope_state", "training_centers", ["organization_id", "state", "id"]
    )
    op.create_table(
        "cohorts",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("program_id", sa.Uuid(), nullable=False),
        sa.Column("center_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(60), nullable=False),
        sa.Column("name_en", sa.String(160), nullable=False),
        sa.Column("name_ta", sa.String(160), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        *record_columns(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["program_id", "organization_id"],
            ["programs.id", "programs.organization_id"],
            name="fk_cohort_program_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["center_id", "organization_id"],
            ["training_centers.id", "training_centers.organization_id"],
            name="fk_cohort_center_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "code"),
        sa.UniqueConstraint("id", "organization_id"),
        sa.UniqueConstraint("id", "program_id", "organization_id"),
        sa.CheckConstraint(
            "state IN ('planned','active','completed','cancelled')", name="cohort_state"
        ),
        sa.CheckConstraint("ends_on >= starts_on", name="cohort_dates"),
        sa.CheckConstraint("capacity IS NULL OR capacity > 0", name="cohort_capacity"),
        sa.CheckConstraint("version > 0", name="cohort_version"),
    )
    op.create_index("ix_cohorts_organization_id", "cohorts", ["organization_id"])
    op.create_index("ix_cohorts_program_id", "cohorts", ["program_id"])
    op.create_index("ix_cohorts_center_id", "cohorts", ["center_id"])
    op.create_index("ix_cohort_program_state", "cohorts", ["program_id", "state", "id"])
    op.create_index("ix_cohort_center_state", "cohorts", ["center_id", "state", "id"])
    op.create_table(
        "application_cycles",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("program_id", sa.Uuid(), nullable=False),
        sa.Column("cohort_id", sa.Uuid(), nullable=True),
        sa.Column("form_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(60), nullable=False),
        sa.Column("name_en", sa.String(160), nullable=False),
        sa.Column("name_ta", sa.String(160), nullable=False),
        sa.Column("opens_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closes_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        *record_columns(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["program_id", "organization_id"],
            ["programs.id", "programs.organization_id"],
            name="fk_application_cycle_program_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["cohort_id", "program_id", "organization_id"],
            ["cohorts.id", "cohorts.program_id", "cohorts.organization_id"],
            name="fk_application_cycle_cohort_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["form_id", "organization_id"],
            ["application_forms.id", "application_forms.organization_id"],
            name="fk_application_cycle_form_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "code"),
        sa.UniqueConstraint("id", "organization_id"),
        sa.CheckConstraint(
            "state IN ('draft','open','closed','cancelled')", name="application_cycle_state"
        ),
        sa.CheckConstraint("closes_at > opens_at", name="application_cycle_dates"),
        sa.CheckConstraint("version > 0", name="application_cycle_version"),
    )
    op.create_index(
        "ix_application_cycles_organization_id", "application_cycles", ["organization_id"]
    )
    op.create_index("ix_application_cycles_program_id", "application_cycles", ["program_id"])
    op.create_index("ix_application_cycles_cohort_id", "application_cycles", ["cohort_id"])
    op.create_index("ix_application_cycles_form_id", "application_cycles", ["form_id"])
    op.create_index(
        "ix_application_cycle_program_state", "application_cycles", ["program_id", "state", "id"]
    )


def downgrade() -> None:
    op.drop_table("application_cycles")
    op.drop_table("cohorts")
    op.drop_table("training_centers")
    op.drop_table("programs")
    op.drop_constraint("uq_application_form_scope", "application_forms", type_="unique")
