from typing import Literal, cast
from uuid import UUID

from sqlalchemy import Select, delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.identity.models import AuditLog, User, now
from app.modules.identity.security import AuthError
from app.modules.identity.service import require_permission
from app.modules.knowledge.models import (
    FundingCase,
    FundingHistory,
    KnowledgeInterest,
    KnowledgeItem,
    KnowledgeRevision,
    KnowledgeSaved,
    KnowledgeTag,
)
from app.modules.knowledge.schemas import (
    FundingCaseList,
    FundingCaseView,
    FundingHistoryView,
    FundingStatus,
    FundingStatusChange,
    KnowledgeAvailability,
    KnowledgeCommand,
    KnowledgeCreate,
    KnowledgeDraft,
    KnowledgeEdit,
    KnowledgeFilters,
    KnowledgeHistory,
    KnowledgeInterestView,
    KnowledgeList,
    KnowledgeLocale,
    KnowledgeMine,
    KnowledgeRevisionView,
    KnowledgeSavedView,
    KnowledgeState,
    KnowledgeView,
)
from app.modules.programs.models import Enrollment, Participant

TRANSITIONS: dict[str, set[str]] = {
    "interested": {"eligibility_check"},
    "eligibility_check": {"document_preparation"},
    "document_preparation": {"applied"},
    "applied": {"under_review"},
    "under_review": {"approved", "rejected"},
    "approved": {"disbursed"},
    "rejected": set(),
    "disbursed": set(),
}


def commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("knowledge_conflict", 409) from exc


def audit(
    db: Session,
    org: UUID,
    actor: User,
    resource: UUID,
    action: str,
    request_id: str,
    version: int | None = None,
    changed_fields: str | None = None,
) -> None:
    # Content and participant reasons remain in scoped evidence, never in the audit payload.
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=resource,
            action=action,
            request_id=request_id,
            resource_version=version,
            changed_fields=changed_fields
            or (
                ("status,version" if action.startswith("funding.") else "state,version")
                if version
                else "item_id"
            ),
        )
    )


def participant(db: Session, org: UUID, actor: User) -> Participant:
    require_permission(db, actor, org, "participant.self")
    row = db.scalar(
        select(Participant).where(
            Participant.organization_id == org,
            Participant.person_id == actor.person_id,
            Participant.status == "active",
            select(Enrollment.id)
            .where(
                Enrollment.participant_id == Participant.id,
                Enrollment.organization_id == org,
                Enrollment.status == "active",
            )
            .exists(),
        )
    )
    if row is None:
        raise AuthError("active_participant_required", 403)
    return row


def availability(item: KnowledgeItem) -> KnowledgeAvailability:
    today = now().date()
    if item.closes_on is not None and item.closes_on < today:
        return "closed"
    if item.opens_on is not None and item.opens_on > today:
        return "upcoming"
    return "open"


def view(db: Session, item: KnowledgeItem, *, tags: list[str] | None = None) -> KnowledgeView:
    values = {name: getattr(item, name) for name in KnowledgeDraft.model_fields if name != "tags"}
    return KnowledgeView(
        **values,
        tags=tags
        if tags is not None
        else list(
            db.scalars(
                select(KnowledgeTag.label)
                .where(KnowledgeTag.item_id == item.id)
                .order_by(KnowledgeTag.label)
            )
        ),
        id=item.id,
        state=cast(KnowledgeState, item.state),
        version=item.version,
        published_at=item.published_at,
        updated_at=item.updated_at,
        availability=availability(item),
    )


def item(db: Session, org: UUID, item_id: UUID, *, lock: bool = False) -> KnowledgeItem:
    query = select(KnowledgeItem).where(
        KnowledgeItem.id == item_id, KnowledgeItem.organization_id == org
    )
    row = db.scalar(query.with_for_update() if lock else query)
    if row is None:
        raise AuthError("not_found", 404)
    return row


def visible(item: KnowledgeItem, audience: Literal["public", "participants"]) -> bool:
    return item.state == "published" and (audience == "participants" or item.visibility == "public")


