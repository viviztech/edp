"""Bounded ClamAV INSTREAM client; an unavailable scanner never implies clean."""

import hashlib
import queue
import re
import socket
import struct
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import BinaryIO, Literal, Protocol

_resolver_slots = threading.BoundedSemaphore(2)


@dataclass(frozen=True)
class ScanResult:
    status: Literal["clean", "infected", "error"]
    sha256: str
    byte_size: int
    reason_code: str
    engine_version: str | None = None
    signature_version: str | None = None
    signature_updated_at: datetime | None = None


class FileScanner(Protocol):
    def scan(self, source: BinaryIO, *, max_bytes: int) -> ScanResult: ...


class _Failure(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class ClamAVScanner:
    def __init__(
        self,
        host: str,
        port: int,
        *,
        timeout_seconds: float,
        max_reply_bytes: int,
        max_signature_age_seconds: int | None = None,
    ) -> None:
        if (
            not host
            or any(ord(char) < 33 for char in host)
            or not 1 <= port <= 65535
            or not 0 < timeout_seconds <= 300
            or not 32 <= max_reply_bytes <= 65536
            or (max_signature_age_seconds is not None and max_signature_age_seconds < 1)
        ):
            raise ValueError("scanner_configuration_invalid")
        self.host, self.port = host, port
        self.timeout_seconds, self.max_reply_bytes = timeout_seconds, max_reply_bytes
        self.max_signature_age_seconds = max_signature_age_seconds

    @staticmethod
    def _remaining(deadline: float) -> float:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise _Failure("scanner_timeout")
        return remaining

    def _connect(self, deadline: float) -> socket.socket:
        # getaddrinfo has no socket timeout. Bound both resolution and the number
        # of outstanding resolver threads rather than hiding an unbounded DNS wait.
        if not _resolver_slots.acquire(timeout=self._remaining(deadline)):
            raise _Failure("scanner_timeout")
        result: queue.Queue[
            list[
                tuple[
                    socket.AddressFamily,
                    socket.SocketKind,
                    int,
                    str,
                    tuple[str, int] | tuple[str, int, int, int] | tuple[int, bytes],
                ]
            ]
            | Exception
        ] = queue.Queue(maxsize=1)

        def resolve() -> None:
            try:
                result.put(socket.getaddrinfo(self.host, self.port, type=socket.SOCK_STREAM))
            except Exception as error:
                result.put(error)
            finally:
                _resolver_slots.release()

        threading.Thread(target=resolve, daemon=True).start()
        try:
            addresses = result.get(timeout=self._remaining(deadline))
        except queue.Empty:
            raise _Failure("scanner_timeout") from None
        if isinstance(addresses, Exception):
            raise _Failure("scanner_unavailable")
        for family, kind, protocol, _, address in addresses:
            connection = socket.socket(family, kind, protocol)
            try:
                connection.settimeout(self._remaining(deadline))
                connection.connect(address)
                return connection
            except TimeoutError:
                connection.close()
                raise _Failure("scanner_timeout") from None
            except OSError:
                connection.close()
            except BaseException:
                connection.close()
                raise
        raise _Failure("scanner_unavailable")

    def _send(self, connection: socket.socket, data: bytes, deadline: float) -> None:
        connection.settimeout(self._remaining(deadline))
        connection.sendall(data)

    def _reply(self, connection: socket.socket, deadline: float) -> str:
        result = bytearray()
        while True:
            connection.settimeout(self._remaining(deadline))
            chunk = connection.recv(min(4096, self.max_reply_bytes - len(result) + 1))
            if not chunk:
                break
            result.extend(chunk)
            if len(result) > self.max_reply_bytes:
                raise _Failure("scanner_reply_limit")
        if not result.endswith(b"\0") or result.count(b"\0") != 1:
            raise _Failure("scanner_reply_invalid")
        try:
            decoded = result[:-1].decode("ascii", errors="strict")
        except UnicodeError:
            raise _Failure("scanner_reply_invalid") from None
        if any(ord(char) < 32 or ord(char) > 126 for char in decoded):
            raise _Failure("scanner_reply_invalid")
        return decoded

    def _health(self, deadline: float) -> tuple[str | None, str | None, datetime | None]:
        with self._connect(deadline) as connection:
            self._send(connection, b"zVERSION\0", deadline)
            reply = self._reply(connection, deadline)
        match = re.fullmatch(
            r"ClamAV ([0-9]+\.[0-9]+\.[0-9]+(?:[-.][A-Za-z0-9]+)?)/([0-9]+)/(.+)", reply
        )
        engine, signature, updated = None, None, None
        if match:
            engine, signature = match[1], match[2]
            try:
                # clamd's VERSION date has no timezone. Deployment must run it
                # in UTC; an unparseable/unknown date is never treated as fresh.
                updated = datetime.strptime(match[3], "%a %b %d %H:%M:%S %Y").replace(tzinfo=UTC)
            except ValueError:
                pass
        if updated is None:
            raise _Failure("scanner_signature_unknown")
        if self.max_signature_age_seconds is not None:
            age = (datetime.now(UTC) - updated).total_seconds()
            if age < -300 or age > self.max_signature_age_seconds:
                raise _Failure("scanner_signatures_stale")
        return engine, signature, updated

    def scan(self, source: BinaryIO, *, max_bytes: int) -> ScanResult:
        digest = hashlib.sha256()
        size = 0
        engine, signature, updated = None, None, None
        deadline = time.monotonic() + self.timeout_seconds

        def result(status: Literal["clean", "infected", "error"], reason: str) -> ScanResult:
            return ScanResult(status, digest.hexdigest(), size, reason, engine, signature, updated)

        try:
            if max_bytes < 1:
                raise _Failure("scanner_size_limit")
            engine, signature, updated = self._health(deadline)
            with self._connect(deadline) as connection:
                self._send(connection, b"zINSTREAM\0", deadline)
                while True:
                    self._remaining(deadline)
                    chunk = source.read(min(65536, max_bytes - size + 1))
                    self._remaining(deadline)
                    if not isinstance(chunk, bytes):
                        raise _Failure("scanner_stream_invalid")
                    if not chunk:
                        break
                    if size + len(chunk) > max_bytes:
                        raise _Failure("scanner_size_limit")
                    size += len(chunk)
                    digest.update(chunk)
                    self._send(connection, struct.pack("!I", len(chunk)) + chunk, deadline)
                if size == 0:
                    raise _Failure("scanner_size_limit")
                self._send(connection, b"\x00\x00\x00\x00", deadline)
                reply = self._reply(connection, deadline)
            if reply == "stream: OK":
                return result("clean", "clean")
            if re.fullmatch(r"stream: [A-Za-z0-9_.() -]{1,200} FOUND", reply):
                return result("infected", "malware_detected")
            return result("error", "scanner_rejected")
        except _Failure as error:
            return result("error", error.code)
        except TimeoutError:
            return result("error", "scanner_timeout")
        except Exception:
            return result("error", "scanner_unavailable")
