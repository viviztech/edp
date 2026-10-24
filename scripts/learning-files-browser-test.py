"""Synthetic LMS file acceptance in an isolated database; no real providers."""

import faulthandler
import hashlib
import os
import secrets
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID, uuid4

from playwright.sync_api import expect, sync_playwright
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.applications.models import Application, ApplicationForm
from app.modules.files import service as files
from app.modules.files.runtime import get_private_storage
from app.modules.files.scanner import ScanResult
from app.modules.files.schemas import FilePolicyCommand, FilePolicyCreate
from app.modules.identity.models import (
    Organization,
    Person,
    Role,
    User,
    UserRole,
    now,
)
from app.modules.identity.security import hasher
from app.modules.identity.service import seed_roles
from app.modules.lms.file_models import AssignmentFile, MaterialFile
from app.modules.programs.models import (
    ApplicationCycle,
    Cohort,
    Enrollment,
    Participant,
    Program,
    ProgramStaffAssignment,
    TrainingCenter,
)

faulthandler.dump_traceback_later(60, repeat=True)
engine = create_engine(os.environ["DATABASE_URL"])
assert engine.url.database == "edp_learning_files_e2e"
assert engine.url.host in {"127.0.0.1", "localhost"}
base = os.environ["WEB_ORIGIN"]
api = os.environ["API_INTERNAL_URL"]
assert urlparse(base).hostname in {"127.0.0.1", "localhost"}
assert urlparse(api).hostname in {"127.0.0.1", "localhost"}
assert urlparse(base).port == 3112 and urlparse(api).port == 8112
settings = get_settings()
assert settings.files_enabled and not settings.files_maintenance_enabled
assert settings.files_storage_backend == "local" and settings.files_max_bytes == 2048
assert settings.clamav_host is None
org_id = UUID(os.environ["PUBLIC_ORGANIZATION_ID"])
suffix = uuid4().hex[:12]
actors = {
    key: {
        "email": f"l01-{key}-{suffix}@example.com",
        "password": secrets.token_urlsafe(24),
    }
    for key in ("author", "owner", "peer", "trainer")
}

