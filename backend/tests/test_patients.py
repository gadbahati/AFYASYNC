from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"]["status"] == "healthy"


def test_api_root() -> None:
    response = client.get("/api/v1")
    assert response.status_code == 200
    assert response.json()["success"] is True
