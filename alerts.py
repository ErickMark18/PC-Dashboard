"""Alert engine for PC Dashboard."""

from typing import List, Optional

from config import settings


_current_thresholds = {
    "cpu_threshold": settings.CPU_THRESHOLD,
    "ram_threshold": settings.RAM_THRESHOLD,
    "disk_threshold": settings.DISK_THRESHOLD,
    "temp_threshold": settings.TEMP_THRESHOLD,
    "gpu_threshold": settings.GPU_THRESHOLD,
}


def check_alerts(metrics: dict, save_alerts: bool = True) -> List[str]:
    """Check metrics against thresholds and return active alerts.

    Args:
        metrics: Dictionary containing current system metrics.
        save_alerts: Whether to save alerts to database.

    Returns:
        List of alert messages for metrics that exceed thresholds.
    """
    alerts: List[str] = []

    if metrics.get("cpu_percent", 0) >= _current_thresholds["cpu_threshold"]:
        alerts.append(f"CPU exceeds {_current_thresholds['cpu_threshold']:.0f}%")
        _save_alert_to_db("cpu_percent", _current_thresholds["cpu_threshold"], metrics["cpu_percent"], alerts[-1], save_alerts)

    if metrics.get("memory_percent", 0) >= _current_thresholds["ram_threshold"]:
        alerts.append(f"RAM exceeds {_current_thresholds['ram_threshold']:.0f}%")
        _save_alert_to_db("memory_percent", _current_thresholds["ram_threshold"], metrics["memory_percent"], alerts[-1], save_alerts)

    if metrics.get("disk_percent", 0) >= _current_thresholds["disk_threshold"]:
        alerts.append(f"Disk above {_current_thresholds['disk_threshold']:.0f}%")
        _save_alert_to_db("disk_percent", _current_thresholds["disk_threshold"], metrics["disk_percent"], alerts[-1], save_alerts)

    cpu_temp = metrics.get("cpu_temp")
    if cpu_temp is not None and cpu_temp >= _current_thresholds["temp_threshold"]:
        alerts.append(f"CPU temperature above {_current_thresholds['temp_threshold']:.0f}°C")
        _save_alert_to_db("cpu_temp", _current_thresholds["temp_threshold"], cpu_temp, alerts[-1], save_alerts)

    if metrics.get("gpu_available") and metrics.get("gpu_percent") is not None:
        if metrics["gpu_percent"] >= _current_thresholds["gpu_threshold"]:
            alerts.append(f"GPU exceeds {_current_thresholds['gpu_threshold']:.0f}%")
            _save_alert_to_db("gpu_percent", _current_thresholds["gpu_threshold"], metrics["gpu_percent"], alerts[-1], save_alerts)

    return alerts


def _save_alert_to_db(metric_name: str, threshold: float, actual: float, message: str, save: bool) -> None:
    """Save alert to database if enabled."""
    if save:
        try:
            from database import save_alert
            save_alert(message, metric_name, threshold, actual)
        except Exception:
            pass


def get_thresholds() -> dict:
    """Return current threshold configuration.

    Returns:
        Dictionary with threshold values.
    """
    return _current_thresholds.copy()


def update_threshold(name: str, value: float) -> dict:
    """Update a threshold value dynamically.

    Args:
        name: Threshold name (e.g., 'cpu_threshold').
        value: New threshold value.

    Returns:
        Updated thresholds dictionary.
    """
    if name in _current_thresholds:
        _current_thresholds[name] = value
    return _current_thresholds.copy()