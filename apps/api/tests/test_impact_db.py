import csv
import io
import os
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_identity import account, auth, signed_in  # noqa: F401
from test_lms_db import learning_context

from app.modules.applications.models import Application
from app.modules.businesses.models import BusinessProfile
from app.modules.identity.models import AuditLog, Role, User, UserRole, now
from app.modules.identity.security import AuthError
from app.modules.programs.models import Enrollment, Participant
from app.modules.reports import service
from app.modules.reports.models import (
    CohortImpactSnapshot,
    ImpactDefinition,
    ImpactDefinitionHistory,
    ImpactRecord,
    ReportExport,
    ReportExportCapability,
)
from app.modules.reports.schemas import ReportDashboard

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)


def context(request):
    authentication, owner_headers, org, other, cohort, enrollment, owner = learning_context(request)
    client, engine, _, _ = authentication
    credentials = {
        name: account(authentication, f"impact-{name}@example.com")
        for name in ("director", "manager", "peer", "outsider")
    }
    users = {}
    with Session(engine) as db:
        roles = {role.name: role.id for role in db.scalars(select(Role))}
        db.execute(
            delete(UserRole).where(
                UserRole.user_id == owner, UserRole.role_id == roles["Program Director"]
            )
        )
        for name, login in credentials.items():
            user = db.scalar(select(User).where(User.email == login["email"]))
            assert user
            users[name] = user.id
            db.add(
                UserRole(
                    user_id=user.id,
                    organization_id=org,
                    role_id=roles[
                        {
                            "director": "Program Director",
                            "manager": "Program Manager",
                            "peer": "Participant",
                            "outsider": "Participant",
                        }[name]
                    ],
                )
            )
        original = db.get(Enrollment, enrollment)
        original.enrolled_at = now() - timedelta(days=60)
        source = db.get(Application, original.application_id)
        peer = db.get(User, users["peer"])
        application = Application(
            organization_id=org,
            person_id=peer.person_id,
            form_id=source.form_id,
            cycle_id=source.cycle_id,
            state="enrolled",
            version=8,
            application_number="EDP-I01-PEER",
            submitted_at=now() - timedelta(days=30),
        )
        participant = Participant(organization_id=org, person_id=peer.person_id, status="active")
        db.add_all([application, participant])
        db.flush()
        peer_enrollment = Enrollment(
            organization_id=org,
            participant_id=participant.id,
            program_id=original.program_id,
            cohort_id=original.cohort_id,
            application_id=application.id,
            status="active",
            enrolled_at=now() - timedelta(days=60),
        )
        db.add(peer_enrollment)
        db.flush()
        peer_id, program_id = peer_enrollment.id, original.program_id
        db.commit()
    headers = {"owner": owner_headers}
    for name, login in credentials.items():
        response = client.post("/api/v1/auth/login", json=login)
        assert response.status_code == 200, response.text
        headers[name] = {"Authorization": "Bearer " + response.json()["access_token"]}
    return {
        "client": client,
        "engine": engine,
        "org": org,
        "other": other,
        "cohort": cohort,
        "program": program_id,
        "enrollment": enrollment,
        "peer_enrollment": peer_id,
        "headers": headers,
        "users": users,
        "impact": f"/api/v1/impact/organizations/{org}",
        "report": f"/api/v1/reports/organizations/{org}",
    }


def definition(ctx, *, publish=True, **overrides):
    payload = {
        "title_en": "Synthetic enterprise measures",
        "title_ta": "செயற்கை நிறுவன அளவீடுகள்",
        "definition_en": "Self-reported started, active and current jobs at the observation date.",
        "definition_ta": "கவனிப்பு தேதியில் தொழில் தொடக்கம், செயல்பாடு மற்றும் வேலைகள் சுய அறிக்கை.",
        "reason": "Synthetic policy edition for local tests",
        **overrides,
    }
    response = ctx["client"].post(
        ctx["impact"] + "/definitions", json=payload, headers=ctx["headers"]["director"]
    )
    assert response.status_code == 201, response.text
    result = response.json()
    if publish:
        response = ctx["client"].post(
            ctx["impact"] + f"/definitions/{result['id']}/publish",
            headers=ctx["headers"]["director"],
            json={"expected_version": 1, "reason": "Policy approved for test"},
        )
        assert response.status_code == 200, response.text
        result = response.json()
    return result


