"""Learning bindings authorize domain context before touching shared private bytes."""

import hashlib
import json
from typing import Literal, cast
from uuid import UUID, uuid4

from sqlalchemy import func, literal, select, tuple_
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.files import service as files
from app.modules.files.models import FileObject, FilePolicy
from app.modules.files.runtime import require_files_enabled
from app.modules.files.schemas import FileCreate, MediaType
from app.modules.files.storage import StoredObject
from app.modules.identity.models import User, now
from app.modules.identity.security import AuthError
from app.modules.identity.service import require_permission, throttle
from app.modules.lms import service as learning
from app.modules.lms.file_models import AssignmentFile, AssignmentFileRule, MaterialFile
from app.modules.lms.file_schemas import (
    AssignmentFileIntent,
    AssignmentFileList,
    AssignmentFileRuleCommand,
    AssignmentFileRuleView,
    AssignmentFileView,
    LearningFileEvidence,
    MaterialFileIntent,
    MaterialFileList,
    MaterialFileView,
)
from app.modules.lms.models import (
    AssignmentGrade,
    AssignmentSubmission,
    Course,
    CourseEnrollment,
    LearningAssignment,
    Lesson,
    LessonMaterial,
    LessonPrerequisite,
    LessonProgress,
)
from app.modules.programs.models import Enrollment


def _policy(db: Session, org: UUID, policy_id: UUID, purpose: str) -> FilePolicy:
    row = db.scalar(
        select(FilePolicy).where(
            FilePolicy.id == policy_id,
            FilePolicy.organization_id == org,
            FilePolicy.purpose == purpose,
        )
    )
    if row is None or row.published_at is None:
        raise AuthError("file_policy_unavailable", 409)
    return row


def _object(db: Session, org: UUID, file_id: UUID, *, lock: bool = False) -> FileObject:
    query = select(FileObject).where(FileObject.id == file_id, FileObject.organization_id == org)
    query = query.execution_options(populate_existing=True)
    row = db.scalar(query.with_for_update() if lock else query)
    if row is None:
        raise AuthError("not_found", 404)
    return row


def clean_reference(row: FileObject) -> StoredObject:
    if (
        row.state != "clean"
        or row.retention_until <= now()
        or not row.storage_version
        or row.stored_sha256 != row.expected_sha256
        or row.stored_byte_size != row.expected_byte_size
        or row.scan_storage_version != row.storage_version
        or row.scan_sha256 != row.stored_sha256
        or row.scan_byte_size != row.stored_byte_size
        or row.scanned_at is None
    ):
        raise AuthError("learning_file_unavailable", 409)
    return StoredObject(
        row.object_key,
        row.storage_version,
        row.expected_media_type,
        row.expected_byte_size,
        row.expected_sha256,
    )


def _evidence(row: AssignmentFile | MaterialFile) -> LearningFileEvidence | None:
    if row.frozen_at is None:
        return None
    if row.frozen_file_version is None or row.frozen_sha256 is None or row.frozen_byte_size is None:
        raise AuthError("file_integrity_error", 503)
    return LearningFileEvidence(
        file_id=row.file_id,
        file_version=row.frozen_file_version,
        sha256=row.frozen_sha256,
        byte_size=row.frozen_byte_size,
        frozen_at=row.frozen_at,
    )


def _pin(row: AssignmentFile | MaterialFile, file: FileObject) -> None:
    ref = clean_reference(file)
    row.frozen_file_version = file.version
    row.frozen_storage_version, row.frozen_sha256 = ref.version_id, ref.sha256
    row.frozen_byte_size, row.frozen_at = ref.byte_size, now()


def _pinned_reference(row: AssignmentFile | MaterialFile, file: FileObject) -> StoredObject:
    ref = clean_reference(file)
    if (
        row.frozen_at is None
        or not file.evidence_frozen
        or (row.frozen_storage_version, row.frozen_sha256, row.frozen_byte_size)
        != (ref.version_id, ref.sha256, ref.byte_size)
    ):
        raise AuthError("file_integrity_error", 503)
    return ref


