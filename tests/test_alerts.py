"""Tests for alerts module."""

import pytest
from unittest.mock import patch, MagicMock
from alerts import check_alerts, get_thresholds, update_threshold, _current_thresholds


class TestCheckAlerts:
    """Tests for check_alerts function with mocked metrics."""

    def test_no_alerts_when_all_metrics_below_threshold(self):
        """Test that no alerts are generated when all metrics are below thresholds."""
        metrics = {
            "cpu_percent": 50.0,
            "memory_percent": 50.0,
            "disk_percent": 50.0,
            "cpu_temp": 50.0,
            "gpu_available": True,
            "gpu_percent": 50.0,
        }
        with patch("alerts._current_thresholds", {
            "cpu_threshold": 90.0,
            "ram_threshold": 85.0,
            "disk_threshold": 90.0,
            "temp_threshold": 80.0,
            "gpu_threshold": 90.0,
        }):
            alerts = check_alerts(metrics, save_alerts=False)
            assert len(alerts) == 0

    def test_cpu_alert_when_at_threshold(self):
        """Test CPU alert is generated when CPU meets threshold."""
        metrics = {
            "cpu_percent": 90.0,
            "memory_percent": 50.0,
            "disk_percent": 50.0,
        }
        with patch("alerts._current_thresholds", {
            "cpu_threshold": 90.0,
            "ram_threshold": 85.0,
            "disk_threshold": 90.0,
            "temp_threshold": 80.0,
            "gpu_threshold": 90.0,
        }):
            alerts = check_alerts(metrics, save_alerts=False)
            assert len(alerts) == 1
            assert "CPU exceeds 90%" in alerts[0]

    def test_cpu_alert_when_above_threshold(self):
        """Test CPU alert is generated when CPU exceeds threshold."""
        metrics = {
            "cpu_percent": 95.0,
            "memory_percent": 50.0,
            "disk_percent": 50.0,
        }
        with patch("alerts._current_thresholds", {
            "cpu_threshold": 90.0,
            "ram_threshold": 85.0,
            "disk_threshold": 90.0,
            "temp_threshold": 80.0,
            "gpu_threshold": 90.0,
        }):
            alerts = check_alerts(metrics, save_alerts=False)
            assert len(alerts) == 1
            assert "CPU exceeds 90%" in alerts[0]

    def test_ram_alert_when_above_threshold(self):
        """Test RAM alert is generated when RAM exceeds threshold."""
        metrics = {
            "cpu_percent": 50.0,
            "memory_percent": 90.0,
            "disk_percent": 50.0,
        }
        with patch("alerts._current_thresholds", {
            "cpu_threshold": 90.0,
            "ram_threshold": 85.0,
            "disk_threshold": 90.0,
            "temp_threshold": 80.0,
            "gpu_threshold": 90.0,
        }):
            alerts = check_alerts(metrics, save_alerts=False)
            assert len(alerts) == 1
            assert "RAM exceeds 85%" in alerts[0]

    def test_disk_alert_when_above_threshold(self):
        """Test Disk alert is generated when Disk exceeds threshold."""
        metrics = {
            "cpu_percent": 50.0,
            "memory_percent": 50.0,
            "disk_percent": 95.0,
        }
        with patch("alerts._current_thresholds", {
            "cpu_threshold": 90.0,
            "ram_threshold": 85.0,
            "disk_threshold": 90.0,
            "temp_threshold": 80.0,
            "gpu_threshold": 90.0,
        }):
            alerts = check_alerts(metrics, save_alerts=False)
            assert len(alerts) == 1
            assert "Disk above 90%" in alerts[0]

    def test_temp_alert_when_above_threshold(self):
        """Test temperature alert is generated when CPU temp exceeds threshold."""
        metrics = {
            "cpu_percent": 50.0,
            "memory_percent": 50.0,
            "disk_percent": 50.0,
            "cpu_temp": 85.0,
        }
        with patch("alerts._current_thresholds", {
            "cpu_threshold": 90.0,
            "ram_threshold": 85.0,
            "disk_threshold": 90.0,
            "temp_threshold": 80.0,
            "gpu_threshold": 90.0,
        }):
            alerts = check_alerts(metrics, save_alerts=False)
            assert len(alerts) == 1
            assert "temperature above 80°C" in alerts[0]

    def test_temp_no_alert_when_null(self):
        """Test no temperature alert when cpu_temp is None."""
        metrics = {
            "cpu_percent": 50.0,
            "memory_percent": 50.0,
            "disk_percent": 50.0,
            "cpu_temp": None,
        }
        with patch("alerts._current_thresholds", {
            "cpu_threshold": 90.0,
            "ram_threshold": 85.0,
            "disk_threshold": 90.0,
            "temp_threshold": 80.0,
            "gpu_threshold": 90.0,
        }):
            alerts = check_alerts(metrics, save_alerts=False)
            assert len(alerts) == 0

    def test_gpu_alert_when_available_and_above_threshold(self):
        """Test GPU alert is generated when GPU is available and exceeds threshold."""
        metrics = {
            "cpu_percent": 50.0,
            "memory_percent": 50.0,
            "disk_percent": 50.0,
            "gpu_available": True,
            "gpu_percent": 95.0,
        }
        with patch("alerts._current_thresholds", {
            "cpu_threshold": 90.0,
            "ram_threshold": 85.0,
            "disk_threshold": 90.0,
            "temp_threshold": 80.0,
            "gpu_threshold": 90.0,
        }):
            alerts = check_alerts(metrics, save_alerts=False)
            assert len(alerts) == 1
            assert "GPU exceeds 90%" in alerts[0]

    def test_no_gpu_alert_when_not_available(self):
        """Test no GPU alert when GPU is not available."""
        metrics = {
            "cpu_percent": 50.0,
            "memory_percent": 50.0,
            "disk_percent": 50.0,
            "gpu_available": False,
            "gpu_percent": None,
        }
        with patch("alerts._current_thresholds", {
            "cpu_threshold": 90.0,
            "ram_threshold": 85.0,
            "disk_threshold": 90.0,
            "temp_threshold": 80.0,
            "gpu_threshold": 90.0,
        }):
            alerts = check_alerts(metrics, save_alerts=False)
            assert len(alerts) == 0

    def test_multiple_alerts(self):
        """Test multiple alerts are generated when multiple metrics exceed thresholds."""
        metrics = {
            "cpu_percent": 95.0,
            "memory_percent": 90.0,
            "disk_percent": 95.0,
            "cpu_temp": 85.0,
            "gpu_available": True,
            "gpu_percent": 95.0,
        }
        with patch("alerts._current_thresholds", {
            "cpu_threshold": 90.0,
            "ram_threshold": 85.0,
            "disk_threshold": 90.0,
            "temp_threshold": 80.0,
            "gpu_threshold": 90.0,
        }):
            alerts = check_alerts(metrics, save_alerts=False)
            assert len(alerts) == 5

    def test_missing_metric_keys_default_to_zero(self):
        """Test that missing metric keys default to 0 for comparison."""
        metrics = {}
        with patch("alerts._current_thresholds", {
            "cpu_threshold": 90.0,
            "ram_threshold": 85.0,
            "disk_threshold": 90.0,
            "temp_threshold": 80.0,
            "gpu_threshold": 90.0,
        }):
            alerts = check_alerts(metrics, save_alerts=False)
            assert len(alerts) == 0


