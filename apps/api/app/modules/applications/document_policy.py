"""Immutable document rules pinned to a published application form edition."""

from collections import defaultdict
from typing import cast
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.applications.document_schemas import (
    DocumentFilePolicyView,
    DocumentRequirementInput,
    DocumentRequirementView,
)
from app.modules.applications.models import ApplicationForm, DocumentRequirement
from app.modules.files.models import FilePolicy
from app.modules.files.schemas import MediaType
from app.modules.identity.models import User
from app.modules.identity.security import AuthError
from app.modules.identity.service import require_permission


def requirements(db: Session, form_id: UUID) -> list[DocumentRequirement]:
    rows = list(
        db.scalars(
            select(DocumentRequirement)
            .where(DocumentRequirement.form_id == form_id)
            .order_by(DocumentRequirement.position)
            .limit(21)
        )
    )
    if len(rows) > 20:
        raise AuthError("application_configuration_invalid", 503)
    return rows


def requirement_input(row: DocumentRequirement) -> DocumentRequirementInput:
    return DocumentRequirementInput(
        key=row.requirement_key,
        label_en=row.label_en,
        label_ta=row.label_ta,
        instructions_en=row.instructions_en,
        instructions_ta=row.instructions_ta,
        file_policy_id=row.file_policy_id,
        min_files=row.min_files,
        max_files=row.max_files,
    )


def validate_requirements(
    db: Session, org: UUID, actor: User, rows: list[DocumentRequirementInput]
) -> None:
    if not rows:
        return
    require_permission(db, actor, org, "files.policy.view")
    minimums: dict[UUID, int] = defaultdict(int)
    for rule in rows:
        policy = db.scalar(
            select(FilePolicy)
            .where(
                FilePolicy.id == rule.file_policy_id,
                FilePolicy.organization_id == org,
                FilePolicy.purpose == "application_document",
            )
            .with_for_update(read=True)
        )
        if not policy or policy.state != "published" or not policy.published_at:
            raise AuthError("file_policy_unavailable", 409)
        minimums[policy.id] += rule.min_files
        if rule.max_files > policy.max_files or minimums[policy.id] > policy.max_files:
            raise AuthError("document_configuration_invalid", 422)


def replace_requirements(
    db: Session, form: ApplicationForm, rows: list[DocumentRequirementInput]
) -> None:
    db.execute(delete(DocumentRequirement).where(DocumentRequirement.form_id == form.id))
    db.add_all(
        [
            DocumentRequirement(
                organization_id=form.organization_id,
                form_id=form.id,
                requirement_key=row.key,
                label_en=row.label_en,
                label_ta=row.label_ta,
                instructions_en=row.instructions_en,
                instructions_ta=row.instructions_ta,
                file_policy_id=row.file_policy_id,
                min_files=row.min_files,
                max_files=row.max_files,
                position=position,
            )
            for position, row in enumerate(rows, start=1)
        ]
    )


def requirement_views(db: Session, form_id: UUID) -> list[DocumentRequirementView]:
    result = []
    settings = get_settings()
    for row in requirements(db, form_id):
        policy = db.get(FilePolicy, row.file_policy_id)
        if not policy or policy.organization_id != row.organization_id:
            raise AuthError("application_configuration_invalid", 503)
        result.append(
            DocumentRequirementView(
                **requirement_input(row).model_dump(),
                id=row.id,
                position=row.position,
                file_policy=DocumentFilePolicyView(
                    id=policy.id,
                    edition=policy.edition,
                    name=policy.name,
                    allowed_mime_types=cast(list[MediaType], policy.allowed_mime_types),
                    max_file_bytes=policy.max_file_bytes,
                    max_upload_bytes=min(policy.max_file_bytes, settings.files_max_bytes),
                    max_files=policy.max_files,
                    retention_days=policy.retention_days,
                    rejected_retention_days=policy.rejected_retention_days,
                    notice_en=policy.notice_en,
                    notice_ta=policy.notice_ta,
                    allow_frozen_disposal=policy.allow_frozen_disposal,
                ),
            )
        )
    return result
