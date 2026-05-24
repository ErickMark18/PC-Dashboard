"""Tests for collector module."""

import pytest
from collector import get_metrics


def test_get_metrics_returns_dict():
    """Test that get_metrics returns a dictionary."""
    metrics = get_metrics()
    assert isinstance(metrics, dict)


def test_get_metrics_contains_required_keys():
    """Test that all required keys are present."""
    required_keys = {
        "cpu_percent",
        "cpu_temp",
        "memory_percent",
        "memory_available_gb",
        "disk_percent",
        "disk_free_gb",
        "network_sent_mb",
        "network_recv_mb",
        "timestamp",
    }
    metrics = get_metrics()
    assert required_keys.issubset(metrics.keys())


def test_cpu_percent_is_valid():
    """Test that CPU percent is a valid percentage."""
    metrics = get_metrics()
    assert isinstance(metrics["cpu_percent"], float)
    assert 0 <= metrics["cpu_percent"] <= 100


def test_memory_percent_is_valid():
    """Test that memory percent is a valid percentage."""
    metrics = get_metrics()
    assert isinstance(metrics["memory_percent"], float)
    assert 0 <= metrics["memory_percent"] <= 100


def test_disk_percent_is_valid():
    """Test that disk percent is a valid percentage."""
    metrics = get_metrics()
    assert isinstance(metrics["disk_percent"], float)
    assert 0 <= metrics["disk_percent"] <= 100


def test_disk_free_gb_is_positive():
    """Test that disk free space is positive."""
    metrics = get_metrics()
    assert metrics["disk_free_gb"] > 0


def test_network_metrics_are_positive():
    """Test that network metrics are non-negative."""
    metrics = get_metrics()
    assert metrics["network_sent_mb"] >= 0
    assert metrics["network_recv_mb"] >= 0


def test_cpu_temp_is_valid_or_none():
    """Test that CPU temp is either None or a valid float."""
    metrics = get_metrics()
    if metrics["cpu_temp"] is not None:
        assert isinstance(metrics["cpu_temp"], float)
        assert metrics["cpu_temp"] > 0


def test_timestamp_is_iso_format():
    """Test that timestamp is in ISO format."""
    metrics = get_metrics()
    from datetime import datetime

    datetime.fromisoformat(metrics["timestamp"].replace("Z", "+00:00"))