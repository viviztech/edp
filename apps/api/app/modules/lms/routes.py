from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from app.modules.identity.routes import DB, Principal
from app.modules.lms import service
from app.modules.lms.schemas import (
    CohortCourseCreate,
    CohortCourseView,
    CompletionRuleUpdate,
    CourseCreate,
    CourseEnrollmentView,
    CourseView,
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
    ModuleCreate,
    ModuleView,
    MyLearningView,
    PublishCourse,
    TrainerDeliveryView,
)

router = APIRouter(prefix="/api/v1/courses/organizations/{org}", tags=["learning"])


@router.get("/catalog", response_model=LearningCatalogView)
def catalog(org: UUID, db: DB, identity: Principal) -> LearningCatalogView:
    return service.catalog(db, org, identity[0])


@router.post("", response_model=CourseView, status_code=201)
def create_course(
    org: UUID,
    data: CourseCreate,
    request: Request,
    db: DB,
    identity: Principal,
) -> CourseView:
    return service.create_course(db, org, identity[0], data, request.state.request_id)


@router.post("/{course_id}/completion-rule", response_model=CourseView)
def update_completion_rule(
    org: UUID,
    course_id: UUID,
    data: CompletionRuleUpdate,
    request: Request,
    db: DB,
    identity: Principal,
) -> CourseView:
    return service.update_completion_rule(
        db, org, course_id, identity[0], data, request.state.request_id
    )


@router.post("/prerequisites", response_model=LessonPrerequisiteView, status_code=201)
def create_prerequisite(
    org: UUID,
    data: LessonPrerequisiteCreate,
    request: Request,
    db: DB,
    identity: Principal,
) -> LessonPrerequisiteView:
    return service.create_prerequisite(db, org, identity[0], data, request.state.request_id)


@router.post("/modules", response_model=ModuleView, status_code=201)
def create_module(
    org: UUID,
    data: ModuleCreate,
    request: Request,
    db: DB,
    identity: Principal,
) -> ModuleView:
    return service.create_module(db, org, identity[0], data, request.state.request_id)


@router.post("/lessons", response_model=LessonView, status_code=201)
def create_lesson(
    org: UUID,
    data: LessonCreate,
    request: Request,
    db: DB,
    identity: Principal,
) -> LessonView:
    return service.create_lesson(db, org, identity[0], data, request.state.request_id)


@router.post("/materials", response_model=MaterialAdminView, status_code=201)
def create_material(
    org: UUID,
    data: MaterialCreate,
    request: Request,
    db: DB,
    identity: Principal,
) -> MaterialAdminView:
    return service.create_material(db, org, identity[0], data, request.state.request_id)


@router.post("/{course_id}/publish", response_model=CourseView)
def publish_course(
    org: UUID,
    course_id: UUID,
    data: PublishCourse,
    request: Request,
    db: DB,
    identity: Principal,
) -> CourseView:
    return service.publish_course(
        db,
        org,
        course_id,
        identity[0],
        data,
        request.state.request_id,
    )


@router.post("/cohort-assignments", response_model=CohortCourseView, status_code=201)
def assign_course(
    org: UUID,
    data: CohortCourseCreate,
    request: Request,
    db: DB,
    identity: Principal,
) -> CohortCourseView:
    return service.assign_course(db, org, identity[0], data, request.state.request_id)


@router.get("/my-learning", response_model=MyLearningView)
def my_learning(org: UUID, db: DB, identity: Principal) -> MyLearningView:
    return service.my_learning(db, org, identity[0])


@router.post("/my-learning/{course_id}/start", response_model=CourseEnrollmentView)
def start_course(
    org: UUID,
    course_id: UUID,
    request: Request,
    db: DB,
    identity: Principal,
) -> CourseEnrollmentView:
    return service.start_course(
        db,
        org,
        course_id,
        identity[0],
        request.state.request_id,
    )


@router.post(
    "/my-learning/{course_id}/lessons/{lesson_id}/complete",
    response_model=LessonProgressView,
)
def complete_lesson(
    org: UUID,
    course_id: UUID,
    lesson_id: UUID,
    data: LessonCompletionCommand,
    request: Request,
    db: DB,
    identity: Principal,
) -> LessonProgressView:
    return service.complete_lesson(
        db, org, course_id, lesson_id, identity[0], data, request.state.request_id
    )


@router.get("/trainer-delivery", response_model=TrainerDeliveryView)
def trainer_delivery(org: UUID, db: DB, identity: Principal) -> TrainerDeliveryView:
    return service.trainer_delivery(db, org, identity[0])


@router.post(
    "/my-learning/{course_id}/materials/{material_id}/access",
    response_model=MaterialAccessView,
)
def learner_material_access(
    org: UUID,
    course_id: UUID,
    material_id: UUID,
    request: Request,
    db: DB,
    identity: Principal,
) -> MaterialAccessView:
    return service.learner_material_access(
        db, org, course_id, material_id, identity[0], request.state.request_id
    )


@router.post(
    "/trainer-delivery/{course_id}/materials/{material_id}/access",
    response_model=MaterialAccessView,
)
def trainer_material_access(
    org: UUID,
    course_id: UUID,
    material_id: UUID,
    request: Request,
    db: DB,
    identity: Principal,
) -> MaterialAccessView:
    return service.trainer_material_access(
        db, org, course_id, material_id, identity[0], request.state.request_id
    )


@router.get("/material-delivery/{token}", response_class=FileResponse)
def material_delivery(
    org: UUID,
    token: str,
    request: Request,
    db: DB,
    identity: Principal,
) -> FileResponse:
    material = service.deliver_material(db, org, token, identity[0], request.state.request_id)
    return FileResponse(
        material.path,
        media_type=material.media_type,
        filename=material.filename,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
