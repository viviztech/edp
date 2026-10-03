"""L02.2 assignments, submissions, manual grading, and feedback."""

import sqlalchemy as sa
from alembic import op

revision = "c3b9e5f7a012"
down_revision = "b2a8d4e6f901"
branch_labels = None
depends_on = None


def record_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.execute(
        "INSERT INTO permissions (code) VALUES ('lms.assessment.grade') ON CONFLICT DO NOTHING"
    )
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_code)
        SELECT roles.id, 'lms.assessment.grade'
        FROM roles
        WHERE roles.name IN ('Super Admin','Program Director','Program Manager','Trainer')
        ON CONFLICT DO NOTHING
    """)

    op.create_table(
        "learning_assignments",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("lesson_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title_en", sa.String(200), nullable=False),
        sa.Column("title_ta", sa.String(200), nullable=False),
        sa.Column("instructions_en", sa.Text(), nullable=False),
        sa.Column("instructions_ta", sa.Text(), nullable=False),
        sa.Column("maximum_points", sa.Integer(), nullable=False),
        sa.Column("passing_points", sa.Integer(), nullable=False),
        sa.Column("max_submissions", sa.Integer(), nullable=False),
        *record_columns(),
        sa.ForeignKeyConstraint(
            ["lesson_id", "course_id", "organization_id"],
            ["lessons.id", "lessons.course_id", "lessons.organization_id"],
            name="fk_learning_assignment_lesson_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lesson_id", "position"),
        sa.UniqueConstraint("id", "course_id", "organization_id"),
        sa.CheckConstraint("position > 0", name="learning_assignment_position"),
        sa.CheckConstraint("maximum_points BETWEEN 1 AND 1000", name="learning_assignment_maximum"),
        sa.CheckConstraint(
            "passing_points BETWEEN 0 AND maximum_points", name="learning_assignment_passing"
        ),
        sa.CheckConstraint(
            "max_submissions BETWEEN 1 AND 10", name="learning_assignment_submission_limit"
        ),
    )
    for column in ("organization_id", "course_id", "lesson_id"):
        op.create_index(f"ix_learning_assignments_{column}", "learning_assignments", [column])

    op.create_table(
        "assignment_submissions",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("course_enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("assignment_id", sa.Uuid(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        *record_columns(),
        sa.ForeignKeyConstraint(
            ["course_enrollment_id", "course_id", "organization_id"],
            [
                "course_enrollments.id",
                "course_enrollments.course_id",
                "course_enrollments.organization_id",
            ],
            name="fk_assignment_submission_enrollment_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["assignment_id", "course_id", "organization_id"],
            [
                "learning_assignments.id",
                "learning_assignments.course_id",
                "learning_assignments.organization_id",
            ],
            name="fk_assignment_submission_definition_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_enrollment_id", "assignment_id", "revision"),
        sa.UniqueConstraint("id", "assignment_id", "course_id", "organization_id"),
        sa.CheckConstraint("revision > 0", name="assignment_submission_revision"),
        sa.CheckConstraint(
            "char_length(response_text) BETWEEN 1 AND 10000", name="assignment_submission_text"
        ),
    )
    for column in ("organization_id", "course_id", "course_enrollment_id", "assignment_id"):
        op.create_index(f"ix_assignment_submissions_{column}", "assignment_submissions", [column])
    op.create_index(
        "ix_assignment_submission_review",
        "assignment_submissions",
        ["assignment_id", "course_enrollment_id", "revision"],
    )

    op.create_table(
        "assignment_grades",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("assignment_id", sa.Uuid(), nullable=False),
        sa.Column("submission_id", sa.Uuid(), nullable=False),
        sa.Column("grader_user_id", sa.Uuid(), nullable=False),
        sa.Column("score_points", sa.Integer(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=False),
        *record_columns(),
        sa.ForeignKeyConstraint(
            ["submission_id", "assignment_id", "course_id", "organization_id"],
            [
                "assignment_submissions.id",
                "assignment_submissions.assignment_id",
                "assignment_submissions.course_id",
                "assignment_submissions.organization_id",
            ],
            name="fk_assignment_grade_submission_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["grader_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("submission_id"),
        sa.CheckConstraint("score_points BETWEEN 0 AND 1000", name="assignment_grade_score"),
        sa.CheckConstraint(
            "char_length(feedback) BETWEEN 1 AND 5000", name="assignment_grade_feedback"
        ),
    )
    for column in (
        "organization_id",
        "course_id",
        "assignment_id",
        "submission_id",
        "grader_user_id",
    ):
        op.create_index(f"ix_assignment_grades_{column}", "assignment_grades", [column])

    op.execute("""
        CREATE TRIGGER trg_learning_assignment_draft_only
        BEFORE INSERT OR UPDATE OR DELETE ON learning_assignments
        FOR EACH ROW EXECUTE FUNCTION protect_published_course_structure();

        CREATE FUNCTION protect_assignment_submission_evidence() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP <> 'INSERT' THEN
            RAISE EXCEPTION 'assignment submission evidence is immutable';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_assignment_submission_immutable
        BEFORE UPDATE OR DELETE ON assignment_submissions
        FOR EACH ROW EXECUTE FUNCTION protect_assignment_submission_evidence();

        CREATE FUNCTION validate_assignment_submission_revision() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE allowed_revisions integer;
        DECLARE latest_revision integer;
        BEGIN
          SELECT max_submissions
          INTO allowed_revisions
          FROM learning_assignments
          WHERE id = NEW.assignment_id;

          SELECT COALESCE(MAX(revision), 0)
          INTO latest_revision
          FROM assignment_submissions
          WHERE assignment_id = NEW.assignment_id
            AND course_enrollment_id = NEW.course_enrollment_id;

          IF NEW.revision > allowed_revisions
             OR NEW.revision <> latest_revision + 1 THEN
            RAISE EXCEPTION 'assignment submission revision is invalid';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_assignment_submission_revision_validate
        BEFORE INSERT ON assignment_submissions
        FOR EACH ROW EXECUTE FUNCTION validate_assignment_submission_revision();

        CREATE FUNCTION validate_assignment_grade() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE assignment_max integer;
        DECLARE assignment_pass integer;
        BEGIN
          SELECT maximum_points, passing_points
          INTO assignment_max, assignment_pass
          FROM learning_assignments
          WHERE id = NEW.assignment_id;
          IF NEW.score_points > assignment_max
             OR NEW.passed <> (NEW.score_points >= assignment_pass) THEN
            RAISE EXCEPTION 'assignment grade is invalid';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_assignment_grade_validate
        BEFORE INSERT ON assignment_grades
        FOR EACH ROW EXECUTE FUNCTION validate_assignment_grade();

        CREATE TRIGGER trg_assignment_grade_immutable
        BEFORE UPDATE OR DELETE ON assignment_grades
        FOR EACH ROW EXECUTE FUNCTION protect_assignment_submission_evidence();
    """)


def downgrade() -> None:
    op.execute("""
        DROP TRIGGER trg_assignment_grade_immutable ON assignment_grades;
        DROP TRIGGER trg_assignment_grade_validate ON assignment_grades;
        DROP FUNCTION validate_assignment_grade;
        DROP TRIGGER IF EXISTS trg_assignment_submission_revision_validate
          ON assignment_submissions;
        DROP FUNCTION IF EXISTS validate_assignment_submission_revision;
        DROP TRIGGER trg_assignment_submission_immutable ON assignment_submissions;
        DROP FUNCTION protect_assignment_submission_evidence;
        DROP TRIGGER trg_learning_assignment_draft_only ON learning_assignments;
    """)
    op.drop_table("assignment_grades")
    op.drop_table("assignment_submissions")
    op.drop_table("learning_assignments")
    op.execute("""
        DELETE FROM role_permissions WHERE permission_code = 'lms.assessment.grade';
        DELETE FROM permissions WHERE code = 'lms.assessment.grade';
    """)