def rule_view(db: Session, org: UUID, rule: AssignmentFileRule) -> AssignmentFileRuleView:
    policy = _policy(db, org, rule.policy_id, "assignment_submission")
    return AssignmentFileRuleView(
        policy_id=policy.id,
        minimum_files=rule.minimum_files,
        maximum_files=rule.maximum_files,
        version=rule.version,
        allowed_mime_types=cast(list[MediaType], policy.allowed_mime_types),
        max_file_bytes=min(policy.max_file_bytes, get_settings().files_max_bytes),
        notice_en=policy.notice_en,
        notice_ta=policy.notice_ta,
    )


def configure_rule(
    db: Session,
    org: UUID,
    course_id: UUID,
    assignment_id: UUID,
    actor: User,
    data: AssignmentFileRuleCommand,
    request_id: str,
) -> AssignmentFileRuleView:
    require_permission(db, actor, org, "lms.assessment.manage")
    require_permission(db, actor, org, "files.policy.view")
    course = learning._course(db, org, course_id, lock=True)
    learning._require_draft(course)
    assignment = db.scalar(
        select(LearningAssignment).where(
            LearningAssignment.id == assignment_id,
            LearningAssignment.course_id == course_id,
            LearningAssignment.organization_id == org,
        )
    )
    if assignment is None:
        raise AuthError("not_found", 404)
    policy = _policy(db, org, data.policy_id, "assignment_submission")
    if policy.state != "published" or data.maximum_files > policy.max_files:
        raise AuthError("file_policy_rejected", 422)
    rule = db.scalar(
        select(AssignmentFileRule).where(AssignmentFileRule.assignment_id == assignment_id)
    )
    if rule is None:
        if data.expected_version is not None:
            raise AuthError("version_conflict", 409)
        rule = AssignmentFileRule(
            organization_id=org,
            course_id=course_id,
            assignment_id=assignment_id,
            policy_id=policy.id,
            minimum_files=data.minimum_files,
            maximum_files=data.maximum_files,
        )
        db.add(rule)
    else:
        if rule.version != data.expected_version:
            raise AuthError("version_conflict", 409)
        rule.policy_id, rule.minimum_files = policy.id, data.minimum_files
        rule.maximum_files, rule.version = data.maximum_files, rule.version + 1
    db.flush()
    learning._audit(
        db,
        actor,
        org,
        rule.id,
        "lms.assignment.file_rule_configured",
        request_id,
        rule.version,
        "policy_id,minimum_files,maximum_files,version",
    )
    learning._commit(db)
    return rule_view(db, org, rule)


def _assignment_context(
    db: Session, org: UUID, course_id: UUID, assignment_id: UUID, actor: User, *, lock: bool = False
) -> tuple[Course, CourseEnrollment, LearningAssignment]:
    eligible = next(
        (row for row in learning._learner_courses(db, org, actor) if row[2].id == course_id), None
    )
    if eligible is None:
        raise AuthError("course_access_denied", 403)
    enrollment, _, course = eligible
    query = select(CourseEnrollment).where(
        CourseEnrollment.enrollment_id == enrollment.id, CourseEnrollment.course_id == course_id
    )
    started = db.scalar(query.with_for_update() if lock else query)
    if started is None:
        raise AuthError("course_not_started", 409)
    assignment = db.scalar(
        select(LearningAssignment).where(
            LearningAssignment.id == assignment_id,
            LearningAssignment.course_id == course_id,
            LearningAssignment.organization_id == org,
        )
    )
    if assignment is None:
        raise AuthError("not_found", 404)
    required = set(
        db.scalars(
            select(LessonPrerequisite.prerequisite_lesson_id).where(
                LessonPrerequisite.lesson_id == assignment.lesson_id,
                LessonPrerequisite.course_id == course_id,
            )
        )
    )
    completed = set(
        db.scalars(
            select(LessonProgress.lesson_id).where(
                LessonProgress.course_enrollment_id == started.id
            )
        )
    )
    if not required.issubset(completed):
        raise AuthError("lesson_prerequisite_incomplete", 409)
    return course, started, assignment


