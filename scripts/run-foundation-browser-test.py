"""Run synthetic local browser acceptance with owned, temporary API/web processes."""

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
material_root = root / ".tool-cache/lms-e2e"
material_file = material_root / "private/e2e/customer-worksheet.pdf"
material_file.parent.mkdir(parents=True, exist_ok=True)
material_file.write_bytes(b"%PDF-1.4 synthetic browser material")
assert make_url(os.environ["DATABASE_URL"]).database in {
    "edp_foundation_e2e",
    "edp_test",
}
env = dict(os.environ)
env.update(
    APP_ENV="local",
    AUTH_DELIVERY_KEY=Fernet.generate_key().decode(),
    BFF_KEY=secrets.token_urlsafe(32),
    PYTHONPATH=str(root / "apps/api"),
    API_INTERNAL_URL="http://127.0.0.1:8100",
    WEB_ORIGIN="http://127.0.0.1:3100",
    COOKIE_SECURE="false",
    HOSTNAME="127.0.0.1",
    PORT="3100",
    PUBLIC_ORGANIZATION_ID=str(uuid4()),
    LMS_MATERIAL_ROOT=str(material_root),
    LMS_MATERIAL_SIGNING_KEY=secrets.token_urlsafe(32),
)
shutil.copytree(
    root / "apps/web/.next/static",
    root / "apps/web/.next/standalone/.next/static",
    dirs_exist_ok=True,
)
shutil.copytree(
    root / "apps/web/public",
    root / "apps/web/.next/standalone/public",
    dirs_exist_ok=True,
)
cache = root / ".tool-cache"
cache.mkdir(exist_ok=True)
for port in (8100, 3100):
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            raise SystemExit(
                f"Port {port} is already in use; refuse to reuse another server"
            )
processes = []
logs = []
try:
    for name, command, url in [
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
                "8100",
                "--no-access-log",
            ],
            "http://127.0.0.1:8100/health",
        ),
        (
            "web",
            [shutil.which("node") or "node", "apps/web/.next/standalone/server.js"],
            "http://127.0.0.1:3100/en",
        ),
    ]:
        log = (cache / ("auth-e2e-" + name + ".log")).open("w", encoding="utf-8")
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
                raise RuntimeError(name + " exited; inspect .tool-cache log")
            try:
                with urlopen(url, timeout=2) as response:
                    if response.status == 200:
                        break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError(name + " did not become ready") from None
                time.sleep(0.25)
    result = subprocess.run(
        [sys.executable, "scripts/foundation-browser-test.py"],
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
