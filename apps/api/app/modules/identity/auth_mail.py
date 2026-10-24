"""Approved-edition authentication mail and a bounded verified-TLS SMTP adapter.

SMTP acceptance is not recipient delivery. No protocol debug output is enabled.
"""

import queue
import re
import smtplib
import socket
import ssl
import threading
import time
from collections.abc import Buffer, Callable
from dataclasses import dataclass
from email.message import EmailMessage
from email.policy import SMTP
from typing import Literal, Protocol
from urllib.parse import urlsplit

from app.core.config import Settings

EDITION = "auth-v1"


def smtp_configured(settings: Settings) -> bool:
    return bool(
        settings.auth_delivery_backend == "smtp"
        and settings.auth_smtp_enabled
        and settings.auth_templates_approved
        and settings.auth_delivery_key
        and settings.auth_delivery_retention_days is not None
        and settings.auth_canonical_origin
        and settings.auth_smtp_host
        and settings.auth_smtp_tls_mode
        and settings.auth_smtp_username
        and settings.auth_smtp_password
        and settings.auth_smtp_from_address
    )


@dataclass(frozen=True)
class Mail:
    sender: str
    recipient: str
    content: bytes


@dataclass(frozen=True)
class MailResult:
    outcome: Literal["accepted", "transient", "permanent", "ambiguous"]
    code: str


class MailProvider(Protocol):
    def send(self, message: Mail) -> MailResult: ...


def render_mail(
    settings: Settings,
    *,
    recipient: str,
    secret: str,
    purpose: str,
    locale: str,
    message_id: str,
    edition: str,
) -> Mail:
    if (
        edition != EDITION
        or purpose not in {"verify", "reset"}
        or locale not in {"en", "ta"}
        or not settings.auth_canonical_origin
        or not settings.auth_smtp_from_address
        or not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", secret)
        or not recipient.isascii()
        or any(ord(char) <= 32 or ord(char) == 127 for char in recipient)
        or not re.fullmatch(r"[^@<>]+@[^@<>]+", recipient)
        or not re.fullmatch(r"<auth-[0-9a-f-]{36}@[A-Za-z0-9.-]+>", message_id)
    ):
        raise ValueError("Invalid authentication message")
    action_url = f"{settings.auth_canonical_origin.rstrip('/')}/{locale}/account/{purpose}"
    if locale == "ta":
        subject = "EDP கணக்கை உறுதிப்படுத்தவும்" if purpose == "verify" else "EDP கடவுச்சொல்லை மீட்டமைக்கவும்"
        instruction = "இந்தப் பக்கத்தைத் திறந்து, கீழே உள்ள ரகசியக் குறியீட்டை உள்ளிடவும்."
        closing = (
            "குறியீடு 30 நிமிடங்களில் காலாவதியாகும். இதைப் பகிர வேண்டாம். நீங்கள் கோரவில்லை என்றால் புறக்கணிக்கவும்."
        )
    else:
        subject = "Verify your EDP account" if purpose == "verify" else "Reset your EDP password"
        instruction = "Open this page and enter the secret code below."
        closing = (
            "The code expires in 30 minutes. Do not share it. "
            "Ignore this email if you did not request it."
        )
    message = EmailMessage(policy=SMTP)
    message["From"] = settings.auth_smtp_from_address
    message["To"] = recipient
    message["Subject"] = subject
    message["Message-ID"] = message_id
    # Plain text avoids HTML/link injection and action URLs never contain the secret.
    message.set_content(
        f"{instruction}\n\n{action_url}\n\n{secret}\n\n{closing}\n", cte="quoted-printable"
    )
    content = message.as_bytes()
    if len(content) > settings.auth_smtp_max_message_bytes:
        raise ValueError("Authentication message exceeds byte limit")
    return Mail(settings.auth_smtp_from_address, recipient, content)


class _Deadline:
    def __init__(self, total: float, stage: float) -> None:
        self.until = time.monotonic() + total
        self.stage = stage

    def remaining(self) -> float:
        remaining = self.until - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("SMTP deadline")
        return min(self.stage, remaining)


def _connect(host: str, port: int, deadline: _Deadline) -> socket.socket:
    # DNS is bounded too. A resolver that stalls cannot hold the delivery worker.
    resolved: queue.Queue[object] = queue.Queue(maxsize=1)

    def resolve() -> None:
        try:
            resolved.put(socket.getaddrinfo(host, port, type=socket.SOCK_STREAM))
        except OSError:
            resolved.put(None)

    threading.Thread(target=resolve, daemon=True).start()
    try:
        addresses = resolved.get(timeout=deadline.remaining())
    except queue.Empty:
        raise TimeoutError("SMTP resolution deadline") from None
    if not isinstance(addresses, list):
        raise OSError("SMTP resolution failed")
    for family, socktype, proto, _, address in addresses[:4]:
        connection = socket.socket(family, socktype, proto)
        try:
            connection.settimeout(deadline.remaining())
            connection.connect(address)
            return connection
        except OSError:
            connection.close()
    raise OSError("SMTP connection failed")


