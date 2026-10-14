"""cms assets"""

import sqlalchemy as sa
from alembic import op

revision = "4d5e6f708192"
down_revision = "3c4d5e6f7081"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cms_assets",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("media_type", sa.String(100), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("scan_status", sa.String(16), nullable=False),
        sa.Column("visibility", sa.String(16), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "scan_status IN ('pending','clean','infected','rejected')", name="cms_asset_scan"
        ),
        sa.CheckConstraint("visibility IN ('private','public')", name="cms_asset_visibility"),
        sa.CheckConstraint("byte_size BETWEEN 1 AND 10485760", name="cms_asset_size"),
        sa.CheckConstraint(
            "media_type IN ('image/jpeg','image/png','image/webp','application/pdf')",
            name="cms_asset_type",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index("ix_cms_assets_organization_id", "cms_assets", ["organization_id"])
    op.create_index(
        "ix_cms_assets_public", "cms_assets", ["organization_id", "visibility", "scan_status"]
    )


def downgrade():
    op.drop_index("ix_cms_assets_public", table_name="cms_assets")
    op.drop_index("ix_cms_assets_organization_id", table_name="cms_assets")
    op.drop_table("cms_assets")
