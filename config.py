"""Configuration management for PC Dashboard."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    CPU_THRESHOLD: float = 90.0
    RAM_THRESHOLD: float = 85.0
    DISK_THRESHOLD: float = 90.0
    TEMP_THRESHOLD: float = 80.0
    CHECK_INTERVAL: float = 1.0
    SAVE_INTERVAL: int = 60
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DATABASE_URL: str = "sqlite:///data/metrics.db"

    class Config:
        env_prefix = "DASHBOARD_"


settings = Settings()