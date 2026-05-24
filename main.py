"""FastAPI server for PC Dashboard."""

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status, Query, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from collector import get_metrics, get_machine_id
from alerts import check_alerts, get_thresholds, update_threshold
from database import (
    save_metric, get_history, export_to_csv, export_to_json,
    get_alert_history, get_peak_records, get_machine_registry,
    register_machine, get_all_machine_metrics
)
from auth import create_access_token, verify_ws_token, verify_token
from config import settings


connected_clients: list[WebSocket] = []
broadcast_task: asyncio.Task | None = None
save_task: asyncio.Task | None = None
_last_saved_metrics: Optional[dict] = None
_SIGNIFICANT_CHANGE_THRESHOLD = 5.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global broadcast_task, save_task
    broadcast_task = asyncio.create_task(broadcast_metrics())
    save_task = asyncio.create_task(periodic_save())
    register_machine(get_machine_id(), get_metrics().get("machine_name", "Unknown"))
    yield
    if broadcast_task:
        broadcast_task.cancel()
    if save_task:
        save_task.cancel()


app = FastAPI(title="PC Dashboard API", lifespan=lifespan)


def _has_significant_change(metrics: dict) -> bool:
    """Check if current metrics differ significantly from last saved."""
    global _last_saved_metrics
    if _last_saved_metrics is None:
        return True

    keys = ["cpu_percent", "memory_percent", "disk_percent"]
    for key in keys:
        current = metrics.get(key, 0)
        previous = _last_saved_metrics.get(key, 0)
        if abs(current - previous) >= _SIGNIFICANT_CHANGE_THRESHOLD:
            return True
    return False


async def broadcast_metrics():
    """Send metrics to all connected WebSocket clients every second."""
    while True:
        metrics = get_metrics()
        alerts = check_alerts(metrics)
        payload = json.dumps({"metrics": metrics, "alerts": alerts})

        for client in connected_clients[:]:
            try:
                await client.send_text(payload)
            except Exception:
                connected_clients.remove(client)

        await asyncio.sleep(1)


async def periodic_save():
    """Save metrics to database only when significant changes occur."""
    global _last_saved_metrics
    while True:
        metrics = get_metrics()
        try:
            significant = _has_significant_change(metrics)
            save_metric(metrics, significant_change=significant)
            if significant:
                _last_saved_metrics = metrics
        except Exception:
            pass
        await asyncio.sleep(settings.SAVE_INTERVAL)


@app.post("/token")
async def generate_token():
    """Generate a JWT token for WebSocket authentication."""
    token = create_access_token({"sub": "dashboard-client"})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/metrics")
async def get_current_metrics():
    """Return current system metrics snapshot via REST."""
    metrics = get_metrics()
    alerts = check_alerts(metrics)
    return {"metrics": metrics, "alerts": alerts}


@app.get("/history")
async def query_history(hours: int = Query(default=24, ge=1, le=168)):
    """Return historical metrics for the specified number of hours."""
    records = get_history(hours=hours)
    return {"records": records, "count": len(records)}


@app.get("/history/export")
async def export_history(
    hours: int = Query(default=24, ge=1, le=168),
    format: str = Query(default="csv", regex="^(csv|json)$"),
):
    """Export historical metrics as CSV or JSON."""
    records = get_history(hours=hours)
    if format == "csv":
        csv_content = export_to_csv(records)
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=metrics_history.csv"},
        )
    else:
        json_content = export_to_json(records)
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            iter([json_content]),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=metrics_history.json"},
        )


@app.get("/alerts/history")
async def get_alerts_history(
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=100, ge=1, le=1000),
):
    """Return alert history for the specified number of hours."""
    alerts = get_alert_history(hours=hours, limit=limit)
    return {"alerts": alerts, "count": len(alerts)}


@app.get("/peaks")
async def get_peaks():
    """Return historical peak records."""
    peaks = get_peak_records()
    return {"peaks": peaks}


@app.get("/machines")
async def list_machines():
    """Return list of registered machines."""
    machines = get_machine_registry()
    return {"machines": machines}


@app.get("/machines/{machine_id}/metrics")
async def get_machine_metrics(machine_id: str):
    """Return latest metrics for a specific machine."""
    all_metrics = get_all_machine_metrics(machine_id)
    if not all_metrics:
        raise HTTPException(status_code=404, detail="Machine not found or no metrics available")
    return {"machine_id": machine_id, "metrics": all_metrics[-1]}


@app.get("/thresholds")
async def get_current_thresholds():
    """Return current alert thresholds."""
    return get_thresholds()


@app.post("/thresholds/reset")
async def reset_thresholds():
    """Reset all thresholds to default values from config."""
    from config import settings
    defaults = {
        "cpu_threshold": settings.CPU_THRESHOLD,
        "ram_threshold": settings.RAM_THRESHOLD,
        "disk_threshold": settings.DISK_THRESHOLD,
        "temp_threshold": settings.TEMP_THRESHOLD,
        "gpu_threshold": settings.GPU_THRESHOLD,
    }
    for name, value in defaults.items():
        update_threshold(name, value)
    return {"message": "Thresholds reset to defaults", "thresholds": get_thresholds()}


@app.patch("/thresholds/{threshold_name}")
async def update_threshold_endpoint(threshold_name: str, value: float):
    """Update a threshold value dynamically."""
    valid_names = ["cpu_threshold", "ram_threshold", "disk_threshold", "temp_threshold", "gpu_threshold"]
    if threshold_name not in valid_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid threshold name. Valid names: {valid_names}",
        )
    if not (0 < value <= 100):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Value must be between 0 and 100",
        )
    return update_threshold(threshold_name, value)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time metric streaming with token auth."""
    try:
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        verify_ws_token(token)
        await websocket.accept()
        connected_clients.append(websocket)

        while True:
            metrics = get_metrics()
            alerts = check_alerts(metrics)
            await websocket.send_json({"metrics": metrics, "alerts": alerts})
            await asyncio.sleep(1)
    except Exception:
        pass
    finally:
        if websocket in connected_clients:
            connected_clients.remove(websocket)


app.mount("/static", StaticFiles(directory="frontend"), name="frontend")


@app.get("/")
async def root():
    """Serve the dashboard frontend."""
    try:
        with open("frontend/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return {"message": "Dashboard not found. Ensure frontend/index.html exists."}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)