import os
from datetime import date

import pytest
from sqlalchemy import select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_identity import auth, signed_in  # noqa: F401
from test_lms_db import learning_context

from app.modules.businesses.models import BusinessOutcomeSnapshot, BusinessProfileRevision

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)


def test_profile_policy_followup_and_immutable_snapshots(request) -> None:
    context, headers, org, other, _, enrollment, _ = learning_context(request)
    client, engine, _, _ = context
    base = f"/api/v1/businesses/organizations/{org}"
    assert client.get(base + "/mine", headers=headers).json()["entries"][0]["profile"] is None
    assert client.get(f"/api/v1/businesses/organizations/{other}/mine", headers=headers).status_code == 403
    policy = client.post(base + "/policy", headers=headers, json={
        "expected_version": 0, "day_offsets": [5, 30], "reason": "Program follow-up schedule",
    })
    assert policy.status_code == 200, policy.text
    assert client.post(base + "/policy", headers=headers, json={
        "expected_version": 0, "day_offsets": [7], "reason": "Stale request",
    }).status_code == 409
    fields = {
        "name": "Synthetic bakery", "sector": "Food", "products_services": "Baked goods",
        "stage": "idea", "team_size": 1, "investment_band": "under_1l",
        "funding_status": "none", "revenue_band": "none", "public_opt_in": False,
    }
    created = client.post(base + "/profiles", headers=headers,
                          json={"enrollment_id": str(enrollment), **fields})
    assert created.status_code == 201, created.text
    profile = created.json()
    assert [f["offset_days"] for f in profile["follow_ups"]] == [5, 30]
    assert client.post(base + "/profiles", headers=headers,
                       json={"enrollment_id": str(enrollment), **fields}).status_code == 409
    assert client.post(base + f"/profiles/{profile['id']}/update", headers=headers,
                       json={"expected_version": 0, **fields}).status_code == 422
    changed = client.post(base + f"/profiles/{profile['id']}/update", headers=headers,
                          json={"expected_version": 1, **{**fields, "name": "New bakery"}})
    assert changed.status_code == 200, changed.text
    assert changed.json()["version"] == 2
    assert len(changed.json()["revisions"]) == 2
    assert client.post(base + f"/profiles/{profile['id']}/update", headers=headers,
                       json={"expected_version": 1, **fields}).status_code == 409
    outcome_url = base + f"/follow-ups/{profile['follow_ups'][0]['id']}/outcome"
    outcome_data = {
        "reported_on": date.today().isoformat(), "business_started": True,
        "business_active": True, "jobs_created": 2, "funding_band": "none",
        "revenue_band": "under_10k", "challenges": "Synthetic challenge",
    }
    outcome = client.post(outcome_url, headers=headers, json=outcome_data)
    assert outcome.status_code == 201, outcome.text
    assert client.post(outcome_url, headers=headers, json=outcome_data).status_code == 409
    queue = client.get(base + "/staff", headers=headers)
    assert queue.status_code == 200
    assert queue.json()["profiles"][0]["completed_count"] == 1
    assert queue.json()["policy"]["day_offsets"] == [5, 30]
    with Session(engine) as db:
        revision = db.scalar(select(BusinessProfileRevision).where(
            BusinessProfileRevision.profile_id == profile["id"],
            BusinessProfileRevision.version == 1,
        ))
        snapshot = db.scalar(select(BusinessOutcomeSnapshot).where(
            BusinessOutcomeSnapshot.id == outcome.json()["id"]
        ))
        assert revision and snapshot
        with pytest.raises(DBAPIError):
            db.execute(update(BusinessProfileRevision).where(
                BusinessProfileRevision.id == revision.id).values(snapshot={"name": "tampered"}))
        db.rollback()
        with pytest.raises(DBAPIError):
            db.execute(update(BusinessOutcomeSnapshot).where(
                BusinessOutcomeSnapshot.id == snapshot.id).values(jobs_created=999))
        db.rollback()