def _next_revision(
    db: Session, started: CourseEnrollment, assignment: LearningAssignment, *, writing: bool = False
) -> int:
    prior = list(
        db.scalars(
            select(AssignmentSubmission)
            .where(
                AssignmentSubmission.course_enrollment_id == started.id,
                AssignmentSubmission.assignment_id == assignment.id,
            )
            .order_by(AssignmentSubmission.revision)
        )
    )
    if writing:
        if len(prior) >= assignment.max_submissions:
            raise AuthError("assignment_submission_limit_reached", 409)
        if prior and not db.scalar(
            select(AssignmentGrade.id).where(AssignmentGrade.submission_id == prior[-1].id)
        ):
            raise AuthError("assignment_review_pending", 409)
    return len(prior) + 1


def _assignment_file_view(db: Session, row: AssignmentFile) -> AssignmentFileView:
    file = _object(db, row.organization_id, row.file_id)
    try:
        _pinned_reference(row, file) if row.state == "submitted" else clean_reference(file)
        usable = row.state != "removed"
    except AuthError:
        usable = False
    return AssignmentFileView(
        id=row.id,
        target_revision=row.target_revision,
        state=cast("Literal['active','removed','submitted']", row.state),
        version=row.version,
        file=files.file_view(file),
        submission_id=row.submission_id,
        evidence=_evidence(row),
        usable=usable,
    )


def assignment_files(
    db: Session, org: UUID, course_id: UUID, assignment_id: UUID, actor: User
) -> AssignmentFileList:
    _, started, assignment = _assignment_context(db, org, course_id, assignment_id, actor)
    rule = db.scalar(
        select(AssignmentFileRule).where(AssignmentFileRule.assignment_id == assignment_id)
    )
    rows = list(
        db.scalars(
            select(AssignmentFile)
            .where(
                AssignmentFile.course_enrollment_id == started.id,
                AssignmentFile.assignment_id == assignment_id,
                AssignmentFile.state != "removed",
            )
            .order_by(AssignmentFile.created_at, AssignmentFile.id)
            .limit(1000)
        )
    )
    return AssignmentFileList(
        collection_enabled=get_settings().files_enabled,
        max_upload_bytes=get_settings().files_max_bytes,
        next_revision=_next_revision(db, started, assignment),
        rule=rule_view(db, org, rule) if rule else None,
        items=[_assignment_file_view(db, row) for row in rows],
    )


def _matches_intent(file: FileObject, data: AssignmentFileIntent) -> bool:
    return (
        file.client_request_id,
        file.expected_media_type,
        file.expected_byte_size,
        file.expected_sha256,
    ) == (data.client_request_id, data.media_type, data.byte_size, data.sha256)


def _assignment_replay(
    db: Session,
    existing: AssignmentFile,
    started: CourseEnrollment,
    assignment: LearningAssignment,
    actor: User,
    data: AssignmentFileIntent,
) -> AssignmentFileView:
    if (
        existing.course_enrollment_id != started.id
        or existing.assignment_id != assignment.id
        or existing.owner_person_id != actor.person_id
        or existing.target_revision != data.expected_revision
        or not _matches_intent(_object(db, existing.organization_id, existing.file_id), data)
    ):
        raise AuthError("idempotency_conflict", 409)
    return _assignment_file_view(db, existing)


