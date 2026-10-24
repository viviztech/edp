import re
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from app.modules.files import service as files
from app.modules.files.http import bounded_upload, private_download
from app.modules.files.runtime import get_private_storage, require_files_enabled
from app.modules.identity.routes import DB, Principal, principal
from app.modules.identity.security import AuthError
from app.modules.lms import file_service as service
from app.modules.lms import service as learning
from app.modules.lms.file_schemas import (
    AssignmentFileIntent,
    AssignmentFileList,
    AssignmentFileRuleCommand,
    AssignmentFileRuleView,
    AssignmentFileView,
    LearningFileRemove,
    MaterialFileIntent,
    MaterialFileList,
    MaterialFileView,
)

router = APIRouter(prefix="/api/v1/courses/organizations/{org}", tags=["learning-files"])


def expected_version(value: str | None) -> int:
    if value is None or not re.fullmatch(r'"[1-9][0-9]{0,9}"', value):
        raise AuthError("file_version_required", 422)
    return int(value[1:-1])


@router.get(
    "/my-learning/{course_id}/assignments/{assignment_id}/files", response_model=AssignmentFileList
)
def assignment_files(
    org: UUID, course_id: UUID, assignment_id: UUID, db: DB, identity: Principal
) -> AssignmentFileList:
    return service.assignment_files(db, org, course_id, assignment_id, identity[0])


@router.post(
    "/my-learning/{course_id}/assignments/{assignment_id}/files",
    response_model=AssignmentFileView,
    status_code=201,
)
def create_assignment_file(
    org: UUID,
    course_id: UUID,
    assignment_id: UUID,
    data: AssignmentFileIntent,
    request: Request,
    db: DB,
    identity: Principal,
) -> AssignmentFileView:
    return service.create_assignment_file(
        db, org, course_id, assignment_id, identity[0], data, request.state.request_id
    )


@router.get(
    "/my-learning/{course_id}/assignments/{assignment_id}/files/{binding_id}",
    response_model=AssignmentFileView,
)
def assignment_file(
    org: UUID, course_id: UUID, assignment_id: UUID, binding_id: UUID, db: DB, identity: Principal
) -> AssignmentFileView:
    row, _ = service.owned_assignment_file(
        db, org, course_id, assignment_id, binding_id, identity[0]
    )
    return service._assignment_file_view(db, row)


@router.delete(
    "/my-learning/{course_id}/assignments/{assignment_id}/files/{binding_id}",
    response_model=AssignmentFileView,
)
def remove_assignment_file(
    org: UUID,
    course_id: UUID,
    assignment_id: UUID,
    binding_id: UUID,
    data: LearningFileRemove,
    request: Request,
    db: DB,
    identity: Principal,
) -> AssignmentFileView:
    return service.remove_assignment_file(
        db,
        org,
        course_id,
        assignment_id,
        binding_id,
        identity[0],
        data.expected_version,
        request.state.request_id,
    )


@router.put(
    "/my-learning/{course_id}/assignments/{assignment_id}/files/{binding_id}/content",
    response_model=AssignmentFileView,
)
async def upload_assignment_file(
    org: UUID,
    course_id: UUID,
    assignment_id: UUID,
    binding_id: UUID,
    request: Request,
    db: DB,
    identity: Principal,
    if_match: Annotated[str | None, Header()] = None,
) -> AssignmentFileView:
    settings = require_files_enabled()
    version = expected_version(if_match)
    _, file = await run_in_threadpool(
        service.owned_assignment_file,
        db,
        org,
        course_id,
        assignment_id,
        binding_id,
        identity[0],
        writing=True,
    )
    if file.version != version:
        raise AuthError("version_conflict", 409)
    media_type, byte_size = file.expected_media_type, file.expected_byte_size
    await run_in_threadpool(db.rollback)
    async with bounded_upload(
        request,
        media_type=media_type,
        byte_size=byte_size,
        settings=settings,
    ) as source:

        def receive() -> AssignmentFileView:
            db.expire_all()
            actor, _ = principal(request, db)
            row, current = service.owned_assignment_file(
                db, org, course_id, assignment_id, binding_id, actor, writing=True, lock=True
            )
            ctx = files.AuthorizedFileContext(
                actor.id, org, row.owner_person_id, "assignment_submission", row.id
            )
            lease = files.begin_upload(
                db,
                ctx,
                actor,
                current.id,
                version,
                request.state.request_id,
                settings.files_upload_lease_seconds,
            )
            files.receive_upload(
                db,
                ctx,
                actor,
                lease,
                source,
                get_private_storage(settings),
                request.state.request_id,
            )
            return service._assignment_file_view(db, row)

        return await run_in_threadpool(receive)