class TestGetThresholds:
    """Tests for get_thresholds function."""

    def test_get_thresholds_returns_dict(self):
        """Test that get_thresholds returns a dictionary."""
        thresholds = get_thresholds()
        assert isinstance(thresholds, dict)

    def test_get_thresholds_contains_expected_keys(self):
        """Test that get_thresholds contains all expected threshold keys."""
        thresholds = get_thresholds()
        expected_keys = ["cpu_threshold", "ram_threshold", "disk_threshold", "temp_threshold", "gpu_threshold"]
        for key in expected_keys:
            assert key in thresholds

    def test_get_thresholds_returns_copy(self):
        """Test that get_thresholds returns a copy, not the original."""
        thresholds = get_thresholds()
        original_length = len(thresholds)
        thresholds["new_key"] = "value"
        thresholds2 = get_thresholds()
        assert "new_key" not in thresholds2


class TestUpdateThreshold:
    """Tests for update_threshold function."""

    def test_update_existing_threshold(self):
        """Test updating an existing threshold value."""
        original_value = _current_thresholds["cpu_threshold"]
        result = update_threshold("cpu_threshold", 75.0)
        assert result["cpu_threshold"] == 75.0
        _current_thresholds["cpu_threshold"] = original_value

    def test_update_threshold_returns_all_thresholds(self):
        """Test that update_threshold returns all thresholds."""
        result = update_threshold("cpu_threshold", 80.0)
        assert isinstance(result, dict)
        assert "cpu_threshold" in result
        assert "ram_threshold" in result
        assert "disk_threshold" in result

    def test_update_invalid_threshold_name_returns_unchanged(self):
        """Test that updating an invalid threshold name doesn't change anything."""
        original_thresholds = _current_thresholds.copy()
        result = update_threshold("invalid_threshold", 50.0)
        assert result == original_thresholds