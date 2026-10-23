from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Path, Query, Request, Response

from app.modules.identity.routes import DB, Principal
from app.modules.reports import service
from app.modules.reports.schemas import (
    ImpactDefinitionCommand,
    ImpactDefinitionCreate,
    ImpactDefinitionList,
    ImpactDefinitionView,
    ImpactMine,
    ImpactRecordCreate,
    ImpactRecordView,
    ReportDashboard,
    ReportDefinitions,
    ReportExportAccess,
    ReportExportCreate,
    ReportExportList,
    ReportExportView,
    ReportFilters,
    ReportOptions,
    ReportSnapshotCreate,
    ReportSnapshotList,
    ReportSnapshotView,
)

router = APIRouter(prefix="/api/v1/reports/organizations/{org}", tags=["reports"])
impact_router = APIRouter(prefix="/api/v1/impact/organizations/{org}", tags=["impact"])
Limit = Annotated[int, Query(ge=1, le=100)]
Filters = Annotated[ReportFilters, Query()]


@router.get("/options", response_model=ReportOptions)
def options(
    org: UUID,
    db: DB,
    identity: Principal,
    program_cursor: UUID | None = None,
    cohort_cursor: UUID | None = None,
    program_id: UUID | None = None,
    limit: Limit = 25,
) -> ReportOptions:
    return service.report_options(
        db,
        org,
        identity[0],
        program_cursor=program_cursor,
        cohort_cursor=cohort_cursor,
        program_id=program_id,
        limit=limit,
    )


@router.get("/dashboard", response_model=ReportDashboard)
def dashboard(
    org: UUID, db: DB, identity: Principal, filters: Filters, request: Request
) -> ReportDashboard:
    return service.dashboard(db, org, identity[0], filters, request.state.request_id)


@router.get("/definitions", response_model=ReportDefinitions)
def definitions(
    org: UUID, db: DB, identity: Principal, cursor: UUID | None = None, limit: Limit = 25
) -> ReportDefinitions:
    return service.definitions(db, org, identity[0], cursor, limit)


@router.get("/snapshots", response_model=ReportSnapshotList)
def snapshots(
    org: UUID,
    db: DB,
    identity: Principal,
    request: Request,
    cursor: UUID | None = None,
    limit: Limit = 25,
) -> ReportSnapshotList:
    return service.snapshots(db, org, identity[0], cursor, limit, request.state.request_id)


@router.post("/snapshots", response_model=ReportSnapshotView, status_code=201)
def create_snapshot(
    org: UUID, db: DB, identity: Principal, data: ReportSnapshotCreate, request: Request
) -> ReportSnapshotView:
    return service.create_snapshot(db, org, identity[0], data, request.state.request_id)


@router.get("/snapshots/{key}", response_model=ReportSnapshotView)
def snapshot(
    org: UUID, key: UUID, db: DB, identity: Principal, request: Request
) -> ReportSnapshotView:
    return service.snapshot_detail(db, org, key, identity[0], request.state.request_id)


@router.get("/exports", response_model=ReportExportList)
def exports(
    org: UUID, db: DB, identity: Principal, cursor: UUID | None = None, limit: Limit = 25
) -> ReportExportList:
    return service.exports(db, org, identity[0], cursor, limit)


@router.post("/exports", response_model=ReportExportView, status_code=201)
def create_export(
    org: UUID, db: DB, identity: Principal, data: ReportExportCreate, request: Request
) -> ReportExportView:
    return service.create_export(db, org, identity[0], data, request.state.request_id)


@router.get("/exports/{key}", response_model=ReportExportView)
def export(org: UUID, key: UUID, db: DB, identity: Principal) -> ReportExportView:
    return service.export_detail(db, org, key, identity[0])


@router.post("/exports/{key}/access", response_model=ReportExportAccess)
def access(
    org: UUID, key: UUID, db: DB, identity: Principal, request: Request
) -> ReportExportAccess:
    return service.export_access(db, org, key, identity[0], request.state.request_id)


@router.get(
    "/exports/{key}/download/{token}",
    response_class=Response,
    responses={200: {"content": {"text/csv": {"schema": {"type": "string"}}}}},
)
def download(
    org: UUID,
    key: UUID,
    token: Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{43}$")],
    db: DB,
    identity: Principal,
    request: Request,
) -> Response:
    return Response(
        service.export_download(db, org, key, token, identity[0], request.state.request_id),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="edp-report-{key}.csv"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
        },
    )


@impact_router.get("/definitions", response_model=ImpactDefinitionList)
def impact_definitions(
    org: UUID,
    db: DB,
    identity: Principal,
    cursor: UUID | None = None,
    limit: Limit = 25,
    state: Literal["draft", "published", "archived"] | None = None,
) -> ImpactDefinitionList:
    return service.definition_listing(db, org, identity[0], cursor=cursor, limit=limit, state=state)


@impact_router.post("/definitions", response_model=ImpactDefinitionView, status_code=201)
def create_definition(
    org: UUID, data: ImpactDefinitionCreate, db: DB, identity: Principal, request: Request
) -> ImpactDefinitionView:
    return service.create_definition(db, org, identity[0], data, request.state.request_id)


@impact_router.post("/definitions/{key}/publish", response_model=ImpactDefinitionView)
def publish(
    org: UUID,
    key: UUID,
    data: ImpactDefinitionCommand,
    db: DB,
    identity: Principal,
    request: Request,
) -> ImpactDefinitionView:
    return service.command_definition(
        db, org, key, identity[0], data, "published", request.state.request_id
    )


@impact_router.post("/definitions/{key}/archive", response_model=ImpactDefinitionView)
def archive(
    org: UUID,
    key: UUID,
    data: ImpactDefinitionCommand,
    db: DB,
    identity: Principal,
    request: Request,
) -> ImpactDefinitionView:
    return service.command_definition(
        db, org, key, identity[0], data, "archived", request.state.request_id
    )


@impact_router.get("/mine", response_model=ImpactMine)
def mine(
    org: UUID,
    db: DB,
    identity: Principal,
    enrollment_cursor: UUID | None = None,
    definition_cursor: UUID | None = None,
    record_cursor: UUID | None = None,
    limit: Limit = 25,
    enrollment_id: UUID | None = None,
    stage: Literal["baseline", "outcome"] | None = None,
    observed_on: date | None = None,
) -> ImpactMine:
    return service.mine(
        db,
        org,
        identity[0],
        enrollment_cursor=enrollment_cursor,
        definition_cursor=definition_cursor,
        record_cursor=record_cursor,
        limit=limit,
        enrollment_id=enrollment_id,
        stage=stage,
        observed_on=observed_on,
    )


@impact_router.post("/records", response_model=ImpactRecordView, status_code=201)
def record(
    org: UUID, data: ImpactRecordCreate, db: DB, identity: Principal, request: Request
) -> ImpactRecordView:
    return service.create_record(db, org, identity[0], data, request.state.request_id)