@router.get("/my-learning/{course_id}/assignments/{assignment_id}/files/{binding_id}/content")
async def download_assignment_file(
    org: UUID,
    course_id: UUID,
    assignment_id: UUID,
    binding_id: UUID,
    request: Request,
    db: DB,
    identity: Principal,
) -> StreamingResponse:
    require_files_enabled()

    def prepare() -> StreamingResponse:
        row, file = service.owned_assignment_file(
            db, org, course_id, assignment_id, binding_id, identity[0]
        )
        if row.state == "removed":
            raise AuthError("not_found", 404)
        ref = (
            service._pinned_reference(row, file)
            if row.state == "submitted"
            else service.clean_reference(file)
        )
        return private_download(get_private_storage(), ref, file.id)

    response = await run_in_threadpool(prepare)
    try:

        def reauthorize() -> None:
            db.expire_all()
            actor, _ = principal(request, db)
            row, file = service.owned_assignment_file(
                db, org, course_id, assignment_id, binding_id, actor
            )
            if row.state == "removed":
                raise AuthError("not_found", 404)
            service.clean_reference(file)
            learning._audit(
                db,
                actor,
                org,
                row.id,
                "lms.assignment.file_downloaded",
                request.state.request_id,
                row.version,
                "file_id",
            )
            learning._commit(db)

        await run_in_threadpool(reauthorize)
        return response
    except BaseException:
        if response.background:
            await response.background()
        raise


@router.get(
    "/trainer-delivery/{course_id}/assignment-submissions/{submission_id}/files",
    response_model=list[AssignmentFileView],
)
def trainer_files(
    org: UUID, course_id: UUID, submission_id: UUID, db: DB, identity: Principal
) -> list[AssignmentFileView]:
    return service.trainer_submission_files(db, org, course_id, submission_id, identity[0])


@router.get(
    "/trainer-delivery/{course_id}/assignment-submissions/{submission_id}/files/{binding_id}/content"
)
async def trainer_file_download(
    org: UUID,
    course_id: UUID,
    submission_id: UUID,
    binding_id: UUID,
    request: Request,
    db: DB,
    identity: Principal,
) -> StreamingResponse:
    require_files_enabled()

    def prepare() -> StreamingResponse:
        row, file = service.trainer_assignment_file(
            db, org, course_id, submission_id, binding_id, identity[0]
        )
        return private_download(
            get_private_storage(), service._pinned_reference(row, file), file.id
        )

    response = await run_in_threadpool(prepare)
    try:

        def reauthorize() -> None:
            db.expire_all()
            actor, _ = principal(request, db)
            row, file = service.trainer_assignment_file(
                db, org, course_id, submission_id, binding_id, actor
            )
            learning._audit(
                db,
                actor,
                org,
                row.id,
                "lms.assignment.file_downloaded",
                request.state.request_id,
                file.version,
                "file_id",
            )
            learning._commit(db)

        await run_in_threadpool(reauthorize)
        return response
    except BaseException:
        if response.background:
            await response.background()
        raise


@router.get(
    "/courses/{course_id}/assignments/{assignment_id}/file-rule",
    response_model=AssignmentFileRuleView | None,
)
def get_file_rule(
    org: UUID, course_id: UUID, assignment_id: UUID, db: DB, identity: Principal
) -> AssignmentFileRuleView | None:
    from sqlalchemy import select

    from app.modules.identity.service import require_permission
    from app.modules.lms.file_models import AssignmentFileRule

    require_permission(db, identity[0], org, "lms.assessment.manage")
    learning._course(db, org, course_id)
    row = db.scalar(
        select(AssignmentFileRule).where(
            AssignmentFileRule.assignment_id == assignment_id,
            AssignmentFileRule.course_id == course_id,
            AssignmentFileRule.organization_id == org,
        )
    )
    return service.rule_view(db, org, row) if row else None


