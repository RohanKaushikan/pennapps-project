import sys
import json
import logging
import logging.config
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

import structlog
from structlog.types import EventDict, Processor
from pythonjsonlogger import jsonlogger

from app.core.config import settings


class RequestContextFilter(logging.Filter):
    """Add request context to log records."""

    def filter(self, record):
        # Add request ID if available from context
        if hasattr(record, 'request_id'):
            record.request_id = getattr(record, 'request_id', 'N/A')
        else:
            record.request_id = 'N/A'

        # Add user ID if available from context
        if hasattr(record, 'user_id'):
            record.user_id = getattr(record, 'user_id', 'anonymous')
        else:
            record.user_id = 'anonymous'

        return True


class CustomJSONFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)

        # Add timestamp
        if not log_record.get('timestamp'):
            log_record['timestamp'] = datetime.utcnow().isoformat()

        # Add environment
        log_record['environment'] = settings.ENVIRONMENT
        log_record['service'] = settings.APP_NAME
        log_record['version'] = settings.APP_VERSION

        # Add level name if not present
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname


def performance_processor(logger, method_name, event_dict: EventDict) -> EventDict:
    """Add performance metrics to structured logs."""
    # Add performance markers
    if 'duration_ms' in event_dict:
        duration = event_dict['duration_ms']
        if duration > 1000:
            event_dict['performance'] = 'slow'
        elif duration > 500:
            event_dict['performance'] = 'medium'
        else:
            event_dict['performance'] = 'fast'

    return event_dict


def security_processor(logger, method_name, event_dict: EventDict) -> EventDict:
    """Add security context to logs."""
    # Mark security-related events
    security_keywords = ['auth', 'login', 'permission', 'access', 'security', 'token']

    event_string = str(event_dict).lower()
    if any(keyword in event_string for keyword in security_keywords):
        event_dict['security_related'] = True

    return event_dict


def error_processor(logger, method_name, event_dict: EventDict) -> EventDict:
    """Process error events with additional context."""
    if 'exception' in event_dict or 'error' in event_dict:
        event_dict['error_category'] = 'application_error'

        # Add error classification
        error_msg = str(event_dict.get('exception', event_dict.get('error', ''))).lower()

        if 'database' in error_msg or 'connection' in error_msg:
            event_dict['error_type'] = 'database_error'
        elif 'api' in error_msg or 'request' in error_msg:
            event_dict['error_type'] = 'api_error'
        elif 'validation' in error_msg:
            event_dict['error_type'] = 'validation_error'
        else:
            event_dict['error_type'] = 'unknown_error'

    return event_dict


def get_logging_config() -> Dict[str, Any]:
    """Get logging configuration based on environment settings."""

    # Base configuration
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'json': {
                '()': CustomJSONFormatter,
                'format': '%(timestamp)s %(level)s %(name)s %(message)s %(request_id)s %(user_id)s'
            },
            'console': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'filters': {
            'request_context': {
                '()': RequestContextFilter,
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': settings.LOG_LEVEL if isinstance(settings.LOG_LEVEL, str) else settings.LOG_LEVEL.value,
                'formatter': 'json' if settings.LOG_FORMAT == 'json' else 'console',
                'filters': ['request_context'],
                'stream': sys.stdout
            }
        },
        'loggers': {
            '': {  # Root logger
                'handlers': ['console'],
                'level': settings.LOG_LEVEL if isinstance(settings.LOG_LEVEL, str) else settings.LOG_LEVEL.value,
                'propagate': False
            },
            'app': {
                'handlers': ['console'],
                'level': settings.LOG_LEVEL if isinstance(settings.LOG_LEVEL, str) else settings.LOG_LEVEL.value,
                'propagate': False
            },
            'uvicorn': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False
            },
            'uvicorn.access': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False
            },
            'sqlalchemy.engine': {
                'handlers': ['console'],
                'level': 'WARNING',
                'propagate': False
            },
            'alembic': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False
            }
        }
    }

    # Add file handler if log file is specified
    if settings.LOG_FILE:
        log_file_path = Path(settings.LOG_FILE)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

        config['handlers']['file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': settings.LOG_LEVEL if isinstance(settings.LOG_LEVEL, str) else settings.LOG_LEVEL.value,
            'formatter': 'json',
            'filters': ['request_context'],
            'filename': str(log_file_path),
            'maxBytes': _parse_size(settings.LOG_ROTATION_SIZE),
            'backupCount': settings.LOG_RETENTION_DAYS,
            'encoding': 'utf-8'
        }

        # Add file handler to all loggers
        for logger_config in config['loggers'].values():
            logger_config['handlers'].append('file')

    return config


def _parse_size(size_str: str) -> int:
    """Parse size string like '100MB' to bytes."""
    size_str = size_str.upper()
    if size_str.endswith('KB'):
        return int(size_str[:-2]) * 1024
    elif size_str.endswith('MB'):
        return int(size_str[:-2]) * 1024 * 1024
    elif size_str.endswith('GB'):
        return int(size_str[:-2]) * 1024 * 1024 * 1024
    else:
        return int(size_str)


def configure_logging():
    """Configure both standard and structured logging."""

    # Configure standard Python logging
    logging_config = get_logging_config()
    logging.config.dictConfig(logging_config)

    # Configure structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="ISO"),
        performance_processor,
        security_processor,
        error_processor,
    ]

    if settings.LOG_FORMAT == 'json':
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.extend([
            structlog.dev.ConsoleRenderer(colors=settings.is_development),
        ])

    log_level = settings.LOG_LEVEL if isinstance(settings.LOG_LEVEL, str) else settings.LOG_LEVEL.value
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level)
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


