import os
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_identity import auth, signed_in  # noqa: F401

from app.modules.applications import service as application_service
from app.modules.applications.schemas import (
    AcknowledgementInput,
    DefinitionCommand,
    DefinitionCreate,
    DefinitionFieldInput,
)
from app.modules.identity.models import AuditLog, Organization, Person, Role, User, UserRole
from app.modules.identity.security import AuthError, hasher
from app.modules.programs import service
from app.modules.programs.models import ProgramStaffAssignment
from app.modules.programs.schemas import (
    CenterCreate,
    CohortCreate,
    CycleCreate,
    NamedCreate,
    SessionCreate,
    StaffAssignmentCreate,
    StaffAssignmentRevoke,
    StateCommand,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)


@pytest.fixture
def program_db(request):
    _, engine, _, _ = request.getfixturevalue("auth")
    with Session(engine) as db:
        org, other, person = (
            Organization(name="Program organization"),
            Organization(name="Other organization"),
            Person(display_name="Program manager"),
        )
        db.add_all([org, other, person])
        db.flush()
        user = User(
            person_id=person.id,
            email="program-manager@example.test",
            password_hash=hasher.hash("Synthetic password 123"),
            status="active",
        )
        db.add(user)
        db.flush()
        role = db.scalar(select(Role).where(Role.name == "Program Director"))
        assert role
        db.add(UserRole(user_id=user.id, role_id=role.id, organization_id=org.id))
        db.commit()
        yield engine, org.id, other.id, user.id


def definition() -> DefinitionCreate:
    return DefinitionCreate(
        title_en="Enterprise intake",
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
                label_en="I declare this is accurate.",
                label_ta="Synthetic Tamil declaration",
            ),
            AcknowledgementInput(
                key="application_consent",
                kind="consent",
                label_en="I consent to application processing.",
                label_ta="Synthetic Tamil consent",
            ),
        ],
    )


def test_program_delivery_lifecycle_scope_version_and_audit(program_db) -> None:
    engine, org, other, user_id = program_db
    with Session(engine) as db:
        actor = db.get(User, user_id)
        assert actor
        program = service.create_program(
            db,
            org,
            actor,
            NamedCreate(code="enterprise", name_en="Enterprise", name_ta="Tamil"),
            "p-create",
        )
        program = service.transition_program(
            db,
            org,
            program.id,
            actor,
            StateCommand(expected_version=1, target="active", reason="Approved delivery plan"),
            "p-active",
        )
        center = service.create_center(
            db,
            org,
            actor,
            CenterCreate(code="chennai", name_en="Chennai", name_ta="Tamil", locality="Guindy"),
            "c-create",
        )
        cohort = service.create_cohort(
            db,
            org,
            actor,
            CohortCreate(
                code="batch-01",
                name_en="Batch 01",
                name_ta="Tamil",
                program_id=program.id,
                center_id=center.id,
                starts_on=date(2027, 1, 1),
                ends_on=date(2027, 3, 1),
                capacity=25,
            ),
            "b-create",
        )
        with pytest.raises(AuthError) as stale:
            service.transition_cohort(
                db,
                org,
                cohort.id,
                actor,
                StateCommand(expected_version=2, target="active", reason="Stale request"),
                "stale",
            )
        assert stale.value.status == 409
        cohort = service.transition_cohort(
            db,
            org,
            cohort.id,
            actor,
            StateCommand(expected_version=1, target="active", reason="Staffing confirmed"),
            "b-active",
        )
        form = application_service.create_definition(db, org, actor, definition(), "form-create")
        form = application_service.publish_definition(
            db, org, form.id, actor, DefinitionCommand(expected_revision=1), "form-publish"
        )
        opens = datetime(2027, 1, 1, tzinfo=UTC)
        cycle = service.create_cycle(
            db,
            org,
            actor,
            CycleCreate(
                code="enterprise-2027",
                name_en="Enterprise 2027",
                name_ta="Tamil",
                program_id=program.id,
                cohort_id=cohort.id,
                form_id=form.id,
                opens_at=opens,
                closes_at=opens + timedelta(days=30),
            ),
            "cycle-create",
        )
        cycle = service.transition_cycle(
            db,
            org,
            cycle.id,
            actor,
            StateCommand(expected_version=1, target="open", reason="Applications approved"),
            "cycle-open",
        )
        assert cycle.state == "open" and len(service.catalog(db, org, actor).cohorts) == 1
        with pytest.raises(AuthError) as scoped:
            service.catalog(db, other, actor)
        assert scoped.value.status == 403
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.action.like("%state_changed"))
            )
            == 3
        )


