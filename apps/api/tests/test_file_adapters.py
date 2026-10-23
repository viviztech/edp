import base64
import hashlib
import io
import os
import socket
import struct
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from uuid import uuid4

import boto3
import pytest
from botocore.response import StreamingBody
from botocore.stub import ANY, Stubber

from app.modules.files.scanner import ClamAVScanner
from app.modules.files.storage import LocalPrivateStorage, S3PrivateStorage, StorageError

PDF = b"%PDF-1.4\nSynthetic private document\n%%EOF"


def key():
    return f"quarantine/{uuid4()}/{uuid4()}"


def digest(value):
    return hashlib.sha256(value).hexdigest()


def put(storage, object_key, content=PDF, media_type="application/pdf"):
    return storage.put(object_key, io.BytesIO(content), media_type, len(content), digest(content))


def test_local_exact_immutable_roundtrip_idempotency_and_versioned_delete(tmp_path):
    storage = LocalPrivateStorage(tmp_path / "objects", max_bytes=1024)
    object_key = key()
    assert storage.recover(object_key, "application/pdf", len(PDF), digest(PDF)) is None
    stored = put(storage, object_key)
    assert storage.recover(object_key, "application/pdf", len(PDF), digest(PDF)) == stored
    with pytest.raises(FrozenInstanceError):
        stored.version_id = "changed"
    assert put(storage, object_key) == stored
    with storage.open(stored) as opened:
        assert opened.read() == PDF
    with pytest.raises(StorageError):
        put(storage, object_key, PDF + b"different")
    with storage.open(stored) as opened:
        assert opened.read() == PDF
    storage.delete(stored)
    storage.delete(stored)
    assert storage.recover(object_key, "application/pdf", len(PDF), digest(PDF)) is None
    replacement = put(storage, object_key, PDF + b"new version")
    assert replacement.version_id != stored.version_id
    with pytest.raises(StorageError, match="storage_version_mismatch"):
        storage.delete(stored)
    with storage.open(replacement) as opened:
        assert opened.read() == PDF + b"new version"


def test_local_recovery_refuses_incomplete_or_mismatched_bytes(tmp_path):
    storage = LocalPrivateStorage(tmp_path / "objects", max_bytes=1024)
    object_key = key()
    stored = put(storage, object_key)
    target = storage.root.joinpath(*object_key.split("/"))
    target.write_bytes(b"partial")
    with pytest.raises(StorageError, match="storage_size_mismatch"):
        storage.recover(object_key, stored.media_type, stored.byte_size, stored.sha256)
    assert target.read_bytes() == b"partial"


def test_storage_uses_only_explicit_private_temp_directory_when_configured(tmp_path, monkeypatch):
    import app.modules.files.storage as module

    private_temp = tmp_path / "private-temp"
    private_temp.mkdir(mode=0o700)
    original = module.tempfile.TemporaryFile
    directories = []

    def temporary(*args, **kwargs):
        directories.append(kwargs.get("dir"))
        return original(*args, **kwargs)

    monkeypatch.setattr(module.tempfile, "TemporaryFile", temporary)
    storage = LocalPrivateStorage(tmp_path / "objects", max_bytes=1024, temp_root=private_temp)
    stored = put(storage, key())
    with storage.open(stored) as opened:
        assert opened.read() == PDF
    storage.delete(stored)
    assert directories and all(directory == private_temp for directory in directories)
    assert list(private_temp.iterdir()) == []
    with pytest.raises(StorageError, match="storage_configuration_invalid"):
        LocalPrivateStorage(tmp_path / "other", max_bytes=1024, temp_root=tmp_path / "missing")
    assert not (tmp_path / "missing").exists()


@pytest.mark.parametrize(
    "bad_key",
    [
        "../outside",
        "/absolute",
        "quarantine/../outside",
        "quarantine/org/filename.pdf",
        "quarantine/" + str(uuid4()) + "/" + str(uuid4()) + ":ads",
        "quarantine\\org\\object",
        "https://outside.example/object",
    ],
)
def test_local_rejects_nonopaque_keys_before_writing(tmp_path, bad_key):
    root = tmp_path / "objects"
    with pytest.raises(StorageError, match="storage_key_invalid"):
        put(LocalPrivateStorage(root, max_bytes=1024), bad_key)
    assert not root.exists()


