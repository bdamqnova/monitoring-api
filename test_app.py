import pytest
from unittest.mock import patch, MagicMock
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_home_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.get_json()["message"] == "Monitoring API is running"


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "healthy"


@patch("app.get_connection")
def test_post_metrics_success(mock_get_connection, client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_get_connection.return_value = mock_conn

    payload = {
        "device_name": "server-test",
        "cpu_percent": 25.5,
        "memory_percent": 60.0,
        "disk_percent": 70.0,
        "timestamp": "2026-04-08T12:00:00Z"
    }

    response = client.post("/api/metrics", json=payload)

    assert response.status_code == 201
    assert response.get_json()["message"] == "Metrics received and stored successfully"


@patch("app.get_connection")
def test_post_metrics_missing_field(mock_get_connection, client):
    payload = {
        "device_name": "server-test",
        "cpu_percent": 25.5,
        "memory_percent": 60.0,
        "timestamp": "2026-04-08T12:00:00Z"
    }

    response = client.post("/api/metrics", json=payload)

    assert response.status_code == 400
    assert "Missing field" in response.get_json()["error"]