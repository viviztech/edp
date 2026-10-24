"""Connected synthetic CRM export acceptance; direct tasks are not broker evidence."""

import csv
import hashlib
import io
import json
import os
import re
import secrets
import socket
import time
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlparse
from uuid import UUID, uuid4

from app.modules.crm import export_service
from app.modules.crm.models import ExportJob, Lead
from app.modules.identity.models import (
    AuditLog,
    Organization,
    Person,
    Role,
    RolePermission,
    User,
    UserRole,
    now,
)
from app.modules.identity.security import hasher
from app.modules.identity.service import seed_roles
from app.workers import crm_exports
from playwright.sync_api import expect, sync_playwright
from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import Session

root = Path(__file__).resolve().parents[1]
assert os.environ.get("CRM_EXPORT_BROWSER_RUNNER") == "synthetic-only"
engine = create_engine(os.environ["DATABASE_URL"])
assert engine.url.database == "edp_crm_exports_e2e"
assert (
    engine.url.host in {"localhost", "127.0.0.1"} and engine.url.username == "edp_dev"
)
assert crm_exports.engine.url == engine.url
base = os.environ["WEB_ORIGIN"]
assert base == "http://127.0.0.1:3113"
assert os.environ["API_INTERNAL_URL"] == "http://127.0.0.1:8113"
redis = urlparse(os.environ["REDIS_URL"])
assert redis.hostname == "127.0.0.1" and redis.port is not None
with socket.socket() as probe:
    assert probe.connect_ex((redis.hostname, redis.port)) != 0, (
        "Redis must be unavailable"
    )

org_id = UUID(os.environ["PUBLIC_ORGANIZATION_ID"])
suffix = uuid4().hex[:12]
actors = {
    key: {
        "email": f"crm-export-{key}-{suffix}@example.com",
        "password": secrets.token_urlsafe(24),
        "name": "Synthetic CRM export " + key,
    }
    for key in ("requester", "peer", "reader", "outsider")
}
with Session(engine) as db:
    seed_roles(db)
    org = Organization(id=org_id, name="Synthetic CRM exports " + suffix)
    other = Organization(name="Unrelated synthetic CRM exports " + suffix)
    reader_role = Role(name="Synthetic export reader " + suffix)
    exporter_role = Role(name="Synthetic export permission " + suffix)
    db.add_all([org, other, reader_role, exporter_role])
    db.flush()
    other_org_id, exporter_role_id = other.id, exporter_role.id
    db.add_all(
        [
            RolePermission(role_id=reader_role.id, permission_code="system.access"),
            RolePermission(role_id=reader_role.id, permission_code="crm.lead.view"),
            RolePermission(role_id=exporter_role.id, permission_code="crm.lead.export"),
        ]
    )
    for key, credentials in actors.items():
        person = Person(display_name=credentials["name"])
        db.add(person)
        db.flush()
        user = User(
            person_id=person.id,
            email=credentials["email"],
            password_hash=hasher.hash(credentials["password"]),
            status="active",
        )
        db.add(user)
        db.flush()
        credentials["user_id"] = user.id
        actor_org = other.id if key == "outsider" else org.id
        db.add(
            UserRole(user_id=user.id, role_id=reader_role.id, organization_id=actor_org)
        )
        if key != "reader":
            db.add(
                UserRole(
                    user_id=user.id, role_id=exporter_role.id, organization_id=actor_org
                )
            )
    for index, name in enumerate(("=SUM(1,1)", 'Plain, quoted "lead"', "  -2+3")):
        db.add(
            Lead(
                organization_id=org.id,
                name=name,
                email=f"synthetic-{index}@example.test",
                phone="+919000000001",
                source="manual",
                campaign="First line\nSecond line",
                dedupe_hash=hashlib.sha256(f"{suffix}:{index}".encode()).hexdigest(),
            )
        )
    db.add(
        Lead(
            organization_id=other.id,
            name="FOREIGN-ORG-EXCLUDED-" + suffix,
            source="manual",
            dedupe_hash=hashlib.sha256(f"{suffix}:foreign".encode()).hexdigest(),
        )
    )
    db.commit()

