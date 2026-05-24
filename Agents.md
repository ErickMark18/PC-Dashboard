# Agents.md - PC Dashboard

## Contexto del Proyecto

Sistema de monitorización de métricas de máquina local (CPU, RAM, temperatura, disco, red, GPU) con streaming en tiempo real via WebSocket a un dashboard web. Todo funciona en red local sin servicios en la nube.

## Estructura del Proyecto

```
PC-Dashboard/
├── collector.py          # Recolector de métricas del sistema
├── config.py             # Configuración con pydantic-settings
├── alerts.py             # Motor de alertas con umbrales configurables
├── database.py           # Modelos SQLAlchemy y operaciones DB
├── main.py               # Servidor FastAPI con REST y WebSocket
├── frontend/
│   └── index.html       # Dashboard web con Chart.js
├── tests/
│   ├── test_collector.py # Tests del collector
│   ├── test_alerts.py    # Tests de alertas
│   └── test_api.py       # Tests de API REST
├── data/
│   └── metrics.db        # SQLite para historial (creado automáticamente)
├── config/
│   └── custom_scripts/   # Scripts custom del usuario
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

### Collector y Servidor
```bash
# Crear virtualenv e instalar dependencias
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# Ejecutar collector standalone (Terminal 1)
python collector.py

# Ejecutar servidor (Terminal 2)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Ejecutar tests
pytest tests/ -v
```

### Variables de Entorno (Windows)
```powershell
$env:DASHBOARD_CPU_THRESHOLD="90"
$env:DASHBOARD_RAM_THRESHOLD="85"
$env:DASHBOARD_DISK_THRESHOLD="90"
$env:DASHBOARD_GPU_THRESHOLD="90"
$env:DASHBOARD_TEMP_THRESHOLD="80"
```

### Dashboard
- Accesible en: http://localhost:8000
- Archivos estáticos servidos desde `/frontend` via FastAPI StaticFiles
- WebSocket requiere token JWT: POST `/token` antes de conectar

### Docker
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
    # - network_speed_sent_mbps: float
    # - network_speed_recv_mbps: float
    # - gpu_percent: float | None
    # - gpu_memory_percent: float | None
    # - gpu_memory_used_mb: float | None
    # - gpu_memory_total_mb: float | None
    # - gpu_temp: float | None (centigrados)
    # - gpu_available: bool
    # - top_processes_cpu: list[dict]
    # - top_processes_mem: list[dict]
    # - custom_metrics: dict
    # - machine_id: str
    # - machine_name: str
    # - timestamp: ISO string
```

### collector.py - GPU Support
- Requiere `nvidia-ml-py` para GPUs NVIDIA
- Fallback: gpu_available será False si no hay NVIDIA o no está instalado

### collector.py - CPU Temperature
- Intenta primero `psutil.sensors_temperatures()` (funciona en Linux/macOS)
- Fallback en Windows usa WMI `MSAcpi_ThermalZoneTemperature` (no funciona en AMD Ryzen)
- Retorna None si no está disponible

### alerts.py - Umbrales por defecto
```python
CPU_THRESHOLD: 90.0    # %
RAM_THRESHOLD: 85.0    # %
DISK_THRESHOLD: 90.0   # %
GPU_THRESHOLD: 90.0    # % (requiere GPU)
TEMP_THRESHOLD: 80.0   # °C (si disponible)
CHECK_INTERVAL: 1.0    # segundos
```

### database.py - Modelos
```python
MetricRecord     # Métricas con cpu_temp, gpu_*, network_speed_*
AlertRecord      # Historial de alertas con metric_name, threshold, value
PeakRecord       # Picos históricos por metric_name
MachineRegistry  # Máquinas registradas
MachineMetricSnapshot  # Snapshots de métricas por máquina
```

### WebSocket Protocol
- Intervalo de emisión: 1 segundo
- Requiere token JWT válido (obtener de POST /token)
- Formato JSON:
```json
{
  "metrics": {...},
  "alerts": ["CPU exceeds 90%", "Disk above 90%"]
}
```

### SQLite Schema (actualizado)
```sql
CREATE TABLE metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    cpu_percent REAL,
    cpu_temp REAL,
    memory_percent REAL,
    disk_percent REAL,
    network_sent_mb REAL,
    network_recv_mb REAL,
    network_speed_sent_mbps REAL,
    network_speed_recv_mbps REAL,
    gpu_percent REAL,
    gpu_memory_percent REAL,
    gpu_memory_used_mb REAL,
    gpu_temp REAL
);
```

### Frontend (index.html)
- Tema claro/oscuro con toggle
- Gráficos Chart.js para CPU/RAM y Disk/GPU
- Panel de configuración flotante (position: fixed)
- Secciones de Alert History y Peaks siempre visibles
- Auto-actualización de Alerts/Peaks cada 10 segundos
- Top Processes en dos columnas (CPU=cyan, RAM=purple)
- Soporte para GPU metrics cuando disponible

## Notas Importantes

- En Windows, `psutil.sensors_temperatures()` puede no devolver datos para todos los sistemas
- CPUs AMD Ryzen no exponen temperatura via WMI MSAcpi en Windows
- El historial se guarda cada 60 segundos, no cada segundo, para no saturar la DB
- El WebSocket envía métricas cada 1 segundo para real-time
- Las notificaciones nativas del navegador requieren que la pestaña tenga focus o permiso explícito
- Puerto 8000 es el default, configurable via `DASHBOARD_PORT`
- GPU metrics requieren `nvidia-ml-py` y GPU NVIDIA
- WebSocket auth requiere POST a `/token` para obtener JWT antes de conectar a `/ws?token=<jwt>`
- Módulo `python-jose` necesario para JWT (`pip install python-jose[cryptography]`)
- Significant change = guardado solo si alguna métrica cambia >5%

## Dependencies nuevas (requirements.txt)
- `nvidia-ml-py>=12.0.0` - GPU NVIDIA metrics
- `wmi>=1.5.0` - Windows temperature via WMI