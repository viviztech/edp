"""Add reviewer scoring, comments, moderation and aggregation evidence."""

import sqlalchemy as sa
from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "f0a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "INSERT INTO permissions (code) VALUES ('selection.review.moderate') ON CONFLICT DO NOTHING"
    )
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_code)
        SELECT id, 'selection.review.moderate' FROM roles
        WHERE name IN ('Super Admin', 'Program Director')
        ON CONFLICT DO NOTHING
    """)
    op.create_unique_constraint(
        "uq_selection_criterion_id_rubric", "selection_criteria", ["id", "rubric_id"]
    )
    op.create_unique_constraint(
        "uq_review_assignment_id_rubric", "review_assignments", ["id", "rubric_id"]
    )
    op.drop_constraint("review_assignment_status", "review_assignments", type_="check")
    op.create_check_constraint(
        "review_assignment_status",
        "review_assignments",
        "status IN ('assigned','in_review','completed')",
    )
    op.add_column("review_assignments", sa.Column("internal_comment", sa.String(4000)))
    op.add_column("review_assignments", sa.Column("weighted_score", sa.Numeric(7, 4)))
    op.add_column("review_assignments", sa.Column("submitted_at", sa.DateTime(timezone=True)))
    op.add_column(
        "review_assignments",
        sa.Column("moderation_status", sa.String(16), nullable=False, server_default="included"),
    )
    op.add_column("review_assignments", sa.Column("moderation_reason", sa.String(1000)))
    op.add_column("review_assignments", sa.Column("moderated_by_user_id", sa.Uuid()))
    op.add_column("review_assignments", sa.Column("moderated_at", sa.DateTime(timezone=True)))
    op.create_foreign_key(
        "fk_review_assignment_moderator",
        "review_assignments",
        "users",
        ["moderated_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "review_assignment_moderation_status",
        "review_assignments",
        "moderation_status IN ('included','excluded')",
    )
    op.create_check_constraint(
        "review_assignment_moderation_reason",
        "review_assignments",
        "(moderation_status = 'included') OR moderation_reason IS NOT NULL",
    )
    op.create_check_constraint(
        "review_assignment_completion",
        "review_assignments",
        "(status = 'completed' AND weighted_score IS NOT NULL AND submitted_at IS NOT NULL) OR "
        "(status <> 'completed' AND weighted_score IS NULL AND submitted_at IS NULL)",
    )
    op.create_table(
        "application_scores",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assignment_id", sa.Uuid(), nullable=False),
        sa.Column("rubric_id", sa.Uuid(), nullable=False),
        sa.Column("criterion_id", sa.Uuid(), nullable=False),
        sa.Column("score", sa.Numeric(6, 2), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assignment_id", "criterion_id"),
        sa.CheckConstraint("score >= 0 AND score <= 100", name="application_score_range"),
        sa.ForeignKeyConstraint(
            ["assignment_id", "rubric_id"],
            ["review_assignments.id", "review_assignments.rubric_id"],
            name="fk_application_score_assignment_rubric",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["criterion_id", "rubric_id"],
            ["selection_criteria.id", "selection_criteria.rubric_id"],
            name="fk_application_score_criterion_rubric",
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_application_scores_assignment_id", "application_scores", ["assignment_id"])
    op.create_index("ix_application_scores_rubric_id", "application_scores", ["rubric_id"])
    op.create_index("ix_application_scores_criterion_id", "application_scores", ["criterion_id"])
    op.execute("""
        CREATE FUNCTION protect_completed_review() RETURNS trigger

        LANGUAGE plpgsql AS $$

        BEGIN

          IF TG_OP = 'DELETE' AND OLD.status = 'completed' THEN
            RAISE EXCEPTION 'completed review evidence is immutable';
          END IF;
          IF OLD.status = 'completed' AND NOT (
            NEW.id = OLD.id AND NEW.organization_id = OLD.organization_id
            AND NEW.selection_cycle_id = OLD.selection_cycle_id
            AND NEW.rubric_id = OLD.rubric_id AND NEW.application_id = OLD.application_id
            AND NEW.reviewer_user_id = OLD.reviewer_user_id AND NEW.status = OLD.status
            AND NEW.conflict_status = OLD.conflict_status
            AND NEW.conflict_note IS NOT DISTINCT FROM OLD.conflict_note
            AND NEW.internal_comment IS NOT DISTINCT FROM OLD.internal_comment
            AND NEW.weighted_score IS NOT DISTINCT FROM OLD.weighted_score
            AND NEW.submitted_at IS NOT DISTINCT FROM OLD.submitted_at
            AND NEW.created_at = OLD.created_at
          ) THEN
            RAISE EXCEPTION 'completed review evidence is immutable';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_completed_review_immutable
        BEFORE UPDATE OR DELETE ON review_assignments
        FOR EACH ROW EXECUTE FUNCTION protect_completed_review();

        CREATE FUNCTION protect_application_score() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE assignment_status text;
        BEGIN
          SELECT status INTO assignment_status FROM review_assignments
          WHERE id = COALESCE(OLD.assignment_id, NEW.assignment_id);
          IF assignment_status = 'completed' THEN
            RAISE EXCEPTION 'submitted scores are immutable';
          END IF;
          IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_application_score_immutable
        BEFORE INSERT OR UPDATE OR DELETE ON application_scores
        FOR EACH ROW EXECUTE FUNCTION protect_application_score();
    """)


def downgrade() -> None:
    op.execute("DELETE FROM role_permissions WHERE permission_code = 'selection.review.moderate'")
    op.execute("DELETE FROM permissions WHERE code = 'selection.review.moderate'")
    op.execute("DROP TRIGGER trg_application_score_immutable ON application_scores")
    op.execute("DROP FUNCTION protect_application_score")
    op.execute("DROP TRIGGER trg_completed_review_immutable ON review_assignments")
    op.execute("DROP FUNCTION protect_completed_review")
    op.drop_index("ix_application_scores_criterion_id", table_name="application_scores")
    op.drop_index("ix_application_scores_rubric_id", table_name="application_scores")
    op.drop_index("ix_application_scores_assignment_id", table_name="application_scores")
    op.drop_table("application_scores")
    op.drop_constraint("review_assignment_completion", "review_assignments", type_="check")
    op.drop_constraint("review_assignment_moderation_reason", "review_assignments", type_="check")
    op.drop_constraint("review_assignment_moderation_status", "review_assignments", type_="check")
    op.drop_constraint("fk_review_assignment_moderator", "review_assignments", type_="foreignkey")
    for name in (
        "moderated_at",
        "moderated_by_user_id",
        "moderation_reason",
        "moderation_status",
        "submitted_at",
        "weighted_score",
        "internal_comment",
    ):
        op.drop_column("review_assignments", name)
    op.drop_constraint("review_assignment_status", "review_assignments", type_="check")
    op.execute("UPDATE review_assignments SET status = 'in_review' WHERE status = 'completed'")
    op.create_check_constraint(
        "review_assignment_status",
        "review_assignments",
        "status IN ('assigned','in_review')",
    )
    op.drop_constraint("uq_review_assignment_id_rubric", "review_assignments", type_="unique")
    op.drop_constraint("uq_selection_criterion_id_rubric", "selection_criteria", type_="unique")