def catalog_item(
    db: Session,
    org: UUID,
    item_id: UUID,
    audience: Literal["public", "participants"],
    *,
    lock: bool = False,
) -> KnowledgeItem:
    row = item(db, org, item_id, lock=lock)
    if not visible(row, audience):
        raise AuthError("not_found", 404)
    return row


def listing(
    db: Session,
    org: UUID,
    *,
    audience: Literal["staff", "public", "participants"],
    filters: KnowledgeFilters,
) -> KnowledgeList:
    locale, kind, q = filters.locale, filters.kind, filters.q
    sector, geography, tag = filters.sector, filters.geography, filters.tag
    availability_filter, state = filters.availability, filters.state
    cursor, limit = filters.cursor, filters.limit
    query = select(KnowledgeItem).where(
        KnowledgeItem.organization_id == org, KnowledgeItem.locale == locale
    )
    if audience != "staff":
        query = query.where(KnowledgeItem.state == "published")
        if audience == "public":
            query = query.where(KnowledgeItem.visibility == "public")
    elif state:
        query = query.where(KnowledgeItem.state == state)
    if kind:
        query = query.where(KnowledgeItem.kind == kind)
    if q:
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(
            or_(
                KnowledgeItem.title.ilike(f"%{escaped}%", escape="\\"),
                KnowledgeItem.provider.ilike(f"%{escaped}%", escape="\\"),
                KnowledgeItem.description.ilike(f"%{escaped}%", escape="\\"),
            )
        )
    if sector:
        query = query.where(KnowledgeItem.sector == sector)
    if geography:
        query = query.where(KnowledgeItem.geography == geography)
    if tag:
        query = query.where(
            select(KnowledgeTag.item_id)
            .where(
                KnowledgeTag.item_id == KnowledgeItem.id,
                KnowledgeTag.label == tag,
                KnowledgeTag.organization_id == org,
            )
            .exists()
        )
    today = now().date()
    if availability_filter == "closed":
        query = query.where(KnowledgeItem.closes_on < today)
    elif availability_filter != "all":
        query = query.where(
            or_(KnowledgeItem.closes_on.is_(None), KnowledgeItem.closes_on >= today)
        )
        if availability_filter == "upcoming":
            query = query.where(KnowledgeItem.opens_on > today)
        elif availability_filter == "open":
            query = query.where(
                or_(KnowledgeItem.opens_on.is_(None), KnowledgeItem.opens_on <= today)
            )
    if cursor:
        query = query.where(KnowledgeItem.id > cursor)
    rows = list(db.scalars(query.order_by(KnowledgeItem.id).limit(limit + 1)))
    grouped_tags: dict[UUID, list[str]] = {}
    if rows:
        for tagged in db.scalars(
            select(KnowledgeTag)
            .where(
                KnowledgeTag.organization_id == org,
                KnowledgeTag.item_id.in_([row.id for row in rows[:limit]]),
            )
            .order_by(KnowledgeTag.label)
        ):
            grouped_tags.setdefault(tagged.item_id, []).append(tagged.label)
    return KnowledgeList(
        items=[view(db, row, tags=grouped_tags.get(row.id, [])) for row in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


def write_fields(db: Session, row: KnowledgeItem, data: KnowledgeDraft) -> None:
    for name in KnowledgeDraft.model_fields:
        if name != "tags":
            setattr(row, name, getattr(data, name))
    db.execute(delete(KnowledgeTag).where(KnowledgeTag.item_id == row.id))
    db.add_all(
        [
            KnowledgeTag(item_id=row.id, organization_id=row.organization_id, label=label)
            for label in data.tags
        ]
    )


def record_revision(
    db: Session, row: KnowledgeItem, actor: User, action: str, reason: str, request_id: str
) -> None:
    db.flush()
    snapshot = view(db, row).model_dump(mode="json")
    fields = "state,version"
    if action == "created":
        fields = "kind,locale,slug,version"
    elif action == "updated":
        previous = db.scalar(
            select(KnowledgeRevision).where(
                KnowledgeRevision.item_id == row.id, KnowledgeRevision.version == row.version - 1
            )
        )
        changed = ["version"]
        if previous:
            for name in KnowledgeDraft.model_fields:
                if previous.snapshot.get(name) != snapshot.get(name):
                    if len(",".join([*changed, name])) <= 200:
                        changed.append(name)
        fields = ",".join(changed)
    db.add(
        KnowledgeRevision(
            organization_id=row.organization_id,
            item_id=row.id,
            version=row.version,
            action=action,
            reason=reason,
            snapshot=snapshot,
            actor_user_id=actor.id,
        )
    )
    audit(
        db,
        row.organization_id,
        actor,
        row.id,
        "knowledge." + action,
        request_id,
        row.version,
        fields,
    )


def create(
    db: Session, org: UUID, actor: User, data: KnowledgeCreate, request_id: str
) -> KnowledgeView:
    require_permission(db, actor, org, "knowledge.manage")
    row = KnowledgeItem(organization_id=org, **data.model_dump(exclude={"tags"}))
    db.add(row)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("knowledge_conflict", 409) from exc
    write_fields(db, row, data)
    record_revision(db, row, actor, "created", "", request_id)
    commit(db)
    return view(db, row)


def edit(
    db: Session, org: UUID, item_id: UUID, actor: User, data: KnowledgeEdit, request_id: str
) -> KnowledgeView:
    require_permission(db, actor, org, "knowledge.manage")
    row = item(db, org, item_id, lock=True)
    if row.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if row.state != "draft":
        raise AuthError("draft_required", 409)
    if (row.kind, row.locale, row.slug) != (data.kind, data.locale, data.slug):
        raise AuthError("knowledge_identity_immutable", 422)
    row.version += 1
    row.updated_at = now()
    write_fields(db, row, data)
    record_revision(db, row, actor, "updated", data.reason, request_id)
    commit(db)
    return view(db, row)


def command(
    db: Session,
    org: UUID,
    item_id: UUID,
    actor: User,
    data: KnowledgeCommand,
    action: Literal["draft", "published", "archived"],
    request_id: str,
) -> KnowledgeView:
    require_permission(db, actor, org, "knowledge.manage")
    row = item(db, org, item_id, lock=True)
    if row.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    allowed = {
        "draft": {"published", "archived"},
        "published": {"draft"},
        "archived": {"draft", "published"},
    }
    if row.state not in allowed[action]:
        raise AuthError("invalid_publication_transition", 409)
    row.state, row.version, row.updated_at = action, row.version + 1, now()
    row.published_at = now() if action == "published" else None
    record_revision(db, row, actor, action, data.reason, request_id)
    commit(db)
    return view(db, row)


def history(
    db: Session, org: UUID, item_id: UUID, actor: User, cursor: UUID | None, limit: int
) -> KnowledgeHistory:
    require_permission(db, actor, org, "knowledge.manage")
    item(db, org, item_id)
    query = select(KnowledgeRevision).where(
        KnowledgeRevision.item_id == item_id, KnowledgeRevision.organization_id == org
    )
    if cursor:
        boundary = db.scalar(
            select(KnowledgeRevision).where(
                KnowledgeRevision.id == cursor,
                KnowledgeRevision.item_id == item_id,
                KnowledgeRevision.organization_id == org,
            )
        )
        if boundary is None:
            raise AuthError("invalid_cursor", 422)
        query = query.where(KnowledgeRevision.version > boundary.version)
    rows = list(db.scalars(query.order_by(KnowledgeRevision.version).limit(limit + 1)))
    return KnowledgeHistory(
        items=[
            KnowledgeRevisionView(
                id=row.id,
                version=row.version,
                action=row.action,
                reason=row.reason,
                snapshot=KnowledgeView.model_validate(row.snapshot),
                created_at=row.created_at,
            )
            for row in rows[:limit]
        ],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


def saved_view(db: Session, row: KnowledgeSaved) -> KnowledgeSavedView:
    resource = db.get(KnowledgeItem, row.item_id)
    return KnowledgeSavedView(
        item_id=row.item_id,
        created_at=row.created_at,
        item=view(db, resource) if resource and visible(resource, "participants") else None,
    )


def interest_view(row: KnowledgeInterest) -> KnowledgeInterestView:
    return KnowledgeInterestView(
        id=row.id,
        item_id=row.item_id,
        item_title=row.item_title,
        locale=cast(KnowledgeLocale, row.locale),
        created_at=row.created_at,
    )


def case_view(db: Session, row: FundingCase) -> FundingCaseView:
    evidence = list(
        db.scalars(
            select(FundingHistory)
            .where(FundingHistory.case_id == row.id)
            .order_by(FundingHistory.version)
        )
    )
    return FundingCaseView(
        id=row.id,
        item_id=row.item_id,
        item_title=row.item_title,
        locale=cast(KnowledgeLocale, row.locale),
        participant_id=row.participant_id,
        status=cast(FundingStatus, row.status),
        version=row.version,
        created_at=row.created_at,
        source=KnowledgeView.model_validate(row.source),
        history=[
            FundingHistoryView(
                id=entry.id,
                status=cast(FundingStatus, entry.status),
                reason=entry.reason,
                created_at=entry.created_at,
            )
            for entry in evidence
        ],
    )


def mine(
    db: Session,
    org: UUID,
    actor: User,
    saved_cursor: UUID | None,
    interest_cursor: UUID | None,
    case_cursor: UUID | None,
    limit: int,
) -> KnowledgeMine:
    owner = participant(db, org, actor)
    saved_query = select(KnowledgeSaved).where(
        KnowledgeSaved.organization_id == org, KnowledgeSaved.participant_id == owner.id
    )
    interests_query = select(KnowledgeInterest).where(
        KnowledgeInterest.organization_id == org, KnowledgeInterest.participant_id == owner.id
    )
    cases_query = select(FundingCase).where(
        FundingCase.organization_id == org, FundingCase.participant_id == owner.id
    )
    if saved_cursor:
        saved_query = saved_query.where(KnowledgeSaved.id > saved_cursor)
    if interest_cursor:
        interests_query = interests_query.where(KnowledgeInterest.id > interest_cursor)
    if case_cursor:
        cases_query = cases_query.where(FundingCase.id > case_cursor)
    saved = list(db.scalars(saved_query.order_by(KnowledgeSaved.id).limit(limit + 1)))
    interests = list(db.scalars(interests_query.order_by(KnowledgeInterest.id).limit(limit + 1)))
    cases = list(db.scalars(cases_query.order_by(FundingCase.id).limit(limit + 1)))
    return KnowledgeMine(
        saved_items=[saved_view(db, row) for row in saved[:limit]],
        interests=[interest_view(row) for row in interests[:limit]],
        funding_cases=[case_view(db, row) for row in cases[:limit]],
        next_saved_cursor=saved[limit - 1].id if len(saved) > limit else None,
        next_interest_cursor=interests[limit - 1].id if len(interests) > limit else None,
        next_case_cursor=cases[limit - 1].id if len(cases) > limit else None,
    )


def save(db: Session, org: UUID, actor: User, item_id: UUID, request_id: str) -> KnowledgeSavedView:
    owner = participant(db, org, actor)
    catalog_item(db, org, item_id, "participants", lock=True)
    row = db.scalar(
        select(KnowledgeSaved).where(
            KnowledgeSaved.participant_id == owner.id, KnowledgeSaved.item_id == item_id
        )
    )
    if row is None:
        row = KnowledgeSaved(organization_id=org, participant_id=owner.id, item_id=item_id)
        db.add(row)
        audit(db, org, actor, item_id, "knowledge.saved", request_id)
        commit(db)
    return saved_view(db, row)


def unsave(db: Session, org: UUID, actor: User, item_id: UUID, request_id: str) -> None:
    owner = participant(db, org, actor)
    row = db.scalar(
        select(KnowledgeSaved)
        .where(
            KnowledgeSaved.participant_id == owner.id,
            KnowledgeSaved.organization_id == org,
            KnowledgeSaved.item_id == item_id,
        )
        .with_for_update()
    )
    if row:
        db.delete(row)
        audit(db, org, actor, item_id, "knowledge.unsaved", request_id)
        commit(db)


def interest(
    db: Session, org: UUID, actor: User, item_id: UUID, request_id: str
) -> KnowledgeInterestView:
    owner = participant(db, org, actor)
    resource = catalog_item(db, org, item_id, "participants", lock=True)
    if resource.kind != "opportunity":
        raise AuthError("opportunity_required", 422)
    row = db.scalar(
        select(KnowledgeInterest).where(
            KnowledgeInterest.participant_id == owner.id, KnowledgeInterest.item_id == item_id
        )
    )
    if row is None:
        if availability(resource) == "closed":
            raise AuthError("knowledge_closed", 409)
        row = KnowledgeInterest(
            organization_id=org,
            participant_id=owner.id,
            item_id=item_id,
            item_title=resource.title,
            locale=resource.locale,
        )
        db.add(row)
        db.flush()
        audit(db, org, actor, row.id, "knowledge.interested", request_id)
        commit(db)
    return interest_view(row)


def create_case(
    db: Session, org: UUID, actor: User, item_id: UUID, request_id: str
) -> FundingCaseView:
    owner = participant(db, org, actor)
    resource = catalog_item(db, org, item_id, "participants", lock=True)
    if resource.kind != "funding":
        raise AuthError("funding_required", 422)
    row = db.scalar(
        select(FundingCase).where(
            FundingCase.participant_id == owner.id, FundingCase.item_id == item_id
        )
    )
    if row is None:
        if availability(resource) == "closed":
            raise AuthError("knowledge_closed", 409)
        row = FundingCase(
            organization_id=org,
            participant_id=owner.id,
            item_id=item_id,
            item_title=resource.title,
            locale=resource.locale,
            source=view(db, resource).model_dump(mode="json"),
        )
        db.add(row)
        db.flush()
        db.add(
            FundingHistory(
                organization_id=org,
                case_id=row.id,
                version=1,
                status="interested",
                reason="",
                actor_user_id=actor.id,
            )
        )
        audit(db, org, actor, row.id, "funding.created", request_id, row.version)
        commit(db)
    return case_view(db, row)


def update_case(
    db: Session, org: UUID, actor: User, case_id: UUID, data: FundingStatusChange, request_id: str
) -> FundingCaseView:
    owner = participant(db, org, actor)
    row = db.scalar(
        select(FundingCase)
        .where(
            FundingCase.id == case_id,
            FundingCase.organization_id == org,
            FundingCase.participant_id == owner.id,
        )
        .with_for_update()
    )
    if row is None:
        raise AuthError("not_found", 404)
    if row.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if data.status not in TRANSITIONS[row.status]:
        raise AuthError("invalid_funding_transition", 409)
    row.status, row.version = data.status, row.version + 1
    row.updated_at = now()
    db.add(
        FundingHistory(
            organization_id=org,
            case_id=row.id,
            version=row.version,
            status=row.status,
            reason=data.reason,
            actor_user_id=actor.id,
        )
    )
    audit(db, org, actor, row.id, "funding.status_changed", request_id, row.version)
    commit(db)
    return case_view(db, row)


def cases(
    db: Session,
    org: UUID,
    actor: User,
    status: FundingStatus | None,
    cursor: UUID | None,
    limit: int,
) -> FundingCaseList:
    require_permission(db, actor, org, "funding.manage")
    query: Select[tuple[FundingCase]] = select(FundingCase).where(
        FundingCase.organization_id == org
    )
    if status:
        query = query.where(FundingCase.status == status)
    if cursor:
        query = query.where(FundingCase.id > cursor)
    rows = list(db.scalars(query.order_by(FundingCase.id).limit(limit + 1)))
    return FundingCaseList(
        items=[case_view(db, row) for row in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )
