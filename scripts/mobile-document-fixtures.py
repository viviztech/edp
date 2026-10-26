"""M02 fixtures and controlled scan evidence for the guarded mobile runner.

This adapter is test-only. It accepts only exact synthetic payloads belonging to
the current run; it is not antivirus, worker, broker or native-device evidence.
"""

import base64
import hashlib
import json
from datetime import timedelta
from pathlib import Path
from threading import Event
from uuid import UUID, uuid4

from app.modules.applications import service as applications
from app.modules.applications.document_schemas import DocumentRequirementInput
from app.modules.applications.models import ApplicationDocument
from app.modules.applications.schemas import (
    AcknowledgementInput,
    DefinitionCommand,
    DefinitionCreate,
    DefinitionFieldInput,
)
from app.modules.files import service as files
from app.modules.files.models import FileObject
from app.modules.files.runtime import get_private_storage
from app.modules.files.scanner import ScanResult
from app.modules.files.schemas import FilePolicyCommand, FilePolicyCreate
from app.modules.helpdesk.file_models import HelpdeskFile
from app.modules.identity.models import User, now
from app.modules.lms.file_models import AssignmentFile
from app.modules.programs import service as programs
from app.modules.programs.schemas import CycleCreate, NamedCreate, StateCommand
from sqlalchemy import create_engine, select
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

PAYLOADS = {
    "application/pdf": b"%PDF-1.4\nSynthetic mobile M02 evidence\n%%EOF",
    "image/png": b"\x89PNG\r\n\x1a\nSynthetic mobile M02 evidence",
    "image/jpeg": b"\xff\xd8\xffSynthetic mobile M02 evidence",
    "image/webp": b"RIFF\x20\x00\x00\x00WEBPSynthetic mobile M02 evidence",
    "text/plain": b"Synthetic mobile M02 evidence. No personal information.\n",
}


def create_domain_policy(
    db: Session, org: UUID, director: User, run_id: str, purpose: str
) -> dict:
    if purpose not in {"assignment_submission", "helpdesk_attachment"}:
        raise ValueError("Unsupported synthetic purpose")
    policy = files.create_policy(
        db,
        org,
        director,
        FilePolicyCreate(
            client_request_id=uuid4(),
            purpose=purpose,
            name=f"Synthetic mobile {purpose} {run_id}",
            notice_en="Only synthetic evidence for this isolated acceptance run.",
            notice_ta="இந்தத் தனிச் சோதனைக்கு செயற்கை ஆதாரங்கள் மட்டும்.",
            allowed_mime_types=list(PAYLOADS),
            max_file_bytes=1024,
            max_files=3,
            retention_days=1,
            rejected_retention_days=1,
            allow_frozen_disposal=False,
            reason="Synthetic mobile acceptance only",
        ),
        "mobile-domain-policy",
    )
    policy = files.publish_policy(
        db,
        org,
        policy.id,
        director,
        FilePolicyCommand(expected_version=1, reason="Synthetic acceptance only"),
        "mobile-domain-policy-publish",
    )
    return {
        "policy_id": str(policy.id),
        "purpose": purpose,
        "payloads": {
            kind: base64.b64encode(data).decode() for kind, data in PAYLOADS.items()
        },
    }


