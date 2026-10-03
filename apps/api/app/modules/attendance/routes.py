from uuid import UUID

from fastapi import APIRouter, Request

from app.modules.attendance import service
from app.modules.attendance.schemas import (
    CheckInCommand,
    CorrectionCommand,
    ManualMark,
    MyAttendanceView,
    PolicyUpdate,
    PolicyView,
    RecordView,
    StaffAttendanceWorkspace,
    WindowClose,
    WindowCreate,
    WindowCreatedView,
    WindowView,
)
from app.modules.identity.routes import DB, Principal

router = APIRouter(prefix="/api/v1/attendance/organizations/{org}", tags=["attendance"])


@router.get("/staff-workspace", response_model=StaffAttendanceWorkspace)
def staff_workspace(org: UUID, db: DB, identity: Principal) -> StaffAttendanceWorkspace:
    return service.staff_workspace(db, org, identity[0])


@router.put("/policy", response_model=PolicyView)
def update_policy(
    org: UUID, data: PolicyUpdate, request: Request, db: DB, identity: Principal
) -> PolicyView:
    return service.update_policy(db, org, identity[0], data, request.state.request_id)


@router.post("/windows", response_model=WindowCreatedView, status_code=201)
def create_window(
    org: UUID, data: WindowCreate, request: Request, db: DB, identity: Principal
) -> WindowCreatedView:
    return service.create_window(db, org, identity[0], data, request.state.request_id)


@router.post("/windows/{window_id}/close", response_model=WindowView)
def close_window(
    org: UUID,
    window_id: UUID,
    data: WindowClose,
    request: Request,
    db: DB,
    identity: Principal,
) -> WindowView:
    return service.close_window(db, org, window_id, identity[0], data, request.state.request_id)


@router.post("/sessions/{session_id}/records", response_model=RecordView, status_code=201)
def manual_mark(
    org: UUID,
    session_id: UUID,
    data: ManualMark,
    request: Request,
    db: DB,
    identity: Principal,
) -> RecordView:
    return service.manual_mark(db, org, session_id, identity[0], data, request.state.request_id)


@router.post("/records/{record_id}/correct", response_model=RecordView)
def correct_record(
    org: UUID,
    record_id: UUID,
    data: CorrectionCommand,
    request: Request,
    db: DB,
    identity: Principal,
) -> RecordView:
    return service.correct_record(db, org, record_id, identity[0], data, request.state.request_id)


@router.get("/my-attendance", response_model=MyAttendanceView)
def my_attendance(org: UUID, db: DB, identity: Principal) -> MyAttendanceView:
    return service.my_attendance(db, org, identity[0])


@router.post("/check-in", response_model=RecordView, status_code=201)
def check_in(
    org: UUID, data: CheckInCommand, request: Request, db: DB, identity: Principal
) -> RecordView:
    return service.check_in(db, org, identity[0], data, request.state.request_id)
