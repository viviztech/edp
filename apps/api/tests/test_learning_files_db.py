import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager, contextmanager
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_identity import auth  # noqa: F401
from test_lms_db import learning_context

from app.core.config import get_settings
from app.modules.applications.models import Application
from app.modules.files import service as files
from app.modules.files.models import FileObject
from app.modules.files.runtime import get_private_storage
from app.modules.files.scanner import ScanResult
from app.modules.files.schemas import FilePolicyCommand, FilePolicyCreate
from app.modules.identity.models import Person, RefreshSession, Role, User, UserRole, now
from app.modules.identity.security import AuthError, hasher
from app.modules.lms import file_service
from app.modules.lms import service as learning
from app.modules.lms.file_models import AssignmentFile, MaterialFile
from app.modules.lms.file_schemas import AssignmentFileIntent, MaterialFileIntent
from app.modules.lms.models import AssignmentSubmission, CourseEnrollment
from app.modules.lms.schemas import PublishCourse
from app.modules.programs.models import Enrollment, Participant

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)
PDF = b"%PDF-1.4\n" + b"Synthetic private learning evidence\n" * 8000 + b"%%EOF"


def checked(response, status=201):
    assert response.status_code == status, response.text[:500]
    return response.json()


@pytest.fixture
def learning_files(request, tmp_path):
    context = learning_context(request)
    auth_context, headers, org, other, cohort, enrollment, user = context
    client, engine, _, _ = auth_context
    temp = tmp_path / "private-temp"
    temp.mkdir(mode=0o700)
    settings = get_settings()
    settings.files_enabled = True
    settings.files_storage_backend = "local"
    settings.files_local_root = str(tmp_path / "objects")
    settings.files_temp_root = str(temp)
    root = f"/api/v1/courses/organizations/{org}"
    course = checked(
        client.post(
            root,
            headers=headers,
            json={
                "code": "synthetic-file-course",
                "title_en": "Synthetic course",
                "title_ta": "செயற்கை பாடம்",
                "description_en": "Synthetic test course only",
                "description_ta": "செயற்கை சோதனை மட்டுமே",
            },
        )
    )
    module = checked(
        client.post(
            root + "/modules",
            headers=headers,
            json={
                "course_id": course["id"],
                "position": 1,
                "title_en": "Synthetic module",
                "title_ta": "செயற்கை தொகுதி",
            },
        )
    )
    lesson = checked(
        client.post(
            root + "/lessons",
            headers=headers,
            json={
                "course_id": course["id"],
                "module_id": module["id"],
                "position": 1,
                "title_en": "Synthetic lesson",
                "title_ta": "செயற்கை வகுப்பு",
                "body_en": "Synthetic test",
                "body_ta": "செயற்கை சோதனை",
                "duration_minutes": 10,
            },
        )
    )
    assignment = checked(
        client.post(
            root + "/assignments",
            headers=headers,
            json={
                "course_id": course["id"],
                "lesson_id": lesson["id"],
                "position": 1,
                "title_en": "Synthetic assignment",
                "title_ta": "செயற்கை பயிற்சி",
                "instructions_en": "Synthetic evidence",
                "instructions_ta": "செயற்கை சான்று",
                "maximum_points": 10,
                "passing_points": 5,
                "max_submissions": 2,
            },
        )
    )
    return {
        "client": client,
        "engine": engine,
        "headers": headers,
        "org": org,
        "other": other,
        "cohort": cohort,
        "enrollment": enrollment,
        "user": user,
        "root": root,
        "course": course["id"],
        "lesson": lesson["id"],
        "assignment": assignment["id"],
    }


def policy(f, purpose="assignment_submission"):
    with Session(f["engine"]) as db:
        actor = db.get(User, f["user"])
        created = files.create_policy(
            db,
            f["org"],
            actor,
            FilePolicyCreate(
                client_request_id=uuid4(),
                purpose=purpose,
                name="Synthetic learning policy",
                notice_en="Synthetic fixture only",
                notice_ta="செயற்கை சோதனை மட்டுமே",
                allowed_mime_types=["application/pdf"],
                max_file_bytes=500000,
                max_files=2,
                retention_days=1,
                rejected_retention_days=1,
                allow_frozen_disposal=False,
                reason="Synthetic test configuration",
            ),
            "policy-create",
        )
        return files.publish_policy(
            db,
            f["org"],
            created.id,
            actor,
            FilePolicyCommand(expected_version=1, reason="Synthetic test publication"),
            "policy-publish",
        )


