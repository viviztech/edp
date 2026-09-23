import os

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_identity import auth, signed_in  # noqa: F401

from app.modules.applications import service
from app.modules.applications.models import ApplicationField, ApplicationForm
from app.modules.applications.schemas import (
    AcknowledgementInput,
    DefinitionCommand,
    DefinitionCreate,
    DefinitionFieldInput,
    DefinitionUpdate,
)
from app.modules.identity.models import (
    AuditLog,
    Organization,
    Person,
    Role,
    User,
    UserRole,
)
from app.modules.identity.security import AuthError, hasher

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)


def content(title: str = "Enterprise application") -> DefinitionCreate:
    return DefinitionCreate(
        title_en=title,
        title_ta="Synthetic Tamil title",
        fields=[
            DefinitionFieldInput(
                key="business_idea",
                section="proposal",
                label_en="Business idea",
                label_ta="Synthetic Tamil label",
                field_type="textarea",
                required=True,
            )
        ],
        acknowledgements=[
            AcknowledgementInput(
                key="final_declaration",
                kind="declaration",
                label_en="I declare this application is accurate",
                label_ta="Synthetic Tamil declaration",
            ),
            AcknowledgementInput(
                key="privacy_consent",
                kind="consent",
                label_en="I consent to application processing",
                label_ta="Synthetic Tamil consent",
            ),
        ],
    )


@pytest.fixture
def definition_db(request):
    _, engine, _, _ = request.getfixturevalue("auth")
    with Session(engine) as db:
        org = Organization(name="Definition organization")
        people = [
            Person(display_name="Manager"),
            Person(display_name="Director"),
            Person(display_name="Applicant one"),
            Person(display_name="Applicant two"),
        ]
        db.add_all([org, *people])
        db.flush()
        users = [
            User(
                person_id=person.id,
                email=f"definition-{index}@example.test",
                password_hash=hasher.hash("Synthetic password 123"),
                status="active",
            )
            for index, person in enumerate(people)
        ]
        db.add_all(users)
        db.flush()
        manager = db.scalar(select(Role).where(Role.name == "Program Manager"))
        director = db.scalar(select(Role).where(Role.name == "Program Director"))
        assert manager and director
        db.add_all(
            [
                UserRole(user_id=users[0].id, role_id=manager.id, organization_id=org.id),
                UserRole(user_id=users[1].id, role_id=director.id, organization_id=org.id),
            ]
        )
        db.commit()
        yield engine, org.id, [item.id for item in users]


def test_definition_authoring_permissions_versioning_and_immutability(definition_db) -> None:
    engine, org, user_ids = definition_db
    with Session(engine) as db:
        manager = db.get(User, user_ids[0])
        director = db.get(User, user_ids[1])
        assert manager and director
        created = service.create_definition(db, org, manager, content(), "create")
        assert created.state == "draft"
        assert created.version == 1 and created.revision == 1
        updated = service.update_definition(
            db,
            org,
            created.id,
            manager,
            DefinitionUpdate(
                expected_revision=1,
                title_en="Enterprise application 2027",
                title_ta="Synthetic Tamil title",
                acknowledgements=content().acknowledgements,
                fields=[
                    *content().fields,
                    DefinitionFieldInput(
                        key="experience",
                        section="background",
                        label_en="Relevant experience",
                        label_ta="Synthetic Tamil experience",
                        field_type="text",
                    ),
                ],
            ),
            "update",
        )
        assert updated.revision == 2 and len(updated.fields) == 2
        with pytest.raises(AuthError) as stale:
            service.update_definition(
                db,
                org,
                created.id,
                manager,
                DefinitionUpdate(
                    expected_revision=1,
                    title_en="Stale",
                    title_ta="Synthetic Tamil",
                    fields=content().fields,
                    acknowledgements=content().acknowledgements,
                ),
                "stale",
            )
        assert stale.value.status == 409
        with pytest.raises(AuthError) as forbidden:
            service.publish_definition(
                db,
                org,
                created.id,
                manager,
                DefinitionCommand(expected_revision=2),
                "manager-publish",
            )
        assert forbidden.value.status == 403
        published = service.publish_definition(
            db,
            org,
            created.id,
            director,
            DefinitionCommand(expected_revision=2),
            "publish",
        )
        assert published.state == "published" and published.revision == 3
        assert published.published_at is not None
        with pytest.raises(AuthError) as immutable:
            service.update_definition(
                db,
                org,
                created.id,
                manager,
                DefinitionUpdate(
                    expected_revision=3,
                    title_en="Changed",
                    title_ta="Synthetic Tamil",
                    fields=content().fields,
                    acknowledgements=content().acknowledgements,
                ),
                "immutable",
            )
        assert immutable.value.status == 409

        field = db.scalar(
            select(ApplicationField).where(ApplicationField.form_id == created.id).limit(1)
        )
        assert field
        field.label_en = "Database bypass"
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()

        copied = service.copy_definition(
            db,
            org,
            created.id,
            manager,
            DefinitionCommand(expected_revision=3),
            "copy",
        )
        assert copied.state == "draft" and copied.version == 2
        with pytest.raises(AuthError) as duplicate:
            service.create_definition(db, org, manager, content("Another"), "duplicate")
        assert duplicate.value.status == 409
        assert len(service.list_definitions(db, org, manager).items) == 2
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.action.like("application.definition_%"))
            )
            == 4
        )


