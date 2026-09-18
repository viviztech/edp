import secrets
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.identity import service
from app.modules.identity.models import AuditLog, Organization, RefreshSession, User, now
from app.modules.identity.repository import database
from app.modules.identity.schemas import (
    AuditView,
    BrowserTokens,
    EmailInput,
    Login,
    Message,
    Profile,
    Register,
    Reset,
    SessionView,
    StaffView,
    TokenInput,
    Tokens,
)
from app.modules.identity.security import AuthError

router = APIRouter(prefix="/api/v1", tags=["identity"])
DB = Annotated[Session, Depends(database)]


def check_bff(request: Request) -> None:
    configured = get_settings().bff_key
    supplied = request.headers.get("X-BFF-Key", "")
    if not configured or not secrets.compare_digest(supplied, configured.get_secret_value()):
        raise AuthError("invalid_client", 403)


def principal(request: Request, db: DB) -> tuple[User, RefreshSession]:
    browser = request.headers.get("X-Browser-Session")
    if browser:
        check_bff(request)
        return service.authenticate(
            db,
            browser,
            True,
            request.headers.get("X-CSRF-Token"),
            request.method not in {"GET", "HEAD"},
        )
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer ") or len(header) > 512:
        raise AuthError("invalid_session")
    return service.authenticate(db, header[7:], False)


Principal = Annotated[tuple[User, RefreshSession], Depends(principal)]


def limit(request: Request, db: Session, operation: str, identifier: str = "") -> None:
    address = request.client.host if request.client else "unknown"
    service.throttle(db, f"{operation}:source", address, 120 if operation == "refresh" else 60)
    if identifier:
        service.throttle(db, operation, identifier, 30 if operation == "refresh" else 10)


@router.post("/auth/register", response_model=Message, status_code=202)
def register(data: Register, request: Request, db: DB) -> Message:
    limit(request, db, "register", str(data.email))
    service.register(db, data, request.state.request_id)
    return Message()


@router.post("/auth/login", response_model=Tokens)
def login(data: Login, request: Request, db: DB) -> Tokens:
    limit(request, db, "login", str(data.email))
    result = service.login(db, data, request.state.request_id)
    assert isinstance(result, Tokens)
    return result


@router.post("/auth/browser/login", response_model=BrowserTokens, include_in_schema=False)
def browser_login(data: Login, request: Request, db: DB) -> BrowserTokens:
    check_bff(request)
    limit(request, db, "login", str(data.email))
    result = service.login(db, data, request.state.request_id, browser=True)
    assert isinstance(result, BrowserTokens)
    return result


@router.post("/auth/refresh", response_model=Tokens)
def refresh(data: TokenInput, request: Request, db: DB) -> Tokens:
    limit(request, db, "refresh", data.token.get_secret_value())
    return service.refresh(db, data.token.get_secret_value(), request.state.request_id)


@router.post("/auth/request-verification", response_model=Message, status_code=202)
def request_verification(data: EmailInput, request: Request, db: DB) -> Message:
    limit(request, db, "challenge", str(data.email))
    service.request_challenge(db, str(data.email), "verify", request.state.request_id)
    return Message()


@router.post("/auth/request-reset", response_model=Message, status_code=202)
def request_reset(data: EmailInput, request: Request, db: DB) -> Message:
    limit(request, db, "challenge", str(data.email))
    service.request_challenge(db, str(data.email), "reset", request.state.request_id)
    return Message()


@router.post("/auth/verify", response_model=Message)
def verify(data: TokenInput, request: Request, db: DB) -> Message:
    limit(request, db, "consume")
    service.consume_challenge(db, data.token.get_secret_value(), "verify", request.state.request_id)
    return Message(status="verified")


@router.post("/auth/reset", response_model=Message)
def reset(data: Reset, request: Request, db: DB) -> Message:
    limit(request, db, "consume")
    service.consume_challenge(
        db,
        data.token.get_secret_value(),
        "reset",
        request.state.request_id,
        data.password.get_secret_value(),
    )
    return Message(status="reset")


@router.get("/auth/me", response_model=Profile)
def me(db: DB, identity: Principal) -> Profile:
    return service.profile(db, identity[0])


@router.get("/auth/sessions", response_model=list[SessionView])
def sessions(db: DB, identity: Principal) -> list[SessionView]:
    user, current = identity
    records = db.scalars(
        select(RefreshSession)
        .where(
            RefreshSession.user_id == user.id,
            RefreshSession.revoked_at.is_(None),
            RefreshSession.expires_at > now(),
        )
        .order_by(RefreshSession.created_at.desc())
        .limit(100)
    )
    return [
        SessionView(
            id=item.id,
            device_name=item.device_name,
            channel=item.channel,
            created_at=item.created_at,
            expires_at=item.expires_at,
            current=item.id == current.id,
        )
        for item in records
    ]


@router.post("/auth/logout", response_model=Message)
def logout(request: Request, db: DB, identity: Principal) -> Message:
    service.revoke(db, *identity, request.state.request_id)
    return Message(status="signed_out")


@router.post("/auth/logout-all", response_model=Message)
def logout_all(request: Request, db: DB, identity: Principal) -> Message:
    service.revoke(db, *identity, request.state.request_id, all_devices=True)
    return Message(status="signed_out")


@router.post("/auth/sessions/{session_id}/revoke", response_model=Message)
def revoke(session_id: UUID, request: Request, db: DB, identity: Principal) -> Message:
    service.revoke(db, *identity, request.state.request_id, target=session_id)
    return Message()


@router.get(
    "/system/organizations/{organization_id}/access", response_model=StaffView, tags=["system"]
)
def staff(organization_id: UUID, db: DB, identity: Principal) -> StaffView:
    service.require_permission(db, identity[0], organization_id, "system.access")
    organization = db.get(Organization, organization_id)
    assert organization is not None
    return StaffView(organization_id=organization.id, organization_name=organization.name)


@router.get(
    "/system/organizations/{organization_id}/audit", response_model=list[AuditView], tags=["system"]
)
def audit(
    organization_id: UUID,
    request: Request,
    db: DB,
    identity: Principal,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> list[AuditView]:
    service.require_permission(db, identity[0], organization_id, "audit.view")
    # Identity events have no org ownership; do not expose them to arbitrary org staff.
    rows = list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.organization_id == organization_id)
            .order_by(AuditLog.created_at.desc(), AuditLog.id)
            .offset(offset)
            .limit(limit)
        )
    )
    service.audit(
        db, "audit.viewed", request.state.request_id, identity[0].id, organization=organization_id
    )
    db.commit()
    return [AuditView.model_validate(row) for row in rows]
