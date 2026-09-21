"""Index notification retention cleanup."""

from alembic import op

revision = "f9b1c2d3e4f5"
down_revision = "f8a0b1c2d3e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_notification_retention", "notification_intents", ["created_at", "id"])


def downgrade() -> None:
    op.drop_index("ix_notification_retention", table_name="notification_intents")