labels = {
    "en": {
        "title": "CSV exports",
        "request": "Prepare export",
        "check": "Check export status",
        "download": "Download CSV",
        "queued": "Queued",
        "completed": "Completed",
        "failed": "Failed",
        "retry": "Your request is saved and waiting for another processing attempt.",
        "no_access": "This export is unavailable or you no longer have access to it.",
    },
    "ta": {
        "title": "CSV ஏற்றுமதி",
        "request": "ஏற்றுமதியைத் தயார் செய்",
        "check": "ஏற்றுமதி நிலையைச் சரிபார்",
        "download": "CSV பதிவிறக்கு",
        "queued": "வரிசையில் உள்ளது",
        "completed": "நிறைவடைந்தது",
        "failed": "தோல்வியடைந்தது",
        "retry": "அடுத்த செயலாக்க முயற்சிக்காகக் காத்திருக்கிறது.",
        "no_access": "இனி அணுகல் இல்லை.",
    },
}
exports_root = f"/api/crm/organizations/{org_id}/exports"
evidence = root / ".tool-cache/evidence"
evidence.mkdir(exist_ok=True)
errors = []
requests = []
jobs = []
screenshots = []


def sign_in(browser, key):
    page = browser.new_context(viewport={"width": 1280, "height": 900}).new_page()
    page.on("pageerror", lambda error: errors.append(type(error).__name__))
    page.on(
        "request",
        lambda request: (
            requests.append((request.method, urlparse(request.url).path))
            if request.url.startswith(base + "/api/")
            else None
        ),
    )
    page.goto(base + "/en/account")
    page.get_by_role("textbox", name="Email", exact=True).fill(actors[key]["email"])
    page.get_by_label("Password", exact=True).fill(actors[key]["password"])
    with page.expect_response(
        lambda response: (
            response.url == base + "/api/session/login"
            and response.request.method == "POST"
        )
    ) as response:
        page.locator("form").get_by_role("button", name="Sign in", exact=True).click()
    assert response.value.status == 200
    expect(page.get_by_text(actors[key]["name"], exact=True)).to_be_visible()
    return page


def workspace(page, locale):
    page.goto(base + f"/{locale}/admin/crm?organization={org_id}")
    region = page.get_by_role("region", name=labels[locale]["title"], exact=True)
    expect(region).to_be_visible()
    return region


def ready(region):
    expect(region).to_have_attribute("aria-busy", "false")


def current(page, identity):
    response = page.request.get(base + exports_root + "/" + str(identity))
    assert response.status == 200
    body = response.json()
    assert body["id"] == str(identity)
    assert all(
        key not in body for key in ("csv_content", "lease_token_digest", "lease_until")
    )
    return body


def count_jobs():
    with Session(engine) as db:
        return db.scalar(
            select(func.count())
            .select_from(ExportJob)
            .where(ExportJob.organization_id == org_id)
        )


def request_export(page, region, locale):
    ready(region)
    with page.expect_response(
        lambda response: (
            response.url == base + exports_root and response.request.method == "POST"
        )
    ) as response:
        region.get_by_role("button", name=labels[locale]["request"], exact=True).click()
    assert response.value.status == 202
    body = response.value.json()
    assert body["status"] == "queued"
    identity = UUID(body["id"])
    ready(region)
    expect(region.get_by_text(labels[locale]["queued"], exact=True)).to_be_visible()
    assert current(page, identity)["status"] == "queued"
    with Session(engine) as db:
        row = db.get(ExportJob, identity)
        assert row is not None and row.requested_by_id == actors["requester"]["user_id"]
        assert row.status == "queued" and row.attempt_count == 0 and row.version == 1
    jobs.append(str(identity))
    return identity


def refresh(region, locale):
    ready(region)
    region.get_by_role("button", name=labels[locale]["check"], exact=True).click()
    ready(region)


def select_saved(region, identity):
    button = region.get_by_role(
        "button", name=re.compile(re.escape(str(identity)) + r"$")
    )
    expect(button).to_be_visible()
    button.click()
    ready(region)


def responsive(page, region, locale, state):
    ready(region)
    for width in (390, 1280):
        page.set_viewport_size({"width": width, "height": 900})
        page.evaluate("document.fonts.ready")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        page.locator("a.skip").focus()
        page.keyboard.press("Enter")
        expect(page.locator("#main")).to_be_focused()
        path = evidence / f"crm-export-{locale}-{state}-{width}.png"
        page.screenshot(path=str(path), full_page=True)
        screenshots.append(str(path.relative_to(root)))


