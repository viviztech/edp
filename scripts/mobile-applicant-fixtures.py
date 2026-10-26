"""Synthetic M01 fixtures, called only inside the guarded mobile runner."""

from datetime import timedelta
from uuid import UUID

from app.modules.applications import service as applications
from app.modules.applications.schemas import (
    AcknowledgementInput,
    DefinitionCommand,
    DefinitionCreate,
    DefinitionFieldInput,
)
from app.modules.identity.models import User, now
from app.modules.programs import service as programs
from app.modules.programs.schemas import CycleCreate, NamedCreate, StateCommand
from sqlalchemy.orm import Session


def create_intake(
    db: Session, org: UUID, director: User, applicant: User, run_id: str
) -> dict[str, str]:
    form = applications.create_definition(
        db,
        org,
        director,
        DefinitionCreate(
            title_en="Synthetic enterprise application",
            title_ta="சோதனை தொழில் விண்ணப்பம்",
            fields=[
                DefinitionFieldInput(
                    key=key,
                    section="proposal",
                    label_en=label,
                    label_ta=tamil,
                    field_type=kind,
                    required=required,
                )
                for key, label, tamil, kind, required in (
                    ("name", "Business name", "தொழில் பெயர்", "text", True),
                    ("idea", "Business idea", "தொழில் திட்டம்", "textarea", True),
                    ("size", "Team size", "குழு அளவு", "number", False),
                    ("date", "Start date", "தொடக்க நாள்", "date", False),
                    ("ready", "Ready to begin", "தொடங்கத் தயார்", "boolean", False),
                )
            ],
            acknowledgements=[
                AcknowledgementInput(
                    key="declaration",
                    kind="declaration",
                    label_en="Synthetic declaration: these test answers are accurate.",
                    label_ta="சோதனை உறுதி: இந்தப் பதில்கள் சரியானவை.",
                ),
                AcknowledgementInput(
                    key="consent",
                    kind="consent",
                    label_en="Synthetic consent for this isolated acceptance run only.",
                    label_ta="இந்தத் தனிமைப்படுத்தப்பட்ட சோதனைக்கு மட்டும் ஒப்புதல்.",
                ),
            ],
        ),
        "mobile-form-create",
    )
    form = applications.publish_definition(
        db,
        org,
        form.id,
        director,
        DefinitionCommand(expected_revision=1),
        "mobile-form-publish",
    )
    program = programs.create_program(
        db,
        org,
        director,
        NamedCreate(
            code=f"mobile-{run_id}", name_en="Synthetic mobile", name_ta="சோதனை"
        ),
        "mobile-program",
    )
    program = programs.transition_program(
        db,
        org,
        program.id,
        director,
        StateCommand(
            expected_version=1, target="active", reason="Synthetic acceptance only"
        ),
        "mobile-program-active",
    )
    result = {"form_id": str(form.id)}
    for name in (
        "open",
        "second",
        "lost",
        "closed",
        *(f"history-{i}" for i in range(26)),
    ):
        current = now()
        cycle = programs.create_cycle(
            db,
            org,
            director,
            CycleCreate(
                code=f"mobile-{run_id}-{name}",
                name_en=f"Synthetic {name} intake",
                name_ta=f"சோதனை {name}",
                program_id=program.id,
                cohort_id=None,
                form_id=form.id,
                opens_at=current - timedelta(days=1),
                closes_at=current + timedelta(days=5),
            ),
            "mobile-cycle-create",
        )
        cycle = programs.transition_cycle(
            db,
            org,
            cycle.id,
            director,
            StateCommand(
                expected_version=1, target="open", reason="Synthetic acceptance only"
            ),
            "mobile-cycle-open",
        )
        if not name.startswith("history-"):
            result[f"{name}_cycle_id"] = str(cycle.id)
        if name == "closed" or name.startswith("history-"):
            draft = applications.create_cycle_draft(
                db, org, cycle.id, applicant, "mobile-closed-draft"
            )
            if name == "closed":
                result["closed_application_id"] = str(draft.id)
            programs.transition_cycle(
                db,
                org,
                cycle.id,
                director,
                StateCommand(
                    expected_version=2, target="closed", reason="Synthetic closure"
                ),
                "mobile-cycle-close",
            )
    return result
