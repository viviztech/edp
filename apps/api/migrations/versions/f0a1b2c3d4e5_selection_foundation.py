"""Add selection cycles, versioned rubrics and review assignments."""

import sqlalchemy as sa
from alembic import op

revision = "f0a1b2c3d4e5"
down_revision = "e6b7c8d9e0f1"
branch_labels = None
depends_on = None


def record_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.drop_constraint("application_state", "applications", type_="check")
    op.drop_constraint("application_submission_evidence", "applications", type_="check")
    op.create_check_constraint(
        "application_state",
        "applications",
        "state IN ('draft','submitted','under_review')",
    )
    op.create_check_constraint(
        "application_submission_evidence",
        "applications",
        "(state = 'draft' AND application_number IS NULL AND submitted_at IS NULL) OR "
        "(state IN ('submitted','under_review') AND cycle_id IS NOT NULL "
        "AND application_number IS NOT NULL AND submitted_at IS NOT NULL)",
    )
    op.create_unique_constraint(
        "uq_application_organization_scope", "applications", ["id", "organization_id"]
    )
    op.drop_constraint(
        "application_history_from_state", "application_status_history", type_="check"
    )
    op.drop_constraint("application_history_to_state", "application_status_history", type_="check")
    op.create_check_constraint(
        "application_history_from_state",
        "application_status_history",
        "from_state IS NULL OR from_state IN ('draft','submitted','under_review')",
    )
    op.create_check_constraint(
        "application_history_to_state",
        "application_status_history",
        "to_state IN ('draft','submitted','under_review')",
    )
    op.execute("DROP TRIGGER trg_application_submitted_immutable ON applications")
    op.execute("DROP FUNCTION protect_submitted_application")
    op.execute("""
        CREATE FUNCTION protect_submitted_application() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'submitted application is immutable';
          END IF;
          IF OLD.state <> 'draft' AND NOT (
            OLD.state = 'submitted' AND NEW.state = 'under_review'
            AND NEW.version = OLD.version + 1
            AND NEW.id = OLD.id
            AND NEW.organization_id = OLD.organization_id
            AND NEW.person_id = OLD.person_id
            AND NEW.form_id = OLD.form_id
            AND NEW.cycle_id = OLD.cycle_id
            AND NEW.current_revision_id = OLD.current_revision_id
            AND NEW.application_number = OLD.application_number
            AND NEW.submitted_at = OLD.submitted_at
            AND NEW.created_at = OLD.created_at
          ) THEN
            RAISE EXCEPTION 'submitted application evidence is immutable';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_application_submitted_immutable
        BEFORE UPDATE OR DELETE ON applications
        FOR EACH ROW EXECUTE FUNCTION protect_submitted_application();
    """)

    op.create_table(
        "selection_cycles",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("application_cycle_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(60), nullable=False),
        sa.Column("name_en", sa.String(160), nullable=False),
        sa.Column("name_ta", sa.String(160), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        *record_columns(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["application_cycle_id", "organization_id"],
            ["application_cycles.id", "application_cycles.organization_id"],
            name="fk_selection_cycle_application_cycle_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "code"),
        sa.UniqueConstraint("application_cycle_id"),
        sa.UniqueConstraint("id", "organization_id"),
        sa.CheckConstraint("state IN ('draft','active','closed')", name="selection_cycle_state"),
        sa.CheckConstraint("version > 0", name="selection_cycle_version"),
    )
    op.create_index("ix_selection_cycles_organization_id", "selection_cycles", ["organization_id"])
    op.create_index(
        "ix_selection_cycles_application_cycle_id", "selection_cycles", ["application_cycle_id"]
    )
    op.create_index(
        "ix_selection_cycle_scope_state",
        "selection_cycles",
        ["organization_id", "state", "id"],
    )
    op.create_table(
        "selection_rubrics",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("selection_cycle_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("edit_version", sa.Integer(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        *record_columns(),
        sa.ForeignKeyConstraint(
            ["selection_cycle_id", "organization_id"],
            ["selection_cycles.id", "selection_cycles.organization_id"],
            name="fk_selection_rubric_cycle_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("selection_cycle_id", "version_number"),
        sa.UniqueConstraint("id", "organization_id"),
        sa.UniqueConstraint("id", "selection_cycle_id", "organization_id"),
        sa.CheckConstraint(
            "state IN ('draft','published','retired')", name="selection_rubric_state"
        ),
        sa.CheckConstraint("version_number > 0", name="selection_rubric_version_number"),
        sa.CheckConstraint("edit_version > 0", name="selection_rubric_edit_version"),
        sa.CheckConstraint(
            "(state = 'draft' AND published_at IS NULL) OR "
            "(state IN ('published','retired') AND published_at IS NOT NULL)",
            name="selection_rubric_publication",
        ),
    )
    op.create_index(
        "ix_selection_rubrics_organization_id", "selection_rubrics", ["organization_id"]
    )
    op.create_index(
        "ix_selection_rubrics_selection_cycle_id", "selection_rubrics", ["selection_cycle_id"]
    )
    op.create_index(
        "ix_selection_rubric_cycle_state",
        "selection_rubrics",
        ["selection_cycle_id", "state", "id"],
    )
    op.create_index(
        "uq_selection_rubric_draft",
        "selection_rubrics",
        ["selection_cycle_id"],
        unique=True,
        postgresql_where=sa.text("state = 'draft'"),
    )
    op.create_index(
        "uq_selection_rubric_published",
        "selection_rubrics",
        ["selection_cycle_id"],
        unique=True,
        postgresql_where=sa.text("state = 'published'"),
    )
    op.create_table(
        "selection_criteria",
        sa.Column("rubric_id", sa.Uuid(), nullable=False),
        sa.Column("criterion_key", sa.String(80), nullable=False),
        sa.Column("label_en", sa.String(300), nullable=False),
        sa.Column("label_ta", sa.String(300), nullable=False),
        sa.Column("guidance_en", sa.String(1000), nullable=True),
        sa.Column("guidance_ta", sa.String(1000), nullable=True),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("minimum_score", sa.Integer(), nullable=False),
        sa.Column("maximum_score", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        *record_columns(),
        sa.ForeignKeyConstraint(["rubric_id"], ["selection_rubrics.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rubric_id", "criterion_key"),
        sa.UniqueConstraint("rubric_id", "position"),
        sa.CheckConstraint("weight > 0 AND weight <= 100", name="selection_criterion_weight"),
        sa.CheckConstraint(
            "minimum_score >= 0 AND maximum_score > minimum_score AND maximum_score <= 100",
            name="selection_criterion_score_range",
        ),
        sa.CheckConstraint("position >= 0", name="selection_criterion_position"),
    )
    op.create_index("ix_selection_criteria_rubric_id", "selection_criteria", ["rubric_id"])
    op.create_table(
        "review_assignments",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("selection_cycle_id", sa.Uuid(), nullable=False),
        sa.Column("rubric_id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("conflict_status", sa.String(16), nullable=False),
        sa.Column("conflict_note", sa.String(500), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        *record_columns(),
        sa.ForeignKeyConstraint(
            ["selection_cycle_id", "organization_id"],
            ["selection_cycles.id", "selection_cycles.organization_id"],
            name="fk_review_assignment_cycle_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["rubric_id", "selection_cycle_id", "organization_id"],
            [
                "selection_rubrics.id",
                "selection_rubrics.selection_cycle_id",
                "selection_rubrics.organization_id",
            ],
            name="fk_review_assignment_rubric_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["application_id", "organization_id"],
            ["applications.id", "applications.organization_id"],
            name="fk_review_assignment_application_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id", "reviewer_user_id"),
        sa.CheckConstraint("status IN ('assigned','in_review')", name="review_assignment_status"),
        sa.CheckConstraint(
            "conflict_status IN ('pending','clear','conflict')",
            name="review_assignment_conflict_status",
        ),
        sa.CheckConstraint(
            "(conflict_status = 'conflict' AND conflict_note IS NOT NULL) OR "
            "(conflict_status <> 'conflict' AND conflict_note IS NULL)",
            name="review_assignment_conflict_note",
        ),
        sa.CheckConstraint("version > 0", name="review_assignment_version"),
    )
    for column in (
        "organization_id",
        "selection_cycle_id",
        "rubric_id",
        "application_id",
        "reviewer_user_id",
    ):
        op.create_index(f"ix_review_assignments_{column}", "review_assignments", [column])
    op.create_index(
        "ix_review_assignment_reviewer",
        "review_assignments",
        ["reviewer_user_id", "status", "id"],
    )
    op.execute("""
        CREATE FUNCTION protect_selection_rubric() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'DELETE' OR (
            OLD.state <> 'draft' AND NOT (
              OLD.state = 'published' AND NEW.state = 'retired'
              AND NEW.id = OLD.id
              AND NEW.organization_id = OLD.organization_id
              AND NEW.selection_cycle_id = OLD.selection_cycle_id
              AND NEW.version_number = OLD.version_number
              AND NEW.edit_version = OLD.edit_version
              AND NEW.published_at = OLD.published_at
              AND NEW.created_at = OLD.created_at
            )
          ) THEN
            RAISE EXCEPTION 'published selection rubric is immutable';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_selection_rubric_immutable
        BEFORE UPDATE OR DELETE ON selection_rubrics
        FOR EACH ROW EXECUTE FUNCTION protect_selection_rubric();

        CREATE FUNCTION protect_selection_criterion() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE target_rubric uuid;
        DECLARE target_state varchar;
        BEGIN
          target_rubric := CASE WHEN TG_OP = 'DELETE' THEN OLD.rubric_id ELSE NEW.rubric_id END;
          SELECT state INTO target_state FROM selection_rubrics WHERE id = target_rubric;
          IF target_state IS DISTINCT FROM 'draft' THEN
            RAISE EXCEPTION 'published selection criteria are immutable';
          END IF;
          RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
        END $$;
        CREATE TRIGGER trg_selection_criterion_immutable
        BEFORE INSERT OR UPDATE OR DELETE ON selection_criteria
        FOR EACH ROW EXECUTE FUNCTION protect_selection_criterion();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_selection_criterion_immutable ON selection_criteria")
    op.execute("DROP FUNCTION protect_selection_criterion")
    op.execute("DROP TRIGGER trg_selection_rubric_immutable ON selection_rubrics")
    op.execute("DROP FUNCTION protect_selection_rubric")
    op.drop_table("review_assignments")
    op.drop_table("selection_criteria")
    op.drop_table("selection_rubrics")
    op.drop_table("selection_cycles")
    op.execute("DROP TRIGGER trg_application_submitted_immutable ON applications")
    op.execute("DROP FUNCTION protect_submitted_application")
    op.execute("""
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
    """)
    op.drop_constraint("application_history_to_state", "application_status_history", type_="check")
    op.drop_constraint(
        "application_history_from_state", "application_status_history", type_="check"
    )
    op.create_check_constraint(
        "application_history_from_state",
        "application_status_history",
        "from_state IS NULL OR from_state IN ('draft','submitted')",
    )
    op.create_check_constraint(
        "application_history_to_state",
        "application_status_history",
        "to_state IN ('draft','submitted')",
    )
    op.drop_constraint("uq_application_organization_scope", "applications", type_="unique")
    op.drop_constraint("application_submission_evidence", "applications", type_="check")
    op.drop_constraint("application_state", "applications", type_="check")
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
