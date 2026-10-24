"""Typed learning evidence; imported with its migration when integration is registered."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.identity.models import Record


class AssignmentFileRule(Record, Base):
    __tablename__ = "assignment_file_rules"
    organization_id: Mapped[UUID] = mapped_column()
    course_id: Mapped[UUID] = mapped_column()
    assignment_id: Mapped[UUID] = mapped_column(unique=True)
    policy_id: Mapped[UUID] = mapped_column()
    purpose: Mapped[str] = mapped_column(String(32), default="assignment_submission")
    minimum_files: Mapped[int] = mapped_column(Integer)
    maximum_files: Mapped[int] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (
        ForeignKeyConstraint(
            ["assignment_id", "course_id", "organization_id"],
            [
                "learning_assignments.id",
                "learning_assignments.course_id",
                "learning_assignments.organization_id",
            ],
            ondelete="RESTRICT",
            name="fk_assignment_file_rule_definition",
        ),
        ForeignKeyConstraint(
            ["policy_id", "organization_id", "purpose"],
            ["file_policies.id", "file_policies.organization_id", "file_policies.purpose"],
            ondelete="RESTRICT",
            name="fk_assignment_file_rule_policy",
        ),
        CheckConstraint("purpose = 'assignment_submission'", name="assignment_file_rule_purpose"),
        CheckConstraint(
            "minimum_files >= 0 AND maximum_files BETWEEN 1 AND 100 "
            "AND minimum_files <= maximum_files",
            name="assignment_file_rule_count",
        ),
        CheckConstraint("version > 0", name="assignment_file_rule_version"),
    )


class AssignmentFile(Record, Base):
    __tablename__ = "assignment_files"
    organization_id: Mapped[UUID] = mapped_column()
    course_id: Mapped[UUID] = mapped_column()
    course_enrollment_id: Mapped[UUID] = mapped_column()
    assignment_id: Mapped[UUID] = mapped_column()
    owner_person_id: Mapped[UUID] = mapped_column()
    client_request_id: Mapped[UUID] = mapped_column()
    file_id: Mapped[UUID] = mapped_column(unique=True)
    purpose: Mapped[str] = mapped_column(String(32), default="assignment_submission")
    target_revision: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(16), default="active")
    version: Mapped[int] = mapped_column(Integer, default=1)
    submission_id: Mapped[UUID | None] = mapped_column(nullable=True)
    frozen_file_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    frozen_storage_version: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    frozen_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    frozen_byte_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        UniqueConstraint("organization_id", "client_request_id"),
        ForeignKeyConstraint(
            ["assignment_id", "course_id", "organization_id"],
            [
                "learning_assignments.id",
                "learning_assignments.course_id",
                "learning_assignments.organization_id",
            ],
            ondelete="RESTRICT",
            name="fk_assignment_file_definition",
        ),
        ForeignKeyConstraint(
            ["course_enrollment_id", "course_id", "organization_id"],
            [
                "course_enrollments.id",
                "course_enrollments.course_id",
                "course_enrollments.organization_id",
            ],
            ondelete="RESTRICT",
            name="fk_assignment_file_enrollment",
        ),
        ForeignKeyConstraint(
            ["file_id", "organization_id", "owner_person_id", "purpose", "id"],
            [
                "file_objects.id",
                "file_objects.organization_id",
                "file_objects.owner_person_id",
                "file_objects.purpose",
                "file_objects.resource_id",
            ],
            ondelete="RESTRICT",
            name="fk_assignment_file_object",
        ),
        ForeignKeyConstraint(
            [
                "submission_id",
                "course_enrollment_id",
                "assignment_id",
                "course_id",
                "organization_id",
            ],
            [
                "assignment_submissions.id",
                "assignment_submissions.course_enrollment_id",
                "assignment_submissions.assignment_id",
                "assignment_submissions.course_id",
                "assignment_submissions.organization_id",
            ],
            ondelete="RESTRICT",
            name="fk_assignment_file_submission",
        ),
        CheckConstraint("purpose = 'assignment_submission'", name="assignment_file_purpose"),
        CheckConstraint(
            "state IN ('active','removed','submitted') AND version > 0 "
            "AND target_revision BETWEEN 1 AND 10",
            name="assignment_file_state",
        ),
        CheckConstraint(
            "(state = 'submitted' AND submission_id IS NOT NULL "
            "AND frozen_file_version IS NOT NULL AND frozen_storage_version IS NOT NULL "
            "AND frozen_sha256 IS NOT NULL AND frozen_byte_size IS NOT NULL "
            "AND frozen_byte_size > 0 AND frozen_at IS NOT NULL) "
            "OR (state <> 'submitted' AND submission_id IS NULL AND frozen_file_version IS NULL "
            "AND frozen_storage_version IS NULL AND frozen_sha256 IS NULL "
            "AND frozen_byte_size IS NULL AND frozen_at IS NULL)",
            name="assignment_file_frozen_evidence",
        ),
    )


class MaterialFile(Record, Base):
    __tablename__ = "lesson_material_files"
    organization_id: Mapped[UUID] = mapped_column()
    course_id: Mapped[UUID] = mapped_column()
    material_id: Mapped[UUID] = mapped_column(unique=True)
    owner_person_id: Mapped[UUID] = mapped_column()
    client_request_id: Mapped[UUID] = mapped_column()
    request_digest: Mapped[str] = mapped_column(String(64))
    file_id: Mapped[UUID] = mapped_column(unique=True)
    purpose: Mapped[str] = mapped_column(String(32), default="lms_material")
    state: Mapped[str] = mapped_column(String(16), default="active")
    version: Mapped[int] = mapped_column(Integer, default=1)
    frozen_file_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    frozen_storage_version: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    frozen_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    frozen_byte_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        UniqueConstraint("organization_id", "client_request_id"),
        ForeignKeyConstraint(
            ["material_id", "course_id", "organization_id"],
            [
                "lesson_materials.id",
                "lesson_materials.course_id",
                "lesson_materials.organization_id",
            ],
            ondelete="RESTRICT",
            name="fk_material_file_material",
        ),
        ForeignKeyConstraint(
            ["file_id", "organization_id", "owner_person_id", "purpose", "material_id"],
            [
                "file_objects.id",
                "file_objects.organization_id",
                "file_objects.owner_person_id",
                "file_objects.purpose",
                "file_objects.resource_id",
            ],
            ondelete="RESTRICT",
            name="fk_material_file_object",
        ),
        CheckConstraint("purpose = 'lms_material'", name="material_file_purpose"),
        CheckConstraint(
            "state IN ('active','removed') AND version > 0 "
            "AND (state <> 'removed' OR frozen_at IS NULL)",
            name="material_file_state",
        ),
        CheckConstraint(
            "(frozen_at IS NULL AND frozen_file_version IS NULL AND frozen_storage_version IS NULL "
            "AND frozen_sha256 IS NULL AND frozen_byte_size IS NULL) OR (frozen_at IS NOT NULL "
            "AND frozen_file_version IS NOT NULL AND frozen_file_version > 0 "
            "AND frozen_storage_version IS NOT NULL AND frozen_sha256 IS NOT NULL "
            "AND frozen_byte_size IS NOT NULL AND frozen_byte_size > 0)",
            name="material_file_frozen_evidence",
        ),
    )
