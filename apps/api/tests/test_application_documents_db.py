import hashlib
import io
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_application_submission_db import policy as application_policy
from test_file_foundation_db import rules
from test_identity import auth  # noqa: F401

from app.core.config import get_settings
from app.modules.applications import document_routes
from app.modules.applications import document_service as documents
from app.modules.applications import service as applications
from app.modules.applications.document_schemas import (
    DocumentCreate,
    DocumentRemove,
    DocumentRequirementInput,
)
from app.modules.applications.models import (
    Application,
    ApplicationDocument,
    ApplicationDocumentEvidence,
    ApplicationForm,
    DocumentRequirement,
)
from app.modules.applications.schemas import (
    AnswerInput,
    DefinitionCommand,
    DefinitionCreate,
    DefinitionUpdate,
    DraftSave,
    SubmitCommand,
)
from app.modules.files import service as files
from app.modules.files.models import FileObject
from app.modules.files.scanner import ScanResult
from app.modules.files.schemas import FileCreate, FilePolicyCommand, FilePolicyCreate
from app.modules.files.storage import LocalPrivateStorage
from app.modules.identity.models import (
    Organization,
    Person,
    RefreshSession,
    Role,
    User,
    UserRole,
    now,
)
from app.modules.identity.security import AuthError, hasher
from app.modules.programs.models import ApplicationCycle, Program
from app.modules.selection.models import ReviewAssignment, SelectionCycle, SelectionRubric

pytestmark = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)
PDF = b"%PDF-1.4\nSynthetic application document acceptance\n%%EOF"
PASSWORD = "Synthetic password 123"


@pytest.fixture
def document_db(request, tmp_path, monkeypatch):
    client, engine, _, _ = request.getfixturevalue("auth")
    private_temp = tmp_path / "temp"
    private_temp.mkdir(mode=0o700)
    for name, value in {
        "FILES_ENABLED": "true",
        "FILES_STORAGE_BACKEND": "local",
        "FILES_LOCAL_ROOT": str(tmp_path / "objects"),
        "FILES_TEMP_ROOT": str(private_temp),
        "FILES_MAX_BYTES": "1024",
    }.items():
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()
    with Session(engine, expire_on_commit=False) as db:
        org, other = Organization(name="Synthetic document intake"), Organization(name="Other")
        people = [Person(display_name=name) for name in ("Director", "Owner", "Peer", "Reviewer")]
        db.add_all([org, other, *people])
        db.flush()
        users = [
            User(
                person_id=person.id,
                email=f"documents-{i}@example.com",
                password_hash=hasher.hash(PASSWORD),
                status="active",
            )
            for i, person in enumerate(people)
        ]
        db.add_all(users)
        db.flush()
        for user, role_name in ((users[0], "Program Director"), (users[3], "Selection Committee")):
            role = db.scalar(select(Role).where(Role.name == role_name))
            assert role
            db.add(UserRole(user_id=user.id, role_id=role.id, organization_id=org.id))
        db.commit()
        policy = files.create_policy(
            db, org.id, users[0], FilePolicyCreate(**rules(max_files=2)), "policy-create"
        )
        policy = files.publish_policy(
            db,
            org.id,
            policy.id,
            users[0],
            FilePolicyCommand(
                expected_version=policy.version, reason="Synthetic policy approval only"
            ),
            "publish",
        )
        content = application_policy().model_dump()
        content["document_requirements"] = [
            DocumentRequirementInput(
                key=key,
                label_en=label,
                label_ta=f"Synthetic Tamil {label}",
                instructions_en="Synthetic test documents only.",
                instructions_ta="Synthetic Tamil test instructions.",
                file_policy_id=policy.id,
                min_files=minimum,
                max_files=2,
            )
            for key, label, minimum in (
                ("proposal", "Proposal document", 1),
                ("support", "Supporting document", 0),
            )
        ]
        form = applications.create_definition(
            db, org.id, users[0], DefinitionCreate(**content), "form-create"
        )
        form = applications.publish_definition(
            db, org.id, form.id, users[0], DefinitionCommand(expected_revision=1), "publish"
        )
        program = Program(
            organization_id=org.id,
            code="documents",
            name_en="Documents",
            name_ta="Synthetic Tamil documents",
            state="active",
        )
        db.add(program)
        db.flush()
        current = now()
        cycle = ApplicationCycle(
            organization_id=org.id,
            program_id=program.id,
            form_id=form.id,
            code="documents",
            name_en="Document intake",
            name_ta="Synthetic Tamil intake",
            state="open",
            opens_at=current - timedelta(days=1),
            closes_at=current + timedelta(days=10),
        )
        db.add(cycle)
        db.commit()
        draft = applications.create_cycle_draft(db, org.id, cycle.id, users[1], "draft")
        draft = applications.save(
            db,
            org.id,
            draft.id,
            users[1],
            DraftSave(
                expected_version=draft.version,
                answers=[AnswerInput(field_id=form.fields[0].id, value="Synthetic proposal")],
            ),
            "save",
        )
        yield {
            "client": client,
            "engine": engine,
            "org": org.id,
            "other": other.id,
            "director": users[0].id,
            "owner": users[1].id,
            "peer": users[2].id,
            "reviewer": users[3].id,
            "form": form,
            "cycle": cycle.id,
            "app": draft.id,
            "policy": policy,
            "temp": private_temp,
            "storage": LocalPrivateStorage(
                tmp_path / "objects", max_bytes=1024, temp_root=private_temp
            ),
        }


