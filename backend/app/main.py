"""AfyaSync API ASGI entrypoint — Phase 139 restore loader.

Loads the full application from gzip+base64 blob parts if present,
otherwise falls back to main_application minimal app.

Developed by BAHATI GAD WANGWE.
"""
from __future__ import annotations

try:
    from app.main_restore import install_into

    _g: dict = {}
    install_into(_g)
    app = _g["app"]
except Exception as _restore_exc:
    import logging

    logging.getLogger("afyasync").exception(
        "Full main blob restore failed (%s); using main_application fallback", _restore_exc
    )
    from app.main_application import app  # noqa: F401

__all__ = ["app"]
