"""Meta event replay versions and recovery indexes."""

import sqlalchemy as sa
from alembic import op

revision = "e7f8091a2b3c"
down_revision = "d6e7f8091a2b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "meta_webhook_events",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_check_constraint("meta_event_version", "meta_webhook_events", "version > 0")
    op.create_index(
        "ix_meta_event_recovery",
        "meta_webhook_events",
        ["state", "next_attempt_at", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_meta_event_recovery", table_name="meta_webhook_events")
    op.drop_constraint("meta_event_version", "meta_webhook_events", type_="check")
    op.drop_column("meta_webhook_events", "version")
