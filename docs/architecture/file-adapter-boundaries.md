# Private file adapter boundaries

Recorded: 2026-10-23. These adapters are shared-file foundations, not authorization endpoints or evidence that a production provider has been activated. The files service owns organization, actor, purpose, lifecycle, lease, retention and domain checks.

## Storage contract

`PrivateStorage.put(key, source, media_type, byte_size, sha256)` returns a frozen `StoredObject` containing the opaque key, immutable version, media type, byte count and SHA-256. `open(ref)` provides a context-managed verified binary stream; `delete(ref)` targets that version and tolerates an already absent version. `recover(key, media_type, byte_size, sha256)` discovers an object left by a lost completion response and returns a reference only after fully verifying its bytes. Only a confirmed missing object returns `None`; denial, corruption, incomplete bytes and unknown failures remain errors.

Keys have the fixed server-generated shape `quarantine/{organization_uuid}/{object_uuid4}`. The adapters never accept original filenames or arbitrary server URLs as object keys. Input bytes are bounded and checked against exact size/hash and declared PDF, JPEG, PNG or WebP signatures. Plain text requires complete valid UTF-8 without prohibited control characters. These signature checks complement the service's stronger format validation and malware scan; they are not a claim that a file is harmless.

Both constructors accept `temp_root`. When configured, every verification spool uses that existing absolute directory; missing, relative, symlink and Windows reparse paths are rejected. No temporary directory is silently provisioned. Production wiring must supply a dedicated private directory with operator-reviewed permissions, capacity, encryption and disposal. Ambient temporary storage is limited to explicit local/test construction.

### Local adapter

`LocalPrivateStorage(root, max_bytes=..., temp_root=...)` uses exclusive creation and never overwrites an object. Repeating a completed write with identical verified content returns the existing version. POSIX traversal uses anchored directory descriptors and no-follow opens; cooperating object operations use file locks. Windows opens every ancestor without following reparse points, keeps directory handles against rename, and denies write/delete sharing on opened objects. Exact-version deletion uses the opened Windows handle. Hard links and nonregular files are rejected.

The local version is an opaque digest of file identity, creation/change metadata, size and content hash. Reads verify bytes into a separate spool before exposing them. Failed owned writes clean up their partial file. A process-killed partial or corrupted object is never adopted as verified or silently overwritten; controlled recovery/disposal is required. The configured root must be writable only by the application/operator boundary. This adapter does not defend against a privileged administrator controlling the process or filesystem.

This workstation's sandbox denies directory handles on the user-profile temporary ancestry. Run adapter tests with `--basetemp=.tool-cache/pytest-file-adapters`; the implementation does not weaken confinement to work around that restriction. POSIX behavior also requires Linux acceptance before deployment.

### S3 adapter

`S3PrivateStorage(client, bucket=..., max_bytes=..., server_side_encryption=..., kms_key_id=..., temp_root=...)` uses an injected SDK client. Each operation requires enabled bucket versioning and all four public-access blocks. Uploads use conditional creation, exact content length, SHA-256 and explicit server-side encryption. Reads/deletes pin `VersionId`; responses and bytes must match the reference. A conditional-create conflict is recovered only through a verified existing version. These operations follow the documented [PutObject](https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/put_object.html) and [GetObject](https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/get_object.html) interfaces.

AES256 and AWS KMS are supported. KMS requires a configured canonical key ARN matching the returned identity; aliases are not silently equated with a different returned key. Unsupported compatibility APIs, missing version/checksum/encryption evidence and provider failures fail closed. Provider diagnostics, credentials, bucket names and object keys are not included in adapter exceptions. Live endpoint compatibility, IAM, private access, encryption, lifecycle and backup behavior remain deployment acceptance work. Tests use botocore Stubber and make no provider calls.

## Scanner contract

`FileScanner.scan(source, max_bytes=...)` returns `ScanResult(status, sha256, byte_size, reason_code, ...)`. The service must bind the returned size/hash to the exact stored version and current scan lease before changing lifecycle state. Sources are verified bounded storage streams, not unbounded request or remote-URL bodies.

`ClamAVScanner` checks daemon version/signature information and sends only INSTREAM bytes, using four-byte network-order chunk lengths. It never sends paths. Replies must be bounded, complete, single NUL-terminated ASCII records. Only the exact clean response is accepted; detection, unknown/error/truncated/oversized replies and source failures cannot become clean. One monotonic deadline covers bounded DNS resolution, connection attempts, health, sending and reading. This follows the [ClamD protocol](https://docs.clamav.net/manual/Usage/ClamdProtocol.html).

Unknown signature information fails closed. When a maximum signature age is configured, stale/future timestamps also fail. The daemon must run with UTC because its version-date record lacks a timezone. Production must configure the maximum age and maintain signatures. TCP clamd traffic is unauthenticated and must remain on a private trusted network, as specified in the [ClamAV scanning guidance](https://docs.clamav.net/manual/Usage/Scanning.html). Daemon stream/scan limits, archive limits and detection-on-limit policy need operational acceptance. Unit tests use a loopback fake peer solely to exercise framing and failures; there is no runtime fake-clean mode.
