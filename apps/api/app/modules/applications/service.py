from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal, cast
from uuid import UUID

from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.applications.models import (
    Application,
    ApplicationAcknowledgement,
    ApplicationAcknowledgementDefinition,
    ApplicationAnswer,
    ApplicationField,
    ApplicationForm,
    ApplicationRevision,
    ApplicationStatusHistory,
)
from app.modules.applications.schemas import (
    AcceptedAcknowledgementView,
    AcknowledgementKind,
    AcknowledgementView,
    AnswerView,
    CycleOpportunityList,
    CycleOpportunityView,
    DefinitionCommand,
    DefinitionContent,
    DefinitionCreate,
    DefinitionList,
    DefinitionState,
    DefinitionUpdate,
    DefinitionView,
    DraftSave,
    DraftView,
    FieldType,
    FieldView,
    FormView,
    StatusHistoryView,
    SubmitCommand,
    SubmittedView,
)
from app.modules.identity.models import AuditLog, Organization, User, now
from app.modules.identity.security import AuthError
from app.modules.identity.service import require_permission
from app.modules.programs.models import ApplicationCycle


def _fields(db: Session, form_id: UUID) -> list[ApplicationField]:
    return list(
        db.scalars(
            select(ApplicationField)
            .where(ApplicationField.form_id == form_id)
            .order_by(ApplicationField.position)
            .limit(101)
        )
    )


def _acknowledgements(db: Session, form_id: UUID) -> list[ApplicationAcknowledgementDefinition]:
    return list(
        db.scalars(
            select(ApplicationAcknowledgementDefinition)
            .where(ApplicationAcknowledgementDefinition.form_id == form_id)
            .order_by(ApplicationAcknowledgementDefinition.position)
            .limit(21)
        )
    )


def form_view(db: Session, form: ApplicationForm, fields: list[ApplicationField]) -> FormView:
    return FormView(
        id=form.id,
        organization_id=form.organization_id,
        version=form.version,
        title_en=form.title_en,
        title_ta=form.title_ta,
        fields=[
            FieldView(
                id=item.id,
                key=item.field_key,
                section=item.section_key,
                label_en=item.label_en,
                label_ta=item.label_ta,
                field_type=cast(FieldType, item.field_type),
                required=item.required,
                position=item.position,
            )
            for item in fields
        ],
        acknowledgements=[
            AcknowledgementView(
                id=item.id,
                key=item.acknowledgement_key,
                kind=cast(AcknowledgementKind, item.kind),
                label_en=item.label_en,
                label_ta=item.label_ta,
                required=item.required,
                position=item.position,
            )
            for item in _acknowledgements(db, form.id)
        ],
    )


def definition_view(
    db: Session,
    form: ApplicationForm,
    fields: list[ApplicationField] | None = None,
) -> DefinitionView:
    result = form_view(db, form, fields if fields is not None else _fields(db, form.id))
    return DefinitionView(
        **result.model_dump(),
        state=cast(DefinitionState, form.state),
        revision=form.revision,
        published_at=form.published_at,
        created_at=form.created_at,
    )


def _definition(db: Session, org: UUID, definition_id: UUID, lock: bool = False) -> ApplicationForm:
    statement = select(ApplicationForm).where(
        ApplicationForm.id == definition_id,
        ApplicationForm.organization_id == org,
    )
    if lock:
        statement = statement.with_for_update()
    form = db.scalar(statement)
    if not form:
        raise AuthError("not_found", 404)
    return form


def _audit_definition(
    db: Session,
    actor: User,
    org: UUID,
    form: ApplicationForm,
    action: str,
    request_id: str,
    changed_fields: str,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=form.id,
            action=action,
            request_id=request_id,
            resource_version=form.revision,
            changed_fields=changed_fields,
        )
    )