def publish_and_start(f, *, rule=True):
    client, headers, root, course = f["client"], f["headers"], f["root"], f["course"]
    if rule:
        configured = policy(f)
        checked(
            client.put(
                root + f"/courses/{course}/assignments/{f['assignment']}/file-rule",
                headers=headers,
                json={"policy_id": str(configured.id), "minimum_files": 1, "maximum_files": 2},
            ),
            200,
        )
    checked(
        client.post(
            root + f"/{course}/publish",
            headers=headers,
            json={"expected_version": 1, "reason": "Synthetic course publication"},
        ),
        200,
    )
    checked(
        client.post(
            root + "/cohort-assignments",
            headers=headers,
            json={
                "course_id": course,
                "cohort_id": str(f["cohort"]),
                "position": 1,
                "reason": "Synthetic course assignment",
            },
        )
    )
    checked(client.post(root + f"/my-learning/{course}/start", headers=headers), 200)
    return root + f"/my-learning/{course}/assignments/{f['assignment']}"


def intent():
    return {
        "client_request_id": str(uuid4()),
        "media_type": "application/pdf",
        "byte_size": len(PDF),
        "sha256": hashlib.sha256(PDF).hexdigest(),
        "expected_revision": 1,
    }


def scan(f, file_id):
    class FixtureScanner:
        def scan(self, source, *, max_bytes):
            actual = source.read(max_bytes + 1)
            return ScanResult("clean", hashlib.sha256(actual).hexdigest(), len(actual), "clean")

    with Session(f["engine"]) as db:
        lease = files.claim_scan(db, f["org"], UUID(file_id), "synthetic-scan")
        return files.scan_with_lease(
            db, f["org"], lease, get_private_storage(), FixtureScanner(), "synthetic-scan"
        )


def upload(f, path, item):
    return checked(
        f["client"].put(
            path + "/content",
            content=PDF,
            headers={
                **f["headers"],
                "Content-Type": "application/pdf",
                "If-Match": f'"{item["file"]["version"]}"',
            },
        ),
        200,
    )


def test_assignment_bytes_scan_freeze_download_and_sql_guards(learning_files):
    f = learning_files
    path = publish_and_start(f)
    command = intent()
    first = checked(f["client"].post(path + "/files", headers=f["headers"], json=command))
    replay = checked(f["client"].post(path + "/files", headers=f["headers"], json=command))
    assert first["id"] == replay["id"]
    item = upload(f, path + f"/files/{first['id']}", first)
    assert item["file"]["state"] == "quarantined" and not item["usable"]
    submit = {"response_text": "Synthetic response", "file_ids": [item["id"]]}
    assert (
        f["client"].post(path + "/submissions", headers=f["headers"], json=submit).status_code
        == 409
    )
    scan(f, item["file"]["id"])
    submission = checked(f["client"].post(path + "/submissions", headers=f["headers"], json=submit))
    listed = checked(f["client"].get(path + "/files", headers=f["headers"]), 200)["items"][0]
    assert listed["state"] == "submitted" and listed["usable"]
    assert listed["evidence"]["sha256"] == hashlib.sha256(PDF).hexdigest()
    assert "storage_version" not in str(listed) and "quarantine/" not in str(listed)
    download = f["client"].get(path + f"/files/{item['id']}/content", headers=f["headers"])
    assert download.status_code == 200 and download.content == PDF
    assert download.headers["cache-control"] == "private, no-store"
    assert (
        f["client"]
        .put(
            path + f"/files/{item['id']}/content",
            content=PDF,
            headers={
                **f["headers"],
                "Content-Type": "application/pdf",
                "If-Match": f'"{listed["file"]["version"]}"',
            },
        )
        .status_code
        == 409
    )
    trainer = (
        f["root"]
        + f"/trainer-delivery/{f['course']}/assignment-submissions/{submission['id']}/files"
    )
    assert checked(f["client"].get(trainer, headers=f["headers"]), 200)[0]["id"] == item["id"]
    assert f["client"].get(trainer + f"/{item['id']}/content", headers=f["headers"]).content == PDF
    with Session(f["engine"]) as db:
        binding = db.get(AssignmentFile, UUID(item["id"]))
        binding.frozen_sha256 = "0" * 64
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()
        actor = db.get(User, f["user"])
        file = db.get(FileObject, UUID(item["file"]["id"]))
        ctx = files.AuthorizedFileContext(
            actor.id, f["org"], actor.person_id, "assignment_submission", binding.id
        )
        files.set_legal_hold(db, ctx, actor, file.id, file.version, True, "synthetic-hold")
    # A hold increments the operational file version without invalidating immutable bytes.
    assert (
        f["client"].get(path + f"/files/{item['id']}/content", headers=f["headers"]).content == PDF
    )
    assert (
        f["client"]
        .post(path + "/files", headers=f["headers"], json={**intent(), "expected_revision": 2})
        .status_code
        == 409
    )