def create_assignment_file(
    db: Session,
    org: UUID,
    course_id: UUID,
    assignment_id: UUID,
    actor: User,
    data: AssignmentFileIntent,
    request_id: str,
) -> AssignmentFileView:
    require_files_enabled()
    _, started, assignment = _assignment_context(db, org, course_id, assignment_id, actor)
    existing = db.scalar(
        select(AssignmentFile).where(
            AssignmentFile.organization_id == org,
            AssignmentFile.client_request_id == data.client_request_id,
        )
    )

    if existing:
        return _assignment_replay(db, existing, started, assignment, actor, data)
    throttle(db, "files.intent", f"{org}:{actor.id}", get_settings().files_intent_limit_per_window)
    course, started, assignment = _assignment_context(
        db, org, course_id, assignment_id, actor, lock=True
    )
    existing = db.scalar(
        select(AssignmentFile).where(
            AssignmentFile.organization_id == org,
            AssignmentFile.client_request_id == data.client_request_id,
        )
    )
    if existing:
        return _assignment_replay(db, existing, started, assignment, actor, data)
    revision = _next_revision(db, started, assignment, writing=True)
    if data.expected_revision != revision:
        raise AuthError("version_conflict", 409)
    rule = db.scalar(
        select(AssignmentFileRule).where(AssignmentFileRule.assignment_id == assignment_id)
    )
    if rule is None:
        raise AuthError("assignment_files_not_configured", 409)
    policy = _policy(db, org, rule.policy_id, "assignment_submission")
    if (
        not course.published_at
        or not policy.published_at
        or policy.published_at > course.published_at
    ):
        raise AuthError("file_policy_unavailable", 409)
    count = (
        db.scalar(
            select(func.count())
            .select_from(AssignmentFile)
            .where(
                AssignmentFile.course_enrollment_id == started.id,
                AssignmentFile.assignment_id == assignment_id,
                AssignmentFile.target_revision == revision,
                AssignmentFile.state == "active",
            )
        )
        or 0
    )
    if count >= min(rule.maximum_files, policy.max_files):
        raise AuthError("file_count_limit", 409)
    if data.byte_size > get_settings().files_max_bytes:
        raise AuthError("file_policy_rejected", 422)
    binding_id = uuid4()
    ctx = files.AuthorizedFileContext(
        actor.id, org, actor.person_id, "assignment_submission", binding_id
    )
    created = files.create_file(
        db,
        ctx,
        actor,
        FileCreate(policy_id=policy.id, **data.model_dump(exclude={"expected_revision"})),
        request_id,
        commit=False,
        allow_retired_policy=True,
    )
    binding = AssignmentFile(
        id=binding_id,
        organization_id=org,
        course_id=course_id,
        course_enrollment_id=started.id,
        assignment_id=assignment_id,
        owner_person_id=actor.person_id,
        client_request_id=data.client_request_id,
        file_id=created.id,
        target_revision=revision,
    )
    db.add(binding)
    db.flush()
    learning._audit(
        db,
        actor,
        org,
        binding.id,
        "lms.assignment.file_created",
        request_id,
        1,
        "file_id,target_revision",
    )
    learning._commit(db)
    return _assignment_file_view(db, binding)


def owned_assignment_file(
    db: Session,
    org: UUID,
    course_id: UUID,
    assignment_id: UUID,
    binding_id: UUID,
    actor: User,
    *,
    writing: bool = False,
    lock: bool = False,
) -> tuple[AssignmentFile, FileObject]:
    _, started, assignment = _assignment_context(
        db, org, course_id, assignment_id, actor, lock=lock
    )
    query = select(AssignmentFile).where(
        AssignmentFile.id == binding_id,
        AssignmentFile.organization_id == org,
        AssignmentFile.assignment_id == assignment_id,
        AssignmentFile.course_enrollment_id == started.id,
        AssignmentFile.owner_person_id == actor.person_id,
    )
    binding = db.scalar(query.with_for_update() if lock else query)
    if binding is None:
        raise AuthError("not_found", 404)
    file = _object(db, org, binding.file_id, lock=lock)
    if writing and (
        binding.state != "active"
        or binding.target_revision != _next_revision(db, started, assignment, writing=True)
        or file.retention_until <= now()
    ):
        raise AuthError("assignment_file_read_only", 409)
    return binding, file


def remove_assignment_file(
    db: Session,
    org: UUID,
    course_id: UUID,
    assignment_id: UUID,
    binding_id: UUID,
    actor: User,
    expected_version: int,
    request_id: str,
) -> AssignmentFileView:
    require_files_enabled()
    row, _ = owned_assignment_file(db, org, course_id, assignment_id, binding_id, actor, lock=True)
    if row.version != expected_version or row.state != "active":
        raise AuthError("version_conflict", 409)
    row.state, row.version = "removed", row.version + 1
    learning._audit(
        db,
        actor,
        org,
        row.id,
        "lms.assignment.file_removed",
        request_id,
        row.version,
        "state,version",
    )
    learning._commit(db)
    return _assignment_file_view(db, row)


