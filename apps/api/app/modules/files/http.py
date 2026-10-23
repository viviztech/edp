"""Bounded byte transport. Domain routes must authorize before calling these helpers."""

import asyncio
import tempfile
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from typing import BinaryIO, cast
from uuid import UUID

from fastapi import Request
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings
from app.modules.files.runtime import private_temp_root, require_files_enabled
from app.modules.files.storage import PrivateStorage, StorageError, StoredObject
from app.modules.identity.security import AuthError

CHUNK_SIZE = 65536
EXTENSIONS = {
    "application/pdf": "pdf",
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "text/plain": "txt",
}


@asynccontextmanager
async def bounded_upload(
    request: Request, *, media_type: str, byte_size: int, settings: Settings
) -> AsyncIterator[BinaryIO]:
    """Verify a bounded body before a domain service claims its storage-write lease."""
    require_files_enabled(settings)
    if media_type not in EXTENSIONS or not 1 <= byte_size <= settings.files_max_bytes:
        raise AuthError("file_metadata_invalid", 422)
    content_type = request.headers.get("content-type", "").strip().lower()
    # Raw media bytes only; multipart parsers and caller-supplied filenames are unnecessary.
    if content_type != media_type or request.headers.get("content-encoding"):
        raise AuthError("file_content_type_invalid", 415)
    declared = request.headers.get("content-length")
    if declared is not None:
        if not declared.isascii() or not declared.isdecimal():
            raise AuthError("file_body_invalid", 422)
        if len(declared) > 12 or int(declared) > byte_size:
            raise AuthError("file_body_too_large", 413)
    root = private_temp_root(settings)
    try:
        with cast(BinaryIO, tempfile.TemporaryFile("w+b", dir=root)) as source:
            measured = 0
            try:
                async with asyncio.timeout(min(90, settings.files_upload_lease_seconds)):
                    async for chunk in request.stream():
                        measured += len(chunk)
                        if measured > byte_size:
                            raise AuthError("file_body_too_large", 413)
                        await run_in_threadpool(source.write, chunk)
            except TimeoutError:
                raise AuthError("file_upload_timeout", 408) from None
            if measured != byte_size:
                raise AuthError("file_body_size_mismatch", 422)
            source.seek(0)
            yield source
    except AuthError:
        raise
    except (OSError, ValueError):
        raise AuthError("file_runtime_unavailable", 503) from None


def private_download(
    storage: PrivateStorage, ref: StoredObject, file_id: UUID
) -> StreamingResponse:
    """Fully verify a pinned snapshot before headers; callers reauthorize every request."""
    extension = EXTENSIONS.get(ref.media_type)
    if extension is None:
        raise AuthError("file_integrity_error", 503)
    context = storage.open(ref)
    try:
        source = context.__enter__()
    except StorageError:
        raise AuthError("file_integrity_error", 503) from None
    closed = False

    def close() -> None:
        nonlocal closed
        if not closed:
            closed = True
            context.__exit__(None, None, None)

    def chunks() -> Iterator[bytes]:
        try:
            while chunk := source.read(CHUNK_SIZE):
                yield chunk
        finally:
            close()

    return StreamingResponse(
        chunks(),
        media_type=ref.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="file-{file_id}.{extension}"',
            "Content-Length": str(ref.byte_size),
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "sandbox; default-src 'none'",
        },
        background=BackgroundTask(close),
    )
