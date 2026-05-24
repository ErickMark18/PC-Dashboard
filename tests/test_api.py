"""Integration tests for PC Dashboard API."""

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestRootEndpoint:
    """Tests for GET / endpoint."""

    def test_root_returns_html(self, client):
        """Test that root endpoint returns HTML content."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


class TestMetricsEndpoint:
    """Tests for GET /metrics endpoint."""

    def test_metrics_returns_current_metrics(self, client):
        """Test that /metrics returns current system metrics."""
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        assert "alerts" in data

    def test_metrics_contains_expected_fields(self, client):
        """Test that /metrics contains all expected metric fields."""
        response = client.get("/metrics")
        data = response.json()
        metrics = data["metrics"]
        expected_fields = [
            "cpu_percent", "cpu_temp", "memory_percent", "memory_available_gb",
            "disk_percent", "disk_free_gb", "network_sent_mb", "network_recv_mb",
            "network_speed_sent_mbps", "network_speed_recv_mbps",
            "gpu_percent", "gpu_available", "timestamp"
        ]
        for field in expected_fields:
            assert field in metrics


class TestHistoryEndpoint:
    """Tests for GET /history endpoint."""

    def test_history_returns_records(self, client):
        """Test that /history returns metric records."""
        response = client.get("/history?hours=1")
        assert response.status_code == 200
        data = response.json()
        assert "records" in data
        assert "count" in data

    def test_history_respects_hours_parameter(self, client):
        """Test that /history accepts hours parameter."""
        response = client.get("/history?hours=24")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["records"], list)

    def test_history_invalidates_extreme_hours(self, client):
        """Test that /history rejects invalid hours values."""
        response = client.get("/history?hours=0")
        assert response.status_code == 422
        response = client.get("/history?hours=500")
        assert response.status_code == 422


class TestExportEndpoint:
    """Tests for GET /history/export endpoint."""

    def test_export_csv_format(self, client):
        """Test CSV export format."""
        response = client.get("/history/export?format=csv")
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")

    def test_export_json_format(self, client):
        """Test JSON export format."""
        response = client.get("/history/export?format=json")
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    def test_export_invalid_format(self, client):
        """Test that invalid format is rejected."""
        response = client.get("/history/export?format=invalid")
        assert response.status_code == 422


class TestThresholdsEndpoint:
    """Tests for threshold endpoints."""

    def test_get_thresholds(self, client):
        """Test GET /thresholds returns current thresholds."""
        response = client.get("/thresholds")
        assert response.status_code == 200
        data = response.json()
        assert "cpu_threshold" in data
        assert "ram_threshold" in data
        assert "disk_threshold" in data

    def test_patch_valid_threshold(self, client):
        """Test PATCH /thresholds/{name} with valid value."""
        response = client.patch("/thresholds/cpu_threshold", json=80.0)
        assert response.status_code == 200
        data = response.json()
        assert data["cpu_threshold"] == 80.0

    def test_patch_invalid_threshold_name(self, client):
        """Test PATCH with invalid threshold name returns 400."""
        response = client.patch("/thresholds/invalid_name", json=80.0)
        assert response.status_code == 400

    def test_patch_threshold_out_of_range(self, client):
        """Test PATCH with out of range value returns 400."""
        response = client.patch("/thresholds/cpu_threshold", json=150.0)
        assert response.status_code == 400


class TestAlertsHistoryEndpoint:
    """Tests for GET /alerts/history endpoint."""

    def test_get_alerts_history(self, client):
        """Test that /alerts/history returns alert records."""
        response = client.get("/alerts/history?hours=24")
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert "count" in data


class TestPeaksEndpoint:
    """Tests for GET /peaks endpoint."""

    def test_get_peaks(self, client):
        """Test that /peaks returns peak records."""
        response = client.get("/peaks")
        assert response.status_code == 200
        data = response.json()
        assert "peaks" in data


class TestTokenEndpoint:
    """Tests for POST /token endpoint."""

    def test_generate_token(self, client):
        """Test that /token generates a JWT token."""
        response = client.post("/token")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


class TestWebSocketEndpoint:
    """Tests for WebSocket /ws endpoint."""

    def test_websocket_requires_token(self, client):
        """Test that WebSocket endpoint requires token."""
        with client.websocket_connect("/ws") as websocket:
            data = websocket.receive_json()
            assert "metrics" in data

    def test_websocket_rejects_invalid_token(self):
        """Test that WebSocket rejects invalid token."""
        import websocket
        with pytest.raises(websocket.WebSocketBadStatusException):
            with TestClient(app).websocket_connect("/ws?token=invalid") as ws:
                pass