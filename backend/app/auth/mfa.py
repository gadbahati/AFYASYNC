"""TOTP MFA for privileged Government Portal identities."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from urllib.parse import quote

from app.auth.security import decrypt_mfa_secret, encrypt_mfa_secret

_STEP = 30
_DIGITS = 6


def generate_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _counter(secret: str, counter: int) -> bytes:
    padded = secret + "=" * ((8 - len(secret) % 8) % 8)
    key = base64.b32decode(padded, casefold=True)
    msg = counter.to_bytes(8, "big")
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = int.from_bytes(digest[offset:offset + 4], "big") & 0x7FFFFFFF
    return str(value % (10 ** _DIGITS)).zfill(_DIGITS).encode("ascii")


def verify_totp(secret: str, code: str, window: int = 1) -> bool:
    normalized = "".join(ch for ch in code.strip() if ch.isdigit())
    if len(normalized) != _DIGITS:
        return False
    now = int(time.time() // _STEP)
    return any(hmac.compare_digest(_counter(secret, now + delta), normalized.encode("ascii")) for delta in range(-window, window + 1))


def encrypted_secret(secret: str) -> str:
    return encrypt_mfa_secret(secret)


def decrypted_secret(value: str) -> str:
    return decrypt_mfa_secret(value)


def otpauth_uri(secret: str, username: str, issuer: str = "AfyaSync Government Portal") -> str:
    label = quote(f"{issuer}:{username}")
    return f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer)}&algorithm=SHA1&digits=6&period=30"
