"""Synthetic prerequisites followed by the real enrollment conversion transaction."""

from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.applications.models import Application, ApplicationForm
from app.modules.identity.models import User, now
from app.modules.programs import service
from app.modules.programs.models import ApplicationCycle, Cohort, Program, TrainingCenter
from app.modules.programs.schemas import EnrollmentConversionView, EnrollmentConvert
from app.modules.selection.models import SelectionCycle


def create_enrollment(
    db: Session, org: UUID, director: User, learner: User, suffix: str
) -> EnrollmentConversionView:
    """Seed synthetic selected intake; invoke the production conversion service.

    Caller supplies active accounts and a director with enrollment.manage in org.
    No outbox/participant/enrollment is fabricated, and no provider is contacted.
    """
    stamp = now()
    form = ApplicationForm(
        organization_id=org,
        version=int(
            db.scalar(
                select(func.max(ApplicationForm.version)).where(
                    ApplicationForm.organization_id == org
                )
            )
            or 0
        )
        + 1,
        state="published",
        title_en="Synthetic enrollment intake",
        title_ta="Synthetic Tamil intake",
        published_at=stamp,
        published_by_id=director.id,
    )
    program = Program(
        organization_id=org,
        code=f"notice-{suffix}",
        name_en="Synthetic participant program",
        name_ta="Synthetic Tamil program",
        state="active",
    )
    center = TrainingCenter(
        organization_id=org,
        code=f"notice-{suffix}",
        name_en="Synthetic center",
        name_ta="Synthetic Tamil center",
        locality="Synthetic locality",
    )
    db.add_all([form, program, center])
    db.flush()
    cohort = Cohort(
        organization_id=org,
        program_id=program.id,
        center_id=center.id,
        code=f"notice-{suffix}",
        name_en="Synthetic participant cohort",
        name_ta="Synthetic Tamil cohort",
        starts_on=stamp.date(),
        ends_on=(stamp + timedelta(days=60)).date(),
        state="active",
    )
    db.add(cohort)
    db.flush()
    cycle = ApplicationCycle(
        organization_id=org,
        program_id=program.id,
        cohort_id=cohort.id,
        form_id=form.id,
        code=f"notice-{suffix}",
        name_en="Synthetic intake",
        name_ta="Synthetic Tamil intake",
        opens_at=stamp - timedelta(days=30),
        closes_at=stamp - timedelta(days=1),
        state="closed",
    )
    db.add(cycle)
    db.flush()
    selection = SelectionCycle(
        organization_id=org,
        application_cycle_id=cycle.id,
        code=f"notice-{suffix}",
        name_en="Synthetic finalized selection",
        name_ta="Synthetic Tamil selection",
        state="closed",
    )
    application = Application(
        organization_id=org,
        person_id=learner.person_id,
        form_id=form.id,
        cycle_id=cycle.id,
        state="selected",
        application_number=f"EDP-NOTICE-{uuid4().hex[:12]}",
        submitted_at=stamp - timedelta(days=20),
    )
    db.add_all([selection, application])
    db.commit()
    return service.convert_enrollment(
        db,
        org,
        director,
        EnrollmentConvert(
            application_id=application.id,
            expected_application_version=application.version,
            reason="Synthetic finalized selection approved for enrollment",
        ),
        f"synthetic-notice-enrollment:{suffix}",
    )
