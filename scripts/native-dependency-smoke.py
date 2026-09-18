"""Read-only API probe against explicitly configured local PostgreSQL/Redis."""
import asyncio
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "apps/api"))
from fastapi.testclient import TestClient
from app.main import app

options = {"loop_factory": asyncio.SelectorEventLoop} if sys.platform == "win32" else {}
with TestClient(app, backend_options=options) as client:
    for path, expected in [("health", "ok"), ("ready", "ready")]:
        response = client.get("/" + path)
        assert response.status_code == 200, response.text
        assert response.json() == {"status": expected}
print("Live PostgreSQL/Redis dependency probes passed; not a Compose or queue test")