def create_intake(
    db: Session, org: UUID, director: User, applicant: User, run_id: str
) -> dict:
    policy = files.create_policy(
        db,
        org,
        director,
        FilePolicyCreate(
            client_request_id=uuid4(),
            purpose="application_document",
            name=f"Synthetic mobile document policy {run_id}",
            notice_en="Only synthetic documents for this isolated acceptance run.",
            notice_ta="இந்தத் தனிச் சோதனைக்கு செயற்கை ஆவணங்கள் மட்டும்.",
            allowed_mime_types=list(PAYLOADS),
            max_file_bytes=1024,
            max_files=5,
            retention_days=1,
            rejected_retention_days=1,
            allow_frozen_disposal=False,
            reason="Synthetic mobile acceptance only",
        ),
        "mobile-document-policy",
    )
    policy = files.publish_policy(
        db,
        org,
        policy.id,
        director,
        FilePolicyCommand(expected_version=1, reason="Synthetic acceptance approval"),
        "mobile-document-publish",
    )
    form = applications.create_definition(
        db,
        org,
        director,
        DefinitionCreate(
            title_en="Synthetic document application",
            title_ta="செயற்கை ஆவண விண்ணப்பம்",
            fields=[
                DefinitionFieldInput(
                    key="proposal",
                    section="proposal",
                    label_en="Synthetic proposal",
                    label_ta="செயற்கைத் திட்டம்",
                    field_type="text",
                    required=True,
                )
            ],
            acknowledgements=[
                AcknowledgementInput(
                    key=key,
                    kind=key,
                    label_en=f"Synthetic {key} for this isolated acceptance only.",
                    label_ta="இந்தத் தனிச் சோதனைக்கு மட்டும் செயற்கை ஒப்புதல்.",
                )
                for key in ("declaration", "consent")
            ],
            document_requirements=[
                DocumentRequirementInput(
                    key="proposal",
                    label_en="Synthetic proposal documents",
                    label_ta="செயற்கைத் திட்ட ஆவணங்கள்",
                    instructions_en="Do not provide personal or identity documents.",
                    instructions_ta="தனிப்பட்ட அல்லது அடையாள ஆவணங்களை வழங்க வேண்டாம்.",
                    file_policy_id=policy.id,
                    min_files=1,
                    max_files=5,
                )
            ],
        ),
        "mobile-document-form",
    )
    form = applications.publish_definition(
        db,
        org,
        form.id,
        director,
        DefinitionCommand(expected_revision=1),
        "mobile-document-form-publish",
    )
    program = programs.create_program(
        db,
        org,
        director,
        NamedCreate(
            code=f"mobile-documents-{run_id}",
            name_en="Synthetic document program",
            name_ta="செயற்கை ஆவண நிகழ்ச்சி",
        ),
        "mobile-document-program",
    )
    programs.transition_program(
        db,
        org,
        program.id,
        director,
        StateCommand(
            expected_version=1, target="active", reason="Synthetic acceptance"
        ),
        "mobile-document-program-active",
    )
    result = {
        "policy_id": str(policy.id),
        "form_id": str(form.id),
        "payloads": {
            media_type: base64.b64encode(payload).decode()
            for media_type, payload in PAYLOADS.items()
        },
    }
    for name in ("workflow", "lost", "bounds", "scope", "revoked"):
        cycle = programs.create_cycle(
            db,
            org,
            director,
            CycleCreate(
                code=f"mobile-documents-{run_id}-{name}",
                name_en=f"Synthetic document {name}",
                name_ta="செயற்கை ஆவணச் சோதனை",
                program_id=program.id,
                cohort_id=None,
                form_id=form.id,
                opens_at=now() - timedelta(days=1),
                closes_at=now() + timedelta(days=5),
            ),
            "mobile-document-cycle",
        )
        programs.transition_cycle(
            db,
            org,
            cycle.id,
            director,
            StateCommand(
                expected_version=1, target="open", reason="Synthetic acceptance"
            ),
            "mobile-document-cycle-open",
        )
        result[f"{name}_cycle_id"] = str(cycle.id)
    return result


class SyntheticScanner:
    def __init__(self, outcome: str) -> None:
        self.outcome = outcome

    def scan(self, source, *, max_bytes: int) -> ScanResult:
        payload = source.read(max_bytes + 1)
        if payload not in PAYLOADS.values() or len(payload) > max_bytes:
            return ScanResult("error", "", 0, "scan_unavailable")
        return ScanResult(
            self.outcome,
            hashlib.sha256(payload).hexdigest(),
            len(payload),
            "clean" if self.outcome == "clean" else "malware_detected",
        )


def observe_scans(
    target: URL,
    folder: Path,
    organization: UUID,
    applicant_user_id: UUID,
    stop: Event,
    record: dict,
    purpose: str = "application_document",
) -> None:
    """Out-of-band test control; no scan or fixture endpoint enters the API."""
    binding = {
        "application_document": ApplicationDocument,
        "assignment_submission": AssignmentFile,
        "helpdesk_attachment": HelpdeskFile,
    }.get(purpose)
    if binding is None:
        raise ValueError("Unsupported synthetic scan purpose")
    engine = create_engine(target, connect_args={"connect_timeout": 3})
    processed: set[UUID] = set()
    try:
        storage = get_private_storage()
        while not stop.is_set():
            for marker in folder.glob("scan-*.json"):
                if marker.stat().st_size > 256:
                    raise ValueError("Synthetic scan marker too large")
                data = json.loads(marker.read_text(encoding="utf-8"))
                file_id = UUID(data["file_id"])
                if marker.name != f"scan-{file_id}.json" or data["outcome"] not in {
                    "clean",
                    "infected",
                }:
                    raise ValueError("Invalid synthetic scan marker")
                if file_id in processed:
                    continue
                with Session(engine) as db:
                    applicant = db.get(User, applicant_user_id)
                    row = db.scalar(
                        select(FileObject)
                        .join(
                            binding,
                            binding.file_id == FileObject.id,
                        )
                        .where(
                            FileObject.id == file_id,
                            FileObject.organization_id == organization,
                            FileObject.owner_person_id == applicant.person_id,
                            FileObject.purpose == purpose,
                        )
                    )
                    if row is None or row.expected_sha256 not in {
                        hashlib.sha256(payload).hexdigest()
                        for payload in PAYLOADS.values()
                    }:
                        raise ValueError("Refuse unowned or nonsynthetic scan")
                    if row.state != "quarantined":
                        continue
                    lease = files.claim_scan(
                        db, organization, file_id, "mobile-synthetic-scan"
                    )
                    files.scan_with_lease(
                        db,
                        organization,
                        lease,
                        storage,
                        SyntheticScanner(data["outcome"]),
                        "mobile-synthetic-scan-finish",
                    )
                    processed.add(file_id)
                marker.unlink()
            stop.wait(0.1)
        record["synthetic_scans_completed"] = len(processed)
    except Exception:  # noqa: BLE001 - no payload, path or connection diagnostics
        record["scan_observer_failed"] = True
    finally:
        engine.dispose()
