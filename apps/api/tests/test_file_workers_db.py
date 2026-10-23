import hashlib
import os
from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session
from test_file_foundation_db import PDF, context, files_db, upload  # noqa: F401
from test_identity import auth  # noqa: F401

from app.modules.files import service
from app.modules.files.scanner import ScanResult
from app.modules.identity.models import User
from app.workers import files as worker

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)


def test_worker_scan_duplicate_hold_and_expiry_use_real_lifecycle(request, monkeypatch):
    f = request.getfixturevalue("files_db")
    calls = []

    class Scanner:
        def scan(self, source, *, max_bytes):
            data = source.read(max_bytes + 1)
            calls.append(data)
            return ScanResult("clean", hashlib.sha256(data).hexdigest(), len(data), "clean")

    monkeypatch.setattr(worker, "engine", f["engine"])
    monkeypatch.setattr(worker, "get_private_storage", lambda *args, **kwargs: f["storage"])
    monkeypatch.setattr(worker, "get_file_scanner", lambda *args: Scanner())
    monkeypatch.setattr(
        worker,
        "get_settings",
        lambda: SimpleNamespace(
            files_enabled=True,
            files_maintenance_enabled=True,
            files_scan_lease_seconds=120,
            files_scan_max_attempts=3,
        ),
    )
    with Session(f["engine"]) as db:
        actor = db.get(User, f["owner"])
        ctx = context(actor, f["org"])
        # Use already expired synthetic retention so the database's own clock
        # independently permits disposal; a Python-only clock shift cannot do so.
        item = upload(db, f, actor, ctx, created_at=f["clock"][0] - timedelta(days=3))
        file_id, org = str(item.id), str(f["org"])
        assert worker.scan_file.run(org, file_id) == {"status": "clean"}
        assert worker.scan_file.run(org, file_id) == {"status": "skipped"}
        assert calls == [PDF]
        db.expire_all()
        item = service.get_file(db, ctx, actor, item.id)
        item = service.set_legal_hold(db, ctx, actor, item.id, item.version, True, "hold")
        assert worker.dispose_file.run(org, file_id, item.version) == {"status": "skipped"}
        item = service.set_legal_hold(db, ctx, actor, item.id, item.version, False, "release")
        assert worker.dispose_file.run(org, file_id, item.version) == {"status": "deleted"}
        db.expire_all()
        assert service.get_file(db, ctx, actor, item.id).state == "deleted"
