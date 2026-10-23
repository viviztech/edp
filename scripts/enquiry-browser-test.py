"""Synthetic public-enquiry and staff-inbox acceptance against owned local servers."""

import os
import re
import secrets
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID, uuid4

from app.modules.cms.models import Enquiry
from app.modules.identity.models import Organization, Person, Role, User, UserRole
from app.modules.identity.security import hasher
from app.modules.identity.service import seed_roles
from playwright.sync_api import expect, sync_playwright
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

engine = create_engine(os.environ["DATABASE_URL"])
assert engine.url.database in {"edp_foundation_e2e", "edp_web_journey_e2e"}
base = os.environ["WEB_ORIGIN"]
api = os.environ["API_INTERNAL_URL"]
assert urlparse(base).hostname in {"127.0.0.1", "localhost"}
assert urlparse(api).hostname in {"127.0.0.1", "localhost"}
assert urlparse(base).scheme == urlparse(api).scheme == "http"
assert os.environ.get("CONTACT_ENQUIRIES_ENABLED") == "true"
org = UUID(os.environ["PUBLIC_ORGANIZATION_ID"])
suffix = uuid4().hex[:12]
staff_email = f"enquiry-staff-{suffix}@example.com"
password = secrets.token_urlsafe(24)
staff_name = "Synthetic enquiry executive " + suffix
with Session(engine) as db:
    seed_roles(db)
    assert db.get(Organization, org), "Run after the applicant journey seeds its organization"
    person = Person(display_name=staff_name)
    db.add(person)
    db.flush()
    actor = User(
        person_id=person.id,
        email=staff_email,
        password_hash=hasher.hash(password),
        status="active",
    )
    db.add(actor)
    db.flush()
    role = db.scalar(select(Role).where(Role.name == "Support Executive"))
    assert role
    db.add(UserRole(user_id=actor.id, role_id=role.id, organization_id=org))
    db.commit()

evidence = Path(".tool-cache/evidence")
evidence.mkdir(parents=True, exist_ok=True)
errors = []


