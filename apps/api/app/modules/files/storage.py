"""Private immutable byte adapters. Authorization belongs to the files service."""

import base64
import codecs
import hashlib
import hmac
import os
import re
import shutil
import stat
import sys
import tempfile
from collections.abc import Iterator
from contextlib import AbstractContextManager, ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Protocol, cast
from uuid import UUID

CHUNK_SIZE = 65536
MEDIA_TYPES = frozenset({"application/pdf", "image/jpeg", "image/png", "image/webp", "text/plain"})


class StorageError(RuntimeError):
    """Only a fixed reason code crosses the adapter boundary, never provider diagnostics."""

    def __init__(self, code: str = "storage_unavailable") -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class StoredObject:
    key: str
    version_id: str
    media_type: str
    byte_size: int
    sha256: str


class PrivateStorage(Protocol):
    def put(
        self, key: str, source: BinaryIO, media_type: str, byte_size: int, sha256: str
    ) -> StoredObject: ...

    def open(self, ref: StoredObject) -> AbstractContextManager[BinaryIO]: ...

    def delete(self, ref: StoredObject) -> None: ...

    def recover(
        self, key: str, media_type: str, byte_size: int, sha256: str
    ) -> StoredObject | None: ...


def validate_key(key: str) -> None:
    parts = key.split("/")
    if len(parts) != 3 or parts[0] != "quarantine":
        raise StorageError("storage_key_invalid")
    try:
        if any(str(UUID(part)) != part for part in parts[1:]):
            raise ValueError
        if UUID(parts[2]).version != 4:
            raise ValueError
    except (ValueError, AttributeError):
        raise StorageError("storage_key_invalid") from None


def _validate_metadata(media_type: str, byte_size: int, digest: str, max_bytes: int) -> None:
    if type(byte_size) is not int or not 1 <= byte_size <= max_bytes:
        raise StorageError("storage_size_invalid")
    if media_type not in MEDIA_TYPES:
        raise StorageError("storage_type_invalid")
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise StorageError("storage_hash_invalid")


def _signature(prefix: bytes) -> str | None:
    if prefix.startswith(b"%PDF-"):
        return "application/pdf"
    if prefix.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if prefix.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if prefix.startswith(b"RIFF") and prefix[8:12] == b"WEBP":
        return "image/webp"
    return None


def _plain_text(value: str) -> None:
    if any((ord(char) < 32 and char not in "\n\r\t") or 127 <= ord(char) <= 159 for char in value):
        raise StorageError("storage_type_mismatch")


def _copy_verified(
    source: BinaryIO, target: BinaryIO, media_type: str, byte_size: int, digest: str
) -> None:
    measured = 0
    hasher = hashlib.sha256()
    prefix = bytearray()
    decoder = (
        codecs.getincrementaldecoder("utf-8")("strict") if media_type == "text/plain" else None
    )
    try:
        while True:
            chunk = source.read(min(CHUNK_SIZE, byte_size - measured + 1))
            if not isinstance(chunk, bytes):
                raise StorageError("storage_stream_invalid")
            if not chunk:
                break
            measured += len(chunk)
            if measured > byte_size:
                raise StorageError("storage_size_mismatch")
            prefix.extend(chunk[: max(0, 16 - len(prefix))])
            hasher.update(chunk)
            if decoder:
                _plain_text(decoder.decode(chunk))
            target.write(chunk)
        if decoder:
            _plain_text(decoder.decode(b"", final=True))
    except UnicodeError:
        raise StorageError("storage_type_mismatch") from None
    if measured != byte_size:
        raise StorageError("storage_size_mismatch")
    if not hmac.compare_digest(hasher.hexdigest(), digest):
        raise StorageError("storage_hash_mismatch")
    detected = _signature(bytes(prefix))
    if (media_type == "text/plain" and detected) or (
        media_type != "text/plain" and detected != media_type
    ):
        raise StorageError("storage_type_mismatch")
    target.flush()
    target.seek(0)


@contextmanager
def _verified_spool(
    source: BinaryIO,
    media_type: str,
    byte_size: int,
    digest: str,
    max_bytes: int,
    temp_root: Path | None = None,
) -> Iterator[BinaryIO]:
    _validate_metadata(media_type, byte_size, digest, max_bytes)
    _temp_root(temp_root)
    with cast(BinaryIO, tempfile.TemporaryFile("w+b", dir=temp_root)) as spool:
        _copy_verified(source, spool, media_type, byte_size, digest)
        yield spool


