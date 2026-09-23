"""Add immutable application submission and consent evidence."""

import sqlalchemy as sa
from alembic import op

revision = "e6b7c8d9e0f1"
down_revision = "d5a6b7c8d9e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_application_cycle_form_scope",
        "application_cycles",
        ["id", "form_id", "organization_id"],
    )
    op.create_table(
        "application_acknowledgement_definitions",
        sa.Column("form_id", sa.Uuid(), nullable=False),
        sa.Column("acknowledgement_key", sa.String(80), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("label_en", sa.String(1000), nullable=False),
        sa.Column("label_ta", sa.String(1000), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["form_id"], ["application_forms.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("form_id", "acknowledgement_key"),
        sa.UniqueConstraint("form_id", "position"),
        sa.UniqueConstraint("id", "form_id"),
        sa.CheckConstraint("kind IN ('declaration','consent')", name="application_ack_kind"),
        sa.CheckConstraint("position >= 0", name="application_ack_position"),
    )
    op.create_index(
        "ix_application_acknowledgement_definitions_form_id",
        "application_acknowledgement_definitions",
        ["form_id"],
    )
    op.drop_constraint("applications_person_id_form_id_key", "applications", type_="unique")
    op.drop_constraint("application_draft_only", "applications", type_="check")
    op.drop_index("ix_application_owner", table_name="applications")
    op.add_column("applications", sa.Column("cycle_id", sa.Uuid(), nullable=True))
    op.add_column("applications", sa.Column("application_number", sa.String(32), nullable=True))
    op.add_column(
        "applications", sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index("ix_applications_cycle_id", "applications", ["cycle_id"])
    op.create_index(
        "ix_applications_application_number",
        "applications",
        ["application_number"],
        unique=True,
    )
    op.create_index(
        "ix_application_owner",
        "applications",
        ["person_id", "organization_id", "state", "id"],
    )
    op.create_unique_constraint(
        "uq_application_person_cycle", "applications", ["person_id", "cycle_id"]
    )
    op.create_check_constraint(
        "application_state", "applications", "state IN ('draft','submitted')"
    )
    op.create_check_constraint(
        "application_submission_evidence",
        "applications",
        "(state = 'draft' AND application_number IS NULL AND submitted_at IS NULL) OR "
        "(state = 'submitted' AND cycle_id IS NOT NULL AND application_number IS NOT NULL "
        "AND submitted_at IS NOT NULL)",
    )
    op.create_foreign_key(
        "fk_application_cycle_scope",
        "applications",
        "application_cycles",
        ["cycle_id", "form_id", "organization_id"],
        ["id", "form_id", "organization_id"],
        ondelete="RESTRICT",
    )
    op.execute("CREATE SEQUENCE application_number_seq START WITH 1")
    op.create_table(
        "application_acknowledgements",
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("form_id", sa.Uuid(), nullable=False),
        sa.Column("definition_id", sa.Uuid(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id", "form_id"],
            ["applications.id", "applications.form_id"],
            name="fk_application_ack_application_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["definition_id", "form_id"],
            [
                "application_acknowledgement_definitions.id",
                "application_acknowledgement_definitions.form_id",
            ],
            name="fk_application_ack_definition_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id", "definition_id"),
    )
    op.create_index(
        "ix_application_acknowledgements_application_id",
        "application_acknowledgements",
        ["application_id"],
    )
    op.create_index(
        "ix_application_acknowledgements_definition_id",
        "application_acknowledgements",
        ["definition_id"],
    )
    op.create_table(
        "application_status_history",
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("from_state", sa.String(20), nullable=True),
        sa.Column("to_state", sa.String(20), nullable=False),
        sa.Column("application_version", sa.Integer(), nullable=False),
        sa.Column("reason_code", sa.String(40), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id", "application_version"),
        sa.CheckConstraint(
            "from_state IS NULL OR from_state IN ('draft','submitted')",
            name="application_history_from_state",
        ),
        sa.CheckConstraint(
            "to_state IN ('draft','submitted')", name="application_history_to_state"
        ),
        sa.CheckConstraint("application_version > 0", name="application_history_version"),
    )
    op.create_index(
        "ix_application_status_history_application_id",
        "application_status_history",
        ["application_id"],
    )
    op.execute(
        """
        CREATE FUNCTION protect_application_status_history() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'application status history is immutable';
        END $$;
        CREATE TRIGGER trg_application_status_history_immutable
        BEFORE UPDATE OR DELETE ON application_status_history
        FOR EACH ROW EXECUTE FUNCTION protect_application_status_history();
        """
    )
    op.execute(
        """
        CREATE FUNCTION protect_submitted_application() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF OLD.state <> 'draft' THEN
            RAISE EXCEPTION 'submitted application is immutable';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_application_submitted_immutable
        BEFORE UPDATE OR DELETE ON applications
        FOR EACH ROW EXECUTE FUNCTION protect_submitted_application();
        """
    )
    op.execute(
        """
        CREATE FUNCTION protect_submitted_revision() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE target_application uuid;
        DECLARE target_state varchar;
        BEGIN
          target_application := CASE
            WHEN TG_OP = 'DELETE' THEN OLD.application_id
            ELSE NEW.application_id
          END;
          SELECT state INTO target_state FROM applications WHERE id = target_application;
          IF target_state IS DISTINCT FROM 'draft' THEN
            RAISE EXCEPTION 'submitted application revisions are immutable';
          END IF;
          RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
        END $$;
        CREATE TRIGGER trg_application_revision_submitted_immutable
        BEFORE INSERT OR UPDATE OR DELETE ON application_revisions
        FOR EACH ROW EXECUTE FUNCTION protect_submitted_revision();
        """
    )
    op.execute(
        """
        CREATE FUNCTION protect_submitted_answer() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE target_revision uuid;
        DECLARE target_state varchar;
        BEGIN
          target_revision := CASE
            WHEN TG_OP = 'DELETE' THEN OLD.revision_id
            ELSE NEW.revision_id
          END;
          SELECT a.state INTO target_state FROM applications a
          JOIN application_revisions r ON r.application_id = a.id
          WHERE r.id = target_revision;
          IF target_state IS DISTINCT FROM 'draft' THEN
            RAISE EXCEPTION 'submitted application answers are immutable';
          END IF;
          RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
        END $$;
        CREATE TRIGGER trg_application_answer_submitted_immutable
        BEFORE INSERT OR UPDATE OR DELETE ON application_answers
        FOR EACH ROW EXECUTE FUNCTION protect_submitted_answer();
        """
    )
    op.execute(
        """
        CREATE FUNCTION protect_application_ack_policy() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE target_form uuid;
        DECLARE target_state varchar;
        BEGIN
          target_form := CASE WHEN TG_OP = 'DELETE' THEN OLD.form_id ELSE NEW.form_id END;
          SELECT state INTO target_state FROM application_forms WHERE id = target_form;
          IF target_state IS DISTINCT FROM 'draft' THEN
            RAISE EXCEPTION 'published application acknowledgement policy is immutable';
          END IF;
          RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
        END $$;
        CREATE TRIGGER trg_application_ack_policy_immutable
        BEFORE INSERT OR UPDATE OR DELETE ON application_acknowledgement_definitions
        FOR EACH ROW EXECUTE FUNCTION protect_application_ack_policy();
        """
    )
    op.execute(
        """
        CREATE FUNCTION protect_application_acceptance() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE target_application uuid;
        DECLARE target_state varchar;
        BEGIN
          target_application := CASE
            WHEN TG_OP = 'DELETE' THEN OLD.application_id
            ELSE NEW.application_id
          END;
          SELECT state INTO target_state FROM applications WHERE id = target_application;
          IF TG_OP <> 'INSERT' OR target_state IS DISTINCT FROM 'draft' THEN
            RAISE EXCEPTION 'application acceptance evidence is immutable';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_application_acceptance_immutable
        BEFORE INSERT OR UPDATE OR DELETE ON application_acknowledgements
        FOR EACH ROW EXECUTE FUNCTION protect_application_acceptance();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_application_status_history_immutable "
        "ON application_status_history"
    )
    op.execute("DROP FUNCTION IF EXISTS protect_application_status_history")
    op.execute(
        "DROP TRIGGER IF EXISTS trg_application_acceptance_immutable ON application_acknowledgements"  # noqa: E501
    )
    op.execute("DROP FUNCTION IF EXISTS protect_application_acceptance")
    op.execute(
        "DROP TRIGGER IF EXISTS trg_application_ack_policy_immutable ON application_acknowledgement_definitions"  # noqa: E501
    )
    op.execute("DROP FUNCTION IF EXISTS protect_application_ack_policy")
    op.execute(
        "DROP TRIGGER IF EXISTS trg_application_answer_submitted_immutable ON application_answers"
    )
    op.execute("DROP FUNCTION IF EXISTS protect_submitted_answer")
    op.execute(
        "DROP TRIGGER IF EXISTS trg_application_revision_submitted_immutable ON application_revisions"  # noqa: E501
    )
    op.execute("DROP FUNCTION IF EXISTS protect_submitted_revision")
    op.execute("DROP TRIGGER IF EXISTS trg_application_submitted_immutable ON applications")
    op.execute("DROP FUNCTION IF EXISTS protect_submitted_application")
    op.drop_table("application_status_history")
    op.drop_table("application_acknowledgements")
    op.execute("DROP SEQUENCE IF EXISTS application_number_seq")
    op.drop_constraint("fk_application_cycle_scope", "applications", type_="foreignkey")
    op.drop_constraint("application_submission_evidence", "applications", type_="check")
    op.drop_constraint("application_state", "applications", type_="check")
    op.drop_constraint("uq_application_person_cycle", "applications", type_="unique")
    op.drop_index("ix_application_owner", table_name="applications")
    op.drop_index("ix_applications_application_number", table_name="applications")
    op.drop_index("ix_applications_cycle_id", table_name="applications")
    op.drop_column("applications", "submitted_at")
    op.drop_column("applications", "application_number")
    op.drop_column("applications", "cycle_id")
    op.create_check_constraint("application_draft_only", "applications", "state = 'draft'")
    op.create_unique_constraint(
        "applications_person_id_form_id_key", "applications", ["person_id", "form_id"]
    )
    op.create_index(
        "ix_application_owner",
        "applications",
        ["person_id", "organization_id", "id"],
    )
    op.drop_table("application_acknowledgement_definitions")
    op.drop_constraint("uq_application_cycle_form_scope", "application_cycles", type_="unique")