def test_concurrent_replay_retired_policy_pin_and_direct_sql_required_files(learning_files):
    f = learning_files
    path = publish_and_start(f)
    policy(f)  # Retire the exact edition pinned by the published course.
    data = AssignmentFileIntent(**intent())

    def create_once(_):
        with Session(f["engine"]) as db:
            return file_service.create_assignment_file(
                db,
                f["org"],
                UUID(f["course"]),
                UUID(f["assignment"]),
                db.get(User, f["user"]),
                data,
                "concurrent",
            ).id

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(create_once, range(2)))
    assert len(set(results)) == 1
    with Session(f["engine"]) as db:
        assert db.scalar(select(func.count()).select_from(AssignmentFile)) == 1
        started = db.scalar(select(CourseEnrollment))
        db.add(
            AssignmentSubmission(
                organization_id=f["org"],
                course_id=UUID(f["course"]),
                course_enrollment_id=started.id,
                assignment_id=UUID(f["assignment"]),
                revision=1,
                response_text="Direct insert must not bypass required file evidence",
            )
        )
        with pytest.raises(DBAPIError):
            db.commit()
    assert (
        checked(f["client"].get(path + "/files", headers=f["headers"]), 200)["items"][0]["state"]
        == "active"
    )


def test_material_shared_gateway_requires_scanned_pin_and_rechecks_revoked_session(
    learning_files, monkeypatch
):
    f = learning_files
    configured = policy(f, "lms_material")
    command = {key: value for key, value in intent().items() if key != "expected_revision"}
    command.update(
        policy_id=str(configured.id),
        course_id=f["course"],
        lesson_id=f["lesson"],
        position=1,
        label_en="Synthetic material",
        label_ta="செயற்கை பாடப்பொருள்",
    )
    item = checked(
        f["client"].post(f["root"] + "/material-files", headers=f["headers"], json=command)
    )
    material_path = f["root"] + f"/courses/{f['course']}/material-files/{item['material_id']}"
    upload(f, material_path, item)
    assert (
        f["client"]
        .post(
            f["root"] + f"/{f['course']}/publish",
            headers=f["headers"],
            json={"expected_version": 1, "reason": "Reject unscanned material"},
        )
        .status_code
        == 409
    )
    scan(f, item["file"]["id"])
    publish_and_start(f, rule=False)
    access_path = f["root"] + f"/my-learning/{f['course']}/materials/{item['material_id']}/access"
    access = checked(f["client"].post(access_path, headers=f["headers"]), 200)
    api_path = access["url"].replace("/api/courses/", "/api/v1/courses/", 1)
    assert not get_settings().lms_material_root
    result = f["client"].get(api_path, headers=f["headers"])
    assert result.status_code == 200 and result.content == PDF
    from app.modules.lms import routes

    real_storage = get_private_storage()

    class RevokingStorage:
        @contextmanager
        def open(self, reference):
            with real_storage.open(reference) as source:
                with Session(f["engine"]) as db:
                    for session in db.scalars(
                        select(RefreshSession).where(RefreshSession.user_id == f["user"])
                    ):
                        session.revoked_at = now()
                    db.commit()
                yield source

    monkeypatch.setattr(routes, "get_private_storage", lambda: RevokingStorage())
    denied = f["client"].get(api_path, headers=f["headers"])
    assert denied.status_code == 401 and PDF not in denied.content


def test_material_intent_refreshes_cached_draft_after_concurrent_publication(learning_files):
    f = learning_files
    configured = policy(f, "lms_material")
    course_id = UUID(f["course"])
    command = MaterialFileIntent(
        client_request_id=uuid4(),
        policy_id=configured.id,
        course_id=course_id,
        lesson_id=UUID(f["lesson"]),
        position=1,
        label_en="Synthetic late material",
        label_ta="Synthetic Tamil late material",
        media_type="application/pdf",
        byte_size=len(PDF),
        sha256=hashlib.sha256(PDF).hexdigest(),
    )
    # Request sessions keep loaded instances across throttle commits. Retain the
    # draft in that identity map while another normal command publishes it.
    with Session(f["engine"], expire_on_commit=False) as db:
        cached = learning._course(db, f["org"], course_id)
        actor = db.get(User, f["user"])
        assert cached.state == "draft"
        with Session(f["engine"]) as publisher:
            published = learning.publish_course(
                publisher,
                f["org"],
                course_id,
                publisher.get(User, f["user"]),
                PublishCourse(expected_version=1, reason="Synthetic concurrent publication"),
                "concurrent-publication",
            )
            assert published.state == "published"
        assert cached.state == "draft"
        with pytest.raises(AuthError) as failure:
            file_service.create_material_file(db, f["org"], actor, command, "late-material")
        assert (failure.value.code, failure.value.status) == ("course_structure_frozen", 409)
        assert cached.state == "published"
        db.rollback()
    with Session(f["engine"]) as db:
        assert not db.scalar(
            select(func.count())
            .select_from(MaterialFile)
            .where(MaterialFile.course_id == course_id)
        )
        assert not db.scalar(
            select(func.count())
            .select_from(FileObject)
            .where(FileObject.organization_id == f["org"], FileObject.purpose == "lms_material")
        )


