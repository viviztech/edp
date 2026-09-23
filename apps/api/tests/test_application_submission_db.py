import os
from datetime import timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_identity import auth, signed_in  # noqa: F401

from app.modules.applications import service
from app.modules.applications.models import (
    ApplicationAcknowledgement,
    ApplicationAnswer,
    ApplicationStatusHistory,
)
from app.modules.applications.schemas import (
    AcknowledgementInput,
    AnswerInput,
    DefinitionCommand,
    DefinitionCreate,
    DefinitionFieldInput,
    DraftSave,
    SubmitCommand,
)
from app.modules.identity.models import AuditLog, Organization, Person, Role, User, UserRole, now
from app.modules.identity.security import AuthError, hasher
from app.modules.programs import service as program_service
from app.modules.programs.schemas import CycleCreate, NamedCreate, StateCommand

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)


def policy() -> DefinitionCreate:
    return DefinitionCreate(
        title_en="Enterprise application",
        title_ta="Synthetic Tamil application",
        fields=[
            DefinitionFieldInput(
                key="business_idea",
                section="proposal",
                label_en="Business idea",
                label_ta="Synthetic Tamil business idea",
                field_type="textarea",
                required=True,
            )
        ],
        acknowledgements=[
            AcknowledgementInput(
                key="final_declaration",
                kind="declaration",
                label_en="I declare that this application is accurate.",
                label_ta="Synthetic Tamil declaration",
            ),
            AcknowledgementInput(
                key="application_consent",
                kind="consent",
                label_en="I consent to processing for this application.",
                label_ta="Synthetic Tamil consent",
            ),
        ],
    )


@pytest.fixture
def submission_db(request):
    _, engine, _, _ = request.getfixturevalue("auth")
    with Session(engine) as db:
        org = Organization(name="Submission organization")
        people = [
            Person(display_name="Director"),
            Person(display_name="Applicant"),
            Person(display_name="Other"),
        ]
        db.add_all([org, *people])
        db.flush()
        users = [
            User(
                person_id=person.id,
                email=f"submission-{index}@example.test",
                password_hash=hasher.hash("Synthetic password 123"),
                status="active",
            )
            for index, person in enumerate(people)
        ]
        db.add_all(users)
        db.flush()
        role = db.scalar(select(Role).where(Role.name == "Program Director"))
        assert role
        db.add(UserRole(user_id=users[0].id, role_id=role.id, organization_id=org.id))
        db.commit()
        director, applicant, other = (db.get(User, item.id) for item in users)
        assert director and applicant and other
        form = service.create_definition(db, org.id, director, policy(), "policy-create")
        form = service.publish_definition(
            db,
            org.id,
            form.id,
            director,
            DefinitionCommand(expected_revision=1),
            "policy-publish",
        )
        program = program_service.create_program(
            db,
            org.id,
            director,
            NamedCreate(code="enterprise", name_en="Enterprise", name_ta="Tamil"),
            "program-create",
        )
        program = program_service.transition_program(
            db,
            org.id,
            program.id,
            director,
            StateCommand(expected_version=1, target="active", reason="Approved intake"),
            "program-open",
        )
        current = now()
        cycle = program_service.create_cycle(
            db,
            org.id,
            director,
            CycleCreate(
                code="enterprise-intake",
                name_en="Enterprise intake",
                name_ta="Synthetic Tamil intake",
                program_id=program.id,
                cohort_id=None,
                form_id=form.id,
                opens_at=current - timedelta(days=1),
                closes_at=current + timedelta(days=10),
            ),
            "cycle-create",
        )
        cycle = program_service.transition_cycle(
            db,
            org.id,
            cycle.id,
            director,
            StateCommand(expected_version=1, target="open", reason="Applications approved"),
            "cycle-open",
        )
        yield engine, org.id, applicant.id, other.id, cycle.id, form