def metadata(f, *, requirement=0, **changes):
    return DocumentCreate(
        **{
            "expected_version": 2,
            "client_request_id": uuid4(),
            "requirement_id": f["form"].document_requirements[requirement].id,
            "media_type": "application/pdf",
            "byte_size": len(PDF),
            "sha256": hashlib.sha256(PDF).hexdigest(),
            **changes,
        }
    )


def create(db, f, *, requirement=0, **changes):
    owner = db.get(User, f["owner"])
    app = db.get(Application, f["app"], populate_existing=True)
    return documents.create_document(
        db,
        f["org"],
        app.id,
        owner,
        metadata(f, requirement=requirement, expected_version=app.version, **changes),
        "create",
    )


def clean(db, f, created):
    owner = db.get(User, f["owner"])
    item = documents.upload_document(
        db,
        f["org"],
        f["app"],
        created.document.id,
        owner,
        created.document.file.version,
        io.BytesIO(PDF),
        f["storage"],
        "upload",
    )
    lease = files.claim_scan(db, f["org"], item.document.file.id, "scan-claim")
    files.finish_scan(
        db,
        f["org"],
        lease,
        ScanResult("clean", hashlib.sha256(PDF).hexdigest(), len(PDF), "clean"),
        "scan",
    )
    return documents.get_document(db, f["org"], f["app"], created.document.id, owner)


def submit(db, f):
    owner = db.get(User, f["owner"])
    app = db.get(Application, f["app"], populate_existing=True)
    return applications.submit(
        db,
        f["org"],
        app.id,
        owner,
        SubmitCommand(
            expected_version=app.version,
            accepted_acknowledgement_ids=[row.id for row in f["form"].acknowledgements],
        ),
        "submit",
    )