def _reparse(path: Path) -> bool:
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def _temp_root(path: Path | None) -> Path | None:
    if path is None:
        return None
    try:
        if (
            not path.is_absolute()
            or not path.is_dir()
            or any(_reparse(parent) for parent in (path, *path.parents))
        ):
            raise StorageError("storage_configuration_invalid")
    except OSError:
        raise StorageError("storage_configuration_invalid") from None
    return path


def _posix_flags(*, directory: bool = False) -> int:
    nofollow = getattr(os, "O_NOFOLLOW", None)
    directory_flag = getattr(os, "O_DIRECTORY", None)
    if not isinstance(nofollow, int) or (directory and not isinstance(directory_flag, int)):
        raise StorageError("storage_configuration_invalid")
    return nofollow | (cast(int, directory_flag) if directory else 0)


def _windows_handle(
    path: Path, *, directory: bool = False, create: bool = False, delete: bool = False
) -> int:
    if sys.platform != "win32":
        raise StorageError("storage_configuration_invalid")

    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    kernel.CreateFileW.restype = wintypes.HANDLE
    access = (
        0x80
        if directory
        else 0x80000000 | (0x40000000 if create else 0) | (0x10000 if delete else 0)
    )
    sharing = 0x1 | (0x2 if directory else 0)  # Deny directory rename; deny file write/delete.
    flags = 0x00200000 | (0x02000000 if directory else 0x80)
    handle = kernel.CreateFileW(str(path), access, sharing, None, 1 if create else 3, flags, None)
    if handle == ctypes.c_void_p(-1).value:
        error = ctypes.get_last_error()
        if error in {80, 183}:
            raise FileExistsError
        if error in {2, 3}:
            raise FileNotFoundError
        raise StorageError()

    class Attributes(ctypes.Structure):
        _fields_ = [("attributes", wintypes.DWORD), ("tag", wintypes.DWORD)]

    attributes = Attributes()
    kernel.GetFileInformationByHandleEx.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    kernel.GetFileInformationByHandleEx.restype = wintypes.BOOL
    if (
        not kernel.GetFileInformationByHandleEx(
            handle, 9, ctypes.byref(attributes), ctypes.sizeof(attributes)
        )
        or attributes.attributes & 0x400
        or bool(attributes.attributes & 0x10) != directory
    ):
        _windows_close(int(handle))
        raise StorageError("storage_path_invalid")
    return int(handle)


def _windows_close(handle: int) -> None:
    if sys.platform != "win32":
        raise StorageError("storage_configuration_invalid")

    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    kernel.CloseHandle(handle)


def _windows_unlink(file: BinaryIO) -> None:
    if sys.platform != "win32":
        raise StorageError("storage_configuration_invalid")

    import ctypes
    import msvcrt
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    delete = wintypes.BOOL(True)
    kernel.SetFileInformationByHandle.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    kernel.SetFileInformationByHandle.restype = wintypes.BOOL
    if not kernel.SetFileInformationByHandle(
        msvcrt.get_osfhandle(file.fileno()), 4, ctypes.byref(delete), ctypes.sizeof(delete)
    ):
        raise StorageError()