def observation(ctx, source, *, owner="owner", **overrides):
    payload = {
        "enrollment_id": str(ctx["enrollment"] if owner == "owner" else ctx["peer_enrollment"]),
        "definition_id": source["id"],
        "stage": "baseline",
        "observed_on": (now().date() - timedelta(days=20)).isoformat(),
        "business_started": False,
        "business_active": False,
        "jobs_created": 0,
        "expected_revision": 0,
        "reason": "Synthetic participant evidence",
        "request_id": str(uuid4()),
        **overrides,
    }
    response = ctx["client"].post(
        ctx["impact"] + "/records", json=payload, headers=ctx["headers"][owner]
    )
    return response, payload


def filters(ctx, **overrides):
    return {
        "from_date": (now().date() - timedelta(days=30)).isoformat(),
        "through_date": now().date().isoformat(),
        **overrides,
    }


def test_definition_editions_publication_scope_and_database_evidence(request):
    ctx = context(request)
    client, headers, base = ctx["client"], ctx["headers"], ctx["impact"]
    draft = definition(ctx, publish=False)
    assert draft["edition"] == 1 and draft["state"] == "draft"
    assert client.get(base + "/definitions", headers=headers["owner"]).json()["items"] == []
    assert client.post(base + "/definitions", headers=headers["owner"], json={}).status_code == 422
    command = {"expected_version": 1, "reason": "Publish approved definition"}
    assert (
        client.post(
            base + f"/definitions/{draft['id']}/publish", headers=headers["owner"], json=command
        ).status_code
        == 403
    )
    published = client.post(
        base + f"/definitions/{draft['id']}/publish", headers=headers["manager"], json=command
    )
    assert published.status_code == 200, published.text
    assert published.json()["version"] == 2
    assert (
        client.post(
            base + f"/definitions/{draft['id']}/archive", headers=headers["director"], json=command
        ).status_code
        == 409
    )
    assert (
        client.post(
            base.replace(str(ctx["org"]), str(ctx["other"]))
            + f"/definitions/{draft['id']}/publish",
            headers=headers["director"],
            json=command,
        ).status_code
        == 403
    )
    edition = definition(ctx)
    assert edition["edition"] == 2
    response, _ = observation(ctx, draft)
    assert response.status_code == 201, response.text
    archived = client.post(
        base + f"/definitions/{draft['id']}/archive",
        headers=headers["director"],
        json={"expected_version": 2, "reason": "Superseded measurement edition"},
    )
    assert archived.status_code == 200
    assert (
        client.get(base + "/definitions", headers=headers["owner"]).json()["items"][0]["id"]
        == edition["id"]
    )
    mine = client.get(base + "/mine", headers=headers["owner"]).json()
    assert any(
        row["id"] == draft["id"] and row["state"] == "archived" for row in mine["definitions"]
    )
    correction, _ = observation(ctx, draft, expected_revision=1, jobs_created=2)
    assert correction.status_code == 201, correction.text
    first, _ = observation(ctx, draft, owner="peer")
    assert first.status_code == 409
    with Session(ctx["engine"]) as db:
        assert db.scalar(select(func.count()).select_from(ImpactDefinitionHistory)) == 5
        for model in (ImpactDefinition, ImpactDefinitionHistory):
            key = db.scalar(select(model.id))
            with pytest.raises(DBAPIError):
                db.execute(update(model).where(model.id == key).values(created_at=now()))
                db.commit()
            db.rollback()
            with pytest.raises(DBAPIError):
                db.execute(delete(model).where(model.id == key))
                db.commit()
            db.rollback()
    bad = {"title_en": "bad\x00title"}
    payload = {
        "title_en": "Valid title",
        "title_ta": "சரியான தலைப்பு",
        "definition_en": "Valid definition",
        "definition_ta": "சரியான விளக்கம்",
        "reason": "Valid reason",
        **bad,
    }
    assert (
        client.post(base + "/definitions", headers=headers["director"], json=payload).status_code
        == 422
    )


