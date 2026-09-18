"""Synthetic browser E2E; run with isolated PostgreSQL and local servers only."""
import json
import os
import secrets
from pathlib import Path
from uuid import UUID, uuid4

from cryptography.fernet import Fernet
from playwright.sync_api import expect, sync_playwright
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.modules.identity.models import AuthDelivery, Organization, Role, User, UserRole, VerificationToken
from app.modules.identity.service import audit, seed_roles

engine = create_engine(os.environ["DATABASE_URL"])
assert engine.url.database in {"edp_foundation_e2e", "edp_test"}, "Isolated test DB required"
base = os.environ["WEB_ORIGIN"]
assert base.startswith(("http://127.0.0.1:", "http://localhost:"))
email = "synthetic-" + uuid4().hex[:12] + "@example.com"
password = secrets.token_urlsafe(24)


def latest_token(purpose):
    with Session(engine) as db:
        row = db.scalar(select(AuthDelivery).join(VerificationToken).join(User)
                        .where(User.email == email, VerificationToken.purpose == purpose)
                        .order_by(AuthDelivery.created_at.desc()).limit(1))
        assert row is not None
        return json.loads(Fernet(os.environ["AUTH_DELIVERY_KEY"].encode()).decrypt(row.encrypted_payload.encode()))["token"]


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel=os.getenv("PLAYWRIGHT_CHANNEL"), headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    pending = set()
    page.on("request", lambda request: pending.add(request.url))
    page.on("requestfinished", lambda request: pending.discard(request.url))
    page.on("requestfailed", lambda request: pending.discard(request.url))
    page.goto(base + "/en/admin")
    page.wait_for_url("**/en/account")
    # Next.js keeps background RSC prefetch requests open in this Chrome build.
    # The first run waited for networkidle and inspected a fully hydrated form.
    # Assert actual user-visible readiness instead of using background network quiescence.
    page.wait_for_load_state("domcontentloaded")
    expect(page.get_by_label("Email", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name="Your account")).to_be_visible()
    evidence = Path(".tool-cache/evidence")
    evidence.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(evidence / "account-en.png"), full_page=True)
    page.get_by_role("button", name="Create account", exact=True).click()
    page.get_by_label("Name", exact=True).fill("Synthetic E2E")
    page.get_by_label("Email", exact=True).fill(email)
    page.get_by_label("Password", exact=True).fill(password)
    page.locator("form").get_by_role("button", name="Create account", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("message has been queued")
    page.get_by_role("button", name="Verify email", exact=True).click()
    page.get_by_label("Verification or reset code", exact=True).fill(latest_token("verify"))
    page.locator("form").get_by_role("button", name="Verify email", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("You can now sign in")
    page.get_by_role("button", name="Sign in", exact=True).click()
    page.get_by_label("Email", exact=True).fill(email)
    page.get_by_label("Password", exact=True).fill(password)
    with page.expect_response(lambda response: response.url.endswith("/api/session/login")) as login_response:
        page.locator("form").get_by_role("button", name="Sign in", exact=True).click()
    assert login_response.value.json() == {"status": "signed_in"}
    expect(page.get_by_text("Synthetic E2E", exact=True)).to_be_visible()
    cookies = page.context.cookies()
    assert all(cookie["httpOnly"] and cookie["sameSite"] == "Strict" for cookie in cookies if cookie["name"] in {"edp_session", "edp_csrf"})
    assert page.evaluate("Object.keys(localStorage)") == []
    csrf = page.request.get(base + "/api/session/csrf").json()["csrf_token"]
    assert page.request.post(base + "/api/session/logout", data={}, headers={"Origin": "https://evil.example", "X-CSRF-Token": csrf}).status == 403
    assert page.request.post(base + "/api/session/logout", data={}, headers={"Origin": base}).status == 403
    with Session(engine) as db:
        seed_roles(db)
        user = db.scalar(select(User).where(User.email == email))
        role = db.scalar(select(Role).where(Role.name == "Super Admin"))
        organization = Organization(id=UUID(os.environ["PUBLIC_ORGANIZATION_ID"]), name="Synthetic E2E Organization")
        db.add(organization); db.flush()
        db.add(UserRole(user_id=user.id, role_id=role.id, organization_id=organization.id))
        audit(db, "system.role_granted", "synthetic-e2e", resource=user.id, organization=organization.id)
        db.commit()
        organization_id = organization.id
    page.reload(); page.wait_for_load_state("domcontentloaded")
    page.get_by_role("link", name="Synthetic E2E Organization", exact=True).click()
    expect(page.get_by_role("heading", name="Staff workspace")).to_be_visible()
    expect(page.get_by_text("system.role_granted", exact=False)).to_be_visible()
    assert page.request.get(base + "/api/session/staff/" + str(uuid4())).status == 403
    page.goto(base + "/en/admin/pages")
    expect(page.get_by_role("heading", name="Publishing workspace")).to_be_visible()
    page.get_by_label("Page address", exact=True).fill("eligibility")
    page.get_by_label("Title", exact=True).fill("Who can apply")
    page.get_by_label("Content", exact=True).fill("Synthetic eligibility <script>alert(1)</script>")
    page.get_by_role("button", name="Save draft", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Saved")
    assert page.request.get(os.environ["API_INTERNAL_URL"]+"/api/v1/public/organizations/"+str(organization_id)+"/pages/eligibility?locale=en").status == 404
    page.get_by_role("button",name="Preview saved draft",exact=True).click()
    expect(page.locator(".cms-preview")).to_contain_text("<script>alert(1)</script>")
    page.get_by_role("button",name="Publish saved draft",exact=True).click()
    expect(page.locator(".cms-state")).to_contain_text("Published")
    public = browser.new_page()
    public.goto(base+"/en/pages/eligibility")
    expect(public.get_by_role("heading",name="Who can apply")).to_be_visible()
    expect(public.locator(".cms-body")).to_contain_text("<script>alert(1)</script>")
    page.screenshot(path=str(evidence/"cms-debug.png"),full_page=True)
    page.get_by_label("Content",exact=True).fill("Unpublished change")
    page.get_by_role("button",name="Save draft",exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Saved")
    public.reload()
    expect(public.locator(".cms-body")).not_to_contain_text("Unpublished change")
    page.get_by_label("Content language").select_option("ta")
    page.get_by_label("Title",exact=True).fill("Tamil synthetic title")
    page.get_by_label("Content",exact=True).fill("Tamil synthetic content")
    page.get_by_role("button",name="Add translation",exact=True).click()
    expect(page.get_by_role("status")).to_have_text("Saved")
    assert page.request.get(os.environ["API_INTERNAL_URL"]+"/api/v1/public/organizations/"+str(organization_id)+"/pages/eligibility?locale=ta").status == 404
    page.get_by_role("button",name="Publish saved draft",exact=True).click()
    expect(page.locator(".cms-state")).to_contain_text("Published")
    public.goto(base+"/ta/pages/eligibility")
    expect(public.get_by_role("heading",name="Tamil synthetic title")).to_be_visible()
    page.get_by_label("Archive reason").fill("Synthetic archive")
    page.get_by_role("button",name="Archive",exact=True).click()
    expect(page.locator(".cms-state")).to_contain_text("Archived")
    assert page.request.get(os.environ["API_INTERNAL_URL"]+"/api/v1/public/organizations/"+str(organization_id)+"/pages/eligibility?locale=ta").status == 404
    page.set_viewport_size({"width":390,"height":844})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.screenshot(path=str(evidence/"cms-mobile.png"),full_page=True)
    page.set_viewport_size({"width":1280,"height":900})
    public.close()
    page.goto(base + "/en/admin?organization=" + str(uuid4()))
    expect(page.get_by_text("You do not have access to this workspace.")).to_be_visible()
    page.goto(base + "/en/account"); page.wait_for_load_state("domcontentloaded")
    page.get_by_role("button", name="Sign out all devices", exact=True).click()
    expect(page.get_by_label("Email", exact=True)).to_be_visible()
    assert page.request.get(base + "/api/session/me").status == 401
    page.get_by_role("button", name="Forgot password", exact=True).click()
    page.get_by_label("Email", exact=True).fill(email)
    page.locator("form").get_by_role("button", name="Forgot password", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("message has been queued")
    page.get_by_role("button", name="Reset password", exact=True).click()
    page.get_by_label("Verification or reset code", exact=True).fill(latest_token("reset"))
    new_password = secrets.token_urlsafe(24)
    page.get_by_label("Password", exact=True).fill(new_password)
    page.locator("form").get_by_role("button", name="Reset password", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("You can now sign in")
    page.get_by_role("button", name="Sign in", exact=True).click()
    page.get_by_label("Email", exact=True).fill(email)
    page.get_by_label("Password", exact=True).fill(new_password)
    page.locator("form").get_by_role("button", name="Sign in", exact=True).click()
    expect(page.get_by_text("Synthetic E2E", exact=True)).to_be_visible()
    page.get_by_role("button", name="Sign out", exact=True).click()
    expect(page.get_by_label("Email", exact=True)).to_be_visible()
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(base + "/ta/account"); page.wait_for_load_state("domcontentloaded")
    assert page.locator("html").get_attribute("lang") == "ta"
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.screenshot(path=str(evidence / "account-ta-mobile.png"), full_page=True)
    assert not errors, errors
    browser.close()
engine.dispose()
print("Browser E2E passed: register, verify, login, secure cookies, CSRF, scope denial, audit UI, logout-all, reset, Tamil mobile layout; no JS errors")