def _replace_policy(
    db: Session,
    form: ApplicationForm,
    data: DefinitionContent,
) -> list[ApplicationField]:
    db.execute(delete(ApplicationField).where(ApplicationField.form_id == form.id))
    db.execute(
        delete(ApplicationAcknowledgementDefinition).where(
            ApplicationAcknowledgementDefinition.form_id == form.id
        )
    )
    fields = [
        ApplicationField(
            form_id=form.id,
            field_key=item.key,
            section_key=item.section,
            label_en=item.label_en,
            label_ta=item.label_ta,
            field_type=item.field_type,
            required=item.required,
            position=position,
        )
        for position, item in enumerate(data.fields, start=1)
    ]
    acknowledgements = [
        ApplicationAcknowledgementDefinition(
            form_id=form.id,
            acknowledgement_key=item.key,
            kind=item.kind,
            label_en=item.label_en,
            label_ta=item.label_ta,
            required=item.required,
            position=position,
        )
        for position, item in enumerate(data.acknowledgements, start=1)
    ]
    db.add_all([*fields, *acknowledgements])
    return fields


def list_definitions(db: Session, org: UUID, actor: User) -> DefinitionList:
    require_permission(db, actor, org, "application.form.view")
    forms = list(
        db.scalars(
            select(ApplicationForm)
            .where(ApplicationForm.organization_id == org)
            .order_by(ApplicationForm.version.desc())
            .limit(100)
        )
    )
    return DefinitionList(items=[definition_view(db, item) for item in forms])


def get_definition(
    db: Session,
    org: UUID,
    definition_id: UUID,
    actor: User,
) -> DefinitionView:
    require_permission(db, actor, org, "application.form.view")
    return definition_view(db, _definition(db, org, definition_id))


def _next_version(db: Session, org: UUID) -> int:
    if not db.scalar(select(Organization.id).where(Organization.id == org).with_for_update()):
        raise AuthError("not_found", 404)
    return (
        int(
            db.scalar(
                select(func.coalesce(func.max(ApplicationForm.version), 0)).where(
                    ApplicationForm.organization_id == org
                )
            )
            or 0
        )
        + 1
    )


def _ensure_no_draft(db: Session, org: UUID) -> None:
    if db.scalar(
        select(ApplicationForm.id).where(
            ApplicationForm.organization_id == org,
            ApplicationForm.state == "draft",
        )
    ):
        raise AuthError("application_definition_draft_exists", 409)


