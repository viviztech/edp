"""Connected synthetic manual-code and enrollment-inbox browser acceptance."""

import json
import os
import re
import secrets
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from app.modules.identity.models import (
    AuthDelivery,
    Organization,
    Person,
    Role,
    User,
    UserRole,
    VerificationToken,
)
from app.modules.identity.security import hasher
from app.modules.identity.service import seed_roles
from app.workers import participant_notifications as worker
from cryptography.fernet import Fernet
from playwright.sync_api import expect, sync_playwright
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

root = Path(__file__).resolve().parents[1]
assert os.environ.get("COMMUNICATIONS_BROWSER_RUNNER") == "synthetic-only"
engine = create_engine(os.environ["DATABASE_URL"])
assert engine.url.database == "edp_communications_e2e"
assert engine.url.host in {"localhost", "127.0.0.1"}
assert engine.url.username == "edp_dev" and engine.url.port is not None
assert os.environ["AUTH_DELIVERY_BACKEND"] == "development"
assert os.environ["AUTH_SMTP_ENABLED"] == "false"
assert os.environ["PARTICIPANT_NOTIFICATION_RETENTION_DAYS"] == "7"
base = os.environ["WEB_ORIGIN"]
assert base == "http://127.0.0.1:3114"
worker.engine = engine
sys.path.insert(0, str(root / "apps/api/tests"))
from participant_notification_fixtures import create_enrollment


def copy(path, locale):
    source = (root / path).read_text(encoding="utf-8")
    block = source.split(f"  {locale}: {{", 1)[1]
    if locale == "en":
        block = block.split("  ta: {", 1)[0]
    return {
        key: json.loads(value)
        for key, value in re.findall(r'(\w+):\s*("(?:\\.|[^"\\])*")', block)
    }


org_id = UUID(os.environ["PUBLIC_ORGANIZATION_ID"])
suffix = uuid4().hex[:10]
staff_email = f"communications-staff-{suffix}@example.com"
staff_password = secrets.token_urlsafe(24)
with Session(engine) as db:
    seed_roles(db)
    db.add(Organization(id=org_id, name="Synthetic communications " + suffix))
    person = Person(display_name="Synthetic communications staff")
    db.add(person)
    db.flush()
    staff = User(
        person_id=person.id,
        email=staff_email,
        password_hash=hasher.hash(staff_password),
        status="active",
    )
    role = db.scalar(select(Role).where(Role.name == "Super Admin"))
    assert role
    db.add(staff)
    db.flush()
    db.add(UserRole(user_id=staff.id, role_id=role.id, organization_id=org_id))
    db.commit()
    staff_id = staff.id


def command(page, path, data):
    csrf = page.request.get(base + "/api/session/csrf")
    assert csrf.status == 200
    return page.request.post(
        base + path,
        data=data,
        headers={"Origin": base, "X-CSRF-Token": csrf.json()["csrf_token"]},
    )


def challenge(email, purpose):
    with Session(engine) as db:
        row = db.scalar(
            select(AuthDelivery)
            .join(VerificationToken)
            .join(User)
            .where(
                User.email == email,
                VerificationToken.purpose == purpose,
                VerificationToken.consumed_at.is_(None),
            )
            .order_by(AuthDelivery.created_at.desc())
            .limit(1)
        )
        assert row and row.encrypted_payload
        payload = json.loads(
            Fernet(os.environ["AUTH_DELIVERY_KEY"].encode()).decrypt(
                row.encrypted_payload.encode()
            )
        )
        return payload["token"], row.token_id


def enroll(email, edition):
    with Session(engine) as db:
        director = db.get(User, staff_id)
        learner = db.scalar(select(User).where(User.email == email))
        assert director and learner
        conversion = create_enrollment(db, org_id, director, learner, suffix + edition)
        return conversion.enrollment.id, learner.id


