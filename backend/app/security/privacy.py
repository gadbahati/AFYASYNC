import re
from collections.abc import Mapping
from typing import Any

_UUID_PATH = re.compile(r"(?i)(?<![A-F0-9])[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}(?![A-F0-9])")
_SENSITIVE_KEYS = {
    "password", "passwd", "secret", "token", "access_token", "refresh_token",
    "authorization", "cookie", "set-cookie", "api_key", "apikey",
    "client_secret", "private_key", "callback_secret", "national_id",
    "id_number", "membership_number", "phone", "email",
}
_MAX_STRING = 500
_MAX_DEPTH = 4
_MAX_ITEMS = 50


def redact_sensitive(value: Any, *, depth: int = 0) -> Any:
    """Return a bounded, JSON-safe copy with common secrets and direct identifiers redacted."""
    if depth > _MAX_DEPTH:
        return "[REDACTED_DEPTH]"
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in list(value.items())[:_MAX_ITEMS]:
            key_text = str(key)
            normalized = key_text.strip().lower().replace("-", "_")
            if normalized in _SENSITIVE_KEYS or normalized.endswith("_token") or normalized.endswith("_secret"):
                out[key_text] = "[REDACTED]"
            else:
                out[key_text] = redact_sensitive(item, depth=depth + 1)
        return out
    if isinstance(value, (list, tuple, set)):
        return [redact_sensitive(item, depth=depth + 1) for item in list(value)[:_MAX_ITEMS]]
    if isinstance(value, str):
        return value[:_MAX_STRING] + ("…" if len(value) > _MAX_STRING else "")
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:_MAX_STRING]


def privacy_safe_path(path: str) -> str:
    """Remove UUID resource identifiers from operational logs while preserving route shape."""
    return _UUID_PATH.sub(":id", path or "")