# Seed synthetic identities and active program enrollments only. Course authoring,
# attachment commands, submission and delivery below use the running application.
with Session(engine) as db:
    seed_roles(db)
    org = Organization(id=org_id, name="Synthetic learning files " + suffix)
    db.add(org)
    db.flush()
    for key, credentials in actors.items():
        person = Person(display_name="Synthetic L01 " + key)
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
        credentials["person_id"] = person.id
        role = db.scalar(
            select(Role).where(
                Role.name
                == (
                    "Program Director"
                    if key == "author"
                    else "Trainer"
                    if key == "trainer"
                    else "Participant"
                )
            )
        )
        assert role
        db.add(UserRole(user_id=user.id, role_id=role.id, organization_id=org_id))
    program = Program(
        organization_id=org_id,
        code="synthetic-learning",
        name_en="Synthetic learning program",
        name_ta="செயற்கை கற்றல் திட்டம்",
        state="active",
    )
    center = TrainingCenter(
        organization_id=org_id,
        code="synthetic-learning-center",
        name_en="Synthetic learning center",
        name_ta="செயற்கை கற்றல் மையம்",
        locality="Synthetic locality",
    )
    form = ApplicationForm(
        organization_id=org_id,
        version=1,
        state="published",
        title_en="Synthetic learning intake",
        title_ta="செயற்கை கற்றல் சேர்க்கை",
        published_at=now(),
        published_by_id=actors["author"]["user_id"],
    )
    db.add_all([program, center, form])
    db.flush()
    cohort = Cohort(
        organization_id=org_id,
        program_id=program.id,
        center_id=center.id,
        code="synthetic-learning-cohort",
        name_en="Synthetic learning cohort",
        name_ta="செயற்கை கற்றல் குழு",
        starts_on=now().date(),
        ends_on=now().date() + timedelta(days=90),
        state="active",
    )
    db.add(cohort)
    db.flush()
    cohort_id = cohort.id
    assignment_scope = ProgramStaffAssignment(
        organization_id=org_id,
        user_id=actors["trainer"]["user_id"],
        center_id=center.id,
        cohort_id=cohort_id,
    )
    db.add(assignment_scope)
    cycle = ApplicationCycle(
        organization_id=org_id,
        program_id=program.id,
        cohort_id=cohort_id,
        form_id=form.id,
        code="synthetic-learning-cycle",
        name_en="Synthetic learning cycle",
        name_ta="செயற்கை கற்றல் சுற்று",
        opens_at=now() - timedelta(days=30),
        closes_at=now() - timedelta(days=1),
        state="closed",
    )
    db.add(cycle)
    db.flush()
    for key in ("owner", "peer"):
        application = Application(
            organization_id=org_id,
            person_id=actors[key]["person_id"],
            form_id=form.id,
            cycle_id=cycle.id,
            state="enrolled",
            version=8,
            application_number=f"L01-{key}-{suffix}",
            submitted_at=now() - timedelta(days=20),
        )
        participant = Participant(
            organization_id=org_id,
            person_id=actors[key]["person_id"],
            status="active",
        )
        db.add_all([application, participant])
        db.flush()
        db.add(
            Enrollment(
                organization_id=org_id,
                participant_id=participant.id,
                program_id=program.id,
                cohort_id=cohort_id,
                application_id=application.id,
                status="active",
            )
        )
    db.flush()
    trainer_scope_id = assignment_scope.id
    db.commit()

    author = db.get(User, actors["author"]["user_id"])
    policies = {}
    for purpose in ("assignment_submission", "lms_material"):
        policy = files.create_policy(
            db,
            org_id,
            author,
            FilePolicyCreate(
                client_request_id=uuid4(),
                purpose=purpose,
                name="Synthetic " + purpose,
                notice_en="Synthetic learning files only. No real personal information.",
                notice_ta="செயற்கை கற்றல் கோப்புகள் மட்டும். உண்மையான தகவல்கள் வேண்டாம்.",
                allowed_mime_types=["application/pdf"],
                max_file_bytes=1024,
                max_files=2,
                retention_days=1,
                rejected_retention_days=1,
                allow_frozen_disposal=False,
                reason="Synthetic browser fixture",
            ),
            "synthetic-browser-policy",
        )
        files.publish_policy(
            db,
            org_id,
            policy.id,
            author,
            FilePolicyCommand(expected_version=1, reason="Synthetic browser only"),
            "synthetic-browser-policy-publish",
        )
        policies[purpose] = str(policy.id)

root = base + f"/api/courses/organizations/{org_id}"
content = b"%PDF-1.4\nSynthetic private learning file only.\n%%EOF"
errors = []
evidence = Path(".tool-cache/evidence")
evidence.mkdir(parents=True, exist_ok=True)


def sign_in(browser, key):
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on(
        "dialog",
        lambda dialog: (
            dialog.accept("Synthetic reviewed publication")
            if dialog.type == "prompt"
            else dialog.accept()
        ),
    )
    page.goto(base + "/en/account")
    page.get_by_label("Email", exact=True).fill(actors[key]["email"])
    page.get_by_label("Password", exact=True).fill(actors[key]["password"])
    with page.expect_response(
        lambda response: response.url.endswith("/api/session/login")
    ) as result:
        page.locator("form").get_by_role("button", name="Sign in", exact=True).click()
    assert result.value.status == 200
    expect(page.get_by_text("Synthetic L01 " + key, exact=True)).to_be_visible()
    return page


def mutate(page, path, data=None, method="POST"):
    csrf = page.request.get(base + "/api/session/csrf").json()["csrf_token"]
    return page.request.fetch(
        root + path,
        method=method,
        data=data,
        headers={"Origin": base, "X-CSRF-Token": csrf},
    )