class LocalPrivateStorage:
    def __init__(self, root: Path, *, max_bytes: int, temp_root: Path | None = None) -> None:
        if max_bytes < 1:
            raise StorageError("storage_configuration_invalid")
        self.root = Path(os.path.abspath(root))
        if sys.platform == "win32" and self.root.drive.startswith("\\\\"):
            raise StorageError("storage_path_invalid")
        self.max_bytes = max_bytes
        self.temp_root = _temp_root(temp_root)

    @contextmanager
    def _parent(self, key: str, *, create: bool = False) -> Iterator[tuple[Path, int | None, str]]:
        validate_key(key)
        target = self.root.joinpath(*key.split("/"))
        with ExitStack() as stack:
            parent_fd: int | None = None
            path = Path(target.anchor)
            if sys.platform == "win32":
                stack.callback(_windows_close, _windows_handle(path, directory=True))
            else:
                parent_fd = os.open(path, os.O_RDONLY | _posix_flags(directory=True))
                stack.callback(os.close, parent_fd)
            for part in target.parent.parts[1:]:
                path = path / part
                try:
                    if sys.platform == "win32":
                        if create:
                            path.mkdir(mode=0o700, exist_ok=True)
                        if _reparse(path):
                            raise StorageError("storage_path_invalid")
                        stack.callback(_windows_close, _windows_handle(path, directory=True))
                    else:
                        if create:
                            try:
                                os.mkdir(part, mode=0o700, dir_fd=parent_fd)
                            except FileExistsError:
                                pass
                        parent_fd = os.open(
                            part, os.O_RDONLY | _posix_flags(directory=True), dir_fd=parent_fd
                        )
                        stack.callback(os.close, parent_fd)
                except FileNotFoundError:
                    raise
                except OSError:
                    raise StorageError("storage_path_invalid") from None
            yield target.parent, parent_fd, target.name

    @contextmanager
    def _file(
        self,
        parent: Path,
        parent_fd: int | None,
        name: str,
        *,
        create: bool = False,
        delete: bool = False,
    ) -> Iterator[BinaryIO]:
        if sys.platform == "win32":
            import msvcrt

            handle = _windows_handle(parent / name, create=create, delete=delete or create)
            try:
                descriptor = msvcrt.open_osfhandle(
                    handle, os.O_BINARY | (os.O_RDWR if create else os.O_RDONLY)
                )
            except Exception:
                _windows_close(handle)
                raise
        else:
            descriptor = os.open(
                name,
                _posix_flags() | (os.O_RDWR | os.O_CREAT | os.O_EXCL if create else os.O_RDONLY),
                0o600,
                dir_fd=parent_fd,
            )
        with os.fdopen(descriptor, "w+b" if create else "rb") as opened:
            info = os.fstat(opened.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise StorageError("storage_path_invalid")
            if sys.platform != "win32":
                import fcntl

                fcntl.flock(opened.fileno(), fcntl.LOCK_EX if create or delete else fcntl.LOCK_SH)
                current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
                if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
                    raise StorageError("storage_version_mismatch")
            yield opened

    @staticmethod
    def _version(opened: BinaryIO, digest: str) -> str:
        info = os.fstat(opened.fileno())
        identity = f"{info.st_dev}:{info.st_ino}:{info.st_ctime_ns}:{info.st_size}:{digest}"
        return hashlib.sha256(identity.encode("ascii")).hexdigest()

    def put(
        self, key: str, source: BinaryIO, media_type: str, byte_size: int, sha256: str
    ) -> StoredObject:
        validate_key(key)
        try:
            with (
                _verified_spool(
                    source, media_type, byte_size, sha256, self.max_bytes, self.temp_root
                ) as verified,
                self._parent(key, create=True) as (parent, parent_fd, name),
            ):
                try:
                    with self._file(parent, parent_fd, name, create=True) as opened:
                        try:
                            shutil.copyfileobj(verified, opened, CHUNK_SIZE)
                            opened.flush()
                            os.fsync(opened.fileno())
                            version = self._version(opened, sha256)
                        except Exception:
                            if sys.platform == "win32":
                                _windows_unlink(opened)
                            else:
                                os.unlink(name, dir_fd=parent_fd)
                            raise
                except FileExistsError:
                    with self._file(parent, parent_fd, name) as opened:
                        with _verified_spool(
                            opened, media_type, byte_size, sha256, self.max_bytes, self.temp_root
                        ):
                            version = self._version(opened, sha256)
                return StoredObject(key, version, media_type, byte_size, sha256)
        except StorageError:
            raise
        except Exception:
            raise StorageError() from None

    @contextmanager
    def open(self, ref: StoredObject) -> Iterator[BinaryIO]:
        validate_key(ref.key)
        _validate_metadata(ref.media_type, ref.byte_size, ref.sha256, self.max_bytes)
        consumer_error: BaseException | None = None
        try:
            with (
                self._parent(ref.key) as (parent, parent_fd, name),
                self._file(parent, parent_fd, name) as opened,
            ):
                if self._version(opened, ref.sha256) != ref.version_id:
                    raise StorageError("storage_version_mismatch")
                with _verified_spool(
                    opened,
                    ref.media_type,
                    ref.byte_size,
                    ref.sha256,
                    self.max_bytes,
                    self.temp_root,
                ) as verified:
                    if self._version(opened, ref.sha256) != ref.version_id:
                        raise StorageError("storage_version_mismatch")
                    try:
                        yield verified
                    except BaseException as error:
                        consumer_error = error
                        raise
        except StorageError:
            raise
        except FileNotFoundError as error:
            if error is consumer_error:
                raise
            raise StorageError("storage_not_found") from None
        except Exception as error:
            if error is consumer_error:
                raise
            raise StorageError() from None

    def delete(self, ref: StoredObject) -> None:
        validate_key(ref.key)
        _validate_metadata(ref.media_type, ref.byte_size, ref.sha256, self.max_bytes)
        try:
            with (
                self._parent(ref.key) as (parent, parent_fd, name),
                self._file(parent, parent_fd, name, delete=True) as opened,
            ):
                if self._version(opened, ref.sha256) != ref.version_id:
                    raise StorageError("storage_version_mismatch")
                with _verified_spool(
                    opened,
                    ref.media_type,
                    ref.byte_size,
                    ref.sha256,
                    self.max_bytes,
                    self.temp_root,
                ):
                    if sys.platform == "win32":
                        _windows_unlink(opened)
                    else:
                        os.unlink(name, dir_fd=parent_fd)
        except FileNotFoundError:
            return
        except StorageError:
            raise
        except Exception:
            raise StorageError() from None

    def recover(
        self, key: str, media_type: str, byte_size: int, sha256: str
    ) -> StoredObject | None:
        validate_key(key)
        _validate_metadata(media_type, byte_size, sha256, self.max_bytes)
        try:
            with (
                self._parent(key) as (parent, parent_fd, name),
                self._file(parent, parent_fd, name) as opened,
            ):
                version = self._version(opened, sha256)
                with _verified_spool(
                    opened, media_type, byte_size, sha256, self.max_bytes, self.temp_root
                ):
                    if version != self._version(opened, sha256):
                        raise StorageError("storage_version_mismatch")
                    return StoredObject(key, version, media_type, byte_size, sha256)
        except FileNotFoundError:
            return None
        except StorageError:
            raise
        except Exception:
            raise StorageError() from None


class S3Client(Protocol):
    def get_bucket_versioning(self, **kwargs: Any) -> dict[str, Any]: ...
    def get_public_access_block(self, **kwargs: Any) -> dict[str, Any]: ...
    def put_object(self, **kwargs: Any) -> dict[str, Any]: ...
    def head_object(self, **kwargs: Any) -> dict[str, Any]: ...
    def get_object(self, **kwargs: Any) -> dict[str, Any]: ...
    def delete_object(self, **kwargs: Any) -> dict[str, Any]: ...


def _provider_code(error: Exception) -> str:
    response = getattr(error, "response", None)
    if isinstance(response, dict):
        details = response.get("Error")
        if isinstance(details, dict) and isinstance(details.get("Code"), str):
            return cast(str, details["Code"])
    return ""


class S3PrivateStorage:
    def __init__(
        self,
        client: S3Client,
        *,
        bucket: str,
        max_bytes: int,
        server_side_encryption: str = "AES256",
        kms_key_id: str | None = None,
        temp_root: Path | None = None,
    ) -> None:
        if (
            not bucket
            or max_bytes < 1
            or server_side_encryption not in {"AES256", "aws:kms"}
            or (server_side_encryption == "aws:kms" and not kms_key_id)
            or (server_side_encryption == "AES256" and kms_key_id is not None)
        ):
            raise StorageError("storage_configuration_invalid")
        self.client, self.bucket, self.max_bytes = client, bucket, max_bytes
        self.encryption, self.kms_key_id = server_side_encryption, kms_key_id
        self.temp_root = _temp_root(temp_root)

    def _private_versioned(self) -> None:
        try:
            if self.client.get_bucket_versioning(Bucket=self.bucket).get("Status") != "Enabled":
                raise StorageError("storage_versioning_required")
            block = self.client.get_public_access_block(Bucket=self.bucket).get(
                "PublicAccessBlockConfiguration", {}
            )
            if not isinstance(block, dict) or not all(
                block.get(name) is True
                for name in (
                    "BlockPublicAcls",
                    "IgnorePublicAcls",
                    "BlockPublicPolicy",
                    "RestrictPublicBuckets",
                )
            ):
                raise StorageError("storage_private_required")
        except StorageError:
            raise
        except Exception:
            raise StorageError() from None

    def _check_response(self, result: dict[str, Any], ref: StoredObject) -> None:
        checksum = base64.b64encode(bytes.fromhex(ref.sha256)).decode("ascii")
        if (
            result.get("VersionId") != ref.version_id
            or result.get("ContentLength") != ref.byte_size
            or result.get("ContentType") != ref.media_type
            or result.get("ChecksumSHA256") != checksum
            or result.get("Metadata", {}).get("sha256") != ref.sha256
        ):
            raise StorageError("storage_object_mismatch")
        if result.get("ServerSideEncryption") != self.encryption or (
            self.kms_key_id and result.get("SSEKMSKeyId") != self.kms_key_id
        ):
            raise StorageError("storage_encryption_mismatch")

    @staticmethod
    def _version(value: object) -> str:
        if (
            not isinstance(value, str)
            or value in {"", "null"}
            or len(value) > 1024
            or any(ord(char) < 33 or ord(char) > 126 for char in value)
        ):
            raise StorageError("storage_versioning_required")
        return value

    @contextmanager
    def _open(self, ref: StoredObject) -> Iterator[BinaryIO]:
        result = self.client.get_object(
            Bucket=self.bucket, Key=ref.key, VersionId=ref.version_id, ChecksumMode="ENABLED"
        )
        body = result.get("Body")
        try:
            self._check_response(result, ref)
            if body is None:
                raise StorageError("storage_object_mismatch")
            with _verified_spool(
                body, ref.media_type, ref.byte_size, ref.sha256, self.max_bytes, self.temp_root
            ) as verified:
                yield verified
        finally:
            if body is not None:
                body.close()

    def put(
        self, key: str, source: BinaryIO, media_type: str, byte_size: int, sha256: str
    ) -> StoredObject:
        validate_key(key)
        try:
            with _verified_spool(
                source, media_type, byte_size, sha256, self.max_bytes, self.temp_root
            ) as verified:
                self._private_versioned()
                checksum = base64.b64encode(bytes.fromhex(sha256)).decode("ascii")
                try:
                    result = self.client.put_object(
                        Bucket=self.bucket,
                        Key=key,
                        Body=verified,
                        ContentType=media_type,
                        ContentLength=byte_size,
                        ChecksumSHA256=checksum,
                        IfNoneMatch="*",
                        Metadata={"sha256": sha256},
                        ServerSideEncryption=self.encryption,
                        **({"SSEKMSKeyId": self.kms_key_id} if self.kms_key_id else {}),
                    )
                except Exception as error:
                    if _provider_code(error) not in {
                        "PreconditionFailed",
                        "412",
                        "ConditionalRequestConflict",
                    }:
                        raise
                    result = self.client.head_object(
                        Bucket=self.bucket, Key=key, ChecksumMode="ENABLED"
                    )
                    ref = StoredObject(
                        key, self._version(result.get("VersionId")), media_type, byte_size, sha256
                    )
                    self._check_response(result, ref)
                    with self._open(ref):
                        return ref
                ref = StoredObject(
                    key, self._version(result.get("VersionId")), media_type, byte_size, sha256
                )
                if (
                    result.get("ChecksumSHA256") != checksum
                    or result.get("ServerSideEncryption") != self.encryption
                    or (self.kms_key_id and result.get("SSEKMSKeyId") != self.kms_key_id)
                ):
                    raise StorageError("storage_object_mismatch")
                return ref
        except StorageError:
            raise
        except Exception:
            raise StorageError() from None

    @contextmanager
    def open(self, ref: StoredObject) -> Iterator[BinaryIO]:
        validate_key(ref.key)
        _validate_metadata(ref.media_type, ref.byte_size, ref.sha256, self.max_bytes)
        self._version(ref.version_id)
        consumer_error: BaseException | None = None
        try:
            self._private_versioned()
            with self._open(ref) as opened:
                try:
                    yield opened
                except BaseException as error:
                    consumer_error = error
                    raise
        except StorageError:
            raise
        except Exception as error:
            if error is consumer_error:
                raise
            code = (
                "storage_not_found"
                if _provider_code(error) in {"NoSuchKey", "NoSuchVersion", "404"}
                else "storage_unavailable"
            )
            raise StorageError(code) from None

    def delete(self, ref: StoredObject) -> None:
        validate_key(ref.key)
        _validate_metadata(ref.media_type, ref.byte_size, ref.sha256, self.max_bytes)
        self._version(ref.version_id)
        try:
            self._private_versioned()
            result = self.client.head_object(
                Bucket=self.bucket, Key=ref.key, VersionId=ref.version_id, ChecksumMode="ENABLED"
            )
            self._check_response(result, ref)
            self.client.delete_object(Bucket=self.bucket, Key=ref.key, VersionId=ref.version_id)
        except StorageError:
            raise
        except Exception as error:
            if _provider_code(error) in {"NoSuchKey", "NoSuchVersion", "404"}:
                return
            raise StorageError() from None

    def recover(
        self, key: str, media_type: str, byte_size: int, sha256: str
    ) -> StoredObject | None:
        validate_key(key)
        _validate_metadata(media_type, byte_size, sha256, self.max_bytes)
        try:
            self._private_versioned()
            try:
                result = self.client.head_object(
                    Bucket=self.bucket, Key=key, ChecksumMode="ENABLED"
                )
            except Exception as error:
                if _provider_code(error) in {"NoSuchKey", "404"}:
                    return None
                raise
            ref = StoredObject(
                key, self._version(result.get("VersionId")), media_type, byte_size, sha256
            )
            self._check_response(result, ref)
            with self._open(ref):
                return ref
        except StorageError:
            raise
        except Exception:
            raise StorageError() from None
