"""AfyaSync API ASGI entrypoint.

Phase 139 — thin loader so the large application module can be maintained safely.
Developed by BAHATI GAD WANGWE.
"""
from app.main_application import app  # noqa: F401

__all__ = ["app"]
