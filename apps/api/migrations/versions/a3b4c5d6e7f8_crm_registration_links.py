"""crm registration links"""

import sqlalchemy as sa
from alembic import op

revision = "a3b4c5d6e7f8"
down_revision = "92a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crm_lead_conversions",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("lead_id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(80), nullable=False),
        sa.Column("campaign", sa.String(120), nullable=False),
        sa.Column("lead_version", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("lead_version > 0", name="crm_conversion_version"),
        sa.CheckConstraint(
            "length(trim(reason)) BETWEEN 1 AND 500",
            name="crm_conversion_reason",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["lead_id"], ["crm_leads.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lead_id"),
    )
    op.create_index(
        "ix_crm_lead_conversions_organization_id",
        "crm_lead_conversions",
        ["organization_id"],
    )
    op.create_index(
        "ix_crm_lead_conversions_person_id",
        "crm_lead_conversions",
        ["person_id"],
    )
    op.create_index(
        "ix_crm_lead_conversions_actor_user_id",
        "crm_lead_conversions",
        ["actor_user_id"],
    )
    op.execute(
        "CREATE FUNCTION crm_conversion_immutable() RETURNS trigger LANGUAGE plpgsql "
        "AS $$ BEGIN RAISE EXCEPTION 'CRM registration links are immutable'; END $$"
    )
    op.execute(
        "CREATE TRIGGER crm_conversion_immutable BEFORE UPDATE OR DELETE "
        "ON crm_lead_conversions FOR EACH ROW "
        "EXECUTE FUNCTION crm_conversion_immutable()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER crm_conversion_immutable ON crm_lead_conversions")
    op.execute("DROP FUNCTION crm_conversion_immutable()")
    op.drop_index(
        "ix_crm_lead_conversions_actor_user_id",
        table_name="crm_lead_conversions",
    )
    op.drop_index("ix_crm_lead_conversions_person_id", table_name="crm_lead_conversions")
    op.drop_index(
        "ix_crm_lead_conversions_organization_id",
        table_name="crm_lead_conversions",
    )
    op.drop_table("crm_lead_conversions")
