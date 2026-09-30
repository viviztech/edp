from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.identity.models import (
    AuditLog,
    Person,
    Role,
    RolePermission,
    User,
    UserRole,
    now,
)
from app.modules.identity.security import AuthError
from app.modules.identity.service import require_permission
from app.modules.lms.material_access import (
    AccessMode,
    LocalMaterial,
    issue_access,
    resolve_local_material,
    verify_access,
)
from app.modules.lms.models import (
    CohortCourse,
    Course,
    CourseEnrollment,
    CourseModule,
    Lesson,
    LessonMaterial,
    LessonPrerequisite,
    LessonProgress,
)
from app.modules.lms.schemas import (
    AdminCourseView,
    AdminLessonView,
    AdminModuleView,
    CohortCourseCreate,
    CohortCourseView,
    CompletionRule,
    CompletionRuleUpdate,
    CourseCreate,
    CourseEnrollmentState,
    CourseEnrollmentView,
    CourseProgressSummary,
    CourseProgressView,
    CourseState,
    CourseView,
    LearnerCourseView,
    LearnerLessonView,
    LearnerMaterialView,
    LearnerModuleView,
    LearningCatalogView,
    LessonCompletionCommand,
    LessonCreate,
    LessonPrerequisiteCreate,
    LessonPrerequisiteView,
    LessonProgressView,
    LessonView,
    MaterialAccessView,
    MaterialAdminView,
    MaterialCreate,
    MaterialKind,
    ModuleCreate,
    ModuleView,
    MyLearningView,
    ProgressState,
    PublishCourse,
    TrainerCourseDeliveryView,
    TrainerDeliveryView,
    TrainerLearnerProgressView,
    TrainerLessonView,
    TrainerModuleView,
)
from app.modules.programs.models import (
    Cohort,
    Enrollment,
    Participant,
    ProgramStaffAssignment,
)


def _audit(
    db: Session,
    actor: User,
    org: UUID,
    resource: UUID,
    action: str,
    request_id: str,
    version: int,
    changed_fields: str,
    reason: str | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=resource,
            action=action,
            request_id=request_id,
            resource_version=version,
            changed_fields=changed_fields,
            reason=reason,
        )
    )


def _commit(db: Session, code: str = "learning_conflict") -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError(code, 409) from exc


