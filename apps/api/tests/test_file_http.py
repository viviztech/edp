import hashlib
import io
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.modules.files.http import bounded_upload, private_download
from app.modules.files.storage import LocalPrivateStorage
from app.modules.identity.security import AuthError

PDF = b"%PDF-1.4\nSynthetic private transport test\n%%EOF"


@pytest.fixture
def file_settings(tmp_path):
    root = tmp_path / "private-temp"
    root.mkdir(mode=0o700)
    return Settings(
        _env_file=None,
        app_env="test",
        database_url="postgresql+psycopg://unused@localhost/edp_test",
        redis_url="redis://localhost/15",
        files_enabled=True,
        files_temp_root=str(root),
    )


def request(chunks, headers):
    iterator = iter(chunks)

    async def receive():
        try:
            chunk = next(iterator)
        except StopIteration:
            return {"type": "http.request", "body": b"", "more_body": False}
        return {"type": "http.request", "body": chunk, "more_body": True}

    return Request(
        {"type": "http", "headers": [(k.encode(), v.encode()) for k, v in headers.items()]}, receive
    )


@pytest.mark.parametrize("declared", [None, "1", str(len(PDF))])
async def test_transport_counts_actual_bytes_even_when_length_is_missing_or_misleading(
    file_settings, declared
):
    headers = {"content-type": "application/pdf"}
    if declared is not None:
        headers["content-length"] = declared
    value = request([PDF[:5], PDF[5:]], headers)
    async with bounded_upload(
        value, media_type="application/pdf", byte_size=len(PDF), settings=file_settings
    ) as source:
        assert source.read() == PDF
        opened = source
    assert opened.closed
    assert not list(Path(file_settings.files_temp_root).iterdir())


@pytest.mark.parametrize(
    ("headers", "body", "code"),
    [
        ({"content-type": "application/pdf"}, PDF + b"x", "file_body_too_large"),
        ({"content-type": "application/pdf"}, PDF[:-1], "file_body_size_mismatch"),
        (
            {"content-type": "application/pdf", "content-length": "invalid"},
            PDF,
            "file_body_invalid",
        ),
        (
            {"content-type": "application/pdf", "content-length": "9999999999999"},
            PDF,
            "file_body_too_large",
        ),
        ({"content-type": "image/png"}, PDF, "file_content_type_invalid"),
        (
            {"content-type": "application/pdf", "content-encoding": "gzip"},
            PDF,
            "file_content_type_invalid",
        ),
    ],
)
async def test_transport_rejects_mismatched_and_unbounded_bodies(
    file_settings, headers, body, code
):
    with pytest.raises(AuthError) as error:
        async with bounded_upload(
            request([body], headers),
            media_type="application/pdf",
            byte_size=len(PDF),
            settings=file_settings,
        ):
            pytest.fail("invalid body reached storage")
    assert error.value.code == code


def test_download_verifies_snapshot_before_headers_and_uses_safe_attachment_headers(
    tmp_path, file_settings
):
    storage = LocalPrivateStorage(
        tmp_path / "objects",
        max_bytes=1024,
        temp_root=Path(file_settings.files_temp_root),
    )
    file_id = uuid4()
    ref = storage.put(
        f"quarantine/{uuid4()}/{file_id}",
        io.BytesIO(PDF),
        "application/pdf",
        len(PDF),
        hashlib.sha256(PDF).hexdigest(),
    )
    app = FastAPI()

    @app.get("/synthetic-download")
    def download():
        return private_download(storage, ref, file_id)

    with TestClient(app) as client:
        result = client.get("/synthetic-download")
    assert result.status_code == 200 and result.content == PDF
    assert result.headers["content-disposition"] == f'attachment; filename="file-{file_id}.pdf"'
    assert result.headers["cache-control"] == "private, no-store"
    assert result.headers["x-content-type-options"] == "nosniff"
    assert result.headers["content-length"] == str(len(PDF))
    storage.root.joinpath(*ref.key.split("/")).write_bytes(b"Corrupted object")
    with pytest.raises(AuthError) as error:
        private_download(storage, ref, file_id)
    assert error.value.code == "file_integrity_error"
