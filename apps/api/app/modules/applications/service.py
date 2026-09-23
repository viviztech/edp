from datetime import date
from decimal import Decimal, InvalidOperation
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.applications.models import (
    Application,
    ApplicationAnswer,
    ApplicationField,
    ApplicationForm,
    ApplicationRevision,
)
from app.modules.applications.schemas import (
    AnswerView,
    DraftSave,
    DraftView,
    FieldType,
    FieldView,
    FormView,
)
from app.modules.identity.models import AuditLog, User, now
from app.modules.identity.security import AuthError


def form_view(form: ApplicationForm, fields: list[ApplicationField]) -> FormView:
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
    )


def published_form(db: Session, org: UUID) -> tuple[ApplicationForm, list[ApplicationField]]:
    form = db.scalar(
        select(ApplicationForm)
        .where(ApplicationForm.organization_id == org, ApplicationForm.state == "published")
        .order_by(ApplicationForm.version.desc())
        .limit(1)
    )
    if not form:
        raise AuthError("application_unavailable", 404)
    fields = list(
        db.scalars(
            select(ApplicationField)
            .where(ApplicationField.form_id == form.id)
            .order_by(ApplicationField.position)
            .limit(101)
        )
    )
    if len(fields) > 100:
        raise AuthError("application_configuration_invalid", 503)
    return form, fields


def get_form(db: Session, org: UUID) -> FormView:
    form, fields = published_form(db, org)
    return form_view(form, fields)


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
        form=form_view(form, fields),
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
    fields = list(
        db.scalars(
            select(ApplicationField)
            .where(ApplicationField.form_id == form.id)
            .order_by(ApplicationField.position)
            .limit(101)
        )
    )
    return _view(db, application, form, fields)


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
    fields = list(db.scalars(select(ApplicationField).where(ApplicationField.form_id == form.id)))
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
    return _view(db, application, form, sorted(fields, key=lambda item: item.position))
