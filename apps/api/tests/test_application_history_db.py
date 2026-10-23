import os
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_application_submission_db import submission_db  # noqa: F401
from test_identity import auth  # noqa: F401

from app.modules.applications import service
from app.modules.applications.models import Application, ApplicationForm, ApplicationRevision
from app.modules.applications.schemas import AnswerInput, DraftSave, SubmitCommand
from app.modules.identity.models import Organization, User, UserRole, now
from app.modules.identity.security import AuthError
from app.modules.programs.models import ApplicationCycle, Program

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)


@pytest.fixture
def history_db(request):
    engine, org, applicant_id, peer_id, cycle_id, form = request.getfixturevalue("submission_db")
    with Session(engine) as db:
        applicant, peer = db.get(User, applicant_id), db.get(User, peer_id)
        director = db.scalar(select(User).where(User.email == "submission-0@example.test"))
        cycle = db.get(ApplicationCycle, cycle_id)
        assert applicant and peer and director and cycle
        # The imported service fixture uses reserved .test addresses. Route login
        # correctly validates EmailStr, so use accepted synthetic example.com here.
        for user in (applicant, peer, director):
            user.email = user.email.replace("@example.test", "@example.com")
        current = now()
        other_org = Organization(name="Other owned application organization")
        db.add(other_org)
        db.flush()
        other_form = ApplicationForm(
            organization_id=other_org.id,
            version=1,
            state="published",
            title_en="Other form",
            title_ta="Other Tamil form",
            published_at=current,
        )
        other_program = Program(
            organization_id=other_org.id,
            code="other-program",
            name_en="Other program",
            name_ta="Other Tamil program",
            state="active",
        )
        db.add_all([other_form, other_program])
        db.flush()
        next_cycle = ApplicationCycle(
            organization_id=org,
            program_id=cycle.program_id,
            form_id=form.id,
            code="next-intake",
            name_en="Next intake",
            name_ta="Next Tamil intake",
            opens_at=current - timedelta(days=1),
            closes_at=current + timedelta(days=10),
            state="open",
        )
        other_cycle = ApplicationCycle(
            organization_id=other_org.id,
            program_id=other_program.id,
            form_id=other_form.id,
            code="other-intake",
            name_en="Other intake",
            name_ta="Other Tamil intake",
            opens_at=current - timedelta(days=1),
            closes_at=current + timedelta(days=10),
            state="open",
        )
        db.add_all([next_cycle, other_cycle])
        db.commit()
        original = service.create_cycle_draft(db, org, cycle_id, applicant, "original")
        peer_draft = service.create_cycle_draft(db, org, cycle_id, peer, "peer")
        staff_draft = service.create_cycle_draft(db, org, cycle_id, director, "staff")
        legacy = service.create_draft(db, other_org.id, applicant, "legacy")
        next_draft = service.create_cycle_draft(db, org, next_cycle.id, applicant, "next")
        other_draft = service.create_cycle_draft(
            db, other_org.id, other_cycle.id, applicant, "other"
        )
        other_peer = service.create_cycle_draft(
            db, other_org.id, other_cycle.id, peer, "other-peer"
        )
        # Equal creation times exercise the UUID tie-breaker. Updated time must not
        # affect pagination: the oldest draft is saved and submitted last below.
        dates = {
            original.id: current - timedelta(days=4),
            legacy.id: current - timedelta(days=3),
            next_draft.id: current - timedelta(days=2),
            other_draft.id: current - timedelta(days=2),
        }
        for application_id, created_at in dates.items():
            row = db.get(Application, application_id)
            assert row
            row.created_at = created_at
        db.commit()
        saved = service.save(
            db,
            org,
            original.id,
            applicant,
            DraftSave(
                expected_version=1,
                answers=[AnswerInput(field_id=form.fields[0].id, value="PRIVATE ANSWER MARKER")],
            ),
            "save-private-answer",
        )
        submitted = service.submit(
            db,
            org,
            original.id,
            applicant,
            SubmitCommand(
                expected_version=saved.version,
                accepted_acknowledgement_ids=[item.id for item in form.acknowledgements],
            ),
            "submit",
        )
        cycle.state = "closed"
        cycle.version += 1
        db.commit()
        yield {
            "engine": engine,
            "org": org,
            "other_org": other_org.id,
            "applicant_id": applicant_id,
            "peer_id": peer_id,
            "director_id": director.id,
            "cycle_id": cycle_id,
            "other_cycle_id": other_cycle.id,
            "original": original.id,
            "legacy": legacy.id,
            "peer": peer_draft.id,
            "other_peer": other_peer.id,
            "staff": staff_draft.id,
            "expected_ids": sorted(dates, key=lambda item: (dates[item], item), reverse=True),
            "submitted_number": submitted.application_number,
            "next": next_draft.id,
        }


