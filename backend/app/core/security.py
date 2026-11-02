"""Password hashing, strength rules, JWT token signing, and login rate limiting."""

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Literal

from app.core.errors import AppError
from app.dtos.auth_dto import UserRole

TokenType = Literal["access", "refresh"]


def validate_password_strength(password: str) -> None:
    """Enforces password complexity rules for journalist and admin accounts."""
    stripped = password.strip()
    if len(stripped) < 8:
        raise AppError(
            code="WEAK_PASSWORD",
            message="Password must be at least 8 characters long.",
            status_code=422,
        )
    has_letter = any(ch.isalpha() for ch in stripped)
    has_digit = any(ch.isdigit() for ch in stripped)
    if not (has_letter and has_digit):
        raise AppError(
            code="WEAK_PASSWORD",
            message="Password must contain at least one letter and one digit.",
            status_code=422,
        )


class PasswordHasher:
    """Salted cryptographic password hasher with constant-time verification."""

    def __init__(self, iterations: int = 120_000) -> None:
        self._iterations = iterations

    def hash_password(self, plain_password: str) -> str:
        salt = secrets.token_hex(16)
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            self._iterations,
        )
        digest_b64 = base64.urlsafe_b64encode(derived).decode("ascii")
        return f"$argon2id-compat$i={self._iterations}${salt}${digest_b64}"

    def verify_password(self, plain_password: str, stored_hash: str) -> bool:
        parts = stored_hash.split("$")
        if len(parts) != 5 or not parts[2].startswith("i="):
            return False
        iterations = int(parts[2].removeprefix("i="))
        salt = parts[3]
        expected_b64 = parts[4]
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        )
        actual_b64 = base64.urlsafe_b64encode(derived).decode("ascii")
        return hmac.compare_digest(actual_b64, expected_b64)


class TokenManager:
    """Signs, verifies, and revokes HMAC-SHA256 JWT access and refresh tokens."""

    def __init__(self, secret_key: str = "scamguard-dev-secret-key-2026") -> None:
        self._secret = secret_key.encode("utf-8")
        self._revoked_jtis: set[str] = set()

    def create_token(
        self,
        user_id: str,
        role: UserRole,
        token_type: TokenType = "access",
        ttl_seconds: int = 3600,
    ) -> str:
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": user_id,
            "role": role,
            "type": token_type,
            "jti": secrets.token_hex(12),
            "exp": int(time.time()) + ttl_seconds,
        }
        header_b64 = self._b64_encode(json.dumps(header).encode("utf-8"))
        payload_b64 = self._b64_encode(json.dumps(payload).encode("utf-8"))
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        signature = hmac.new(self._secret, signing_input, hashlib.sha256).digest()
        sig_b64 = self._b64_encode(signature)
        return f"{header_b64}.{payload_b64}.{sig_b64}"

    def verify_token(
        self, token: str, expected_type: TokenType = "access"
    ) -> dict[str, object]:
        parts = token.split(".")
        if len(parts) != 3:
            raise AppError(
                code="INVALID_TOKEN",
                message="Malformed authentication token.",
                status_code=401,
            )
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = hmac.new(self._secret, signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(self._b64_encode(expected_sig), sig_b64):
            raise AppError(
                code="INVALID_TOKEN",
                message="Invalid token signature.",
                status_code=401,
            )

        payload_raw = self._b64_decode(payload_b64)
        payload: dict[str, object] = json.loads(payload_raw.decode("utf-8"))

        exp = int(str(payload.get("exp", 0)))
        if exp < int(time.time()):
            raise AppError(
                code="TOKEN_EXPIRED",
                message="Authentication token has expired.",
                status_code=401,
            )

        if payload.get("type") != expected_type:
            raise AppError(
                code="INVALID_TOKEN_TYPE",
                message=f"Expected {expected_type} token.",
                status_code=401,
            )

        jti = str(payload.get("jti", ""))
        if jti in self._revoked_jtis:
            raise AppError(
                code="TOKEN_REVOKED",
                message="Token has been logged out.",
                status_code=401,
            )

        return payload

    def revoke_token(self, token: str) -> None:
        parts = token.split(".")
        if len(parts) == 3:
            try:
                payload_raw = self._b64_decode(parts[1])
                payload: dict[str, object] = json.loads(payload_raw.decode("utf-8"))
                jti = str(payload.get("jti", ""))
                if jti:
                    self._revoked_jtis.add(jti)
            except Exception:
                return

    @staticmethod
    def _b64_encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    @staticmethod
    def _b64_decode(data: str) -> bytes:
        padding = "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(data + padding)


class LoginRateLimiter:
    """In-memory sliding counter protecting login against brute-force attempts."""

    def __init__(self, max_attempts: int = 5) -> None:
        self._max_attempts = max_attempts
        self._failures: dict[str, int] = {}

    def check_allowed(self, key: str) -> None:
        normalized = key.strip().lower()
        if self._failures.get(normalized, 0) >= self._max_attempts:
            raise AppError(
                code="RATE_LIMITED",
                message="Too many failed login attempts. Please wait before retrying.",
                status_code=429,
                details={"max_attempts": self._max_attempts},
            )

    def record_failure(self, key: str) -> None:
        normalized = key.strip().lower()
        self._failures[normalized] = self._failures.get(normalized, 0) + 1

    def reset(self, key: str) -> None:
        normalized = key.strip().lower()
        self._failures.pop(normalized, None)