def course_view(item: Course) -> CourseView:
    return CourseView(
        id=item.id,
        organization_id=item.organization_id,
        code=item.code,
        title_en=item.title_en,
        title_ta=item.title_ta,
        description_en=item.description_en,
        description_ta=item.description_ta,
        completion_rule=cast(CompletionRule, item.completion_rule),
        minimum_lessons=item.minimum_lessons,
        state=cast(CourseState, item.state),
        version=item.version,
        published_at=item.published_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def module_view(item: CourseModule) -> ModuleView:
    return ModuleView(
        id=item.id,
        organization_id=item.organization_id,
        course_id=item.course_id,
        position=item.position,
        title_en=item.title_en,
        title_ta=item.title_ta,
        created_at=item.created_at,
    )


def lesson_view(item: Lesson) -> LessonView:
    return LessonView(
        id=item.id,
        organization_id=item.organization_id,
        course_id=item.course_id,
        module_id=item.module_id,
        position=item.position,
        title_en=item.title_en,
        title_ta=item.title_ta,
        body_en=item.body_en,
        body_ta=item.body_ta,
        duration_minutes=item.duration_minutes,
        created_at=item.created_at,
    )


def material_admin_view(item: LessonMaterial) -> MaterialAdminView:
    return MaterialAdminView(
        id=item.id,
        organization_id=item.organization_id,
        course_id=item.course_id,
        lesson_id=item.lesson_id,
        position=item.position,
        kind=cast(MaterialKind, item.kind),
        label_en=item.label_en,
        label_ta=item.label_ta,
        provider_key=item.provider_key,
        is_private=item.is_private,
        created_at=item.created_at,
    )


def assignment_view(item: CohortCourse) -> CohortCourseView:
    return CohortCourseView(
        id=item.id,
        organization_id=item.organization_id,
        course_id=item.course_id,
        cohort_id=item.cohort_id,
        position=item.position,
        created_at=item.created_at,
    )


def course_enrollment_view(item: CourseEnrollment) -> CourseEnrollmentView:
    return CourseEnrollmentView(
        id=item.id,
        organization_id=item.organization_id,
        enrollment_id=item.enrollment_id,
        course_id=item.course_id,
        status=cast(CourseEnrollmentState, item.status),
        version=item.version,
        started_at=item.started_at,
        completed_at=item.completed_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _course(db: Session, org: UUID, course_id: UUID, lock: bool = False) -> Course:
    statement = select(Course).where(
        Course.id == course_id,
        Course.organization_id == org,
    )
    if lock:
        statement = statement.with_for_update()
    item = db.scalar(statement)
    if not item:
        raise AuthError("not_found", 404)
    return item


def _require_draft(item: Course) -> None:
    if item.state != "draft":
        raise AuthError("course_structure_frozen", 409)


def _admin_structure(db: Session, item: Course) -> AdminCourseView:
    modules = list(
        db.scalars(
            select(CourseModule)
            .where(CourseModule.course_id == item.id)
            .order_by(CourseModule.position, CourseModule.id)
        )
    )
    lessons = list(
        db.scalars(
            select(Lesson)
            .where(Lesson.course_id == item.id)
            .order_by(Lesson.module_id, Lesson.position, Lesson.id)
        )
    )
    materials = list(
        db.scalars(
            select(LessonMaterial)
            .where(LessonMaterial.course_id == item.id)
            .order_by(LessonMaterial.lesson_id, LessonMaterial.position, LessonMaterial.id)
        )
    )
    prerequisites = list(
        db.scalars(
            select(LessonPrerequisite)
            .where(LessonPrerequisite.course_id == item.id)
            .order_by(LessonPrerequisite.lesson_id, LessonPrerequisite.prerequisite_lesson_id)
        )
    )
    prerequisite_map: dict[UUID, list[UUID]] = {}
    for prerequisite in prerequisites:
        prerequisite_map.setdefault(prerequisite.lesson_id, []).append(
            prerequisite.prerequisite_lesson_id
        )
    material_map: dict[UUID, list[MaterialAdminView]] = {}
    for material in materials:
        material_map.setdefault(material.lesson_id, []).append(material_admin_view(material))
    lesson_map: dict[UUID, list[AdminLessonView]] = {}
    for lesson in lessons:
        lesson_map.setdefault(lesson.module_id, []).append(
            AdminLessonView(
                **lesson_view(lesson).model_dump(),
                materials=material_map.get(lesson.id, []),
                prerequisite_lesson_ids=prerequisite_map.get(lesson.id, []),
            )
        )
    return AdminCourseView(
        **course_view(item).model_dump(),
        modules=[
            AdminModuleView(
                **module_view(module).model_dump(),
                lessons=lesson_map.get(module.id, []),
            )
            for module in modules
        ],
    )


def _progress_view(
    course: Course,
    total_lessons: int,
    completed_lessons: int,
    started: bool,
) -> CourseProgressView:
    required = (
        total_lessons
        if course.completion_rule == "all_lessons"
        else min(course.minimum_lessons or total_lessons, total_lessons)
    )
    percent = min(100, round(completed_lessons * 100 / required)) if required else 0
    status = (
        "completed"
        if required and completed_lessons >= required
        else ("in_progress" if started else "not_started")
    )
    return CourseProgressView(
        total_lessons=total_lessons,
        required_lessons=required,
        completed_lessons=completed_lessons,
        percent=percent,
        status=cast(ProgressState, status),
    )


def _progress_summaries(
    db: Session,
    assignments: list[CohortCourse],
    courses: dict[UUID, Course],
) -> list[CourseProgressSummary]:
    result: list[CourseProgressSummary] = []
    for assignment in assignments:
        course = courses.get(assignment.course_id)
        if course is None:
            continue
        enrollment_ids = list(
            db.scalars(
                select(Enrollment.id).where(
                    Enrollment.organization_id == assignment.organization_id,
                    Enrollment.cohort_id == assignment.cohort_id,
                    Enrollment.status == "active",
                )
            )
        )
        started = (
            list(
                db.scalars(
                    select(CourseEnrollment).where(
                        CourseEnrollment.enrollment_id.in_(enrollment_ids),
                        CourseEnrollment.course_id == assignment.course_id,
                    )
                )
            )
            if enrollment_ids
            else []
        )
        total = len(
            list(db.scalars(select(Lesson.id).where(Lesson.course_id == assignment.course_id)))
        )
        percents: list[int] = []
        for course_enrollment in started:
            completed = len(
                list(
                    db.scalars(
                        select(LessonProgress.id).where(
                            LessonProgress.course_enrollment_id == course_enrollment.id
                        )
                    )
                )
            )
            percents.append(_progress_view(course, total, completed, True).percent)
        result.append(
            CourseProgressSummary(
                course_id=assignment.course_id,
                cohort_id=assignment.cohort_id,
                assigned_learners=len(enrollment_ids),
                started_learners=len(started),
                completed_learners=sum(item.status == "completed" for item in started),
                average_percent=round(sum(percents) / len(percents)) if percents else 0,
            )
        )
    return result


def catalog(db: Session, org: UUID, actor: User) -> LearningCatalogView:
    require_permission(db, actor, org, "lms.course.view")
    courses = list(
        db.scalars(
            select(Course)
            .where(Course.organization_id == org)
            .order_by(Course.created_at, Course.id)
            .limit(100)
        )
    )
    assignments = list(
        db.scalars(
            select(CohortCourse)
            .where(CohortCourse.organization_id == org)
            .order_by(CohortCourse.cohort_id, CohortCourse.position, CohortCourse.id)
            .limit(500)
        )
    )
    return LearningCatalogView(
        courses=[_admin_structure(db, item) for item in courses],
        assignments=[assignment_view(item) for item in assignments],
        progress_summaries=_progress_summaries(
            db, assignments, {item.id: item for item in courses}
        ),
    )


def create_course(
    db: Session,
    org: UUID,
    actor: User,
    data: CourseCreate,
    request_id: str,
) -> CourseView:
    require_permission(db, actor, org, "lms.course.manage")
    item = Course(organization_id=org, **data.model_dump())
    db.add(item)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("course_code_exists", 409) from exc
    _audit(
        db,
        actor,
        org,
        item.id,
        "lms.course.created",
        request_id,
        1,
        "code,title_en,title_ta,description_en,description_ta,completion_rule,minimum_lessons",
    )
    _commit(db)
    return course_view(item)


def update_completion_rule(
    db: Session,
    org: UUID,
    course_id: UUID,
    actor: User,
    data: CompletionRuleUpdate,
    request_id: str,
) -> CourseView:
    require_permission(db, actor, org, "lms.course.manage")
    item = _course(db, org, course_id, lock=True)
    _require_draft(item)
    if item.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    item.completion_rule = data.completion_rule
    item.minimum_lessons = data.minimum_lessons
    item.version += 1
    item.updated_at = now()
    _audit(
        db,
        actor,
        org,
        item.id,
        "lms.course.completion_rule_updated",
        request_id,
        item.version,
        "completion_rule,minimum_lessons",
        data.reason,
    )
    _commit(db)
    return course_view(item)


def create_prerequisite(
    db: Session,
    org: UUID,
    actor: User,
    data: LessonPrerequisiteCreate,
    request_id: str,
) -> LessonPrerequisiteView:
    require_permission(db, actor, org, "lms.course.manage")
    course = _course(db, org, data.course_id, lock=True)
    _require_draft(course)
    lessons = list(
        db.scalars(
            select(Lesson).where(
                Lesson.id.in_([data.lesson_id, data.prerequisite_lesson_id]),
                Lesson.course_id == data.course_id,
                Lesson.organization_id == org,
            )
        )
    )
    if len(lessons) != 2:
        raise AuthError("not_found", 404)
    modules = {
        item.id: item.position
        for item in db.scalars(select(CourseModule).where(CourseModule.course_id == data.course_id))
    }
    by_id = {item.id: item for item in lessons}
    target = by_id[data.lesson_id]
    required = by_id[data.prerequisite_lesson_id]
    target_order = (modules[target.module_id], target.position)
    required_order = (modules[required.module_id], required.position)
    if required_order >= target_order:
        raise AuthError("prerequisite_must_precede_lesson", 422)
    item = LessonPrerequisite(organization_id=org, **data.model_dump(exclude={"reason"}))
    db.add(item)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("prerequisite_exists", 409) from exc
    _audit(
        db,
        actor,
        org,
        item.id,
        "lms.lesson.prerequisite_created",
        request_id,
        course.version,
        "course_id,lesson_id,prerequisite_lesson_id",
        data.reason,
    )
    _commit(db)
    return LessonPrerequisiteView.model_validate(item, from_attributes=True)


def create_module(
    db: Session,
    org: UUID,
    actor: User,
    data: ModuleCreate,
    request_id: str,
) -> ModuleView:
    require_permission(db, actor, org, "lms.course.manage")
    course = _course(db, org, data.course_id, lock=True)
    _require_draft(course)
    item = CourseModule(organization_id=org, **data.model_dump())
    db.add(item)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("module_position_exists", 409) from exc
    _audit(
        db,
        actor,
        org,
        item.id,
        "lms.module.created",
        request_id,
        course.version,
        "course_id,position,title_en,title_ta",
    )
    _commit(db)
    return module_view(item)


def create_lesson(
    db: Session,
    org: UUID,
    actor: User,
    data: LessonCreate,
    request_id: str,
) -> LessonView:
    require_permission(db, actor, org, "lms.course.manage")
    course = _course(db, org, data.course_id, lock=True)
    _require_draft(course)
    module = db.scalar(
        select(CourseModule).where(
            CourseModule.id == data.module_id,
            CourseModule.course_id == data.course_id,
            CourseModule.organization_id == org,
        )
    )
    if not module:
        raise AuthError("not_found", 404)
    item = Lesson(organization_id=org, **data.model_dump())
    db.add(item)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("lesson_position_exists", 409) from exc
    _audit(
        db,
        actor,
        org,
        item.id,
        "lms.lesson.created",
        request_id,
        course.version,
        "course_id,module_id,position,title_en,title_ta,body_en,body_ta,duration_minutes",
    )
    _commit(db)
    return lesson_view(item)


def create_material(
    db: Session,
    org: UUID,
    actor: User,
    data: MaterialCreate,
    request_id: str,
) -> MaterialAdminView:
    require_permission(db, actor, org, "lms.course.manage")
    course = _course(db, org, data.course_id, lock=True)
    _require_draft(course)
    lesson = db.scalar(
        select(Lesson).where(
            Lesson.id == data.lesson_id,
            Lesson.course_id == data.course_id,
            Lesson.organization_id == org,
        )
    )
    if not lesson:
        raise AuthError("not_found", 404)
    item = LessonMaterial(organization_id=org, is_private=True, **data.model_dump())
    db.add(item)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("material_position_exists", 409) from exc
    _audit(
        db,
        actor,
        org,
        item.id,
        "lms.material.created",
        request_id,
        course.version,
        "course_id,lesson_id,position,kind,label_en,label_ta,provider_key",
    )
    _commit(db)
    return material_admin_view(item)


def publish_course(
    db: Session,
    org: UUID,
    course_id: UUID,
    actor: User,
    data: PublishCourse,
    request_id: str,
) -> CourseView:
    require_permission(db, actor, org, "lms.course.publish")
    item = _course(db, org, course_id, lock=True)
    if item.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    _require_draft(item)
    modules = list(
        db.scalars(
            select(CourseModule)
            .where(CourseModule.course_id == item.id)
            .order_by(CourseModule.position)
        )
    )
    if not modules:
        raise AuthError("course_structure_incomplete", 422)
    module_ids_with_lessons = set(
        db.scalars(select(Lesson.module_id).where(Lesson.course_id == item.id).distinct())
    )
    if any(module.id not in module_ids_with_lessons for module in modules):
        raise AuthError("course_structure_incomplete", 422)
    lesson_count = len(list(db.scalars(select(Lesson.id).where(Lesson.course_id == item.id))))
    if item.completion_rule == "minimum_lessons" and (
        item.minimum_lessons is None or item.minimum_lessons > lesson_count
    ):
        raise AuthError("completion_rule_invalid", 422)
    item.state = "published"
    item.version += 1
    item.published_at = now()
    item.updated_at = item.published_at
    _audit(
        db,
        actor,
        org,
        item.id,
        "lms.course.published",
        request_id,
        item.version,
        "state,published_at",
        data.reason,
    )
    _commit(db)
    return course_view(item)


def assign_course(
    db: Session,
    org: UUID,
    actor: User,
    data: CohortCourseCreate,
    request_id: str,
) -> CohortCourseView:
    require_permission(db, actor, org, "lms.course.assign")
    course = _course(db, org, data.course_id)
    if course.state != "published":
        raise AuthError("course_not_published", 409)
    cohort = db.scalar(
        select(Cohort).where(
            Cohort.id == data.cohort_id,
            Cohort.organization_id == org,
        )
    )
    if not cohort:
        raise AuthError("not_found", 404)
    if cohort.state not in {"planned", "active"}:
        raise AuthError("cohort_not_available", 409)
    item = CohortCourse(
        organization_id=org,
        course_id=data.course_id,
        cohort_id=data.cohort_id,
        position=data.position,
    )
    db.add(item)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("course_assignment_conflict", 409) from exc
    _audit(
        db,
        actor,
        org,
        item.id,
        "lms.course.assigned",
        request_id,
        1,
        "course_id,cohort_id,position",
        data.reason,
    )
    _commit(db)
    return assignment_view(item)


def _learner_courses(
    db: Session,
    org: UUID,
    actor: User,
) -> list[tuple[Enrollment, CohortCourse, Course]]:
    require_permission(db, actor, org, "lms.learn")
    participant = db.scalar(
        select(Participant).where(
            Participant.organization_id == org,
            Participant.person_id == actor.person_id,
            Participant.status == "active",
        )
    )
    if not participant:
        raise AuthError("not_found", 404)
    enrollments = list(
        db.scalars(
            select(Enrollment).where(
                Enrollment.organization_id == org,
                Enrollment.participant_id == participant.id,
                Enrollment.status == "active",
            )
        )
    )
    if not enrollments:
        return []
    enrollment_by_cohort = {item.cohort_id: item for item in enrollments}
    rows = db.execute(
        select(CohortCourse, Course)
        .join(
            Course,
            (Course.id == CohortCourse.course_id)
            & (Course.organization_id == CohortCourse.organization_id),
        )
        .where(
            CohortCourse.organization_id == org,
            CohortCourse.cohort_id.in_(enrollment_by_cohort),
            Course.state == "published",
        )
        .order_by(CohortCourse.cohort_id, CohortCourse.position, Course.id)
    ).all()
    return [
        (enrollment_by_cohort[assignment.cohort_id], assignment, course)
        for assignment, course in rows
    ]


def _learner_structure(
    db: Session,
    enrollment: Enrollment,
    assignment: CohortCourse,
    course: Course,
) -> LearnerCourseView:
    admin = _admin_structure(db, course)
    started = db.scalar(
        select(CourseEnrollment).where(
            CourseEnrollment.enrollment_id == enrollment.id,
            CourseEnrollment.course_id == course.id,
        )
    )
    progress_rows = (
        list(
            db.scalars(
                select(LessonProgress).where(LessonProgress.course_enrollment_id == started.id)
            )
        )
        if started
        else []
    )
    completed = {item.lesson_id: item for item in progress_rows}
    total_lessons = sum(len(module.lessons) for module in admin.modules)
    return LearnerCourseView(
        id=course.id,
        code=course.code,
        title_en=course.title_en,
        title_ta=course.title_ta,
        description_en=course.description_en,
        description_ta=course.description_ta,
        completion_rule=cast(CompletionRule, course.completion_rule),
        minimum_lessons=course.minimum_lessons,
        cohort_id=enrollment.cohort_id,
        enrollment_id=enrollment.id,
        position=assignment.position,
        course_enrollment=course_enrollment_view(started) if started else None,
        progress=_progress_view(course, total_lessons, len(completed), started is not None),
        modules=[
            LearnerModuleView(
                id=module.id,
                position=module.position,
                title_en=module.title_en,
                title_ta=module.title_ta,
                lessons=[
                    LearnerLessonView(
                        id=lesson.id,
                        position=lesson.position,
                        title_en=lesson.title_en,
                        title_ta=lesson.title_ta,
                        body_en=lesson.body_en,
                        body_ta=lesson.body_ta,
                        duration_minutes=lesson.duration_minutes,
                        prerequisite_lesson_ids=lesson.prerequisite_lesson_ids,
                        locked=started is None
                        or not set(lesson.prerequisite_lesson_ids).issubset(completed),
                        completed=lesson.id in completed,
                        completed_at=completed[lesson.id].completed_at
                        if lesson.id in completed
                        else None,
                        materials=[
                            LearnerMaterialView(
                                id=material.id,
                                position=material.position,
                                kind=material.kind,
                                label_en=material.label_en,
                                label_ta=material.label_ta,
                                available=started is not None
                                and set(lesson.prerequisite_lesson_ids).issubset(completed),
                            )
                            for material in lesson.materials
                        ],
                    )
                    for lesson in module.lessons
                ],
            )
            for module in admin.modules
        ],
    )


def my_learning(db: Session, org: UUID, actor: User) -> MyLearningView:
    return MyLearningView(
        courses=[
            _learner_structure(db, enrollment, assignment, course)
            for enrollment, assignment, course in _learner_courses(db, org, actor)
        ]
    )


def start_course(
    db: Session,
    org: UUID,
    course_id: UUID,
    actor: User,
    request_id: str,
) -> CourseEnrollmentView:
    eligible = next(
        (row for row in _learner_courses(db, org, actor) if row[2].id == course_id),
        None,
    )
    if not eligible:
        raise AuthError("course_access_denied", 403)
    enrollment, _, course = eligible
    existing = db.scalar(
        select(CourseEnrollment)
        .where(
            CourseEnrollment.enrollment_id == enrollment.id,
            CourseEnrollment.course_id == course.id,
        )
        .with_for_update()
    )
    if existing:
        return course_enrollment_view(existing)
    item = CourseEnrollment(
        organization_id=org,
        enrollment_id=enrollment.id,
        course_id=course.id,
    )
    db.add(item)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(CourseEnrollment).where(
                CourseEnrollment.enrollment_id == enrollment.id,
                CourseEnrollment.course_id == course.id,
            )
        )
        if not existing:
            raise AuthError("learning_conflict", 409) from None
        return course_enrollment_view(existing)
    _audit(
        db,
        actor,
        org,
        item.id,
        "lms.course.started",
        request_id,
        1,
        "enrollment_id,course_id,status,started_at",
    )
    _commit(db)
    return course_enrollment_view(item)


def complete_lesson(
    db: Session,
    org: UUID,
    course_id: UUID,
    lesson_id: UUID,
    actor: User,
    data: LessonCompletionCommand,
    request_id: str,
) -> LessonProgressView:
    eligible = next(
        (row for row in _learner_courses(db, org, actor) if row[2].id == course_id),
        None,
    )
    if not eligible:
        raise AuthError("course_access_denied", 403)
    enrollment, _, course = eligible
    course_enrollment = db.scalar(
        select(CourseEnrollment)
        .where(
            CourseEnrollment.enrollment_id == enrollment.id,
            CourseEnrollment.course_id == course.id,
        )
        .with_for_update()
    )
    if not course_enrollment:
        raise AuthError("course_not_started", 409)
    existing = db.scalar(
        select(LessonProgress).where(
            LessonProgress.course_enrollment_id == course_enrollment.id,
            LessonProgress.lesson_id == lesson_id,
        )
    )
    total = len(list(db.scalars(select(Lesson.id).where(Lesson.course_id == course.id))))
    if existing:
        completed = len(
            list(
                db.scalars(
                    select(LessonProgress.id).where(
                        LessonProgress.course_enrollment_id == course_enrollment.id
                    )
                )
            )
        )
        return LessonProgressView(
            id=existing.id,
            course_enrollment_id=existing.course_enrollment_id,
            course_id=existing.course_id,
            lesson_id=existing.lesson_id,
            completed_at=existing.completed_at,
            course_enrollment=course_enrollment_view(course_enrollment),
            progress=_progress_view(course, total, completed, True),
        )
    if course_enrollment.version != data.expected_course_enrollment_version:
        raise AuthError("version_conflict", 409)
    lesson = db.scalar(
        select(Lesson).where(
            Lesson.id == lesson_id,
            Lesson.course_id == course.id,
            Lesson.organization_id == org,
        )
    )
    if not lesson:
        raise AuthError("not_found", 404)
    required = set(
        db.scalars(
            select(LessonPrerequisite.prerequisite_lesson_id).where(
                LessonPrerequisite.lesson_id == lesson_id,
                LessonPrerequisite.course_id == course.id,
            )
        )
    )
    completed_ids = set(
        db.scalars(
            select(LessonProgress.lesson_id).where(
                LessonProgress.course_enrollment_id == course_enrollment.id
            )
        )
    )
    if not required.issubset(completed_ids):
        raise AuthError("lesson_prerequisite_incomplete", 409)
    item = LessonProgress(
        organization_id=org,
        course_id=course.id,
        course_enrollment_id=course_enrollment.id,
        lesson_id=lesson.id,
    )
    db.add(item)
    db.flush()
    completed_count = len(completed_ids) + 1
    course_enrollment.version += 1
    course_enrollment.updated_at = now()
    progress = _progress_view(course, total, completed_count, True)
    became_complete = progress.status == "completed" and course_enrollment.status != "completed"
    if became_complete:
        course_enrollment.status = "completed"
        course_enrollment.completed_at = now()
    _audit(
        db,
        actor,
        org,
        item.id,
        "lms.lesson.completed",
        request_id,
        course_enrollment.version,
        "course_enrollment_id,lesson_id,completed_at",
    )
    if became_complete:
        _audit(
            db,
            actor,
            org,
            course_enrollment.id,
            "lms.course.completed",
            request_id,
            course_enrollment.version,
            "status,completed_at",
        )
    _commit(db)
    return LessonProgressView(
        id=item.id,
        course_enrollment_id=item.course_enrollment_id,
        course_id=item.course_id,
        lesson_id=item.lesson_id,
        completed_at=item.completed_at,
        course_enrollment=course_enrollment_view(course_enrollment),
        progress=progress,
    )


def _learner_material_context(
    db: Session,
    org: UUID,
    course_id: UUID,
    material_id: UUID,
    actor: User,
) -> tuple[Course, CourseEnrollment, LessonMaterial]:
    eligible = next(
        (row for row in _learner_courses(db, org, actor) if row[2].id == course_id),
        None,
    )
    if not eligible:
        raise AuthError("course_access_denied", 403)
    enrollment, _, course = eligible
    course_enrollment = db.scalar(
        select(CourseEnrollment).where(
            CourseEnrollment.enrollment_id == enrollment.id,
            CourseEnrollment.course_id == course.id,
        )
    )
    if not course_enrollment:
        raise AuthError("course_not_started", 409)
    material = db.scalar(
        select(LessonMaterial).where(
            LessonMaterial.id == material_id,
            LessonMaterial.course_id == course.id,
            LessonMaterial.organization_id == org,
        )
    )
    if not material:
        raise AuthError("not_found", 404)
    required = set(
        db.scalars(
            select(LessonPrerequisite.prerequisite_lesson_id).where(
                LessonPrerequisite.lesson_id == material.lesson_id,
                LessonPrerequisite.course_id == course.id,
            )
        )
    )
    completed = set(
        db.scalars(
            select(LessonProgress.lesson_id).where(
                LessonProgress.course_enrollment_id == course_enrollment.id
            )
        )
    )
    if not required.issubset(completed):
        raise AuthError("lesson_prerequisite_incomplete", 409)
    return course, course_enrollment, material


def _trainer_cohort_ids(
    db: Session,
    org: UUID,
    actor: User,
) -> set[UUID] | None:
    require_permission(db, actor, org, "lms.delivery.view")
    unrestricted = db.scalar(
        select(UserRole.id)
        .join(Role, Role.id == UserRole.role_id)
        .join(RolePermission, RolePermission.role_id == Role.id)
        .where(
            UserRole.user_id == actor.id,
            UserRole.organization_id == org,
            RolePermission.permission_code == "lms.delivery.view",
            Role.name != "Trainer",
        )
        .limit(1)
    )
    if unrestricted:
        return None
    assignments = list(
        db.scalars(
            select(ProgramStaffAssignment).where(
                ProgramStaffAssignment.organization_id == org,
                ProgramStaffAssignment.user_id == actor.id,
                ProgramStaffAssignment.state == "active",
            )
        )
    )
    if not assignments:
        raise AuthError("staff_scope_required", 403)
    center_ids = {item.center_id for item in assignments if item.cohort_id is None}
    cohort_ids = {item.cohort_id for item in assignments if item.cohort_id is not None}
    if center_ids:
        cohort_ids.update(
            db.scalars(
                select(Cohort.id).where(
                    Cohort.organization_id == org,
                    Cohort.center_id.in_(center_ids),
                    Cohort.state != "cancelled",
                )
            )
        )
    return {item for item in cohort_ids if item is not None}


def _trainer_course_rows(
    db: Session,
    org: UUID,
    actor: User,
) -> list[tuple[CohortCourse, Course, Cohort]]:
    cohort_ids = _trainer_cohort_ids(db, org, actor)
    statement = (
        select(CohortCourse, Course, Cohort)
        .join(
            Course,
            (Course.id == CohortCourse.course_id)
            & (Course.organization_id == CohortCourse.organization_id),
        )
        .join(
            Cohort,
            (Cohort.id == CohortCourse.cohort_id)
            & (Cohort.organization_id == CohortCourse.organization_id),
        )
        .where(
            CohortCourse.organization_id == org,
            Course.state == "published",
        )
        .order_by(Cohort.starts_on, CohortCourse.position, Course.id)
        .limit(250)
    )
    if cohort_ids is not None:
        if not cohort_ids:
            return []
        statement = statement.where(CohortCourse.cohort_id.in_(cohort_ids))
    return [(row[0], row[1], row[2]) for row in db.execute(statement).all()]


def _require_trainer_course(
    db: Session,
    org: UUID,
    course_id: UUID,
    actor: User,
) -> Course:
    row = next(
        (item for item in _trainer_course_rows(db, org, actor) if item[1].id == course_id),
        None,
    )
    if not row:
        raise AuthError("staff_scope_denied", 403)
    return row[1]


def _trainer_modules(db: Session, course: Course) -> list[TrainerModuleView]:
    admin = _admin_structure(db, course)
    return [
        TrainerModuleView(
            id=module.id,
            position=module.position,
            title_en=module.title_en,
            title_ta=module.title_ta,
            lessons=[
                TrainerLessonView(
                    id=lesson.id,
                    position=lesson.position,
                    title_en=lesson.title_en,
                    title_ta=lesson.title_ta,
                    duration_minutes=lesson.duration_minutes,
                    materials=[
                        LearnerMaterialView(
                            id=material.id,
                            position=material.position,
                            kind=material.kind,
                            label_en=material.label_en,
                            label_ta=material.label_ta,
                            available=True,
                        )
                        for material in lesson.materials
                    ],
                )
                for lesson in module.lessons
            ],
        )
        for module in admin.modules
    ]


def trainer_delivery(
    db: Session,
    org: UUID,
    actor: User,
) -> TrainerDeliveryView:
    courses: list[TrainerCourseDeliveryView] = []
    for assignment, course, cohort in _trainer_course_rows(db, org, actor):
        total = len(list(db.scalars(select(Lesson.id).where(Lesson.course_id == course.id))))
        learners: list[TrainerLearnerProgressView] = []
        enrollment_rows = db.execute(
            select(Enrollment, Participant, Person)
            .join(Participant, Participant.id == Enrollment.participant_id)
            .join(Person, Person.id == Participant.person_id)
            .where(
                Enrollment.organization_id == org,
                Enrollment.cohort_id == assignment.cohort_id,
                Enrollment.status == "active",
                Participant.status == "active",
            )
            .order_by(Person.display_name, Participant.id)
            .limit(500)
        ).all()
        for enrollment, participant, person in enrollment_rows:
            started = db.scalar(
                select(CourseEnrollment).where(
                    CourseEnrollment.enrollment_id == enrollment.id,
                    CourseEnrollment.course_id == course.id,
                )
            )
            completed = (
                len(
                    list(
                        db.scalars(
                            select(LessonProgress.id).where(
                                LessonProgress.course_enrollment_id == started.id
                            )
                        )
                    )
                )
                if started
                else 0
            )
            learners.append(
                TrainerLearnerProgressView(
                    participant_id=participant.id,
                    display_name=person.display_name,
                    course_enrollment=course_enrollment_view(started) if started else None,
                    progress=_progress_view(course, total, completed, started is not None),
                )
            )
        courses.append(
            TrainerCourseDeliveryView(
                course_id=course.id,
                cohort_id=cohort.id,
                course_code=course.code,
                title_en=course.title_en,
                title_ta=course.title_ta,
                cohort_name_en=cohort.name_en,
                cohort_name_ta=cohort.name_ta,
                modules=_trainer_modules(db, course),
                learners=learners,
            )
        )
    return TrainerDeliveryView(courses=courses)


def _material_access_view(
    org: UUID,
    actor: User,
    course: Course,
    material: LessonMaterial,
    mode: str,
) -> MaterialAccessView:
    settings = get_settings()
    token, expires_at = issue_access(
        settings,
        org,
        actor.id,
        course.id,
        material.id,
        cast(AccessMode, mode),
    )
    return MaterialAccessView(
        url=f"/api/courses/organizations/{org}/material-delivery/{token}",
        expires_at=expires_at,
    )


def learner_material_access(
    db: Session,
    org: UUID,
    course_id: UUID,
    material_id: UUID,
    actor: User,
    request_id: str,
) -> MaterialAccessView:
    course, _, material = _learner_material_context(db, org, course_id, material_id, actor)
    view = _material_access_view(org, actor, course, material, "learner")
    _audit(
        db,
        actor,
        org,
        material.id,
        "lms.material.access_issued",
        request_id,
        1,
        "course_id,material_id,expires_at",
    )
    _commit(db)
    return view


def trainer_material_access(
    db: Session,
    org: UUID,
    course_id: UUID,
    material_id: UUID,
    actor: User,
    request_id: str,
) -> MaterialAccessView:
    course = _require_trainer_course(db, org, course_id, actor)
    material = db.scalar(
        select(LessonMaterial).where(
            LessonMaterial.id == material_id,
            LessonMaterial.course_id == course.id,
            LessonMaterial.organization_id == org,
        )
    )
    if not material:
        raise AuthError("not_found", 404)
    view = _material_access_view(org, actor, course, material, "trainer")
    _audit(
        db,
        actor,
        org,
        material.id,
        "lms.material.access_issued",
        request_id,
        1,
        "course_id,material_id,expires_at",
    )
    _commit(db)
    return view


def deliver_material(
    db: Session,
    org: UUID,
    token: str,
    actor: User,
    request_id: str,
) -> LocalMaterial:
    settings = get_settings()
    claims = verify_access(settings, token)
    if claims.organization_id != org or claims.actor_id != actor.id:
        raise AuthError("material_access_invalid", 403)
    if claims.mode == "learner":
        course, _, material = _learner_material_context(
            db, org, claims.course_id, claims.material_id, actor
        )
    else:
        course = _require_trainer_course(db, org, claims.course_id, actor)
        trainer_material = db.scalar(
            select(LessonMaterial).where(
                LessonMaterial.id == claims.material_id,
                LessonMaterial.course_id == course.id,
                LessonMaterial.organization_id == org,
            )
        )
        if not trainer_material:
            raise AuthError("not_found", 404)
        material = trainer_material
    resolved = resolve_local_material(settings, material.provider_key)
    _audit(
        db,
        actor,
        org,
        material.id,
        "lms.material.delivered",
        request_id,
        1,
        "course_id,material_id",
    )
    _commit(db)
    return resolved