def test_requirement_copy_legacy_and_database_immutability(document_db):
    f = document_db
    with Session(f["engine"]) as db:
        director = db.get(User, f["director"])
        form = applications.get_definition(db, f["org"], f["form"].id, director)
        assert form.collection_enabled and form.max_upload_bytes == 1024
        assert form.document_requirements[0].file_policy.max_upload_bytes == 1024
        copied = applications.copy_definition(
            db,
            f["org"],
            form.id,
            director,
            DefinitionCommand(expected_revision=form.revision),
            "copy",
        )
        assert copied.document_requirements[0].id != form.document_requirements[0].id
        assert copied.document_requirements[0].file_policy_id == f["policy"].id
        row = db.get(DocumentRequirement, form.document_requirements[0].id)
        row.instructions_en = "Cannot change published requirement"
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()
        published_form = db.get(ApplicationForm, form.id)
        published_form.published_at = now() + timedelta(days=1)
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()
        legacy = application_policy().model_dump()
        legacy["expected_revision"] = copied.revision
        updated = applications.update_definition(
            db, f["org"], copied.id, director, DefinitionUpdate(**legacy), "legacy"
        )
        assert updated.document_requirements == []
        published = applications.publish_definition(
            db,
            f["org"],
            copied.id,
            director,
            DefinitionCommand(expected_revision=updated.revision),
            "legacy-publish",
        )
        assert published.document_requirements == []


def test_owner_replay_scope_counts_replacement_and_removal(document_db):
    f = document_db
    with Session(f["engine"]) as db:
        owner, peer = db.get(User, f["owner"]), db.get(User, f["peer"])
        data = metadata(f)
        first = documents.create_document(db, f["org"], f["app"], owner, data, "create")
        assert documents.create_document(db, f["org"], f["app"], owner, data, "retry") == first
        with pytest.raises(AuthError, match="idempotency_conflict"):
            documents.create_document(
                db,
                f["org"],
                f["app"],
                owner,
                data.model_copy(update={"byte_size": len(PDF) + 1}),
                "changed",
            )
        second = create(db, f, requirement=1)
        with pytest.raises(AuthError, match="file_count_exceeded"):
            create(db, f)
        replacement = create(db, f, replaces_document_id=first.document.id)
        old = documents.get_document(db, f["org"], f["app"], first.document.id, owner)
        assert old.document.removed_at and old.document.replaced_by_id == replacement.document.id
        assert documents.get_document(db, f["org"], f["app"], replacement.document.id, owner)
        assert documents.list_documents(db, f["org"], f["app"], owner, limit=1).next_cursor
        for org, actor in ((f["org"], peer), (f["other"], owner)):
            with pytest.raises(AuthError) as denied:
                documents.list_documents(db, org, f["app"], actor)
            assert denied.value.status == 404
        with pytest.raises(AuthError, match="invalid_cursor"):
            documents.list_documents(db, f["org"], f["app"], owner, uuid4())
        removed = documents.remove_document(
            db,
            f["org"],
            f["app"],
            second.document.id,
            owner,
            DocumentRemove(expected_version=replacement.application_version),
            "remove",
        )
        assert removed.document.removed_at
        assert db.scalar(select(func.count()).select_from(FileObject)) == 3
        assert not documents.get_document(
            db, f["org"], f["app"], replacement.document.id, owner
        ).document.file.evidence_frozen
        bound = db.get(ApplicationDocument, replacement.document.id)
        bound.owner_person_id = peer.person_id
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()


def test_submit_requires_clean_and_freezes_exact_immutable_evidence(document_db):
    f = document_db
    with Session(f["engine"]) as db:
        with pytest.raises(AuthError, match="application_documents_incomplete"):
            submit(db, f)
        pending = create(db, f)
        with pytest.raises(AuthError, match="application_documents_not_clean"):
            submit(db, f)
        ready = clean(db, f, pending)
        receipt = submit(db, f)
        assert receipt.state == "submitted"
        owner = db.get(User, f["owner"])
        view = documents.get_document(db, f["org"], f["app"], ready.document.id, owner)
        proof = db.scalar(select(ApplicationDocumentEvidence))
        item = db.get(FileObject, ready.document.file.id)
        assert proof.storage_version == item.storage_version
        assert proof.sha256 == hashlib.sha256(PDF).hexdigest()
        assert proof.byte_size == len(PDF) and item.evidence_frozen
        assert view.document.submitted_evidence.file_version == proof.file_version
        assert "storage_version" not in view.model_dump_json()
        assert "object_key" not in view.model_dump_json()
        cycle = db.get(ApplicationCycle, f["cycle"])
        cycle.state = "closed"
        db.commit()
        assert applications.cycle_application(db, f["org"], f["cycle"], owner).id == f["app"]
        assert documents.owner_download(db, f["org"], f["app"], ready.document.id, owner)[1]
        with pytest.raises(AuthError, match="application_documents_immutable"):
            documents.remove_document(
                db,
                f["org"],
                f["app"],
                ready.document.id,
                owner,
                DocumentRemove(expected_version=receipt.version),
                "remove",
            )
        proof.sha256 = "0" * 64
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()


