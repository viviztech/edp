from io import BytesIO
from uuid import UUID

import qrcode
import qrcode.image.svg
from fastapi import APIRouter, Path, Request
from fastapi.responses import FileResponse, Response

from app.modules.identity.routes import DB, Principal
from app.modules.lms import service
from app.modules.lms.schemas import (
    AssignmentCreate,
    AssignmentGradeCommand,
    AssignmentGradeView,
    AssignmentSubmissionCreate,
    AssignmentSubmissionView,
    CertificateIssueCommand,
    CertificateRevokeCommand,
    CertificateTemplateCreate,
    CertificateTemplatePublish,
    CertificateTemplateView,
    CertificateView,
    CohortCourseCreate,
    CohortCourseView,
    CompletionRuleUpdate,
    CourseCreate,
    CourseEnrollmentView,
    CourseView,
    LearningAssignmentView,
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
    PublicCertificateView,
    PublishCourse,
    QuizAttemptSubmit,
    QuizAttemptView,
    QuizChoiceAdminView,
    QuizChoiceCreate,
    QuizCreate,
    QuizQuestionCreate,
    QuizQuestionView,
    QuizView,
    TrainerDeliveryView,
)

router = APIRouter(prefix="/api/v1/courses/organizations/{org}", tags=["learning"])
public_router = APIRouter(prefix="/api/v1/certificates", tags=["certificates"])


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


@router.post("/quizzes", response_model=QuizView, status_code=201)
def create_quiz(
    org: UUID,
    data: QuizCreate,
    request: Request,
    db: DB,
    identity: Principal,
) -> QuizView:
    return service.create_quiz(db, org, identity[0], data, request.state.request_id)


@router.post("/quiz-questions", response_model=QuizQuestionView, status_code=201)
def create_quiz_question(
    org: UUID,
    data: QuizQuestionCreate,
    request: Request,
    db: DB,
    identity: Principal,
) -> QuizQuestionView:
    return service.create_quiz_question(db, org, identity[0], data, request.state.request_id)


@router.post("/quiz-choices", response_model=QuizChoiceAdminView, status_code=201)
def create_quiz_choice(
    org: UUID,
    data: QuizChoiceCreate,
    request: Request,
    db: DB,
    identity: Principal,
) -> QuizChoiceAdminView:
    return service.create_quiz_choice(db, org, identity[0], data, request.state.request_id)


@router.post(
    "/my-learning/{course_id}/quizzes/{quiz_id}/attempts",
    response_model=QuizAttemptView,
    status_code=201,
)
def submit_quiz_attempt(
    org: UUID,
    course_id: UUID,
    quiz_id: UUID,
    data: QuizAttemptSubmit,
    request: Request,
    db: DB,
    identity: Principal,
) -> QuizAttemptView:
    return service.submit_quiz_attempt(
        db,
        org,
        course_id,
        quiz_id,
        identity[0],
        data,
        request.state.request_id,
    )


@router.post("/assignments", response_model=LearningAssignmentView, status_code=201)
def create_learning_assignment(
    org: UUID,
    data: AssignmentCreate,
    request: Request,
    db: DB,
    identity: Principal,
) -> LearningAssignmentView:
    return service.create_learning_assignment(db, org, identity[0], data, request.state.request_id)


@router.post(
    "/my-learning/{course_id}/assignments/{assignment_id}/submissions",
    response_model=AssignmentSubmissionView,
    status_code=201,
)
def submit_assignment(
    org: UUID,
    course_id: UUID,
    assignment_id: UUID,
    data: AssignmentSubmissionCreate,
    request: Request,
    db: DB,
    identity: Principal,
) -> AssignmentSubmissionView:
    return service.submit_assignment(
        db,
        org,
        course_id,
        assignment_id,
        identity[0],
        data,
        request.state.request_id,
    )


@router.post(
    "/trainer-delivery/{course_id}/assignment-submissions/{submission_id}/grade",
    response_model=AssignmentGradeView,
    status_code=201,
)
def grade_assignment_submission(
    org: UUID,
    course_id: UUID,
    submission_id: UUID,
    data: AssignmentGradeCommand,
    request: Request,
    db: DB,
    identity: Principal,
) -> AssignmentGradeView:
    return service.grade_assignment_submission(
        db,
        org,
        course_id,
        submission_id,
        identity[0],
        data,
        request.state.request_id,
    )


@router.post("/certificate-templates", response_model=CertificateTemplateView, status_code=201)
def create_certificate_template(
    org: UUID,
    data: CertificateTemplateCreate,
    request: Request,
    db: DB,
    identity: Principal,
) -> CertificateTemplateView:
    return service.create_certificate_template(
        db, org, identity[0], data, request.state.request_id
    )


@router.post(
    "/certificate-templates/{template_id}/publish",
    response_model=CertificateTemplateView,
)
def publish_certificate_template(
    org: UUID,
    template_id: UUID,
    data: CertificateTemplatePublish,
    request: Request,
    db: DB,
    identity: Principal,
) -> CertificateTemplateView:
    return service.publish_certificate_template(
        db, org, template_id, identity[0], data, request.state.request_id
    )


@router.post("/certificates/issue", response_model=CertificateView, status_code=201)
def issue_certificate(
    org: UUID,
    data: CertificateIssueCommand,
    request: Request,
    db: DB,
    identity: Principal,
) -> CertificateView:
    return service.issue_certificate(db, org, identity[0], data, request.state.request_id)


@router.post("/certificates/{certificate_id}/revoke", response_model=CertificateView)
def revoke_certificate(
    org: UUID,
    certificate_id: UUID,
    data: CertificateRevokeCommand,
    request: Request,
    db: DB,
    identity: Principal,
) -> CertificateView:
    return service.revoke_certificate(
        db, org, certificate_id, identity[0], data, request.state.request_id
    )


@public_router.get("/verify/{verification_code}", response_model=PublicCertificateView)
def verify_certificate(
    db: DB,
    verification_code: str = Path(min_length=20, max_length=48, pattern=r"^[A-Za-z0-9_-]+$"),
) -> PublicCertificateView:
    return service.verify_certificate(db, verification_code)


@public_router.get("/verify/{verification_code}/qr", response_class=Response)
def certificate_qr(
    request: Request,
    db: DB,
    verification_code: str = Path(min_length=20, max_length=48, pattern=r"^[A-Za-z0-9_-]+$"),
) -> Response:
    service.verify_certificate(db, verification_code)
    target = str(request.url_for("verify_certificate", verification_code=verification_code))
    image = qrcode.make(target, image_factory=qrcode.image.svg.SvgPathImage)
    output = BytesIO()
    image.save(output)
    return Response(
        content=output.getvalue(),
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "public, max-age=300",
            "X-Content-Type-Options": "nosniff",
        },
    )