def test_observation_independent_owner_corrections_idempotency_validation_and_guards(request):
    ctx = context(request)
    source, second = sorted(
        [definition(ctx), definition(ctx)], key=lambda row: row["id"], reverse=True
    )
    client, headers, base = ctx["client"], ctx["headers"], ctx["impact"]
    response, payload = observation(ctx, source)
    assert response.status_code == 201, response.text
    first = response.json()
    assert first["revision"] == 1
    replay = client.post(base + "/records", headers=headers["owner"], json=payload)
    assert replay.status_code == 201 and replay.json() == first
    assert (
        client.post(
            base + "/records", headers=headers["owner"], json={**payload, "jobs_created": 1}
        ).status_code
        == 409
    )
    stale, _ = observation(ctx, source, jobs_created=1)
    assert stale.status_code == 409
    pinned, _ = observation(ctx, second, jobs_created=1, expected_revision=1)
    assert pinned.status_code == 409
    corrected, _ = observation(ctx, source, jobs_created=3, expected_revision=1)
    assert corrected.status_code == 201 and corrected.json()["revision"] == 2
    for actor in ("peer", "director", "outsider"):
        rejected = client.post(
            base + "/records", headers=headers[actor], json={**payload, "request_id": str(uuid4())}
        )
        assert rejected.status_code == 403, (actor, rejected.text)
    assert client.get(base + "/mine", headers=headers["peer"]).json()["records"] == []
    queried = client.get(
        base + "/mine",
        headers=headers["owner"],
        params={
            "enrollment_id": payload["enrollment_id"],
            "stage": "baseline",
            "observed_on": payload["observed_on"],
            "limit": 1,
        },
    ).json()
    assert queried["records"][0]["revision"] == 2 and queried["record_next_cursor"]
    assert {row["id"] for row in queried["definitions"]} == {source["id"], second["id"]}
    older = client.get(
        base + "/mine",
        headers=headers["owner"],
        params={"record_cursor": queried["record_next_cursor"], "limit": 1},
    ).json()
    assert older["records"][0]["revision"] == 1
    assert (
        client.get(
            base + "/mine",
            headers=headers["peer"],
            params={"record_cursor": queried["record_next_cursor"]},
        ).status_code
        == 422
    )
    for changes in (
        {"business_active": True},
        {"jobs_created": -1},
        {"jobs_created": 100001},
        {"reason": "  "},
        {"reason": "bad\x00reason"},
        {"observed_on": (now().date() + timedelta(days=1)).isoformat()},
    ):
        assert (
            client.post(
                base + "/records", headers=headers["owner"], json={**payload, **changes}
            ).status_code
            == 422
        )
    with Session(ctx["engine"]) as db:
        assert db.scalar(select(func.count()).select_from(BusinessProfile)) == 0
        assert db.scalar(select(func.count()).select_from(ImpactRecord)) == 2
        original = db.get(ImpactRecord, UUID(first["id"]))
        for statement in (
            update(ImpactRecord).where(ImpactRecord.id == original.id).values(jobs_created=99),
            delete(ImpactRecord).where(ImpactRecord.id == original.id),
        ):
            with pytest.raises(DBAPIError):
                db.execute(statement)
                db.commit()
            db.rollback()
        invalid = ImpactRecord(
            organization_id=ctx["org"],
            participant_id=original.participant_id,
            enrollment_id=ctx["peer_enrollment"],
            definition_id=UUID(source["id"]),
            actor_user_id=original.actor_user_id,
            stage="outcome",
            observed_on=now().date(),
            business_started=False,
            business_active=False,
            jobs_created=0,
            revision=1,
            reason="Invalid owner",
            request_id=uuid4(),
            request_digest="0" * 64,
        )
        db.add(invalid)
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()


