"""Own isolated Communications servers; no Redis, sender or provider is started."""

import hashlib
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen
from uuid import uuid4

from cryptography.fernet import Fernet
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

root = Path(__file__).resolve().parents[1]
target = make_url(os.environ["DATABASE_URL"])
assert target.database == "edp_communications_e2e"
assert target.host in {"127.0.0.1", "localhost"} and target.username == "edp_dev"
assert target.port is not None
for port in (8114, 3114):
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            raise SystemExit(f"Port {port} is in use; refuse to reuse another server")

# Select a currently closed loopback port. This test never starts a broker.
with socket.socket() as reservation:
    reservation.bind(("127.0.0.1", 0))
    unavailable_redis_port = reservation.getsockname()[1]

run_id = uuid4().hex[:8]
cache = root / ".tool-cache"
cache.mkdir(exist_ok=True)
local = root / ".local"
local.mkdir(exist_ok=True)
log_root = cache / f"communications-e2e-{run_id}"
log_root.mkdir()
record_path = local / f"communications-acceptance-{run_id}.json"
build = root / "apps/web/.next/BUILD_ID"
assert build.is_file(), "Build the accepted web source before browser acceptance"
record = {
    "started_at": datetime.now(UTC).isoformat(),
    "synthetic_only": True,
    "database": target.database,
    "ports": [8114, 3114],
    "build_id": build.read_text(encoding="utf-8").strip(),
    "build_sha256": hashlib.sha256(build.read_bytes()).hexdigest(),
    "direct_task_functions": True,
    "broker_worker_beat_acceptance": False,
    "passed": False,
    "logs": str(log_root.relative_to(root)),
}
env = dict(os.environ)
env.update(
    APP_ENV="local",
    FILES_ENABLED="false",
    FILES_MAINTENANCE_ENABLED="false",
    CONTACT_ENQUIRIES_ENABLED="false",
    REDIS_URL=f"redis://127.0.0.1:{unavailable_redis_port}/15",
    BFF_KEY=secrets.token_urlsafe(32),
    AUTH_DELIVERY_KEY=Fernet.generate_key().decode(),
    AUTH_DELIVERY_BACKEND="development",
    AUTH_SMTP_ENABLED="false",
    PARTICIPANT_NOTIFICATION_RETENTION_DAYS="7",
    API_INTERNAL_URL="http://127.0.0.1:8114",
    WEB_ORIGIN="http://127.0.0.1:3114",
    COOKIE_SECURE="false",
    HOSTNAME="127.0.0.1",
    PORT="3114",
    PUBLIC_ORGANIZATION_ID=str(uuid4()),
    PYTHONPATH=str(root / "apps/api"),
    PYTHONIOENCODING="utf-8",
    PYTHONUTF8="1",
    COMMUNICATIONS_BROWSER_RUNNER="synthetic-only",
    COMMUNICATIONS_BROWSER_EVIDENCE=str(
        local / f"communications-browser-{run_id}.json"
    ),
)
hidden = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
processes = []
logs = []
try:
    admin = create_engine(target.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as connection:
            if not connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": "edp_communications_e2e"},
            ):
                connection.execute(text("CREATE DATABASE edp_communications_e2e"))
    finally:
        admin.dispose()

    with (log_root / "migrations.log").open("w", encoding="utf-8") as output:
        migration = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=root / "apps/api",
            env=env,
            stdout=output,
            stderr=subprocess.STDOUT,
            creationflags=hidden,
            check=False,
        )
    if migration.returncode:
        raise RuntimeError(
            "Communications synthetic database migration failed; inspect runner log"
        )

    for source, destination in (
        ("apps/web/.next/static", "apps/web/.next/standalone/.next/static"),
        ("apps/web/public", "apps/web/.next/standalone/public"),
    ):
        shutil.copytree(root / source, root / destination, dirs_exist_ok=True)

    for name, command, url in (
        (
            "api",
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8114",
                "--no-access-log",
            ],
            "http://127.0.0.1:8114/health",
        ),
        (
            "web",
            [shutil.which("node") or "node", "apps/web/.next/standalone/server.js"],
            "http://127.0.0.1:3114/en",
        ),
    ):
        log = (log_root / f"{name}.log").open("w", encoding="utf-8")
        logs.append(log)
        process = subprocess.Popen(
            command,
            cwd=root,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=hidden,
        )
        processes.append(process)
        deadline = time.monotonic() + 40
        while True:
            if process.poll() is not None:
                raise RuntimeError(f"Owned {name} exited; inspect runner log")
            try:
                with urlopen(url, timeout=2) as response:
                    if response.status == 200:
                        break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError(f"Owned {name} did not become ready") from None
                time.sleep(0.25)

    with socket.socket() as probe:
        assert probe.connect_ex(("127.0.0.1", unavailable_redis_port)) != 0
    try:
        urlopen("http://127.0.0.1:8114/ready", timeout=6)
    except HTTPError as response:
        assert response.code == 503
        assert json.load(response) == {"status": "unavailable"}
    else:
        raise AssertionError(
            "Readiness must remain unavailable without the Redis dependency"
        )

    script_log = log_root / "browser.log"
    with script_log.open("w", encoding="utf-8") as output:
        result = subprocess.run(
            [sys.executable, "-u", "scripts/communications-browser-test.py"],
            cwd=root,
            env=env,
            stdout=output,
            stderr=subprocess.STDOUT,
            creationflags=hidden,
            check=False,
        )
    print(script_log.read_text(encoding="utf-8", errors="replace"), end="", flush=True)
    record["exit_code"] = result.returncode
    record["browser_evidence"] = str(
        Path(env["COMMUNICATIONS_BROWSER_EVIDENCE"]).relative_to(root)
    )
    assert build.read_text(encoding="utf-8").strip() == record["build_id"]
    record["passed"] = result.returncode == 0
    if result.returncode:
        raise SystemExit(result.returncode)
finally:
    for process in reversed(processes):
        if process.poll() is not None:
            continue
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=hidden,
                check=False,
            )
        else:
            process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    for log in logs:
        log.close()
    record["owned_servers_cleaned_up"] = all(
        process.poll() is not None for process in processes
    )
    record["finished_at"] = datetime.now(UTC).isoformat()
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(
        f"Communications acceptance evidence: {record_path.relative_to(root)}",
        flush=True,
    )