def create_definition(
    db: Session,
    org: UUID,
    actor: User,
    data: DefinitionCreate,
    request_id: str,
) -> DefinitionView:
    require_permission(db, actor, org, "application.form.create")
    _ensure_no_draft(db, org)
    form = ApplicationForm(
        organization_id=org,
        version=_next_version(db, org),
        revision=1,
        state="draft",
        title_en=data.title_en,
        title_ta=data.title_ta,
    )
    db.add(form)
    try:
        db.flush()
        fields = _replace_policy(db, form, data)
        _audit_definition(
            db,
            actor,
            org,
            form,
            "application.definition_created",
            request_id,
            "title_en,title_ta,fields,acknowledgements",
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("version_conflict", 409) from exc
    return definition_view(db, form, fields)


def update_definition(
    db: Session,
    org: UUID,
    definition_id: UUID,
    actor: User,
    data: DefinitionUpdate,
    request_id: str,
) -> DefinitionView:
    require_permission(db, actor, org, "application.form.update")
    form = _definition(db, org, definition_id, lock=True)
    if form.state != "draft":
        raise AuthError("application_definition_immutable", 409)
    if form.revision != data.expected_revision:
        raise AuthError("version_conflict", 409)
    form.title_en = data.title_en
    form.title_ta = data.title_ta
    form.revision += 1
    fields = _replace_policy(db, form, data)
    _audit_definition(
        db,
        actor,
        org,
        form,
        "application.definition_updated",
        request_id,
        "title_en,title_ta,fields,acknowledgements",
    )
    db.commit()
    return definition_view(db, form, fields)


def copy_definition(
    db: Session,
    org: UUID,
    definition_id: UUID,
    actor: User,
    data: DefinitionCommand,
    request_id: str,
) -> DefinitionView:
    require_permission(db, actor, org, "application.form.create")
    source = _definition(db, org, definition_id, lock=True)
    if source.revision != data.expected_revision:
        raise AuthError("version_conflict", 409)
    if source.state == "draft":
        raise AuthError("invalid_transition", 409)
    _ensure_no_draft(db, org)
    source_fields = _fields(db, source.id)
    source_acknowledgements = _acknowledgements(db, source.id)
    form = ApplicationForm(
        organization_id=org,
        version=_next_version(db, org),
        revision=1,
        state="draft",
        title_en=source.title_en,
        title_ta=source.title_ta,
    )
    db.add(form)
    try:
        db.flush()
        fields = [
            ApplicationField(
                form_id=form.id,
                field_key=item.field_key,
                section_key=item.section_key,
                label_en=item.label_en,
                label_ta=item.label_ta,
                field_type=item.field_type,
                required=item.required,
                position=item.position,
            )
            for item in source_fields
        ]
        acknowledgements = [
            ApplicationAcknowledgementDefinition(
                form_id=form.id,
                acknowledgement_key=item.acknowledgement_key,
                kind=item.kind,
                label_en=item.label_en,
                label_ta=item.label_ta,
                required=item.required,
                position=item.position,
            )
            for item in source_acknowledgements
        ]
        db.add_all([*fields, *acknowledgements])
        _audit_definition(
            db,
            actor,
            org,
            form,
            "application.definition_copied",
            request_id,
            "source_definition",
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("version_conflict", 409) from exc
    return definition_view(db, form, fields)


def publish_definition(
    db: Session,
    org: UUID,
    definition_id: UUID,
    actor: User,
    data: DefinitionCommand,
    request_id: str,
) -> DefinitionView:
    require_permission(db, actor, org, "application.form.publish")
    form = _definition(db, org, definition_id, lock=True)
    if form.state != "draft":
        raise AuthError("invalid_transition", 409)
    if form.revision != data.expected_revision:
        raise AuthError("version_conflict", 409)
    fields = _fields(db, form.id)
    acknowledgements = _acknowledgements(db, form.id)
    required_kinds = {item.kind for item in acknowledgements if item.required}
    if not fields or not {"declaration", "consent"}.issubset(required_kinds):
        raise AuthError("application_configuration_invalid", 422)
    active = list(
        db.scalars(
            select(ApplicationForm)
            .where(
                ApplicationForm.organization_id == org,
                ApplicationForm.state == "published",
                ApplicationForm.id != form.id,
            )
            .with_for_update()
        )
    )
    for previous in active:
        previous.state = "retired"
        previous.revision += 1
    form.state = "published"
    form.published_at = now()
    form.published_by_id = actor.id
    form.revision += 1
    _audit_definition(
        db,
        actor,
        org,
        form,
        "application.definition_published",
        request_id,
        "state,published_at,published_by_id",
    )
    db.commit()
    return definition_view(db, form, fields)


def published_form(db: Session, org: UUID) -> tuple[ApplicationForm, list[ApplicationField]]:
    form = db.scalar(
        select(ApplicationForm)
        .where(ApplicationForm.organization_id == org, ApplicationForm.state == "published")
        .order_by(ApplicationForm.version.desc())
        .limit(1)
    )
    if not form:
        raise AuthError("application_unavailable", 404)
    fields = _fields(db, form.id)
    if len(fields) > 100:
        raise AuthError("application_configuration_invalid", 503)
    return form, fields


def get_form(db: Session, org: UUID) -> FormView:
    form, fields = published_form(db, org)
    return form_view(db, form, fields)


def _validate(field: ApplicationField, value: str) -> str:
    cleaned = value.strip()
    if len(cleaned) > 5000:
        raise AuthError("invalid_answer", 422)
    if not cleaned:
        return ""
    try:
        if field.field_type == "number":
            Decimal(cleaned)
        elif field.field_type == "date":
            date.fromisoformat(cleaned)
        elif field.field_type == "boolean" and cleaned not in {"true", "false"}:
            raise ValueError
    except (InvalidOperation, ValueError) as exc:
        raise AuthError("invalid_answer", 422) from exc
    return cleaned


def _view(
    db: Session,
    application: Application,
    form: ApplicationForm,
    fields: list[ApplicationField],
) -> DraftView:
    revision = db.get(ApplicationRevision, application.current_revision_id)
    if not revision:
        raise AuthError("application_integrity_error", 503)
    answers = list(
        db.scalars(
            select(ApplicationAnswer)
            .where(ApplicationAnswer.revision_id == revision.id)
            .order_by(ApplicationAnswer.field_id)
            .limit(101)
        )
    )
    values = {item.field_id: item.value for item in answers}
    required = [item for item in fields if item.required]
    completed = sum(bool(values.get(item.id, "").strip()) for item in required)
    percent = 100 if not required else int(completed * 100 / len(required))
    return DraftView(
        id=application.id,
        cycle_id=application.cycle_id,
        form=form_view(db, form, fields),
        state="draft",
        version=application.version,
        revision=revision.revision,
        completion_percent=percent,
        answers=[AnswerView(field_id=item.field_id, value=item.value) for item in answers],
        updated_at=application.updated_at,
    )


def create_draft(db: Session, org: UUID, actor: User, request_id: str) -> DraftView:
    form, fields = published_form(db, org)
    existing = db.scalar(
        select(Application).where(
            Application.person_id == actor.person_id,
            Application.form_id == form.id,
        )
    )
    if existing:
        return _view(db, existing, form, fields)
    application = Application(
        organization_id=org,
        person_id=actor.person_id,
        form_id=form.id,
    )
    db.add(application)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("version_conflict", 409) from exc
    revision = ApplicationRevision(application_id=application.id, form_id=form.id, revision=1)
    db.add(revision)
    db.flush()
    application.current_revision_id = revision.id
    db.add(
        ApplicationStatusHistory(
            application_id=application.id,
            actor_user_id=actor.id,
            from_state=None,
            to_state="draft",
            application_version=1,
            reason_code="applicant_started",
        )
    )
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=application.id,
            action="application.draft_created",
            request_id=request_id,
            resource_version=1,
            changed_fields="state",
        )
    )
    db.commit()
    return _view(db, application, form, fields)