def test_impact_aggregates_latest_revisions_mixed_editions_coverage_and_frozen_snapshot(
    request, monkeypatch
):
    ctx = context(request)
    source, second = definition(ctx), definition(ctx)
    client, headers, base = ctx["client"], ctx["headers"], ctx["report"]
    for overrides in (
        {"jobs_created": 2},
        {"jobs_created": 3, "expected_revision": 1},
        {
            "stage": "outcome",
            "observed_on": (now().date() - timedelta(days=10)).isoformat(),
            "jobs_created": 6,
            "business_started": True,
            "business_active": True,
        },
        {
            "stage": "outcome",
            "observed_on": now().date().isoformat(),
            "jobs_created": 1,
            "business_started": True,
            "business_active": False,
        },
    ):
        result, _ = observation(ctx, source, **overrides)
        assert result.status_code == 201, result.text
    result, _ = observation(
        ctx,
        second,
        owner="peer",
        stage="outcome",
        observed_on=now().date().isoformat(),
        jobs_created=4,
    )
    assert result.status_code == 201, result.text
    query = filters(ctx, cohort_id=str(ctx["cohort"]), program_id=str(ctx["program"]))
    response = client.get(base + "/dashboard", headers=headers["director"], params=query)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["eligible_impact_enrollments"] == 2 and data["impact_reported_enrollments"] == 2
    assert data["impact_coverage"] == 100
    groups = {row["definition"]["id"]: row for row in data["impact"]}
    assert groups[source["id"]]["baseline_jobs"] == 3
    assert groups[source["id"]]["outcome_jobs"] == 1
    assert groups[source["id"]]["matched_sample"] == 1
    assert groups[source["id"]]["matched_jobs_change"] == -2
    assert groups[second["id"]]["matched_sample"] == 0
    assert groups[second["id"]]["matched_jobs_change"] is None
    assert len(groups) == 2
    snapshot_payload = {**query, "request_id": str(uuid4())}
    original_builder = service.build_operational_metrics

    def mutate_after_operational_read(db, org, **kwargs):
        assert db.connection().get_isolation_level() == "REPEATABLE READ"
        metrics = original_builder(db, org, **kwargs)
        # A separate writer commits between operational and impact queries. Snapshot
        # evidence must still contain the original value from the same database view.
        with Session(ctx["engine"]) as writer:
            previous = writer.scalar(
                select(ImpactRecord).where(
                    ImpactRecord.enrollment_id == ctx["enrollment"],
                    ImpactRecord.stage == "outcome",
                    ImpactRecord.observed_on == now().date(),
                )
            )
            writer.add(
                ImpactRecord(
                    organization_id=ctx["org"],
                    participant_id=previous.participant_id,
                    enrollment_id=previous.enrollment_id,
                    definition_id=previous.definition_id,
                    actor_user_id=previous.actor_user_id,
                    stage="outcome",
                    observed_on=previous.observed_on,
                    business_started=True,
                    business_active=True,
                    jobs_created=8,
                    revision=2,
                    reason="Concurrent independently committed correction",
                    request_id=uuid4(),
                    request_digest="1" * 64,
                )
            )
            writer.commit()
        return metrics

    monkeypatch.setattr(service, "build_operational_metrics", mutate_after_operational_read)
    created = client.post(base + "/snapshots", headers=headers["director"], json=snapshot_payload)
    monkeypatch.setattr(service, "build_operational_metrics", original_builder)
    assert created.status_code == 201, created.text
    frozen = created.json()
    assert (
        next(
            group
            for group in frozen["dashboard"]["impact"]
            if group["definition"]["id"] == source["id"]
        )["outcome_jobs"]
        == 1
    )
    assert (
        client.post(base + "/snapshots", headers=headers["director"], json=snapshot_payload).json()
        == frozen
    )
    assert (
        client.post(
            base + "/snapshots",
            headers=headers["director"],
            json={**snapshot_payload, "from_date": now().date().isoformat()},
        ).status_code
        == 409
    )
    result, _ = observation(
        ctx,
        source,
        stage="outcome",
        observed_on=now().date().isoformat(),
        expected_revision=2,
        jobs_created=9,
        business_started=True,
        business_active=True,
    )
    assert result.status_code == 201
    assert (
        client.get(base + f"/snapshots/{frozen['id']}", headers=headers["manager"]).json() == frozen
    )
    listing = client.get(base + "/snapshots", headers=headers["manager"]).json()["items"][0]
    assert "dashboard" not in listing and listing["filters"] == frozen["dashboard"]["filters"]
    assert (
        client.get(base + "/dashboard", headers=headers["owner"], params=query).status_code == 403
    )
    assert (
        client.get(
            base.replace(str(ctx["org"]), str(ctx["other"])) + f"/snapshots/{frozen['id']}",
            headers=headers["director"],
        ).status_code
        == 403
    )
    for invalid in (
        {"from_date": "2020-01-01"},
        {"through_date": "2099-01-01"},
        {"program_id": str(uuid4())},
        {"cohort_id": str(uuid4())},
    ):
        assert (
            client.get(
                base + "/dashboard", headers=headers["director"], params={**query, **invalid}
            ).status_code
            == 422
        )
    with Session(ctx["engine"]) as db:
        db.execute(
            update(Enrollment)
            .where(Enrollment.id == ctx["peer_enrollment"])
            .values(status="withdrawn", version=2)
        )
        db.commit()
        for statement in (
            update(CohortImpactSnapshot).values(dictionary_version="altered"),
            delete(CohortImpactSnapshot),
        ):
            with pytest.raises(DBAPIError):
                db.execute(statement)
                db.commit()
            db.rollback()
    withdrawn = client.get(base + "/dashboard", headers=headers["director"], params=query).json()
    assert (
        withdrawn["eligible_impact_enrollments"] == 2
        and withdrawn["impact_reported_enrollments"] == 2
    )
    assert (
        next(row for row in withdrawn["impact"] if row["definition"]["id"] == second["id"])[
            "outcome_jobs"
        ]
        == 4
    )