def test_raw_route_flag_bounds_owner_and_private_delivery(document_db, monkeypatch):
    f = document_db
    login = f["client"].post(
        "/api/v1/auth/login", json={"email": "documents-1@example.com", "password": PASSWORD}
    )
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    base = f"/api/v1/applications/organizations/{f['org']}/applications/{f['app']}/documents"
    monkeypatch.setenv("FILES_ENABLED", "false")
    get_settings.cache_clear()
    assert f["client"].get(base, headers=headers).json()["collection_enabled"] is False
    assert (
        f["client"]
        .post(base, headers=headers, json=metadata(f).model_dump(mode="json"))
        .status_code
        == 503
    )
    monkeypatch.setenv("FILES_ENABLED", "true")
    get_settings.cache_clear()
    response = f["client"].post(base, headers=headers, json=metadata(f).model_dump(mode="json"))
    assert response.status_code == 201, response.text
    item = response.json()["document"]
    path = base + f"/{item['id']}/content"
    upload_headers = {**headers, "Content-Type": "application/pdf", "If-Match": '"1"'}
    assert (
        f["client"].put(path, headers={**upload_headers, "If-Match": "*"}, content=PDF).status_code
        == 422
    )
    assert (
        f["client"]
        .put(path, headers={**upload_headers, "Content-Type": "image/png"}, content=PDF)
        .status_code
        == 415
    )
    assert f["client"].put(path, headers=upload_headers, content=PDF + b"excess").status_code == 413
    uploaded = f["client"].put(path, headers=upload_headers, content=PDF)
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["document"]["file"]["state"] == "quarantined"
    assert f["client"].get(path, headers=headers).status_code == 409
    with Session(f["engine"]) as db:
        lease = files.claim_scan(db, f["org"], item["file"]["id"], "scan")
        files.finish_scan(
            db,
            f["org"],
            lease,
            ScanResult("clean", hashlib.sha256(PDF).hexdigest(), len(PDF), "clean"),
            "clean",
        )
    downloaded = f["client"].get(path, headers=headers)
    assert downloaded.status_code == 200 and downloaded.content == PDF
    assert downloaded.headers["cache-control"] == "private, no-store"
    assert "attachment" in downloaded.headers["content-disposition"]
    with Session(f["engine"]) as db:
        monkeypatch.setattr(documents, "now", lambda: now() + timedelta(days=2))
        assert not documents.get_document(
            db, f["org"], f["app"], item["id"], db.get(User, f["owner"])
        ).document.usable
        with pytest.raises(AuthError, match="file_not_available"):
            documents.owner_download(db, f["org"], f["app"], item["id"], db.get(User, f["owner"]))