@pytest.mark.parametrize(
    "media_type,content",
    [
        ("image/png", PDF),
        ("application/pdf", b"plain text"),
        ("text/plain", b"bad\xc3\x28"),
        ("text/plain", b"bad\x00text"),
        ("text/plain", PDF),
    ],
)
def test_local_rejects_type_signature_utf8_and_control_mismatches(tmp_path, media_type, content):
    root = tmp_path / "objects"
    with pytest.raises(StorageError, match="storage_type_mismatch"):
        put(LocalPrivateStorage(root, max_bytes=1024), key(), content, media_type)
    assert not root.exists()


def test_local_rejects_size_hash_and_stream_failures_without_partial_objects(tmp_path, monkeypatch):
    import app.modules.files.storage as module

    root = tmp_path / "objects"
    storage = LocalPrivateStorage(root, max_bytes=1024)
    object_key = key()
    for size, checksum in [
        (len(PDF) - 1, digest(PDF)),
        (len(PDF) + 1, digest(PDF)),
        (len(PDF), "0" * 64),
        (2048, digest(PDF)),
    ]:
        with pytest.raises(StorageError):
            storage.put(object_key, io.BytesIO(PDF), "application/pdf", size, checksum)

    def fail_copy(_source, target, _length):
        target.write(b"partial")
        raise OSError("private path and provider secret must not escape")

    monkeypatch.setattr(module.shutil, "copyfileobj", fail_copy)
    with pytest.raises(StorageError) as error:
        put(storage, object_key)
    assert str(error.value) == "storage_unavailable"
    assert not root.joinpath(*object_key.split("/")).exists()


def test_local_rejects_directory_symlink_or_windows_junction(tmp_path):
    root, outside = tmp_path / "objects", tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    marker = outside / "marker.txt"
    marker.write_text("unchanged", encoding="utf-8")
    link = root / "quarantine"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        if os.name != "nt":
            raise
        result = subprocess.run(
            ["cmd.exe", "/c", "mklink", "/J", str(link), str(outside)],
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0
    with pytest.raises(StorageError, match="storage_path_invalid"):
        put(LocalPrivateStorage(root, max_bytes=1024), key())
    assert marker.read_text(encoding="utf-8") == "unchanged"
    assert list(outside.iterdir()) == [marker]


def test_local_conflicting_concurrent_writes_never_overwrite(tmp_path):
    storage = LocalPrivateStorage(tmp_path / "objects", max_bytes=1024)
    object_key = key()

    def write(content):
        try:
            return put(storage, object_key, content)
        except StorageError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(write, [PDF, PDF + b"other"]))
    winners = [item for item in outcomes if item is not None]
    assert len(winners) == 1
    with storage.open(winners[0]) as opened:
        assert opened.read() in {PDF, PDF + b"other"}


@pytest.mark.skipif(os.name != "nt", reason="Windows handle sharing boundary")
def test_windows_holds_parent_and_object_against_replacement_during_read(tmp_path):
    storage = LocalPrivateStorage(tmp_path / "objects", max_bytes=1024)
    object_key = key()
    stored = put(storage, object_key)
    target = storage.root.joinpath(*object_key.split("/"))
    with storage.open(stored):
        with pytest.raises(OSError):
            target.parent.rename(tmp_path / "moved")
        with pytest.raises(OSError):
            target.write_bytes(b"replacement")


def client():
    return boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id="synthetic",
        aws_secret_access_key="synthetic",
        endpoint_url="https://storage.invalid",
    )


def add_private(stub, *, versioning="Enabled", private=True):
    stub.add_response("get_bucket_versioning", {"Status": versioning}, {"Bucket": "private-test"})
    if versioning == "Enabled":
        stub.add_response(
            "get_public_access_block",
            {
                "PublicAccessBlockConfiguration": {
                    name: private
                    for name in [
                        "BlockPublicAcls",
                        "IgnorePublicAcls",
                        "BlockPublicPolicy",
                        "RestrictPublicBuckets",
                    ]
                }
            },
            {"Bucket": "private-test"},
        )


def object_response(content=PDF, version="opaque-version", **overrides):
    return {
        "VersionId": version,
        "ContentLength": len(content),
        "ContentType": "application/pdf",
        "ChecksumSHA256": base64.b64encode(hashlib.sha256(content).digest()).decode(),
        "Metadata": {"sha256": digest(content)},
        "ServerSideEncryption": "AES256",
        **overrides,
    }