def responsive(page, name):
    for width in (360, 390, 768, 1280):
        page.set_viewport_size({"width": width, "height": 900})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        page.locator("a.skip").focus()
        page.keyboard.press("Enter")
        assert page.evaluate("document.activeElement.id") == "main"
        page.screenshot(path=str(evidence / f"enquiry-{name}-{width}.png"), full_page=True)


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel=os.getenv("PLAYWRIGHT_CHANNEL"), headless=True)
    try:
        public_context = browser.new_context(viewport={"width": 1280, "height": 900})
        public = public_context.new_page()
        public.on("pageerror", lambda error: errors.append(type(error).__name__))
        reference = None
        for locale in ("en", "ta"):
            public.goto(base + f"/{locale}/pages/contact")
            expect(public.locator("html")).to_have_attribute("lang", locale)
            form = public.get_by_role(
                "form", name="Send an enquiry" if locale == "en" else "விசாரணை அனுப்பவும்"
            )
            expect(form).to_be_visible()
            submit = form.get_by_role(
                "button", name="Send enquiry" if locale == "en" else "விசாரணை அனுப்பு"
            )
            expect(submit).to_be_disabled()
            form.locator("input[name=name]").fill("Synthetic public enquirer " + suffix)
            form.locator("input[name=email]").fill(f"enquiry-{locale}-{suffix}@example.com")
            form.locator("textarea[name=message]").fill("Synthetic private question " + locale)
            consent = os.environ["CONTACT_CONSENT_TEXT_" + locale.upper()]
            form.get_by_label(consent, exact=True).check()
            expect(form.get_by_role("link")).to_have_attribute(
                "href", os.environ["CONTACT_PRIVACY_NOTICE_URL_" + locale.upper()]
            )
            responsive(public, "public-" + locale)
            with public.expect_response(
                lambda response: response.url.endswith("/api/enquiries/public")
            ) as accepted:
                submit.click()
            assert accepted.value.status == 202
            receipt = accepted.value.json()
            assert set(receipt) == {"accepted", "reference"}
            UUID(receipt["reference"])
            if locale == "en":
                reference = receipt["reference"]
            expect(public.get_by_text(receipt["reference"], exact=True)).to_be_visible()
            expect(public.locator("input[name=email]")).to_have_count(0)
            assert os.environ["BFF_KEY"] not in public.content()
        assert reference
        staff_base = f"/api/enquiries/organizations/{org}/enquiries"
        assert public.request.get(base + staff_base + "/queue").status == 401
        assert (
            public.request.post(
                base + "/api/enquiries/public", data={}, headers={"Origin": base}
            ).status
            == 403
        )

        staff_context = browser.new_context(viewport={"width": 1280, "height": 900})
        staff = staff_context.new_page()
        staff.on("pageerror", lambda error: errors.append(type(error).__name__))
        staff.goto(base + "/en/account")
        staff.get_by_label("Email", exact=True).fill(staff_email)
        staff.get_by_label("Password", exact=True).fill(password)
        staff.locator("form").get_by_role("button", name="Sign in", exact=True).click()
        expect(staff.get_by_text(staff_name, exact=True)).to_be_visible()
        staff.goto(base + f"/en/admin?organization={org}")
        staff.get_by_role("link", name="Enquiry inbox", exact=False).click()
        expect(staff.get_by_role("heading", name="Enquiry inbox", exact=True)).to_be_visible()
        staff.get_by_role("button", name=re.compile("^Synthetic public enquirer")).first.click()
        detail = staff.get_by_role("region", name="Enquiry details", exact=True)
        expect(detail.get_by_text("Synthetic private question", exact=False)).to_be_visible()
        chosen_id = None
        with Session(engine) as db:
            chosen = db.scalar(
                select(Enquiry).where(
                    Enquiry.organization_id == org,
                    Enquiry.email == detail.locator("dd").first.inner_text(),
                )
            )
            assert chosen
            chosen_id = str(chosen.id)
        staff.get_by_role("button", name="Mark reviewed", exact=True).click()
        expect(detail.get_by_role("button", name="Close enquiry", exact=True)).to_be_enabled()
        token = staff.request.get(base + "/api/session/csrf").json()["csrf_token"]
        headers = {"Origin": base, "X-CSRF-Token": token}
        stale = staff.request.post(
            base + staff_base + f"/{chosen_id}/status",
            data={"expected_version": 1, "status": "reviewed"},
            headers=headers,
        )
        assert stale.status == 409
        assert (
            staff.request.post(
                base + staff_base + f"/{chosen_id}/status",
                data={"expected_version": 2, "status": "closed"},
                headers=headers | {"Origin": "https://unrelated.example"},
            ).status
            == 403
        )
        assert staff.request.get(base + staff_base + f"/{chosen_id}/notes").status == 404
        staff.get_by_role("button", name="Close enquiry", exact=True).click()
        expect(detail.get_by_role("button", name="Close enquiry", exact=True)).to_have_count(0)
        staff.get_by_role("combobox", name="Status", exact=True).select_option("closed")
        expect(
            staff.get_by_role("button", name=re.compile("^Synthetic public enquirer"))
        ).to_have_count(1)
        responsive(staff, "staff-en")
        staff.goto(base + f"/ta/admin/enquiries?organization={org}")
        expect(staff.get_by_role("heading", name="விசாரணைப் பெட்டி", exact=True)).to_be_visible()
        expect(staff.get_by_role("combobox", name="நிலை", exact=True)).to_be_visible()
        responsive(staff, "staff-ta")
        with Session(engine) as db:
            record = db.get(Enquiry, UUID(chosen_id))
            assert record and record.status == "closed" and record.version == 3
        assert not errors, errors
    finally:
        browser.close()
        engine.dispose()

print(
    "PASS: anonymous bilingual consent/enquiry/receipt; scoped staff navigation and "
    "review/close lifecycle; stale version, anonymous, CSRF, cross-origin and closed-route "
    "negatives; responsive public/staff English/Tamil and keyboard skip links; no JS errors"
)
