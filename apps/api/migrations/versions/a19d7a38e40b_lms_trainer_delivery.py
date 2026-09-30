"""L01.3 trainer-scoped learning delivery permission."""

import sqlalchemy as sa
from alembic import op

revision = "a19d7a38e40b"
down_revision = "9a8cc5a7c32f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "INSERT INTO permissions (code) VALUES ('lms.delivery.view') ON CONFLICT DO NOTHING"
        )
    )
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_code)
        SELECT roles.id, 'lms.delivery.view'
        FROM roles
        WHERE roles.name IN ('Super Admin','Program Director','Program Manager','Trainer')
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM role_permissions WHERE permission_code = 'lms.delivery.view'")
    op.execute("DELETE FROM permissions WHERE code = 'lms.delivery.view'")
