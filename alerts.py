"""Alert engine for PC Dashboard."""

from typing import List, Optional

from config import settings


def check_alerts(metrics: dict) -> List[str]:
    """Check metrics against thresholds and return active alerts.

    Args:
        metrics: Dictionary containing current system metrics.

    Returns:
        List of alert messages for metrics that exceed thresholds.
    """
    alerts: List[str] = []

    if metrics.get("cpu_percent", 0) >= settings.CPU_THRESHOLD:
        alerts.append(f"CPU exceeds {settings.CPU_THRESHOLD:.0f}%")

    if metrics.get("memory_percent", 0) >= settings.RAM_THRESHOLD:
        alerts.append(f"RAM exceeds {settings.RAM_THRESHOLD:.0f}%")

    if metrics.get("disk_percent", 0) >= settings.DISK_THRESHOLD:
        alerts.append(f"Disk above {settings.DISK_THRESHOLD:.0f}%")

    cpu_temp = metrics.get("cpu_temp")
    if cpu_temp is not None and cpu_temp >= settings.TEMP_THRESHOLD:
        alerts.append(f"CPU temperature above {settings.TEMP_THRESHOLD:.0f}°C")

    return alerts


def get_thresholds() -> dict:
    """Return current threshold configuration.

    Returns:
        Dictionary with threshold values.
    """
    return {
        "cpu_threshold": settings.CPU_THRESHOLD,
        "ram_threshold": settings.RAM_THRESHOLD,
        "disk_threshold": settings.DISK_THRESHOLD,
        "temp_threshold": settings.TEMP_THRESHOLD,
    }