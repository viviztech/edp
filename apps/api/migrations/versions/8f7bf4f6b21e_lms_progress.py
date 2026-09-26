"""L01.2 lesson progress, prerequisites, and completion rules."""

# ruff: noqa: E501

import sqlalchemy as sa
from alembic import op

revision = "8f7bf4f6b21e"
down_revision = "7e6ae3e5a10d"
branch_labels = None
depends_on = None


def record_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.add_column(
        "courses",
        sa.Column("completion_rule", sa.String(24), nullable=False, server_default="all_lessons"),
    )
    op.add_column("courses", sa.Column("minimum_lessons", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "course_completion_rule",
        "courses",
        "completion_rule IN ('all_lessons','minimum_lessons')",
    )
    op.create_check_constraint(
        "course_completion_rule_value",
        "courses",
        "(completion_rule = 'all_lessons' AND minimum_lessons IS NULL) OR "
        "(completion_rule = 'minimum_lessons' AND minimum_lessons > 0)",
    )
    op.create_unique_constraint(
        "uq_course_enrollment_progress_scope",
        "course_enrollments",
        ["id", "course_id", "organization_id"],
    )
    op.create_table(
        "lesson_prerequisites",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("lesson_id", sa.Uuid(), nullable=False),
        sa.Column("prerequisite_lesson_id", sa.Uuid(), nullable=False),
        *record_columns(),
        sa.CheckConstraint(
            "lesson_id <> prerequisite_lesson_id", name="lesson_prerequisite_distinct"
        ),
        sa.ForeignKeyConstraint(
            ["lesson_id", "course_id", "organization_id"],
            ["lessons.id", "lessons.course_id", "lessons.organization_id"],
            name="fk_lesson_prerequisite_target_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["prerequisite_lesson_id", "course_id", "organization_id"],
            ["lessons.id", "lessons.course_id", "lessons.organization_id"],
            name="fk_lesson_prerequisite_required_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lesson_id", "prerequisite_lesson_id"),
    )
    op.create_index(
        "ix_lesson_prerequisites_organization_id", "lesson_prerequisites", ["organization_id"]
    )
    op.create_index("ix_lesson_prerequisites_course_id", "lesson_prerequisites", ["course_id"])
    op.create_index("ix_lesson_prerequisites_lesson_id", "lesson_prerequisites", ["lesson_id"])
    op.create_index(
        "ix_lesson_prerequisites_prerequisite_lesson_id",
        "lesson_prerequisites",
        ["prerequisite_lesson_id"],
    )
    op.create_index(
        "ix_lesson_prerequisite_course", "lesson_prerequisites", ["course_id", "lesson_id"]
    )
    op.create_table(
        "lesson_progress",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("course_enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("lesson_id", sa.Uuid(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        *record_columns(),
        sa.ForeignKeyConstraint(
            ["course_enrollment_id", "course_id", "organization_id"],
            [
                "course_enrollments.id",
                "course_enrollments.course_id",
                "course_enrollments.organization_id",
            ],
            name="fk_lesson_progress_enrollment_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["lesson_id", "course_id", "organization_id"],
            ["lessons.id", "lessons.course_id", "lessons.organization_id"],
            name="fk_lesson_progress_lesson_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_enrollment_id", "lesson_id"),
    )
    for column in ("organization_id", "course_id", "course_enrollment_id", "lesson_id"):
        op.create_index(f"ix_lesson_progress_{column}", "lesson_progress", [column])
    op.create_index(
        "ix_lesson_progress_rollup", "lesson_progress", ["course_enrollment_id", "course_id"]
    )
    op.execute("""
        CREATE TRIGGER trg_lesson_prerequisite_draft_only
        BEFORE INSERT OR UPDATE OR DELETE ON lesson_prerequisites
        FOR EACH ROW EXECUTE FUNCTION protect_published_course_structure();

        CREATE FUNCTION protect_lesson_progress() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP <> 'INSERT' THEN
            RAISE EXCEPTION 'lesson completion evidence is immutable';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_lesson_progress_immutable
        BEFORE UPDATE OR DELETE ON lesson_progress
        FOR EACH ROW EXECUTE FUNCTION protect_lesson_progress();

        CREATE FUNCTION protect_course_completion_rule() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF OLD.state <> 'draft'
             AND (NEW.completion_rule IS DISTINCT FROM OLD.completion_rule
                  OR NEW.minimum_lessons IS DISTINCT FROM OLD.minimum_lessons) THEN
            RAISE EXCEPTION 'published completion rule is immutable';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_course_completion_rule_immutable
        BEFORE UPDATE ON courses
        FOR EACH ROW EXECUTE FUNCTION protect_course_completion_rule();

    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_course_completion_rule_immutable ON courses")
    op.execute("DROP FUNCTION protect_course_completion_rule")
    op.execute("DROP TRIGGER trg_lesson_progress_immutable ON lesson_progress")
    op.execute("DROP FUNCTION protect_lesson_progress")
    op.execute("DROP TRIGGER trg_lesson_prerequisite_draft_only ON lesson_prerequisites")
    op.drop_table("lesson_progress")
    op.drop_table("lesson_prerequisites")
    op.drop_constraint("uq_course_enrollment_progress_scope", "course_enrollments", type_="unique")
    op.drop_constraint("course_completion_rule_value", "courses", type_="check")
    op.drop_constraint("course_completion_rule", "courses", type_="check")
    op.drop_column("courses", "minimum_lessons")
    op.drop_column("courses", "completion_rule")