def test_s3_conditional_checksummed_put_pinned_read_and_delete_without_provider_calls():
    s3 = client()
    object_key = key()
    storage = S3PrivateStorage(s3, bucket="private-test", max_bytes=1024)
    checksum = object_response()["ChecksumSHA256"]
    with Stubber(s3) as stub:
        add_private(stub)
        stub.add_response(
            "put_object",
            {
                "VersionId": "opaque-version",
                "ChecksumSHA256": checksum,
                "ServerSideEncryption": "AES256",
            },
            {
                "Bucket": "private-test",
                "Key": object_key,
                "Body": ANY,
                "ContentType": "application/pdf",
                "ContentLength": len(PDF),
                "ChecksumSHA256": checksum,
                "IfNoneMatch": "*",
                "Metadata": {"sha256": digest(PDF)},
                "ServerSideEncryption": "AES256",
            },
        )
        stored = put(storage, object_key)
        add_private(stub)
        stub.add_response(
            "get_object",
            {**object_response(), "Body": StreamingBody(io.BytesIO(PDF), len(PDF))},
            {
                "Bucket": "private-test",
                "Key": object_key,
                "VersionId": "opaque-version",
                "ChecksumMode": "ENABLED",
            },
        )
        with storage.open(stored) as opened:
            assert opened.read() == PDF
        add_private(stub)
        stub.add_response(
            "head_object",
            object_response(),
            {
                "Bucket": "private-test",
                "Key": object_key,
                "VersionId": "opaque-version",
                "ChecksumMode": "ENABLED",
            },
        )
        stub.add_response(
            "delete_object",
            {"VersionId": "opaque-version"},
            {"Bucket": "private-test", "Key": object_key, "VersionId": "opaque-version"},
        )
        storage.delete(stored)
        add_private(stub)
        stub.add_client_error(
            "head_object",
            "NoSuchVersion",
            http_status_code=404,
            expected_params={
                "Bucket": "private-test",
                "Key": object_key,
                "VersionId": "opaque-version",
                "ChecksumMode": "ENABLED",
            },
        )
        storage.delete(stored)
        stub.assert_no_pending_responses()


def test_s3_existing_matching_bytes_are_recovered_by_version_and_reverified():
    s3 = client()
    object_key = key()
    with Stubber(s3) as stub:
        add_private(stub)
        stub.add_client_error("put_object", "PreconditionFailed", http_status_code=412)
        stub.add_response(
            "head_object",
            object_response(),
            {"Bucket": "private-test", "Key": object_key, "ChecksumMode": "ENABLED"},
        )
        stub.add_response(
            "get_object",
            {**object_response(), "Body": StreamingBody(io.BytesIO(PDF), len(PDF))},
            {
                "Bucket": "private-test",
                "Key": object_key,
                "VersionId": "opaque-version",
                "ChecksumMode": "ENABLED",
            },
        )
        assert (
            put(S3PrivateStorage(s3, bucket="private-test", max_bytes=1024), object_key).version_id
            == "opaque-version"
        )
        stub.assert_no_pending_responses()


def test_s3_recovery_discovers_then_pins_and_verifies_exact_version():
    s3 = client()
    storage = S3PrivateStorage(s3, bucket="private-test", max_bytes=1024)
    object_key = key()
    with Stubber(s3) as stub:
        add_private(stub)
        stub.add_response(
            "head_object",
            object_response(),
            {"Bucket": "private-test", "Key": object_key, "ChecksumMode": "ENABLED"},
        )
        stub.add_response(
            "get_object",
            {**object_response(), "Body": StreamingBody(io.BytesIO(PDF), len(PDF))},
            {
                "Bucket": "private-test",
                "Key": object_key,
                "VersionId": "opaque-version",
                "ChecksumMode": "ENABLED",
            },
        )
        recovered = storage.recover(object_key, "application/pdf", len(PDF), digest(PDF))
        assert recovered is not None and recovered.version_id == "opaque-version"
        stub.assert_no_pending_responses()
    with Stubber(s3) as stub:
        add_private(stub)
        stub.add_client_error("head_object", "NoSuchKey", http_status_code=404)
        assert storage.recover(object_key, "application/pdf", len(PDF), digest(PDF)) is None
        stub.assert_no_pending_responses()


