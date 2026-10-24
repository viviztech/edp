import ipaddress
import socket
import ssl
import threading
import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from email import policy as email_policy
from email.parser import BytesParser
from uuid import uuid4

import pytest
from cryptography import x509
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from pydantic import ValidationError

from app.core.config import Settings
from app.modules.identity.auth_mail import (
    EDITION,
    SMTPProvider,
    message_identity,
    render_mail,
    smtp_configured,
)


def smtp_policy(**changes):
    values = dict(
        _env_file=None,
        app_env="test",
        database_url="postgresql+psycopg://localhost/unused",
        redis_url="redis://localhost:6379/15",
        auth_delivery_key=Fernet.generate_key().decode(),
        auth_delivery_backend="smtp",
        auth_smtp_enabled=True,
        auth_templates_approved=True,
        auth_canonical_origin="https://edp.example.test",
        auth_smtp_host="127.0.0.1",
        auth_smtp_port=465,
        auth_smtp_tls_mode="implicit",
        auth_smtp_username="synthetic-user",
        auth_smtp_password="synthetic-password",
        auth_smtp_from_address="edp@example.test",
        auth_delivery_retention_days=2,
    )
    values.update(changes)
    return Settings(**values)


def message(settings, locale="en", purpose="verify"):
    return render_mail(
        settings,
        recipient="learner@example.test",
        secret="x" * 43,
        purpose=purpose,
        locale=locale,
        message_id=message_identity(str(uuid4()), settings),
        edition=EDITION,
    )


