"""Own isolated synthetic PostgreSQL/API/Flutter M05 acceptance; no providers."""

import hashlib
import importlib.util
import json
import os
import secrets
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import ProxyHandler, build_opener
from uuid import uuid4

from cryptography.fernet import Fernet
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    root = Path(__file__).resolve().parents[1]
    credentials = json.loads(
        (root / ".local/postgres17/credentials.json").read_text(encoding="utf-8-sig")
    )
    target = URL.create(
        "postgresql+psycopg",
        username=credentials["user"],
        password=credentials["password"],
        host=credentials["host"],
        port=int(credentials["port"]),
        database="edp_mobile_alumni_e2e",
    )
    require(
        target.host in {"localhost", "127.0.0.1"} and target.username == "edp_dev",
        "Refuse non-local synthetic database",
    )
    port = 8217
    with socket.socket() as probe:
        require(
            probe.connect_ex(("127.0.0.1", port)) != 0, "Owned alumni port is occupied"
        )
    run_id = uuid4().hex[:8]
    folder = root / ".tool-cache" / f"mobile-api-alumni-{run_id}"
    folder.mkdir()
    fixture_path = folder / "fixture.json"
    record_path = root / ".local" / f"mobile-api-alumni-{run_id}.json"
    hidden = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    env = dict(os.environ)
    env.update(
        DATABASE_URL=target.render_as_string(hide_password=False),
        APP_ENV="local",
        AUTH_DELIVERY_BACKEND="development",
        AUTH_SMTP_ENABLED="false",
        AUTH_TEMPLATES_APPROVED="false",
        AUTH_DELIVERY_KEY=Fernet.generate_key().decode(),
        BFF_KEY=secrets.token_urlsafe(32),
        FILES_ENABLED="false",
        FILES_MAINTENANCE_ENABLED="false",
        CONTACT_ENQUIRIES_ENABLED="false",
        PARTICIPANT_NOTIFICATION_RETENTION_DAYS="7",
        REDIS_URL="redis://127.0.0.1:1/15",
        PYTHONPATH=str(root / "apps/api"),
        PYTHONUTF8="1",
        PYTHONIOENCODING="utf-8",
        PUB_CACHE=str(root / ".tool-cache/pub"),
    )
    record = {
        "synthetic_only": True,
        "database": target.database,
        "native_device_acceptance": False,
        "providers_enabled": False,
        "passed": False,
        "started_at": datetime.now(UTC).isoformat(),
        "openapi_sha256": hashlib.sha256(
            (root / "packages/api-contracts/openapi.json").read_bytes()
        ).hexdigest(),
    }
    server = flutter_process = api_output = None
    spec = importlib.util.spec_from_file_location(
        "mobile_runner_shared", root / "scripts/run-mobile-api-tests.py"
    )
    shared = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shared)
    try:
        admin = create_engine(
            target.set(database="postgres"), isolation_level="AUTOCOMMIT"
        )
        try:
            with admin.connect() as connection:
                if not connection.scalar(
                    text("SELECT 1 FROM pg_database WHERE datname=:name"),
                    {"name": target.database},
                ):
                    connection.execute(text("CREATE DATABASE edp_mobile_alumni_e2e"))
        finally:
            admin.dispose()
        with (folder / "migration.log").open("w", encoding="utf-8") as log:
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=root / "apps/api",
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=hidden,
                timeout=120,
                check=False,
            )
            require(result.returncode == 0, "Synthetic migration failed")
        os.environ.update(env)
        sys.path.insert(0, str(root / "apps/api"))
        sys.path.insert(0, str(root / "apps/api/tests"))
        from app.modules.identity.models import (
            Organization,
            Person,
            Role,
            User,
            UserRole,
        )
        from app.modules.identity.security import hasher
        from app.modules.identity.service import seed_roles
        from app.modules.programs.models import Enrollment, Participant
        from app.modules.reports import service as impact
        from app.modules.reports.schemas import (
            ImpactDefinitionCommand,
            ImpactDefinitionCreate,
        )
        from app.workers import participant_notifications
        from participant_notification_fixtures import create_enrollment

        engine = create_engine(target)
        fixture = {
            "synthetic_only": True,
            "api_base": f"http://127.0.0.1:{port}/api/v1",
            "accounts": {},
            "enrollments": {},
        }
        try:
            with Session(engine) as db:
                seed_roles(db)
                primary, other = (
                    Organization(name=f"Synthetic alumni {run_id}"),
                    Organization(name=f"Synthetic other alumni {run_id}"),
                )
                db.add_all([primary, other])
                db.flush()
                fixture.update(
                    organization_id=str(primary.id), other_organization_id=str(other.id)
                )
                users = {}
                for name in ["director", "owner", "alumnus", "peer", "outsider"]:
                    person = Person(
                        display_name=f"Synthetic alumni {name}",
                        locale="ta" if name == "owner" else "en",
                    )
                    db.add(person)
                    db.flush()
                    password = secrets.token_urlsafe(24)
                    user = User(
                        person_id=person.id,
                        email=f"alumni-{run_id}-{name}@example.com",
                        password_hash=hasher.hash(password),
                        status="active",
                    )
                    db.add(user)
                    db.flush()
                    users[name] = user
                    fixture["accounts"][name] = {
                        "email": user.email,
                        "password": password,
                        "user_id": str(user.id),
                    }
                role = db.scalar(select(Role).where(Role.name == "Super Admin"))
                for org in [primary, other]:
                    db.add(
                        UserRole(
                            user_id=users["director"].id,
                            role_id=role.id,
                            organization_id=org.id,
                        )
                    )
                db.commit()
                for name, count, org in [
                    ("owner", 26, primary),
                    ("alumnus", 1, primary),
                    ("peer", 1, primary),
                    ("outsider", 1, other),
                ]:
                    for index in range(count):
                        conversion = create_enrollment(
                            db,
                            org.id,
                            users["director"],
                            users[name],
                            f"alumni-{run_id}-{name}-{index}",
                        )
                        if index == 0:
                            fixture["enrollments"][name] = str(conversion.enrollment.id)
                        if name == "alumnus":
                            db.get(
                                Enrollment, conversion.enrollment.id
                            ).status = "completed"
                            db.get(
                                Participant, conversion.participant.id
                            ).status = "completed"
                            db.commit()
                for index in range(27):
                    definition = impact.create_definition(
                        db,
                        primary.id,
                        users["director"],
                        ImpactDefinitionCreate(
                            title_en=f"Synthetic self report {index}",
                            title_ta=f"சோதனை சுய அறிக்கை {index}",
                            definition_en="Synthetic participant reported business and jobs observations.",
                            definition_ta="சோதனை பங்கேற்பாளர் தெரிவித்த தொழில் மற்றும் வேலைக் கவனிப்புகள்.",
                            reason="Synthetic mobile acceptance",
                        ),
                        "synthetic-alumni-definition",
                    )
                    impact.command_definition(
                        db,
                        primary.id,
                        definition.id,
                        users["director"],
                        ImpactDefinitionCommand(
                            expected_version=definition.version,
                            reason="Synthetic publication only",
                        ),
                        "published",
                        "synthetic-alumni-publication",
                    )
            participant_notifications.engine = engine
            dispatched = 0
            for _ in range(20):
                consumed = participant_notifications.consume_outbox.run()
                require(
                    isinstance(consumed.get("dispatched"), int),
                    "Synthetic outbox failed",
                )
                dispatched += consumed["dispatched"]
                if dispatched >= 29:
                    break
            require(
                dispatched >= 29,
                "Synthetic enrollment inbox consumption failed",
            )
        finally:
            engine.dispose()
        fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
        fixture_path.chmod(0o600)
        api_output = (folder / "api.log").open("w", encoding="utf-8")
        server = subprocess.Popen(
            [
                sys.executable,
                "scripts/run-native-api.py",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=root,
            env=env,
            stdout=api_output,
            stderr=subprocess.STDOUT,
            creationflags=hidden,
            start_new_session=os.name != "nt",
        )
        deadline = time.monotonic() + 45
        http = build_opener(ProxyHandler({}))
        while True:
            require(
                server.poll() is None and time.monotonic() < deadline,
                "Owned API startup failed",
            )
            try:
                with http.open(
                    f"http://127.0.0.1:{port}/health", timeout=2
                ) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(0.2)
        with (folder / "flutter.log").open("w", encoding="utf-8") as log:
            flutter_process = subprocess.Popen(
                [
                    "cmd.exe",
                    "/d",
                    "/c",
                    str(root / ".tool-cache/flutter/bin/flutter.bat"),
                    "test",
                    "--no-pub",
                    "--reporter",
                    "expanded",
                    "test/live_api/alumni_acceptance_test.dart",
                    f"--dart-define=MOBILE_ACCEPTANCE_FIXTURE={fixture_path}",
                    "--dart-define=MOBILE_ACCEPTANCE_SYNTHETIC_ONLY=true",
                ],
                cwd=root / "apps/mobile",
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=hidden,
                start_new_session=os.name != "nt",
            )
            exit_code = flutter_process.wait(timeout=360)
        record.update(passed=exit_code == 0, exit_code=exit_code)
        print(
            f"M05 Flutter/API acceptance exit {exit_code}; evidence {folder.relative_to(root)}",
            flush=True,
        )
        return exit_code
    finally:
        shared.stop_owned(flutter_process, hidden)
        shared.stop_owned(server, hidden)
        if api_output:
            api_output.close()
        fixture_path.unlink(missing_ok=True)
        record.update(
            fixture_removed=not fixture_path.exists(),
            owned_api_stopped=server is None or server.poll() is not None,
            owned_flutter_stopped=flutter_process is None
            or flutter_process.poll() is not None,
            finished_at=datetime.now(UTC).isoformat(),
        )
        record_path.write_text(json.dumps(record, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
