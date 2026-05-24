"""Collector module for system metrics."""

from datetime import datetime, timezone
from typing import Optional
import socket
import hashlib

import psutil


_prev_net_io: Optional[dict] = None
_machine_id: Optional[str] = None


def get_machine_id() -> str:
    """Get or generate a unique machine ID."""
    global _machine_id
    if _machine_id is None:
        try:
            hostname = socket.gethostname()
            _machine_id = hashlib.sha256(hostname.encode()).hexdigest()[:16]
        except Exception:
            _machine_id = "unknown"
    return _machine_id


def get_metrics() -> dict:
    """Collect current system metrics.

    Returns:
        dict: Dictionary containing CPU, memory, disk, network, GPU and temperature metrics.
    """
    global _prev_net_io

    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    net_io = psutil.net_io_counters()

    now = datetime.now(timezone.utc)
    timestamp = now.isoformat()

    if _prev_net_io is not None:
        time_delta = (now - _prev_net_io["timestamp"]).total_seconds()
        if time_delta > 0:
            sent_diff = net_io.bytes_sent - _prev_net_io["bytes_sent"]
            recv_diff = net_io.bytes_recv - _prev_net_io["bytes_recv"]
            network_speed_sent_mbps = round((sent_diff * 8) / (time_delta * 1_000_000), 2)
            network_speed_recv_mbps = round((recv_diff * 8) / (time_delta * 1_000_000), 2)
        else:
            network_speed_sent_mbps = 0.0
            network_speed_recv_mbps = 0.0
    else:
        network_speed_sent_mbps = 0.0
        network_speed_recv_mbps = 0.0

    _prev_net_io = {
        "timestamp": now,
        "bytes_sent": net_io.bytes_sent,
        "bytes_recv": net_io.bytes_recv,
    }

    cpu_temp: Optional[float] = None
    if hasattr(psutil, "sensors_temperatures"):
        temps = psutil.sensors_temperatures()
        if temps:
            for name, entries in temps.items():
                if entries:
                    cpu_temp = entries[0].current
                    break

    gpu_metrics = _get_gpu_metrics()
    process_metrics = _get_process_metrics()
    custom_metrics = _get_custom_metrics()

    return {
        "machine_id": get_machine_id(),
        "machine_name": socket.gethostname(),
        "cpu_percent": cpu_percent,
        "cpu_temp": cpu_temp,
        "memory_percent": memory.percent,
        "memory_available_gb": round(memory.available / (1024**3), 2),
        "disk_percent": disk.percent,
        "disk_free_gb": round(disk.free / (1024**3), 2),
        "network_sent_mb": round(net_io.bytes_sent / (1024**2), 2),
        "network_recv_mb": round(net_io.bytes_recv / (1024**2), 2),
        "network_speed_sent_mbps": network_speed_sent_mbps,
        "network_speed_recv_mbps": network_speed_recv_mbps,
        "gpu_percent": gpu_metrics.get("gpu_percent"),
        "gpu_memory_percent": gpu_metrics.get("gpu_memory_percent"),
        "gpu_memory_used_mb": gpu_metrics.get("gpu_memory_used_mb"),
        "gpu_memory_total_mb": gpu_metrics.get("gpu_memory_total_mb"),
        "gpu_temp": gpu_metrics.get("gpu_temp"),
        "gpu_available": gpu_metrics.get("gpu_available"),
        "top_processes_cpu": process_metrics.get("top_processes_cpu", []),
        "top_processes_mem": process_metrics.get("top_processes_mem", []),
        "custom_metrics": custom_metrics,
        "timestamp": timestamp,
    }


def _get_gpu_metrics() -> dict:
    """Get GPU metrics using nvidia-ml-py.

    Returns:
        dict with GPU metrics or empty values if no GPU available.
    """
    result = {
        "gpu_percent": None,
        "gpu_memory_percent": None,
        "gpu_memory_used_mb": None,
        "gpu_memory_total_mb": None,
        "gpu_temp": None,
        "gpu_available": False,
    }

    try:
        import pynvml

        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        if device_count > 0:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)

            result["gpu_percent"] = float(util.gpu)
            result["gpu_memory_percent"] = float(mem.used / mem.total * 100)
            result["gpu_memory_used_mb"] = round(mem.used / (1024**2), 1)
            result["gpu_memory_total_mb"] = round(mem.total / (1024**2), 1)
            result["gpu_temp"] = float(temp)
            result["gpu_available"] = True
        pynvml.nvmlShutdown()
    except Exception:
        pass

    return result


def _get_process_metrics() -> dict:
    """Get top processes by CPU and memory usage.

    Returns:
        dict with top_processes_cpu and top_processes_mem lists.
    """
    result = {"top_processes_cpu": [], "top_processes_mem": []}

    try:
        processes = []
        for proc in psutil.process_iter(["name", "cpu_percent", "memory_percent"]):
            try:
                processes.append({
                    "name": proc.info["name"] or "Unknown",
                    "cpu_percent": proc.info["cpu_percent"] or 0.0,
                    "memory_percent": proc.info["memory_percent"] or 0.0,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        processes.sort(key=lambda x: x["cpu_percent"], reverse=True)
        result["top_processes_cpu"] = processes[:5]

        processes.sort(key=lambda x: x["memory_percent"], reverse=True)
        result["top_processes_mem"] = processes[:5]
    except Exception:
        pass

    return result


def _get_custom_metrics() -> dict:
    """Get custom metrics from user-defined scripts.

    Searches for executable scripts in the config/custom_scripts directory
    and runs them if they output valid JSON.

    Returns:
        dict with custom metric key-value pairs.
    """
    result = {}
    import os
    import subprocess
    import json

    custom_scripts_dir = "config/custom_scripts"
    if not os.path.isdir(custom_scripts_dir):
        return result

    for filename in os.listdir(custom_scripts_dir):
        if filename.endswith((".py", ".sh", ".ps1")):
            filepath = os.path.join(custom_scripts_dir, filename)
            try:
                if filename.endswith(".py"):
                    result_proc = subprocess.run(
                        ["python", filepath],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                elif filename.endswith(".ps1"):
                    result_proc = subprocess.run(
                        ["powershell", "-File", filepath],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                else:
                    result_proc = subprocess.run(
                        [filepath],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )

                if result_proc.returncode == 0:
                    output = result_proc.stdout.strip()
                    if output:
                        data = json.loads(output)
                        if isinstance(data, dict):
                            result[filename] = data
            except Exception:
                pass

    return result


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
            f"  Network: ↑{metrics['network_sent_mb']} MB ({metrics['network_speed_sent_mbps']} Mbps) | "
            f"↓{metrics['network_recv_mb']} MB ({metrics['network_speed_recv_mbps']} Mbps)"
        )
        if metrics.get("gpu_available"):
            print(
                f"  GPU: {metrics['gpu_percent']}% | "
                f"VRAM: {metrics['gpu_memory_percent']}% "
                f"({metrics['gpu_memory_used_mb']}/{metrics['gpu_memory_total_mb']} MB) | "
                f"{metrics['gpu_temp']}°C"
            )
        else:
            print("  GPU: Not available")
        print()
        time.sleep(1)