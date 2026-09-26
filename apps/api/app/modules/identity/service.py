import json
import secrets
from datetime import timedelta
from uuid import UUID

from cryptography.fernet import Fernet
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.identity.models import (
    AuditLog,
    AuthDelivery,
    AuthThrottle,
    Organization,
    Permission,
    Person,
    RefreshSession,
    RefreshToken,
    Role,
    RolePermission,
    User,
    UserRole,
    VerificationToken,
    now,
)
from app.modules.identity.schemas import BrowserTokens, Grant, Login, Profile, Register, Tokens
from app.modules.identity.security import (
    DUMMY_HASH,
    AuthError,
    digest,
    hasher,
    token,
    verify_password,
)

ROLE_NAMES = [
    "Super Admin",
    "Program Director",
    "Program Manager",
    "CRM Executive",
    "Marketing Executive",
    "Selection Committee",
    "Trainer",
    "Mentor",
    "Training Center Coordinator",
    "Funding Coordinator",
    "Content Manager",
    "Support Executive",
    "Participant",
]
CMS_PERMISSIONS = [
    "cms.page." + action for action in ("view", "create", "update", "publish", "archive")
]
CMS_PERMISSIONS += [
    "cms.editorial." + action for action in ("view", "create", "update", "publish", "archive")
]
CMS_PERMISSIONS += ["cms.asset." + action for action in ("view", "create", "publish")]
ENQUIRY_PERMISSIONS = ["enquiry.view"]
NOTIFICATION_OPERATIONS_PERMISSIONS = [
    "notification.operations.view",
    "notification.operations.replay",
]
META_PERMISSIONS = ["meta.integration." + action for action in ("view", "manage", "replay")]
APPLICATION_PERMISSIONS = [
    "application.form." + action for action in ("view", "create", "update", "publish")
]
PROGRAM_PERMISSIONS = [
    "program.view",
    "program.manage",
    "cohort.manage",
    "application.cycle.manage",
]
PROGRAM_DELIVERY_PERMISSIONS = [
    "participant.view",
    "participant.update",
    "enrollment.manage",
    "schedule.manage",
    "staff.assignment.manage",
]
PARTICIPANT_SELF_PERMISSION = "participant.self"
LMS_STAFF_PERMISSIONS = [
    "lms.course.view",
    "lms.course.manage",
    "lms.course.publish",
    "lms.course.assign",
]
LMS_LEARN_PERMISSION = "lms.learn"
SELECTION_PERMISSIONS = [
    "selection.cycle.view",
    "selection.cycle.manage",
    "selection.rubric.manage",
    "selection.rubric.publish",
    "selection.assignment.manage",
    "selection.review",
    "selection.review.moderate",
    "selection.interview.manage",
    "selection.interview.score",
    "selection.decision.manage",
    "selection.decision.override",
    "selection.finalize",
]
CRM_PERMISSIONS = (
    [
        "crm.lead." + action
        for action in ("view", "create", "update", "assign", "merge", "convert", "export")
    ]
    + ["crm.activity." + action for action in ("view", "create", "update")]
    + ["crm.tag." + action for action in ("view", "manage")]
)
PERMISSIONS = [
    "system.access",
    "audit.view",
    *CMS_PERMISSIONS,
    *ENQUIRY_PERMISSIONS,
    *CRM_PERMISSIONS,
    *META_PERMISSIONS,
    *NOTIFICATION_OPERATIONS_PERMISSIONS,
    *APPLICATION_PERMISSIONS,
    *PROGRAM_PERMISSIONS,
    *PROGRAM_DELIVERY_PERMISSIONS,
    PARTICIPANT_SELF_PERMISSION,
    *LMS_STAFF_PERMISSIONS,
    LMS_LEARN_PERMISSION,
    *SELECTION_PERMISSIONS,
]


def audit(
    db: Session,
    action: str,
    request_id: str,
    actor: UUID | None = None,
    resource: UUID | None = None,
    organization: UUID | None = None,
) -> None:
    db.add(
        AuditLog(
            action=action,
            request_id=request_id,
            actor_id=actor,
            resource_id=resource,
            organization_id=organization,
        )
    )