def mine(db: Session, org: UUID, actor: User) -> DraftView:
    application = db.scalar(
        select(Application).where(
            Application.organization_id == org,
            Application.person_id == actor.person_id,
            Application.state == "draft",
        )
    )
    if not application:
        raise AuthError("not_found", 404)
    form = db.get(ApplicationForm, application.form_id)
    if not form:
        raise AuthError("application_integrity_error", 503)
    return _view(db, application, form, _fields(db, form.id))


def save(
    db: Session,
    org: UUID,
    application_id: UUID,
    actor: User,
    data: DraftSave,
    request_id: str,
) -> DraftView:
    application = db.scalar(
        select(Application)
        .where(
            Application.id == application_id,
            Application.organization_id == org,
            Application.person_id == actor.person_id,
            Application.state == "draft",
        )
        .with_for_update()
    )
    if not application:
        raise AuthError("not_found", 404)
    if application.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    form = db.get(ApplicationForm, application.form_id)
    if not form:
        raise AuthError("application_integrity_error", 503)
    fields = _fields(db, form.id)
    field_map = {item.id: item for item in fields}
    if any(item.field_id not in field_map for item in data.answers):
        raise AuthError("invalid_answer", 422)
    revision = ApplicationRevision(
        application_id=application.id,
        form_id=form.id,
        revision=application.version + 1,
    )
    db.add(revision)
    db.flush()
    for item in data.answers:
        value = _validate(field_map[item.field_id], item.value)
        if value:
            db.add(ApplicationAnswer(revision_id=revision.id, field_id=item.field_id, value=value))
    application.current_revision_id = revision.id
    application.version += 1
    application.updated_at = now()
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=application.id,
            action="application.draft_saved",
            request_id=request_id,
            resource_version=application.version,
            changed_fields="answers",
        )
    )
    db.commit()
    return _view(db, application, form, fields)


def _open_cycle(db: Session, org: UUID, cycle_id: UUID, lock: bool = False) -> ApplicationCycle:
    query = select(ApplicationCycle).where(
        ApplicationCycle.id == cycle_id,
        ApplicationCycle.organization_id == org,
    )
    cycle = db.scalar(query.with_for_update() if lock else query)
    current = now()
    if not cycle or cycle.state != "open" or cycle.opens_at > current or cycle.closes_at <= current:
        raise AuthError("application_cycle_unavailable", 404)
    return cycle


