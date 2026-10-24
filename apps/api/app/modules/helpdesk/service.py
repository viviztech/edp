import hashlib
import json
from typing import Literal, cast
from uuid import UUID, uuid4

from sqlalchemy import Select, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.helpdesk.models import (
    HelpdeskAssignment,
    HelpdeskAttachment,
    HelpdeskHistory,
    HelpdeskMessage,
    HelpdeskNotice,
    HelpdeskPreference,
    HelpdeskTicket,
)
from app.modules.helpdesk.schemas import (
    AssigneeList,
    AssigneeView,
    AssignmentChange,
    AttachmentInput,
    AttachmentView,
    Category,
    HelpdeskPreferenceView,
    HistoryList,
    HistoryView,
    MessageCreate,
    MessageList,
    MessageView,
    NoticeList,
    NoticeView,
    PreferenceChange,
    Priority,
    PriorityChange,
    StatusChange,
    TicketClaimView,
    TicketCommand,
    TicketCreate,
    TicketList,
    TicketOwnerView,
    TicketStaffView,
    TicketStatus,
    TicketView,
)
from app.modules.identity.models import AuditLog, Person, RolePermission, User, UserRole, now
from app.modules.identity.security import AuthError
from app.modules.programs.models import Enrollment, Participant


def permissions(db: Session, org: UUID, actor: User) -> set[str]:
    return set(
        db.scalars(
            select(RolePermission.permission_code)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .where(UserRole.user_id == actor.id, UserRole.organization_id == org)
        )
    )


def participant(db: Session, org: UUID, actor: User) -> Participant | None:
    if "participant.self" not in permissions(db, org, actor):
        return None
    return db.scalar(
        select(Participant).where(
            Participant.organization_id == org,
            Participant.person_id == actor.person_id,
            Participant.status.in_(["active", "completed"]),
            select(Enrollment.id)
            .where(
                Enrollment.participant_id == Participant.id,
                Enrollment.organization_id == org,
                Enrollment.status.in_(["active", "completed"]),
            )
            .exists(),
        )
    )


def eligible(db: Session, org: UUID, user_id: UUID) -> bool:
    actor = db.get(User, user_id)
    return bool(
        actor
        and actor.status == "active"
        and {"ticket.view", "ticket.update"} <= permissions(db, org, actor)
    )


def ticket(db: Session, org: UUID, ticket_id: UUID, *, lock: bool = False) -> HelpdeskTicket:
    query = select(HelpdeskTicket).where(
        HelpdeskTicket.id == ticket_id, HelpdeskTicket.organization_id == org
    )
    query = query.execution_options(populate_existing=True)
    row = db.scalar(query.with_for_update() if lock else query)
    if row is None:
        raise AuthError("not_found", 404)
    return row


def access(
    db: Session, row: HelpdeskTicket, actor: User, *, write: bool = False
) -> Literal["owner", "staff"]:
    if row.owner_user_id == actor.id and participant(db, row.organization_id, actor):
        return "owner"
    caps = permissions(db, row.organization_id, actor)
    if "ticket.admin" in caps or (
        row.assignee_user_id == actor.id
        and "ticket.view" in caps
        and (not write or "ticket.update" in caps)
    ):
        return "staff"
    raise AuthError("forbidden", 403)


