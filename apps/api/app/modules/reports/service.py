import csv
import hashlib
import io
import json
import secrets
from datetime import UTC, date, datetime, time, timedelta
from typing import Literal
from uuid import UUID

from sqlalchemy import and_, func, or_, select, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from app.modules.identity.models import AuditLog, Organization, User, now
from app.modules.identity.security import AuthError
from app.modules.identity.service import require_permission
from app.modules.programs.models import Cohort, Enrollment, Participant, Program
from app.modules.reports.definitions import (
    METRIC_DICTIONARY_VERSION,
    operational_metric_definitions,
)
from app.modules.reports.metrics import build_operational_metrics
from app.modules.reports.models import (
    CohortImpactSnapshot,
    ImpactDefinition,
    ImpactDefinitionHistory,
    ImpactRecord,
    ReportExport,
    ReportExportCapability,
)
from app.modules.reports.schemas import (
    ImpactAggregate,
    ImpactDefinitionCommand,
    ImpactDefinitionCreate,
    ImpactDefinitionList,
    ImpactDefinitionView,
    ImpactEnrollmentView,
    ImpactMine,
    ImpactRecordCreate,
    ImpactRecordView,
    ReportChoice,
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
    ReportSnapshotSummary,
    ReportSnapshotView,
)

DICTIONARY_VERSION = METRIC_DICTIONARY_VERSION


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("report_conflict", 409) from exc


def audit(
    db: Session,
    org: UUID,
    actor: User,
    resource: UUID,
    action: str,
    request_id: str,
    changed_fields: str = "id",
    version: int | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=resource,
            action=action,
            request_id=request_id,
            changed_fields=changed_fields,
            resource_version=version,
        )
    )


def definition_view(row: ImpactDefinition) -> ImpactDefinitionView:
    return ImpactDefinitionView.model_validate(row)


def definition(db: Session, org: UUID, key: UUID, *, lock: bool = False) -> ImpactDefinition:
    query = select(ImpactDefinition).where(
        ImpactDefinition.organization_id == org, ImpactDefinition.id == key
    )
    row = db.scalar(query.with_for_update() if lock else query)
    if row is None:
        raise AuthError("not_found", 404)
    return row


def actor_participant(db: Session, org: UUID, actor: User) -> Participant:
    require_permission(db, actor, org, "participant.self")
    row = db.scalar(
        select(Participant).where(
            Participant.organization_id == org,
            Participant.person_id == actor.person_id,
            Participant.status.in_(("active", "completed")),
        )
    )
    if row is None:
        raise AuthError("participant_required", 403)
    return row