def throttle(db: Session, operation: str, identifier: str, limit: int) -> None:
    current = now()
    slot = int(current.timestamp()) // 900
    key = digest(f"{operation}:{identifier}:{slot}")
    statement = insert(AuthThrottle).values(
        key=key, hits=1, expires_at=current + timedelta(minutes=30)
    )
    hits = db.scalar(
        statement.on_conflict_do_update(
            index_elements=[AuthThrottle.key], set_={"hits": AuthThrottle.hits + 1}
        ).returning(AuthThrottle.hits)
    )
    db.commit()  # Persist even when subsequent authentication fails.
    if hits is None or hits > limit:
        raise AuthError("rate_limited", 429)


def delivery_available() -> Fernet:
    settings = get_settings()
    if settings.app_env not in {"local", "test"} or not settings.auth_delivery_key:
        raise AuthError("delivery_unavailable", 503)
    return Fernet(settings.auth_delivery_key.get_secret_value().encode())


def issue_challenge(db: Session, user: User, purpose: str, request_id: str) -> None:
    cipher = delivery_available()
    db.execute(
        update(VerificationToken)
        .where(
            VerificationToken.user_id == user.id,
            VerificationToken.purpose == purpose,
            VerificationToken.consumed_at.is_(None),
        )
        .values(consumed_at=now())
    )
    raw = token()
    challenge = VerificationToken(
        user_id=user.id,
        token_hash=digest(raw),
        purpose=purpose,
        expires_at=now() + timedelta(minutes=30),
    )
    db.add(challenge)
    db.flush()
    encrypted = cipher.encrypt(
        json.dumps({"email": user.email, "purpose": purpose, "token": raw}).encode()
    ).decode()
    db.add(AuthDelivery(token_id=challenge.id, encrypted_payload=encrypted))
    audit(db, f"auth.{purpose}_requested", request_id, user.id, challenge.id)


