"""CRM tags and follow-up completion."""

import sqlalchemy as sa
from alembic import op

revision = "b4c5d6e7f809"
down_revision = "a3b4c5d6e7f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "crm_lead_activities",
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
    )
    op.create_check_constraint("crm_activity_version", "crm_lead_activities", "version > 0")

    op.create_table(
        "crm_tags",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(40), nullable=False),
        sa.Column("normalized_name", sa.String(40), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(trim(name)) BETWEEN 1 AND 40", name="crm_tag_name"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "normalized_name"),
    )
    op.create_index("ix_crm_tags_organization_id", "crm_tags", ["organization_id"])

    op.create_table(
        "crm_lead_tags",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("lead_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["lead_id"], ["crm_leads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["crm_tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "lead_id", "tag_id"),
    )
    op.create_index("ix_crm_lead_tags_organization_id", "crm_lead_tags", ["organization_id"])
    op.create_index("ix_crm_lead_tags_lead_id", "crm_lead_tags", ["lead_id"])
    op.create_index("ix_crm_lead_tags_tag_id", "crm_lead_tags", ["tag_id"])


def downgrade() -> None:
    op.drop_index("ix_crm_lead_tags_tag_id", table_name="crm_lead_tags")
    op.drop_index("ix_crm_lead_tags_lead_id", table_name="crm_lead_tags")
    op.drop_index("ix_crm_lead_tags_organization_id", table_name="crm_lead_tags")
    op.drop_table("crm_lead_tags")
    op.drop_index("ix_crm_tags_organization_id", table_name="crm_tags")
    op.drop_table("crm_tags")
    op.drop_constraint("crm_activity_version", "crm_lead_activities", type_="check")
    op.drop_column("crm_lead_activities", "version")
