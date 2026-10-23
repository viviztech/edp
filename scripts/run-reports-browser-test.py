"""Run I01 acceptance against owned local servers and an isolated synthetic database."""

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
from sqlalchemy.engine import make_url

root = Path(__file__).resolve().parents[1]
assert make_url(os.environ["DATABASE_URL"]).database in {
    "edp_foundation_e2e",
    "edp_reports_e2e",
}, "An isolated synthetic database is required"
env = dict(os.environ)
env.update(
    APP_ENV="local",
    AUTH_DELIVERY_KEY=Fernet.generate_key().decode(),
    BFF_KEY=secrets.token_urlsafe(32),
    PYTHONPATH=str(root / "apps/api"),
    API_INTERNAL_URL="http://127.0.0.1:8103",
    WEB_ORIGIN="http://127.0.0.1:3103",
    COOKIE_SECURE="false",
    HOSTNAME="127.0.0.1",
    PORT="3103",
    PUBLIC_ORGANIZATION_ID=str(uuid4()),
)
for source, destination in (
    ("apps/web/.next/static", "apps/web/.next/standalone/.next/static"),
    ("apps/web/public", "apps/web/.next/standalone/public"),
):
    shutil.copytree(root / source, root / destination, dirs_exist_ok=True)
cache = root / ".tool-cache"
cache.mkdir(exist_ok=True)
for port in (8103, 3103):
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            raise SystemExit(f"Port {port} is in use; refuse to reuse another server")
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
                "8103",
                "--no-access-log",
            ],
            "http://127.0.0.1:8103/health",
        ),
        (
            "web",
            [shutil.which("node") or "node", "apps/web/.next/standalone/server.js"],
            "http://127.0.0.1:3103/en",
        ),
    ):
        log = (cache / f"reports-e2e-{name}.log").open("w", encoding="utf-8")
        logs.append(log)
        process = subprocess.Popen(
            command,
            cwd=root,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        processes.append(process)
        deadline = time.monotonic() + 40
        while True:
            if process.poll() is not None:
                raise RuntimeError(
                    f"{name} exited; inspect .tool-cache/reports-e2e-{name}.log"
                )
            try:
                with urlopen(url, timeout=2) as response:
                    if response.status == 200:
                        break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError(f"{name} did not become ready") from None
                time.sleep(0.25)
    result = subprocess.run(
        [sys.executable, "scripts/reports-browser-test.py"],
        cwd=root,
        env=env,
        check=False,
    )
    if result.returncode:
        raise SystemExit(result.returncode)
finally:
    for process in reversed(processes):
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
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