def download_csv(page, region, locale, identity):
    link = region.get_by_role("link", name=labels[locale]["download"], exact=True)
    expect(link).to_be_visible()
    link.focus()
    assert link.evaluate("element => element === document.activeElement")
    with page.expect_download() as downloaded:
        page.keyboard.press("Enter")
    assert downloaded.value.suggested_filename == f"crm-leads-{identity}.csv"
    path = evidence / f"crm-export-{locale}-{identity}.csv"
    downloaded.value.save_as(path)
    contents = path.read_bytes().decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(contents)))
    assert len(rows) == 3
    assert {row["name"] for row in rows} == {
        "'=SUM(1,1)",
        'Plain, quoted "lead"',
        "'  -2+3",
    }
    assert {row["phone"] for row in rows} == {"'+919000000001"}
    assert {row["campaign"] for row in rows} == {"First line\nSecond line"}
    assert "FOREIGN-ORG-EXCLUDED" not in contents
    response = page.request.get(base + exports_root + f"/{identity}/download")
    assert response.status == 200 and response.text() == contents
    assert response.headers["content-type"].startswith("text/csv")
    assert "no-store" in response.headers["cache-control"]
    assert not {"set-cookie", "x-bff-key", "authorization"}.intersection(
        response.headers
    )


def restore_export_permission():
    with Session(engine) as db:
        db.add(
            UserRole(
                user_id=actors["requester"]["user_id"],
                role_id=exporter_role_id,
                organization_id=org_id,
            )
        )
        db.commit()