@pytest.mark.parametrize("rejected", [False, True])
def test_draft_material_removal_recovers_abandoned_or_rejected_intent(learning_files, rejected):
    f = learning_files
    configured = policy(f, "lms_material")
    command = {key: value for key, value in intent().items() if key != "expected_revision"}
    command.update(
        policy_id=str(configured.id),
        course_id=f["course"],
        lesson_id=f["lesson"],
        position=1,
        label_en="Synthetic abandoned material",
        label_ta="செயற்கை பாடப்பொருள்",
    )
    if rejected:
        command["sha256"] = "0" * 64
    item = checked(
        f["client"].post(f["root"] + "/material-files", headers=f["headers"], json=command)
    )
    path = f["root"] + f"/courses/{f['course']}/material-files/{item['material_id']}"
    if rejected:
        checked(
            f["client"].put(
                path + "/content",
                content=PDF,
                headers={
                    **f["headers"],
                    "Content-Type": "application/pdf",
                    "If-Match": '"1"',
                },
            ),
            422,
        )
    checked(
        f["client"].post(
            f["root"] + f"/{f['course']}/publish",
            headers=f["headers"],
            json={
                "expected_version": 1,
                "reason": "Cannot silently ignore an incomplete material",
            },
        ),
        409,
    )
    checked(
        f["client"].request("DELETE", path, headers=f["headers"], json={"expected_version": 2}), 409
    )
    removed = checked(
        f["client"].request("DELETE", path, headers=f["headers"], json={"expected_version": 1}), 200
    )
    assert removed["state"] == "removed" and removed["version"] == 2 and not removed["usable"]
    assert checked(f["client"].get(path, headers=f["headers"]), 200) == removed
    checked(f["client"].get(path + "/content", headers=f["headers"]), 409)
    checked(
        f["client"].put(
            path + "/content",
            content=PDF,
            headers={
                **f["headers"],
                "Content-Type": "application/pdf",
                "If-Match": '"1"',
            },
        ),
        409,
    )
    with Session(f["engine"]) as db:
        binding = db.scalar(
            select(MaterialFile).where(MaterialFile.material_id == UUID(item["material_id"]))
        )
        assert db.get(FileObject, binding.file_id) is not None
        binding.state, binding.version = "active", 3
        with pytest.raises(DBAPIError):
            db.commit()
    # History reserves the original position. A replacement is a new immutable intent.
    command.update(
        client_request_id=str(uuid4()), position=2, sha256=hashlib.sha256(PDF).hexdigest()
    )
    replacement = checked(
        f["client"].post(f["root"] + "/material-files", headers=f["headers"], json=command)
    )
    replacement_path = (
        f["root"] + f"/courses/{f['course']}/material-files/{replacement['material_id']}"
    )
    upload(f, replacement_path, replacement)
    scan(f, replacement["file"]["id"])
    publish_and_start(f, rule=False)
    learner = checked(f["client"].get(f["root"] + "/my-learning", headers=f["headers"]), 200)
    material_ids = [
        row["id"]
        for course in learner["courses"]
        for module in course["modules"]
        for lesson in module["lessons"]
        for row in lesson["materials"]
    ]
    assert item["material_id"] not in material_ids and replacement["material_id"] in material_ids
    checked(
        f["client"].post(
            f["root"] + f"/my-learning/{f['course']}/materials/{item['material_id']}/access",
            headers=f["headers"],
        ),
        409,
    )
    checked(
        f["client"].request(
            "DELETE", replacement_path, headers=f["headers"], json={"expected_version": 2}
        ),
        409,
    )