def test_publish_retires_previous_policy_and_keeps_applicant_draft_pinned(definition_db) -> None:
    engine, org, user_ids = definition_db
    with Session(engine) as db:
        manager = db.get(User, user_ids[0])
        director = db.get(User, user_ids[1])
        first_applicant = db.get(User, user_ids[2])
        second_applicant = db.get(User, user_ids[3])
        assert manager and director and first_applicant and second_applicant

        first = service.create_definition(db, org, manager, content("Version one"), "create-v1")
        first = service.publish_definition(
            db,
            org,
            first.id,
            director,
            DefinitionCommand(expected_revision=1),
            "publish-v1",
        )
        applicant_draft = service.create_draft(db, org, first_applicant, "applicant-v1")
        assert applicant_draft.form.version == 1

        second = service.copy_definition(
            db,
            org,
            first.id,
            manager,
            DefinitionCommand(expected_revision=2),
            "copy-v2",
        )
        second = service.publish_definition(
            db,
            org,
            second.id,
            director,
            DefinitionCommand(expected_revision=1),
            "publish-v2",
        )
        assert second.version == 2 and second.state == "published"
        old = db.get(ApplicationForm, first.id)
        assert old and old.state == "retired"
        assert service.mine(db, org, first_applicant).form.version == 1
        assert service.create_draft(db, org, second_applicant, "applicant-v2").form.version == 2


def test_definition_routes_apply_scoped_role_permissions(request) -> None:
    auth_context = request.getfixturevalue("auth")
    client, engine, _, _ = auth_context
    credentials, _, headers = signed_in(auth_context)
    with Session(engine) as db:
        user = db.scalar(select(User).where(User.email == credentials["email"]))
        manager = db.scalar(select(Role).where(Role.name == "Program Manager"))
        director = db.scalar(select(Role).where(Role.name == "Program Director"))
        assert user and manager and director
        org = Organization(name="Route definition organization")
        db.add(org)
        db.flush()
        db.add(UserRole(user_id=user.id, role_id=manager.id, organization_id=org.id))
        db.commit()
        org_id = org.id
        director_id = director.id
        user_id = user.id

    root = f"/api/v1/applications/organizations/{org_id}/definitions"
    created = client.post(root, headers=headers, json=content().model_dump())
    assert created.status_code == 201
    definition = created.json()
    assert client.get(root, headers=headers).status_code == 200
    assert (
        client.post(
            f"{root}/{definition['id']}/publish",
            headers=headers,
            json={"expected_revision": 1},
        ).status_code
        == 403
    )
    with Session(engine) as db:
        db.add(UserRole(user_id=user_id, role_id=director_id, organization_id=org_id))
        db.commit()
    published = client.post(
        f"{root}/{definition['id']}/publish",
        headers=headers,
        json={"expected_revision": 1},
    )
    assert published.status_code == 200
    assert published.json()["state"] == "published"
