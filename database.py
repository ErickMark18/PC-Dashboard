"""Database models for metrics history."""

import csv
import io
import json
import zlib
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, Column, Integer, Float, DateTime, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config import settings

Base = declarative_base()


class MetricRecord(Base):
    """Single metric snapshot stored in database."""

    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    cpu_percent = Column(Float)
    cpu_temp = Column(Float, nullable=True)
    memory_percent = Column(Float)
    disk_percent = Column(Float)
    network_sent_mb = Column(Float)
    network_recv_mb = Column(Float)
    network_speed_sent_mbps = Column(Float, nullable=True)
    network_speed_recv_mbps = Column(Float, nullable=True)
    gpu_percent = Column(Float, nullable=True)
    gpu_memory_percent = Column(Float, nullable=True)
    gpu_memory_used_mb = Column(Float, nullable=True)
    gpu_temp = Column(Float, nullable=True)


class AlertRecord(Base):
    """Alert event stored in database."""

    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    metric_name = Column(String(50))
    threshold_value = Column(Float)
    actual_value = Column(Float)
    message = Column(Text)


class PeakRecord(Base):
    """Historical peak record for metrics."""

    __tablename__ = "peaks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_name = Column(String(50), unique=True)
    peak_value = Column(Float)
    peak_timestamp = Column(DateTime)


class MachineRegistry(Base):
    """Registry of machines connected to the dashboard."""

    __tablename__ = "machines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    machine_id = Column(String(64), unique=True)
    machine_name = Column(String(128))
    last_seen = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(45), nullable=True)


class MachineMetricSnapshot(Base):
    """Latest metrics snapshot for a machine (for multi-machine support)."""

    __tablename__ = "machine_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    machine_id = Column(String(64))
    timestamp = Column(DateTime, default=datetime.utcnow)
    cpu_percent = Column(Float)
    memory_percent = Column(Float)
    disk_percent = Column(Float)
    gpu_percent = Column(Float, nullable=True)
    network_sent_mb = Column(Float)
    network_recv_mb = Column(Float)


class ConfigStore(Base):
    """Persistent configuration store for thresholds and settings."""

    __tablename__ = "config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(64), unique=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow)


engine = create_engine(settings.DATABASE_URL, echo=False)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)


def save_metric(metrics: dict, significant_change: bool = True) -> Optional[MetricRecord]:
    """Save a metric snapshot to the database.

    Args:
        metrics: Dictionary with metric values.
        significant_change: If False, skip saving to reduce DB writes.

    Returns:
        Created database record or None if skipped.
    """
    session = SessionLocal()
    try:
        _update_peaks(session, metrics)
        if not significant_change:
            return None
        record = MetricRecord(
            cpu_percent=metrics["cpu_percent"],
            cpu_temp=metrics.get("cpu_temp"),
            memory_percent=metrics["memory_percent"],
            disk_percent=metrics["disk_percent"],
            network_sent_mb=metrics["network_sent_mb"],
            network_recv_mb=metrics["network_recv_mb"],
            network_speed_sent_mbps=metrics.get("network_speed_sent_mbps"),
            network_speed_recv_mbps=metrics.get("network_speed_recv_mbps"),
            gpu_percent=metrics.get("gpu_percent"),
            gpu_memory_percent=metrics.get("gpu_memory_percent"),
            gpu_memory_used_mb=metrics.get("gpu_memory_used_mb"),
            gpu_temp=metrics.get("gpu_temp"),
        )
        session.add(record)
        session.commit()
        session.refresh(record)
    except Exception:
        session.rollback()
    finally:
        session.close()
    return record


def get_config(key: str, default: str | None = None) -> str | None:
    """Get a configuration value from the database.

    Args:
        key: Configuration key.
        default: Default value if key not found.

    Returns:
        Configuration value or default.
    """
    session = SessionLocal()
    record = session.query(ConfigStore).filter(ConfigStore.key == key).first()
    value = record.value if record else default
    session.close()
    return value


