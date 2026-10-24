"""Seal Git-selected source and scan it with the verified cached Gitleaks release."""

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from uuid import uuid4

ARCHIVE_NAME = "gitleaks_8.24.3_windows_x64.zip"
ARCHIVE_SHA256 = "3f1a35578631dbfe633cc5b49e6c906e55ff14a4bfd7336a10fb27fe33b6dcd2"
EXCLUDED_PARTS = {".git", ".local", ".tool-cache", "node_modules", ".venv", ".aws"}
MAX_TOOL_BYTES = 64 * 1024 * 1024


class SealError(Exception):
    """A fixed error category safe to show without source or secret values."""


def label_argument(value: str) -> str:
    if len(value) > 48 or re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value) is None:
        raise argparse.ArgumentTypeError("label must be a lowercase slug of 1-48 characters")
    if value == "process3":
        raise argparse.ArgumentTypeError("the historical process3 evidence label is reserved")
    return value


def confined(path: Path, root: Path) -> None:
    if not path.resolve().is_relative_to(root):
        raise SealError("path_outside_workspace")
    for item in (path, *path.parents):
        if item == root:
            break
        if item.exists() or item.is_symlink():
            attributes = item.lstat()
            if stat.S_ISLNK(attributes.st_mode) or (
                getattr(attributes, "st_file_attributes", 0)
                & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
            ):
                raise SealError("linked_path_rejected")


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def verified_scanner(root: Path) -> tuple[Path, str]:
    cache = root / ".tool-cache/gitleaks-8.24.3"
    checksums = cache / "gitleaks_8.24.3_checksums.txt"
    archive = cache / ARCHIVE_NAME
    executable = cache / "verified/gitleaks.exe"
    for path in (checksums, archive, executable):
        confined(path, root)
        if not path.is_file() or path.stat().st_size > MAX_TOOL_BYTES:
            raise SealError("scanner_artifact_unavailable")
    entries = [
        line.split()
        for line in checksums.read_text(encoding="utf-8").splitlines()
        if line.split() and line.split()[-1] == ARCHIVE_NAME
    ]
    if len(entries) != 1 or entries[0] != [ARCHIVE_SHA256, ARCHIVE_NAME]:
        raise SealError("scanner_checksum_record_mismatch")
    if file_digest(archive) != ARCHIVE_SHA256:
        raise SealError("scanner_archive_checksum_mismatch")
    with zipfile.ZipFile(archive) as bundle:
        candidates = [item for item in bundle.infolist() if item.filename == "gitleaks.exe"]
        if len(candidates) != 1 or candidates[0].file_size > MAX_TOOL_BYTES:
            raise SealError("scanner_archive_entry_invalid")
        expected = hashlib.sha256(bundle.read(candidates[0])).hexdigest()
    actual = file_digest(executable)
    if actual != expected:
        raise SealError("scanner_executable_checksum_mismatch")
    return executable, actual


def git_output(root: Path, *arguments: str) -> bytes:
    result = subprocess.run(["git", *arguments], cwd=root, capture_output=True, check=False)
    if result.returncode:
        raise SealError("git_source_selection_failed")
    return result.stdout


def selected_paths(root: Path) -> list[str]:
    top = git_output(root, "rev-parse", "--show-toplevel").decode("utf-8").strip()
    if Path(top).resolve() != root:
        raise SealError("repository_root_mismatch")
    return sorted(
        set(
            name
            for name in git_output(
                root, "ls-files", "--cached", "--others", "--exclude-standard", "-z"
            )
            .decode("utf-8")
            .split("\0")
            if name
        )
    )


def source_path(root: Path, name: str) -> Path:
    relative = PurePosixPath(name)
    windows = PureWindowsPath(name)
    if (
        relative.is_absolute()
        or windows.drive
        or windows.root
        or ".." in relative.parts
        or "\\" in name
        or ":" in name
        or any(ord(character) < 32 or ord(character) == 127 for character in name)
        or EXCLUDED_PARTS.intersection(part.casefold() for part in relative.parts)
    ):
        raise SealError("selected_source_path_rejected")
    basename = relative.name.casefold()
    if (
        (basename == ".env" or basename.startswith(".env."))
        and basename != ".env.example"
        or basename.endswith((".pem", ".key", ".dump", ".sql.gz"))
        or "service-account" in basename
        and basename.endswith(".json")
        or basename in {"google-services.json", "googleservice-info.plist"}
    ):
        raise SealError("selected_secret_artifact_rejected")
    original = root.joinpath(*relative.parts)
    confined(original, root)
    return original


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True, type=label_argument)
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    record = {"label": arguments.label, "status": "failed"}
    snapshot = None
    try:
        executable, tool_hash = verified_scanner(root)
        paths = selected_paths(root)
        local = root / ".local"
        confined(local, root)
        local.mkdir(exist_ok=True)
        snapshot = local / f"source-{arguments.label}-{uuid4().hex}"
        snapshot.mkdir()
        source = snapshot / "source"
        source.mkdir()
        record.update(
            snapshot=snapshot.relative_to(root).as_posix(),
            source_revision=git_output(root, "rev-parse", "HEAD").decode("ascii").strip(),
            scanner_sha256=tool_hash,
        )
        manifest = []
        deleted = []
        for name in paths:
            original = source_path(root, name)
            if not original.exists():
                deleted.append(name)
                continue
            before = original.stat()
            if not stat.S_ISREG(before.st_mode):
                raise SealError("nonregular_source_rejected")
            content = original.read_bytes()
            confined(original, root)
            after = original.stat()
            if (before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_ino,
                after.st_size,
                after.st_mtime_ns,
            ):
                raise SealError("source_changed_during_copy")
            destination = source / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            manifest.append(
                {
                    "path": name,
                    "bytes": len(content),
                    "sha256": hashlib.sha256(content).hexdigest(),
                }
            )
        manifest_path = snapshot / "manifest.json"
        write_json(manifest_path, {"files": manifest, "deleted_paths": deleted})
        record.update(
            file_count=len(manifest),
            deleted_file_count=len(deleted),
            manifest_sha256=file_digest(manifest_path),
        )
        report = snapshot / "gitleaks.json"
        scan_command = [
            str(executable),
            "dir",
            str(source),
            "--redact=100",
            "--no-banner",
            "--max-target-megabytes",
            "0",
            "--exit-code",
            "1",
            "--report-format",
            "json",
            "--report-path",
            str(report),
        ]
        if (source / ".gitleaks.toml").is_file():
            scan_command.extend(["--config", str(source / ".gitleaks.toml")])
        scan_environment = {
            key: value
            for key, value in os.environ.items()
            if key.upper() not in {"GITLEAKS_CONFIG", "GITLEAKS_CONFIG_TOML"}
        }
        result = subprocess.run(
            scan_command,
            cwd=source,
            env=scan_environment,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
        (snapshot / "gitleaks.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        record["scanner_exit_code"] = result.returncode
        findings = json.loads(report.read_text(encoding="utf-8")) if report.is_file() else None
        if not isinstance(findings, list):
            raise SealError("scanner_report_invalid")
        record["findings"] = len(findings)
        if result.returncode or findings:
            raise SealError("source_scan_failed")
        record["status"] = "passed"
    except Exception as error:
        record["error"] = str(error) if isinstance(error, SealError) else type(error).__name__
    if snapshot is not None:
        write_json(snapshot / "result.json", record)
        write_json(root / ".local" / f"{arguments.label}-latest-source-scan.json", record)
    print(json.dumps(record, sort_keys=True))
    return 0 if record["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
