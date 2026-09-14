import asyncio
from types import SimpleNamespace

from app.main import SecurityHeadersMiddleware
from starlette.responses import Response


def test_security_middleware_sets_request_id_and_security_headers() -> None:
    request = SimpleNamespace(headers={}, state=SimpleNamespace())

    async def call_next(_request):
        return Response(status_code=204)

    middleware = SecurityHeadersMiddleware(lambda scope: None)
    response = asyncio.run(middleware.dispatch(request, call_next))

    assert request.state.request_id
    assert response.headers["X-Request-ID"] == request.state.request_id
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert response.headers["Cross-Origin-Resource-Policy"] == "same-origin"


def test_security_middleware_preserves_valid_request_id() -> None:
    supplied = "request-123"
    request = SimpleNamespace(headers={"X-Request-ID": supplied}, state=SimpleNamespace())

    async def call_next(_request):
        return Response(status_code=200)

    middleware = SecurityHeadersMiddleware(lambda scope: None)
    response = asyncio.run(middleware.dispatch(request, call_next))

    assert request.state.request_id == supplied
    assert response.headers["X-Request-ID"] == supplied