def _login(client, email):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Synthetic password 123"},
    )
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def test_history_is_owner_only_across_organizations_and_closed_cycles(history_db) -> None:
    data = history_db
    with Session(data["engine"]) as db:
        applicant = db.get(User, data["applicant_id"])
        peer = db.get(User, data["peer_id"])
        director = db.get(User, data["director_id"])
        assert applicant and peer and director
        assert (
            db.scalar(
                select(func.count()).select_from(UserRole).where(UserRole.user_id == applicant.id)
            )
            == 0
        )
        result = service.history(db, applicant, None, 100)
        assert [item.id for item in result.items] == data["expected_ids"]
        assert result.next_cursor is None
        assert {item.organization_id for item in result.items} == {data["org"], data["other_org"]}
        receipt = next(item for item in result.items if item.id == data["original"])
        assert receipt.state == "submitted"
        assert receipt.version == 3 and receipt.submitted_at
        assert receipt.application_number == data["submitted_number"]
        assert receipt.cycle_id == data["cycle_id"]
        assert receipt.cycle_name_en == "Enterprise intake"
        assert receipt.cycle_name_ta == "Synthetic Tamil intake"
        assert receipt.organization_name == "Submission organization"
        legacy = next(item for item in result.items if item.id == data["legacy"])
        assert legacy.cycle_id is None and legacy.cycle_code is None
        assert legacy.cycle_name_en is None and legacy.cycle_name_ta is None
        assert legacy.application_number is None and legacy.submitted_at is None
        assert {item.id for item in service.history(db, peer, None, 100).items} == {
            data["peer"],
            data["other_peer"],
        }
        # A staff role does not turn this endpoint into a staff queue.
        assert [item.id for item in service.history(db, director, None, 100).items] == [
            data["staff"]
        ]
        assert service.available_cycles(db, data["org"]).items[0].id != data["cycle_id"]
        detail = service.cycle_application(db, data["org"], data["cycle_id"], applicant)
        assert detail.id == data["original"] and detail.state == "submitted"
        for org, cycle_id in (
            (data["other_org"], data["cycle_id"]),
            (data["org"], uuid4()),
        ):
            with pytest.raises(AuthError) as hidden:
                service.cycle_application(db, org, cycle_id, applicant)
            assert hidden.value.status == 404


def test_history_pagination_is_stable_when_owned_drafts_are_saved(history_db) -> None:
    data = history_db
    with Session(data["engine"]) as db:
        applicant = db.get(User, data["applicant_id"])
        assert applicant
        first = service.history(db, applicant, None, 2)
        assert [item.id for item in first.items] == data["expected_ids"][:2]
        assert first.next_cursor == data["expected_ids"][1]
        legacy = db.get(Application, data["legacy"])
        assert legacy
        service.save(
            db,
            data["other_org"],
            legacy.id,
            applicant,
            DraftSave(expected_version=legacy.version, answers=[]),
            "update-between-pages",
        )
        second = service.history(db, applicant, first.next_cursor, 2)
        assert [item.id for item in second.items] == data["expected_ids"][2:]
        assert second.next_cursor is None
        assert service.history(db, applicant, second.items[-1].id, 2).items == []
        for cursor in (uuid4(), data["peer"], data["other_peer"], data["staff"]):
            with pytest.raises(AuthError) as invalid:
                service.history(db, applicant, cursor, 2)
            assert invalid.value.status == 422 and invalid.value.code == "invalid_cursor"


