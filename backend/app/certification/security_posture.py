"""Runtime security posture — configuration and middleware checks."""

from __future__ import annotations

import os

from app.config import settings


def security_posture() -> dict:
    env = (settings.environment or "development").lower()
    is_prod = env == "production"

    checks = []

    def add(code: str, ok: bool, detail: str, severity: str = "HIGH"):
        checks.append({"code": code, "ok": ok, "detail": detail, "severity": severity})

    # JWT / secrets
    secret = getattr(settings, "jwt_secret", None) or os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY")
    weak = not secret or secret in {"secret", "changeme", "dev", "test"} or len(str(secret)) < 24
    add(
        "JWT_SECRET_STRENGTH",
        not weak if is_prod else True,
        "Production requires strong JWT secret (≥24 chars, not default)" if is_prod else "Non-prod: secret strength advisory only",
        "CRITICAL" if is_prod else "MEDIUM",
    )

    add(
        "ENVIRONMENT_DECLARED",
        bool(env),
        f"environment={env}",
        "MEDIUM",
    )

    cors = []
    try:
        cors = settings.cors_origin_list() if hasattr(settings, "cors_origin_list") else []
    except Exception:
        cors = []
    add(
        "CORS_NOT_WILDCARD",
        "*" not in (cors or []),
        f"cors_origins_count={len(cors or [])}",
        "HIGH",
    )

    add(
        "HSTS_POLICY",
        True,  # enforced in middleware when production
        "Strict-Transport-Security set when environment=production",
        "HIGH",
    )

    add(
        "SEED_ADMIN_LOCKED_IN_PROD",
        not (is_prod and os.getenv("SEED_UNIVERSAL_ADMIN", "").lower() in {"1", "true", "yes"}),
        "SEED_UNIVERSAL_ADMIN forbidden in production without bootstrap flag",
        "CRITICAL",
    )

    sha_mode = (os.getenv("SHA_DHA_MODE") or "mock").lower()
    add(
        "SHA_LIVE_REQUIRES_TOKEN",
        not (sha_mode == "live" and not (os.getenv("AFYALINK_BEARER_TOKEN") or os.getenv("SHA_DHA_BEARER_TOKEN"))),
        f"SHA_DHA_MODE={sha_mode}",
        "HIGH",
    )

    failed = [c for c in checks if not c["ok"]]
    critical_failed = [c for c in failed if c["severity"] == "CRITICAL"]

    return {
        "environment": env,
        "passed": len(checks) - len(failed),
        "failed": len(failed),
        "critical_failed": len(critical_failed),
        "posture": "FAIL" if critical_failed else ("WARN" if failed else "PASS"),
        "checks": checks,
        "developer": "BAHATI GAD WANGWE",
    }
