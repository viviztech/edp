"""Own synthetic loopback API fixtures for Flutter repository/API acceptance.

This is not Android/iOS, secure-storage plugin, file-provider or camera evidence.
No broker, sender or external provider is enabled. The documents slice enables
only per-run synthetic collection and an explicitly controlled test scanner.
"""

import argparse
import hashlib
import importlib.util
import json
import os
import secrets
import signal
import socket
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import ProxyHandler, build_opener
from uuid import UUID, uuid4

from cryptography.fernet import Fernet
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def synthetic_database(root: Path) -> URL:
    """Read local credentials internally; never print/render them for evidence."""
    configured = os.environ.get("DATABASE_URL")
    if configured:
        target = make_url(configured)
    else:
        credentials = json.loads(
            (root / ".local/postgres17/credentials.json").read_text(
                encoding="utf-8-sig"
            )
        )
        target = URL.create(
            "postgresql+psycopg",
            username=credentials["user"],
            password=credentials["password"],
            host=credentials["host"],
            port=int(credentials["port"]),
            database="edp_mobile_e2e",
        )
    require(
        target.drivername == "postgresql+psycopg",
        "Unsupported synthetic database driver",
    )
    require(
        target.database == "edp_mobile_e2e", "Refuse a non-mobile acceptance database"
    )
    require(
        target.host in {"127.0.0.1", "localhost"} and target.username == "edp_dev",
        "Refuse a non-local synthetic database identity",
    )
    require(
        target.port is not None and 0 < target.port < 65536,
        "Explicit database port required",
    )
    return target