def definition_listing(
    db: Session,
    org: UUID,
    actor: User,
    *,
    cursor: UUID | None = None,
    limit: int = 25,
    state: str | None = None,
) -> ImpactDefinitionList:
    # An organization-scoped management grant allows drafts; participants see publications.
    try:
        require_permission(db, actor, org, "impact.manage")
        staff = True
    except AuthError:
        actor_participant(db, org, actor)
        staff = False
    query = select(ImpactDefinition).where(ImpactDefinition.organization_id == org)
    if not staff:
        query = query.where(ImpactDefinition.state == "published")
    elif state:
        query = query.where(ImpactDefinition.state == state)
    if cursor:
        if db.scalar(query.where(ImpactDefinition.id == cursor)) is None:
            raise AuthError("invalid_cursor", 422)
        query = query.where(ImpactDefinition.id > cursor)
    rows = list(db.scalars(query.order_by(ImpactDefinition.id).limit(limit + 1)))
    return ImpactDefinitionList(
        items=[definition_view(row) for row in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


def create_definition(
    db: Session, org: UUID, actor: User, data: ImpactDefinitionCreate, request_id: str
) -> ImpactDefinitionView:
    require_permission(db, actor, org, "impact.manage")
    db.scalar(select(Organization).where(Organization.id == org).with_for_update())
    edition = (
        db.scalar(
            select(func.max(ImpactDefinition.edition)).where(
                ImpactDefinition.organization_id == org
            )
        )
        or 0
    ) + 1
    row = ImpactDefinition(
        organization_id=org, edition=edition, **data.model_dump(exclude={"reason"})
    )
    db.add(row)
    db.flush()
    db.add(
        ImpactDefinitionHistory(
            organization_id=org,
            definition_id=row.id,
            version=1,
            state="draft",
            reason=data.reason,
            actor_user_id=actor.id,
        )
    )
    audit(db, org, actor, row.id, "impact.definition.created", request_id, "edition,state", 1)
    commit(db)
    return definition_view(row)


def command_definition(
    db: Session,
    org: UUID,
    key: UUID,
    actor: User,
    data: ImpactDefinitionCommand,
    target: Literal["published", "archived"],
    request_id: str,
) -> ImpactDefinitionView:
    require_permission(db, actor, org, "impact.manage")
    row = definition(db, org, key, lock=True)
    if row.version != data.expected_version:
        raise AuthError("impact_stale_version", 409)
    if not (
        (row.state == "draft" and target == "published")
        or (row.state in {"draft", "published"} and target == "archived")
    ):
        raise AuthError("impact_invalid_transition", 409)
    row.state = target
    row.version += 1
    if target == "published":
        row.published_at = now()
    db.add(
        ImpactDefinitionHistory(
            organization_id=org,
            definition_id=row.id,
            version=row.version,
            state=target,
            reason=data.reason,
            actor_user_id=actor.id,
        )
    )
    audit(
        db,
        org,
        actor,
        row.id,
        "impact.definition." + target,
        request_id,
        "state,version",
        row.version,
    )
    commit(db)
    return definition_view(row)


def create_record(
    db: Session, org: UUID, actor: User, data: ImpactRecordCreate, request_id: str
) -> ImpactRecordView:
    owner = actor_participant(db, org, actor)
    enrollment = db.scalar(
        select(Enrollment)
        .where(
            Enrollment.id == data.enrollment_id,
            Enrollment.organization_id == org,
            Enrollment.participant_id == owner.id,
            Enrollment.status.in_(("active", "completed")),
        )
        .with_for_update()
    )
    if enrollment is None:
        raise AuthError("owned_enrollment_required", 403)
    request_digest = digest(data.model_dump(mode="json"))
    replay = db.scalar(
        select(ImpactRecord).where(
            ImpactRecord.organization_id == org,
            ImpactRecord.actor_user_id == actor.id,
            ImpactRecord.request_id == data.request_id,
        )
    )
    if replay:
        if replay.request_digest != request_digest:
            raise AuthError("impact_request_reused", 409)
        return ImpactRecordView.model_validate(replay)
    previous = db.scalar(
        select(ImpactRecord)
        .where(
            ImpactRecord.enrollment_id == enrollment.id,
            ImpactRecord.stage == data.stage,
            ImpactRecord.observed_on == data.observed_on,
        )
        .order_by(ImpactRecord.revision.desc())
        .limit(1)
    )
    if (previous.revision if previous else 0) != data.expected_revision:
        raise AuthError("impact_stale_revision", 409)
    source = definition(db, org, data.definition_id, lock=True)
    if previous and previous.definition_id != source.id:
        raise AuthError("impact_definition_pinned", 409)
    if source.state != "published" and not (previous and source.state == "archived"):
        raise AuthError("impact_published_definition_required", 409)
    row = ImpactRecord(
        organization_id=org,
        participant_id=owner.id,
        actor_user_id=actor.id,
        revision=data.expected_revision + 1,
        request_digest=request_digest,
        **data.model_dump(exclude={"expected_revision"}),
    )
    db.add(row)
    db.flush()
    audit(
        db,
        org,
        actor,
        row.id,
        "impact.record.created",
        request_id,
        "enrollment_id,definition_id,stage,observed_on,revision",
        row.revision,
    )
    commit(db)
    return ImpactRecordView.model_validate(row)


def mine(
    db: Session,
    org: UUID,
    actor: User,
    *,
    enrollment_cursor: UUID | None = None,
    definition_cursor: UUID | None = None,
    record_cursor: UUID | None = None,
    limit: int = 25,
    enrollment_id: UUID | None = None,
    stage: str | None = None,
    observed_on: date | None = None,
) -> ImpactMine:
    owner = actor_participant(db, org, actor)
    enrollment_query = (
        select(Enrollment, Cohort)
        .join(Cohort, Cohort.id == Enrollment.cohort_id)
        .where(
            Enrollment.organization_id == org,
            Enrollment.participant_id == owner.id,
            Enrollment.status.in_(("active", "completed")),
        )
    )
    if enrollment_cursor:
        if db.execute(enrollment_query.where(Enrollment.id == enrollment_cursor)).first() is None:
            raise AuthError("invalid_cursor", 422)
        enrollment_query = enrollment_query.where(Enrollment.id > enrollment_cursor)
    enrollments = list(db.execute(enrollment_query.order_by(Enrollment.id).limit(limit + 1)))
    definitions_query = select(ImpactDefinition).where(
        ImpactDefinition.organization_id == org,
        or_(
            ImpactDefinition.state == "published",
            select(ImpactRecord.id)
            .where(
                ImpactRecord.participant_id == owner.id,
                ImpactRecord.definition_id == ImpactDefinition.id,
            )
            .exists(),
        ),
    )
    if definition_cursor:
        if db.scalar(definitions_query.where(ImpactDefinition.id == definition_cursor)) is None:
            raise AuthError("invalid_cursor", 422)
        definitions_query = definitions_query.where(ImpactDefinition.id > definition_cursor)
    definitions = list(db.scalars(definitions_query.order_by(ImpactDefinition.id).limit(limit + 1)))
    record_query = select(ImpactRecord).where(
        ImpactRecord.organization_id == org, ImpactRecord.participant_id == owner.id
    )
    if enrollment_id:
        record_query = record_query.where(ImpactRecord.enrollment_id == enrollment_id)
    if stage:
        record_query = record_query.where(ImpactRecord.stage == stage)
    if observed_on:
        record_query = record_query.where(ImpactRecord.observed_on == observed_on)
    if record_cursor:
        anchor = db.scalar(record_query.where(ImpactRecord.id == record_cursor))
        if anchor is None:
            raise AuthError("invalid_cursor", 422)
        record_query = record_query.where(
            tuple_(ImpactRecord.observed_on, ImpactRecord.revision, ImpactRecord.id)
            < (anchor.observed_on, anchor.revision, anchor.id)
        )
    records = list(
        db.scalars(
            record_query.order_by(
                ImpactRecord.observed_on.desc(),
                ImpactRecord.revision.desc(),
                ImpactRecord.id.desc(),
            ).limit(limit + 1)
        )
    )
    # A history page must remain interpretable even when its pinned edition is
    # outside the independently paged publication list. At most one extra edition
    # per returned record is added; the definition cursor still pages the base list.
    page_definitions = definitions[:limit]
    missing_definitions = {row.definition_id for row in records[:limit]} - {
        row.id for row in page_definitions
    }
    if missing_definitions:
        page_definitions += list(
            db.scalars(
                select(ImpactDefinition).where(
                    ImpactDefinition.organization_id == org,
                    ImpactDefinition.id.in_(missing_definitions),
                )
            )
        )
    return ImpactMine(
        enrollments=[
            ImpactEnrollmentView(
                id=e.id,
                program_id=e.program_id,
                cohort_id=e.cohort_id,
                name_en=c.name_en,
                name_ta=c.name_ta,
                status=e.status,
            )
            for e, c in enrollments[:limit]
        ],
        definitions=[definition_view(d) for d in page_definitions],
        records=[ImpactRecordView.model_validate(r) for r in records[:limit]],
        enrollment_next_cursor=enrollments[limit - 1][0].id if len(enrollments) > limit else None,
        definition_next_cursor=definitions[limit - 1].id if len(definitions) > limit else None,
        record_next_cursor=records[limit - 1].id if len(records) > limit else None,
    )


def validate_filters(db: Session, org: UUID, filters: ReportFilters) -> None:
    if (
        filters.program_id
        and db.scalar(
            select(Program.id).where(
                Program.id == filters.program_id, Program.organization_id == org
            )
        )
        is None
    ):
        raise AuthError("invalid_program", 422)
    if filters.cohort_id:
        cohort = db.scalar(
            select(Cohort).where(Cohort.id == filters.cohort_id, Cohort.organization_id == org)
        )
        if cohort is None or (filters.program_id and cohort.program_id != filters.program_id):
            raise AuthError("invalid_cohort", 422)


def report_options(
    db: Session,
    org: UUID,
    actor: User,
    *,
    program_cursor: UUID | None = None,
    cohort_cursor: UUID | None = None,
    program_id: UUID | None = None,
    limit: int = 25,
) -> ReportOptions:
    require_permission(db, actor, org, "report.view")
    programs_query = select(Program).where(Program.organization_id == org)
    cohorts_query = select(Cohort).where(Cohort.organization_id == org)
    if program_id:
        if db.scalar(programs_query.where(Program.id == program_id)) is None:
            raise AuthError("invalid_program", 422)
        cohorts_query = cohorts_query.where(Cohort.program_id == program_id)
    if program_cursor:
        if db.scalar(programs_query.where(Program.id == program_cursor)) is None:
            raise AuthError("invalid_cursor", 422)
        programs_query = programs_query.where(Program.id > program_cursor)
    if cohort_cursor:
        if db.scalar(cohorts_query.where(Cohort.id == cohort_cursor)) is None:
            raise AuthError("invalid_cursor", 422)
        cohorts_query = cohorts_query.where(Cohort.id > cohort_cursor)
    programs = list(db.scalars(programs_query.order_by(Program.id).limit(limit + 1)))
    cohorts = list(db.scalars(cohorts_query.order_by(Cohort.id).limit(limit + 1)))
    return ReportOptions(
        programs=[
            ReportChoice(id=p.id, name_en=p.name_en, name_ta=p.name_ta) for p in programs[:limit]
        ],
        cohorts=[
            ReportChoice(id=c.id, name_en=c.name_en, name_ta=c.name_ta, program_id=c.program_id)
            for c in cohorts[:limit]
        ],
        program_next_cursor=programs[limit - 1].id if len(programs) > limit else None,
        cohort_next_cursor=cohorts[limit - 1].id if len(cohorts) > limit else None,
    )


def impact_aggregates(
    db: Session, org: UUID, filters: ReportFilters
) -> tuple[list[ImpactAggregate], int, int]:
    # Retain withdrawn enrollments in the reporting population to avoid attrition bias.
    eligible_query = select(Enrollment.id).where(
        Enrollment.organization_id == org,
        Enrollment.enrolled_at
        < datetime.combine(filters.through_date + timedelta(days=1), time.min, UTC),
    )
    if filters.program_id:
        eligible_query = eligible_query.where(Enrollment.program_id == filters.program_id)
    if filters.cohort_id:
        eligible_query = eligible_query.where(Enrollment.cohort_id == filters.cohort_id)
    eligible = eligible_query.cte("impact_eligible")
    eligible_count = db.scalar(select(func.count()).select_from(eligible)) or 0
    dated = (
        select(
            ImpactRecord,
            func.row_number()
            .over(
                partition_by=(
                    ImpactRecord.enrollment_id,
                    ImpactRecord.stage,
                    ImpactRecord.observed_on,
                ),
                order_by=ImpactRecord.revision.desc(),
            )
            .label("revision_rank"),
        )
        .where(
            ImpactRecord.organization_id == org,
            ImpactRecord.enrollment_id.in_(select(eligible.c.id)),
            ImpactRecord.observed_on >= filters.from_date,
            ImpactRecord.observed_on <= filters.through_date,
        )
        .cte("impact_dated")
    )
    latest_dates = (
        select(
            dated,
            func.row_number()
            .over(
                partition_by=(dated.c.enrollment_id, dated.c.stage),
                order_by=dated.c.observed_on.desc(),
            )
            .label("date_rank"),
        )
        .where(dated.c.revision_rank == 1)
        .cte("impact_latest")
    )
    latest = select(latest_dates).where(latest_dates.c.date_rank == 1).cte("impact_selected")
    totals = list(
        db.execute(
            select(
                latest.c.definition_id,
                func.count().filter(latest.c.stage == "baseline"),
                func.count().filter(latest.c.stage == "outcome"),
                func.coalesce(
                    func.sum(latest.c.jobs_created).filter(latest.c.stage == "baseline"), 0
                ),
                func.coalesce(
                    func.sum(latest.c.jobs_created).filter(latest.c.stage == "outcome"), 0
                ),
                func.count().filter(and_(latest.c.stage == "outcome", latest.c.business_started)),
                func.count().filter(and_(latest.c.stage == "outcome", latest.c.business_active)),
            )
            .group_by(latest.c.definition_id)
            .limit(26)
        )
    )
    if len(totals) > 25:
        raise AuthError("report_too_large_narrow_filters", 422)
    baseline, outcome = aliased(latest), aliased(latest)
    matches = {
        row[0]: row
        for row in db.execute(
            select(
                baseline.c.definition_id,
                func.count(),
                func.sum(baseline.c.jobs_created),
                func.sum(outcome.c.jobs_created),
            )
            .select_from(baseline)
            .join(
                outcome,
                and_(
                    baseline.c.enrollment_id == outcome.c.enrollment_id,
                    baseline.c.definition_id == outcome.c.definition_id,
                    outcome.c.stage == "outcome",
                    baseline.c.observed_on <= outcome.c.observed_on,
                ),
            )
            .where(baseline.c.stage == "baseline")
            .group_by(baseline.c.definition_id)
        )
    }
    definitions = {
        row.id: row
        for row in db.scalars(
            select(ImpactDefinition).where(
                ImpactDefinition.organization_id == org,
                ImpactDefinition.id.in_([row[0] for row in totals]),
            )
        )
    }
    reported = db.scalar(select(func.count(func.distinct(latest.c.enrollment_id)))) or 0
    groups = []
    for row in totals:
        match = matches.get(row[0])
        count, before, after = (int(match[1]), int(match[2]), int(match[3])) if match else (0, 0, 0)
        groups.append(
            ImpactAggregate(
                definition=definition_view(definitions[row[0]]),
                eligible_enrollments=eligible_count,
                baseline_reported=row[1],
                outcome_reported=row[2],
                matched_sample=count,
                baseline_jobs=row[3],
                outcome_jobs=row[4],
                matched_baseline_jobs=before,
                matched_outcome_jobs=after,
                matched_jobs_change=after - before if count else None,
                outcome_started=row[5],
                outcome_active=row[6],
                caveat_en=(
                    "Self-reported enrollment observations; latest revision and date per stage "
                    "in this period. Matched comparisons require the same edition and baseline "
                    "no later than outcome. Not causal or verified impact."
                ),
                caveat_ta=(
                    "பங்கேற்பாளர் தெரிவித்த சேர்க்கை அளவீடுகள்; ஒவ்வொரு நிலையில் சமீபத்திய தேதி "
                    "மற்றும் திருத்தம். ஒப்பீட்டிற்கு ஒரே பதிப்பும் முடிவிற்கு முந்தைய அடிப்படையும் "
                    "தேவை. காரண விளைவு அல்லது சரிபார்க்கப்பட்ட தாக்கம் அல்ல."
                ),
            )
        )
    groups.sort(key=lambda group: group.definition.edition)
    return groups, eligible_count, reported


def build_dashboard(db: Session, org: UUID, filters: ReportFilters) -> ReportDashboard:
    validate_filters(db, org, filters)
    metrics = build_operational_metrics(
        db,
        org,
        from_date=filters.from_date,
        through_date=filters.through_date,
        program_id=filters.program_id,
        cohort_id=filters.cohort_id,
    )
    impact, eligible, reported = impact_aggregates(db, org, filters)
    return ReportDashboard(
        filters=filters,
        generated_at=now(),
        dictionary_version=DICTIONARY_VERSION,
        metrics=metrics,
        impact=impact,
        eligible_impact_enrollments=eligible,
        impact_reported_enrollments=reported,
        impact_coverage=100 * reported / eligible if eligible else None,
        caveat_en=(
            "UTC inclusive dates. Current statuses are observed at generation time, "
            "not historical period-end states. Membership scope does not establish program "
            "attribution. Impact coverage uses all enrollments begun by period end, including "
            "withdrawn enrollments; self-reported impact and B02 outcomes are separate sources. "
            "More than 25 represented measurement editions requires narrower filters."
        ),
        caveat_ta=(
            "UTC தேதிகள் உட்பட. தற்போதைய நிலைகள் உருவாக்க நேரத்தில் காணப்படுகின்றன; "
            "கால முடிவு வரலாற்று நிலைகள் அல்ல. திட்ட உறுப்பினர் நிலை காரணத்தை நிரூபிக்காது. "
            "தாக்கப் பதிவு விகிதம் விலகியவர்கள் உட்பட கால முடிவிற்குள் தொடங்கிய அனைத்து "
            "சேர்க்கைகளையும் பயன்படுத்துகிறது; சுய அறிக்கைத் தாக்கமும் B02 முடிவுகளும் தனித்தனி "
            "ஆதாரங்கள். 25-க்கும் மேற்பட்ட அளவீட்டுப் பதிப்புகளுக்கு குறுகிய வடிகட்டிகள் தேவை."
        ),
    )


def dashboard(
    db: Session, org: UUID, actor: User, filters: ReportFilters, request_id: str
) -> ReportDashboard:
    require_permission(db, actor, org, "report.view")
    # Authentication has already read on the request session. A dedicated connection sets
    # isolation before its first query, without changing any existing module transaction.
    with Session(
        bind=db.get_bind().execution_options(isolation_level="REPEATABLE READ")
    ) as coherent:
        require_permission(coherent, actor, org, "report.view")
        result = build_dashboard(coherent, org, filters)
        audit(
            coherent,
            org,
            actor,
            org,
            "report.dashboard.read",
            request_id,
            ",".join(name for name, value in filters.model_dump().items() if value is not None),
        )
        commit(coherent)
        return result


def definitions(
    db: Session, org: UUID, actor: User, cursor: UUID | None, limit: int
) -> ReportDefinitions:
    require_permission(db, actor, org, "report.view")
    query = select(ImpactDefinition).where(ImpactDefinition.organization_id == org)
    if cursor:
        if db.scalar(query.where(ImpactDefinition.id == cursor)) is None:
            raise AuthError("invalid_cursor", 422)
        query = query.where(ImpactDefinition.id > cursor)
    rows = list(db.scalars(query.order_by(ImpactDefinition.id).limit(limit + 1)))
    return ReportDefinitions(
        dictionary_version=DICTIONARY_VERSION,
        metrics=operational_metric_definitions(),
        impact_definitions=[definition_view(row) for row in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


def snapshot_view(row: CohortImpactSnapshot) -> ReportSnapshotView:
    return ReportSnapshotView(
        id=row.id,
        created_at=row.created_at,
        request_id=row.request_id,
        dashboard=ReportDashboard.model_validate(row.dashboard),
    )


def snapshot(db: Session, org: UUID, key: UUID) -> CohortImpactSnapshot:
    row = db.scalar(
        select(CohortImpactSnapshot).where(
            CohortImpactSnapshot.organization_id == org, CohortImpactSnapshot.id == key
        )
    )
    if row is None:
        raise AuthError("not_found", 404)
    return row


def create_snapshot(
    db: Session, org: UUID, actor: User, data: ReportSnapshotCreate, request_id: str
) -> ReportSnapshotView:
    require_permission(db, actor, org, "report.view")
    filters = ReportFilters.model_validate(data.model_dump(exclude={"request_id"}))
    request_digest = digest(filters.model_dump(mode="json"))
    with Session(
        bind=db.get_bind().execution_options(isolation_level="REPEATABLE READ")
    ) as coherent:
        require_permission(coherent, actor, org, "report.view")
        replay = coherent.scalar(
            select(CohortImpactSnapshot).where(
                CohortImpactSnapshot.organization_id == org,
                CohortImpactSnapshot.requester_user_id == actor.id,
                CohortImpactSnapshot.request_id == data.request_id,
            )
        )
        if replay:
            if replay.request_digest != request_digest:
                raise AuthError("report_request_reused", 409)
            audit(coherent, org, actor, replay.id, "report.snapshot.read", request_id, "request_id")
            result = snapshot_view(replay)
            commit(coherent)
            return result
        response = build_dashboard(coherent, org, filters)
        if len(json.dumps(response.model_dump(mode="json"), ensure_ascii=False).encode()) > 900000:
            raise AuthError("report_too_large_narrow_filters", 422)
        row = CohortImpactSnapshot(
            organization_id=org,
            requester_user_id=actor.id,
            request_id=data.request_id,
            request_digest=request_digest,
            filters=filters.model_dump(mode="json"),
            dictionary_version=DICTIONARY_VERSION,
            definition_ids=[str(group.definition.id) for group in response.impact],
            dashboard=response.model_dump(mode="json"),
        )
        coherent.add(row)
        coherent.flush()
        audit(
            coherent,
            org,
            actor,
            row.id,
            "report.snapshot.created",
            request_id,
            ",".join(name for name, value in filters.model_dump().items() if value is not None),
        )
        result = snapshot_view(row)
        commit(coherent)
        return result


def snapshot_detail(
    db: Session, org: UUID, key: UUID, actor: User, request_id: str
) -> ReportSnapshotView:
    require_permission(db, actor, org, "report.view")
    row = snapshot(db, org, key)
    result = snapshot_view(row)
    audit(db, org, actor, key, "report.snapshot.read", request_id)
    commit(db)
    return result


def snapshots(
    db: Session, org: UUID, actor: User, cursor: UUID | None, limit: int, request_id: str
) -> ReportSnapshotList:
    require_permission(db, actor, org, "report.view")
    query = select(
        CohortImpactSnapshot.id,
        CohortImpactSnapshot.created_at,
        CohortImpactSnapshot.request_id,
        CohortImpactSnapshot.filters,
        CohortImpactSnapshot.dictionary_version,
        CohortImpactSnapshot.dashboard["generated_at"].as_string().label("generated_at"),
    ).where(CohortImpactSnapshot.organization_id == org)
    if cursor:
        if db.execute(query.where(CohortImpactSnapshot.id == cursor)).first() is None:
            raise AuthError("invalid_cursor", 422)
        query = query.where(CohortImpactSnapshot.id > cursor)
    rows = list(db.execute(query.order_by(CohortImpactSnapshot.id).limit(limit + 1)))
    result = ReportSnapshotList(
        items=[ReportSnapshotSummary.model_validate(dict(row._mapping)) for row in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )
    audit(db, org, actor, org, "report.snapshots.read", request_id, "cursor,limit")
    commit(db)
    return result


def csv_cell(value: object) -> str:
    if isinstance(value, (int, float)):
        return str(value)
    cell = "" if value is None else str(value)
    if cell.lstrip("\ufeff \t\r\n\v\f").startswith(("=", "+", "-", "@")):
        return "'" + cell
    return cell


def csv_report(dashboard: ReportDashboard) -> tuple[str, int]:
    rows: list[list[object]] = [
        [
            "group",
            "metric",
            "label_en",
            "label_ta",
            "value",
            "unit",
            "numerator",
            "denominator",
            "source",
            "temporal_basis",
            "definition_en",
            "caveat_en",
        ]
    ]
    for metric in dashboard.metrics:
        rows.append(
            [
                metric.group,
                metric.key,
                metric.label_en,
                metric.label_ta,
                metric.value,
                metric.unit,
                metric.numerator,
                metric.denominator,
                metric.source,
                metric.temporal_basis,
                metric.definition_en,
                metric.caveat_en,
            ]
        )
        for bucket in metric.breakdown:
            rows.append(
                [
                    metric.group,
                    metric.key + ":" + bucket.key,
                    bucket.label,
                    "",
                    bucket.count,
                    "count",
                    "",
                    "",
                    metric.source,
                    metric.temporal_basis,
                    "Breakdown of " + metric.key,
                    metric.caveat_en,
                ]
            )
    for group in dashboard.impact:
        for name in (
            "eligible_enrollments",
            "baseline_reported",
            "outcome_reported",
            "matched_sample",
            "baseline_jobs",
            "outcome_jobs",
            "matched_baseline_jobs",
            "matched_outcome_jobs",
            "matched_jobs_change",
            "outcome_started",
            "outcome_active",
        ):
            rows.append(
                [
                    "impact",
                    f"edition_{group.definition.edition}:{name}",
                    group.definition.title_en,
                    group.definition.title_ta,
                    getattr(group, name),
                    "count",
                    "",
                    "",
                    "impact_records",
                    "latest observations in selected period",
                    group.definition.definition_en,
                    group.caveat_en,
                ]
            )
    # Include context so an isolated CSV remains independently interpretable.
    rows.extend(
        [
            ["context", key, value, "", "", "", "", "", "", "", "", ""]
            for key, value in {
                "from_date": dashboard.filters.from_date.isoformat(),
                "through_date": dashboard.filters.through_date.isoformat(),
                "program_id": dashboard.filters.program_id,
                "cohort_id": dashboard.filters.cohort_id,
                "generated_at": dashboard.generated_at.isoformat(),
                "dictionary_version": dashboard.dictionary_version,
                "eligible_impact_enrollments": dashboard.eligible_impact_enrollments,
                "impact_reported_enrollments": dashboard.impact_reported_enrollments,
                "impact_coverage_percent": dashboard.impact_coverage,
                "caveat": dashboard.caveat_en,
            }.items()
        ]
    )
    if len(rows) > 500:
        raise AuthError("report_export_too_large", 422)
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerows([[csv_cell(cell) for cell in row] for row in rows])
    content = buffer.getvalue()
    if len(content.encode("utf-8")) > 262144:
        raise AuthError("report_export_too_large", 422)
    return content, len(rows)


def require_export(db: Session, org: UUID, actor: User) -> None:
    require_permission(db, actor, org, "report.view")
    require_permission(db, actor, org, "report.export")


def export_row(db: Session, org: UUID, key: UUID, actor: User) -> ReportExport:
    require_export(db, org, actor)
    row = db.scalar(
        select(ReportExport).where(
            ReportExport.organization_id == org,
            ReportExport.id == key,
            ReportExport.requester_user_id == actor.id,
        )
    )
    if row is None:
        raise AuthError("not_found", 404)
    return row


def create_export(
    db: Session, org: UUID, actor: User, data: ReportExportCreate, request_id: str
) -> ReportExportView:
    require_export(db, org, actor)
    request_digest = digest(data.model_dump(mode="json", exclude={"request_id"}))
    replay = db.scalar(
        select(ReportExport).where(
            ReportExport.organization_id == org,
            ReportExport.requester_user_id == actor.id,
            ReportExport.request_id == data.request_id,
        )
    )
    if replay:
        if replay.request_digest != request_digest:
            raise AuthError("report_request_reused", 409)
        return ReportExportView.model_validate(replay)
    source = snapshot(db, org, data.snapshot_id)
    content, row_count = csv_report(ReportDashboard.model_validate(source.dashboard))
    row = ReportExport(
        organization_id=org,
        requester_user_id=actor.id,
        snapshot_id=source.id,
        request_id=data.request_id,
        request_digest=request_digest,
        reason=data.reason,
        expires_at=now() + timedelta(hours=24),
        csv_content=content,
        row_count=row_count,
        byte_count=len(content.encode("utf-8")),
    )
    db.add(row)
    db.flush()
    audit(db, org, actor, row.id, "report.export.created", request_id, "snapshot_id,request_id")
    commit(db)
    return ReportExportView.model_validate(row)


def exports(
    db: Session, org: UUID, actor: User, cursor: UUID | None, limit: int
) -> ReportExportList:
    require_export(db, org, actor)
    query = select(ReportExport).where(
        ReportExport.organization_id == org, ReportExport.requester_user_id == actor.id
    )
    if cursor:
        if db.scalar(query.where(ReportExport.id == cursor)) is None:
            raise AuthError("invalid_cursor", 422)
        query = query.where(ReportExport.id > cursor)
    rows = list(db.scalars(query.order_by(ReportExport.id).limit(limit + 1)))
    return ReportExportList(
        items=[ReportExportView.model_validate(row) for row in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


def export_detail(db: Session, org: UUID, key: UUID, actor: User) -> ReportExportView:
    return ReportExportView.model_validate(export_row(db, org, key, actor))


def export_access(
    db: Session, org: UUID, key: UUID, actor: User, request_id: str
) -> ReportExportAccess:
    row = export_row(db, org, key, actor)
    if row.expires_at <= now():
        raise AuthError("report_export_expired", 410)
    token = secrets.token_urlsafe(32)
    expiry = min(now() + timedelta(minutes=5), row.expires_at)
    db.add(
        ReportExportCapability(
            organization_id=org,
            export_id=key,
            requester_user_id=actor.id,
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            expires_at=expiry,
        )
    )
    audit(db, org, actor, key, "report.export.access", request_id)
    commit(db)
    return ReportExportAccess(token=token, expires_at=expiry)


def export_download(
    db: Session, org: UUID, key: UUID, token: str, actor: User, request_id: str
) -> bytes:
    row = export_row(db, org, key, actor)
    capability = db.scalar(
        select(ReportExportCapability).where(
            ReportExportCapability.organization_id == org,
            ReportExportCapability.export_id == key,
            ReportExportCapability.requester_user_id == actor.id,
            ReportExportCapability.token_hash == hashlib.sha256(token.encode()).hexdigest(),
        )
    )
    if row.expires_at <= now() or (capability and capability.expires_at <= now()):
        raise AuthError("report_export_expired", 410)
    if capability is None:
        raise AuthError("not_found", 404)
    audit(db, org, actor, key, "report.export.download", request_id)
    content = row.csv_content.encode("utf-8")
    commit(db)
    return content