def test_s3_recovery_never_turns_unknown_failure_into_absence_or_trusts_metadata_only():
    s3 = client()
    storage = S3PrivateStorage(s3, bucket="private-test", max_bytes=1024)
    object_key = key()
    with Stubber(s3) as stub:
        add_private(stub)
        stub.add_client_error(
            "head_object", "AccessDenied", service_message="private secret", http_status_code=403
        )
        with pytest.raises(StorageError, match="storage_unavailable"):
            storage.recover(object_key, "application/pdf", len(PDF), digest(PDF))
    with Stubber(s3) as stub:
        add_private(stub)
        stub.add_response("head_object", object_response())
        stub.add_response(
            "get_object",
            {**object_response(), "Body": StreamingBody(io.BytesIO(b"x" * len(PDF)), len(PDF))},
        )
        with pytest.raises(StorageError, match="storage_hash_mismatch"):
            storage.recover(object_key, "application/pdf", len(PDF), digest(PDF))


def test_s3_kms_encryption_is_requested_and_response_key_verified():
    s3 = client()
    object_key = key()
    kms = "arn:aws:kms:us-east-1:123456789012:key/synthetic-key"
    checksum = object_response()["ChecksumSHA256"]
    storage = S3PrivateStorage(
        s3, bucket="private-test", max_bytes=1024, server_side_encryption="aws:kms", kms_key_id=kms
    )
    for returned_key, succeeds in [(kms, True), ("different-key", False)]:
        with Stubber(s3) as stub:
            add_private(stub)
            stub.add_response(
                "put_object",
                {
                    "VersionId": "version",
                    "ChecksumSHA256": checksum,
                    "ServerSideEncryption": "aws:kms",
                    "SSEKMSKeyId": returned_key,
                },
                {
                    "Bucket": "private-test",
                    "Key": object_key,
                    "Body": ANY,
                    "ContentType": "application/pdf",
                    "ContentLength": len(PDF),
                    "ChecksumSHA256": checksum,
                    "IfNoneMatch": "*",
                    "Metadata": {"sha256": digest(PDF)},
                    "ServerSideEncryption": "aws:kms",
                    "SSEKMSKeyId": kms,
                },
            )
            if succeeds:
                assert put(storage, object_key).version_id == "version"
            else:
                with pytest.raises(StorageError, match="storage_object_mismatch"):
                    put(storage, object_key)
            stub.assert_no_pending_responses()
    with pytest.raises(StorageError, match="storage_configuration_invalid"):
        S3PrivateStorage(
            s3, bucket="private-test", max_bytes=1024, server_side_encryption="aws:kms"
        )


def test_s3_retry_never_adopts_different_existing_content_or_deletes_it():
    s3 = client()
    with Stubber(s3) as stub:
        add_private(stub)
        stub.add_client_error("put_object", "PreconditionFailed", http_status_code=412)
        stub.add_response("head_object", object_response(Metadata={"sha256": "0" * 64}))
        with pytest.raises(StorageError, match="storage_object_mismatch"):
            put(S3PrivateStorage(s3, bucket="private-test", max_bytes=1024), key())
        stub.assert_no_pending_responses()


@pytest.mark.parametrize(
    "overrides",
    [
        {"VersionId": "different-version"},
        {"ContentLength": 1},
        {"ContentType": "image/png"},
        {"ChecksumSHA256": "different-checksum"},
        {"ServerSideEncryption": "aws:kms"},
    ],
)
def test_s3_refuses_mismatched_version_metadata_and_encryption(overrides):
    from app.modules.files.storage import StoredObject

    s3 = client()
    storage = S3PrivateStorage(s3, bucket="private-test", max_bytes=1024)
    ref = StoredObject(key(), "version", "application/pdf", len(PDF), digest(PDF))
    with Stubber(s3) as stub:
        add_private(stub)
        body = StreamingBody(io.BytesIO(PDF), len(PDF))
        stub.add_response(
            "get_object", {**object_response(version="version", **overrides), "Body": body}
        )
        with pytest.raises(StorageError), storage.open(ref):
            pytest.fail("Unverified provider bytes were exposed")
        assert body._raw_stream.closed


@pytest.mark.parametrize(
    "versioning,private,reason",
    [
        ("Suspended", True, "storage_versioning_required"),
        ("Enabled", False, "storage_private_required"),
    ],
)
def test_s3_fails_closed_for_unversioned_or_public_buckets(versioning, private, reason):
    s3 = client()
    with Stubber(s3) as stub:
        add_private(stub, versioning=versioning, private=private)
        with pytest.raises(StorageError, match=reason):
            put(S3PrivateStorage(s3, bucket="private-test", max_bytes=1024), key())
        stub.assert_no_pending_responses()


