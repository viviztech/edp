"""L02.1 quizzes, attempts, and automatic grading."""

# ruff: noqa: E501

import sqlalchemy as sa
from alembic import op

revision = "b2a8d4e6f901"
down_revision = "a19d7a38e40b"
branch_labels = None
depends_on = None


def record_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    for code in ("lms.assessment.view", "lms.assessment.manage"):
        op.execute(
            sa.text(
                "INSERT INTO permissions (code) VALUES (:code) ON CONFLICT DO NOTHING"
            ).bindparams(code=code)
        )
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_code)
        SELECT roles.id, permissions.code
        FROM roles CROSS JOIN permissions
        WHERE roles.name IN ('Super Admin','Program Director','Program Manager')
          AND permissions.code IN ('lms.assessment.view','lms.assessment.manage')
        ON CONFLICT DO NOTHING
    """)
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_code)
        SELECT roles.id, 'lms.assessment.view'
        FROM roles
        WHERE roles.name = 'Trainer'
        ON CONFLICT DO NOTHING
    """)

    op.create_table(
        "quizzes",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("lesson_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title_en", sa.String(200), nullable=False),
        sa.Column("title_ta", sa.String(200), nullable=False),
        sa.Column("instructions_en", sa.Text(), nullable=False),
        sa.Column("instructions_ta", sa.Text(), nullable=False),
        sa.Column("passing_percent", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        *record_columns(),
        sa.ForeignKeyConstraint(
            ["lesson_id", "course_id", "organization_id"],
            ["lessons.id", "lessons.course_id", "lessons.organization_id"],
            name="fk_quiz_lesson_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lesson_id", "position"),
        sa.UniqueConstraint("id", "course_id", "organization_id"),
        sa.CheckConstraint("position > 0", name="quiz_position"),
        sa.CheckConstraint("passing_percent BETWEEN 0 AND 100", name="quiz_passing_percent"),
        sa.CheckConstraint("max_attempts BETWEEN 1 AND 10", name="quiz_max_attempts"),
    )
    for column in ("organization_id", "course_id", "lesson_id"):
        op.create_index(f"ix_quizzes_{column}", "quizzes", [column])

    op.create_table(
        "quiz_questions",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("quiz_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("prompt_en", sa.Text(), nullable=False),
        sa.Column("prompt_ta", sa.Text(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        *record_columns(),
        sa.ForeignKeyConstraint(
            ["quiz_id", "course_id", "organization_id"],
            ["quizzes.id", "quizzes.course_id", "quizzes.organization_id"],
            name="fk_quiz_question_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("quiz_id", "position"),
        sa.UniqueConstraint("id", "quiz_id", "course_id", "organization_id"),
        sa.CheckConstraint("position > 0", name="quiz_question_position"),
        sa.CheckConstraint("points BETWEEN 1 AND 100", name="quiz_question_points"),
    )
    for column in ("organization_id", "course_id", "quiz_id"):
        op.create_index(f"ix_quiz_questions_{column}", "quiz_questions", [column])

    op.create_table(
        "quiz_choices",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("quiz_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("label_en", sa.String(500), nullable=False),
        sa.Column("label_ta", sa.String(500), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        *record_columns(),
        sa.ForeignKeyConstraint(
            ["question_id", "quiz_id", "course_id", "organization_id"],
            [
                "quiz_questions.id",
                "quiz_questions.quiz_id",
                "quiz_questions.course_id",
                "quiz_questions.organization_id",
            ],
            name="fk_quiz_choice_question_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("question_id", "position"),
        sa.UniqueConstraint("id", "question_id", "quiz_id", "course_id", "organization_id"),
        sa.CheckConstraint("position > 0", name="quiz_choice_position"),
    )
    for column in ("organization_id", "course_id", "quiz_id", "question_id"):
        op.create_index(f"ix_quiz_choices_{column}", "quiz_choices", [column])

    op.create_table(
        "quiz_attempts",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("course_enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("quiz_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("score_points", sa.Integer(), nullable=False),
        sa.Column("maximum_points", sa.Integer(), nullable=False),
        sa.Column("percent", sa.Integer(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        *record_columns(),
        sa.ForeignKeyConstraint(
            ["course_enrollment_id", "course_id", "organization_id"],
            [
                "course_enrollments.id",
                "course_enrollments.course_id",
                "course_enrollments.organization_id",
            ],
            name="fk_quiz_attempt_enrollment_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["quiz_id", "course_id", "organization_id"],
            ["quizzes.id", "quizzes.course_id", "quizzes.organization_id"],
            name="fk_quiz_attempt_quiz_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_enrollment_id", "quiz_id", "attempt_number"),
        sa.UniqueConstraint("id", "quiz_id", "course_id", "organization_id"),
        sa.CheckConstraint("attempt_number > 0", name="quiz_attempt_number"),
        sa.CheckConstraint("maximum_points > 0", name="quiz_attempt_maximum"),
        sa.CheckConstraint("score_points BETWEEN 0 AND maximum_points", name="quiz_attempt_score"),
        sa.CheckConstraint("percent BETWEEN 0 AND 100", name="quiz_attempt_percent"),
    )
    for column in ("organization_id", "course_id", "course_enrollment_id", "quiz_id"):
        op.create_index(f"ix_quiz_attempts_{column}", "quiz_attempts", [column])
    op.create_index(
        "ix_quiz_attempt_learner",
        "quiz_attempts",
        ["course_enrollment_id", "quiz_id", "attempt_number"],
    )

    op.create_table(
        "quiz_attempt_answers",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("quiz_id", sa.Uuid(), nullable=False),
        sa.Column("quiz_attempt_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("selected_choice_id", sa.Uuid(), nullable=False),
        sa.Column("question_points", sa.Integer(), nullable=False),
        sa.Column("points_awarded", sa.Integer(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        *record_columns(),
        sa.ForeignKeyConstraint(
            ["quiz_attempt_id", "quiz_id", "course_id", "organization_id"],
            [
                "quiz_attempts.id",
                "quiz_attempts.quiz_id",
                "quiz_attempts.course_id",
                "quiz_attempts.organization_id",
            ],
            name="fk_quiz_answer_attempt_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["selected_choice_id", "question_id", "quiz_id", "course_id", "organization_id"],
            [
                "quiz_choices.id",
                "quiz_choices.question_id",
                "quiz_choices.quiz_id",
                "quiz_choices.course_id",
                "quiz_choices.organization_id",
            ],
            name="fk_quiz_answer_choice_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("quiz_attempt_id", "question_id"),
        sa.CheckConstraint("question_points BETWEEN 1 AND 100", name="quiz_answer_points"),
        sa.CheckConstraint(
            "points_awarded BETWEEN 0 AND question_points", name="quiz_answer_awarded"
        ),
    )
    for column in (
        "organization_id",
        "course_id",
        "quiz_id",
        "quiz_attempt_id",
        "question_id",
        "selected_choice_id",
    ):
        op.create_index(f"ix_quiz_attempt_answers_{column}", "quiz_attempt_answers", [column])

    op.execute("""
        CREATE TRIGGER trg_quiz_draft_only
        BEFORE INSERT OR UPDATE OR DELETE ON quizzes
        FOR EACH ROW EXECUTE FUNCTION protect_published_course_structure();
        CREATE TRIGGER trg_quiz_question_draft_only
        BEFORE INSERT OR UPDATE OR DELETE ON quiz_questions
        FOR EACH ROW EXECUTE FUNCTION protect_published_course_structure();
        CREATE TRIGGER trg_quiz_choice_draft_only
        BEFORE INSERT OR UPDATE OR DELETE ON quiz_choices
        FOR EACH ROW EXECUTE FUNCTION protect_published_course_structure();

        CREATE FUNCTION validate_course_quiz_structure() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF OLD.state = 'draft' AND NEW.state <> 'draft' AND (
            EXISTS (
              SELECT 1 FROM quizzes q
              WHERE q.course_id = NEW.id
                AND NOT EXISTS (SELECT 1 FROM quiz_questions qq WHERE qq.quiz_id = q.id)
            )
            OR EXISTS (
              SELECT 1 FROM quiz_questions qq
              WHERE qq.course_id = NEW.id
                AND (
                  (SELECT count(*) FROM quiz_choices qc WHERE qc.question_id = qq.id) < 2
                  OR (SELECT count(*) FROM quiz_choices qc WHERE qc.question_id = qq.id AND qc.is_correct) <> 1
                )
            )
          ) THEN
            RAISE EXCEPTION 'quiz structure is incomplete';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_course_quiz_structure
        BEFORE UPDATE ON courses
        FOR EACH ROW EXECUTE FUNCTION validate_course_quiz_structure();

        CREATE FUNCTION protect_quiz_attempt_evidence() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP <> 'INSERT' THEN
            RAISE EXCEPTION 'submitted quiz attempt evidence is immutable';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_quiz_attempt_immutable
        BEFORE UPDATE OR DELETE ON quiz_attempts
        FOR EACH ROW EXECUTE FUNCTION protect_quiz_attempt_evidence();
        CREATE TRIGGER trg_quiz_answer_immutable
        BEFORE UPDATE OR DELETE ON quiz_attempt_answers
        FOR EACH ROW EXECUTE FUNCTION protect_quiz_attempt_evidence();
    """)


def downgrade() -> None:
    op.execute("""
        DROP TRIGGER trg_quiz_answer_immutable ON quiz_attempt_answers;
        DROP TRIGGER trg_quiz_attempt_immutable ON quiz_attempts;
        DROP FUNCTION protect_quiz_attempt_evidence;
        DROP TRIGGER trg_course_quiz_structure ON courses;
        DROP FUNCTION validate_course_quiz_structure;
        DROP TRIGGER trg_quiz_choice_draft_only ON quiz_choices;
        DROP TRIGGER trg_quiz_question_draft_only ON quiz_questions;
        DROP TRIGGER trg_quiz_draft_only ON quizzes;
    """)
    for table in (
        "quiz_attempt_answers",
        "quiz_attempts",
        "quiz_choices",
        "quiz_questions",
        "quizzes",
    ):
        op.drop_table(table)
    op.execute("""
        DELETE FROM role_permissions
        WHERE permission_code IN ('lms.assessment.view','lms.assessment.manage')
    """)
    op.execute("""
        DELETE FROM permissions
        WHERE code IN ('lms.assessment.view','lms.assessment.manage')
    """)
