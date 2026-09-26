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