class LoggingMiddleware:
    """Middleware for request/response logging."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Generate request ID
        import uuid
        request_id = str(uuid.uuid4())

        # Add request context
        with structlog.contextvars.bound_contextvars(
            request_id=request_id,
            path=scope.get("path", ""),
            method=scope.get("method", ""),
            client_ip=scope.get("client", ["unknown", None])[0]
        ):
            logger = structlog.get_logger("app.middleware")

            # Log request start
            logger.info(
                "Request started",
                request_id=request_id,
                path=scope.get("path"),
                method=scope.get("method"),
                user_agent=dict(scope.get("headers", {})).get(b"user-agent", b"").decode()
            )

            import time
            start_time = time.time()

            # Process request
            await self.app(scope, receive, send)

            # Log request completion
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "Request completed",
                request_id=request_id,
                duration_ms=round(duration_ms, 2)
            )


class PerformanceLogger:
    """Context manager for performance logging."""

    def __init__(self, operation: str, logger: Optional[structlog.BoundLogger] = None):
        self.operation = operation
        self.logger = logger or structlog.get_logger()
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.debug(f"Starting {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds() * 1000

        if exc_type:
            self.logger.error(
                f"Failed {self.operation}",
                duration_ms=round(duration, 2),
                exception=str(exc_val)
            )
        else:
            self.logger.info(
                f"Completed {self.operation}",
                duration_ms=round(duration, 2)
            )


class DatabaseQueryLogger:
    """Logger for database query performance."""

    @staticmethod
    def log_query(query: str, parameters: Dict[str, Any], duration_ms: float):
        """Log database query with performance metrics."""
        logger = structlog.get_logger("app.database")

        # Sanitize query for logging (remove sensitive data)
        sanitized_query = query.replace('\n', ' ').strip()
        if len(sanitized_query) > 200:
            sanitized_query = sanitized_query[:200] + "..."

        log_data = {
            "query": sanitized_query,
            "duration_ms": round(duration_ms, 2),
            "parameter_count": len(parameters) if parameters else 0
        }

        # Add performance classification
        if duration_ms > 1000:
            logger.warning("Slow database query", **log_data)
        elif duration_ms > 500:
            logger.info("Medium duration database query", **log_data)
        else:
            logger.debug("Database query", **log_data)


class SecurityLogger:
    """Logger for security-related events."""

    @staticmethod
    def log_authentication_attempt(user_id: str, success: bool, ip_address: str, user_agent: str):
        """Log authentication attempts."""
        logger = structlog.get_logger("app.security")

        logger.info(
            "Authentication attempt",
            user_id=user_id,
            success=success,
            ip_address=ip_address,
            user_agent=user_agent,
            security_related=True,
            event_type="authentication"
        )

    @staticmethod
    def log_authorization_failure(user_id: str, resource: str, action: str, ip_address: str):
        """Log authorization failures."""
        logger = structlog.get_logger("app.security")

        logger.warning(
            "Authorization failure",
            user_id=user_id,
            resource=resource,
            action=action,
            ip_address=ip_address,
            security_related=True,
            event_type="authorization_failure"
        )

    @staticmethod
    def log_suspicious_activity(event_type: str, details: Dict[str, Any], ip_address: str):
        """Log suspicious activities."""
        logger = structlog.get_logger("app.security")

        logger.warning(
            "Suspicious activity detected",
            event_type=event_type,
            ip_address=ip_address,
            security_related=True,
            **details
        )


class ErrorLogger:
    """Logger for application errors with context."""

    @staticmethod
    def log_application_error(error: Exception, context: Optional[Dict[str, Any]] = None):
        """Log application errors with full context."""
        logger = structlog.get_logger("app.errors")

        error_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "error_category": "application_error"
        }

        if context:
            error_data.update(context)

        logger.error("Application error occurred", **error_data, exception=error)

    @staticmethod
    def log_external_api_error(api_name: str, error: Exception, endpoint: str, response_code: Optional[int] = None):
        """Log external API errors."""
        logger = structlog.get_logger("app.external_apis")

        logger.error(
            "External API error",
            api_name=api_name,
            endpoint=endpoint,
            response_code=response_code,
            error_message=str(error),
            error_category="external_api_error"
        )


# Global loggers for easy access
performance_logger = PerformanceLogger
db_logger = DatabaseQueryLogger()
security_logger = SecurityLogger()
error_logger = ErrorLogger()


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


def setup_sentry_logging():
    """Setup Sentry integration if configured."""
    if not settings.SENTRY_DSN:
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
        from sentry_sdk.integrations.httpx import HttpxIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.SENTRY_ENVIRONMENT or settings.ENVIRONMENT,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            release=f"{settings.APP_NAME}@{settings.APP_VERSION}",
            integrations=[
                SqlalchemyIntegration(),
                RedisIntegration(),
                HttpxIntegration()
            ],
            # Don't send sensitive data
            send_default_pii=False,
            # Include local variables in error reports (development only)
            include_local_variables=settings.is_development,
            # Performance monitoring
            profiles_sample_rate=0.1 if settings.is_production else 0.0,
        )

        logger = get_logger("app.sentry")
        logger.info("Sentry logging initialized", dsn_configured=True)

    except ImportError:
        logger = get_logger("app.sentry")
        logger.warning("Sentry SDK not installed, skipping Sentry integration")
    except Exception as e:
        logger = get_logger("app.sentry")
        logger.error("Failed to initialize Sentry", error=str(e))


# Initialize logging on module import
if not getattr(configure_logging, '_configured', False):
    configure_logging()
    setup_sentry_logging()
    configure_logging._configured = True