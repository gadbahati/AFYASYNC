"""AfyaSync API ASGI entrypoint (Phase 140).

Uses main_application bootstrap (router registry). Optional blob restore remains
available for a future full historical main.py drop-in.

Developed by BAHATI GAD WANGWE.
"""
from app.main_application import SecurityHeadersMiddleware, app  # noqa: F401

__all__ = ["app", "SecurityHeadersMiddleware"]
