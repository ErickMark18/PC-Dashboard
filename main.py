"""FastAPI server for PC Dashboard."""

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from collector import get_metrics
from alerts import check_alerts, get_thresholds
from database import save_metric, get_history
from config import settings


connected_clients: list[WebSocket] = []
broadcast_task: asyncio.Task | None = None
save_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global broadcast_task, save_task
    broadcast_task = asyncio.create_task(broadcast_metrics())
    save_task = asyncio.create_task(periodic_save())
    yield
    if broadcast_task:
        broadcast_task.cancel()
    if save_task:
        save_task.cancel()


app = FastAPI(title="PC Dashboard API", lifespan=lifespan)


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
    """Save metrics to database every SAVE_INTERVAL seconds."""
    while True:
        metrics = get_metrics()
        try:
            save_metric(metrics)
        except Exception:
            pass
        await asyncio.sleep(settings.SAVE_INTERVAL)


@app.get("/metrics")
async def get_current_metrics():
    """Return current system metrics snapshot via REST."""
    metrics = get_metrics()
    alerts = check_alerts(metrics)
    return {"metrics": metrics, "alerts": alerts}


@app.get("/history")
async def query_history(hours: int = 24):
    """Return historical metrics for the specified number of hours."""
    records = get_history(hours=hours)
    return {"records": records, "count": len(records)}


@app.get("/thresholds")
async def get_current_thresholds():
    """Return current alert thresholds."""
    return get_thresholds()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time metric streaming."""
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            metrics = get_metrics()
            alerts = check_alerts(metrics)
            await websocket.send_json({"metrics": metrics, "alerts": alerts})
            await asyncio.sleep(1)
    except WebSocketDisconnect:
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