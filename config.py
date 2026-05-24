"""Configuration management for PC Dashboard."""

import secrets
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    CPU_THRESHOLD: float = 90.0
    RAM_THRESHOLD: float = 85.0
    DISK_THRESHOLD: float = 90.0
    TEMP_THRESHOLD: float = 80.0
    GPU_THRESHOLD: float = 90.0
    CHECK_INTERVAL: float = 1.0
    SAVE_INTERVAL: int = 60
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DATABASE_URL: str = "sqlite:///data/metrics.db"
    JWT_SECRET_KEY: str = secrets.token_urlsafe(32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    class Config:
        env_prefix = "DASHBOARD_"


settings = Settings()