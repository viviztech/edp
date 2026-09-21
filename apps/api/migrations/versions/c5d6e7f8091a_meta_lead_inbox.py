"""Meta lead integration inbox and mappings."""

import sqlalchemy as sa
from alembic import op

revision = "c5d6e7f8091a"
down_revision = "b4c5d6e7f809"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meta_integrations",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("page_id", sa.String(80), nullable=False),
        sa.Column("access_token_ciphertext", sa.Text(), nullable=False),
        sa.Column("app_secret_ciphertext", sa.Text(), nullable=False),
        sa.Column("verify_token_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('active','disabled')", name="meta_integration_status"),
        sa.CheckConstraint("version > 0", name="meta_integration_version"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "page_id"),
    )
    op.create_index(
        "ix_meta_integrations_organization_id",
        "meta_integrations",
        ["organization_id"],
    )

    op.create_table(
        "meta_form_mappings",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("integration_id", sa.Uuid(), nullable=False),
        sa.Column("form_id", sa.String(80), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("campaign", sa.String(120), nullable=False),
        sa.Column("field_mapping", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('active','disabled')", name="meta_mapping_status"),
        sa.CheckConstraint("version > 0", name="meta_mapping_version"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["integration_id"], ["meta_integrations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("integration_id", "form_id"),
    )
    op.create_index(
        "ix_meta_form_mappings_organization_id",
        "meta_form_mappings",
        ["organization_id"],
    )
    op.create_index(
        "ix_meta_form_mappings_integration_id",
        "meta_form_mappings",
        ["integration_id"],
    )

    op.create_table(
        "meta_webhook_events",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("integration_id", sa.Uuid(), nullable=False),
        sa.Column("mapping_id", sa.Uuid(), nullable=True),
        sa.Column("provider_event_id", sa.String(120), nullable=False),
        sa.Column("meta_lead_id", sa.String(120), nullable=False),
        sa.Column("page_id", sa.String(80), nullable=False),
        sa.Column("form_id", sa.String(80), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(48), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("lead_id", sa.Uuid(), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "state IN ('queued','processing','retrying','completed','failed')",
            name="meta_event_state",
        ),
        sa.CheckConstraint("attempt_count >= 0", name="meta_event_attempt_count"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["integration_id"], ["meta_integrations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["mapping_id"], ["meta_form_mappings.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["lead_id"], ["crm_leads.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("integration_id", "provider_event_id"),
    )
    op.create_index(
        "ix_meta_webhook_events_organization_id",
        "meta_webhook_events",
        ["organization_id"],
    )
    op.create_index(
        "ix_meta_webhook_events_integration_id",
        "meta_webhook_events",
        ["integration_id"],
    )
    op.create_index(
        "ix_meta_webhook_events_mapping_id",
        "meta_webhook_events",
        ["mapping_id"],
    )
    op.create_index(
        "ix_meta_webhook_events_meta_lead_id",
        "meta_webhook_events",
        ["meta_lead_id"],
    )
    op.create_index(
        "ix_meta_webhook_events_lead_id",
        "meta_webhook_events",
        ["lead_id"],
    )
    op.create_index(
        "ix_meta_webhook_events_retention_expires_at",
        "meta_webhook_events",
        ["retention_expires_at"],
    )
    op.create_index(
        "ix_meta_event_health",
        "meta_webhook_events",
        ["organization_id", "state", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_meta_event_health", table_name="meta_webhook_events")
    op.drop_index(
        "ix_meta_webhook_events_retention_expires_at",
        table_name="meta_webhook_events",
    )
    op.drop_index("ix_meta_webhook_events_lead_id", table_name="meta_webhook_events")
    op.drop_index(
        "ix_meta_webhook_events_meta_lead_id",
        table_name="meta_webhook_events",
    )
    op.drop_index("ix_meta_webhook_events_mapping_id", table_name="meta_webhook_events")
    op.drop_index(
        "ix_meta_webhook_events_integration_id",
        table_name="meta_webhook_events",
    )
    op.drop_index(
        "ix_meta_webhook_events_organization_id",
        table_name="meta_webhook_events",
    )
    op.drop_table("meta_webhook_events")
    op.drop_index(
        "ix_meta_form_mappings_integration_id",
        table_name="meta_form_mappings",
    )
    op.drop_index(
        "ix_meta_form_mappings_organization_id",
        table_name="meta_form_mappings",
    )
    op.drop_table("meta_form_mappings")
    op.drop_index(
        "ix_meta_integrations_organization_id",
        table_name="meta_integrations",
    )
    op.drop_table("meta_integrations")