def freeze_submission(
    db: Session,
    submission: AssignmentSubmission,
    actor: User,
    binding_ids: list[UUID],
    request_id: str,
) -> None:
    rule = db.scalar(
        select(AssignmentFileRule).where(
            AssignmentFileRule.assignment_id == submission.assignment_id
        )
    )
    if not rule:
        if binding_ids:
            raise AuthError("assignment_files_not_configured", 409)
        return
    if not rule.minimum_files <= len(binding_ids) <= rule.maximum_files:
        raise AuthError("assignment_files_required", 422)
    if not binding_ids:
        return
    require_files_enabled()
    for binding_id in sorted(binding_ids):
        row = db.scalar(
            select(AssignmentFile)
            .where(
                AssignmentFile.id == binding_id,
                AssignmentFile.organization_id == submission.organization_id,
                AssignmentFile.course_enrollment_id == submission.course_enrollment_id,
                AssignmentFile.assignment_id == submission.assignment_id,
                AssignmentFile.owner_person_id == actor.person_id,
            )
            .with_for_update()
        )
        if row is None or row.state != "active" or row.target_revision != submission.revision:
            raise AuthError("assignment_file_unavailable", 409)
        file = _object(db, submission.organization_id, row.file_id, lock=True)
        clean_reference(file)
        ctx = files.AuthorizedFileContext(
            actor.id, submission.organization_id, actor.person_id, "assignment_submission", row.id
        )
        files.freeze_evidence(db, ctx, actor, file.id, file.version, request_id, commit=False)
        row.state, row.version, row.submission_id = "submitted", row.version + 1, submission.id
        _pin(row, file)
        db.flush()


def trainer_assignment_file(
    db: Session, org: UUID, course_id: UUID, submission_id: UUID, binding_id: UUID, actor: User
) -> tuple[AssignmentFile, FileObject]:
    require_permission(db, actor, org, "lms.assessment.grade")
    submission = db.scalar(
        select(AssignmentSubmission).where(
            AssignmentSubmission.id == submission_id,
            AssignmentSubmission.organization_id == org,
            AssignmentSubmission.course_id == course_id,
        )
    )
    if submission is None:
        raise AuthError("not_found", 404)
    started = db.get(CourseEnrollment, submission.course_enrollment_id)
    enrollment = db.get(Enrollment, started.enrollment_id) if started else None
    if not enrollment or not any(
        row_course.id == course_id and cohort.id == enrollment.cohort_id
        for _, row_course, cohort in learning._trainer_course_rows(db, org, actor)
    ):
        raise AuthError("staff_scope_denied", 403)
    binding = db.scalar(
        select(AssignmentFile).where(
            AssignmentFile.id == binding_id,
            AssignmentFile.submission_id == submission.id,
            AssignmentFile.state == "submitted",
            AssignmentFile.organization_id == org,
        )
    )
    if binding is None:
        raise AuthError("not_found", 404)
    file = _object(db, org, binding.file_id)
    _pinned_reference(binding, file)
    return binding, file


def _material_view(db: Session, binding: MaterialFile) -> MaterialFileView:
    file = _object(db, binding.organization_id, binding.file_id)
    try:
        if binding.state != "active":
            raise AuthError("material_file_removed", 409)
        _pinned_reference(binding, file) if binding.frozen_at else clean_reference(file)
        usable = True
    except AuthError:
        usable = False
    return MaterialFileView(
        material_id=binding.material_id,
        state=cast(Literal["active", "removed"], binding.state),
        version=binding.version,
        file=files.file_view(file),
        evidence=_evidence(binding),
        usable=usable,
    )


def material_files(
    db: Session,
    org: UUID,
    course_id: UUID,
    actor: User,
    cursor: UUID | None = None,
    limit: int = 50,
) -> MaterialFileList:
    require_permission(db, actor, org, "lms.course.manage")
    learning._course(db, org, course_id)
    if not 1 <= limit <= 100:
        raise AuthError("invalid_request", 422)
    query = select(MaterialFile).where(
        MaterialFile.organization_id == org, MaterialFile.course_id == course_id
    )
    if cursor:
        anchor = db.scalar(query.where(MaterialFile.material_id == cursor))
        if anchor is None:
            raise AuthError("invalid_cursor", 422)
        query = query.where(
            tuple_(MaterialFile.created_at, MaterialFile.id)
            > tuple_(literal(anchor.created_at), literal(anchor.id))
        )
    rows = list(
        db.scalars(query.order_by(MaterialFile.created_at, MaterialFile.id).limit(limit + 1))
    )
    return MaterialFileList(
        collection_enabled=get_settings().files_enabled,
        max_upload_bytes=get_settings().files_max_bytes,
        items=[_material_view(db, row) for row in rows[:limit]],
        next_cursor=rows[limit - 1].material_id if len(rows) > limit else None,
    )


