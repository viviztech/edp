"""Application-authorized document operations; no generic file access is granted."""

import hashlib
import json
from collections import Counter
from datetime import datetime
from typing import BinaryIO
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.applications.document_policy import requirement_views, requirements
from app.modules.applications.document_schemas import (
    ApplicationDocumentList,
    ApplicationDocumentResult,
    ApplicationDocumentView,
    DocumentCreate,
    DocumentEvidenceView,
    DocumentRemove,
)
from app.modules.applications.models import (
    Application,
    ApplicationDocument,
    ApplicationDocumentEvidence,
    ApplicationForm,
    DocumentRequirement,
)
from app.modules.files import service as files
from app.modules.files.models import FileObject, FilePolicy
from app.modules.files.runtime import require_files_enabled
from app.modules.files.schemas import FileCreate, FileView
from app.modules.files.storage import PrivateStorage, StoredObject
from app.modules.identity.models import AuditLog, User, now
from app.modules.identity.security import AuthError
from app.modules.identity.service import require_permission, throttle
from app.modules.selection.models import ReviewAssignment, SelectionCycle


def owner_application(
    db: Session, org: UUID, application_id: UUID, actor: User, *, lock: bool = False
) -> Application:
    current = db.get(User, actor.id, populate_existing=True)
    if current is None or current.status != "active":
        raise AuthError("not_found", 404)
    query = (
        select(Application)
        .where(
            Application.id == application_id,
            Application.organization_id == org,
            Application.person_id == actor.person_id,
        )
        .execution_options(populate_existing=True)
    )
    row = db.scalar(query.with_for_update() if lock else query)
    if row is None or actor.status != "active":
        raise AuthError("not_found", 404)
    return row


def _editable(db: Session, row: Application, *, lock: bool = False) -> None:
    from app.modules.applications.service import _open_cycle

    if row.state != "draft":
        raise AuthError("application_documents_immutable", 409)
    if row.cycle_id is None:
        raise AuthError("application_cycle_required", 422)
    _open_cycle(db, row.organization_id, row.cycle_id, lock=lock)


