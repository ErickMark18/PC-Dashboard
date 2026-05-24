# PC Dashboard

Sistema de monitorización de métricas de máquina local (CPU, RAM, temperatura, disco, red, GPU) con streaming en tiempo real via WebSocket a un dashboard web. Todo funciona en red local sin servicios en la nube.

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

## Características

- **Métricas en tiempo real**: CPU, RAM, Disco, Red, GPU (con soporte NVIDIA)
- **Temperatura**: CPU (cuando está disponible) y GPU
- **WebSocket streaming**: Actualización cada segundo
- **Historial**: Guardado en SQLite cada 60 segundos (solo cambios significativos)
- **Alertas configurables**: Con umbral personalizado y notificaciones
- **Peak tracking**: Registro de picos históricos por métrica
- **Exportación**: CSV y JSON del historial
- **Tema claro/oscuro**: Toggle en el dashboard
- **Top procesos**: Ver los procesos que más CPU/RAM consumen
- **Multi-máquina**: Soporte para监控 múltiples PCs (API REST completa)

## Requisitos

- Python 3.11+
- Docker (opcional)
- NVIDIA GPU (opcional, para métricas de GPU)

## Instalación Local

```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecución

```bash
# Terminal 1: Collector (recopila métricas)
python collector.py

# Terminal 2: Servidor
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
| GET | `/history/export?format=csv` | Exportar historial (csv/json) |
| GET | `/thresholds` | Configuración de umbrales |
| PUT | `/thresholds` | Actualizar umbrales |
| GET | `/alerts/history?hours=24` | Historial de alertas |
| GET | `/peaks` | Pico históricos por métrica |
| POST | `/token` | Generar token JWT para WebSocket |
| WS | `/ws?token=<jwt>` | Stream en tiempo real |
| GET | `/machines` | Lista de máquinas registradas |
| GET | `/machines/{machine_id}/metrics` | Métricas de máquina específica |

## Configuración

Variables de entorno con prefijo `DASHBOARD_`:

| Variable | Default | Descripción |
|----------|---------|-------------|
| `DASHBOARD_CPU_THRESHOLD` | 90 | Umbral de CPU (%) |
| `DASHBOARD_RAM_THRESHOLD` | 85 | Umbral de RAM (%) |
| `DASHBOARD_DISK_THRESHOLD` | 90 | Umbral de disco (%) |
| `DASHBOARD_GPU_THRESHOLD` | 90 | Umbral de GPU (%) |
| `DASHBOARD_TEMP_THRESHOLD` | 80 | Umbral de temperatura (°C) |
| `DASHBOARD_SAVE_INTERVAL` | 60 | Intervalo de guardado en DB (s) |
| `DASHBOARD_PORT` | 8000 | Puerto del servidor |

## Métricas

El collector obtiene:

- **CPU**: porcentaje de uso y temperatura (si está disponible)
- **RAM**: porcentaje de uso y GB disponibles
- **Disco**: porcentaje usado y GB libres
- **Red**: MB enviados/recibidos y velocidad en Mbps
- **GPU**: porcentaje de uso, temperatura, VRAM (requiere NVIDIA + nvidia-ml-py)
- **Procesos**: Top 5 por CPU y por RAM

## Alertas

El sistema genera alertas visuales (banner) y nativas del navegador cuando:
- CPU > umbral
- RAM > umbral
- Disco > umbral
- Temperatura > umbral
- GPU > umbral (si disponible)

Las alertas se guardan en la base de datos con timestamp.

## Testing

```bash
pytest tests/ -v
```

## Stack Tecnológico

- **Backend**: FastAPI, uvicorn, psutil, python-jose
- **Base de datos**: SQLite + SQLAlchemy
- **Frontend**: HTML5, Chart.js
- **GPU**: nvidia-ml-py (NVIDIA)
- **Temperatura Windows**: wmi
- **Docker**: python:3.11-slim