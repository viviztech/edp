import hashlib
import io
import os
from datetime import timedelta
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from PIL import Image, PngImagePlugin
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_identity import auth, signed_in  # noqa: F401

from app.core.config import get_settings
from app.modules.cms import asset_routes, asset_service
from app.modules.cms.media_processor import sanitize_image
from app.modules.cms.models import AssetFile
from app.modules.files import service as files
from app.modules.files.models import FileObject
from app.modules.files.scanner import ScanResult
from app.modules.files.schemas import FileCreate, FilePolicyCommand, FilePolicyCreate
from app.modules.identity.models import Organization, Role, User, UserRole, now
from app.modules.identity.security import AuthError

PDF = b"%PDF-1.4\nSynthetic CMS media acceptance only\n%%EOF"
db_test = pytest.mark.skipif(
    not os.getenv("AUTH_TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)


def image_bytes():
    output = io.BytesIO()
    with Image.new("RGB", (16, 12), "red") as image:
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("private-location", "secret-untrusted-metadata")
        image.save(output, format="PNG", pnginfo=metadata)
    return output.getvalue()


@pytest.mark.parametrize(
    "media,fmt", [("image/png", "PNG"), ("image/jpeg", "JPEG"), ("image/webp", "WEBP")]
)
def test_public_image_reencoded_from_pixels_without_private_metadata(media, fmt):
    source = io.BytesIO()
    with Image.new("RGB", (16, 12), "red") as image:
        exif = Image.Exif()
        exif[270] = "private-image-description"
        image.save(source, format=fmt, exif=exif)
    source.seek(0)
    with sanitize_image(source, media, 10000) as output:
        result = output.read()
        assert b"private-image-description" not in result
        with Image.open(io.BytesIO(result)) as image:
            assert image.size == (16, 12) and not image.getexif()
            assert not image.info.get("icc_profile") and not image.info.get("xmp")


def test_public_image_rejects_animation_corruption_pixel_and_output_limits(monkeypatch):
    animated = io.BytesIO()
    with Image.new("RGB", (4, 4), "red") as first, Image.new("RGB", (4, 4), "blue") as second:
        first.save(animated, format="PNG", save_all=True, append_images=[second])
    for data, limit in [
        (b"\x89PNG\r\n\x1a\nmalformed", 10000),
        (animated.getvalue(), 10000),
        (image_bytes(), 5),
    ]:
        with pytest.raises(AuthError, match="asset_image_invalid"):
            sanitize_image(io.BytesIO(data), "image/png", limit)
    monkeypatch.setattr("app.modules.cms.media_processor.MAX_IMAGE_PIXELS", 10)
    with pytest.raises(AuthError):
        sanitize_image(io.BytesIO(image_bytes()), "image/png", 10000)


@pytest.fixture
def media(request, tmp_path, monkeypatch):
    temporary = tmp_path / "private-temp"
    temporary.mkdir(mode=0o700)
    monkeypatch.setenv("FILES_ENABLED", "true")
    monkeypatch.setenv("FILES_STORAGE_BACKEND", "local")
    monkeypatch.setenv("FILES_LOCAL_ROOT", str(tmp_path / "objects"))
    monkeypatch.setenv("FILES_TEMP_ROOT", str(temporary))
    get_settings.cache_clear()
    fixture = request.getfixturevalue("auth")
    client, engine, _, _ = fixture
    credentials, tokens, _ = signed_in(fixture)
    client.headers["Authorization"] = "Bearer " + tokens["access_token"]
    with Session(engine) as db:
        actor = db.scalar(select(User).where(User.email == credentials["email"]))
        org, other = (
            Organization(name="Synthetic CMS bytes"),
            Organization(name="Unrelated CMS bytes"),
        )
        db.add_all([org, other])
        db.flush()
        for name in ("Content Manager", "Program Director"):
            role = db.scalar(select(Role).where(Role.name == name))
            db.add(UserRole(user_id=actor.id, role_id=role.id, organization_id=org.id))
        db.commit()
        policy = files.create_policy(
            db,
            org.id,
            actor,
            FilePolicyCreate(
                client_request_id=uuid4(),
                purpose="cms_asset",
                name="Synthetic CMS policy",
                notice_en="Synthetic only",
                notice_ta="செயற்கை மட்டும்",
                allowed_mime_types=["application/pdf", "image/png", "image/jpeg", "image/webp"],
                max_file_bytes=1048576,
                max_files=2,
                retention_days=1,
                rejected_retention_days=1,
                allow_frozen_disposal=False,
                reason="Synthetic fixture",
            ),
            "policy",
        )
        policy = files.publish_policy(
            db,
            org.id,
            policy.id,
            actor,
            FilePolicyCommand(expected_version=1, reason="Synthetic fixture"),
            "publish-policy",
        )
        return {
            "client": client,
            "engine": engine,
            "org": org.id,
            "other": other.id,
            "actor": actor.id,
            "policy": policy.id,
            "base": f"/api/v1/cms/organizations/{org.id}/assets",
            "public": f"/api/v1/public/organizations/{org.id}/assets",
        }


def metadata(media, data=PDF, media_type="application/pdf"):
    return {
        "filename": "synthetic.pdf" if media_type == "application/pdf" else "synthetic.png",
        "title": "Synthetic media",
        "media_type": media_type,
        "byte_size": len(data),
        "client_request_id": str(uuid4()),
    }


def new_source(media, data=PDF, media_type="application/pdf"):
    client, base = media["client"], media["base"]
    created = client.post(base, json=metadata(media, data, media_type))
    assert created.status_code == 201, created.text
    a = created.json()
    intent = {
        "expected_version": a["version"],
        "client_request_id": str(uuid4()),
        "policy_id": str(media["policy"]),
        "media_type": media_type,
        "byte_size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    response = client.post(base + "/" + a["id"] + "/source", json=intent)
    assert response.status_code == 201, response.text
    a = response.json()
    response = client.put(
        base + "/" + a["id"] + "/source/content",
        content=data,
        headers={"Content-Type": media_type, "If-Match": f'"{a["source"]["version"]}"'},
    )
    assert response.status_code == 200, response.text
    return response.json(), intent


def scan(media, file_id, status="clean"):
    with Session(media["engine"]) as db:
        row = db.get(FileObject, file_id)
        lease = files.claim_scan(db, media["org"], row.id, "scan-claim")
        return files.finish_scan(
            db,
            media["org"],
            lease,
            ScanResult(status, row.stored_sha256, row.stored_byte_size, "synthetic-test-verdict"),
            "scan-finish",
        )


def command(a, file=None):
    return {
        "expected_version": a["version"],
        "expected_file_version": (file or a["prepared"] or a["source"])["version"],
        "reason": "Synthetic publication decision",
    }


@db_test
def test_cms_metadata_cannot_forge_scan_or_publication_and_legacy_stays_unbacked(media):
    client, base = media["client"], media["base"]
    data = metadata(media)
    response = client.post(base, json=data)
    a = response.json()
    assert client.post(base, json=data).json()["id"] == a["id"]
    assert client.post(base, json={**data, "title": "Changed request"}).status_code == 409
    assert (
        client.post(
            base + "/" + a["id"] + "/publish", json={"expected_version": 1, "reason": "No bytes"}
        ).status_code
        == 409
    )
    callback = f"/api/v1/internal/cms/organizations/{media['org']}/assets/{a['id']}/scan"
    assert (
        client.post(
            callback, json={"clean": True}, headers={"X-Asset-Scanner-Key": "anything"}
        ).status_code
        == 410
    )
    with media["engine"].begin() as connection:
        connection.execute(
            text("UPDATE cms_assets SET scan_status='clean',visibility='public',version=version+1")
        )
    a = client.get(base + "/" + a["id"]).json()
    assert a["scan_status"] == "clean" and a["visibility"] == "public"
    assert a["byte_state"] == "unbacked" and a["public_url"] is None and not a["can_publish"]
    assert client.get(media["public"]).json()["items"] == []


@db_test
def test_cms_pdf_verified_scan_publish_revoke_and_exact_private_delivery(media):
    client, base = media["client"], media["base"]
    a, intent = new_source(media)
    path = base + "/" + a["id"]
    assert client.post(path + "/source", json=intent).json()["source"]["id"] == a["source"]["id"]
    assert client.get(path + "/source/content").status_code == 409
    assert client.post(path + "/publish", json=command(a)).status_code == 409
    scan(media, a["source"]["id"])
    a = client.get(path).json()
    private = client.get(path + "/source/content")
    assert private.content == PDF and "attachment;" in private.headers["content-disposition"]
    response = client.post(path + "/publish", json=command(a))
    assert response.status_code == 200, response.text
    a = response.json()
    assert a["public_url"]
    public = client.get(a["public_url"])
    assert public.content == PDF and public.headers["cache-control"] == "no-store"
    assert "attachment;" in public.headers["content-disposition"]
    listed = client.get(media["public"]).json()["items"][0]
    assert listed["source"] is None and listed["prepared"] is None
    assert "object_key" not in response.text and "storage_version" not in response.text
    assert (
        client.post(path + "/revoke", json={**command(a), "expected_version": 1}).status_code == 409
    )
    assert client.post(path + "/revoke", json=command(a)).status_code == 200
    assert client.get(a["public_url"]).status_code == 404
    assert client.get(path + "/source/content").content == PDF


@db_test
def test_cms_images_need_sanitized_separately_scanned_derivative(media):
    client, base = media["client"], media["base"]
    a, _ = new_source(media, image_bytes(), "image/png")
    path = base + "/" + a["id"]
    scan(media, a["source"]["id"])
    a = client.get(path).json()
    assert not a["can_publish"]
    response = client.post(path + "/prepare", json=command(a))
    assert response.status_code == 200, response.text
    a = response.json()
    assert a["prepared"]["state"] == "quarantined" and not a["can_publish"]
    assert client.post(path + "/publish", json=command(a)).status_code == 409
    scan(media, a["prepared"]["id"])
    a = client.get(path).json()
    published = client.post(path + "/publish", json=command(a))
    assert published.status_code == 200, published.text
    response = client.get(published.json()["public_url"])
    assert response.status_code == 200 and "inline;" in response.headers["content-disposition"]
    assert (
        b"secret-untrusted-metadata" not in response.content and response.content != image_bytes()
    )
    with Session(media["engine"]) as db:
        rows = list(db.scalars(select(FileObject)))
        assert len(rows) == 2 and {row.resource_id for row in rows} == {UUID(a["id"])}
        assert {row.owner_person_id for row in rows} == {rows[0].owner_person_id}
        actor = db.get(User, media["actor"])
        domain = asset_service.asset(db, media["org"], UUID(a["id"]))
        with pytest.raises(AuthError, match="file_count_exceeded"):
            files.create_file(
                db,
                asset_service.context(domain, actor, rows[0].owner_person_id),
                actor,
                FileCreate(
                    client_request_id=uuid4(),
                    policy_id=media["policy"],
                    media_type="image/png",
                    byte_size=len(image_bytes()),
                    sha256=hashlib.sha256(image_bytes()).hexdigest(),
                ),
                "third-file",
            )


@db_test
def test_cms_wrong_org_revoked_permissions_and_malicious_source(media):
    client, base = media["client"], media["base"]
    data = b"\x89PNG\r\n\x1a\nNot a decoded image"
    a, _ = new_source(media, data, "image/png")
    path = base + "/" + a["id"]
    scan(media, a["source"]["id"])
    a = client.get(path).json()
    assert client.post(path + "/prepare", json=command(a)).status_code == 422
    wrong = path.replace(str(media["org"]), str(media["other"]))
    assert client.get(wrong).status_code == 403
    with media["engine"].begin() as connection:
        connection.execute(text("DELETE FROM user_roles"))
    assert client.get(path + "/source/content").status_code == 403
    assert client.post(path + "/prepare", json=command(a)).status_code == 403


@db_test
def test_cms_publication_survives_operational_version_and_expires_at_retention(media):
    client, base = media["client"], media["base"]
    a, _ = new_source(media)
    path = base + "/" + a["id"]
    scan(media, a["source"]["id"])
    a = client.get(path).json()
    a = client.post(path + "/publish", json=command(a)).json()
    with Session(media["engine"]) as db:
        row = db.get(FileObject, a["source"]["id"])
        actor = db.get(User, media["actor"])
        domain = asset_service.asset(db, media["org"], UUID(a["id"]))
        files.set_legal_hold(
            db,
            asset_service.context(domain, actor, row.owner_person_id),
            actor,
            row.id,
            row.version,
            True,
            "hold",
        )
    assert client.get(a["public_url"]).status_code == 200
    with Session(media["engine"]) as db:
        row = db.get(FileObject, a["source"]["id"])
        with pytest.raises(DBAPIError):
            db.execute(text("UPDATE cms_asset_files SET role='public_derivative'"))
        db.rollback()
    # Expiry itself prevents access even when a legal hold correctly preserves stored bytes.
    with patch("app.modules.cms.asset_service.now", return_value=now() + timedelta(days=2)):
        assert client.get(a["public_url"]).status_code == 404


@db_test
def test_cms_mutation_only_grants_do_not_disclose_file_metadata(media):
    client, base = media["client"], media["base"]
    a = client.post(base, json=metadata(media)).json()
    with media["engine"].begin() as connection:
        connection.execute(
            text("DELETE FROM role_permissions WHERE permission_code='cms.asset.view'")
        )
    assert client.post(base, json=metadata(media)).status_code == 403
    for action in ("prepare", "publish", "revoke"):
        result = client.post(
            base + "/" + a["id"] + "/" + action,
            json={"expected_version": 1, "reason": "Synthetic action-only grant"},
        )
        assert result.status_code == 403, result.text


@db_test
def test_cms_binding_scope_immutability_and_atomic_source_creation(media):
    client, base = media["client"], media["base"]
    a = client.post(base, json=metadata(media)).json()
    intent = {
        "expected_version": 1,
        "client_request_id": str(uuid4()),
        "policy_id": str(media["policy"]),
        "media_type": "application/pdf",
        "byte_size": len(PDF),
        "sha256": hashlib.sha256(PDF).hexdigest(),
    }
    with patch(
        "app.modules.cms.asset_service._audit", side_effect=RuntimeError("synthetic audit failure")
    ):
        assert client.post(base + "/" + a["id"] + "/source", json=intent).status_code == 500
    with Session(media["engine"]) as db:
        assert list(db.scalars(select(FileObject))) == []
        assert list(db.scalars(select(AssetFile))) == []
    result = client.post(base + "/" + a["id"] + "/source", json=intent)
    assert result.status_code == 201, result.text
    other = client.post(base, json=metadata(media)).json()
    with Session(media["engine"]) as db:
        source = db.get(FileObject, UUID(result.json()["source"]["id"]))
        db.add(
            AssetFile(
                asset_id=UUID(other["id"]),
                organization_id=media["org"],
                owner_person_id=source.owner_person_id,
                file_id=source.id,
                role="source",
            )
        )
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()
        with pytest.raises(DBAPIError):
            db.execute(text("UPDATE cms_asset_files SET role='public_derivative'"))


@db_test
def test_cms_download_rechecks_session_after_provider_snapshot(media):
    client, base = media["client"], media["base"]
    a, _ = new_source(media)
    scan(media, a["source"]["id"])
    original = asset_routes.private_download

    def revoke_during_snapshot(*args, **kwargs):
        result = original(*args, **kwargs)
        with media["engine"].begin() as connection:
            connection.execute(text("UPDATE refresh_sessions SET revoked_at=CURRENT_TIMESTAMP"))
        return result

    with patch("app.modules.cms.asset_routes.private_download", side_effect=revoke_during_snapshot):
        result = client.get(base + "/" + a["id"] + "/source/content")
    assert result.status_code == 401 and PDF not in result.content


@db_test
def test_cms_image_two_file_policy_and_retired_source_cannot_create_derivative(media):
    client, base = media["client"], media["base"]
    source, _ = new_source(media, image_bytes(), "image/png")
    scan(media, source["source"]["id"])
    source = client.get(base + "/" + source["id"]).json()
    with Session(media["engine"]) as db:
        actor = db.get(User, media["actor"])
        data = files.get_policy(db, media["org"], media["policy"], actor).model_dump(
            exclude={
                "id",
                "organization_id",
                "edition",
                "version",
                "state",
                "published_at",
                "created_at",
                "updated_at",
            }
        )
        data.update(
            client_request_id=uuid4(),
            max_files=1,
            reason="Synthetic one-file edition",
            copy_from=media["policy"],
        )
        policy = files.create_policy(
            db, media["org"], actor, FilePolicyCreate(**data), "new-policy"
        )
        files.publish_policy(
            db,
            media["org"],
            policy.id,
            actor,
            FilePolicyCommand(expected_version=1, reason="Synthetic only"),
            "publish-policy",
        )
        policy_id = str(policy.id)
    response = client.post(base + "/" + source["id"] + "/prepare", json=command(source))
    assert (
        response.status_code == 409 and response.json()["error"]["code"] == "asset_policy_retired"
    )
    asset = client.post(base, json=metadata(media, image_bytes(), "image/png")).json()
    result = client.post(
        base + "/" + asset["id"] + "/source",
        json={
            "expected_version": 1,
            "client_request_id": str(uuid4()),
            "policy_id": policy_id,
            "media_type": "image/png",
            "byte_size": len(image_bytes()),
            "sha256": hashlib.sha256(image_bytes()).hexdigest(),
        },
    )
    assert (
        result.status_code == 422
        and result.json()["error"]["code"] == "asset_policy_requires_derivative"
    )
