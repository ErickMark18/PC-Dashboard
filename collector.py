"""Collector module for system metrics."""

from datetime import datetime, timezone
from typing import Optional

import psutil


def get_metrics() -> dict:
    """Collect current system metrics.

    Returns:
        dict: Dictionary containing CPU, memory, disk, network and temperature metrics.
    """
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    net_io = psutil.net_io_counters()

    cpu_temp: Optional[float] = None
    if hasattr(psutil, "sensors_temperatures"):
        temps = psutil.sensors_temperatures()
        if temps:
            for name, entries in temps.items():
                if entries:
                    cpu_temp = entries[0].current
                    break

    return {
        "cpu_percent": cpu_percent,
        "cpu_temp": cpu_temp,
        "memory_percent": memory.percent,
        "memory_available_gb": round(memory.available / (1024**3), 2),
        "disk_percent": disk.percent,
        "disk_free_gb": round(disk.free / (1024**3), 2),
        "network_sent_mb": round(net_io.bytes_sent / (1024**2), 2),
        "network_recv_mb": round(net_io.bytes_recv / (1024**2), 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    import time

    print("PC Metrics Collector - Press Ctrl+C to stop\n")
    while True:
        metrics = get_metrics()
        print(f"[{metrics['timestamp']}]")
        print(f"  CPU: {metrics['cpu_percent']}%", end="")
        if metrics["cpu_temp"] is not None:
            print(f" ({metrics['cpu_temp']:.1f}°C)", end="")
        print()
        print(f"  RAM: {metrics['memory_percent']}% ({metrics['memory_available_gb']} GB free)")
        print(f"  Disk: {metrics['disk_percent']}% ({metrics['disk_free_gb']} GB free)")
        print(
            f"  Network: ↑{metrics['network_sent_mb']} MB | ↓{metrics['network_recv_mb']} MB"
        )
        print()
        time.sleep(1)