def view(row: HelpdeskTicket, audience: Literal["owner", "staff", "claim"]) -> TicketView:
    fields = dict(
        id=row.id,
        number=row.number,
        category=cast(Category, row.category),
        status=cast(TicketStatus, row.status),
        priority=cast(Priority, row.priority),
        version=row.version,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
    if audience == "claim":
        return TicketClaimView(**fields)
    if audience == "owner":
        return TicketOwnerView(**fields, subject=row.subject)
    return TicketStaffView(
        **fields,
        subject=row.subject,
        assignee_user_id=row.assignee_user_id,
        owner_participant_id=row.owner_participant_id,
        owner_user_id=row.owner_user_id,
    )


def checked_version(row: HelpdeskTicket, expected: int) -> None:
    if row.version != expected:
        raise AuthError("helpdesk_stale_version", 409)


def commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("helpdesk_conflict", 409) from exc


def evidence(
    db: Session,
    row: HelpdeskTicket,
    actor: User,
    event: str,
    reason: str,
    request_id: str,
    *,
    staff_only: bool = False,
    private_reason: bool = False,
    changed: str = "version",
) -> None:
    db.add(
        HelpdeskHistory(
            organization_id=row.organization_id,
            ticket_id=row.id,
            version=row.version,
            event=event,
            status=row.status,
            priority=row.priority,
            reason=reason,
            staff_only=staff_only,
            private_reason=private_reason,
            actor_user_id=actor.id,
        )
    )
    db.add(
        AuditLog(
            organization_id=row.organization_id,
            actor_id=actor.id,
            resource_id=row.id,
            action="helpdesk." + event,
            request_id=request_id,
            resource_version=row.version,
            changed_fields=changed,
        )
    )


def add_message(
    db: Session,
    row: HelpdeskTicket,
    actor: User,
    body: str,
    internal: bool,
    attachments: list[AttachmentInput],
    file_ids: list[UUID] | None = None,
) -> HelpdeskMessage:
    # The message's immutable selection is checked against the new ticket version.
    # Flush that parent transition before inserting its message evidence.
    db.flush()
    message = HelpdeskMessage(
        organization_id=row.organization_id,
        ticket_id=row.id,
        ticket_version=row.version,
        author_user_id=actor.id,
        body=body,
        internal=internal,
        shared_file_ids=file_ids or [],
    )
    db.add(message)
    db.flush()
    for attachment in attachments:
        db.add(
            HelpdeskAttachment(
                organization_id=row.organization_id,
                ticket_id=row.id,
                message_id=message.id,
                filename=attachment.filename,
                content=attachment.content,
                size_bytes=len(attachment.content.encode("utf-8")),
            )
        )
    return message


def notify(
    db: Session, row: HelpdeskTicket, recipient: UUID | None, actor: User, event: str
) -> None:
    if recipient is None or recipient == actor.id:
        return
    pref = db.scalar(
        select(HelpdeskPreference).where(
            HelpdeskPreference.organization_id == row.organization_id,
            HelpdeskPreference.user_id == recipient,
        )
    )
    if pref is not None and not pref.enabled:
        return
    db.add(
        HelpdeskNotice(
            organization_id=row.organization_id,
            ticket_id=row.id,
            recipient_user_id=recipient,
            event=event,
            ticket_version=row.version,
        )
    )


def create(db: Session, org: UUID, actor: User, data: TicketCreate, request_id: str) -> TicketView:
    owner = participant(db, org, actor)
    if owner is None:
        raise AuthError("enrolled_participant_required", 403)
    # Lock the derived owner so concurrent retries serialize before the unique request key check.
    db.execute(select(Participant).where(Participant.id == owner.id).with_for_update())
    digest = hashlib.sha256(
        json.dumps(data.model_dump(mode="json"), sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    existing = db.scalar(
        select(HelpdeskTicket).where(
            HelpdeskTicket.organization_id == org,
            HelpdeskTicket.owner_user_id == actor.id,
            HelpdeskTicket.request_id == data.request_id,
        )
    )
    if existing:
        if existing.request_digest != digest:
            raise AuthError("helpdesk_request_reused", 409)
        return view(existing, "owner")
    ident = uuid4()
    row = HelpdeskTicket(
        id=ident,
        organization_id=org,
        owner_participant_id=owner.id,
        owner_user_id=actor.id,
        request_id=data.request_id,
        request_digest=digest,
        number="HD-" + ident.hex.upper(),
        category=data.category,
        subject=data.subject,
        priority=data.priority,
        status="open",
        version=1,
    )
    db.add(row)
    db.flush()
    add_message(db, row, actor, data.body, False, data.attachments)
    evidence(
        db,
        row,
        actor,
        "created",
        "",
        request_id,
        changed="category,subject,priority,status,version",
    )
    commit(db)
    return view(row, "owner")


def listing(
    db: Session,
    org: UUID,
    actor: User,
    queue: str,
    status: TicketStatus | None,
    category: Category | None,
    priority: Priority | None,
    cursor: UUID | None,
    limit: int,
) -> TicketList:
    caps = permissions(db, org, actor)
    owner = participant(db, org, actor)
    query = select(HelpdeskTicket).where(HelpdeskTicket.organization_id == org)
    audience: Literal["owner", "staff", "claim"]
    if queue == "mine" or (owner is not None and queue == "assigned" and "ticket.view" not in caps):
        if owner is None:
            raise AuthError("enrolled_participant_required", 403)
        query = query.where(HelpdeskTicket.owner_user_id == actor.id)
        audience = "owner"
    elif queue == "organization":
        if "ticket.admin" not in caps:
            raise AuthError("forbidden", 403)
        audience = "staff"
    elif queue == "unassigned":
        if not {"ticket.view", "ticket.update", "ticket.assign"} <= caps:
            raise AuthError("forbidden", 403)
        query = query.where(
            HelpdeskTicket.assignee_user_id.is_(None), HelpdeskTicket.status == "open"
        )
        audience = "claim"
    else:
        if "ticket.view" not in caps:
            raise AuthError("forbidden", 403)
        query = query.where(HelpdeskTicket.assignee_user_id == actor.id)
        audience = "staff"
    if status:
        query = query.where(HelpdeskTicket.status == status)
    if category:
        query = query.where(HelpdeskTicket.category == category)
    if priority:
        query = query.where(HelpdeskTicket.priority == priority)
    if cursor:
        if db.scalar(query.where(HelpdeskTicket.id == cursor)) is None:
            raise AuthError("invalid_cursor", 422)
        query = query.where(HelpdeskTicket.id > cursor)
    rows = list(db.scalars(query.order_by(HelpdeskTicket.id).limit(limit + 1)))
    return TicketList(
        items=[view(row, audience) for row in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


def detail(db: Session, org: UUID, ticket_id: UUID, actor: User) -> TicketView:
    row = ticket(db, org, ticket_id)
    return view(row, access(db, row, actor))


def messages(
    db: Session, org: UUID, ticket_id: UUID, actor: User, cursor: UUID | None, limit: int
) -> MessageList:
    from app.modules.helpdesk.file_service import posted_message_files

    row = ticket(db, org, ticket_id)
    audience = access(db, row, actor)
    query = select(HelpdeskMessage).where(
        HelpdeskMessage.ticket_id == row.id, HelpdeskMessage.organization_id == org
    )
    if audience == "owner":
        query = query.where(HelpdeskMessage.internal.is_(False))
    if cursor:
        prior = db.scalar(query.where(HelpdeskMessage.id == cursor))
        if prior is None:
            raise AuthError("invalid_cursor", 422)
        query = query.where(HelpdeskMessage.ticket_version > prior.ticket_version)
    rows = list(db.scalars(query.order_by(HelpdeskMessage.ticket_version).limit(limit + 1)))
    ids = [message.id for message in rows[:limit]]
    attachments = (
        list(
            db.scalars(
                select(HelpdeskAttachment)
                .where(
                    HelpdeskAttachment.organization_id == org,
                    HelpdeskAttachment.message_id.in_(ids),
                )
                .order_by(HelpdeskAttachment.id)
            )
        )
        if ids
        else []
    )
    return MessageList(
        items=[
            MessageView(
                id=message.id,
                body=message.body,
                internal=message.internal,
                author_user_id=message.author_user_id,
                created_at=message.created_at,
                attachments=[
                    AttachmentView(id=a.id, filename=a.filename, size_bytes=a.size_bytes)
                    for a in attachments
                    if a.message_id == message.id
                ],
                files=posted_message_files(db, org, message.id),
            )
            for message in rows[:limit]
        ],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


def history(
    db: Session, org: UUID, ticket_id: UUID, actor: User, cursor: UUID | None, limit: int
) -> HistoryList:
    row = ticket(db, org, ticket_id)
    audience = access(db, row, actor)
    query = select(HelpdeskHistory).where(
        HelpdeskHistory.ticket_id == row.id, HelpdeskHistory.organization_id == org
    )
    if audience == "owner":
        query = query.where(HelpdeskHistory.staff_only.is_(False))
    if cursor:
        prior = db.scalar(query.where(HelpdeskHistory.id == cursor))
        if prior is None:
            raise AuthError("invalid_cursor", 422)
        query = query.where(HelpdeskHistory.version > prior.version)
    rows = list(db.scalars(query.order_by(HelpdeskHistory.version).limit(limit + 1)))
    return HistoryList(
        items=[
            HistoryView(
                id=h.id,
                event=h.event,
                status=cast(TicketStatus, h.status),
                priority=cast(Priority, h.priority),
                version=h.version,
                reason=None if audience == "owner" and h.private_reason else h.reason or None,
                actor_user_id=h.actor_user_id,
                created_at=h.created_at,
            )
            for h in rows[:limit]
        ],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


def attachment(
    db: Session, org: UUID, ticket_id: UUID, attachment_id: UUID, actor: User, request_id: str
) -> HelpdeskAttachment:
    row = ticket(db, org, ticket_id)
    audience = access(db, row, actor)
    query = (
        select(HelpdeskAttachment)
        .join(HelpdeskMessage, HelpdeskMessage.id == HelpdeskAttachment.message_id)
        .where(
            HelpdeskAttachment.id == attachment_id,
            HelpdeskAttachment.ticket_id == row.id,
            HelpdeskAttachment.organization_id == org,
        )
    )
    if audience == "owner":
        query = query.where(HelpdeskMessage.internal.is_(False))
    found = db.scalar(query)
    if found is None:
        raise AuthError("not_found", 404)
    db.add(
        AuditLog(
            organization_id=org,
            actor_id=actor.id,
            resource_id=found.id,
            action="helpdesk.attachment_download",
            request_id=request_id,
            resource_version=row.version,
            changed_fields="attachment_id",
        )
    )
    commit(db)
    return found


def reply(
    db: Session, org: UUID, ticket_id: UUID, actor: User, data: MessageCreate, request_id: str
) -> TicketView:
    row = ticket(db, org, ticket_id, lock=True)
    audience = access(db, row, actor, write=True)
    checked_version(row, data.expected_version)
    if row.status in {"resolved", "closed"}:
        raise AuthError("helpdesk_reopen_required", 409)
    if data.internal and audience != "staff":
        raise AuthError("forbidden", 403)
    from app.modules.helpdesk.file_service import freeze_message, validate_message_files

    validate_message_files(db, row, actor, data.file_ids, data.internal)
    row.version += 1
    if audience == "owner" and row.status == "waiting_for_user":
        row.status = "in_progress"
    message = add_message(db, row, actor, data.body, data.internal, data.attachments, data.file_ids)
    freeze_message(db, row, message, actor, request_id)
    evidence(
        db,
        row,
        actor,
        "internal_note" if data.internal else "shared_reply",
        "",
        request_id,
        staff_only=data.internal,
        changed="message,status,version",
    )
    if not data.internal:
        notify(
            db,
            row,
            row.assignee_user_id if audience == "owner" else row.owner_user_id,
            actor,
            "shared_reply",
        )
    commit(db)
    return view(row, audience)


def assign(
    db: Session, org: UUID, ticket_id: UUID, actor: User, data: AssignmentChange, request_id: str
) -> TicketView:
    row = ticket(db, org, ticket_id, lock=True)
    caps = permissions(db, org, actor)
    if "ticket.assign" not in caps or not (
        "ticket.admin" in caps
        or row.assignee_user_id == actor.id
        or (
            row.assignee_user_id is None
            and data.assignee_user_id == actor.id
            and {"ticket.view", "ticket.update"} <= caps
        )
    ):
        raise AuthError("forbidden", 403)
    checked_version(row, data.expected_version)
    if row.status in {"resolved", "closed"} or row.assignee_user_id == data.assignee_user_id:
        raise AuthError("helpdesk_invalid_assignment", 409)
    if not eligible(db, org, data.assignee_user_id):
        raise AuthError("helpdesk_ineligible_assignee", 422)
    prior = row.assignee_user_id
    row.assignee_user_id = data.assignee_user_id
    if row.status == "open":
        row.status = "assigned"
    row.version += 1
    db.add(
        HelpdeskAssignment(
            organization_id=org,
            ticket_id=row.id,
            version=row.version,
            from_user_id=prior,
            to_user_id=data.assignee_user_id,
            actor_user_id=actor.id,
            reason=data.reason,
        )
    )
    evidence(
        db,
        row,
        actor,
        "assigned",
        data.reason,
        request_id,
        private_reason=True,
        changed="assignee_user_id,status,version",
    )
    notify(db, row, row.assignee_user_id, actor, "assigned")
    commit(db)
    # Return the committed handover; later reads reauthorize the new assignment.
    return view(row, "staff")


def priority_change(
    db: Session, org: UUID, ticket_id: UUID, actor: User, data: PriorityChange, request_id: str
) -> TicketView:
    row = ticket(db, org, ticket_id, lock=True)
    audience = access(db, row, actor, write=True)
    if audience != "staff":
        raise AuthError("forbidden", 403)
    checked_version(row, data.expected_version)
    if row.status in {"resolved", "closed"} or row.priority == data.priority:
        raise AuthError("helpdesk_invalid_priority", 409)
    row.priority = data.priority
    row.version += 1
    evidence(
        db,
        row,
        actor,
        "priority",
        data.reason,
        request_id,
        private_reason=True,
        changed="priority,version",
    )
    commit(db)
    return view(row, "staff")


def status_change(
    db: Session, org: UUID, ticket_id: UUID, actor: User, data: StatusChange, request_id: str
) -> TicketView:
    row = ticket(db, org, ticket_id, lock=True)
    audience = access(db, row, actor, write=True)
    checked_version(row, data.expected_version)
    allowed = {
        "assigned": {"in_progress"},
        "in_progress": {"waiting_for_user", "resolved"},
        "waiting_for_user": {"in_progress", "resolved"},
        "resolved": {"closed"},
    }
    if data.status not in allowed.get(row.status, set()) or (
        audience == "owner" and data.status != "closed"
    ):
        raise AuthError("helpdesk_invalid_status", 409)
    row.status = data.status
    row.version += 1
    evidence(db, row, actor, "status", data.reason, request_id, changed="status,version")
    notify(db, row, row.owner_user_id, actor, "status")
    commit(db)
    return view(row, audience)


def reopen(
    db: Session, org: UUID, ticket_id: UUID, actor: User, data: TicketCommand, request_id: str
) -> TicketView:
    row = ticket(db, org, ticket_id, lock=True)
    audience = access(db, row, actor, write=True)
    if audience != "owner" and "ticket.admin" not in permissions(db, org, actor):
        raise AuthError("forbidden", 403)
    checked_version(row, data.expected_version)
    if row.status not in {"resolved", "closed"}:
        raise AuthError("helpdesk_invalid_status", 409)
    prior = row.assignee_user_id
    row.status = "open"
    row.assignee_user_id = None
    row.version += 1
    db.add(
        HelpdeskAssignment(
            organization_id=org,
            ticket_id=row.id,
            version=row.version,
            from_user_id=prior,
            to_user_id=None,
            actor_user_id=actor.id,
            reason=data.reason,
        )
    )
    evidence(
        db,
        row,
        actor,
        "reopened",
        data.reason,
        request_id,
        changed="status,assignee_user_id,version",
    )
    notify(db, row, row.owner_user_id, actor, "reopened")
    commit(db)
    return view(row, audience)


def assignees(db: Session, org: UUID, actor: User, cursor: UUID | None, limit: int) -> AssigneeList:
    if not {"ticket.view", "ticket.assign"} <= permissions(db, org, actor):
        raise AuthError("forbidden", 403)
    query = (
        select(User.id, Person.display_name)
        .join(Person, Person.id == User.person_id)
        .where(User.status == "active")
    )
    for code in ("ticket.view", "ticket.update"):
        query = query.where(
            select(UserRole.id)
            .join(RolePermission, RolePermission.role_id == UserRole.role_id)
            .where(
                UserRole.user_id == User.id,
                UserRole.organization_id == org,
                RolePermission.permission_code == code,
            )
            .exists()
        )
    if cursor:
        if db.execute(query.where(User.id == cursor)).first() is None:
            raise AuthError("invalid_cursor", 422)
        query = query.where(User.id > cursor)
    rows = list(db.execute(query.order_by(User.id).limit(limit + 1)))
    return AssigneeList(
        items=[AssigneeView(id=row.id, display_name=row.display_name) for row in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


def member(db: Session, org: UUID, actor: User) -> None:
    if participant(db, org, actor) is None and "ticket.view" not in permissions(db, org, actor):
        raise AuthError("forbidden", 403)


def notice_query(db: Session, org: UUID, actor: User) -> Select[tuple[HelpdeskNotice]]:
    member(db, org, actor)
    caps = permissions(db, org, actor)
    visible = []
    if participant(db, org, actor):
        visible.append(HelpdeskTicket.owner_user_id == actor.id)
    if "ticket.admin" in caps:
        visible.append(HelpdeskTicket.organization_id == org)
    elif "ticket.view" in caps:
        visible.append(HelpdeskTicket.assignee_user_id == actor.id)
    return (
        select(HelpdeskNotice)
        .join(HelpdeskTicket, HelpdeskTicket.id == HelpdeskNotice.ticket_id)
        .where(
            HelpdeskNotice.organization_id == org,
            HelpdeskNotice.recipient_user_id == actor.id,
            or_(*visible),
        )
    )


def notice_view(row: HelpdeskNotice) -> NoticeView:
    return NoticeView(
        id=row.id,
        ticket_id=row.ticket_id,
        event=row.event,
        ticket_version=row.ticket_version,
        version=row.version,
        read_at=row.read_at,
        created_at=row.created_at,
    )


def notices(db: Session, org: UUID, actor: User, cursor: UUID | None, limit: int) -> NoticeList:
    query = notice_query(db, org, actor)
    if cursor:
        if db.scalar(query.where(HelpdeskNotice.id == cursor)) is None:
            raise AuthError("invalid_cursor", 422)
        query = query.where(HelpdeskNotice.id > cursor)
    rows = list(db.scalars(query.order_by(HelpdeskNotice.id).limit(limit + 1)))
    return NoticeList(
        items=[notice_view(row) for row in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


def read_notice(
    db: Session, org: UUID, actor: User, notice_id: UUID, expected: int, request_id: str
) -> NoticeView:
    row = db.scalar(
        notice_query(db, org, actor)
        .where(HelpdeskNotice.id == notice_id)
        .with_for_update(of=HelpdeskNotice)
    )
    if row is None:
        raise AuthError("not_found", 404)
    if row.version != expected:
        raise AuthError("helpdesk_stale_version", 409)
    if row.read_at is None:
        row.read_at = now()
        row.version += 1
        db.add(
            AuditLog(
                organization_id=org,
                actor_id=actor.id,
                resource_id=row.id,
                action="helpdesk.notice_read",
                request_id=request_id,
                resource_version=row.version,
                changed_fields="read_at,version",
            )
        )
        commit(db)
    return notice_view(row)


def preference(
    db: Session, org: UUID, actor: User, data: PreferenceChange | None = None, request_id: str = ""
) -> HelpdeskPreferenceView:
    member(db, org, actor)
    # Serialize first materialization and preferences so exact-version writes remain deterministic.
    db.execute(select(User).where(User.id == actor.id).with_for_update())
    row = db.scalar(
        select(HelpdeskPreference)
        .where(HelpdeskPreference.organization_id == org, HelpdeskPreference.user_id == actor.id)
        .with_for_update()
    )
    if row is None:
        row = HelpdeskPreference(organization_id=org, user_id=actor.id, enabled=True, version=1)
        db.add(row)
        db.flush()
    if data is not None:
        if data.expected_version != row.version:
            raise AuthError("helpdesk_stale_version", 409)
        if row.enabled != data.enabled:
            row.enabled = data.enabled
            row.version += 1
            db.add(
                AuditLog(
                    organization_id=org,
                    actor_id=actor.id,
                    resource_id=row.id,
                    action="helpdesk.preference_update",
                    request_id=request_id,
                    resource_version=row.version,
                    changed_fields="enabled,version",
                )
            )
    commit(db)
    return HelpdeskPreferenceView(enabled=row.enabled, version=row.version)
