# Agents.md - PC Dashboard

## Contexto del Proyecto

Sistema de monitorización de métricas de máquina local (CPU, RAM, temperatura, disco, red) con streaming en tiempo real via WebSocket a un dashboard web. Todo funciona en red local sin servicios en la nube.

## Estructura del Proyecto

```
PC-Dashboard/
├── collector.py          # Recolector de métricas del sistema
├── config.py             # Configuración con pydantic-settings
├── alerts.py             # Motor de alertas con umbrales configurables
├── main.py               # Servidor FastAPI con REST y WebSocket
├── frontend/
│   └── index.html       # Dashboard web con Chart.js
├── tests/
│   └── test_collector.py # Tests básicos de métricas
├── data/
│   └── metrics.db        # SQLite para historial (creado automáticamente)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Convenciones de Código

### Python
- Tipo hints obligatorios en todas las funciones
- Docstrings Google style para módulos y funciones públicas
- Imports ordenados: stdlib → third-party → local
- Variables de entorno en mayúsculas con underscore (ej: `CPU_THRESHOLD`)
- Funciones async con `async def` cuando interactúan con I/O

### Configuración (config.py)
- Usar `pydantic-settings` con `BaseSettings`
- Variables de entorno con prefijos `DASHBOARD_` (ej: `DASHBOARD_CPU_THRESHOLD`)
- Valores por defecto sensatos para desarrollo local
- Tipado fuerte con types de pydantic

### Testing (pytest)
- Tests en `tests/` con prefijo `test_`
- Fixtures para datos simulados de métricas
- Tests deben ser independientes, sin estado compartido
- Usar `pytest-asyncio` para tests de async si es necesario

### Docker
- Imagen base: `python:3.11-slim`
- Puerto expuesto: 8000
- No ejecutar como root (USER directive)
- Volumen para persistencia de SQLite

## Comandos de Desarrollo

### Fase 1 - Collector
```bash
# Crear virtualenv e instalar dependencias
python -m venv venv
.\venv\Scripts\activate
pip install psutil fastapi uvicorn pytest pytest-asyncio

# Ejecutar collector standalone
python collector.py

# Ejecutar tests
pytest tests/ -v
```

### Fase 2 - Backend
```bash
# Variables de entorno (Windows)
$env:DASHBOARD_CPU_THRESHOLD="90"
$env:DASHBOARD_RAM_THRESHOLD="85"
$env:DASHBOARD_DISK_THRESHOLD="90"

# Ejecutar servidor
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Probar WebSocket con wscat
wscat -c ws://localhost:8000/ws
```

### Fase 3 - Dashboard
- Accesible en: http://localhost:8000
- Archivos estáticos servidos desde `/frontend` via FastAPI StaticFiles

### Fase 4 - Docker
```bash
# Build y ejecución
docker-compose up --build

# Ver logs
docker-compose logs -f

# Detener
docker-compose down
```

## Detalles de Implementación

### collector.py - Métricas
```python
def get_metrics() -> dict:
    # Retorna:
    # - cpu_percent: float (0-100)
    # - cpu_temp: float | None (centigrados)
    # - memory_percent: float (0-100)
    # - memory_available_gb: float
    # - disk_percent: float (0-100)
    # - disk_free_gb: float
    # - network_sent_mb: float
    # - network_recv_mb: float
    # - timestamp: ISO string
```

### alerts.py - Umbrales por defecto
```python
CPU_THRESHOLD: 90.0  # %
RAM_THRESHOLD: 85.0  # %
DISK_THRESHOLD: 90.0  # %
TEMP_THRESHOLD: 80.0  # °C (si disponible)
CHECK_INTERVAL: 1.0   # segundos
```

### WebSocket Protocol
- Intervalo de emisión: 1 segundo
- Formato JSON:
```json
{
  "metrics": {...},
  "alerts": ["CPU exceeds 90%", "Disk above 90%"]
}
```

### SQLite Schema
```sql
CREATE TABLE metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    cpu_percent REAL,
    memory_percent REAL,
    disk_percent REAL,
    network_sent_mb REAL,
    network_recv_mb REAL
);
```

## Notas Importantes

- En Windows, `psutil.sensors_temperatures()` puede no devolver datos para todos los sistemas
- El historial se guarda cada 60 segundos, no cada segundo, para no saturar la DB
- El WebSocket envía métricas cada 1 segundo para real-time
- Las notificaciones nativas del navegador requieren que la pestaña tenga focus o permiso explícito
- Puerto 8000 es el default, configurable via `DASHBOARD_PORT`