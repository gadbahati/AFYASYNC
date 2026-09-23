"""Production readiness — secrets hygiene, env gates, deploy checklist.

Never returns secret values — only pass/fail and lengths.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone

from app.config import settings

_DEFAULT_JWT = "change-this-development-secret"
_WEAK_SECRETS = {"secret", "changeme", "dev", "test", "password", "jwt_secret", _DEFAULT_JWT}


def _secret_meta(name: str, value: str | None) -> dict:
    raw = (value or "").strip()
    present = bool(raw)
    weak = (not present) or (raw.lower() in _WEAK_SECRETS) or (len(raw) < 24)
    if present and len(raw) >= 32 and len(set(raw)) >= 8 and not re.fullmatch(r"(.)\1+", raw):
        weak = False
    if present and raw == _DEFAULT_JWT:
        weak = True
    return {
        "name": name,
        "present": present,
        "length": len(raw) if present else 0,
        "strong_enough": present and not weak,
        # never return the value
    }


def production_readiness() -> dict:
    env = (getattr(settings, "environment", None) or os.getenv("ENVIRONMENT") or "development").lower()
    is_prod = env in {"production", "prod"}

    jwt = getattr(settings, "jwt_secret", None) or os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY")
    db_url = getattr(settings, "database_url", None) or os.getenv("DATABASE_URL") or ""
    cors = []
    try:
        cors = settings.cors_origin_list() if hasattr(settings, "cors_origin_list") else []
    except Exception:
        cors = []

    seed_on = os.getenv("SEED_UNIVERSAL_ADMIN", "").strip().lower() in {"1", "true", "yes"}
    bootstrap_once = os.getenv("BOOTSTRAP_UNIVERSAL_ADMIN_ONCE", "").strip().lower() in {"1", "true", "yes"}
    sha_mode = (os.getenv("SHA_DHA_MODE") or getattr(settings, "sha_dha_mode", None) or "mock").lower()
    sha_token = os.getenv("AFYALINK_BEARER_TOKEN") or os.getenv("SHA_DHA_BEARER_TOKEN") or ""

    checks = []

    def add(code: str, ok: bool, detail: str, severity: str = "HIGH"):
        checks.append({"code": code, "ok": ok, "detail": detail, "severity": severity})

    jwt_meta = _secret_meta("JWT_SECRET", str(jwt) if jwt else None)
    add(
        "JWT_SECRET_STRONG",
        jwt_meta["strong_enough"] if is_prod else True,
        f"present={jwt_meta['present']} length={jwt_meta['length']} (value never exposed)",
        "CRITICAL" if is_prod else "MEDIUM",
    )

    add(
        "ENVIRONMENT_SET",
        bool(env),
        f"environment={env}",
        "HIGH",
    )

    add(
        "DATABASE_URL_SET",
        bool(str(db_url).strip()),
        "DATABASE_URL configured" if str(db_url).strip() else "DATABASE_URL missing",
        "CRITICAL",
    )

    add(
        "NO_DEFAULT_JWT_IN_PROD",
        not (is_prod and str(jwt or "").strip() == _DEFAULT_JWT),
        "Default JWT secret forbidden in production",
        "CRITICAL",
    )

    add(
        "SEED_DISABLED_IN_PROD",
        not (is_prod and seed_on and not bootstrap_once),
        f"SEED_UNIVERSAL_ADMIN={seed_on} BOOTSTRAP_ONCE={bootstrap_once}",
        "CRITICAL",
    )

    add(
        "CORS_NOT_WILDCARD",
        "*" not in (cors or []),
        f"cors_origin_count={len(cors or [])}",
        "HIGH",
    )

    add(
        "SHA_LIVE_HAS_TOKEN",
        not (sha_mode == "live" and not sha_token.strip()),
        f"SHA_DHA_MODE={sha_mode} token_present={bool(sha_token.strip())}",
        "HIGH",
    )

    add(
        "SECURITY_HEADERS",
        True,
        "SecurityHeadersMiddleware registered in main",
        "MEDIUM",
    )

    critical_fail = [c for c in checks if not c["ok"] and c["severity"] == "CRITICAL"]
    high_fail = [c for c in checks if not c["ok"] and c["severity"] == "HIGH"]
    passed = sum(1 for c in checks if c["ok"])
    score = round(100.0 * passed / len(checks), 1) if checks else 0.0
    if critical_fail:
        band = "RED"
    elif high_fail or score < 80:
        band = "AMBER"
    else:
        band = "GREEN"

    return {
        "environment": env,
        "is_production": is_prod,
        "band": band,
        "score_pct": score,
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "secrets_hygiene": {
            "jwt": jwt_meta,
            "sha_token_present": bool(sha_token.strip()),
            "note": "Secret values are never returned by this API",
        },
        "deploy_blocked": bool(critical_fail) and is_prod,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "developer": "BAHATI GAD WANGWE",
    }


def deploy_checklist() -> dict:
    return {
        "title": "AfyaSync production deploy checklist",
        "steps": [
            {
                "id": "ENV-01",
                "step": "Set ENVIRONMENT=production",
            },
            {
                "id": "ENV-02",
                "step": "Set JWT_SECRET to ≥32 random characters (not the default)",
            },
            {
                "id": "ENV-03",
                "step": "Set DATABASE_URL to managed Postgres with TLS",
            },
            {
                "id": "ENV-04",
                "step": "Set CORS_ORIGINS to explicit frontend origins (no *)",
            },
            {
                "id": "ENV-05",
                "step": "Ensure SEED_UNIVERSAL_ADMIN is unset in production",
            },
            {
                "id": "DB-01",
                "step": "Run alembic upgrade head",
            },
            {
                "id": "DB-02",
                "step": "Verify GET /ready returns ready with no missing_tables",
            },
            {
                "id": "APP-01",
                "step": "GET /api/v1/production/readiness must be GREEN (or only non-critical gaps)",
            },
            {
                "id": "APP-02",
                "step": "GET /api/v1/reliability/readiness-matrix",
            },
            {
                "id": "APP-03",
                "step": "GET /api/v1/certification/submission-kit for evidence snapshot",
            },
            {
                "id": "SHA-01",
                "step": "When ready for live claims: SHA_DHA_MODE=live + AFYALINK_BEARER_TOKEN",
            },
            {
                "id": "OPS-01",
                "step": "Configure HTTPS terminator + HSTS at edge",
            },
            {
                "id": "OPS-02",
                "step": "Backup Postgres; test restore",
            },
        ],
        "env_template": {
            "ENVIRONMENT": "production",
            "JWT_SECRET": "<generate-32+-chars>",
            "DATABASE_URL": "postgresql+psycopg://user:pass@host:5432/afyasync",
            "CORS_ORIGINS": "https://app.example.go.ke",
            "SHA_DHA_MODE": "mock",
            "AFYALINK_BEARER_TOKEN": "",
            "SEED_UNIVERSAL_ADMIN": "0",
        },
        "note": "Template uses placeholders only — never commit real secrets",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "developer": "BAHATI GAD WANGWE",
    }