def test_history_route_requires_authentication_and_returns_only_summary_fields(request, history_db):
    client = request.getfixturevalue("auth")[0]
    data = history_db
    path = "/api/v1/applications/mine"
    assert client.get(path).status_code == 401
    headers = _login(client, "submission-1@example.com")
    response = client.get(path, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "next_cursor"}
    assert {item["id"] for item in body["items"]} == {
        str(application_id) for application_id in data["expected_ids"]
    }
    assert all(
        set(item)
        == {
            "id",
            "organization_id",
            "organization_name",
            "cycle_id",
            "cycle_code",
            "cycle_name_en",
            "cycle_name_ta",
            "state",
            "version",
            "application_number",
            "submitted_at",
            "updated_at",
        }
        for item in body["items"]
    )
    assert "PRIVATE ANSWER MARKER" not in response.text
    for field in ("person_id", "answers", "reason_code", "status_history", "scores", "notes"):
        assert field not in response.text
    for cursor in (uuid4(), data["peer"], data["other_peer"], data["staff"]):
        invalid = client.get(path, params={"cursor": str(cursor)}, headers=headers)
        assert invalid.status_code == 422
        assert invalid.json()["error"]["code"] == "invalid_cursor"
        assert str(cursor) not in invalid.text
    assert client.post(path, headers=headers, json={}).status_code == 405


def test_history_route_rejects_unbounded_or_unsupported_query(request, history_db):
    client = request.getfixturevalue("auth")[0]
    headers = _login(client, "submission-1@example.com")
    for query in (
        "limit=0",
        "limit=101",
        "limit=-1",
        "limit=invalid",
        "cursor=invalid",
        "organization_id=00000000-0000-0000-0000-000000000001",
        "person_id=other",
        "extra=true",
    ):
        assert client.get("/api/v1/applications/mine?" + query, headers=headers).status_code == 422


def test_draft_creation_resumes_only_drafts_and_rejects_all_later_states(request):
    engine, org, applicant_id, _, cycle_id, _ = request.getfixturevalue("submission_db")
    client = request.getfixturevalue("auth")[0]
    with Session(engine) as db:
        applicant = db.get(User, applicant_id)
        original_cycle = db.get(ApplicationCycle, cycle_id)
        assert applicant and original_cycle
        applicant.email = "draft-state-owner@example.com"
        db.commit()
        headers = _login(client, applicant.email)
        for state in (
            "submitted",
            "under_review",
            "shortlisted",
            "interview_scheduled",
            "selected",
            "waitlisted",
            "rejected",
            "enrolled",
        ):
            cycle = ApplicationCycle(
                organization_id=org,
                program_id=original_cycle.program_id,
                form_id=original_cycle.form_id,
                code="draft-state-" + state,
                name_en="Synthetic " + state,
                name_ta="Synthetic Tamil " + state,
                opens_at=now() - timedelta(days=1),
                closes_at=now() + timedelta(days=1),
                state="open",
            )
            db.add(cycle)
            db.commit()
            root = f"/api/v1/applications/organizations/{org}/cycles/{cycle.id}"
            started = client.post(root + "/draft", headers=headers, json={})
            assert started.status_code == 201
            draft_id = started.json()["id"]
            resumed = client.post(root + "/draft", headers=headers, json={})
            assert resumed.status_code == 201 and resumed.json()["id"] == draft_id
            row = db.get(Application, UUID(draft_id))
            assert row
            # Seed each later state with the same immutable submission evidence.
            # Selection/enrollment transitions have separate workflow coverage.
            row.state = state
            row.version += 1
            row.application_number = "SYNTHETIC-" + uuid4().hex[:16]
            row.submitted_at = now()
            db.commit()
            result = client.post(root + "/draft", headers=headers, json={})
            assert result.status_code == 409
            assert result.json()["error"]["code"] == "application_already_submitted"
            view = client.get(root + "/application", headers=headers)
            assert view.status_code == 200 and view.json()["state"] == state
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(ApplicationRevision)
                    .where(ApplicationRevision.application_id == row.id)
                )
                == 1
            )