@router.put(
    "/courses/{course_id}/assignments/{assignment_id}/file-rule",
    response_model=AssignmentFileRuleView,
)
def configure_file_rule(
    org: UUID,
    course_id: UUID,
    assignment_id: UUID,
    data: AssignmentFileRuleCommand,
    request: Request,
    db: DB,
    identity: Principal,
) -> AssignmentFileRuleView:
    return service.configure_rule(
        db, org, course_id, assignment_id, identity[0], data, request.state.request_id
    )


@router.get("/courses/{course_id}/material-files", response_model=MaterialFileList)
def material_files(
    org: UUID,
    course_id: UUID,
    db: DB,
    identity: Principal,
    cursor: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> MaterialFileList:
    return service.material_files(db, org, course_id, identity[0], cursor, limit)


@router.post("/material-files", response_model=MaterialFileView, status_code=201)
def create_material_file(
    org: UUID, data: MaterialFileIntent, request: Request, db: DB, identity: Principal
) -> MaterialFileView:
    return service.create_material_file(db, org, identity[0], data, request.state.request_id)


@router.get("/courses/{course_id}/material-files/{material_id}", response_model=MaterialFileView)
def material_file(
    org: UUID, course_id: UUID, material_id: UUID, db: DB, identity: Principal
) -> MaterialFileView:
    row, _ = service.author_material_file(
        db, org, course_id, material_id, identity[0], include_removed=True
    )
    return service._material_view(db, row)


@router.delete("/courses/{course_id}/material-files/{material_id}", response_model=MaterialFileView)
def remove_material_file(
    org: UUID,
    course_id: UUID,
    material_id: UUID,
    data: LearningFileRemove,
    request: Request,
    db: DB,
    identity: Principal,
) -> MaterialFileView:
    return service.remove_material_file(
        db,
        org,
        course_id,
        material_id,
        identity[0],
        data.expected_version,
        request.state.request_id,
    )


@router.put(
    "/courses/{course_id}/material-files/{material_id}/content", response_model=MaterialFileView
)
async def upload_material_file(
    org: UUID,
    course_id: UUID,
    material_id: UUID,
    request: Request,
    db: DB,
    identity: Principal,
    if_match: Annotated[str | None, Header()] = None,
) -> MaterialFileView:
    settings = require_files_enabled()
    version = expected_version(if_match)
    _, file = await run_in_threadpool(
        service.author_material_file, db, org, course_id, material_id, identity[0], writing=True
    )
    if file.version != version:
        raise AuthError("version_conflict", 409)
    media_type, byte_size = file.expected_media_type, file.expected_byte_size
    await run_in_threadpool(db.rollback)
    async with bounded_upload(
        request,
        media_type=media_type,
        byte_size=byte_size,
        settings=settings,
    ) as source:

        def receive() -> MaterialFileView:
            db.expire_all()
            actor, _ = principal(request, db)
            row, current = service.author_material_file(
                db, org, course_id, material_id, actor, writing=True, lock=True
            )
            ctx = files.AuthorizedFileContext(
                actor.id, org, row.owner_person_id, "lms_material", material_id
            )
            lease = files.begin_upload(
                db,
                ctx,
                actor,
                current.id,
                version,
                request.state.request_id,
                settings.files_upload_lease_seconds,
            )
            files.receive_upload(
                db,
                ctx,
                actor,
                lease,
                source,
                get_private_storage(settings),
                request.state.request_id,
            )
            return service._material_view(db, row)

        return await run_in_threadpool(receive)


@router.get("/courses/{course_id}/material-files/{material_id}/content")
async def download_author_material(
    org: UUID, course_id: UUID, material_id: UUID, request: Request, db: DB, identity: Principal
) -> StreamingResponse:
    require_files_enabled()

    def prepare() -> StreamingResponse:
        _, file = service.author_material_file(db, org, course_id, material_id, identity[0])
        return private_download(get_private_storage(), service.clean_reference(file), file.id)

    response = await run_in_threadpool(prepare)
    try:

        def reauthorize() -> None:
            db.expire_all()
            actor, _ = principal(request, db)
            _, file = service.author_material_file(db, org, course_id, material_id, actor)
            service.clean_reference(file)

        await run_in_threadpool(reauthorize)
        return response
    except BaseException:
        if response.background:
            await response.background()
        raise
