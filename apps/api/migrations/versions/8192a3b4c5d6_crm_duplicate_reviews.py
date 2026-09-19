"""crm duplicate reviews"""

import sqlalchemy as sa
from alembic import op

revision = "8192a3b4c5d6"
down_revision = "708192a3b4c5"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("crm_lead_status", "crm_leads", type_="check")
    op.add_column("crm_leads", sa.Column("merged_into_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_crm_leads_merged_into",
        "crm_leads",
        "crm_leads",
        ["merged_into_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_crm_leads_merged_into_id", "crm_leads", ["merged_into_id"])
    op.create_check_constraint(
        "crm_lead_status",
        "crm_leads",
        "status IN ('new','contacted','interested','registration_started',"
        "'converted','not_interested','merged')",
    )
    op.create_check_constraint(
        "crm_lead_merge_state",
        "crm_leads",
        "(status = 'merged' AND merged_into_id IS NOT NULL) OR "
        "(status <> 'merged' AND merged_into_id IS NULL)",
    )
    op.create_table(
        "crm_duplicate_reviews",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("lead_a_id", sa.Uuid(), nullable=False),
        sa.Column("lead_b_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("resolved_by_id", sa.Uuid()),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("lead_a_id <> lead_b_id", name="crm_duplicate_distinct"),
        sa.CheckConstraint("state IN ('pending','merged','rejected')", name="crm_duplicate_state"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["lead_a_id"], ["crm_leads.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["lead_b_id"], ["crm_leads.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["resolved_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "lead_a_id", "lead_b_id"),
    )
    op.create_index(
        "ix_crm_duplicate_reviews_organization_id", "crm_duplicate_reviews", ["organization_id"]
    )
    op.create_index("ix_crm_duplicate_reviews_lead_a_id", "crm_duplicate_reviews", ["lead_a_id"])
    op.create_index("ix_crm_duplicate_reviews_lead_b_id", "crm_duplicate_reviews", ["lead_b_id"])


def downgrade():
    op.drop_table("crm_duplicate_reviews")
    op.drop_constraint("crm_lead_merge_state", "crm_leads", type_="check")
    op.drop_constraint("crm_lead_status", "crm_leads", type_="check")
    op.drop_index("ix_crm_leads_merged_into_id", table_name="crm_leads")
    op.drop_constraint("fk_crm_leads_merged_into", "crm_leads", type_="foreignkey")
    op.drop_column("crm_leads", "merged_into_id")
    op.create_check_constraint(
        "crm_lead_status",
        "crm_leads",
        "status IN ('new','contacted','interested','registration_started',"
        "'converted','not_interested')",
    )
