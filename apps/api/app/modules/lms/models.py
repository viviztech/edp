from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.identity.models import Record, now


class Course(Record, Base):
    __tablename__ = "courses"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    code: Mapped[str] = mapped_column(String(60))
    title_en: Mapped[str] = mapped_column(String(200))
    title_ta: Mapped[str] = mapped_column(String(200))
    description_en: Mapped[str] = mapped_column(Text)
    description_ta: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(16), default="draft")
    completion_rule: Mapped[str] = mapped_column(String(24), default="all_lessons")
    minimum_lessons: Mapped[int | None] = mapped_column(Integer, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        UniqueConstraint("organization_id", "code"),
        UniqueConstraint("id", "organization_id"),
        CheckConstraint("state IN ('draft','published','archived')", name="course_state"),
        CheckConstraint(
            "completion_rule IN ('all_lessons','minimum_lessons')", name="course_completion_rule"
        ),
        CheckConstraint(
            "(completion_rule = 'all_lessons' AND minimum_lessons IS NULL) OR "
            "(completion_rule = 'minimum_lessons' AND minimum_lessons > 0)",
            name="course_completion_rule_value",
        ),
        CheckConstraint("version > 0", name="course_version"),
        CheckConstraint(
            "(state = 'draft' AND published_at IS NULL) OR "
            "(state IN ('published','archived') AND published_at IS NOT NULL)",
            name="course_publication_evidence",
        ),
        Index("ix_course_scope_state", "organization_id", "state", "id"),
    )


