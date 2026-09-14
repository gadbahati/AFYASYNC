from types import SimpleNamespace
from fastapi import HTTPException
from app.auth.rate_limit import AuthRateLimiter, enforce_auth_rate_limit
from app.patients.national_identity_service import normalize_afya_id

def test_afya_id_normalization_enforces_platform_format():
    assert normalize_afya_id(" af-00000042 ") == "AF-00000042"
    for value in ("AF-42", "AF00000042", "AF-0000000X", ""):
        try: normalize_afya_id(value)
        except ValueError as exc: assert str(exc) == "INVALID_AFYA_ID"
        else: raise AssertionError(f"invalid Afya ID accepted: {value}")

def test_auth_rate_limiter_blocks_after_limit():
    limiter = AuthRateLimiter(limit=2, window_seconds=60)
    request = SimpleNamespace(url=SimpleNamespace(path="/api/v1/auth/login"), client=SimpleNamespace(host="10.0.0.1"), headers={})
    limiter.check(request); limiter.check(request)
    try: limiter.check(request)
    except HTTPException as exc:
        assert exc.status_code == 429; assert exc.detail["code"] == "AUTH_RATE_LIMITED"; assert exc.headers["Retry-After"]
    else: raise AssertionError("rate limiter did not block the third attempt")

def test_auth_rate_limit_enforcer_ignores_non_auth_paths():
    request = SimpleNamespace(url=SimpleNamespace(path="/api/v1/health"), client=SimpleNamespace(host="10.0.0.1"), headers={})
    enforce_auth_rate_limit(request)
