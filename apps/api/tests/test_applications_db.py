import os

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_identity import auth  # noqa: F401

from app.modules.applications import service
from app.modules.applications.models import (
    Application,
    ApplicationAnswer,
    ApplicationField,
    ApplicationForm,
    ApplicationRevision,
)
from app.modules.applications.schemas import AnswerInput, DraftSave
from app.modules.identity.models import AuditLog, Organization, Person, User, now
from app.modules.identity.security import AuthError, hasher

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)


@pytest.fixture
def application_db(request):
    _, engine, _, _ = request.getfixturevalue("auth")
    with Session(engine) as db:
        org = Organization(name="Application test organization")
        people = [Person(display_name="Applicant one"), Person(display_name="Applicant two")]
        db.add_all([org, *people])
        db.flush()
        users = [
            User(
                person_id=person.id,
                email=f"applicant-{index}@example.test",
                password_hash=hasher.hash("Synthetic password 123"),
                status="active",
            )
            for index, person in enumerate(people)
        ]
        form = ApplicationForm(
            organization_id=org.id,
            version=1,
            state="draft",
            title_en="Development application",
            title_ta="Development application",
            published_at=now(),
        )
        db.add_all([*users, form])
        db.flush()
        fields = [
            ApplicationField(
                form_id=form.id,
                field_key="business_idea",
                section_key="proposal",
                label_en="Business idea",
                label_ta="Business idea",
                field_type="textarea",
                required=True,
                position=1,
            ),
            ApplicationField(
                form_id=form.id,
                field_key="funding",
                section_key="proposal",
                label_en="Funding requirement",
                label_ta="Funding requirement",
                field_type="number",
                required=False,
                position=2,
            ),
        ]
        db.add_all(fields)
        db.flush()
        form.state = "published"
        form.published_at = now()
        db.commit()
        yield engine, org.id, users[0].id, users[1].id, fields[0].id, fields[1].id


def test_owned_draft_autosave_creates_immutable_revisions(application_db) -> None:
    engine, org, first_id, second_id, required_id, number_id = application_db
    with Session(engine) as db:
        first = db.get(User, first_id)
        second = db.get(User, second_id)
        assert first and second
        created = service.create_draft(db, org, first, "request")
        assert created.version == 1 and created.revision == 1
        assert created.completion_percent == 0 and created.answers == []
        assert service.create_draft(db, org, first, "request").id == created.id
        saved = service.save(
            db,
            org,
            created.id,
            first,
            DraftSave(
                expected_version=1,
                answers=[
                    AnswerInput(field_id=required_id, value="Community tailoring service"),
                    AnswerInput(field_id=number_id, value="25000"),
                ],
            ),
            "request",
        )
        assert saved.version == 2 and saved.revision == 2
        assert saved.completion_percent == 100
        assert len(saved.answers) == 2
        assert db.scalar(select(func.count()).select_from(ApplicationRevision)) == 2
        assert db.scalar(select(func.count()).select_from(ApplicationAnswer)) == 2
        with pytest.raises(AuthError) as stale:
            service.save(
                db,
                org,
                created.id,
                first,
                DraftSave(expected_version=1, answers=[]),
                "request",
            )
        assert stale.value.status == 409
        with pytest.raises(AuthError) as hidden:
            service.save(
                db,
                org,
                created.id,
                second,
                DraftSave(expected_version=2, answers=[]),
                "request",
            )
        assert hidden.value.status == 404
        assert service.mine(db, org, first).revision == 2
        with pytest.raises(AuthError) as not_owned:
            service.mine(db, org, second)
        assert not_owned.value.status == 404
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(
                    AuditLog.resource_id == created.id,
                    AuditLog.action.in_(("application.draft_created", "application.draft_saved")),
                )
            )
            == 2
        )


def test_form_scope_and_typed_answer_validation(application_db) -> None:
    engine, org, first_id, _, _, number_id = application_db
    with Session(engine) as db:
        first = db.get(User, first_id)
        assert first is not None
        with pytest.raises(AuthError) as unavailable:
            service.get_form(db, Organization().id)
        assert unavailable.value.status == 404
        draft = service.create_draft(db, org, first, "request")
        with pytest.raises(AuthError) as invalid:
            service.save(
                db,
                org,
                draft.id,
                first,
                DraftSave(
                    expected_version=1,
                    answers=[AnswerInput(field_id=number_id, value="not a number")],
                ),
                "request",
            )
        assert invalid.value.status == 422
        db.rollback()
        row = db.get(Application, draft.id)
        assert row is not None and row.version == 1
        assert db.scalar(select(func.count()).select_from(ApplicationRevision)) == 1
