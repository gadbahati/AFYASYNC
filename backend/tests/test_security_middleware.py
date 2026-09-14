import asyncio

from starlette.requests import Request
from starlette.responses import Response

from app.main import SecurityHeadersMiddleware


def _request(headers=None):
    raw_headers = []
    for key, value in (headers or {}).items():
        raw_headers.append((key.lower().encode(), value.encode()))
    return Request({
        "type": "http",
        "method": "GET",
        "path": "/health",
        "headers": raw_headers,
        "query_string": b"",
        "server": ("testserver", 80),
        "client": ("testclient", 1234),
        "scheme": "http",
        "http_version": "1.1",
    })


def test_security_headers_and_request_id_are_added():
    async def call_next(request):
        assert request.state.request_id
        return Response("ok")

    response = asyncio.run(SecurityHeadersMiddleware(None).dispatch(_request(), call_next))
    assert response.headers["X-Request-ID"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Permissions-Policy"] == "geolocation=(), microphone=(), camera=()"
    assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert response.headers["Cross-Origin-Resource-Policy"] == "same-origin"
    assert response.headers["X-Permitted-Cross-Domain-Policies"] == "none"
    assert response.headers["Cache-Control"] == "no-store"


def test_client_request_id_is_preserved():
    async def call_next(request):
        assert request.state.request_id == "test-request-123"
        return Response("ok")

    response = asyncio.run(
        SecurityHeadersMiddleware(None).dispatch(
            _request({"X-Request-ID": "test-request-123"}), call_next
        )
    )
    assert response.headers["X-Request-ID"] == "test-request-123"


def test_unhandled_errors_return_generic_response_with_request_id():
    async def call_next(request):
        raise RuntimeError("sensitive internal detail")

    response = asyncio.run(
        SecurityHeadersMiddleware(None).dispatch(
            _request({"X-Request-ID": "incident-42"}), call_next
        )
    )
    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == "incident-42"
