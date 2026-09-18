import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def token() -> str:
    return secrets.token_urlsafe(32)


def verify_password(encoded: str, supplied: str) -> bool:
    try:
        return hasher.verify(encoded, supplied)
    except (VerificationError, InvalidHashError):
        return False


class AuthError(Exception):
    def __init__(self, code: str, status: int = 401) -> None:
        self.code = code
        self.status = status