def test_s3_sanitizes_errors_and_refuses_missing_version_checksum_or_encryption():
    s3 = client()
    storage = S3PrivateStorage(s3, bucket="private-test", max_bytes=1024)
    with Stubber(s3) as stub:
        add_private(stub)
        stub.add_client_error(
            "put_object",
            "AccessDenied",
            service_message="secret credential private-key",
            http_status_code=403,
        )
        with pytest.raises(StorageError) as error:
            put(storage, key())
        assert str(error.value) == "storage_unavailable"
    for response in [
        {"VersionId": "null"},
        {"VersionId": "v1", "ServerSideEncryption": "AES256"},
        {"VersionId": "v1", "ChecksumSHA256": object_response()["ChecksumSHA256"]},
    ]:
        with Stubber(s3) as stub:
            add_private(stub)
            stub.add_response("put_object", response)
            with pytest.raises(StorageError):
                put(storage, key())


def test_s3_open_detects_corrupt_bytes_before_exposing_stream():
    s3 = client()
    object_key = key()
    storage = S3PrivateStorage(s3, bucket="private-test", max_bytes=1024)
    from app.modules.files.storage import StoredObject

    ref = StoredObject(object_key, "version", "application/pdf", len(PDF), digest(PDF))
    with Stubber(s3) as stub:
        add_private(stub)
        body = StreamingBody(io.BytesIO(b"x" * len(PDF)), len(PDF))
        stub.add_response("get_object", {**object_response(version="version"), "Body": body})
        with pytest.raises(StorageError, match="storage_hash_mismatch"), storage.open(ref):
            pytest.fail("Corrupt bytes were exposed")
        assert body._raw_stream.closed


class Peer:
    def __init__(
        self, reply=b"stream: OK\0", *, version=None, delay=0, byte_delay=0, version_delay=0
    ):
        updated = datetime.now(UTC).strftime("%a %b %d %H:%M:%S %Y")
        self.version = (
            version if version is not None else f"ClamAV 1.4.3/27835/{updated}".encode() + b"\0"
        )
        self.reply, self.delay, self.byte_delay = reply, delay, byte_delay
        self.version_delay = version_delay
        self.commands, self.payloads = [], []
        self.stop = threading.Event()
        self.server = socket.socket()
        self.server.bind(("127.0.0.1", 0))
        self.server.listen()
        self.server.settimeout(0.1)
        self.port = self.server.getsockname()[1]
        self.thread = threading.Thread(target=self.run, daemon=True)

    @staticmethod
    def read(connection, size):
        data = bytearray()
        while len(data) < size:
            chunk = connection.recv(size - len(data))
            if not chunk:
                raise EOFError
            data.extend(chunk)
        return bytes(data)

    def run(self):
        while not self.stop.is_set():
            try:
                connection, _ = self.server.accept()
            except TimeoutError:
                continue
            except OSError:
                return
            with connection:
                connection.settimeout(1)
                try:
                    command = bytearray()
                    while not command.endswith(b"\0"):
                        command.extend(self.read(connection, 1))
                    self.commands.append(bytes(command))
                    if command == b"zVERSION\0":
                        if self.stop.wait(self.version_delay):
                            return
                        connection.sendall(self.version)
                        continue
                    assert command == b"zINSTREAM\0"
                    content = bytearray()
                    while True:
                        size = struct.unpack("!I", self.read(connection, 4))[0]
                        if size == 0:
                            break
                        assert size <= 65536
                        content.extend(self.read(connection, size))
                    self.payloads.append(bytes(content))
                    if self.stop.wait(self.delay):
                        return
                    if self.byte_delay:
                        for byte in self.reply:
                            connection.sendall(bytes([byte]))
                            if self.stop.wait(self.byte_delay):
                                return
                    else:
                        connection.sendall(self.reply)
                except (OSError, EOFError):
                    pass

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_args):
        self.stop.set()
        self.server.close()
        self.thread.join(timeout=2)
        assert not self.thread.is_alive()


def scanner(peer, *, timeout=1, max_age=3600, max_reply=1024):
    return ClamAVScanner(
        "127.0.0.1",
        peer.port,
        timeout_seconds=timeout,
        max_reply_bytes=max_reply,
        max_signature_age_seconds=max_age,
    )


