import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.notifications.participant_schemas import (
    ParticipantMarkRead,
    ParticipantPreferenceEdit,
)
from app.modules.notifications.participant_service import enrollment_payload
from app.modules.programs.models import DomainOutbox


def event(payload=None):
    enrollment, application, participant = uuid4(), uuid4(), uuid4()
    return DomainOutbox(
        event_key=f"enrollment.created:{enrollment}",
        event_type="enrollment.created",
        aggregate_type="enrollment",
        aggregate_id=enrollment,
        organization_id=uuid4(),
        payload=payload
        or json.dumps(
            {
                "enrollment_id": str(enrollment),
                "application_id": str(application),
                "participant_id": str(participant),
            }
        ),
    )


def test_enrollment_contract_rejects_extra_duplicate_mismatched_and_nonuuid_fields():
    row = event()
    parsed = enrollment_payload(row)
    assert parsed and parsed.enrollment_id == row.aggregate_id
    original = row.payload
    row.payload = original[:-1] + ',"recipient_user_id":"' + str(uuid4()) + '"}'
    assert enrollment_payload(row) is None
    row.payload = original[:-1] + ',"enrollment_id":"' + str(row.aggregate_id) + '"}'
    assert enrollment_payload(row) is None
    row.payload = original.replace(str(row.aggregate_id), "invalid")
    assert enrollment_payload(row) is None
    row.payload = original
    row.aggregate_id = uuid4()
    assert enrollment_payload(row) is None


def test_mutations_reject_arbitrary_links_extra_fields_and_invalid_versions():
    with pytest.raises(ValidationError):
        ParticipantPreferenceEdit.model_validate(
            {"enabled": True, "expected_version": 0, "destination": "https://example.test"}
        )
    with pytest.raises(ValidationError):
        ParticipantMarkRead(expected_version=0)
