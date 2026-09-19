from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.modules.crm import service
from app.modules.crm.models import LeadActivity
from app.modules.crm.schemas import ActivityComplete
from app.modules.identity.security import AuthError


def test_tag_name_normalization_is_case_and_whitespace_insensitive() -> None:
    assert service.normalize_tag_name("  High   Intent  ") == "high intent"


def test_activity_completion_is_versioned_and_audited(monkeypatch) -> None:
    org, lead_id, activity_id, actor_id = uuid4(), uuid4(), uuid4(), uuid4()
    activity = LeadActivity(
        id=activity_id,
        organization_id=org,
        lead_id=lead_id,
        actor_user_id=actor_id,
        activity_type="task",
        note="Call tomorrow",
        version=2,
    )
    db = MagicMock()
    db.scalar.return_value = activity
    monkeypatch.setattr(service, "require_permission", MagicMock())

    result = service.complete_activity(
        db,
        org,
        lead_id,
        activity_id,
        SimpleNamespace(id=actor_id),
        ActivityComplete(expected_version=2),
        "request-id",
    )

    assert result.completed_at is not None
    assert result.version == 3
    db.commit.assert_called_once()


def test_activity_completion_rejects_stale_version(monkeypatch) -> None:
    activity = LeadActivity(
        id=uuid4(),
        organization_id=uuid4(),
        lead_id=uuid4(),
        actor_user_id=uuid4(),
        activity_type="task",
        note="Call tomorrow",
        version=3,
    )
    db = MagicMock()
    db.scalar.return_value = activity
    monkeypatch.setattr(service, "require_permission", MagicMock())

    with pytest.raises(AuthError) as error:
        service.complete_activity(
            db,
            activity.organization_id,
            activity.lead_id,
            activity.id,
            SimpleNamespace(id=activity.actor_user_id),
            ActivityComplete(expected_version=2),
            "request-id",
        )

    assert error.value.status == 409
    db.commit.assert_not_called()