def register(db: Session, data: Register, request_id: str) -> None:
    delivery_available()
    encoded = hasher.hash(data.password.get_secret_value())
    if db.scalar(select(User.id).where(User.email == str(data.email))):
        return
    person = Person(display_name=data.display_name, locale=data.locale)
    db.add(person)
    db.flush()
    user = User(person_id=person.id, email=str(data.email), password_hash=encoded)
    db.add(user)
    try:
        db.flush()
        issue_challenge(db, user, "verify", request_id)
        audit(db, "auth.registered", request_id, user.id, user.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        if not db.scalar(select(User.id).where(User.email == str(data.email))):
            raise  # Only a duplicate account has the generic accepted outcome.


def request_challenge(db: Session, email: str, purpose: str, request_id: str) -> None:
    delivery_available()
    user = db.scalar(select(User).where(User.email == email).with_for_update())
    expected = "pending" if purpose == "verify" else "active"
    if user and user.status == expected:
        issue_challenge(db, user, purpose, request_id)
        db.commit()


def consume_challenge(
    db: Session, raw: str, purpose: str, request_id: str, password: str | None = None
) -> None:
    found = db.scalar(select(VerificationToken).where(VerificationToken.token_hash == digest(raw)))
    if not found:
        raise AuthError("invalid_token", 400)
    user = db.scalar(select(User).where(User.id == found.user_id).with_for_update())
    challenge = db.scalar(
        select(VerificationToken)
        .where(VerificationToken.id == found.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    expected = "pending" if purpose == "verify" else "active"
    if (
        not user
        or user.status != expected
        or not challenge
        or challenge.purpose != purpose
        or challenge.consumed_at
        or challenge.expires_at <= now()
    ):
        raise AuthError("invalid_token", 400)
    challenge.consumed_at = now()
    if purpose == "verify":
        user.status = "active"
    else:
        if password is None:
            raise AuthError("invalid_request", 400)
        user.password_hash = hasher.hash(password)
        db.execute(
            update(RefreshSession)
            .where(RefreshSession.user_id == user.id, RefreshSession.revoked_at.is_(None))
            .values(revoked_at=now())
        )
        db.execute(
            update(VerificationToken)
            .where(VerificationToken.user_id == user.id, VerificationToken.purpose == "reset")
            .values(consumed_at=now())
        )
    audit(db, f"auth.{purpose}_completed", request_id, user.id, user.id)
    db.commit()


def issue_mobile_tokens(db: Session, family: RefreshSession) -> Tokens:
    settings = get_settings()
    access, refresh = token(), token()
    family.access_hash = digest(access)
    family.access_expires_at = now() + timedelta(seconds=settings.access_token_seconds)
    db.add(RefreshToken(session_id=family.id, token_hash=digest(refresh)))
    return Tokens(
        access_token=access, refresh_token=refresh, expires_in=settings.access_token_seconds
    )


def login(
    db: Session, data: Login, request_id: str, browser: bool = False
) -> Tokens | BrowserTokens:
    user = db.scalar(select(User).where(User.email == str(data.email)).with_for_update())
    valid = verify_password(
        user.password_hash if user else DUMMY_HASH, data.password.get_secret_value()
    )
    if not valid or not user or user.status != "active":
        audit(db, "auth.login_failed", request_id)
        db.commit()
        raise AuthError("invalid_credentials")
    if hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hasher.hash(data.password.get_secret_value())
    lifetime = get_settings().session_seconds
    family = RefreshSession(
        user_id=user.id,
        device_name=data.device_name,
        channel="browser" if browser else "mobile",
        expires_at=now() + timedelta(seconds=lifetime),
    )
    db.add(family)
    db.flush()
    result: Tokens | BrowserTokens
    if browser:
        cookie, csrf = token(), token()
        family.browser_hash, family.csrf_hash = digest(cookie), digest(csrf)
        result = BrowserTokens(browser_token=cookie, csrf_token=csrf, expires_in=lifetime)
    else:
        result = issue_mobile_tokens(db, family)
    audit(db, "auth.login", request_id, user.id, family.id)
    db.commit()
    return result


def refresh(db: Session, raw: str, request_id: str) -> Tokens:
    found = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == digest(raw)))
    if not found:
        raise AuthError("invalid_session")
    family = db.get(RefreshSession, found.session_id)
    if not family:
        raise AuthError("invalid_session")
    user = db.scalar(select(User).where(User.id == family.user_id).with_for_update())
    family = db.scalar(
        select(RefreshSession)
        .where(RefreshSession.id == family.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    old = db.scalar(
        select(RefreshToken)
        .where(RefreshToken.id == found.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (
        not user
        or user.status != "active"
        or not family
        or family.revoked_at
        or family.expires_at <= now()
        or not old
    ):
        raise AuthError("invalid_session")
    if old.used_at:
        family.revoked_at = now()
        audit(db, "auth.refresh_replay", request_id, user.id, family.id)
        db.commit()  # Revocation must survive the rejected response.
        raise AuthError("invalid_session")
    old.used_at = now()
    result = issue_mobile_tokens(db, family)
    audit(db, "auth.refresh", request_id, user.id, family.id)
    db.commit()
    return result


def authenticate(
    db: Session, raw: str, browser: bool, csrf: str | None = None, mutation: bool = False
) -> tuple[User, RefreshSession]:
    column = RefreshSession.browser_hash if browser else RefreshSession.access_hash
    family = db.scalar(select(RefreshSession).where(column == digest(raw)))
    if not family or family.revoked_at or family.expires_at <= now():
        raise AuthError("invalid_session")
    if not browser and (not family.access_expires_at or family.access_expires_at <= now()):
        raise AuthError("invalid_session")
    if (
        browser
        and mutation
        and (
            not csrf
            or not family.csrf_hash
            or not secrets.compare_digest(digest(csrf), family.csrf_hash)
        )
    ):
        raise AuthError("csrf_failed", 403)
    user = db.get(User, family.user_id)
    if not user or user.status != "active":
        raise AuthError("invalid_session")
    return user, family


def require_permission(db: Session, user: User, organization: UUID, permission: str) -> None:
    allowed = db.scalar(
        select(UserRole.id)
        .join(RolePermission, RolePermission.role_id == UserRole.role_id)
        .where(
            UserRole.user_id == user.id,
            UserRole.organization_id == organization,
            RolePermission.permission_code == permission,
        )
        .limit(1)
    )
    if not allowed:
        raise AuthError("forbidden", 403)


def profile(db: Session, user: User) -> Profile:
    person = db.get(Person, user.person_id)
    assert person is not None
    rows = db.execute(
        select(Organization.id, Organization.name, RolePermission.permission_code)
        .join(UserRole, UserRole.organization_id == Organization.id)
        .join(RolePermission, RolePermission.role_id == UserRole.role_id)
        .where(UserRole.user_id == user.id)
    ).all()
    grants: dict[UUID, Grant] = {}
    for org_id, name, code in rows:
        if org_id not in grants:
            grants[org_id] = Grant(organization_id=org_id, organization_name=name, permissions=[])
        if code not in grants[org_id].permissions:
            grants[org_id].permissions.append(code)
    return Profile(
        id=user.id,
        display_name=person.display_name,
        email=user.email,
        locale=person.locale,
        grants=list(grants.values()),
    )


def revoke(
    db: Session,
    user: User,
    family: RefreshSession,
    request_id: str,
    all_devices: bool = False,
    target: UUID | None = None,
) -> None:
    statement = select(RefreshSession).where(RefreshSession.user_id == user.id)
    if not all_devices:
        statement = statement.where(RefreshSession.id == (target or family.id))
    sessions = list(db.scalars(statement.with_for_update()))
    if not sessions:
        raise AuthError("not_found", 404)
    for item in sessions:
        item.revoked_at = now()
        audit(db, "auth.session_revoked", request_id, user.id, item.id)
    db.commit()


def seed_roles(db: Session) -> None:
    for code in PERMISSIONS:
        if not db.get(Permission, code):
            db.add(Permission(code=code))
    db.flush()
    for name in ROLE_NAMES:
        role = db.scalar(select(Role).where(Role.name == name))
        if not role:
            role = Role(name=name)
            db.add(role)
            db.flush()
        if name == "Super Admin":
            codes = PERMISSIONS
        elif name == "Content Manager":
            codes = ["system.access", *CMS_PERMISSIONS]
        elif name == "CRM Executive":
            codes = ["system.access", *CRM_PERMISSIONS]
        elif name == "Program Director":
            codes = [
                "system.access",
                *NOTIFICATION_OPERATIONS_PERMISSIONS,
                *APPLICATION_PERMISSIONS,
                *PROGRAM_PERMISSIONS,
                *PROGRAM_DELIVERY_PERMISSIONS,
                *LMS_STAFF_PERMISSIONS,
                *SELECTION_PERMISSIONS,
            ]
        elif name == "Program Manager":
            codes = [
                "system.access",
                *NOTIFICATION_OPERATIONS_PERMISSIONS,
                *APPLICATION_PERMISSIONS[:-1],
                *PROGRAM_PERMISSIONS,
                *PROGRAM_DELIVERY_PERMISSIONS,
                *LMS_STAFF_PERMISSIONS,
                "selection.cycle.view",
                "selection.cycle.manage",
                "selection.rubric.manage",
                "selection.assignment.manage",
                "selection.interview.manage",
                "selection.decision.manage",
            ]
        elif name == "Selection Committee":
            codes = [
                "system.access",
                "selection.cycle.view",
                "selection.review",
                "selection.interview.score",
            ]
        elif name == "Training Center Coordinator":
            codes = [
                "system.access",
                "program.view",
                "cohort.manage",
                "participant.view",
                "participant.update",
                "schedule.manage",
            ]
        elif name == "Marketing Executive":
            codes = ["system.access", *META_PERMISSIONS]
        elif name == "Participant":
            codes = [
                "system.access",
                PARTICIPANT_SELF_PERMISSION,
                LMS_LEARN_PERMISSION,
            ]
        else:
            codes = ["system.access"]
        for code in codes:
            if not db.get(RolePermission, (role.id, code)):
                db.add(RolePermission(role_id=role.id, permission_code=code))
    db.commit()
