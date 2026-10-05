"""Password hashing — pure, no FastAPI or SQLite dependency."""
from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

_hasher = PasswordHasher()

# A real argon2 hash of an unknowable password, used so that checking a
# nonexistent email takes the same time as checking a wrong password —
# neither branch can be timed to reveal whether the account exists.
_DUMMY_HASH = _hasher.hash("not-a-real-account-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def waste_time_like_a_verify(password: str) -> None:
    """Run a verify against a dummy hash, for constant-time-ish failure paths."""
    verify_password(_DUMMY_HASH, password)
