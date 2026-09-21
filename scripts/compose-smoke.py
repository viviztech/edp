"""Non-destructive local stack probes; Docker Compose must already be running."""

import json
import subprocess
from urllib.request import urlopen

for path, expected in [("health", "ok"), ("ready", "ready")]:
    with urlopen(f"http://localhost:8000/{path}", timeout=6) as response:
        assert json.load(response) == {"status": expected}
with urlopen("http://127.0.0.1:3001/en", timeout=10) as response:
    assert response.status == 200
worker_code = (
    "from app.workers.celery_app import celery_app; "
    "assert celery_app.send_task('edp.probe').get(timeout=20) == {'status':'ok'}"
)
subprocess.run(
    [
        "docker",
        "compose",
        "exec",
        "-T",
        "worker",
        "python",
        "-c",
        worker_code,
    ],
    check=True,
)
print("API, web and worker queue round-trip passed")