errors = []
screenshots = []
request_urls = []
inbox_root = f"/api/participant-notifications/organizations/{org_id}"
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        channel=os.getenv("PLAYWRIGHT_CHANNEL"), headless=True
    )
    try:
        for locale in ("en", "ta"):
            auth_text = copy("apps/web/src/lib/auth-messages.ts", locale)
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("request", lambda request: request_urls.append(request.url))
            email = f"communications-{locale}-{suffix}@example.com"
            password, replacement = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
            result = command(
                page,
                "/api/session/register",
                {
                    "email": email,
                    "password": password,
                    "display_name": "Synthetic communications learner",
                    "locale": locale,
                },
            )
            assert result.status == 202, f"Registration status {result.status}"
            raw, token_id = challenge(email, "verify")
            assert (
                command(
                    page,
                    "/api/session/login",
                    {"email": staff_email, "password": staff_password},
                ).status
                == 200
            )
            page.goto(base + f"/{locale}/account/verify")
            expect(page.locator('input[name="token"]')).to_have_value("")
            with Session(engine) as db:
                assert db.get(VerificationToken, token_id).consumed_at is None
            page.locator('input[name="token"]').fill(raw)
            with page.expect_response(
                lambda response: response.url.endswith("/api/session/verify")
            ) as response:
                page.locator("form").get_by_role("button").click()
            assert response.value.status == 200
            expect(page.locator('input[name="token"]')).to_have_count(0)
            expect(page.get_by_role("status")).to_contain_text(auth_text["completed"])
            assert page.request.get(base + "/api/session/me").json()["id"] == str(
                staff_id
            )
            assert (
                command(page, "/api/session/request-reset", {"email": email}).status
                == 202
            )
            reset, token_id = challenge(email, "reset")
            page.goto(base + f"/{locale}/account/reset")
            with Session(engine) as db:
                assert db.get(VerificationToken, token_id).consumed_at is None
            page.locator('input[name="token"]').fill(reset)
            page.locator('input[name="password"]').fill(replacement)
            with page.expect_response(
                lambda response: response.url.endswith("/api/session/reset")
            ) as response:
                page.locator("form").get_by_role("button").click()
            assert response.value.status == 200
            expect(page.locator('input[name="token"]')).to_have_count(0)
            expect(page.locator('input[name="password"]')).to_have_count(0)
            expect(page.get_by_role("status")).to_contain_text(auth_text["completed"])
            assert page.request.get(base + "/api/session/me").json()["id"] == str(
                staff_id
            )
            assert raw not in page.url and reset not in page.url
            assert page.evaluate(
                "localStorage.length === 0 && sessionStorage.length === 0"
            )
            assert (
                command(
                    page, "/api/session/login", {"email": email, "password": password}
                ).status
                == 401
            )
            assert (
                command(
                    page,
                    "/api/session/login",
                    {"email": email, "password": replacement},
                ).status
                == 200
            )

            enrollment_id, learner_id = enroll(email, locale)
            first = worker.consume_outbox.run()
            assert first["dispatched"] == 1
            assert worker.consume_outbox.run()["dispatched"] == 0
            text = copy("apps/web/src/app/[locale]/updates/content.ts", locale)
            page.goto(base + f"/{locale}/updates?organization={org_id}")
            region = page.get_by_role("region", name=text["notices"], exact=True)
            expect(region.get_by_role("article")).to_have_count(1)
            expect(region).to_contain_text(text["enrollmentTitle"])
            notices = page.request.get(base + inbox_root + "/mine").json()["items"]
            assert len(notices) == 1 and notices[0]["enrollment_id"] == str(
                enrollment_id
            )
            notice_id = notices[0]["id"]
            region.get_by_role("button", name=text["markRead"], exact=True).click()
            expect(
                region.get_by_role("button", name=text["markRead"], exact=True)
            ).to_have_count(0)
            assert page.request.get(base + inbox_root + "/mine").json()["items"][0][
                "read_at"
            ]
            preference = page.get_by_role(
                "region", name=text["preferences"], exact=True
            )
            preference.get_by_role("checkbox").uncheck()
            preference.get_by_role("button", name=text["save"], exact=True).click()
            expect(preference).to_contain_text(text["saved"])
            assert (
                page.request.get(base + inbox_root + "/preference").json()["enabled"]
                is False
            )
            enroll(email, locale + "-suppressed")
            assert worker.consume_outbox.run()["suppressed"] == 1
            preference.get_by_role("checkbox").check()
            preference.get_by_role("button", name=text["save"], exact=True).click()
            expect(preference).to_contain_text(text["saved"])
            assert worker.consume_outbox.run()["dispatched"] == 0
            assert (
                len(page.request.get(base + inbox_root + "/mine").json()["items"]) == 1
            )
            assert (
                page.request.post(
                    base + inbox_root + f"/{notice_id}/read",
                    data={"expected_version": 1},
                    headers={"Origin": base},
                ).status
                == 403
            )
            for width in (390, 1280):
                page.set_viewport_size({"width": width, "height": 900})
                page.evaluate("document.fonts.ready")
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth + 1"
                )
                page.locator("a.skip").focus()
                page.keyboard.press("Enter")
                expect(page.locator("#main")).to_be_focused()
                destination = (
                    root / f".tool-cache/evidence/communications-{locale}-{width}.png"
                )
                destination.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(destination), full_page=True)
                screenshots.append(str(destination.relative_to(root)))
            with Session(engine) as db:
                role = db.scalar(select(Role).where(Role.name == "Participant"))
                assert role
                db.execute(
                    delete(UserRole).where(
                        UserRole.user_id == learner_id,
                        UserRole.role_id == role.id,
                        UserRole.organization_id == org_id,
                    )
                )
                db.commit()
            assert page.request.get(base + inbox_root + "/mine").status == 403
            assert (
                command(
                    page, inbox_root + f"/{notice_id}/read", {"expected_version": 2}
                ).status
                == 403
            )
            region.get_by_role("button", name=text["refresh"], exact=True).click()
            expect(page.get_by_role("article")).to_have_count(0)
            assert not any(raw in url or reset in url for url in request_urls)
            context.close()
        assert not errors, (
            "Unexpected JavaScript error; inspect synthetic runner evidence"
        )
    finally:
        browser.close()
        engine.dispose()

record = {
    "passed": True,
    "recorded_at": datetime.now(UTC).isoformat(),
    "synthetic_only": True,
    "locales": ["en", "ta"],
    "widths": [390, 1280],
    "javascript_errors": len(errors),
    "screenshots": screenshots,
    "identity_transport": "explicit no-delivery development queue",
    "direct_task_functions": True,
    "broker_worker_beat_acceptance": False,
    "external_messages": False,
}
Path(os.environ["COMMUNICATIONS_BROWSER_EVIDENCE"]).write_text(
    json.dumps(record, indent=2) + "\n", encoding="utf-8"
)
print(
    "PASS: EN/TA fixed verification/reset pages while another account is signed in; real enrollment transaction to deduplicated inbox; read, preference suppression/no backfill, CSRF/revocation and keyboard layouts. No external messages; direct tasks only."
)