@pytest.fixture(scope="module")
def tls_contexts(tmp_path_factory):
    directory = tmp_path_factory.mktemp("synthetic-smtp-tls")
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC) - timedelta(minutes=1))
        .not_valid_after(datetime.now(UTC) + timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    cert_path, key_path = directory / "cert.pem", directory / "key.pem"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    server = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server.load_cert_chain(cert_path, key_path)

    def client():
        return ssl.create_default_context(cafile=str(cert_path))

    return server, client


@contextmanager
def peer(contexts, *, mode="implicit", mail_code=250, final="accepted", quit_drop=False):
    server_context, client_context = contexts
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    listener.settimeout(3)
    state = {"commands": [], "messages": [], "tls_auth": []}

    def serve():
        connection = None
        reader = None
        try:
            connection, _ = listener.accept()
            connection.settimeout(3)
            tls = mode == "implicit"
            if tls:
                connection = server_context.wrap_socket(connection, server_side=True)
            reader = connection.makefile("rb")
            connection.sendall(b"220 synthetic SMTP\r\n")
            while True:
                line = reader.readline(65537)
                if not line:
                    return
                verb = line.split(b" ", 1)[0].strip().decode().upper()
                state["commands"].append(verb)
                if verb in {"EHLO", "HELO"}:
                    connection.sendall(b"250-synthetic\r\n250-STARTTLS\r\n250 AUTH PLAIN\r\n")
                elif verb == "STARTTLS":
                    connection.sendall(b"220 TLS ready\r\n")
                    reader.close()
                    connection = server_context.wrap_socket(connection, server_side=True)
                    reader = connection.makefile("rb")
                    tls = True
                elif verb == "AUTH":
                    state["tls_auth"].append(tls)
                    connection.sendall(b"235 authenticated\r\n")
                elif verb == "MAIL":
                    connection.sendall(f"{mail_code} synthetic envelope result\r\n".encode())
                    if mail_code != 250:
                        return
                elif verb == "RCPT":
                    connection.sendall(b"250 recipient accepted\r\n")
                elif verb == "DATA":
                    connection.sendall(b"354 content\r\n")
                    body = bytearray()
                    while (chunk := reader.readline(65537)) != b".\r\n":
                        if not chunk:
                            return
                        body.extend(chunk)
                    state["messages"].append(bytes(body))
                    if final == "drop":
                        return
                    if final == "slow":
                        time.sleep(1.3)
                    if final == "malformed":
                        connection.sendall(b"250-first line\r\n550 inconsistent reply\r\n")
                    elif final == "temporary":
                        connection.sendall(b"451 rejected temporarily\r\n")
                    else:
                        connection.sendall(b"250 accepted\r\n")
                elif verb == "QUIT":
                    if not quit_drop:
                        connection.sendall(b"221 goodbye\r\n")
                    return
                else:
                    connection.sendall(b"500 unsupported\r\n")
        except (OSError, ssl.SSLError):
            pass
        finally:
            if reader:
                reader.close()
            if connection:
                connection.close()

    worker = threading.Thread(target=serve, daemon=True)
    worker.start()
    try:
        yield listener.getsockname()[1], client_context, state
    finally:
        listener.close()
        worker.join(timeout=4)
        assert not worker.is_alive()


@pytest.mark.parametrize("mode", ["implicit", "starttls"])
def test_verified_tls_acceptance_survives_quit_disconnect(tls_contexts, mode):
    with peer(tls_contexts, mode=mode, quit_drop=True) as (port, context, state):
        settings = smtp_policy(auth_smtp_port=port, auth_smtp_tls_mode=mode)
        mail = message(settings, "ta", "reset")
        result = SMTPProvider(settings, context).send(mail)
        assert result.outcome == "accepted" and result.code == "smtp_250"
        assert state["tls_auth"] == [True] and len(state["messages"]) == 1
        parsed = BytesParser(policy=email_policy.default).parsebytes(state["messages"][0])
        assert parsed["Message-ID"] and "/ta/account/reset" in parsed.get_content()
        assert "x" * 43 in parsed.get_content()


@pytest.mark.parametrize("code,outcome", [(450, "transient"), (550, "permanent")])
def test_mail_rejection_stops_before_rcpt_even_when_peer_closes(tls_contexts, code, outcome):
    with peer(tls_contexts, mail_code=code) as (port, context, state):
        settings = smtp_policy(auth_smtp_port=port)
        assert SMTPProvider(settings, context).send(message(settings)).outcome == outcome
        assert "MAIL" in state["commands"]
        assert "RCPT" not in state["commands"] and "DATA" not in state["commands"]
        assert state["messages"] == []


@pytest.mark.parametrize(
    "final,outcome", [("drop", "ambiguous"), ("malformed", "ambiguous"), ("temporary", "transient")]
)
def test_post_data_unknown_and_definite_rejection_differ(tls_contexts, final, outcome):
    with peer(tls_contexts, final=final) as (port, context, state):
        settings = smtp_policy(auth_smtp_port=port)
        result = SMTPProvider(settings, context).send(message(settings))
        assert result.outcome == outcome
        assert len(state["messages"]) == 1


def test_total_deadline_bounds_acknowledgement_wait(tls_contexts):
    with peer(tls_contexts, final="slow") as (port, context, _):
        settings = smtp_policy(
            auth_smtp_port=port,
            auth_smtp_total_timeout_seconds=1,
            auth_smtp_stage_timeout_seconds=2,
        )
        started = time.monotonic()
        result = SMTPProvider(settings, context).send(message(settings))
        assert result.outcome == "ambiguous"
        assert time.monotonic() - started < 1.8


def test_untrusted_tls_peer_never_receives_authentication(tls_contexts):
    with peer(tls_contexts) as (port, _, state):
        settings = smtp_policy(auth_smtp_port=port)
        assert SMTPProvider(settings).send(message(settings)).code == "tls_unverified"
        assert not state["commands"] and not state["messages"]


@pytest.mark.parametrize(
    "locale,purpose", [("en", "verify"), ("en", "reset"), ("ta", "verify"), ("ta", "reset")]
)
def test_templates_use_token_free_action_url_and_fixed_edition(locale, purpose):
    settings = smtp_policy()
    mail = message(settings, locale, purpose)
    assert all(byte < 128 for byte in mail.content)  # No undeclared 8BITMIME requirement.
    parsed = BytesParser(policy=email_policy.default).parsebytes(mail.content)
    body = parsed.get_content()
    assert f"https://edp.example.test/{locale}/account/{purpose}" in body
    assert not any("x" * 43 in line for line in body.splitlines() if line.startswith("https:"))
    assert parsed["Bcc"] is None and len(parsed.get_all("To")) == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("auth_canonical_origin", "https://example.test/path"),
        ("auth_canonical_origin", "https://user@example.test"),
        ("auth_canonical_origin", "https://example.test?token=x"),
        ("auth_canonical_origin", "http://example.test"),
        ("auth_smtp_host", "smtp://example.test"),
        ("auth_smtp_from_address", "edp@example.test\r\nBcc: victim@example.test"),
    ],
)
def test_configuration_rejects_unsafe_addresses_and_origins(field, value):
    with pytest.raises(ValidationError):
        smtp_policy(**{field: value})


def test_disabled_or_incomplete_provider_cannot_claim_real_capability():
    assert smtp_configured(smtp_policy())
    for changes in (
        {"auth_templates_approved": False},
        {"auth_smtp_enabled": False},
        {"auth_delivery_retention_days": None},
        {"auth_smtp_tls_mode": None},
    ):
        settings = smtp_policy(**changes)
        assert not smtp_configured(settings)
        assert SMTPProvider(settings).send(message(settings)).code == "configuration_unavailable"
    with pytest.raises(ValidationError):
        smtp_policy(app_env="production", auth_canonical_origin="http://localhost")