def checked(response, expected=201):
    assert response.status == expected, response.text()[:1000]
    return response.json()


class SyntheticScanner:
    def scan(self, source, *, max_bytes):
        data = source.read(max_bytes + 1)
        assert data == content
        return ScanResult("clean", hashlib.sha256(data).hexdigest(), len(data), "synthetic_fixture")


def scan(file_id):
    # Only this isolated fixture injects the scanner; the API has no fake-clean
    # runtime mode, scanner connection or real provider activation.
    with Session(engine) as db:
        lease = files.claim_scan(db, org_id, UUID(file_id), "synthetic-browser-claim")
        result = files.scan_with_lease(
            db,
            org_id,
            lease,
            get_private_storage(),
            SyntheticScanner(),
            "synthetic-browser-scan",
        )
        assert result.state == "clean"


def choose_file(region, name):
    region.get_by_label("Select file", exact=True).set_input_files(
        {"name": name, "mimeType": "application/pdf", "buffer": content}
    )


def responsive(page, route, heading, name):
    page.goto(base + route)
    expect(page.get_by_role("heading", name=heading, exact=True)).to_be_visible()
    tamil = route.startswith("/ta/")
    region_name = (
        ("தனிப்பட்ட கற்றல் கோப்புகள்" if tamil else "Private learning files")
        if name.startswith("author")
        else ("பணிக்கான கோப்புகள்" if tamil else "Assignment files")
    )
    download_name = "சரிபார்த்த கோப்பைப் பதிவிறக்கு" if tamil else "Download verified file"
    # The server heading renders before the client loads its course and file
    # widgets. Inspect the populated saved state at every width, not a skeleton.
    files_region = page.get_by_role("region", name=region_name, exact=True).first
    expect(files_region.get_by_role("link", name=download_name, exact=True)).to_be_visible()
    for width in (360, 390, 768, 1280):
        page.set_viewport_size({"width": width, "height": 900})
        expect(page.locator("main#main")).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), (
            f"{name} overflows at {width}"
        )
        page.locator("a.skip").focus()
        expect(page.locator("a.skip")).to_be_focused()
        page.keyboard.press("Enter")
        expect(page.locator("main#main")).to_be_focused()
        page.screenshot(path=str(evidence / f"learning-files-{name}-{width}.png"), full_page=True)