@pytest.mark.parametrize("change", ["suspend", "remove"])
def test_upload_rechecks_owner_and_binding_after_body_without_writing_storage(
    learning_files, monkeypatch, change
):
    from app.modules.lms import file_routes

    f = learning_files
    path = publish_and_start(f)
    item = checked(f["client"].post(path + "/files", headers=f["headers"], json=intent()))
    original = file_routes.bounded_upload

    @asynccontextmanager
    async def race(*args, **kwargs):
        async with original(*args, **kwargs) as source:
            with Session(f["engine"]) as db:
                if change == "suspend":
                    db.get(User, f["user"]).status = "suspended"
                else:
                    binding = db.get(AssignmentFile, UUID(item["id"]))
                    binding.state, binding.version = "removed", binding.version + 1
                db.commit()
            yield source

    monkeypatch.setattr(file_routes, "bounded_upload", race)
    result = f["client"].put(
        path + f"/files/{item['id']}/content",
        content=PDF,
        headers={**f["headers"], "Content-Type": "application/pdf", "If-Match": '"1"'},
    )
    assert result.status_code == (401 if change == "suspend" else 409)
    with Session(f["engine"]) as db:
        file = db.get(FileObject, UUID(item["file"]["id"]))
        assert file.state == "pending" and file.storage_version is None


def test_expired_clean_bytes_are_not_usable_or_submittable(learning_files, monkeypatch):
    f = learning_files
    path = publish_and_start(f)
    item = checked(f["client"].post(path + "/files", headers=f["headers"], json=intent()))
    upload(f, path + f"/files/{item['id']}", item)
    scan(f, item["file"]["id"])
    monkeypatch.setattr(file_service, "now", lambda: now() + timedelta(days=2))
    listed = checked(f["client"].get(path + "/files", headers=f["headers"]), 200)["items"][0]
    assert listed["file"]["state"] == "clean" and not listed["usable"]
    assert (
        f["client"].get(path + f"/files/{item['id']}/content", headers=f["headers"]).status_code
        == 409
    )
    assert (
        f["client"]
        .post(
            path + "/submissions",
            headers=f["headers"],
            json={
                "response_text": "Expired evidence must not be accepted",
                "file_ids": [item["id"]],
            },
        )
        .status_code
        == 409
    )


def test_enrolled_peer_cannot_read_or_submit_owner_file(learning_files):
    f = learning_files
    path = publish_and_start(f)
    item = checked(f["client"].post(path + "/files", headers=f["headers"], json=intent()))
    upload(f, path + f"/files/{item['id']}", item)
    scan(f, item["file"]["id"])
    with Session(f["engine"]) as db:
        source = db.get(Enrollment, f["enrollment"])
        original_application = db.get(Application, source.application_id)
        person = Person(display_name="Synthetic enrolled peer")
        db.add(person)
        db.flush()
        user = User(
            person_id=person.id,
            email="learning-file-peer@example.com",
            password_hash=hasher.hash("Synthetic peer password 123"),
            status="active",
        )
        participant = Participant(organization_id=f["org"], person_id=person.id, status="active")
        application = Application(
            organization_id=f["org"],
            person_id=person.id,
            form_id=original_application.form_id,
            cycle_id=original_application.cycle_id,
            state="enrolled",
            version=8,
            application_number="EDP-LMS-PEER-0001",
            submitted_at=now(),
        )
        db.add_all([user, participant, application])
        db.flush()
        role = db.scalar(select(Role).where(Role.name == "Participant"))
        db.add(UserRole(user_id=user.id, role_id=role.id, organization_id=f["org"]))
        db.add(
            Enrollment(
                organization_id=f["org"],
                participant_id=participant.id,
                program_id=source.program_id,
                cohort_id=source.cohort_id,
                application_id=application.id,
                status="active",
            )
        )
        db.commit()
    tokens = checked(
        f["client"].post(
            "/api/v1/auth/login",
            json={
                "email": "learning-file-peer@example.com",
                "password": "Synthetic peer password 123",
            },
        ),
        200,
    )
    peer = {"Authorization": "Bearer " + tokens["access_token"]}
    checked(f["client"].post(f["root"] + f"/my-learning/{f['course']}/start", headers=peer), 200)
    assert checked(f["client"].get(path + "/files", headers=peer), 200)["items"] == []
    assert f["client"].get(path + f"/files/{item['id']}", headers=peer).status_code == 404
    assert f["client"].get(path + f"/files/{item['id']}/content", headers=peer).status_code == 404
    assert (
        f["client"]
        .post(
            path + "/submissions",
            headers=peer,
            json={"response_text": "Borrowed binding must be rejected", "file_ids": [item["id"]]},
        )
        .status_code
        == 409
    )