def _binding(db: Session, app: Application, document_id: UUID) -> ApplicationDocument:
    row = db.scalar(
        select(ApplicationDocument)
        .where(
            ApplicationDocument.id == document_id,
            ApplicationDocument.application_id == app.id,
            ApplicationDocument.organization_id == app.organization_id,
            ApplicationDocument.owner_person_id == app.person_id,
            ApplicationDocument.form_id == app.form_id,
        )
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise AuthError("not_found", 404)
    return row


def _context(row: ApplicationDocument, actor: User) -> files.AuthorizedFileContext:
    return files.AuthorizedFileContext(
        actor.id, row.organization_id, row.owner_person_id, "application_document", row.id
    )


def _view(db: Session, row: ApplicationDocument) -> ApplicationDocumentView:
    item = db.get(FileObject, row.file_id, populate_existing=True)
    if item is None:
        raise AuthError("application_integrity_error", 503)
    evidence = db.scalar(
        select(ApplicationDocumentEvidence).where(ApplicationDocumentEvidence.document_id == row.id)
    )
    app = db.get(Application, row.application_id)
    usable = bool(
        not row.removed_at
        and item.state == "clean"
        and item.retention_until > now()
        and item.verified_at
        and item.scanned_at
        and item.stored_sha256 == item.expected_sha256
        and item.stored_byte_size == item.expected_byte_size
        and item.storage_version
        and item.scan_storage_version == item.storage_version
        and item.scan_sha256 == item.stored_sha256
        and item.scan_byte_size == item.stored_byte_size
        and app
        and (
            app.state == "draft"
            or (
                evidence
                and item.evidence_frozen
                and evidence.storage_version == item.storage_version
                and evidence.sha256 == item.stored_sha256
                and evidence.byte_size == item.stored_byte_size
            )
        )
    )
    return ApplicationDocumentView(
        id=row.id,
        requirement_id=row.requirement_id,
        file=files.file_view(item),
        usable=usable,
        removed_at=row.removed_at,
        replaced_by_id=row.replaced_by_id,
        submitted_evidence=DocumentEvidenceView(
            file_id=evidence.file_id,
            file_version=evidence.file_version,
            sha256=evidence.sha256,
            byte_size=evidence.byte_size,
            frozen_at=evidence.frozen_at,
        )
        if evidence
        else None,
    )


def _result(db: Session, app: Application, row: ApplicationDocument) -> ApplicationDocumentResult:
    return ApplicationDocumentResult(application_version=app.version, document=_view(db, row))


def _list(
    db: Session, app: Application, cursor: UUID | None, limit: int
) -> ApplicationDocumentList:
    if not 1 <= limit <= 100:
        raise AuthError("invalid_request", 422)
    query = select(ApplicationDocument).where(
        ApplicationDocument.application_id == app.id,
        ApplicationDocument.organization_id == app.organization_id,
        ApplicationDocument.removed_at.is_(None),
    )
    if cursor is not None:
        if db.scalar(query.where(ApplicationDocument.id == cursor)) is None:
            raise AuthError("invalid_cursor", 400)
        query = query.where(ApplicationDocument.id > cursor)
    rows = list(db.scalars(query.order_by(ApplicationDocument.id).limit(limit + 1)))
    settings = get_settings()
    return ApplicationDocumentList(
        application_id=app.id,
        application_version=app.version,
        collection_enabled=settings.files_enabled,
        max_upload_bytes=settings.files_max_bytes,
        document_requirements=requirement_views(db, app.form_id),
        items=[_view(db, row) for row in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


def list_documents(
    db: Session,
    org: UUID,
    application_id: UUID,
    actor: User,
    cursor: UUID | None = None,
    limit: int = 25,
) -> ApplicationDocumentList:
    return _list(db, owner_application(db, org, application_id, actor), cursor, limit)


def get_document(
    db: Session, org: UUID, application_id: UUID, document_id: UUID, actor: User
) -> ApplicationDocumentResult:
    app = owner_application(db, org, application_id, actor)
    return _result(db, app, _binding(db, app, document_id))


def _fingerprint(data: DocumentCreate) -> str:
    return hashlib.sha256(
        json.dumps(
            data.model_dump(mode="json", exclude={"expected_version"}),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def _audit(db: Session, app: Application, actor: User, action: str, request_id: str) -> None:
    db.add(
        AuditLog(
            organization_id=app.organization_id,
            actor_id=actor.id,
            resource_id=app.id,
            resource_version=app.version,
            action="application.documents." + action,
            request_id=request_id,
            changed_fields="documents,version",
        )
    )


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("version_conflict", 409) from exc


def create_document(
    db: Session,
    org: UUID,
    application_id: UUID,
    actor: User,
    data: DocumentCreate,
    request_id: str,
) -> ApplicationDocumentResult:
    settings = require_files_enabled()
    app = owner_application(db, org, application_id, actor)
    fingerprint = _fingerprint(data)
    # Exact replay does not consume another intent allowance or repeat a mutation.
    existing = db.scalar(
        select(ApplicationDocument).where(
            ApplicationDocument.organization_id == org,
            ApplicationDocument.client_request_id == data.client_request_id,
        )
    )
    if existing:
        if existing.application_id != app.id or existing.request_digest != fingerprint:
            raise AuthError("idempotency_conflict", 409)
        return _result(db, app, existing)
    _editable(db, app)
    # The durable counter commits by design; acquire domain locks only afterwards.
    throttle(
        db, "application-file:intent", f"{org}:{actor.id}", settings.files_intent_limit_per_window
    )
    app = owner_application(db, org, application_id, actor, lock=True)
    _editable(db, app, lock=True)
    existing = db.scalar(
        select(ApplicationDocument).where(
            ApplicationDocument.organization_id == org,
            ApplicationDocument.client_request_id == data.client_request_id,
        )
    )
    if existing:
        if existing.application_id != app.id or existing.request_digest != fingerprint:
            raise AuthError("idempotency_conflict", 409)
        return _result(db, app, existing)
    if app.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    rule = db.scalar(
        select(DocumentRequirement).where(
            DocumentRequirement.id == data.requirement_id,
            DocumentRequirement.form_id == app.form_id,
            DocumentRequirement.organization_id == org,
        )
    )
    if rule is None:
        raise AuthError("not_found", 404)
    policy, form = db.get(FilePolicy, rule.file_policy_id), db.get(ApplicationForm, app.form_id)
    if (
        not policy
        or not form
        or not form.published_at
        or not policy.published_at
        or policy.published_at > form.published_at
        or form.state not in {"published", "retired"}
        or policy.state not in {"published", "retired"}
    ):
        raise AuthError("file_policy_unavailable", 409)
    if data.byte_size > min(policy.max_file_bytes, settings.files_max_bytes):
        raise AuthError("file_policy_rejected", 422)
    replaced = None
    if data.replaces_document_id:
        replaced = _binding(db, app, data.replaces_document_id)
        if replaced.removed_at or replaced.requirement_id != rule.id:
            raise AuthError("document_replacement_invalid", 409)
    active = select(ApplicationDocument).where(
        ApplicationDocument.application_id == app.id,
        ApplicationDocument.removed_at.is_(None),
    )
    if replaced:
        active = active.where(ApplicationDocument.id != replaced.id)
    current = list(db.scalars(active))
    if (
        sum(row.requirement_id == rule.id for row in current) >= rule.max_files
        or sum(row.file_policy_id == policy.id for row in current) >= policy.max_files
    ):
        raise AuthError("file_count_exceeded", 409)
    document_id = uuid4()
    if replaced:
        replaced.removed_at, replaced.replaced_by_id = now(), document_id
        db.flush()  # Deferred replacement FK is satisfied by the new binding below.
    ctx = files.AuthorizedFileContext(
        actor.id, org, actor.person_id, "application_document", document_id
    )
    file = files.create_file(
        db,
        ctx,
        actor,
        FileCreate(
            client_request_id=data.client_request_id,
            policy_id=policy.id,
            media_type=data.media_type,
            byte_size=data.byte_size,
            sha256=data.sha256,
        ),
        request_id,
        commit=False,
        allow_retired_policy=policy.state == "retired",
    )
    row = ApplicationDocument(
        id=document_id,
        organization_id=org,
        application_id=app.id,
        form_id=app.form_id,
        requirement_id=rule.id,
        owner_person_id=app.person_id,
        file_policy_id=policy.id,
        file_id=file.id,
        client_request_id=data.client_request_id,
        request_digest=fingerprint,
    )
    db.add(row)
    app.version += 1
    app.updated_at = now()
    _audit(db, app, actor, "replaced" if replaced else "created", request_id)
    _commit(db)
    return _result(db, app, row)


def remove_document(
    db: Session,
    org: UUID,
    application_id: UUID,
    document_id: UUID,
    actor: User,
    data: DocumentRemove,
    request_id: str,
) -> ApplicationDocumentResult:
    require_files_enabled()
    app = owner_application(db, org, application_id, actor, lock=True)
    row = _binding(db, app, document_id)
    if row.removed_at:
        return _result(db, app, row)
    _editable(db, app, lock=True)
    if app.version != data.expected_version:
        raise AuthError("version_conflict", 409)
    row.removed_at = now()
    app.version += 1
    app.updated_at = now()
    _audit(db, app, actor, "removed", request_id)
    _commit(db)
    return _result(db, app, row)


def authorize_upload(
    db: Session,
    org: UUID,
    application_id: UUID,
    document_id: UUID,
    actor: User,
    *,
    lock: bool = False,
) -> tuple[Application, ApplicationDocument, FileView]:
    require_files_enabled()
    app = owner_application(db, org, application_id, actor, lock=lock)
    _editable(db, app, lock=lock)
    row = _binding(db, app, document_id)
    item = files.get_file(db, _context(row, actor), actor, row.file_id)
    if row.removed_at:
        raise AuthError("not_found", 404)
    if item.retention_until <= now():
        raise AuthError("file_expired", 409)
    return app, row, item


def upload_document(
    db: Session,
    org: UUID,
    application_id: UUID,
    document_id: UUID,
    actor: User,
    expected_version: int,
    source: BinaryIO,
    storage: PrivateStorage,
    request_id: str,
) -> ApplicationDocumentResult:
    app, row, item = authorize_upload(db, org, application_id, document_id, actor, lock=True)
    lease = files.begin_upload(
        db,
        _context(row, actor),
        actor,
        item.id,
        expected_version,
        request_id,
        lease_seconds=get_settings().files_upload_lease_seconds,
    )
    files.receive_upload(db, _context(row, actor), actor, lease, source, storage, request_id)
    db.refresh(app)
    return _result(db, app, row)


def _download_ref(db: Session, app: Application, row: ApplicationDocument) -> StoredObject:
    file = db.get(FileObject, row.file_id, populate_existing=True)
    if row.removed_at or file is None:
        raise AuthError("not_found", 404)
    if (
        file.state != "clean"
        or file.retention_until <= now()
        or not file.storage_version
        or file.stored_byte_size is None
        or not file.stored_sha256
    ):
        raise AuthError("file_not_available", 409)
    if app.state != "draft":
        proof = db.scalar(
            select(ApplicationDocumentEvidence).where(
                ApplicationDocumentEvidence.document_id == row.id
            )
        )
        if (
            not proof
            or proof.storage_version != file.storage_version
            or proof.sha256 != file.stored_sha256
            or proof.byte_size != file.stored_byte_size
        ):
            raise AuthError("application_integrity_error", 503)
    return StoredObject(
        file.object_key,
        file.storage_version,
        file.expected_media_type,
        file.stored_byte_size,
        file.stored_sha256,
    )


def owner_download(
    db: Session, org: UUID, application_id: UUID, document_id: UUID, actor: User
) -> tuple[UUID, StoredObject]:
    require_files_enabled()
    app = owner_application(db, org, application_id, actor)
    row = _binding(db, app, document_id)
    return row.file_id, _download_ref(db, app, row)


def _review_application(db: Session, org: UUID, assignment_id: UUID, actor: User) -> Application:
    current = db.get(User, actor.id, populate_existing=True)
    if current is None or current.status != "active":
        raise AuthError("not_found", 404)
    require_permission(db, actor, org, "selection.review")
    assignment = db.scalar(
        select(ReviewAssignment)
        .where(
            ReviewAssignment.id == assignment_id,
            ReviewAssignment.organization_id == org,
            ReviewAssignment.reviewer_user_id == actor.id,
            ReviewAssignment.conflict_status == "clear",
            ReviewAssignment.moderation_status == "included",
        )
        .execution_options(populate_existing=True)
    )
    if assignment is None:
        raise AuthError("not_found", 404)
    cycle = db.get(SelectionCycle, assignment.selection_cycle_id, populate_existing=True)
    app = db.get(Application, assignment.application_id, populate_existing=True)
    if (
        not cycle
        or cycle.state != "active"
        or not app
        or app.state == "draft"
        or app.organization_id != org
        or app.cycle_id != cycle.application_cycle_id
    ):
        raise AuthError("not_found", 404)
    return app


def reviewer_documents(
    db: Session,
    org: UUID,
    assignment_id: UUID,
    actor: User,
    cursor: UUID | None = None,
    limit: int = 25,
) -> ApplicationDocumentList:
    return _list(db, _review_application(db, org, assignment_id, actor), cursor, limit)


def reviewer_download(
    db: Session, org: UUID, assignment_id: UUID, document_id: UUID, actor: User
) -> tuple[UUID, StoredObject]:
    require_files_enabled()
    app = _review_application(db, org, assignment_id, actor)
    row = _binding(db, app, document_id)
    return row.file_id, _download_ref(db, app, row)


def freeze_submission_documents(
    db: Session, app: Application, actor: User, request_id: str, frozen_at: datetime
) -> None:
    rules = requirements(db, app.form_id)
    rows = list(
        db.scalars(
            select(ApplicationDocument)
            .where(
                ApplicationDocument.application_id == app.id,
                ApplicationDocument.removed_at.is_(None),
            )
            .order_by(ApplicationDocument.id)
            .limit(101)
            .with_for_update()
        )
    )
    if len(rows) > 100:
        raise AuthError("application_configuration_invalid", 503)
    counts = Counter(row.requirement_id for row in rows)
    if any(not rule.min_files <= counts[rule.id] <= rule.max_files for rule in rules):
        raise AuthError("application_documents_incomplete", 422)
    rule_ids = {rule.id for rule in rules}
    if any(row.requirement_id not in rule_ids for row in rows):
        raise AuthError("application_integrity_error", 503)
    for row in rows:
        item = db.scalar(select(FileObject).where(FileObject.id == row.file_id).with_for_update())
        if item is None or item.state != "clean" or item.retention_until <= frozen_at:
            raise AuthError("application_documents_not_clean", 422)
        files.freeze_evidence(
            db, _context(row, actor), actor, item.id, item.version, request_id, commit=False
        )
        if not item.storage_version or not item.stored_sha256 or item.stored_byte_size is None:
            raise AuthError("application_integrity_error", 503)
        db.add(
            ApplicationDocumentEvidence(
                application_id=app.id,
                document_id=row.id,
                file_id=item.id,
                file_version=item.version,
                storage_version=item.storage_version,
                byte_size=item.stored_byte_size,
                sha256=item.stored_sha256,
                frozen_at=frozen_at,
            )
        )
    db.flush()
