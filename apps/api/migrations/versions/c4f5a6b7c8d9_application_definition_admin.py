"""Add application definition administration policy controls."""

import sqlalchemy as sa
from alembic import op

revision = "c4f5a6b7c8d9"
down_revision = "b3e4f5a6b7c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "application_forms",
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "application_forms",
        sa.Column("published_by_id", sa.Uuid(), nullable=True),
    )
    op.create_check_constraint("application_form_revision", "application_forms", "revision > 0")
    op.create_foreign_key(
        "fk_application_form_published_by",
        "application_forms",
        "users",
        ["published_by_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_application_forms_published_by_id",
        "application_forms",
        ["published_by_id"],
    )
    op.create_index(
        "uq_application_form_draft",
        "application_forms",
        ["organization_id"],
        unique=True,
        postgresql_where=sa.text("state = 'draft'"),
    )
    op.execute(
        """
        CREATE FUNCTION protect_application_form_policy() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF OLD.state <> 'draft' AND (
            NEW.organization_id IS DISTINCT FROM OLD.organization_id OR
            NEW.version IS DISTINCT FROM OLD.version OR
            NEW.title_en IS DISTINCT FROM OLD.title_en OR
            NEW.title_ta IS DISTINCT FROM OLD.title_ta
          ) THEN
            RAISE EXCEPTION 'published application definition policy is immutable';
          END IF;
          RETURN NEW;
        END $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_application_form_policy_immutable
        BEFORE UPDATE ON application_forms
        FOR EACH ROW EXECUTE FUNCTION protect_application_form_policy();
        """
    )
    op.execute(
        """
        CREATE FUNCTION protect_application_field_policy() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE target_form uuid;
        DECLARE target_state varchar;
        BEGIN
          target_form := CASE WHEN TG_OP = 'DELETE' THEN OLD.form_id ELSE NEW.form_id END;
          SELECT state INTO target_state FROM application_forms WHERE id = target_form;
          IF target_state IS DISTINCT FROM 'draft' THEN
            RAISE EXCEPTION 'published application definition fields are immutable';
          END IF;
          RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
        END $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_application_field_policy_immutable
        BEFORE INSERT OR UPDATE OR DELETE ON application_fields
        FOR EACH ROW EXECUTE FUNCTION protect_application_field_policy();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_application_field_policy_immutable ON application_fields"
    )
    op.execute("DROP FUNCTION IF EXISTS protect_application_field_policy")
    op.execute("DROP TRIGGER IF EXISTS trg_application_form_policy_immutable ON application_forms")
    op.execute("DROP FUNCTION IF EXISTS protect_application_form_policy")
    op.drop_index("uq_application_form_draft", table_name="application_forms")
    op.drop_index(
        "ix_application_forms_published_by_id",
        table_name="application_forms",
        if_exists=True,
    )
    op.drop_constraint("fk_application_form_published_by", "application_forms", type_="foreignkey")
    op.drop_constraint("application_form_revision", "application_forms", type_="check")
    op.drop_column("application_forms", "published_by_id")
    op.drop_column("application_forms", "revision")