def available_cycles(db: Session, org: UUID) -> CycleOpportunityList:
    current = now()
    rows = list(
        db.scalars(
            select(ApplicationCycle)
            .where(
                ApplicationCycle.organization_id == org,
                ApplicationCycle.state == "open",
                ApplicationCycle.opens_at <= current,
                ApplicationCycle.closes_at > current,
            )
            .order_by(ApplicationCycle.closes_at, ApplicationCycle.id)
            .limit(100)
        )
    )
    return CycleOpportunityList(
        items=[
            CycleOpportunityView(
                id=item.id,
                code=item.code,
                name_en=item.name_en,
                name_ta=item.name_ta,
                form_id=item.form_id,
                opens_at=item.opens_at,
                closes_at=item.closes_at,
            )
            for item in rows
        ]
    )


def _create_cycle_draft(
    db: Session,
    org: UUID,
    cycle: ApplicationCycle,
    actor: User,
    request_id: str,
) -> DraftView:
    existing = db.scalar(
        select(Application).where(
            Application.person_id == actor.person_id,
            Application.cycle_id == cycle.id,
        )
    )
    if existing:
        form = db.get(ApplicationForm, existing.form_id)
        if not form:
            raise AuthError("application_integrity_error", 503)
        if existing.state == "submitted":
            raise AuthError("application_already_submitted", 409)
        return _view(db, existing, form, _fields(db, form.id))
    form = db.get(ApplicationForm, cycle.form_id)
    if not form or form.organization_id != org or form.state not in {"published", "retired"}:
        raise AuthError("application_configuration_invalid", 503)
    fields = _fields(db, form.id)
    application = Application(
        organization_id=org,
        person_id=actor.person_id,
        form_id=form.id,
        cycle_id=cycle.id,
    )
    db.add(application)
    try:
        db.flush()
        revision = ApplicationRevision(
            application_id=application.id,
            form_id=form.id,
            revision=1,
        )
        db.add(revision)
        db.flush()
        application.current_revision_id = revision.id
        db.add(
            ApplicationStatusHistory(
                application_id=application.id,
                actor_user_id=actor.id,
                from_state=None,
                to_state="draft",
                application_version=1,
                reason_code="applicant_started",
            )
        )
        db.add(
            AuditLog(
                actor_id=actor.id,
                organization_id=org,
                resource_id=application.id,
                action="application.draft_created",
                request_id=request_id,
                resource_version=1,
                changed_fields="state,cycle_id,form_id",
            )
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("version_conflict", 409) from exc
    return _view(db, application, form, fields)


def create_cycle_draft(
    db: Session,
    org: UUID,
    cycle_id: UUID,
    actor: User,
    request_id: str,
) -> DraftView:
    return _create_cycle_draft(db, org, _open_cycle(db, org, cycle_id), actor, request_id)


def _submitted_view(
    db: Session,
    application: Application,
    form: ApplicationForm,
) -> SubmittedView:
    revision = db.get(ApplicationRevision, application.current_revision_id)
    if (
        not revision
        or not application.cycle_id
        or not application.application_number
        or not application.submitted_at
    ):
        raise AuthError("application_integrity_error", 503)
    answers = list(
        db.scalars(
            select(ApplicationAnswer)
            .where(ApplicationAnswer.revision_id == revision.id)
            .order_by(ApplicationAnswer.field_id)
            .limit(101)
        )
    )
    accepted = list(
        db.scalars(
            select(ApplicationAcknowledgement)
            .where(ApplicationAcknowledgement.application_id == application.id)
            .order_by(ApplicationAcknowledgement.accepted_at, ApplicationAcknowledgement.id)
            .limit(21)
        )
    )
    history = list(
        db.scalars(
            select(ApplicationStatusHistory)
            .where(ApplicationStatusHistory.application_id == application.id)
            .order_by(ApplicationStatusHistory.application_version)
            .limit(25)
        )
    )
    return SubmittedView(
        id=application.id,
        cycle_id=application.cycle_id,
        form=form_view(db, form, _fields(db, form.id)),
        state=cast(
            "Literal['submitted', 'under_review', 'shortlisted', "
            "'interview_scheduled', 'selected', 'waitlisted', 'rejected', 'enrolled']",
            application.state,
        ),
        version=application.version,
        revision=revision.revision,
        completion_percent=100,
        application_number=application.application_number,
        submitted_at=application.submitted_at,
        answers=[AnswerView(field_id=item.field_id, value=item.value) for item in answers],
        accepted_acknowledgements=[
            AcceptedAcknowledgementView(
                definition_id=item.definition_id,
                accepted_at=item.accepted_at,
            )
            for item in accepted
        ],
        status_history=[
            StatusHistoryView(
                from_state=item.from_state,
                to_state=item.to_state,
                application_version=item.application_version,
                reason_code=item.reason_code,
                created_at=item.created_at,
            )
            for item in history
        ],
        updated_at=application.updated_at,
    )


def cycle_application(
    db: Session,
    org: UUID,
    cycle_id: UUID,
    actor: User,
) -> DraftView | SubmittedView:
    application = db.scalar(
        select(Application).where(
            Application.organization_id == org,
            Application.cycle_id == cycle_id,
            Application.person_id == actor.person_id,
        )
    )
    if not application:
        raise AuthError("not_found", 404)
    form = db.get(ApplicationForm, application.form_id)
    if not form:
        raise AuthError("application_integrity_error", 503)
    if application.state != "draft":
        return _submitted_view(db, application, form)
    return _view(db, application, form, _fields(db, form.id))


def submit(
    db: Session,
    org: UUID,
    application_id: UUID,
    actor: User,
    data: SubmitCommand,
    request_id: str,
) -> SubmittedView:
    application = db.scalar(
        select(Application)
        .where(
            Application.id == application_id,
            Application.organization_id == org,
            Application.person_id == actor.person_id,
        )
        .with_for_update()
    )
    if not application:
        raise AuthError("not_found", 404)
    form = db.get(ApplicationForm, application.form_id)
    if not form:
        raise AuthError("application_integrity_error", 503)
    if application.state != "draft":
        return _submitted_view(db, application, form)
    if application.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    if not application.cycle_id:
        raise AuthError("application_cycle_required", 422)
    cycle = _open_cycle(db, org, application.cycle_id, lock=True)
    if cycle.form_id != application.form_id:
        raise AuthError("application_configuration_invalid", 503)
    revision = db.get(ApplicationRevision, application.current_revision_id)
    if not revision:
        raise AuthError("application_integrity_error", 503)
    fields = _fields(db, form.id)
    answers = list(
        db.scalars(select(ApplicationAnswer).where(ApplicationAnswer.revision_id == revision.id))
    )
    values = {item.field_id: item.value.strip() for item in answers}
    if any(item.required and not values.get(item.id) for item in fields):
        raise AuthError("application_incomplete", 422)
    definitions = _acknowledgements(db, form.id)
    required_kinds = {item.kind for item in definitions if item.required}
    if not {"declaration", "consent"}.issubset(required_kinds):
        raise AuthError("application_configuration_invalid", 503)
    allowed_ids = {item.id for item in definitions}
    accepted_ids = set(data.accepted_acknowledgement_ids)
    required_ids = {item.id for item in definitions if item.required}
    if not accepted_ids.issubset(allowed_ids) or not required_ids.issubset(accepted_ids):
        raise AuthError("acknowledgement_required", 422)
    submitted_at = now()
    sequence = db.scalar(text("SELECT nextval('application_number_seq')"))
    if sequence is None:
        raise AuthError("application_integrity_error", 503)
    application_number = f"EDP-{submitted_at.year}-{int(sequence):08d}"
    for definition_id in accepted_ids:
        db.add(
            ApplicationAcknowledgement(
                application_id=application.id,
                form_id=form.id,
                definition_id=definition_id,
                accepted_at=submitted_at,
            )
        )
    # Acceptance evidence must exist while the application is still a draft.
    # The database trigger freezes it in the same transaction on submission.
    db.flush()
    previous_state = application.state
    application.state = "submitted"
    application.version += 1
    application.application_number = application_number
    application.submitted_at = submitted_at
    application.updated_at = submitted_at
    db.add(
        ApplicationStatusHistory(
            application_id=application.id,
            actor_user_id=actor.id,
            from_state=previous_state,
            to_state="submitted",
            application_version=application.version,
            reason_code="applicant_submitted",
        )
    )
    db.add(
        AuditLog(
            actor_id=actor.id,
            organization_id=org,
            resource_id=application.id,
            action="application.submitted",
            request_id=request_id,
            resource_version=application.version,
            changed_fields=(
                "state,cycle_id,current_revision_id,application_number,submitted_at,"
                "acknowledgements"
            ),
        )
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("version_conflict", 409) from exc
    return _submitted_view(db, application, form)