class _BoundedSMTP(smtplib.SMTP):
    _host: str = ""

    def __init__(self, deadline: _Deadline) -> None:
        self.deadline = deadline
        super().__init__(timeout=deadline.remaining(), local_hostname="edp.invalid")

    def _get_socket(self, host: str, port: int, timeout: float) -> socket.socket:
        return _connect(host, port, self.deadline)

    def send(self, s: Buffer | str) -> None:
        if self.sock is not None:
            self.sock.settimeout(self.deadline.remaining())
        super().send(s)

    def getreply(self) -> tuple[int, bytes]:
        # Read with a fresh remaining deadline for every receive, including slow
        # multiline replies. smtplib's buffered readline alone has no total bound.
        lines: list[bytes] = []
        total = 0
        response_code: int | None = None
        for _ in range(20):
            line = bytearray()
            while not line.endswith(b"\n"):
                if self.sock is None:
                    raise smtplib.SMTPServerDisconnected("SMTP disconnected")
                self.sock.settimeout(self.deadline.remaining())
                byte = self.sock.recv(1)
                if not byte:
                    raise smtplib.SMTPServerDisconnected("SMTP disconnected")
                line.extend(byte)
                total += 1
                if len(line) > 1000 or total > 8192:
                    raise smtplib.SMTPServerDisconnected("SMTP reply limit")
            if (
                len(line) < 6
                or not bytes(line[:3]).isdigit()
                or bytes(line[3:4]) not in {b" ", b"-"}
                or not line.endswith(b"\r\n")
            ):
                raise smtplib.SMTPServerDisconnected("Invalid SMTP reply")
            code = int(line[:3])
            if response_code is not None and code != response_code:
                raise smtplib.SMTPServerDisconnected("Inconsistent SMTP reply")
            response_code = code
            lines.append(bytes(line[4:]).strip())
            if line[3:4] != b"-":
                return code, b"\n".join(lines)
        raise smtplib.SMTPServerDisconnected("SMTP reply limit")


class _ImplicitSMTP(_BoundedSMTP):
    def __init__(self, deadline: _Deadline, context: ssl.SSLContext) -> None:
        self.context = context
        super().__init__(deadline)

    def _get_socket(self, host: str, port: int, timeout: float) -> socket.socket:
        raw = super()._get_socket(host, port, timeout)
        try:
            raw.settimeout(self.deadline.remaining())
            return self.context.wrap_socket(raw, server_hostname=host)
        except Exception:
            raw.close()
            raise


class SMTPProvider:
    def __init__(
        self,
        settings: Settings,
        context_factory: Callable[[], ssl.SSLContext] = ssl.create_default_context,
    ) -> None:
        self.settings = settings
        self.context_factory = context_factory

    def send(self, message: Mail) -> MailResult:
        policy = self.settings
        if not smtp_configured(policy):
            return MailResult("permanent", "configuration_unavailable")
        if len(message.content) > policy.auth_smtp_max_message_bytes:
            return MailResult("permanent", "message_invalid")
        context = self.context_factory()
        if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
            return MailResult("permanent", "tls_unverified")
        deadline = _Deadline(
            policy.auth_smtp_total_timeout_seconds, policy.auth_smtp_stage_timeout_seconds
        )
        client: _BoundedSMTP | None = None
        data_started = False
        accepted = False
        try:
            client = (
                _ImplicitSMTP(deadline, context)
                if policy.auth_smtp_tls_mode == "implicit"
                else _BoundedSMTP(deadline)
            )
            assert policy.auth_smtp_host and policy.auth_smtp_username and policy.auth_smtp_password
            client._host = policy.auth_smtp_host
            code, _ = client.connect(policy.auth_smtp_host, policy.auth_smtp_port)
            if code != 220:
                raise smtplib.SMTPResponseException(code, b"Greeting rejected")
            client.ehlo_or_helo_if_needed()
            if policy.auth_smtp_tls_mode == "starttls":
                client.starttls(context=context)
                client.ehlo()
            client.login(
                policy.auth_smtp_username.get_secret_value(),
                policy.auth_smtp_password.get_secret_value(),
            )
            for command, argument in (
                (client.mail, message.sender),
                (client.rcpt, message.recipient),
            ):
                code, _ = command(argument)
                if code not in {250, 251}:
                    raise smtplib.SMTPResponseException(code, b"Envelope rejected")
            code, _ = client.docmd("DATA")
            if code != 354:
                raise smtplib.SMTPResponseException(code, b"DATA rejected")
            data_started = True
            # smtplib's sendmail combines body write and acknowledgement; keeping
            # these stages explicit makes the uncertain boundary reviewable.
            body = re.sub(rb"(?m)^\.", b"..", message.content)
            if not body.endswith(b"\r\n"):
                body += b"\r\n"
            client.send(body + b".\r\n")
            code, _ = client.getreply()
            if code != 250:
                if 400 <= code <= 599:
                    raise smtplib.SMTPResponseException(code, b"Message rejected")
                return MailResult("ambiguous", "acknowledgement_unknown")
            accepted = True
            return MailResult("accepted", "smtp_250")
        except smtplib.SMTPResponseException as error:
            return MailResult(
                "transient" if 400 <= error.smtp_code <= 499 else "permanent",
                "provider_temporary" if 400 <= error.smtp_code <= 499 else "provider_rejected",
            )
        except ssl.SSLError:
            return (
                MailResult("ambiguous", "acknowledgement_unknown")
                if data_started
                else MailResult("permanent", "tls_unverified")
            )
        except (OSError, smtplib.SMTPException, ValueError):
            if data_started:
                return MailResult("ambiguous", "acknowledgement_unknown")
            return MailResult("transient", "connection_failed")
        finally:
            if client is not None:
                # Once DATA was accepted, QUIT failure cannot revoke acceptance.
                try:
                    if accepted:
                        client.quit()
                except (OSError, smtplib.SMTPException):
                    pass
                finally:
                    try:
                        client.close()
                    except OSError:
                        pass


def message_identity(identity: str, settings: Settings) -> str:
    host = urlsplit(settings.auth_canonical_origin or "https://development.invalid").hostname
    return f"<auth-{identity}@{host}>"