class CourseModule(Record, Base):
    __tablename__ = "course_modules"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    course_id: Mapped[UUID] = mapped_column(index=True)
    position: Mapped[int] = mapped_column(Integer)
    title_en: Mapped[str] = mapped_column(String(200))
    title_ta: Mapped[str] = mapped_column(String(200))
    __table_args__ = (
        ForeignKeyConstraint(
            ["course_id", "organization_id"],
            ["courses.id", "courses.organization_id"],
            name="fk_course_module_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("course_id", "position"),
        UniqueConstraint("id", "course_id", "organization_id"),
        CheckConstraint("position > 0", name="course_module_position"),
    )


class Lesson(Record, Base):
    __tablename__ = "lessons"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    course_id: Mapped[UUID] = mapped_column(index=True)
    module_id: Mapped[UUID] = mapped_column(index=True)
    position: Mapped[int] = mapped_column(Integer)
    title_en: Mapped[str] = mapped_column(String(200))
    title_ta: Mapped[str] = mapped_column(String(200))
    body_en: Mapped[str] = mapped_column(Text)
    body_ta: Mapped[str] = mapped_column(Text)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    __table_args__ = (
        ForeignKeyConstraint(
            ["module_id", "course_id", "organization_id"],
            ["course_modules.id", "course_modules.course_id", "course_modules.organization_id"],
            name="fk_lesson_module_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("module_id", "position"),
        UniqueConstraint("id", "course_id", "organization_id"),
        CheckConstraint("position > 0", name="lesson_position"),
        CheckConstraint("duration_minutes IS NULL OR duration_minutes > 0", name="lesson_duration"),
    )


class LessonMaterial(Record, Base):
    __tablename__ = "lesson_materials"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    course_id: Mapped[UUID] = mapped_column(index=True)
    lesson_id: Mapped[UUID] = mapped_column(index=True)
    position: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(16))
    label_en: Mapped[str] = mapped_column(String(200))
    label_ta: Mapped[str] = mapped_column(String(200))
    provider_key: Mapped[str] = mapped_column(String(500))
    is_private: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (
        ForeignKeyConstraint(
            ["lesson_id", "course_id", "organization_id"],
            ["lessons.id", "lessons.course_id", "lessons.organization_id"],
            name="fk_lesson_material_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("lesson_id", "position"),
        CheckConstraint("position > 0", name="lesson_material_position"),
        CheckConstraint("kind IN ('video','document','link')", name="lesson_material_kind"),
        CheckConstraint("is_private = true", name="lesson_material_private"),
    )


class LessonPrerequisite(Record, Base):
    __tablename__ = "lesson_prerequisites"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    course_id: Mapped[UUID] = mapped_column(index=True)
    lesson_id: Mapped[UUID] = mapped_column(index=True)
    prerequisite_lesson_id: Mapped[UUID] = mapped_column(index=True)
    __table_args__ = (
        ForeignKeyConstraint(
            ["lesson_id", "course_id", "organization_id"],
            ["lessons.id", "lessons.course_id", "lessons.organization_id"],
            name="fk_lesson_prerequisite_target_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["prerequisite_lesson_id", "course_id", "organization_id"],
            ["lessons.id", "lessons.course_id", "lessons.organization_id"],
            name="fk_lesson_prerequisite_required_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("lesson_id", "prerequisite_lesson_id"),
        CheckConstraint("lesson_id <> prerequisite_lesson_id", name="lesson_prerequisite_distinct"),
        Index("ix_lesson_prerequisite_course", "course_id", "lesson_id"),
    )


class CohortCourse(Record, Base):
    __tablename__ = "cohort_courses"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    cohort_id: Mapped[UUID] = mapped_column(index=True)
    course_id: Mapped[UUID] = mapped_column(index=True)
    position: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        ForeignKeyConstraint(
            ["cohort_id", "organization_id"],
            ["cohorts.id", "cohorts.organization_id"],
            name="fk_cohort_course_cohort_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["course_id", "organization_id"],
            ["courses.id", "courses.organization_id"],
            name="fk_cohort_course_course_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("cohort_id", "course_id"),
        UniqueConstraint("cohort_id", "position"),
        UniqueConstraint("id", "organization_id"),
        CheckConstraint("position > 0", name="cohort_course_position"),
        Index("ix_cohort_course_order", "cohort_id", "position", "id"),
    )


class CourseEnrollment(Record, Base):
    __tablename__ = "course_enrollments"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    enrollment_id: Mapped[UUID] = mapped_column(index=True)
    course_id: Mapped[UUID] = mapped_column(index=True)
    status: Mapped[str] = mapped_column(String(16), default="in_progress")
    version: Mapped[int] = mapped_column(Integer, default=1)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["enrollment_id", "organization_id"],
            ["enrollments.id", "enrollments.organization_id"],
            name="fk_course_enrollment_enrollment_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["course_id", "organization_id"],
            ["courses.id", "courses.organization_id"],
            name="fk_course_enrollment_course_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("enrollment_id", "course_id"),
        UniqueConstraint("id", "organization_id"),
        UniqueConstraint("id", "course_id", "organization_id"),
        CheckConstraint("status IN ('in_progress','completed')", name="course_enrollment_status"),
        CheckConstraint("version > 0", name="course_enrollment_version"),
        CheckConstraint(
            "(status = 'in_progress' AND completed_at IS NULL) OR "
            "(status = 'completed' AND completed_at IS NOT NULL)",
            name="course_enrollment_completion_evidence",
        ),
    )


class LessonProgress(Record, Base):
    __tablename__ = "lesson_progress"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    course_id: Mapped[UUID] = mapped_column(index=True)
    course_enrollment_id: Mapped[UUID] = mapped_column(index=True)
    lesson_id: Mapped[UUID] = mapped_column(index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["course_enrollment_id", "course_id", "organization_id"],
            [
                "course_enrollments.id",
                "course_enrollments.course_id",
                "course_enrollments.organization_id",
            ],
            name="fk_lesson_progress_enrollment_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["lesson_id", "course_id", "organization_id"],
            ["lessons.id", "lessons.course_id", "lessons.organization_id"],
            name="fk_lesson_progress_lesson_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("course_enrollment_id", "lesson_id"),
        Index("ix_lesson_progress_rollup", "course_enrollment_id", "course_id"),
    )


class Quiz(Record, Base):
    __tablename__ = "quizzes"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    course_id: Mapped[UUID] = mapped_column(index=True)
    lesson_id: Mapped[UUID] = mapped_column(index=True)
    position: Mapped[int] = mapped_column(Integer)
    title_en: Mapped[str] = mapped_column(String(200))
    title_ta: Mapped[str] = mapped_column(String(200))
    instructions_en: Mapped[str] = mapped_column(Text)
    instructions_ta: Mapped[str] = mapped_column(Text)
    passing_percent: Mapped[int] = mapped_column(Integer)
    max_attempts: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        ForeignKeyConstraint(
            ["lesson_id", "course_id", "organization_id"],
            ["lessons.id", "lessons.course_id", "lessons.organization_id"],
            name="fk_quiz_lesson_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("lesson_id", "position"),
        UniqueConstraint("id", "course_id", "organization_id"),
        CheckConstraint("position > 0", name="quiz_position"),
        CheckConstraint("passing_percent BETWEEN 0 AND 100", name="quiz_passing_percent"),
        CheckConstraint("max_attempts BETWEEN 1 AND 10", name="quiz_max_attempts"),
    )


class QuizQuestion(Record, Base):
    __tablename__ = "quiz_questions"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    course_id: Mapped[UUID] = mapped_column(index=True)
    quiz_id: Mapped[UUID] = mapped_column(index=True)
    position: Mapped[int] = mapped_column(Integer)
    prompt_en: Mapped[str] = mapped_column(Text)
    prompt_ta: Mapped[str] = mapped_column(Text)
    points: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        ForeignKeyConstraint(
            ["quiz_id", "course_id", "organization_id"],
            ["quizzes.id", "quizzes.course_id", "quizzes.organization_id"],
            name="fk_quiz_question_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("quiz_id", "position"),
        UniqueConstraint("id", "quiz_id", "course_id", "organization_id"),
        CheckConstraint("position > 0", name="quiz_question_position"),
        CheckConstraint("points BETWEEN 1 AND 100", name="quiz_question_points"),
    )


class QuizChoice(Record, Base):
    __tablename__ = "quiz_choices"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    course_id: Mapped[UUID] = mapped_column(index=True)
    quiz_id: Mapped[UUID] = mapped_column(index=True)
    question_id: Mapped[UUID] = mapped_column(index=True)
    position: Mapped[int] = mapped_column(Integer)
    label_en: Mapped[str] = mapped_column(String(500))
    label_ta: Mapped[str] = mapped_column(String(500))
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (
        ForeignKeyConstraint(
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
        UniqueConstraint("question_id", "position"),
        UniqueConstraint("id", "question_id", "quiz_id", "course_id", "organization_id"),
        CheckConstraint("position > 0", name="quiz_choice_position"),
    )


class QuizAttempt(Record, Base):
    __tablename__ = "quiz_attempts"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    course_id: Mapped[UUID] = mapped_column(index=True)
    course_enrollment_id: Mapped[UUID] = mapped_column(index=True)
    quiz_id: Mapped[UUID] = mapped_column(index=True)
    attempt_number: Mapped[int] = mapped_column(Integer)
    score_points: Mapped[int] = mapped_column(Integer)
    maximum_points: Mapped[int] = mapped_column(Integer)
    percent: Mapped[int] = mapped_column(Integer)
    passed: Mapped[bool] = mapped_column(Boolean)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["course_enrollment_id", "course_id", "organization_id"],
            [
                "course_enrollments.id",
                "course_enrollments.course_id",
                "course_enrollments.organization_id",
            ],
            name="fk_quiz_attempt_enrollment_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["quiz_id", "course_id", "organization_id"],
            ["quizzes.id", "quizzes.course_id", "quizzes.organization_id"],
            name="fk_quiz_attempt_quiz_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("course_enrollment_id", "quiz_id", "attempt_number"),
        UniqueConstraint("id", "quiz_id", "course_id", "organization_id"),
        CheckConstraint("attempt_number > 0", name="quiz_attempt_number"),
        CheckConstraint("maximum_points > 0", name="quiz_attempt_maximum"),
        CheckConstraint("score_points BETWEEN 0 AND maximum_points", name="quiz_attempt_score"),
        CheckConstraint("percent BETWEEN 0 AND 100", name="quiz_attempt_percent"),
        Index(
            "ix_quiz_attempt_learner",
            "course_enrollment_id",
            "quiz_id",
            "attempt_number",
        ),
    )


class QuizAttemptAnswer(Record, Base):
    __tablename__ = "quiz_attempt_answers"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    course_id: Mapped[UUID] = mapped_column(index=True)
    quiz_id: Mapped[UUID] = mapped_column(index=True)
    quiz_attempt_id: Mapped[UUID] = mapped_column(index=True)
    question_id: Mapped[UUID] = mapped_column(index=True)
    selected_choice_id: Mapped[UUID] = mapped_column(index=True)
    question_points: Mapped[int] = mapped_column(Integer)
    points_awarded: Mapped[int] = mapped_column(Integer)
    is_correct: Mapped[bool] = mapped_column(Boolean)
    __table_args__ = (
        ForeignKeyConstraint(
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
        ForeignKeyConstraint(
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
        UniqueConstraint("quiz_attempt_id", "question_id"),
        CheckConstraint("question_points BETWEEN 1 AND 100", name="quiz_answer_points"),
        CheckConstraint("points_awarded BETWEEN 0 AND question_points", name="quiz_answer_awarded"),
    )


class LearningAssignment(Record, Base):
    __tablename__ = "learning_assignments"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    course_id: Mapped[UUID] = mapped_column(index=True)
    lesson_id: Mapped[UUID] = mapped_column(index=True)
    position: Mapped[int] = mapped_column(Integer)
    title_en: Mapped[str] = mapped_column(String(200))
    title_ta: Mapped[str] = mapped_column(String(200))
    instructions_en: Mapped[str] = mapped_column(Text)
    instructions_ta: Mapped[str] = mapped_column(Text)
    maximum_points: Mapped[int] = mapped_column(Integer)
    passing_points: Mapped[int] = mapped_column(Integer)
    max_submissions: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        ForeignKeyConstraint(
            ["lesson_id", "course_id", "organization_id"],
            ["lessons.id", "lessons.course_id", "lessons.organization_id"],
            name="fk_learning_assignment_lesson_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("lesson_id", "position"),
        UniqueConstraint("id", "course_id", "organization_id"),
        CheckConstraint("position > 0", name="learning_assignment_position"),
        CheckConstraint("maximum_points BETWEEN 1 AND 1000", name="learning_assignment_maximum"),
        CheckConstraint(
            "passing_points BETWEEN 0 AND maximum_points",
            name="learning_assignment_passing",
        ),
        CheckConstraint(
            "max_submissions BETWEEN 1 AND 10",
            name="learning_assignment_submission_limit",
        ),
    )


class AssignmentSubmission(Record, Base):
    __tablename__ = "assignment_submissions"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    course_id: Mapped[UUID] = mapped_column(index=True)
    course_enrollment_id: Mapped[UUID] = mapped_column(index=True)
    assignment_id: Mapped[UUID] = mapped_column(index=True)
    revision: Mapped[int] = mapped_column(Integer)
    response_text: Mapped[str] = mapped_column(Text)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["course_enrollment_id", "course_id", "organization_id"],
            [
                "course_enrollments.id",
                "course_enrollments.course_id",
                "course_enrollments.organization_id",
            ],
            name="fk_assignment_submission_enrollment_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["assignment_id", "course_id", "organization_id"],
            [
                "learning_assignments.id",
                "learning_assignments.course_id",
                "learning_assignments.organization_id",
            ],
            name="fk_assignment_submission_definition_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("course_enrollment_id", "assignment_id", "revision"),
        UniqueConstraint("id", "assignment_id", "course_id", "organization_id"),
        CheckConstraint("revision > 0", name="assignment_submission_revision"),
        CheckConstraint(
            "char_length(response_text) BETWEEN 1 AND 10000",
            name="assignment_submission_text",
        ),
        Index(
            "ix_assignment_submission_review",
            "assignment_id",
            "course_enrollment_id",
            "revision",
        ),
    )


class AssignmentGrade(Record, Base):
    __tablename__ = "assignment_grades"
    organization_id: Mapped[UUID] = mapped_column(index=True)
    course_id: Mapped[UUID] = mapped_column(index=True)
    assignment_id: Mapped[UUID] = mapped_column(index=True)
    submission_id: Mapped[UUID] = mapped_column(index=True)
    grader_user_id: Mapped[UUID] = mapped_column(index=True)
    score_points: Mapped[int] = mapped_column(Integer)
    passed: Mapped[bool] = mapped_column(Boolean)
    feedback: Mapped[str] = mapped_column(Text)
    graded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (
        ForeignKeyConstraint(
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
        ForeignKeyConstraint(["grader_user_id"], ["users.id"], ondelete="RESTRICT"),
        UniqueConstraint("submission_id"),
        CheckConstraint("score_points BETWEEN 0 AND 1000", name="assignment_grade_score"),
        CheckConstraint(
            "char_length(feedback) BETWEEN 1 AND 5000",
            name="assignment_grade_feedback",
        ),
    )
