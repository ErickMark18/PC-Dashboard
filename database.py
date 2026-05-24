"""Database models for metrics history."""

from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, Float, DateTime
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
    memory_percent = Column(Float)
    disk_percent = Column(Float)
    network_sent_mb = Column(Float)
    network_recv_mb = Column(Float)


engine = create_engine(settings.DATABASE_URL, echo=False)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)


def save_metric(metrics: dict) -> MetricRecord:
    """Save a metric snapshot to the database.

    Args:
        metrics: Dictionary with metric values.

    Returns:
        Created database record.
    """
    session = SessionLocal()
    record = MetricRecord(
        cpu_percent=metrics["cpu_percent"],
        memory_percent=metrics["memory_percent"],
        disk_percent=metrics["disk_percent"],
        network_sent_mb=metrics["network_sent_mb"],
        network_recv_mb=metrics["network_recv_mb"],
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    session.close()
    return record


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
            "memory_percent": r.memory_percent,
            "disk_percent": r.disk_percent,
            "network_sent_mb": r.network_sent_mb,
            "network_recv_mb": r.network_recv_mb,
        }
        for r in records
    ]
    session.close()
    return result