def test_review_access_rechecks_current_assignment_and_permission(document_db):
    f = document_db
    with Session(f["engine"]) as db:
        ready = clean(db, f, create(db, f))
        submit(db, f)
        cycle = SelectionCycle(
            organization_id=f["org"],
            application_cycle_id=f["cycle"],
            code="review",
            name_en="Synthetic review",
            name_ta="Tamil",
            state="active",
        )
        db.add(cycle)
        db.flush()
        rubric = SelectionRubric(
            organization_id=f["org"],
            selection_cycle_id=cycle.id,
            version_number=1,
            state="published",
            published_at=now(),
        )
        db.add(rubric)
        db.flush()
        assignment = ReviewAssignment(
            organization_id=f["org"],
            selection_cycle_id=cycle.id,
            rubric_id=rubric.id,
            application_id=f["app"],
            reviewer_user_id=f["reviewer"],
            conflict_status="clear",
            status="in_review",
        )
        db.add(assignment)
        db.commit()
        reviewer, director = db.get(User, f["reviewer"]), db.get(User, f["director"])
        result = documents.reviewer_documents(db, f["org"], assignment.id, reviewer)
        assert result.document_requirements[0].label_en == "Proposal document"
        assert result.items[0].submitted_evidence
        assert "answers" not in result.model_dump_json()
        assert documents.reviewer_download(
            db, f["org"], assignment.id, ready.document.id, reviewer
        )[1]
        with pytest.raises(AuthError):
            documents.reviewer_documents(db, f["org"], assignment.id, director)
        assignment.conflict_status, assignment.conflict_note = "conflict", "Synthetic conflict"
        db.commit()
        with pytest.raises(AuthError):
            documents.reviewer_documents(db, f["org"], assignment.id, reviewer)
        assignment.conflict_status, assignment.conflict_note = "clear", None
        db.commit()
        role = db.scalar(select(UserRole).where(UserRole.user_id == reviewer.id))
        db.delete(role)
        db.commit()
        with pytest.raises(AuthError) as revoked:
            documents.reviewer_download(db, f["org"], assignment.id, ready.document.id, reviewer)
        assert revoked.value.status == 403


