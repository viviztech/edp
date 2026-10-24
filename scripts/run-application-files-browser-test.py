"""Isolated synthetic application-document acceptance, with local test bytes only."""

import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen
from uuid import uuid4

from cryptography.fernet import Fernet
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

root = Path(__file__).resolve().parents[1]
target = make_url(os.environ["DATABASE_URL"])
assert target.database == "edp_application_files_e2e"
assert target.host in {"127.0.0.1", "localhost"}
assert target.username == "edp_dev"
private = root / ".tool-cache" / ("application-files-private-" + uuid4().hex)
assert private.resolve().is_relative_to((root / ".tool-cache").resolve())
(private / "temp").mkdir(mode=0o700, parents=True)
env = dict(os.environ)
env.update(
    APP_ENV="local",
    FILES_ENABLED="true",
    FILES_MAINTENANCE_ENABLED="false",
    FILES_STORAGE_BACKEND="local",
    FILES_LOCAL_ROOT=str(private / "objects"),
    FILES_TEMP_ROOT=str(private / "temp"),
    FILES_MAX_BYTES="2048",
    BFF_KEY=secrets.token_urlsafe(32),
    AUTH_DELIVERY_KEY=Fernet.generate_key().decode(),
    API_INTERNAL_URL="http://127.0.0.1:8108",
    WEB_ORIGIN="http://127.0.0.1:3108",
    COOKIE_SECURE="false",
    HOSTNAME="127.0.0.1",
    PORT="3108",
    PUBLIC_ORGANIZATION_ID=str(uuid4()),
    PYTHONPATH=str(root / "apps/api"),
    PYTHONIOENCODING="utf-8",
    PYTHONUTF8="1",
)
# This runner never contacts a scanner provider. Its child explicitly supplies a
# controlled test scanner to the service for these synthetic bytes only.
env.pop("CLAMAV_HOST", None)
hidden = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
for port in (8108, 3108):
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            raise SystemExit(f"Port {port} is in use; refuse to reuse another server")

# The database identifier is a fixed guarded name, never caller-built SQL.
admin = create_engine(target.set(database="postgres"), isolation_level="AUTOCOMMIT")
try:
    with admin.connect() as connection:
        if not connection.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": "edp_application_files_e2e"},
        ):
            connection.execute(text("CREATE DATABASE edp_application_files_e2e"))
finally:
    admin.dispose()

cache = root / ".tool-cache"
cache.mkdir(exist_ok=True)
with (cache / "application-files-e2e-migrations.log").open("w", encoding="utf-8") as output:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=root / "apps/api",
        env=env,
        stdout=output,
        stderr=subprocess.STDOUT,
        creationflags=hidden,
        check=False,
    )
if result.returncode:
    raise SystemExit(
        "Application database migration failed; "
        "inspect .tool-cache/application-files-e2e-migrations.log"
    )
for source, destination in (
    ("apps/web/.next/static", "apps/web/.next/standalone/.next/static"),
    ("apps/web/public", "apps/web/.next/standalone/public"),
):
    shutil.copytree(root / source, root / destination, dirs_exist_ok=True)

processes = []
logs = []
try:
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
                "8108",
                "--no-access-log",
            ],
            "http://127.0.0.1:8108/health",
        ),
        (
            "web",
            [shutil.which("node") or "node", "apps/web/.next/standalone/server.js"],
            "http://127.0.0.1:3108/en",
        ),
    ):
        log = (cache / f"application-files-e2e-{name}.log").open("w", encoding="utf-8")
        logs.append(log)
        process = subprocess.Popen(
            command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT, creationflags=hidden
        )
        processes.append(process)
        deadline = time.monotonic() + 40
        while True:
            if process.poll() is not None:
                raise RuntimeError(
                    f"{name} exited; inspect .tool-cache/application-files-e2e-{name}.log"
                )
            try:
                with urlopen(url, timeout=2) as response:
                    if response.status == 200:
                        break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError(f"{name} did not become ready") from None
                time.sleep(0.25)
    script_log = cache / "application-files-browser-test.log"
    with script_log.open("w", encoding="utf-8") as output:
        result = subprocess.run(
            [sys.executable, "-u", "scripts/application-files-browser-test.py"],
            cwd=root,
            env=env,
            stdout=output,
            stderr=subprocess.STDOUT,
            check=False,
            creationflags=hidden,
        )
    captured = script_log.read_text(encoding="utf-8", errors="replace")
    if captured:
        print(captured, end="" if captured.endswith("\n") else "\n", flush=True)
    if result.returncode:
        print(
            f"Application file browser test exited {result.returncode}; "
            f"inspect {script_log.relative_to(root)}",
            file=sys.stderr,
            flush=True,
        )
        raise SystemExit(result.returncode)
finally:
    for process in reversed(processes):
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                creationflags=hidden,
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