with sync_playwright() as playwright:
    channel = os.getenv("PLAYWRIGHT_CHANNEL", "chrome")
    browser = playwright.chromium.launch(headless=True, **({"channel": channel} if channel else {}))
    author = sign_in(browser, "author")
    print("LMS browser: author signed in", flush=True)
    course = checked(
        mutate(
            author,
            "",
            {
                "code": "synthetic-files-" + suffix,
                "title_en": "Synthetic secure learning",
                "title_ta": "செயற்கை பாதுகாப்பான கற்றல்",
                "description_en": "Synthetic browser acceptance only.",
                "description_ta": "செயற்கை உலாவி சோதனை மட்டும்.",
            },
        )
    )
    course_id = course["id"]
    module = checked(
        mutate(
            author,
            "/modules",
            {
                "course_id": course_id,
                "position": 1,
                "title_en": "Synthetic module",
                "title_ta": "செயற்கை தொகுதி",
            },
        )
    )
    lesson = checked(
        mutate(
            author,
            "/lessons",
            {
                "course_id": course_id,
                "module_id": module["id"],
                "position": 1,
                "title_en": "Synthetic lesson",
                "title_ta": "செயற்கை பாடப்பகுதி",
                "body_en": "Synthetic evidence lesson.",
                "body_ta": "செயற்கை சான்றுப் பகுதி.",
            },
        )
    )
    assignments = []
    for position, name in ((1, "Evidence"), (2, "Text-only")):
        assignments.append(
            checked(
                mutate(
                    author,
                    "/assignments",
                    {
                        "course_id": course_id,
                        "lesson_id": lesson["id"],
                        "position": position,
                        "title_en": f"Synthetic {name} assignment",
                        "title_ta": f"செயற்கை பணி {position}",
                        "instructions_en": "Synthetic response only.",
                        "instructions_ta": "செயற்கை பதில் மட்டும்.",
                        "maximum_points": 10,
                        "passing_points": 5,
                        "max_submissions": 2,
                    },
                )
            )
        )
    assignment_id = assignments[0]["id"]
    author.goto(base + f"/en/admin/learning?organization={org_id}")
    rule = author.get_by_role("region", name="Assignment file rules", exact=True).first
    expect(rule.get_by_label("Minimum files", exact=True)).to_have_value("")
    expect(rule.get_by_label("Maximum files", exact=True)).to_have_value("")
    rule.get_by_role("combobox", name="Published file policy", exact=True).select_option(
        policies["assignment_submission"]
    )
    rule.get_by_label("Minimum files", exact=True).fill("1")
    rule.get_by_label("Maximum files", exact=True).fill("2")
    with author.expect_response(
        lambda response: response.url.endswith("/file-rule") and response.request.method == "PUT"
    ) as configured:
        rule.get_by_role("button", name="Save file rules", exact=True).click()
    assert configured.value.status == 200, configured.value.text()

    materials = author.get_by_role("region", name="Private learning files", exact=True)
    materials.get_by_role("combobox", name="Lesson", exact=True).select_option(lesson["id"])
    materials.get_by_role("combobox", name="Published file policy", exact=True).select_option(
        policies["lms_material"]
    )
    materials.get_by_label("Material position", exact=True).fill("1")
    materials.get_by_label("English file label", exact=True).fill("Synthetic handout")
    materials.get_by_label("Tamil file label", exact=True).fill("செயற்கை கையேடு")
    choose_file(materials, "synthetic-handout.pdf")
    with author.expect_response(
        lambda response: (
            "/material-files/" in response.url
            and response.url.endswith("/content")
            and response.request.method == "PUT"
        )
    ) as uploaded:
        materials.get_by_role("button", name="Upload selected file", exact=True).click()
    assert uploaded.value.status == 200, uploaded.value.text()
    material_binding = uploaded.value.json()
    assert not material_binding["usable"]
    scan(material_binding["file"]["id"])
    materials.get_by_role("button", name="Refresh saved files", exact=True).click()
    expect(materials.get_by_role("link", name="Download verified file")).to_be_visible()

    # An abandoned material intent can be explicitly removed without deleting
    # history or reserving a misleading active downloadable material.
    abandoned = checked(
        mutate(
            author,
            "/material-files",
            {
                "client_request_id": str(uuid4()),
                "policy_id": policies["lms_material"],
                "course_id": course_id,
                "lesson_id": lesson["id"],
                "position": 2,
                "label_en": "Synthetic abandoned material",
                "label_ta": "செயற்கை முடிக்காத கோப்பு",
                "media_type": "application/pdf",
                "byte_size": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            },
        )
    )
    materials.get_by_role("button", name="Refresh saved files", exact=True).click()
    abandoned_row = materials.locator("li").filter(has_text="Awaiting upload")
    with author.expect_response(
        lambda response: (
            response.url.endswith("/" + abandoned["material_id"])
            and response.request.method == "DELETE"
        )
    ) as removed:
        abandoned_row.get_by_role("button", name="Remove staged file", exact=True).click()
    assert removed.value.status == 200, removed.value.text()
    expect(materials.get_by_text("Removed from the course", exact=True)).to_be_visible()
    publish = author.get_by_role("button", name="Publish course", exact=True)
    expect(publish).to_be_enabled()
    with author.expect_response(
        lambda response: response.url.endswith(f"/{course_id}/publish")
    ) as published:
        publish.click()
    assert published.value.status == 200, published.value.text()
    print("LMS browser: explicit rules and verified material published", flush=True)
    checked(
        mutate(
            author,
            "/cohort-assignments",
            {
                "course_id": course_id,
                "cohort_id": str(cohort_id),
                "position": 1,
                "reason": "Synthetic learning assignment",
            },
        )
    )

    owner = sign_in(browser, "owner")
    print("LMS browser: learner signed in", flush=True)
    owner.goto(base + f"/en/learning?organization={org_id}")
    with owner.expect_response(
        lambda response: response.url.endswith(f"/{course_id}/start")
    ) as started:
        owner.get_by_role("button", name="Start course", exact=True).click()
    assert started.value.status == 200
    assignment = owner.locator("form.learning-private").filter(
        has=owner.get_by_text("Synthetic Evidence assignment", exact=True)
    )
    attachments = assignment.get_by_role("region", name="Assignment files", exact=True)
    submit = assignment.get_by_role("button", name="Submit assignment", exact=True)
    expect(submit).to_be_disabled()
    assignment.get_by_role("textbox", name="Your response", exact=True).fill(
        "Synthetic response preserved through a lost metadata reply."
    )
    file_path = f"/my-learning/{course_id}/assignments/{assignment_id}/files"
    posted_payloads = []

    def lost_create(route):
        if route.request.method != "POST":
            route.continue_()
            return
        posted_payloads.append(route.request.post_data_json)
        response = route.fetch()
        if len(posted_payloads) == 1:
            assert response.status == 201
            route.abort("failed")
        else:
            route.fulfill(response=response)

    owner.route("**/api/courses/organizations/*" + file_path, lost_create)
    choose_file(attachments, "synthetic-assignment.pdf")
    attachments.get_by_role("button", name="Upload selected file", exact=True).click()
    expect(
        attachments.get_by_role("button", name="Retry the same metadata request")
    ).to_be_visible()
    with owner.expect_response(
        lambda response: response.url.endswith("/content") and response.request.method == "PUT"
    ) as uploaded:
        attachments.get_by_role(
            "button", name="Retry the same metadata request", exact=True
        ).click()
    assert uploaded.value.status == 200, uploaded.value.text()
    print("LMS browser: lost metadata recovered and learner bytes uploaded", flush=True)
    assert len(posted_payloads) == 2 and posted_payloads[0] == posted_payloads[1]
    owner.unroute("**/api/courses/organizations/*" + file_path, lost_create)
    binding = uploaded.value.json()
    expect(submit).to_be_disabled()
    assert owner.request.get(root + file_path + f"/{binding['id']}/content").status == 409
    scan(binding["file"]["id"])
    attachments.get_by_role("button", name="Refresh saved files", exact=True).click()
    selection = attachments.get_by_role("checkbox", name="Include file", exact=False)
    expect(selection).to_be_enabled()
    expect(selection).not_to_be_checked()
    selection.check()
    expect(submit).to_be_enabled()
    expect(assignment.get_by_role("textbox", name="Your response", exact=True)).to_have_value(
        "Synthetic response preserved through a lost metadata reply."
    )
    with owner.expect_response(
        lambda response: response.url.endswith(f"/{assignment_id}/submissions")
    ) as submitted:
        submit.click()
    print("LMS browser: submission response received", flush=True)
    assert submitted.value.status == 201, submitted.value.text()
    assert submitted.value.request.post_data_json["file_ids"] == [binding["id"]]
    # The page intentionally refreshes its saved pathway after a command. Verify
    # the same authoritative read rather than requesting a DevTools body for a
    # fetch response that the page did not consume.
    saved_learning = checked(owner.request.get(root + "/my-learning"), 200)
    saved_course = next(row for row in saved_learning["courses"] if row["id"] == course_id)
    saved_assignment = next(
        row
        for module in saved_course["modules"]
        for lesson in module["lessons"]
        for row in lesson["assignments"]
        if row["id"] == assignment_id
    )
    assert len(saved_assignment["submissions"]) == 1
    submission = saved_assignment["submissions"][0]
    assert submission["response_text"] == (
        "Synthetic response preserved through a lost metadata reply."
    )
    print("LMS browser: immutable persisted submission verified", flush=True)
    expect(attachments.get_by_text("Immutable submitted evidence", exact=False)).to_be_visible()
    print("LMS browser: immutable receipt visible", flush=True)
    with owner.expect_download(timeout=15000) as downloaded:
        attachments.get_by_role("link", name="Download verified file", exact=True).click()
    print("LMS browser: learner download event received", flush=True)
    assert Path(downloaded.value.path()).read_bytes() == content
    print("LMS browser: learner downloaded bytes verified", flush=True)

    # The independent assignment with no configured rule stays text-only.
    text_only = owner.locator("form.learning-private").filter(
        has=owner.get_by_text("Synthetic Text-only assignment", exact=True)
    )
    text_only.get_by_role("textbox", name="Your response", exact=True).fill(
        "Synthetic text-only compatibility response."
    )
    expect(text_only.get_by_role("button", name="Submit assignment", exact=True)).to_be_enabled()

    peer = sign_in(browser, "peer")
    checked(mutate(peer, f"/my-learning/{course_id}/start"), 200)
    assert peer.request.get(root + file_path + f"/{binding['id']}").status in {403, 404}
    assert peer.request.get(root + file_path + f"/{binding['id']}/content").status in {403, 404}
    assert checked(peer.request.get(root + file_path), 200)["items"] == []
    assert owner.request.get(root + file_path + "?cursor=" + str(uuid4())).status == 404
    assert owner.request.get(root + file_path + f"/{binding['id']}/unsafe").status == 404

    trainer = sign_in(browser, "trainer")
    print("LMS browser: peer scope verified; trainer signed in", flush=True)
    trainer.goto(base + f"/en/admin/learning?organization={org_id}")
    receipt = trainer.get_by_role("region", name="Immutable submitted evidence", exact=True)
    expect(receipt.get_by_role("link", name="Download verified file", exact=True)).to_be_visible()
    with trainer.expect_download(timeout=15000) as downloaded:
        receipt.get_by_role("link", name="Download verified file", exact=True).click()
    assert Path(downloaded.value.path()).read_bytes() == content
    trainer_path = f"/trainer-delivery/{course_id}/assignment-submissions/{submission['id']}/files"
    # Current assignment revocation is enforced after a receipt was visible.
    with Session(engine) as db:
        scope = db.get(ProgramStaffAssignment, trainer_scope_id)
        scope.state = "revoked"
        scope.revoked_at = now()
        scope.version += 1
        db.commit()
    assert trainer.request.get(root + trainer_path).status == 403
    assert trainer.request.get(root + trainer_path + f"/{binding['id']}/content").status == 403
    receipt.get_by_role("button", name="Refresh saved files", exact=True).click()
    expect(receipt.get_by_role("link", name="Download verified file", exact=True)).to_have_count(0)

    for locale, learner_heading, admin_heading in (
        ("en", "My learning path", "Course studio"),
        ("ta", "எனது கற்றல் பாதை", "பாடநெறி உருவாக்கம்"),
    ):
        responsive(
            owner,
            f"/{locale}/learning?organization={org_id}",
            learner_heading,
            "learner-" + locale,
        )
        responsive(
            author,
            f"/{locale}/admin/learning?organization={org_id}",
            admin_heading,
            "author-" + locale,
        )
    with Session(engine) as db:
        saved = db.get(AssignmentFile, UUID(binding["id"]))
        material = db.scalar(
            select(MaterialFile).where(
                MaterialFile.material_id == UUID(material_binding["material_id"])
            )
        )
        assert saved.state == "submitted" and material.state == "active"
    assert not errors, errors
    browser.close()
faulthandler.cancel_dump_traceback_later()
print(
    "Learning files Chrome PASS: explicit rules, material upload/removal, "
    "lost metadata recovery, clean selection/freeze, text-only compatibility, "
    "peer/trainer scope, EN/TA four-width layout, no JavaScript errors."
)
