from app.config import Settings
from app.main import app


def test_security_headers_middleware_installed() -> None:
    names = [middleware.cls.__name__ for middleware in app.user_middleware]
    assert "SecurityHeadersMiddleware" in names


def test_cors_origins_parsed_from_settings() -> None:
    settings = Settings(cors_origins="https://app.example.com, https://admin.example.com")
    assert settings.cors_origin_list() == [
        "https://app.example.com",
        "https://admin.example.com",
    ]
