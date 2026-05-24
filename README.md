# PC Dashboard

Sistema de monitorización de métricas de máquina local con streaming en tiempo real via WebSocket.

## Arquitectura

```
┌─────────────────┐     WebSocket      ┌─────────────────┐
│  PC Dashboard   │◄──────────────────┤  FastAPI Server │
│  (HTML/JS/Chart)│     GET /ws        │   (Python)      │
└─────────────────┘                    └────────┬────────┘
                                                │
                   ┌────────────────────────────┼────────────────────────────┐
                   │                            │                            │
            ┌──────▼──────┐             ┌───────▼───────┐            ┌───────▼───────┐
            │  collector  │             │    alerts     │            │   database    │
            │   (psutil)  │             │  (thresholds) │            │   (SQLite)    │
            └─────────────┘             └───────────────┘            └───────────────┘
```

## Requisitos

- Python 3.11+
- Docker (opcional)

## Instalación Local

```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecución

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Accede a http://localhost:8000

## Docker

```bash
docker-compose up --build
```

## API Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Dashboard web |
| GET | `/metrics` | Snapshot actual de métricas |
| GET | `/history?hours=24` | Historial de métricas |
| GET | `/thresholds` | Configuración de umbrales |
| WS | `/ws` | Stream en tiempo real |

## Configuración

Variables de entorno con prefijo `DASHBOARD_`:

| Variable | Default | Descripción |
|----------|---------|-------------|
| `DASHBOARD_CPU_THRESHOLD` | 90 | Umbral de CPU (%) |
| `DASHBOARD_RAM_THRESHOLD` | 85 | Umbral de RAM (%) |
| `DASHBOARD_DISK_THRESHOLD` | 90 | Umbral de disco (%) |
| `DASHBOARD_TEMP_THRESHOLD` | 80 | Umbral de temperatura (°C) |
| `DASHBOARD_SAVE_INTERVAL` | 60 | Intervalo de guardado en DB (s) |

## Métricas

El collector obtiene:

- **CPU**: porcentaje de uso y temperatura (si está disponible)
- **RAM**: porcentaje de uso y GB disponibles
- **Disco**: porcentaje usado y GB libres
- **Red**: MB enviados y recibidos

## Alertas

El sistema genera alertas visuales (banner) y nativas del navegador cuando:
- CPU > umbral
- RAM > umbral
- Disco > umbral
- Temperatura > umbral

## Testing

```bash
pytest tests/ -v
```

## Stack Tecnológico

- **Backend**: FastAPI, uvicorn, psutil
- **Base de datos**: SQLite + SQLAlchemy
- **Frontend**: HTML5, Chart.js
- **Docker**: python:3.11-slim