def test_program_routes_require_scoped_permission_and_expose_catalog(request) -> None:
    auth_context = request.getfixturevalue("auth")
    client, engine, _, _ = auth_context
    _, _, headers = signed_in(auth_context)
    with Session(engine) as db:
        user = db.scalar(select(User).where(User.email == "learner@example.com"))
        role = db.scalar(select(Role).where(Role.name == "Program Manager"))
        org = Organization(name="Route program organization")
        assert user and role
        db.add(org)
        db.flush()
        db.add(UserRole(user_id=user.id, role_id=role.id, organization_id=org.id))
        db.commit()
        org_id = org.id
    root = f"/api/v1/programs/organizations/{org_id}"
    created = client.post(
        root + "/programs",
        headers=headers,
        json={"code": "enterprise", "name_en": "Enterprise", "name_ta": "Tamil"},
    )
    assert created.status_code == 201
    program = created.json()
    assert (
        client.get(root + "/catalog", headers=headers).json()["programs"][0]["id"] == program["id"]
    )
    activated = client.post(
        root + f"/programs/{program['id']}/state",
        headers=headers,
        json={"expected_version": 1, "target": "active", "reason": "Approved plan"},
    )
    assert activated.status_code == 200 and activated.json()["state"] == "active"


def test_scoped_program_staff_assignment_authorization_and_immutability(program_db) -> None:
    engine, org, _, director_id = program_db
    with Session(engine) as db:
        director = db.get(User, director_id)
        coordinator_role = db.scalar(select(Role).where(Role.name == "Training Center Coordinator"))
        assert director and coordinator_role
        coordinator_person = Person(display_name="Scoped coordinator")
        db.add(coordinator_person)
        db.flush()
        coordinator = User(
            person_id=coordinator_person.id,
            email="scoped-coordinator@example.test",
            password_hash=hasher.hash("Synthetic password 123"),
            status="active",
        )
        db.add(coordinator)
        db.flush()
        db.add(
            UserRole(
                user_id=coordinator.id,
                role_id=coordinator_role.id,
                organization_id=org,
            )
        )
        db.commit()

        program = service.create_program(
            db,
            org,
            director,
            NamedCreate(code="scoped-program", name_en="Scoped", name_ta="Tamil"),
            "scope-program",
        )
        program = service.transition_program(
            db,
            org,
            program.id,
            director,
            StateCommand(
                expected_version=program.version,
                target="active",
                reason="Ready for scoped delivery",
            ),
            "scope-program-active",
        )
        first_center = service.create_center(
            db,
            org,
            director,
            CenterCreate(
                code="scope-one",
                name_en="Scope one",
                name_ta="Tamil",
                locality="North",
            ),
            "scope-center-one",
        )
        second_center = service.create_center(
            db,
            org,
            director,
            CenterCreate(
                code="scope-two",
                name_en="Scope two",
                name_ta="Tamil",
                locality="South",
            ),
            "scope-center-two",
        )
        first_cohort = service.create_cohort(
            db,
            org,
            director,
            CohortCreate(
                code="scope-batch-one",
                name_en="Scope batch one",
                name_ta="Tamil",
                program_id=program.id,
                center_id=first_center.id,
                starts_on=date(2027, 4, 1),
                ends_on=date(2027, 5, 31),
                capacity=20,
            ),
            "scope-cohort-one",
        )
        second_cohort = service.create_cohort(
            db,
            org,
            director,
            CohortCreate(
                code="scope-batch-two",
                name_en="Scope batch two",
                name_ta="Tamil",
                program_id=program.id,
                center_id=second_center.id,
                starts_on=date(2027, 4, 1),
                ends_on=date(2027, 5, 31),
                capacity=20,
            ),
            "scope-cohort-two",
        )

        with pytest.raises(AuthError) as unassigned:
            service.catalog(db, org, coordinator)
        assert unassigned.value.code == "staff_scope_required"

        assignment = service.create_staff_assignment(
            db,
            org,
            director,
            StaffAssignmentCreate(
                email=coordinator.email,
                center_id=first_center.id,
                reason="Coordinator owns the north center",
            ),
            "scope-assignment",
        )
        assert assignment.state == "active" and assignment.cohort_id is None

        with pytest.raises(AuthError) as duplicate:
            service.create_staff_assignment(
                db,
                org,
                director,
                StaffAssignmentCreate(
                    email=coordinator.email,
                    center_id=first_center.id,
                    reason="Duplicate must be rejected",
                ),
                "scope-assignment-duplicate",
            )
        assert duplicate.value.code == "assignment_exists"

        scoped_catalog = service.catalog(db, org, coordinator)
        assert [item.id for item in scoped_catalog.centers] == [first_center.id]
        assert [item.id for item in scoped_catalog.cohorts] == [first_cohort.id]
        assert [item.id for item in scoped_catalog.staff_assignments] == [assignment.id]

        starts_at = datetime(2027, 4, 10, 9, tzinfo=UTC)
        session = service.create_session(
            db,
            org,
            coordinator,
            SessionCreate(
                cohort_id=first_cohort.id,
                title_en="Scoped session",
                title_ta="Tamil",
                starts_at=starts_at,
                ends_at=starts_at + timedelta(hours=2),
                mode="online",
            ),
            "scope-session",
        )
        assert session.cohort_id == first_cohort.id
        with pytest.raises(AuthError) as denied:
            service.create_session(
                db,
                org,
                coordinator,
                SessionCreate(
                    cohort_id=second_cohort.id,
                    title_en="Denied session",
                    title_ta="Tamil",
                    starts_at=starts_at,
                    ends_at=starts_at + timedelta(hours=2),
                    mode="online",
                ),
                "scope-session-denied",
            )
        assert denied.value.code == "staff_scope_denied"

        row = db.get(ProgramStaffAssignment, assignment.id)
        assert row
        row.center_id = second_center.id
        with pytest.raises(DBAPIError, match="immutable"):
            db.commit()
        db.rollback()

        assignment = service.revoke_staff_assignment(
            db,
            org,
            assignment.id,
            director,
            StaffAssignmentRevoke(
                expected_version=assignment.version,
                reason="Coordinator moved to another center",
            ),
            "scope-assignment-revoke",
        )
        assert assignment.state == "revoked" and assignment.revoked_at
        with pytest.raises(AuthError) as revoked:
            service.catalog(db, org, coordinator)
        assert revoked.value.code == "staff_scope_required"
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.action.like("program_staff_assignment.%"))
            )
            == 2
        )