def set_config(key: str, value: str) -> None:
    """Set a configuration value in the database.

    Args:
        key: Configuration key.
        value: Configuration value.
    """
    session = SessionLocal()
    try:
        record = session.query(ConfigStore).filter(ConfigStore.key == key).first()
        if record:
            record.value = value
            record.updated_at = datetime.utcnow()
        else:
            session.add(ConfigStore(key=key, value=value))
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


def _update_peaks(session, metrics: dict) -> None:
    """Update peak records if new highs are detected."""
    peak_metrics = [
        ("cpu_percent", metrics.get("cpu_percent")),
        ("memory_percent", metrics.get("memory_percent")),
        ("disk_percent", metrics.get("disk_percent")),
        ("gpu_percent", metrics.get("gpu_percent")),
    ]
    for name, value in peak_metrics:
        if value is None:
            continue
        existing = session.query(PeakRecord).filter(PeakRecord.metric_name == name).first()
        if existing:
            if value > existing.peak_value:
                existing.peak_value = value
                existing.peak_timestamp = datetime.utcnow()
        else:
            session.add(PeakRecord(metric_name=name, peak_value=value, peak_timestamp=datetime.utcnow()))


def save_alert(alert_message: str, metric_name: str, threshold: float, actual: float) -> AlertRecord:
    """Save an alert event to the database.

    Args:
        alert_message: Human-readable alert message.
        metric_name: Name of the metric that triggered the alert.
        threshold: Threshold value that was exceeded.
        actual: Actual value that triggered the alert.

    Returns:
        Created alert record.
    """
    session = SessionLocal()
    record = AlertRecord(
        metric_name=metric_name,
        threshold_value=threshold,
        actual_value=actual,
        message=alert_message,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    session.close()
    return record


def get_alert_history(hours: int = 24, limit: int = 100) -> list[dict]:
    """Retrieve alert history for the specified time period.

    Args:
        hours: Number of hours to look back.
        limit: Maximum number of records to return.

    Returns:
        List of alert records as dictionaries.
    """
    from datetime import timedelta

    session = SessionLocal()
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    records = (
        session.query(AlertRecord)
        .filter(AlertRecord.timestamp >= cutoff)
        .order_by(AlertRecord.timestamp.desc())
        .limit(limit)
        .all()
    )
    result = [
        {
            "timestamp": r.timestamp.isoformat(),
            "metric_name": r.metric_name,
            "threshold_value": r.threshold_value,
            "actual_value": r.actual_value,
            "message": r.message,
        }
        for r in records
    ]
    session.close()
    return result


def get_peak_records() -> list[dict]:
    """Retrieve all historical peak records.

    Returns:
        List of peak records as dictionaries.
    """
    session = SessionLocal()
    records = session.query(PeakRecord).all()
    result = [
        {
            "metric_name": r.metric_name,
            "peak_value": r.peak_value,
            "peak_timestamp": r.peak_timestamp.isoformat(),
        }
        for r in records
    ]
    session.close()
    return result


def get_history(hours: int = 24) -> list[dict]:
    """Retrieve metric history for the specified time period.

    Args:
        hours: Number of hours to look back.

    Returns:
        List of metric records as dictionaries.
    """
    from datetime import timedelta

    session = SessionLocal()
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    records = (
        session.query(MetricRecord)
        .filter(MetricRecord.timestamp >= cutoff)
        .order_by(MetricRecord.timestamp)
        .all()
    )
    result = [
        {
            "timestamp": r.timestamp.isoformat(),
            "cpu_percent": r.cpu_percent,
            "cpu_temp": r.cpu_temp,
            "memory_percent": r.memory_percent,
            "disk_percent": r.disk_percent,
            "network_sent_mb": r.network_sent_mb,
            "network_recv_mb": r.network_recv_mb,
            "network_speed_sent_mbps": r.network_speed_sent_mbps,
            "network_speed_recv_mbps": r.network_speed_recv_mbps,
            "gpu_percent": r.gpu_percent,
            "gpu_memory_percent": r.gpu_memory_percent,
            "gpu_memory_used_mb": r.gpu_memory_used_mb,
            "gpu_temp": r.gpu_temp,
        }
        for r in records
    ]
    session.close()
    return result


def export_to_csv(records: list[dict]) -> str:
    """Export records to CSV format.

    Args:
        records: List of metric records.

    Returns:
        CSV string.
    """
    output = io.StringIO()
    if not records:
        return ""

    fieldnames = list(records[0].keys())
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(records)
    return output.getvalue()


def export_to_json(records: list[dict]) -> str:
    """Export records to JSON format.

    Args:
        records: List of metric records.

    Returns:
        JSON string.
    """
    return json.dumps(records, indent=2)


def register_machine(machine_id: str, machine_name: str, ip_address: str = None) -> MachineRegistry:
    """Register or update a machine in the registry.

    Args:
        machine_id: Unique machine identifier.
        machine_name: Human-readable machine name.
        ip_address: Optional IP address.

    Returns:
        Created or updated machine record.
    """
    session = SessionLocal()
    existing = session.query(MachineRegistry).filter(MachineRegistry.machine_id == machine_id).first()
    if existing:
        existing.machine_name = machine_name
        existing.last_seen = datetime.utcnow()
        if ip_address:
            existing.ip_address = ip_address
        session.commit()
        session.refresh(existing)
    else:
        record = MachineRegistry(machine_id=machine_id, machine_name=machine_name, ip_address=ip_address)
        session.add(record)
        session.commit()
        session.refresh(record)
    session.close()
    return existing or record


def get_machine_registry() -> list[dict]:
    """Retrieve all registered machines.

    Returns:
        List of machine records as dictionaries.
    """
    session = SessionLocal()
    records = session.query(MachineRegistry).order_by(MachineRegistry.last_seen.desc()).all()
    result = [
        {
            "machine_id": r.machine_id,
            "machine_name": r.machine_name,
            "last_seen": r.last_seen.isoformat(),
            "ip_address": r.ip_address,
        }
        for r in records
    ]
    session.close()
    return result


def get_all_machine_metrics(machine_id: str, limit: int = 100) -> list[dict]:
    """Retrieve latest metrics snapshots for a machine.

    Args:
        machine_id: Unique machine identifier.
        limit: Maximum number of records to return.

    Returns:
        List of metric snapshots as dictionaries.
    """
    session = SessionLocal()
    records = (
        session.query(MachineMetricSnapshot)
        .filter(MachineMetricSnapshot.machine_id == machine_id)
        .order_by(MachineMetricSnapshot.timestamp.desc())
        .limit(limit)
        .all()
    )
    result = [
        {
            "timestamp": r.timestamp.isoformat(),
            "cpu_percent": r.cpu_percent,
            "memory_percent": r.memory_percent,
            "disk_percent": r.disk_percent,
            "gpu_percent": r.gpu_percent,
            "network_sent_mb": r.network_sent_mb,
            "network_recv_mb": r.network_recv_mb,
        }
        for r in records
    ]
    session.close()
    return result


def save_machine_snapshot(machine_id: str, metrics: dict) -> MachineMetricSnapshot:
    """Save a metrics snapshot for a machine.

    Args:
        machine_id: Unique machine identifier.
        metrics: Dictionary with metric values.

    Returns:
        Created snapshot record.
    """
    session = SessionLocal()
    record = MachineMetricSnapshot(
        machine_id=machine_id,
        cpu_percent=metrics.get("cpu_percent"),
        memory_percent=metrics.get("memory_percent"),
        disk_percent=metrics.get("disk_percent"),
        gpu_percent=metrics.get("gpu_percent"),
        network_sent_mb=metrics.get("network_sent_mb"),
        network_recv_mb=metrics.get("network_recv_mb"),
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    session.close()
    return record