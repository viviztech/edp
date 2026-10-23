from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.modules.identity.security import AuthError
from app.workers import files as worker


@pytest.fixture
def queue(monkeypatch):
    policy = SimpleNamespace(
        files_enabled=True,
        files_maintenance_enabled=True,
        files_cleanup_batch_size=2,
        files_scan_lease_seconds=120,
        files_scan_max_attempts=3,
    )
    monkeypatch.setattr(worker, "get_settings", lambda: policy)
    session = MagicMock()
    monkeypatch.setattr(worker, "Session", MagicMock(return_value=session))
    storage, scanner = object(), object()
    storage_factory, scanner_factory = (
        MagicMock(return_value=storage),
        MagicMock(return_value=scanner),
    )
    monkeypatch.setattr(worker, "get_private_storage", storage_factory)
    monkeypatch.setattr(worker, "get_file_scanner", scanner_factory)
    return policy, session.__enter__.return_value, storage_factory, scanner_factory


def test_disabled_poll_and_jobs_do_not_touch_database_or_providers(queue, monkeypatch):
    policy, _, storage, scanner = queue
    policy.files_enabled = policy.files_maintenance_enabled = False
    session = MagicMock(side_effect=AssertionError("database access"))
    monkeypatch.setattr(worker, "Session", session)
    assert worker.queue_due_files.run() == {
        "scans": 0,
        "abandoned": 0,
        "disposals": 0,
        "dispatch_failed": 0,
    }
    for result in (
        worker.scan_file.run(str(uuid4()), str(uuid4())),
        worker.reject_abandoned_file.run(str(uuid4()), str(uuid4()), 1),
        worker.dispose_file.run(str(uuid4()), str(uuid4()), 1),
    ):
        assert result == {"status": "disabled"}
    storage.assert_not_called()
    scanner.assert_not_called()


def test_broker_failure_keeps_database_candidates_recoverable(queue, monkeypatch):
    _, db, _, _ = queue
    org, file_id = uuid4(), uuid4()
    scans = MagicMock(return_value=[(org, file_id)])
    abandoned = MagicMock(return_value=[(org, file_id, 7)])
    disposal = MagicMock(return_value=[(org, file_id, 8)])
    monkeypatch.setattr(worker.service, "scan_candidates", scans)
    monkeypatch.setattr(worker.service, "abandoned_candidates", abandoned)
    monkeypatch.setattr(worker.service, "cleanup_candidates", disposal)
    dispatchers = [
        MagicMock(side_effect=ConnectionError("synthetic broker unavailable")) for _ in range(3)
    ]
    for task, dispatch in zip(
        (worker.scan_file, worker.reject_abandoned_file, worker.dispose_file),
        dispatchers,
        strict=True,
    ):
        monkeypatch.setattr(task, "apply_async", dispatch)
    assert worker.queue_due_files.run()["dispatch_failed"] == 3
    # Dispatch failure does not claim or mutate records. The next poll sees the same IDs.
    assert worker.queue_due_files.run()["dispatch_failed"] == 3
    for candidates in (scans, abandoned, disposal):
        candidates.assert_called_with(db, 2)
        assert candidates.call_count == 2
    db.commit.assert_not_called()
    db.execute.assert_not_called()
    for dispatcher in dispatchers:
        assert dispatcher.call_count == 2
        assert dispatcher.call_args.kwargs["args"][:2] == [str(org), str(file_id)]


def test_scan_uses_fenced_service_claim_and_treats_duplicate_as_skipped(queue, monkeypatch):
    _, db, storage, scanner = queue
    org, identity = uuid4(), uuid4()
    lease = object()
    claim = MagicMock(return_value=lease)
    scan = MagicMock(return_value=SimpleNamespace(state="clean"))
    monkeypatch.setattr(worker.service, "claim_scan", claim)
    monkeypatch.setattr(worker.service, "scan_with_lease", scan)
    assert worker.scan_file.run(str(org), str(identity)) == {"status": "clean"}
    claim.assert_called_once_with(
        db, org, identity, f"file-scan:{identity}", lease_seconds=120, max_attempts=3
    )
    scan.assert_called_once_with(
        db, org, lease, storage.return_value, scanner.return_value, f"file-scan:{identity}", 3
    )
    claim.side_effect = AuthError("file_scan_unavailable", 409)
    assert worker.scan_file.run(str(org), str(identity)) == {"status": "skipped"}
    assert scan.call_count == 1


def test_maintenance_runs_with_collection_disabled_and_preserves_service_holds(queue, monkeypatch):
    policy, db, storage, scanner = queue
    policy.files_enabled = False
    org, identity = uuid4(), uuid4()
    abandon = MagicMock(return_value=SimpleNamespace(state="rejected"))
    cleanup = MagicMock(side_effect=AuthError("file_disposal_denied", 409))
    monkeypatch.setattr(worker.service, "reject_abandoned", abandon)
    monkeypatch.setattr(worker.service, "cleanup_file", cleanup)
    assert worker.reject_abandoned_file.run(str(org), str(identity), 8) == {"status": "rejected"}
    abandon.assert_called_once_with(
        db, org, identity, 8, f"file-abandoned:{identity}", storage=storage.return_value
    )
    assert worker.dispose_file.run(str(org), str(identity), 9) == {"status": "skipped"}
    cleanup.assert_called_once_with(
        db, org, identity, 9, storage.return_value, f"file-dispose:{identity}"
    )
    storage.assert_called_with(policy, allow_disabled=True)
    scanner.assert_not_called()


def test_provider_or_worker_interruption_never_reports_clean(queue, monkeypatch):
    _, _, storage, _ = queue
    storage.side_effect = AuthError("file_runtime_unavailable", 503)
    assert worker.scan_file.run(str(uuid4()), str(uuid4())) == {"status": "unavailable"}
    storage.side_effect = RuntimeError("synthetic private details")
    assert worker.scan_file.run(str(uuid4()), str(uuid4())) == {"status": "interrupted"}