def test_program_staff_assignment_routes(request) -> None:
    auth_context = request.getfixturevalue("auth")
    client, engine, _, _ = auth_context
    _, _, headers = signed_in(auth_context)
    with Session(engine) as db:
        manager = db.scalar(select(User).where(User.email == "learner@example.com"))
        manager_role = db.scalar(select(Role).where(Role.name == "Program Manager"))
        coordinator_role = db.scalar(select(Role).where(Role.name == "Training Center Coordinator"))
        assert manager and manager_role and coordinator_role
        org = Organization(name="Staff assignment route organization")
        coordinator_person = Person(display_name="Route coordinator")
        db.add_all([org, coordinator_person])
        db.flush()
        coordinator = User(
            person_id=coordinator_person.id,
            email="route-coordinator@example.test",
            password_hash=hasher.hash("Synthetic password 123"),
            status="active",
        )
        db.add(coordinator)
        db.flush()
        db.add_all(
            [
                UserRole(
                    user_id=manager.id,
                    role_id=manager_role.id,
                    organization_id=org.id,
                ),
                UserRole(
                    user_id=coordinator.id,
                    role_id=coordinator_role.id,
                    organization_id=org.id,
                ),
            ]
        )
        db.commit()
        center = service.create_center(
            db,
            org.id,
            manager,
            CenterCreate(
                code="route-center",
                name_en="Route center",
                name_ta="Tamil",
                locality="Central",
            ),
            "route-center",
        )
        org_id = org.id

    root = f"/api/v1/programs/organizations/{org_id}"
    created = client.post(
        root + "/staff-assignments",
        headers=headers,
        json={
            "email": "route-coordinator@example.test",
            "center_id": str(center.id),
            "cohort_id": None,
            "reason": "Route assignment coverage",
        },
    )
    assert created.status_code == 201
    assignment = created.json()
    assert assignment["state"] == "active"
    revoked = client.post(
        root + f"/staff-assignments/{assignment['id']}/revoke",
        headers=headers,
        json={
            "expected_version": assignment["version"],
            "reason": "Route revocation coverage",
        },
    )
    assert revoked.status_code == 200
    assert revoked.json()["state"] == "revoked"
