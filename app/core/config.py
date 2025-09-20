import os
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import validator, Field
from pydantic_settings import BaseSettings
from decouple import config


class Environment(str, Enum):
    """Application environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class LogLevel(str, Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """
    Application settings with environment-based configuration.

    Supports multiple environments with appropriate defaults and validation.
    All sensitive values should be provided via environment variables.
    """

    # Environment and Application
    ENVIRONMENT: Environment = config("ENVIRONMENT", default=Environment.DEVELOPMENT, cast=Environment)
    APP_NAME: str = config("APP_NAME", default="Travel Legal Alert System")
    APP_VERSION: str = config("APP_VERSION", default="1.0.0")
    DEBUG: bool = config("DEBUG", default=True, cast=bool)
    SECRET_KEY: str = config("SECRET_KEY", default="dev-secret-key-change-in-production")

    # Host Configuration
    HOST: str = config("HOST", default="0.0.0.0")
    PORT: int = config("PORT", default=8000, cast=int)
    ALLOWED_HOSTS: str = Field(default="*")

    # Database Configuration
    DATABASE_URL: str = config("DATABASE_URL", default="postgresql+asyncpg://postgres:password@localhost:5432/travel_alerts")
    DB_POOL_SIZE: int = config("DB_POOL_SIZE", default=20, cast=int)
    DB_MAX_OVERFLOW: int = config("DB_MAX_OVERFLOW", default=30, cast=int)
    DB_POOL_TIMEOUT: int = config("DB_POOL_TIMEOUT", default=30, cast=int)
    DB_POOL_RECYCLE: int = config("DB_POOL_RECYCLE", default=3600, cast=int)
    DB_ECHO: bool = config("DB_ECHO", default=False, cast=bool)

    # Redis Configuration
    REDIS_URL: str = config("REDIS_URL", default="redis://localhost:6379/0")
    REDIS_POOL_SIZE: int = config("REDIS_POOL_SIZE", default=20, cast=int)
    REDIS_TIMEOUT: int = config("REDIS_TIMEOUT", default=5, cast=int)
    REDIS_RETRY_ON_TIMEOUT: bool = config("REDIS_RETRY_ON_TIMEOUT", default=True, cast=bool)

    # Cache Configuration
    CACHE_TTL: int = config("CACHE_TTL", default=3600, cast=int)
    CACHE_KEY_PREFIX: str = config("CACHE_KEY_PREFIX", default="travel_alerts")

    # Authentication & Security
    JWT_SECRET_KEY: str = config("JWT_SECRET_KEY", default="jwt-secret-key-change-in-production")
    JWT_ALGORITHM: str = config("JWT_ALGORITHM", default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = config("ACCESS_TOKEN_EXPIRE_MINUTES", default=30, cast=int)
    REFRESH_TOKEN_EXPIRE_DAYS: int = config("REFRESH_TOKEN_EXPIRE_DAYS", default=7, cast=int)

    # Security Headers
    SECURITY_HEADERS_ENABLED: bool = config("SECURITY_HEADERS_ENABLED", default=True, cast=bool)
    HSTS_MAX_AGE: int = config("HSTS_MAX_AGE", default=31536000, cast=int)  # 1 year

    # External API Configuration
    US_STATE_DEPT_API_KEY: Optional[str] = config("US_STATE_DEPT_API_KEY", default=None)
    UK_FOREIGN_OFFICE_API_KEY: Optional[str] = config("UK_FOREIGN_OFFICE_API_KEY", default=None)
    NEWS_API_KEY: Optional[str] = config("NEWS_API_KEY", default=None)

    # API Rate Limiting
    API_RATE_LIMIT_ENABLED: bool = config("API_RATE_LIMIT_ENABLED", default=True, cast=bool)
    API_RATE_LIMIT_PER_MINUTE: int = config("API_RATE_LIMIT_PER_MINUTE", default=100, cast=int)
    API_RATE_LIMIT_BURST: int = config("API_RATE_LIMIT_BURST", default=20, cast=int)

    # Monitoring and Metrics
    METRICS_ENABLED: bool = config("METRICS_ENABLED", default=True, cast=bool)
    METRICS_PATH: str = config("METRICS_PATH", default="/metrics")
    HEALTH_CHECK_PATH: str = config("HEALTH_CHECK_PATH", default="/health")

    # Logging Configuration
    LOG_LEVEL: LogLevel = config("LOG_LEVEL", default=LogLevel.INFO, cast=LogLevel)
    LOG_FORMAT: str = config("LOG_FORMAT", default="json")
    LOG_FILE: Optional[str] = config("LOG_FILE", default=None)
    LOG_ROTATION_SIZE: str = config("LOG_ROTATION_SIZE", default="100MB")
    LOG_RETENTION_DAYS: int = config("LOG_RETENTION_DAYS", default=30, cast=int)

    # CORS Configuration
    CORS_ENABLED: bool = config("CORS_ENABLED", default=True, cast=bool)
    CORS_ORIGINS: str = Field(default="*")
    CORS_ALLOW_CREDENTIALS: bool = config("CORS_ALLOW_CREDENTIALS", default=True, cast=bool)
    CORS_ALLOW_METHODS: str = Field(default="GET,POST,PUT,DELETE,PATCH,OPTIONS")
    CORS_ALLOW_HEADERS: str = Field(default="*")

    # Worker Configuration (for Celery/background tasks)
    WORKER_CONCURRENCY: int = config("WORKER_CONCURRENCY", default=4, cast=int)
    WORKER_MAX_TASKS_PER_CHILD: int = config("WORKER_MAX_TASKS_PER_CHILD", default=1000, cast=int)

    # Performance Tuning
    REQUEST_TIMEOUT: int = config("REQUEST_TIMEOUT", default=30, cast=int)
    KEEPALIVE_TIMEOUT: int = config("KEEPALIVE_TIMEOUT", default=5, cast=int)
    MAX_REQUEST_SIZE: int = config("MAX_REQUEST_SIZE", default=16777216, cast=int)  # 16MB

    # Feature Flags
    ENABLE_SCRAPING: bool = config("ENABLE_SCRAPING", default=True, cast=bool)
    ENABLE_API_CLIENTS: bool = config("ENABLE_API_CLIENTS", default=True, cast=bool)
    ENABLE_NOTIFICATIONS: bool = config("ENABLE_NOTIFICATIONS", default=True, cast=bool)
    ENABLE_LOCATION_PROCESSING: bool = config("ENABLE_LOCATION_PROCESSING", default=True, cast=bool)

    # Notification Services
    NOTIFICATION_EMAIL_ENABLED: bool = config("NOTIFICATION_EMAIL_ENABLED", default=False, cast=bool)
    NOTIFICATION_SMS_ENABLED: bool = config("NOTIFICATION_SMS_ENABLED", default=False, cast=bool)
    NOTIFICATION_PUSH_ENABLED: bool = config("NOTIFICATION_PUSH_ENABLED", default=True, cast=bool)

    # Email Configuration
    SMTP_HOST: Optional[str] = config("SMTP_HOST", default=None)
    SMTP_PORT: int = config("SMTP_PORT", default=587, cast=int)
    SMTP_USER: Optional[str] = config("SMTP_USER", default=None)
    SMTP_PASSWORD: Optional[str] = config("SMTP_PASSWORD", default=None)
    SMTP_TLS: bool = config("SMTP_TLS", default=True, cast=bool)

    # SMS Configuration
    TWILIO_ACCOUNT_SID: Optional[str] = config("TWILIO_ACCOUNT_SID", default=None)
    TWILIO_AUTH_TOKEN: Optional[str] = config("TWILIO_AUTH_TOKEN", default=None)
    TWILIO_FROM_NUMBER: Optional[str] = config("TWILIO_FROM_NUMBER", default=None)

    # Push Notification Configuration
    FCM_SERVER_KEY: Optional[str] = config("FCM_SERVER_KEY", default=None)
    APNS_KEY_ID: Optional[str] = config("APNS_KEY_ID", default=None)
    APNS_TEAM_ID: Optional[str] = config("APNS_TEAM_ID", default=None)

    # Sentry Configuration
    SENTRY_DSN: Optional[str] = config("SENTRY_DSN", default=None)
    SENTRY_ENVIRONMENT: Optional[str] = config("SENTRY_ENVIRONMENT", default=None)
    SENTRY_TRACES_SAMPLE_RATE: float = config("SENTRY_TRACES_SAMPLE_RATE", default=0.1, cast=float)


    @property
    def allowed_hosts_list(self) -> List[str]:
        """Get allowed hosts as a list."""
        if isinstance(self.ALLOWED_HOSTS, str):
            return [i.strip() for i in self.ALLOWED_HOSTS.split(",") if i.strip()]
        return [self.ALLOWED_HOSTS] if self.ALLOWED_HOSTS else ["*"]


    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == Environment.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == Environment.PRODUCTION

    @property
    def is_staging(self) -> bool:
        """Check if running in staging environment."""
        return self.ENVIRONMENT == Environment.STAGING

    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.ENVIRONMENT == Environment.TESTING

    def get_database_url(self) -> str:
        """Get the database URL with proper formatting."""
        return self.DATABASE_URL

    def get_redis_url(self) -> str:
        """Get the Redis URL with proper formatting."""
        return self.REDIS_URL

    def get_cors_origins(self) -> List[str]:
        """Get CORS origins, with wildcard handling for development."""
        if isinstance(self.CORS_ORIGINS, str):
            origins = [i.strip() for i in self.CORS_ORIGINS.split(",") if i.strip()]
        else:
            origins = [self.CORS_ORIGINS]
        
        if self.is_development and "*" in origins:
            return ["*"]
        return [origin for origin in origins if origin != "*"]

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"
        use_enum_values = True
        extra = "ignore"  # Ignore extra fields from .env


# Create settings instance
settings = Settings()


def get_environment_settings() -> Dict[str, Any]:
    """Get environment-specific settings for debugging and monitoring."""
    return {
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "is_production": settings.is_production,
        "database_configured": bool(settings.DATABASE_URL),
        "redis_configured": bool(settings.REDIS_URL),
        "cors_enabled": settings.CORS_ENABLED,
        "metrics_enabled": settings.METRICS_ENABLED,
        "security_headers_enabled": settings.SECURITY_HEADERS_ENABLED,
        "features": {
            "scraping": settings.ENABLE_SCRAPING,
            "api_clients": settings.ENABLE_API_CLIENTS,
            "notifications": settings.ENABLE_NOTIFICATIONS,
            "location_processing": settings.ENABLE_LOCATION_PROCESSING,
        }
    }