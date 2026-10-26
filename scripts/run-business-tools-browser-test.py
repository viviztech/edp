"""Guarded synthetic business-tool acceptance against a built web artifact.

Creates and drops only a fresh database owned by this run. Uses no provider,
external destination, real contact, or persistent account credentials.
"""

import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import ProxyHandler, build_opener
from uuid import uuid4

from cryptography.fernet import Fernet
from playwright.sync_api import expect, sync_playwright
from sqlalchemy import URL, create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session


def main():
    root = Path(__file__).resolve().parents[1]
    run_id = uuid4().hex[:12]
    folder = root / ".tool-cache" / f"business-tools-browser-{run_id}"
    folder.mkdir()
    if os.getenv("BUSINESS_TOOLS_DATABASE_URL"):
        admin_url = make_url(os.environ["BUSINESS_TOOLS_DATABASE_URL"])
        assert admin_url.drivername == "postgresql+psycopg"
        assert not admin_url.query, "Connection overrides are not supported"
        assert admin_url.database == "postgres"
        assert admin_url.host in {"127.0.0.1", "localhost"}
        assert admin_url.port in {5432, 55432} and admin_url.username == "edp_dev"
    else:
        credentials = json.loads(
            (root / ".local/postgres17/credentials.json").read_text(encoding="utf-8-sig")
        )
        assert credentials["host"] == "127.0.0.1" and int(credentials["port"]) == 55432
        assert credentials["user"] == "edp_dev"
        admin_url = URL.create(
            "postgresql+psycopg",
            username=credentials["user"],
            password=credentials["password"],
            host="127.0.0.1",
            port=55432,
            database="postgres",
        )
    name = f"edp_business_tools_e2e_{run_id}"
    target = admin_url.set(database=name)
    for port in (8120, 3120):
        with socket.socket() as probe:
            assert probe.connect_ex(("127.0.0.1", port)) != 0, "Owned port occupied"
    base = "http://127.0.0.1:3120"
    env = dict(os.environ)
    env.update(
        DATABASE_URL=target.render_as_string(hide_password=False),
        APP_ENV="local",
        REDIS_URL="redis://127.0.0.1:1/15",
        AUTH_DELIVERY_KEY=Fernet.generate_key().decode(),
        BFF_KEY=secrets.token_urlsafe(32),
        AUTH_DELIVERY_BACKEND="development",
        AUTH_SMTP_ENABLED="false",
        AUTH_TEMPLATES_APPROVED="false",
        FILES_ENABLED="false",
        FILES_MAINTENANCE_ENABLED="false",
        CONTACT_ENQUIRIES_ENABLED="false",
        PYTHONUTF8="1",
        PYTHONIOENCODING="utf-8",
        PYTHONPATH=str(root / "apps/api"),
        API_INTERNAL_URL="http://127.0.0.1:8120",
        WEB_ORIGIN=base,
        COOKIE_SECURE="false",
        HOSTNAME="127.0.0.1",
        PORT="3120",
    )
    hidden = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    admin = create_engine(target.set(database="postgres"), isolation_level="AUTOCOMMIT")
    created = False
    processes = []
    logs = []
    record = {
        "synthetic_only": True,
        "passed": False,
        "database": name,
        "database_dropped": False,
    }
    try:
        with admin.connect() as db:
            assert not db.scalar(
                text("select 1 from pg_database where datname=:name"), {"name": name}
            )
            db.execute(text(f'CREATE DATABASE "{name}"'))
            created = True
        with (folder / "migration.log").open("w", encoding="utf-8") as log:
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=root / "apps/api",
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=hidden,
                timeout=180,
                check=False,
            )
            assert result.returncode == 0, "Migration failed"
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
        from participant_notification_fixtures import create_enrollment

        actors = {}
        engine = create_engine(target)
        try:
            with Session(engine) as db:
                seed_roles(db)
                org = Organization(name="Synthetic tools organization")
                db.add(org)
                db.flush()
                org_id = str(org.id)
                for key in ("director", "owner", "peer"):
                    person = Person(display_name="Synthetic tools " + key)
                    db.add(person)
                    db.flush()
                    password = secrets.token_urlsafe(24)
                    user = User(
                        person_id=person.id,
                        email=f"tools-{run_id}-{key}@example.com",
                        password_hash=hasher.hash(password),
                        status="active",
                    )
                    db.add(user)
                    db.flush()
                    role = db.scalar(
                        select(Role).where(
                            Role.name == ("Super Admin" if key == "director" else "Participant")
                        )
                    )
                    db.add(UserRole(user_id=user.id, role_id=role.id, organization_id=org.id))
                    actors[key] = {
                        "user": user,
                        "email": user.email,
                        "password": password,
                    }
                db.commit()
                create_enrollment(
                    db,
                    org.id,
                    actors["director"]["user"],
                    actors["owner"]["user"],
                    run_id,
                )
        finally:
            engine.dispose()
        for source, destination in (
            ("apps/web/.next/static", "apps/web/.next/standalone/.next/static"),
            ("apps/web/public", "apps/web/.next/standalone/public"),
        ):
            shutil.copytree(root / source, root / destination, dirs_exist_ok=True)
        http = build_opener(ProxyHandler({}))
        for label, command, ready in (
            (
                "api",
                [sys.executable, "scripts/run-native-api.py", "--port", "8120"],
                "http://127.0.0.1:8120/health",
            ),
            (
                "web",
                [shutil.which("node") or "node", "apps/web/.next/standalone/server.js"],
                base + "/en",
            ),
        ):
            log = (folder / f"{label}.log").open("w", encoding="utf-8")
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
            deadline = time.monotonic() + 60
            while True:
                assert process.poll() is None and time.monotonic() < deadline, (
                    f"Owned {label} failed startup"
                )
                try:
                    with http.open(ready, timeout=2) as response:
                        if response.status == 200:
                            break
                except OSError:
                    time.sleep(0.2)
        errors = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                channel=os.getenv("PLAYWRIGHT_CHANNEL") or ("chrome" if os.name == "nt" else None),
                headless=True,
            )
            context = browser.new_context(
                viewport={"width": 1280, "height": 900}, accept_downloads=True
            )
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base + "/en/account")
            page.get_by_label("Email", exact=True).fill(actors["owner"]["email"])
            page.get_by_label("Password", exact=True).fill(actors["owner"]["password"])
            page.locator("form").get_by_role("button", name="Sign in", exact=True).click()
            expect(page.get_by_text("Synthetic tools owner", exact=True)).to_be_visible()
            csrf = page.request.get(base + "/api/session/csrf").json()["csrf_token"]
            headers = {"Origin": base, "X-CSRF-Token": csrf}
            businesses = f"{base}/api/businesses/organizations/{org_id}"
            enrollment = page.request.get(businesses + "/mine").json()["entries"][0][
                "enrollment_id"
            ]
            response = page.request.post(
                businesses + "/profiles",
                headers=headers,
                data={
                    "enrollment_id": enrollment,
                    "name": "Synthetic tools bakery",
                    "sector": "Food",
                    "products_services": "Synthetic bread",
                    "stage": "idea",
                    "team_size": 1,
                    "investment_band": "none",
                    "funding_status": "none",
                    "revenue_band": "none",
                    "public_opt_in": False,
                },
            )
            assert response.status == 201
            profile_id = response.json()["id"]
            tools_root = f"{base}/api/business-tools/organizations/{org_id}/profiles/{profile_id}"
            page.goto(f"{base}/en/business-tools?organization={org_id}")
            card = page.locator("section").filter(
                has=page.get_by_role("heading", name="Digital business card", exact=True)
            )
            card.get_by_label("Name in English", exact=True).fill("Synthetic share bakery")
            card.get_by_label("Name in English", exact=True).focus()
            page.keyboard.press("Tab")
            expect(card.get_by_label("Name in Tamil", exact=True)).to_be_focused()
            card.get_by_label("Name in Tamil", exact=True).fill("செயற்கை பேக்கரி")
            card.get_by_label("Description in English", exact=True).fill(
                "Synthetic public details <script>never execute</script>"
            )
            # Simulate a response lost after the server commits; replay must use the same UUID.
            captured = []

            def lose_once(route):
                captured.append(route.request.post_data)
                route.fetch()
                route.abort("failed")
                page.unroute("**/api/business-tools/**/card", lose_once)

            page.route("**/api/business-tools/**/card", lose_once)
            card.get_by_role("button", name="Save draft", exact=True).click()
            card.get_by_role("button", name="Confirm interrupted request", exact=True).click()
            expect(card.get_by_text("Saved.", exact=True)).to_be_visible()
            assert (
                len(captured) == 1 and page.request.get(tools_root + "/card").json()["version"] == 1
            )
            card.get_by_role("button", name="Publish these saved details", exact=True).click()
            share_path = card.get_by_role("link", name="Open shared page").get_attribute("href")
            anonymous = browser.new_page()
            assert anonymous.goto(base + share_path).status == 200
            expect(
                anonymous.get_by_role("heading", name="Synthetic share bakery", exact=True)
            ).to_be_visible()
            card.get_by_role("button", name="Revoke sharing", exact=True).click()
            expect(
                card.get_by_role("button", name="Publish these saved details", exact=True)
            ).to_be_visible()
            anonymous.reload()
            # Next.js may stream a 200 before its asynchronous notFound result.
            # Revocation acceptance is absence of the formerly public projection.
            expect(
                anonymous.get_by_role("heading", name="Synthetic share bakery", exact=True)
            ).to_have_count(0)
            catalogue = page.locator("section").filter(
                has=page.get_by_role("heading", name="Products and services", exact=True)
            )
            catalogue.get_by_label("Name in English", exact=True).fill("Synthetic bread")
            catalogue.get_by_label("Name in Tamil", exact=True).fill("செயற்கை ரொட்டி")
            catalogue.get_by_label("Unit price (optional)", exact=True).fill("12.50")
            catalogue.get_by_role("button", name="Add item", exact=True).click()
            expect(catalogue.get_by_text("Saved.", exact=True)).to_be_visible()
            catalogue.get_by_role("button", name="Publish these saved details", exact=True).click()
            expect(catalogue.get_by_role("link", name="Open shared page")).to_be_visible()
            assert (
                anonymous.goto(
                    base
                    + catalogue.get_by_role("link", name="Open shared page").get_attribute("href")
                ).status
                == 200
            )
            expect(
                anonymous.get_by_role("heading", name="Synthetic bread", exact=True)
            ).to_be_visible()
            catalogue.get_by_role("button", name="Revoke sharing", exact=True).click()
            expect(
                catalogue.get_by_role("button", name="Publish these saved details", exact=True)
            ).to_be_visible()
            anonymous.reload()
            expect(
                anonymous.get_by_role("heading", name="Synthetic bread", exact=True)
            ).to_have_count(0)
            quotations = page.locator("section").filter(
                has=page.get_by_role("heading", name="Quotations", exact=True)
            )
            quotations.get_by_label("Customer name", exact=True).fill("Synthetic quotation buyer")
            quotations.get_by_label("Description", exact=True).fill("Synthetic consulting")
            quotations.get_by_label("Quantity", exact=True).fill("1.005")
            quotations.get_by_label("Unit price", exact=True).fill("0.10")
            quotations.get_by_role("button", name="Save draft", exact=True).click()
            expect(quotations.get_by_text("Saved.", exact=True)).to_be_visible()
            assert page.request.get(tools_root + "/quotes").json()["items"][0]["total"] == "0.10"
            quotations.get_by_label(
                "I reviewed the saved quotation and want to issue this immutable version",
                exact=True,
            ).check()
            quotations.get_by_role("button", name="Issue saved quotation", exact=True).click()
            with page.expect_download() as download:
                quotations.get_by_role("link", name="Download printable copy", exact=True).click()
            artifact = folder / "quotation.html"
            download.value.save_as(artifact)
            assert "0.10" in artifact.read_text(encoding="utf-8")
            contacts = page.locator("section").filter(
                has=page.get_by_role("heading", name="Contacts", exact=True)
            )
            contacts.get_by_label("Contact name", exact=True).fill("Synthetic private customer")
            contacts.get_by_role("button", name="Save draft", exact=True).click()
            expect(contacts.get_by_text("Saved.", exact=True)).to_be_visible()
            tasks = page.locator("section").filter(
                has=page.get_by_role("heading", name="Follow-ups", exact=True)
            )
            expect(tasks).to_be_visible()
            tasks.get_by_label("Contact name").select_option(label="Synthetic private customer")
            tasks.get_by_label("Follow-up title", exact=True).fill("Synthetic follow-up")
            tasks.get_by_label("Due at (your local time)", exact=True).fill("2026-11-01T09:30")
            tasks.get_by_role("button", name="Save draft", exact=True).click()
            expect(tasks.get_by_text("Saved.", exact=True)).to_be_visible()
            tasks.get_by_label("Status").last.select_option("completed")
            tasks.get_by_role("button", name="Save draft", exact=True).click()
            expect(tasks.locator("li").filter(has_text="Synthetic follow-up")).to_contain_text(
                "Completed"
            )
            assert (
                page.request.get(tools_root + "/tasks").json()["items"][0]["status"] == "completed"
            )
            assert page.request.get(tools_root + "/card?owner=other").status == 400
            bad = page.request.post(
                tools_root + "/card/sharing",
                headers={**headers, "Origin": "https://unrelated.example"},
                data={},
            )
            assert bad.status == 403
            page.screenshot(path=str(folder / "tools-en-desktop.png"), full_page=True)
            card.screenshot(path=str(folder / "card-en.png"))
            quotations.screenshot(path=str(folder / "quotation-en.png"))
            tasks.screenshot(path=str(folder / "followup-en.png"))
            page.goto(f"{base}/ta/business-tools?organization={org_id}")
            page.set_viewport_size({"width": 390, "height": 844})
            expect(
                page.get_by_role("heading", name="எனது தொழில் கருவிகள்", exact=True)
            ).to_be_visible()
            expect(page.get_by_role("heading", name="மின்னணு வணிக அட்டை", exact=True)).to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            page.screenshot(path=str(folder / "tools-ta-mobile.png"), full_page=True)
            page.locator("section").filter(
                has=page.get_by_role("heading", name="மின்னணு வணிக அட்டை", exact=True)
            ).screenshot(path=str(folder / "card-ta-mobile.png"))
            assert not errors, "Browser JavaScript errors"
            record.update(
                passed=True,
                browser_errors=len(errors),
                tested=[
                    "lost-save-retry",
                    "card-share-revoke",
                    "catalogue-share-revoke",
                    "quote-decimals-issue-download",
                    "contact-followup-completion",
                    "csrf-query-denial",
                    "tamil-responsive",
                ],
            )
            browser.close()
    finally:
        for process in reversed(processes):
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
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
        for log in logs:
            log.close()
        if created:
            with admin.connect() as db:
                db.execute(
                    text(
                        "select pg_terminate_backend(pid) from pg_stat_activity "
                        "where datname=:name and pid<>pg_backend_pid()"
                    ),
                    {"name": name},
                )
                db.execute(text(f'DROP DATABASE "{name}"'))
                record["database_dropped"] = True
        admin.dispose()
        (folder / "report.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print(
            f"Business tools browser passed={record['passed']}; "
            f"evidence {folder.relative_to(root)}",
            flush=True,
        )


if __name__ == "__main__":
    main()
