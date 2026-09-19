from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from app.modules.crm import service
from app.modules.crm.models import Lead, LeadConversion
from app.modules.crm.schemas import LeadConversionCreate


def test_registration_link_preserves_attribution_and_does_not_mark_converted(monkeypatch) -> None:
    org, lead_id, person_id, actor_id = uuid4(), uuid4(), uuid4(), uuid4()
    lead = Lead(
        id=lead_id,
        organization_id=org,
        name="Synthetic lead",
        email="lead@example.test",
        phone="",
        source="campaign-form",
        campaign="cohort-1",
        dedupe_hash="a" * 64,
        status="interested",
        version=3,
        notes="",
    )
    db = MagicMock()
    db.scalar.side_effect = [lead, None]
    db.get.return_value = object()
    monkeypatch.setattr(service, "require_permission", MagicMock())
    marker = object()
    monkeypatch.setattr(service, "conversion_view", lambda _: marker)
    result = service.link_registration(
        db,
        org,
        lead_id,
        SimpleNamespace(id=actor_id),
        LeadConversionCreate(
            person_id=person_id, expected_version=3, reason="Verified registration identity"
        ),
        "request-id",
    )
    link = db.add.call_args_list[0].args[0]
    assert isinstance(link, LeadConversion)
    assert link.source == "campaign-form"
    assert link.campaign == "cohort-1"
    assert link.person_id == person_id
    assert lead.status == "registration_started"
    assert lead.version == 4
    assert result is marker