def test_aggregate_exports_owner_permissions_tokens_expiry_formula_safety_and_audits(
    request, monkeypatch
):
    ctx = context(request)
    source = definition(ctx, title_en="=Synthetic untrusted title")
    for overrides in (
        {"jobs_created": 3},
        {"stage": "outcome", "observed_on": now().date().isoformat(), "jobs_created": 1},
    ):
        assert observation(ctx, source, **overrides)[0].status_code == 201
    client, headers, base = ctx["client"], ctx["headers"], ctx["report"]
    snapshot = client.post(
        base + "/snapshots",
        headers=headers["director"],
        json={**filters(ctx), "request_id": str(uuid4())},
    ).json()
    payload = {
        "snapshot_id": snapshot["id"],
        "request_id": str(uuid4()),
        "reason": "Aggregate impact review",
    }
    assert (
        client.post(base + "/exports", headers=headers["manager"], json=payload).status_code == 403
    )
    created = client.post(base + "/exports", headers=headers["director"], json=payload)
    assert created.status_code == 201, created.text
    job = created.json()
    assert "csv_content" not in job and "reason" not in job
    assert client.post(base + "/exports", headers=headers["director"], json=payload).json() == job
    assert (
        client.post(
            base + "/exports",
            headers=headers["director"],
            json={**payload, "reason": "Changed request"},
        ).status_code
        == 409
    )
    access = client.post(
        base + f"/exports/{job['id']}/access", headers=headers["director"], json={}
    )
    assert access.status_code == 200, access.text
    token = access.json()["token"]
    path = base + f"/exports/{job['id']}/download/{token}"
    downloaded = client.get(path, headers=headers["director"])
    assert downloaded.status_code == 200, downloaded.text
    assert downloaded.headers["content-type"].startswith("text/csv")
    assert downloaded.headers["cache-control"] == "no-store"
    assert downloaded.headers["x-content-type-options"] == "nosniff"
    assert "attachment" in downloaded.headers["content-disposition"]
    rows = list(csv.reader(io.StringIO(downloaded.text)))
    assert any("'=Synthetic untrusted title" in row for row in rows)
    negative = next(row for row in rows if row[1] == "edition_1:matched_jobs_change")
    assert negative[4] == "-2"
    assert any(row[1] == "impact_coverage_percent" and row[2] == "50.0" for row in rows)
    assert (
        "learner@example.com" not in downloaded.text
        and "Synthetic participant evidence" not in downloaded.text
    )
    assert (
        client.get(
            base + f"/exports/{job['id']}/download/{'X' * 43}", headers=headers["director"]
        ).status_code
        == 404
    )
    assert client.get(path, headers=headers["manager"]).status_code == 403
    with Session(ctx["engine"]) as db:
        peer = db.get(User, ctx["users"]["peer"])
        director = db.scalar(select(Role).where(Role.name == "Program Director"))
        db.add(UserRole(user_id=peer.id, organization_id=ctx["org"], role_id=director.id))
        db.commit()
    assert client.get(path, headers=headers["peer"]).status_code == 404
    assert client.get(base + "/exports", headers=headers["peer"]).json()["items"] == []
    with Session(ctx["engine"]) as db:
        capabilities = list(db.scalars(select(ReportExportCapability)))
        assert len(capabilities) == 1 and token not in capabilities[0].token_hash
        audits = list(db.scalars(select(AuditLog).where(AuditLog.action.like("report.%"))))
        assert any(row.action == "report.export.download" for row in audits)
        assert all(
            token not in str(row.__dict__) and payload["reason"] not in str(row.__dict__)
            for row in audits
        )
        for model in (ReportExport, ReportExportCapability):
            for statement in (update(model).values(created_at=now()), delete(model)):
                with pytest.raises(DBAPIError):
                    db.execute(statement)
                    db.commit()
                db.rollback()
    actual = now()
    monkeypatch.setattr(service, "now", lambda: actual + timedelta(minutes=6))
    assert client.get(path, headers=headers["director"]).status_code == 410
    monkeypatch.setattr(service, "now", lambda: actual)
    fresh = client.post(base + f"/exports/{job['id']}/access", headers=headers["director"], json={})
    assert fresh.status_code == 200
    monkeypatch.setattr(service, "now", lambda: actual + timedelta(days=2))
    assert (
        client.post(
            base + f"/exports/{job['id']}/access", headers=headers["director"], json={}
        ).status_code
        == 410
    )
    monkeypatch.setattr(service, "now", lambda: actual)
    with Session(ctx["engine"]) as db:
        director = db.scalar(select(Role).where(Role.name == "Program Director"))
        db.execute(
            delete(UserRole).where(
                UserRole.user_id == ctx["users"]["director"], UserRole.role_id == director.id
            )
        )
        db.commit()
    assert client.get(path, headers=headers["director"]).status_code == 403


