"""Add versioned applicant-owned application drafts."""

import sqlalchemy as sa
from alembic import op

revision = "b3e4f5a6b7c8"
down_revision = "a2d3e4f5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "application_forms",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("title_en", sa.String(160), nullable=False),
        sa.Column("title_ta", sa.String(160), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "version"),
        sa.CheckConstraint("version > 0", name="application_form_version"),
        sa.CheckConstraint(
            "state IN ('draft','published','retired')", name="application_form_state"
        ),
    )
    op.create_index(
        "ix_application_forms_organization_id", "application_forms", ["organization_id"]
    )
    op.create_index(
        "ix_application_form_active", "application_forms", ["organization_id", "state", "version"]
    )
    op.create_table(
        "application_fields",
        sa.Column("form_id", sa.Uuid(), nullable=False),
        sa.Column("field_key", sa.String(80), nullable=False),
        sa.Column("section_key", sa.String(80), nullable=False),
        sa.Column("label_en", sa.String(200), nullable=False),
        sa.Column("label_ta", sa.String(200), nullable=False),
        sa.Column("field_type", sa.String(16), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["form_id"], ["application_forms.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("form_id", "field_key"),
        sa.UniqueConstraint("form_id", "position"),
        sa.CheckConstraint(
            "field_type IN ('text','textarea','number','date','boolean')",
            name="application_field_type",
        ),
        sa.CheckConstraint("position >= 0", name="application_field_position"),
    )
    op.create_index("ix_application_fields_form_id", "application_fields", ["form_id"])
    op.create_table(
        "applications",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("form_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("current_revision_id", sa.Uuid(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["form_id"], ["application_forms.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("person_id", "form_id"),
        sa.UniqueConstraint("id", "form_id"),
        sa.CheckConstraint("state = 'draft'", name="application_draft_only"),
        sa.CheckConstraint("version > 0", name="application_version"),
    )
    op.create_index("ix_applications_organization_id", "applications", ["organization_id"])
    op.create_index("ix_applications_person_id", "applications", ["person_id"])
    op.create_index("ix_application_owner", "applications", ["person_id", "organization_id", "id"])
    op.create_table(
        "application_revisions",
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("form_id", sa.Uuid(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id", "form_id"],
            ["applications.id", "applications.form_id"],
            name="fk_application_revision_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["form_id"], ["application_forms.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id", "revision"),
        sa.UniqueConstraint("id", "application_id"),
        sa.CheckConstraint("revision > 0", name="application_revision_number"),
    )
    op.create_index(
        "ix_application_revisions_application_id", "application_revisions", ["application_id"]
    )
    op.create_foreign_key(
        "fk_application_current_revision",
        "applications",
        "application_revisions",
        ["current_revision_id", "id"],
        ["id", "application_id"],
    )
    op.create_table(
        "application_answers",
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("field_id", sa.Uuid(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["revision_id"], ["application_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["field_id"], ["application_fields.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("revision_id", "field_id"),
    )
    op.create_index("ix_application_answers_revision_id", "application_answers", ["revision_id"])


def downgrade() -> None:
    op.drop_table("application_answers")
    op.drop_constraint("fk_application_current_revision", "applications", type_="foreignkey")
    op.drop_table("application_revisions")
    op.drop_table("applications")
    op.drop_table("application_fields")
    op.drop_table("application_forms")
