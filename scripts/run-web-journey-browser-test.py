"""Run applicant-journey acceptance with owned local API/web processes."""

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
    "edp_web_journey_e2e",
}, "An isolated synthetic database is required"
env = dict(os.environ)
env.update(
    APP_ENV="local",
    FILES_ENABLED="false",
    FILES_MAINTENANCE_ENABLED="false",
    AUTH_DELIVERY_KEY=Fernet.generate_key().decode(),
    BFF_KEY=secrets.token_urlsafe(32),
    PYTHONPATH=str(root / "apps/api"),
    PYTHONIOENCODING="utf-8",
    API_INTERNAL_URL="http://127.0.0.1:8104",
    WEB_ORIGIN="http://127.0.0.1:3104",
    COOKIE_SECURE="false",
    HOSTNAME="127.0.0.1",
    PORT="3104",
    PUBLIC_ORGANIZATION_ID=str(uuid4()),
    CONTACT_ENQUIRIES_ENABLED="true",
    CONTACT_PRIVACY_VERSION="v1",
    CONTACT_PRIVACY_NOTICE_URL_EN="/en/pages/privacy",
    CONTACT_PRIVACY_NOTICE_URL_TA="/ta/pages/privacy",
    CONTACT_CONSENT_TEXT_EN="Synthetic local acceptance consent only",
    CONTACT_CONSENT_TEXT_TA="செயற்கை உள்ளூர் சோதனை ஒப்புதல் மட்டும்",
)
for source, destination in (
    ("apps/web/.next/static", "apps/web/.next/standalone/.next/static"),
    ("apps/web/public", "apps/web/.next/standalone/public"),
):
    shutil.copytree(root / source, root / destination, dirs_exist_ok=True)
cache = root / ".tool-cache"
cache.mkdir(exist_ok=True)
for port in (8104, 3104):
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            raise SystemExit(f"Port {port} is in use; refuse to reuse another server")
processes = []
logs = []
hidden = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
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
                "8104",
                "--no-access-log",
            ],
            "http://127.0.0.1:8104/health",
        ),
        (
            "web",
            [shutil.which("node") or "node", "apps/web/.next/standalone/server.js"],
            "http://127.0.0.1:3104/en",
        ),
    ):
        log = (cache / f"web-journey-e2e-{name}.log").open("w", encoding="utf-8")
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
                raise RuntimeError(f"{name} exited; inspect .tool-cache/web-journey-e2e-{name}.log")
            try:
                with urlopen(url, timeout=2) as response:
                    if response.status == 200:
                        break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError(f"{name} did not become ready") from None
                time.sleep(0.25)
    for script in (
        "web-journey-browser-test.py",
        "enquiry-browser-test.py",
        "editorial-browser-test.py",
    ):
        script_log = cache / (script.removesuffix(".py") + ".log")
        with script_log.open("w", encoding="utf-8") as output:
            result = subprocess.run(
                [sys.executable, "-u", "scripts/" + script],
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
                f"{script} exited {result.returncode}; inspect {script_log.relative_to(root)}",
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