def test_submission_validates_and_freezes_evidence(submission_db) -> None:
    engine, org, applicant_id, other_id, cycle_id, form = submission_db
    with Session(engine) as db:
        applicant, other = db.get(User, applicant_id), db.get(User, other_id)
        assert applicant and other
        assert service.available_cycles(db, org).items[0].id == cycle_id
        draft = service.create_cycle_draft(db, org, cycle_id, applicant, "draft")
        acknowledgement_ids = [item.id for item in draft.form.acknowledgements]
        with pytest.raises(AuthError) as incomplete:
            service.submit(
                db,
                org,
                draft.id,
                applicant,
                SubmitCommand(
                    expected_version=1,
                    accepted_acknowledgement_ids=acknowledgement_ids,
                ),
                "incomplete",
            )
        assert incomplete.value.status == 422
        saved = service.save(
            db,
            org,
            draft.id,
            applicant,
            DraftSave(
                expected_version=1,
                answers=[
                    AnswerInput(
                        field_id=form.fields[0].id,
                        value="Community enterprise",
                    )
                ],
            ),
            "save",
        )
        with pytest.raises(AuthError) as consent:
            service.submit(
                db,
                org,
                draft.id,
                applicant,
                SubmitCommand(
                    expected_version=saved.version,
                    accepted_acknowledgement_ids=[acknowledgement_ids[0]],
                ),
                "missing-consent",
            )
        assert consent.value.status == 422
        submitted = service.submit(
            db,
            org,
            draft.id,
            applicant,
            SubmitCommand(
                expected_version=saved.version,
                accepted_acknowledgement_ids=acknowledgement_ids,
            ),
            "submit",
        )
        assert submitted.state == "submitted"
        assert submitted.application_number.startswith(f"EDP-{now().year}-")
        assert submitted.status_history[-1].to_state == "submitted"
        assert len(submitted.accepted_acknowledgements) == 2
        retried = service.submit(
            db,
            org,
            draft.id,
            applicant,
            SubmitCommand(
                expected_version=saved.version,
                accepted_acknowledgement_ids=acknowledgement_ids,
            ),
            "retry",
        )
        assert retried.application_number == submitted.application_number
        with pytest.raises(AuthError) as hidden:
            service.cycle_application(db, org, cycle_id, other)
        assert hidden.value.status == 404
        assert db.scalar(select(func.count()).select_from(ApplicationStatusHistory)) == 2
        assert db.scalar(select(func.count()).select_from(ApplicationAcknowledgement)) == 2
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.action == "application.submitted")
            )
            == 1
        )
        answer = db.scalar(select(ApplicationAnswer))
        assert answer
        answer.value = "Database bypass"
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()
        history = db.scalar(
            select(ApplicationStatusHistory).where(ApplicationStatusHistory.to_state == "submitted")
        )
        assert history
        history.reason_code = "database_bypass"
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()


def test_submission_routes_return_stable_receipt(request, submission_db) -> None:
    auth_context = request.getfixturevalue("auth")
    client, engine, _, _ = auth_context
    _, _, headers = signed_in(auth_context)
    _, org, _, _, cycle_id, form = submission_db
    with Session(engine) as db:
        signed_user = db.scalar(select(User).where(User.email == "learner@example.com"))
        assert signed_user
    root = f"/api/v1/applications/organizations/{org}"
    assert client.get(root + "/cycles", headers=headers).status_code == 200
    created = client.post(root + f"/cycles/{cycle_id}/draft", headers=headers, json={})
    assert created.status_code == 201
    draft = created.json()
    saved = client.patch(
        root + f"/draft/{draft['id']}",
        headers=headers,
        json={
            "expected_version": 1,
            "answers": [{"field_id": str(form.fields[0].id), "value": "A viable idea"}],
        },
    )
    assert saved.status_code == 200
    submitted = client.post(
        root + f"/draft/{draft['id']}/submit",
        headers=headers,
        json={
            "expected_version": 2,
            "accepted_acknowledgement_ids": [
                item["id"] for item in draft["form"]["acknowledgements"]
            ],
        },
    )
    assert submitted.status_code == 200
    receipt = submitted.json()
    assert receipt["state"] == "submitted" and receipt["application_number"]
    current = client.get(root + f"/cycles/{cycle_id}/application", headers=headers)
    assert current.status_code == 200
    assert current.json()["application_number"] == receipt["application_number"]
