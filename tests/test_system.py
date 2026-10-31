"""Foundation tests for service availability and request correlation."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_reports_application_status_and_correlation_id() -> None:
    with TestClient(app) as client:
        response = client.get("/health", headers={"X-Correlation-ID": "test-correlation"})

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["correlation_id"] == "test-correlation"
    assert response.headers["X-Correlation-ID"] == "test-correlation"


def test_versioned_readiness_endpoint_is_available() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.headers["X-Correlation-ID"]