@pytest.mark.parametrize(
    "reply,status,reason",
    [
        (b"stream: OK\0", "clean", "clean"),
        (b"stream: Eicar-Signature FOUND\0", "infected", "malware_detected"),
    ],
)
def test_clamav_stream_framing_and_verdict_are_bound_to_exact_hash(reply, status, reason):
    content = PDF * 1800
    with Peer(reply) as peer:
        result = scanner(peer).scan(io.BytesIO(content), max_bytes=len(content))
        assert (result.status, result.reason_code, result.sha256, result.byte_size) == (
            status,
            reason,
            digest(content),
            len(content),
        )
        assert peer.commands == [b"zVERSION\0", b"zINSTREAM\0"]
        assert peer.payloads == [content]
        assert result.engine_version == "1.4.3"
        assert result.signature_updated_at is not None


@pytest.mark.parametrize(
    "reply",
    [
        b"stream: OK",
        b"stream: OK\0stream: Eicar FOUND\0",
        b"stream: OK extra\0",
        b"INSTREAM size limit exceeded ERROR\0",
        b"stream: \xff FOUND\0",
        b"x" * 1025 + b"\0",
    ],
)
def test_clamav_unknown_truncated_oversized_or_error_reply_never_cleans(reply):
    with Peer(reply) as peer:
        result = scanner(peer).scan(io.BytesIO(PDF), max_bytes=1024)
        assert result.status == "error"
        assert result.sha256 == digest(PDF)
        assert result.byte_size == len(PDF)
        assert "Eicar" not in result.reason_code


@pytest.mark.parametrize(
    "version",
    [b"UNKNOWN\0", b"ClamAV 1.4.3/1/unknown\0", b"ClamAV 1.4.3/1/Mon Jan 01 00:00:00 2024\0"],
)
def test_clamav_required_unknown_or_stale_signatures_fail_before_stream(version):
    with Peer(version=version) as peer:
        result = scanner(peer).scan(io.BytesIO(PDF), max_bytes=1024)
        assert result.status == "error"
        assert result.signature_updated_at is None
        assert peer.commands == [b"zVERSION\0"]


def test_clamav_total_deadline_is_not_reset_by_slow_reply_bytes():
    with Peer(byte_delay=0.03) as peer:
        started = time.monotonic()
        result = scanner(peer, timeout=0.14).scan(io.BytesIO(PDF), max_bytes=1024)
        elapsed = time.monotonic() - started
        assert result.status == "error"
        assert result.reason_code == "scanner_timeout"
        assert elapsed < 0.5


def test_clamav_health_and_scan_share_one_deadline_and_unknown_health_never_cleans():
    with Peer(version_delay=0.06, delay=0.06) as peer:
        started = time.monotonic()
        result = scanner(peer, timeout=0.1).scan(io.BytesIO(PDF), max_bytes=1024)
        assert result.reason_code == "scanner_timeout"
        assert time.monotonic() - started < 0.3
    with Peer(version=b"unknown-version\0") as peer:
        assert scanner(peer, max_age=None).scan(io.BytesIO(PDF), max_bytes=1024).status == "error"


def test_clamav_dns_resolution_obeys_total_deadline(monkeypatch):
    original = socket.getaddrinfo
    finished = threading.Event()

    def delayed(*args, **kwargs):
        try:
            time.sleep(0.2)
            return original(*args, **kwargs)
        finally:
            finished.set()

    monkeypatch.setattr(socket, "getaddrinfo", delayed)
    with Peer() as peer:
        started = time.monotonic()
        result = scanner(peer, timeout=0.05).scan(io.BytesIO(PDF), max_bytes=1024)
        assert result.reason_code == "scanner_timeout"
        assert time.monotonic() - started < 0.15
        assert finished.wait(1)


def test_clamav_size_limit_and_source_errors_fail_closed():
    with Peer() as peer:
        result = scanner(peer).scan(io.BytesIO(PDF), max_bytes=len(PDF) - 1)
        assert result.status == "error"
        assert result.reason_code == "scanner_size_limit"
        assert result.byte_size <= len(PDF) - 1

    class Broken(io.BytesIO):
        def read(self, _size=-1):
            raise OSError("private document path must not escape")

    with Peer() as peer:
        result = scanner(peer).scan(Broken(), max_bytes=1024)
        assert result.status == "error"
        assert result.reason_code == "scanner_unavailable"