def create_material_file(
    db: Session, org: UUID, actor: User, data: MaterialFileIntent, request_id: str
) -> MaterialFileView:
    require_files_enabled()
    require_permission(db, actor, org, "lms.course.manage")
    require_permission(db, actor, org, "files.policy.view")
    digest = hashlib.sha256(
        json.dumps(data.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    learning._course(db, org, data.course_id)
    prior = db.scalar(
        select(MaterialFile).where(
            MaterialFile.organization_id == org,
            MaterialFile.client_request_id == data.client_request_id,
        )
    )
    if prior:
        if prior.course_id != data.course_id or prior.request_digest != digest:
            raise AuthError("idempotency_conflict", 409)
        return _material_view(db, prior)
    throttle(db, "files.intent", f"{org}:{actor.id}", get_settings().files_intent_limit_per_window)
    course = learning._course(db, org, data.course_id, lock=True)
    prior = db.scalar(
        select(MaterialFile).where(
            MaterialFile.organization_id == org,
            MaterialFile.client_request_id == data.client_request_id,
        )
    )
    if prior:
        if prior.course_id != data.course_id or prior.request_digest != digest:
            raise AuthError("idempotency_conflict", 409)
        return _material_view(db, prior)
    learning._require_draft(course)
    lesson = db.scalar(
        select(Lesson).where(
            Lesson.id == data.lesson_id,
            Lesson.course_id == course.id,
            Lesson.organization_id == org,
        )
    )
    if not lesson:
        raise AuthError("not_found", 404)
    policy = _policy(db, org, data.policy_id, "lms_material")
    if policy.state != "published" or data.byte_size > get_settings().files_max_bytes:
        raise AuthError("file_policy_unavailable", 409)
    material_id = uuid4()
    material = LessonMaterial(
        id=material_id,
        organization_id=org,
        course_id=course.id,
        lesson_id=lesson.id,
        position=data.position,
        kind="document",
        label_en=data.label_en.strip(),
        label_ta=data.label_ta.strip(),
        provider_key=f"shared-file:{material_id}",
        is_private=True,
    )
    db.add(material)
    ctx = files.AuthorizedFileContext(actor.id, org, actor.person_id, "lms_material", material_id)
    file = files.create_file(
        db,
        ctx,
        actor,
        FileCreate(
            policy_id=policy.id,
            **data.model_dump(include={"client_request_id", "media_type", "byte_size", "sha256"}),
        ),
        request_id,
        commit=False,
    )
    binding = MaterialFile(
        organization_id=org,
        course_id=course.id,
        material_id=material_id,
        owner_person_id=actor.person_id,
        client_request_id=data.client_request_id,
        request_digest=digest,
        file_id=file.id,
    )
    db.add(binding)
    db.flush()
    learning._audit(
        db, actor, org, material_id, "lms.material.file_created", request_id, 1, "file_id"
    )
    learning._commit(db)
    return _material_view(db, binding)


def author_material_file(
    db: Session,
    org: UUID,
    course_id: UUID,
    material_id: UUID,
    actor: User,
    *,
    writing: bool = False,
    lock: bool = False,
    include_removed: bool = False,
) -> tuple[MaterialFile, FileObject]:
    require_permission(db, actor, org, "lms.course.manage")
    course = learning._course(db, org, course_id, lock=lock)
    if writing:
        learning._require_draft(course)
    binding = db.scalar(
        select(MaterialFile).where(
            MaterialFile.organization_id == org,
            MaterialFile.course_id == course_id,
            MaterialFile.material_id == material_id,
        )
    )
    if binding is None:
        raise AuthError("not_found", 404)
    if binding.state != "active" and not include_removed:
        raise AuthError("material_file_removed", 409)
    file = _object(db, org, binding.file_id)
    if writing and (binding.frozen_at or file.retention_until <= now()):
        raise AuthError("material_file_read_only", 409)
    return binding, file


def remove_material_file(
    db: Session,
    org: UUID,
    course_id: UUID,
    material_id: UUID,
    actor: User,
    expected_version: int,
    request_id: str,
) -> MaterialFileView:
    binding, _ = author_material_file(
        db, org, course_id, material_id, actor, lock=True, include_removed=True
    )
    learning._require_draft(learning._course(db, org, course_id))
    if binding.version != expected_version:
        raise AuthError("version_conflict", 409)
    if binding.state == "removed":
        return _material_view(db, binding)
    if binding.frozen_at is not None:
        raise AuthError("material_file_read_only", 409)
    binding.state, binding.version = "removed", binding.version + 1
    db.flush()
    learning._audit(
        db,
        actor,
        org,
        material_id,
        "lms.material.file_removed",
        request_id,
        binding.version,
        "state",
    )
    learning._commit(db)
    return _material_view(db, binding)


def trainer_submission_files(
    db: Session, org: UUID, course_id: UUID, submission_id: UUID, actor: User
) -> list[AssignmentFileView]:
    require_permission(db, actor, org, "lms.assessment.grade")
    submission = db.scalar(
        select(AssignmentSubmission).where(
            AssignmentSubmission.id == submission_id,
            AssignmentSubmission.organization_id == org,
            AssignmentSubmission.course_id == course_id,
        )
    )
    if submission is None:
        raise AuthError("not_found", 404)
    started = db.get(CourseEnrollment, submission.course_enrollment_id)
    enrollment = db.get(Enrollment, started.enrollment_id) if started else None
    if not enrollment or not any(
        row_course.id == course_id and cohort.id == enrollment.cohort_id
        for _, row_course, cohort in learning._trainer_course_rows(db, org, actor)
    ):
        raise AuthError("staff_scope_denied", 403)
    rows = list(
        db.scalars(
            select(AssignmentFile)
            .where(
                AssignmentFile.submission_id == submission_id,
                AssignmentFile.organization_id == org,
                AssignmentFile.state == "submitted",
            )
            .order_by(AssignmentFile.id)
        )
    )
    return [_assignment_file_view(db, row) for row in rows]


def prepare_course_publication(db: Session, course: Course, actor: User, request_id: str) -> None:
    rules = list(
        db.scalars(select(AssignmentFileRule).where(AssignmentFileRule.course_id == course.id))
    )
    for rule in rules:
        policy = _policy(db, course.organization_id, rule.policy_id, "assignment_submission")
        if policy.state != "published" or rule.maximum_files > policy.max_files:
            raise AuthError("file_policy_unavailable", 409)
    bindings = list(
        db.scalars(
            select(MaterialFile)
            .where(
                MaterialFile.course_id == course.id,
                MaterialFile.organization_id == course.organization_id,
                MaterialFile.state == "active",
            )
            .order_by(MaterialFile.id)
            .with_for_update()
        )
    )
    for binding in bindings:
        require_files_enabled()
        file = _object(db, course.organization_id, binding.file_id, lock=True)
        clean_reference(file)
        ctx = files.AuthorizedFileContext(
            actor.id,
            course.organization_id,
            binding.owner_person_id,
            "lms_material",
            binding.material_id,
        )
        files.freeze_evidence(db, ctx, actor, file.id, file.version, request_id, commit=False)
        _pin(binding, file)
        binding.version += 1
        db.flush()


def material_reference(
    db: Session, org: UUID, material: LessonMaterial
) -> tuple[StoredObject, UUID] | None:
    if not material.provider_key.startswith("shared-file:"):
        return None
    require_files_enabled()
    binding = db.scalar(
        select(MaterialFile).where(
            MaterialFile.material_id == material.id,
            MaterialFile.organization_id == org,
            MaterialFile.course_id == material.course_id,
        )
    )
    if binding is None or material.provider_key != f"shared-file:{material.id}":
        raise AuthError("file_integrity_error", 503)
    if binding.state != "active":
        raise AuthError("material_file_removed", 409)
    file = _object(db, org, binding.file_id)
    return _pinned_reference(binding, file), file.id
