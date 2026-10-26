"""Reject incomplete quotation catalogue references, including SQL NULL/UNKNOWN."""

from alembic import op

revision = "q3b9c5d1e678"
down_revision = "q2a8b4c0d567"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("tool_line_reference", "tool_quotation_lines", type_="check")
    op.create_check_constraint(
        "tool_line_reference",
        "tool_quotation_lines",
        "(catalogue_item_id IS NULL AND catalogue_version IS NULL) OR "
        "(catalogue_item_id IS NOT NULL AND catalogue_version IS NOT NULL "
        "AND catalogue_version > 0)",
    )


def downgrade() -> None:
    op.drop_constraint("tool_line_reference", "tool_quotation_lines", type_="check")
    op.create_check_constraint(
        "tool_line_reference",
        "tool_quotation_lines",
        "(catalogue_item_id IS NULL AND catalogue_version IS NULL) OR "
        "(catalogue_item_id IS NOT NULL AND catalogue_version > 0)",
    )
