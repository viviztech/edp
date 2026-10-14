"""contact enquiries"""

import sqlalchemy as sa
from alembic import op

revision = "5e6f708192a3"
down_revision = "4d5e6f708192"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "contact_enquiries",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("consent_version", sa.String(40), nullable=False),
        sa.Column("dedupe_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('new','reviewed','closed')", name="enquiry_status"),
        sa.CheckConstraint(
            "length(trim(name)) BETWEEN 1 AND 120 AND length(message) BETWEEN 1 AND 5000",
            name="enquiry_content",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "dedupe_hash"),
    )
    op.create_index(
        "ix_contact_enquiries_organization_id", "contact_enquiries", ["organization_id"]
    )


def downgrade():
    op.drop_index("ix_contact_enquiries_organization_id", table_name="contact_enquiries")
    op.drop_table("contact_enquiries")