with sync_playwright() as playwright:
    options = {"headless": True}
    if os.getenv("PLAYWRIGHT_CHANNEL"):
        options["channel"] = os.environ["PLAYWRIGHT_CHANNEL"]
    browser = playwright.chromium.launch(**options)
    try:
        requester = sign_in(browser, "requester")
        peer = sign_in(browser, "peer")
        reader = sign_in(browser, "reader")
        outsider = sign_in(browser, "outsider")
        for locale in ("en", "ta"):
            region = workspace(requester, locale)
            failed_id = request_export(requester, region, locale)
            with patch.object(
                export_service,
                "generate_csv",
                side_effect=export_service.ExportLimitError("output_too_large"),
            ):
                assert crm_exports.export_leads.run(str(failed_id)) == {
                    "status": "settled"
                }
            assert current(requester, failed_id)["error_code"] == "output_too_large"
            refresh(region, locale)
            expect(
                region.get_by_text(labels[locale]["failed"], exact=True)
            ).to_be_visible()
            expect(
                region.get_by_role("link", name=labels[locale]["download"], exact=True)
            ).to_have_count(0)
            responsive(requester, region, locale, "failed")

            identity = request_export(requester, region, locale)
            with patch.object(
                export_service,
                "generate_csv",
                side_effect=RuntimeError("Synthetic generation loss"),
            ):
                assert crm_exports.export_leads.run(str(identity)) == {
                    "status": "settled"
                }
            retry = current(requester, identity)
            assert (
                retry["status"] == "queued"
                and retry["error_code"] == "generation_failed"
            )
            refresh(region, locale)
            expect(region).to_contain_text(labels[locale]["retry"])
            responsive(requester, region, locale, "retrying")

            # Respect the real SQL due-time guard. No clock/trigger/row is weakened.
            deadline = time.monotonic() + 20
            while True:
                result = crm_exports.export_leads.run(str(identity))
                if result["status"] != "ignored":
                    break
                assert time.monotonic() < deadline, "Synthetic retry did not become due"
                time.sleep(0.2)
            assert result == {"status": "completed"}
            refresh(region, locale)
            expect(
                region.get_by_text(labels[locale]["completed"], exact=True)
            ).to_be_visible()
            download_csv(requester, region, locale, identity)
            with Session(engine) as db:
                row = db.get(ExportJob, identity)
                assert row is not None and row.attempt_count == 2
                version = row.version
            assert crm_exports.export_leads.run(str(identity)) == {"status": "ignored"}
            assert current(requester, identity) == current(requester, identity)
            with Session(engine) as db:
                row = db.get(ExportJob, identity)
                assert row is not None and row.version == version
                assert (
                    db.scalar(
                        select(func.count())
                        .select_from(AuditLog)
                        .where(
                            AuditLog.resource_id == identity,
                            AuditLog.action == "crm.lead.export_completed",
                        )
                    )
                    == 1
                )

            # Reload loses component memory. The real owner history must recover it.
            region = workspace(requester, locale)
            select_saved(region, identity)
            expect(
                region.get_by_role("link", name=labels[locale]["download"], exact=True)
            ).to_be_visible()
            responsive(requester, region, locale, "completed-history")

            # Lose exactly one successful server response after its real commit.
            committed = []
            before = count_jobs()
            post_count = requests.count(("POST", exports_root))

            def lose_committed_response(route):
                if route.request.method != "POST":
                    route.continue_()
                    return
                response = route.fetch()
                assert response.status == 202
                committed.append(UUID(response.json()["id"]))
                route.abort("failed")

            requester.route(base + exports_root, lose_committed_response, times=1)
            region.get_by_role(
                "button", name=labels[locale]["request"], exact=True
            ).click()
            expect(region.get_by_role("alert")).to_be_visible()
            assert len(committed) == 1 and count_jobs() == before + 1
            lost_id = committed[0]
            jobs.append(str(lost_id))
            select_saved(region, lost_id)
            expect(region.get_by_role("alert")).to_have_count(0)
            assert current(requester, lost_id)["status"] == "queued"
            requester.wait_for_timeout(3500)
            assert requests.count(("POST", exports_root)) == post_count + 1
            assert count_jobs() == before + 1
            assert crm_exports.export_leads.run(str(lost_id)) == {"status": "completed"}
            refresh(region, locale)
            download_csv(requester, region, locale, lost_id)

            detail = base + exports_root + f"/{lost_id}"
            for page, expected_status in ((peer, 404), (reader, 403), (outsider, 403)):
                assert page.request.get(detail).status == expected_status
                assert page.request.get(detail + "/download").status == expected_status
            history = peer.request.get(base + exports_root)
            assert history.status == 200 and history.json()["items"] == []
            assert outsider.request.get(base + exports_root).status == 403
            assert (
                requester.request.get(
                    base + f"/api/crm/organizations/{other_org_id}/exports/{lost_id}"
                ).status
                == 403
            )
            assert (
                requester.request.post(
                    base + exports_root, data={}, headers={"Origin": base}
                ).status
                == 403
            )

            with Session(engine) as db:
                db.execute(
                    delete(UserRole).where(
                        UserRole.user_id == actors["requester"]["user_id"],
                        UserRole.role_id == exporter_role_id,
                        UserRole.organization_id == org_id,
                    )
                )
                db.commit()
            assert requester.request.get(detail).status == 403
            assert requester.request.get(detail + "/download").status == 403
            refresh(region, locale)
            expect(region).to_contain_text(labels[locale]["no_access"])
            expect(
                region.get_by_role("link", name=labels[locale]["download"], exact=True)
            ).to_have_count(0)
            requester.reload()
            expect(
                requester.get_by_role(
                    "region", name=labels[locale]["title"], exact=True
                )
            ).to_have_count(0)
            restore_export_permission()
        assert not errors, errors
    finally:
        browser.close()
        engine.dispose()

record = {
    "recorded_at": now().isoformat(),
    "synthetic_only": True,
    "passed": True,
    "javascript_errors": len(errors),
    "locales": ["en", "ta"],
    "widths": [390, 1280],
    "jobs": jobs,
    "screenshots": screenshots,
    "direct_task_functions": True,
    "broker_worker_beat_acceptance": False,
    "coverage": [
        "actual sign-in/API/BFF export creation while Redis unavailable",
        "failure, bounded retry, completed download and formula-safe scoped bytes",
        "duplicate task/GET, owner history reload and committed lost-response recovery",
        "peer/permission/organization/CSRF/current-grant revocation negatives",
        "English/Tamil responsive keyboard journeys without JavaScript errors",
    ],
}
record_path = Path(os.environ["CRM_EXPORT_BROWSER_EVIDENCE"])
assert record_path.resolve().is_relative_to((root / ".local").resolve())
record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
print(
    "PASS: CRM export connected UI/history/recovery, failure/retry, real escaped CSV, "
    "scope/revocation/CSRF and EN/TA 390/1280 keyboard layouts. "
    "Direct task functions only; Redis/Celery worker/Beat runtime acceptance remains open.",
    flush=True,
)