def test_csv_bounds_preserve_numeric_changes_and_escape_text_after_bom():
    assert service.csv_cell(-2) == "-2"
    assert service.csv_cell("-2") == "'-2"
    assert service.csv_cell("\ufeff \t=SUM(A1:A2)") == "'\ufeff \t=SUM(A1:A2)"
    sample = {
        "key": "synthetic",
        "group": "program",
        "label_en": "Synthetic metric",
        "label_ta": "செயற்கை அளவீடு",
        "definition_en": "Synthetic definition",
        "definition_ta": "செயற்கை விளக்கம்",
        "source": "synthetic",
        "temporal_basis": "UTC date range",
        "unit": "count",
        "value": 2,
    }
    dashboard = ReportDashboard.model_validate(
        {
            "filters": {"from_date": now().date(), "through_date": now().date()},
            "generated_at": now(),
            "dictionary_version": "synthetic",
            "metrics": [sample],
            "impact": [],
            "eligible_impact_enrollments": 0,
            "impact_reported_enrollments": 0,
            "impact_coverage": None,
            "caveat_en": "Synthetic local evidence",
            "caveat_ta": "செயற்கை உள்ளூர் ஆதாரம்",
        }
    )
    assert service.csv_report(dashboard)[1] < 500
    with pytest.raises(AuthError):
        service.csv_report(dashboard.model_copy(update={"metrics": dashboard.metrics * 500}))
    huge = dashboard.metrics[0].model_copy(update={"label_en": "x" * 262144})
    with pytest.raises(AuthError):
        service.csv_report(dashboard.model_copy(update={"metrics": [huge]}))