def test_concurrent_metadata_replay_creates_one_binding(document_db):
    f = document_db
    data = metadata(f)

    def attempt():
        with Session(f["engine"]) as db:
            return documents.create_document(
                db, f["org"], f["app"], db.get(User, f["owner"]), data, "concurrent"
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert results[0].document.id == results[1].document.id
    with Session(f["engine"]) as db:
        assert db.scalar(select(func.count()).select_from(ApplicationDocument)) == 1
        assert db.scalar(select(func.count()).select_from(FileObject)) == 1
        assert db.get(Application, f["app"]).version == 3


def test_submission_freeze_rolls_back_and_sql_cannot_bypass(document_db, monkeypatch):
    f = document_db
    with Session(f["engine"]) as db:
        clean(db, f, create(db, f))
        clean(db, f, create(db, f, requirement=1))
        original = files.freeze_evidence
        calls = []

        def fail_second(*args, **kwargs):
            calls.append(True)
            if len(calls) == 2:
                raise AuthError("synthetic_freeze_failure", 503)
            return original(*args, **kwargs)

        monkeypatch.setattr(files, "freeze_evidence", fail_second)
        with pytest.raises(AuthError, match="synthetic_freeze_failure"):
            submit(db, f)
        db.rollback()
        assert db.scalar(select(func.count()).select_from(ApplicationDocumentEvidence)) == 0
        assert (
            db.scalar(
                select(func.count())
                .select_from(FileObject)
                .where(FileObject.evidence_frozen.is_(True))
            )
            == 0
        )
        app = db.get(Application, f["app"])
        app.state, app.application_number, app.submitted_at = "submitted", "SYNTHETIC-BYPASS", now()
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()
        assert db.get(Application, f["app"]).state == "draft"


def test_published_form_keeps_retired_policy_pin(document_db):
    f = document_db
    with Session(f["engine"]) as db:
        director = db.get(User, f["director"])
        new_policy = files.create_policy(
            db, f["org"], director, FilePolicyCreate(**rules(max_files=2)), "next"
        )
        files.publish_policy(
            db,
            f["org"],
            new_policy.id,
            director,
            FilePolicyCommand(expected_version=1, reason="Synthetic next edition"),
            "publish-next",
        )
        created = create(db, f)
        assert created.document.file.policy_id == f["policy"].id
        copied = applications.copy_definition(
            db,
            f["org"],
            f["form"].id,
            director,
            DefinitionCommand(expected_revision=f["form"].revision),
            "copy",
        )
        with pytest.raises(AuthError, match="file_policy_unavailable"):
            applications.publish_definition(
                db, f["org"], copied.id, director, DefinitionCommand(expected_revision=1), "publish"
            )
        db.rollback()
        owner = db.get(User, f["owner"])
        context = files.AuthorizedFileContext(
            owner.id, f["org"], owner.person_id, "application_document", uuid4()
        )
        raw = FileCreate(
            client_request_id=uuid4(),
            policy_id=f["policy"].id,
            media_type="application/pdf",
            byte_size=len(PDF),
            sha256=hashlib.sha256(PDF).hexdigest(),
        )
        with pytest.raises(AuthError, match="file_policy_unavailable"):
            files.create_file(db, context, owner, raw, "generic-retired")
        with pytest.raises(DBAPIError):
            files.create_file(db, context, owner, raw, "unbound-retired", allow_retired_policy=True)
        db.rollback()


@pytest.mark.parametrize(
    "change,expected_status",
    [
        ("closed", 404),
        ("removed", 404),
        ("revoked", 401),
        ("disabled", 401),
    ],
)
def test_upload_rechecks_context_and_session_after_body(
    document_db,
    monkeypatch,
    change,
    expected_status,
):
    f = document_db
    with Session(f["engine"]) as db:
        created = create(db, f)
    login = f["client"].post(
        "/api/v1/auth/login",
        json={
            "email": "documents-1@example.com",
            "password": PASSWORD,
        },
    )
    headers = {
        "Authorization": "Bearer " + login.json()["access_token"],
        "Content-Type": "application/pdf",
        "If-Match": '"1"',
    }
    original = document_routes.bounded_upload

    @asynccontextmanager
    async def interrupted(*args, **kwargs):
        async with original(*args, **kwargs) as source:
            with Session(f["engine"]) as db:
                if change == "closed":
                    db.get(ApplicationCycle, f["cycle"]).state = "closed"
                elif change == "removed":
                    documents.remove_document(
                        db,
                        f["org"],
                        f["app"],
                        created.document.id,
                        db.get(User, f["owner"]),
                        DocumentRemove(expected_version=created.application_version),
                        "remove",
                    )
                elif change == "revoked":
                    db.scalar(
                        select(RefreshSession).where(RefreshSession.user_id == f["owner"])
                    ).revoked_at = now()
                else:
                    db.get(User, f["owner"]).status = "suspended"
                db.commit()
            yield source

    monkeypatch.setattr(document_routes, "bounded_upload", interrupted)
    base = f"/api/v1/applications/organizations/{f['org']}/applications/{f['app']}/documents"
    result = f["client"].put(base + f"/{created.document.id}/content", headers=headers, content=PDF)
    assert result.status_code == expected_status, result.text
    with Session(f["engine"]) as db:
        file = db.get(FileObject, created.document.file.id)
        assert file.state == "pending" and file.storage_version is None
    assert not list(f["temp"].iterdir())


def test_intent_rate_bound_preserves_exact_request_recovery(document_db, monkeypatch):
    f = document_db
    monkeypatch.setenv("FILES_INTENT_LIMIT_PER_WINDOW", "1")
    get_settings.cache_clear()
    with Session(f["engine"]) as db:
        owner = db.get(User, f["owner"])
        data = metadata(f)
        first = documents.create_document(db, f["org"], f["app"], owner, data, "first")
        assert (
            documents.create_document(db, f["org"], f["app"], owner, data, "lost-reply").document.id
            == first.document.id
        )
        with pytest.raises(AuthError) as limited:
            create(db, f, requirement=1)
        assert limited.value.status == 429
        assert db.scalar(select(func.count()).select_from(ApplicationDocument)) == 1