def stop_owned(process: subprocess.Popen[bytes] | None, hidden: int) -> None:
    """Only terminate the process/tree started and retained by this invocation."""
    if process is None or process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=hidden,
            check=False,
            timeout=10,
        )
    else:
        os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            process.kill()
        else:
            os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--slice",
        choices=["m00", "applicant", "documents", "learning", "support", "alumni"],
        default="m00",
    )
    args = parser.parse_args()
    file_slice = args.slice in {"documents", "learning", "support"}
    root = Path(__file__).resolve().parents[1]
    if args.slice == "alumni":
        return subprocess.call(
            [sys.executable, str(root / "scripts/run-mobile-alumni-tests.py")], cwd=root
        )
    target = synthetic_database(root)
    with socket.socket() as probe:
        require(
            probe.connect_ex(("127.0.0.1", 8115)) != 0,
            "Owned mobile acceptance port is occupied",
        )
    flutter = root / ".tool-cache/flutter/bin/flutter.bat"
    require(flutter.is_file(), "Use the supported existing project Flutter SDK")
    test_path = f"test/live_api/{args.slice}_test.dart"
    require(
        (root / "apps/mobile" / test_path).is_file(),
        "Selected acceptance test must exist",
    )
    run_id = uuid4().hex[:8]
    folder = root / ".tool-cache" / f"mobile-api-{args.slice}-{run_id}"
    folder.mkdir(parents=True)
    local = root / ".local"
    local.mkdir(exist_ok=True)
    record_path = local / f"mobile-api-{args.slice}-{run_id}.json"
    fixture_path = folder / "fixture.json"
    record = {
        "started_at": datetime.now(UTC).isoformat(),
        "slice": args.slice,
        "database": target.database,
        "synthetic_only": True,
        "passed": False,
        "native_device_acceptance": False,
        "secure_storage_plugin_acceptance": False,
        "broker_worker_beat_acceptance": False,
        "direct_task_functions": True,
        "synthetic_file_collection": file_slice,
        "real_scanner_acceptance": False,
        "openapi_sha256": hashlib.sha256(
            (root / "packages/api-contracts/openapi.json").read_bytes()
        ).hexdigest(),
        "logs": str(folder.relative_to(root)),
    }
    # This runner never starts a broker; avoid accidentally using a local service.
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        unavailable_redis_port = reservation.getsockname()[1]
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
        REDIS_URL=f"redis://127.0.0.1:{unavailable_redis_port}/15",
        PYTHONPATH=str(root / "apps/api"),
        PYTHONUTF8="1",
        PYTHONIOENCODING="utf-8",
        PUB_CACHE=str(root / ".tool-cache/pub"),
    )
    if file_slice:
        # These paths and this database belong only to the owned synthetic run.
        private_temp = folder / "private-temp"
        private_temp.mkdir(mode=0o700)
        env.update(
            FILES_ENABLED="true",
            FILES_STORAGE_BACKEND="local",
            FILES_LOCAL_ROOT=str(folder / "private-objects"),
            FILES_TEMP_ROOT=str(private_temp),
            FILES_MAX_BYTES="1024",
        )
    hidden = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    server = None
    flutter_process = None
    verification_stop = threading.Event()
    verification_thread = None
    scan_thread = None
    verification_path = folder / "verification.json"
    output = None
    exit_code = 1
    try:
        admin = create_engine(
            target.set(database="postgres"),
            isolation_level="AUTOCOMMIT",
            connect_args={"connect_timeout": 3},
        )
        try:
            with admin.connect() as connection:
                if not connection.scalar(
                    text("SELECT 1 FROM pg_database WHERE datname=:name"),
                    {"name": target.database},
                ):
                    connection.execute(text("CREATE DATABASE edp_mobile_e2e"))
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
                check=False,
                timeout=120,
            )
        require(result.returncode == 0, "Owned synthetic database migration failed")

        # Import only after the guarded local environment is established. The
        # production API has no test endpoint or memory-token-store fallback.
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
        from app.modules.notifications.participant_models import ParticipantNotice
        from app.workers import participant_notifications
        from participant_notification_fixtures import create_enrollment

        engine = create_engine(target, connect_args={"connect_timeout": 3})
        accounts = {}
        try:
            with Session(engine) as db:
                seed_roles(db)
                organizations = [
                    Organization(name=f"Synthetic mobile {run_id} {name}")
                    for name in ("primary", "other")
                ]
                db.add_all(organizations)
                db.flush()
                org, other_org = organizations[0].id, organizations[1].id
                roles = {
                    name: db.scalar(select(Role).where(Role.name == name))
                    for name in ("Super Admin", "CRM Executive")
                }
                require(all(roles.values()), "Synthetic role catalog unavailable")
                users = {}
                for name in ("director", "owner", "peer", "outsider", "applicant"):
                    person = Person(
                        display_name=f"Synthetic mobile {name}",
                        locale="ta" if name == "owner" else "en",
                    )
                    db.add(person)
                    db.flush()
                    password = secrets.token_urlsafe(24)
                    user = User(
                        person_id=person.id,
                        email=f"mobile-{name}-{run_id}@example.com",
                        password_hash=hasher.hash(password),
                        status="active",
                    )
                    db.add(user)
                    db.flush()
                    users[name] = user
                    accounts[name] = {
                        "email": user.email,
                        "password": password,
                        "user_id": str(user.id),
                    }
                for organization in organizations:
                    db.add(
                        UserRole(
                            user_id=users["director"].id,
                            role_id=roles["Super Admin"].id,
                            organization_id=organization.id,
                        )
                    )
                if args.slice == "support":
                    mentor = db.scalar(select(Role).where(Role.name == "Mentor"))
                    require(mentor is not None, "Synthetic mentor role unavailable")
                    db.add(
                        UserRole(
                            user_id=users["director"].id,
                            role_id=mentor.id,
                            organization_id=org,
                        )
                    )
                db.commit()
                conversions = {}
                for name, organization in (
                    ("owner", org),
                    ("peer", org),
                    ("outsider", other_org),
                ):
                    conversion = create_enrollment(
                        db,
                        organization,
                        users["director"],
                        users[name],
                        f"mobile-{run_id}-{name}",
                    )
                    conversions[name] = {
                        "enrollment_id": str(conversion.enrollment.id),
                        "participant_id": str(conversion.participant.id),
                        "application_id": str(conversion.enrollment.application_id),
                        "program_id": str(conversion.enrollment.program_id),
                        "cohort_id": str(conversion.enrollment.cohort_id),
                    }
                # A permission in a second organization must not create a
                # participant profile or leak that organization's participant inbox.
                db.add(
                    UserRole(
                        user_id=users["owner"].id,
                        role_id=roles["CRM Executive"].id,
                        organization_id=other_org,
                    )
                )
                db.commit()
                application_intake = None
                document_intake = None
                domain_intake = None
                if args.slice in {"applicant", "documents"}:
                    fixture_module = importlib.util.spec_from_file_location(
                        f"mobile_{args.slice}_fixtures",
                        root
                        / "scripts"
                        / (
                            "mobile-applicant-fixtures.py"
                            if args.slice == "applicant"
                            else "mobile-document-fixtures.py"
                        ),
                    )
                    require(
                        fixture_module is not None
                        and fixture_module.loader is not None,
                        "Synthetic applicant fixture module unavailable",
                    )
                    fixtures = importlib.util.module_from_spec(fixture_module)
                    fixture_module.loader.exec_module(fixtures)
                    intake = fixtures.create_intake(
                        db, org, users["director"], users["applicant"], run_id
                    )
                    if args.slice == "applicant":
                        application_intake = intake
                    else:
                        document_intake = intake
                if args.slice in {"learning", "support"}:
                    fixture_module = importlib.util.spec_from_file_location(
                        "mobile_domain_file_fixtures",
                        root / "scripts/mobile-document-fixtures.py",
                    )
                    fixtures = importlib.util.module_from_spec(fixture_module)
                    fixture_module.loader.exec_module(fixtures)
                    purpose = (
                        "assignment_submission"
                        if args.slice == "learning"
                        else "helpdesk_attachment"
                    )
                    domain_intake = fixtures.create_domain_policy(
                        db, org, users["director"], run_id, purpose
                    )
            participant_notifications.engine = engine
            task_result = participant_notifications.consume_outbox.run()
            require(
                isinstance(task_result.get("dispatched"), int)
                and task_result["dispatched"] >= 3,
                "Synthetic enrollment event consumption failed",
            )
            with Session(engine) as db:
                for name in ("owner", "peer", "outsider"):
                    notice = db.scalar(
                        select(ParticipantNotice).where(
                            ParticipantNotice.recipient_user_id
                            == UUID(accounts[name]["user_id"])
                        )
                    )
                    require(notice is not None, "Synthetic participant notice missing")
                    conversions[name]["notice_id"] = str(notice.id)
        finally:
            engine.dispose()
        fixture = {
            "synthetic_only": True,
            "run_id": run_id,
            "api_base": "http://127.0.0.1:8115/api/v1",
            "organization_id": str(org),
            "other_organization_id": str(other_org),
            "accounts": accounts,
            "enrollments": conversions,
            "application_intake": application_intake,
            "document_intake": document_intake,
            "domain_intake": domain_intake,
        }
        if args.slice == "applicant":
            fixture["registration"] = {
                "email": f"mobile-fresh-{run_id}@example.com",
                "password": secrets.token_urlsafe(24),
            }
        fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
        fixture_path.chmod(0o600)
        if file_slice:
            scan_thread = threading.Thread(
                target=fixtures.observe_scans,
                args=(
                    target,
                    folder,
                    org,
                    UUID(
                        accounts["applicant" if args.slice == "documents" else "owner"][
                            "user_id"
                        ]
                    ),
                    verification_stop,
                    record,
                    "application_document"
                    if args.slice == "documents"
                    else domain_intake["purpose"],
                ),
                daemon=True,
            )
            scan_thread.start()
        if args.slice == "applicant":
            # Out-of-band local verification mirrors the development mailbox.
            # No test endpoint or external sender is added to the production API.
            from app.modules.identity.models import AuthDelivery, VerificationToken

            def record_verification() -> None:
                observer_engine = create_engine(
                    target, connect_args={"connect_timeout": 3}
                )
                try:
                    while not verification_stop.is_set():
                        with Session(observer_engine) as observer_db:
                            delivery = observer_db.scalar(
                                select(AuthDelivery)
                                .join(VerificationToken)
                                .join(User, User.id == VerificationToken.user_id)
                                .where(
                                    User.email == fixture["registration"]["email"],
                                    VerificationToken.purpose == "verify",
                                    VerificationToken.consumed_at.is_(None),
                                )
                                .order_by(AuthDelivery.created_at.desc())
                                .limit(1)
                            )
                            if delivery:
                                payload = json.loads(
                                    Fernet(env["AUTH_DELIVERY_KEY"].encode()).decrypt(
                                        delivery.encrypted_payload.encode()
                                    )
                                )
                                temporary = folder / "verification.tmp"
                                temporary.write_text(
                                    json.dumps({"token": payload["token"]}),
                                    encoding="utf-8",
                                )
                                temporary.chmod(0o600)
                                temporary.replace(verification_path)
                                return
                        verification_stop.wait(0.1)
                except Exception:  # noqa: BLE001 - do not expose mailbox payloads
                    record["verification_observer_failed"] = True
                finally:
                    observer_engine.dispose()

            verification_thread = threading.Thread(
                target=record_verification, daemon=True
            )
            verification_thread.start()
        output = (folder / "api.log").open("w", encoding="utf-8")
        server = subprocess.Popen(
            [
                sys.executable,
                "scripts/run-native-api.py",
                "--host",
                "127.0.0.1",
                "--port",
                "8115",
            ],
            cwd=root,
            env=env,
            stdout=output,
            stderr=subprocess.STDOUT,
            creationflags=hidden,
            start_new_session=os.name != "nt",
        )
        deadline = time.monotonic() + 40
        loopback_http = build_opener(ProxyHandler({}))
        while True:
            require(server.poll() is None, "Owned API stopped before liveness")
            try:
                with loopback_http.open(
                    "http://127.0.0.1:8115/health", timeout=2
                ) as response:
                    if response.status == 200:
                        break
            except OSError:
                require(time.monotonic() < deadline, "Owned API startup timeout")
                time.sleep(0.25)
        with (folder / "flutter.log").open("w", encoding="utf-8") as log:
            flutter_process = subprocess.Popen(
                [
                    "cmd.exe",
                    "/d",
                    "/c",
                    str(flutter),
                    "test",
                    "--no-pub",
                    test_path,
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
            exit_code = flutter_process.wait(timeout=300)
        record.update(passed=exit_code == 0, exit_code=exit_code)
        print(
            "Flutter/API acceptance",
            args.slice,
            "exit",
            exit_code,
            "evidence",
            folder.relative_to(root),
            flush=True,
        )
    except Exception as error:  # noqa: BLE001 - sanitize credential-bearing database exceptions
        # Database exceptions can contain credentials; preserve classification only.
        record.update(failure_type=type(error).__name__)
        print("Mobile/API acceptance failed; type", type(error).__name__, flush=True)
        exit_code = 1
    finally:
        verification_stop.set()
        if verification_thread:
            verification_thread.join(timeout=5)
        if scan_thread:
            scan_thread.join(timeout=5)
        cleanup_failed = (
            (verification_thread is not None and verification_thread.is_alive())
            or (scan_thread is not None and scan_thread.is_alive())
            or record.get("scan_observer_failed", False)
        )
        for process in (flutter_process, server):
            try:
                stop_owned(process, hidden)
            except (OSError, subprocess.SubprocessError):
                cleanup_failed = True
        if output:
            output.close()
        if fixture_path.exists():
            fixture_path.unlink()
        if verification_path.exists():
            verification_path.unlink()
        verification_temporary = folder / "verification.tmp"
        if verification_temporary.exists():
            verification_temporary.unlink()
        record.update(
            finished_at=datetime.now(UTC).isoformat(),
            owned_server_cleaned_up=server is None or server.poll() is not None,
            owned_flutter_cleaned_up=flutter_process is None
            or flutter_process.poll() is not None,
            ephemeral_fixture_removed=not fixture_path.exists(),
            ephemeral_verification_removed=not verification_path.exists()
            and not verification_temporary.exists(),
            verification_observer_stopped=verification_thread is None
            or not verification_thread.is_alive(),
            scan_observer_stopped=scan_thread is None or not scan_thread.is_alive(),
            cleanup_failed=cleanup_failed,
        )
        if cleanup_failed:
            record["passed"] = False
            exit_code = 1
        record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print("Mobile/API record", record_path.relative_to(root), flush=True)
    return exit_code


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:  # noqa: BLE001 - sanitize credential-bearing preflight exceptions
        # Preflight failures must not render a database URL or credential content.
        print("Mobile/API preflight failed; type", type(error).__name__, flush=True)
        raise SystemExit(1) from None
