import time
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import threading

from prometheus_client import (
    Counter, Histogram, Gauge, Info, Summary,
    CollectorRegistry, generate_latest,
    CONTENT_TYPE_LATEST, REGISTRY
)
from prometheus_client.multiprocess import MultiProcessCollector

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.metrics")


class MetricType(str, Enum):
    """Types of metrics."""
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    GAUGE = "gauge"
    SUMMARY = "summary"
    INFO = "info"


class ApplicationMetrics:
    """
    Comprehensive metrics collection for the application.

    Provides Prometheus-compatible metrics for monitoring application
    performance, business metrics, and system health.
    """

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or REGISTRY
        self._lock = threading.Lock()
        self._custom_metrics: Dict[str, Any] = {}
        self._request_durations = deque(maxlen=1000)  # Keep last 1000 request times

        # Initialize core metrics
        self._init_http_metrics()
        self._init_database_metrics()
        self._init_cache_metrics()
        self._init_business_metrics()
        self._init_system_metrics()
        self._init_external_api_metrics()

    def _init_http_metrics(self):
        """Initialize HTTP request metrics."""
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )

        self.http_request_duration_seconds = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry
        )

        self.http_requests_in_progress = Gauge(
            'http_requests_in_progress',
            'Current HTTP requests in progress',
            registry=self.registry
        )

        self.http_request_size_bytes = Histogram(
            'http_request_size_bytes',
            'HTTP request size in bytes',
            buckets=[100, 1000, 10000, 100000, 1000000],
            registry=self.registry
        )

        self.http_response_size_bytes = Histogram(
            'http_response_size_bytes',
            'HTTP response size in bytes',
            buckets=[100, 1000, 10000, 100000, 1000000],
            registry=self.registry
        )

    def _init_database_metrics(self):
        """Initialize database metrics."""
        self.db_connections_active = Gauge(
            'db_connections_active',
            'Active database connections',
            registry=self.registry
        )

        self.db_connections_idle = Gauge(
            'db_connections_idle',
            'Idle database connections',
            registry=self.registry
        )

        self.db_query_duration_seconds = Histogram(
            'db_query_duration_seconds',
            'Database query duration in seconds',
            ['operation'],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
            registry=self.registry
        )

        self.db_queries_total = Counter(
            'db_queries_total',
            'Total database queries',
            ['operation', 'status'],
            registry=self.registry
        )

        self.db_connection_errors_total = Counter(
            'db_connection_errors_total',
            'Total database connection errors',
            ['error_type'],
            registry=self.registry
        )

    def _init_cache_metrics(self):
        """Initialize cache metrics."""
        self.cache_operations_total = Counter(
            'cache_operations_total',
            'Total cache operations',
            ['operation', 'status'],  # get, set, delete / hit, miss, error
            registry=self.registry
        )

        self.cache_hit_ratio = Gauge(
            'cache_hit_ratio',
            'Cache hit ratio (0-1)',
            registry=self.registry
        )

        self.cache_size_bytes = Gauge(
            'cache_size_bytes',
            'Cache size in bytes',
            registry=self.registry
        )

        self.cache_operation_duration_seconds = Histogram(
            'cache_operation_duration_seconds',
            'Cache operation duration in seconds',
            ['operation'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25],
            registry=self.registry
        )

    def _init_business_metrics(self):
        """Initialize business-specific metrics."""
        self.scraping_jobs_total = Counter(
            'scraping_jobs_total',
            'Total scraping jobs',
            ['source', 'status'],
            registry=self.registry
        )

        self.scraping_job_duration_seconds = Histogram(
            'scraping_job_duration_seconds',
            'Scraping job duration in seconds',
            ['source'],
            buckets=[10, 30, 60, 180, 300, 600, 1800],
            registry=self.registry
        )

        self.travel_advisories_processed_total = Counter(
            'travel_advisories_processed_total',
            'Total travel advisories processed',
            ['source', 'country'],
            registry=self.registry
        )

        self.location_events_total = Counter(
            'location_events_total',
            'Total location events processed',
            ['event_type', 'country'],
            registry=self.registry
        )

        self.alerts_sent_total = Counter(
            'alerts_sent_total',
            'Total alerts sent',
            ['alert_type', 'severity', 'channel'],
            registry=self.registry
        )

        self.alert_delivery_duration_seconds = Histogram(
            'alert_delivery_duration_seconds',
            'Alert delivery duration in seconds',
            ['channel'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
            registry=self.registry
        )

        self.active_users = Gauge(
            'active_users',
            'Number of active users',
            ['time_window'],  # 1h, 24h, 7d
            registry=self.registry
        )

    def _init_system_metrics(self):
        """Initialize system metrics."""
        self.application_info = Info(
            'application_info',
            'Application information',
            registry=self.registry
        )

        # Set application info
        self.application_info.info({
            'name': settings.APP_NAME,
            'version': settings.APP_VERSION,
            'environment': settings.ENVIRONMENT
        })

        self.application_start_time = Gauge(
            'application_start_time',
            'Application start time in Unix timestamp',
            registry=self.registry
        )
        self.application_start_time.set_to_current_time()

        self.memory_usage_bytes = Gauge(
            'memory_usage_bytes',
            'Memory usage in bytes',
            ['type'],  # rss, vms, shared
            registry=self.registry
        )

        self.cpu_usage_percent = Gauge(
            'cpu_usage_percent',
            'CPU usage percentage',
            registry=self.registry
        )

        self.background_tasks_active = Gauge(
            'background_tasks_active',
            'Number of active background tasks',
            ['task_type'],
            registry=self.registry
        )

    def _init_external_api_metrics(self):
        """Initialize external API metrics."""
        self.external_api_requests_total = Counter(
            'external_api_requests_total',
            'Total external API requests',
            ['api_name', 'status_code'],
            registry=self.registry
        )

        self.external_api_duration_seconds = Histogram(
            'external_api_duration_seconds',
            'External API request duration in seconds',
            ['api_name'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
            registry=self.registry
        )

        self.external_api_errors_total = Counter(
            'external_api_errors_total',
            'Total external API errors',
            ['api_name', 'error_type'],
            registry=self.registry
        )

        self.circuit_breaker_state = Gauge(
            'circuit_breaker_state',
            'Circuit breaker state (0=closed, 1=open, 0.5=half-open)',
            ['api_name'],
            registry=self.registry
        )

    # HTTP Metrics Methods
    def record_http_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration_seconds: float,
        request_size_bytes: Optional[int] = None,
        response_size_bytes: Optional[int] = None
    ):
        """Record HTTP request metrics."""
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code
        ).inc()

        self.http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration_seconds)

        if request_size_bytes is not None:
            self.http_request_size_bytes.observe(request_size_bytes)

        if response_size_bytes is not None:
            self.http_response_size_bytes.observe(response_size_bytes)

        # Track request durations for statistics
        with self._lock:
            self._request_durations.append(duration_seconds)

    def increment_http_requests_in_progress(self):
        """Increment HTTP requests in progress counter."""
        self.http_requests_in_progress.inc()

    def decrement_http_requests_in_progress(self):
        """Decrement HTTP requests in progress counter."""
        self.http_requests_in_progress.dec()

    # Database Metrics Methods
    def record_db_query(
        self,
        operation: str,
        duration_seconds: float,
        success: bool = True
    ):
        """Record database query metrics."""
        status = "success" if success else "error"

        self.db_queries_total.labels(
            operation=operation,
            status=status
        ).inc()

        self.db_query_duration_seconds.labels(
            operation=operation
        ).observe(duration_seconds)

    def update_db_connection_metrics(self, active: int, idle: int):
        """Update database connection pool metrics."""
        self.db_connections_active.set(active)
        self.db_connections_idle.set(idle)

    def record_db_connection_error(self, error_type: str):
        """Record database connection error."""
        self.db_connection_errors_total.labels(
            error_type=error_type
        ).inc()

    # Cache Metrics Methods
    def record_cache_operation(
        self,
        operation: str,  # get, set, delete
        status: str,     # hit, miss, error
        duration_seconds: float
    ):
        """Record cache operation metrics."""
        self.cache_operations_total.labels(
            operation=operation,
            status=status
        ).inc()

        self.cache_operation_duration_seconds.labels(
            operation=operation
        ).observe(duration_seconds)

    def update_cache_hit_ratio(self, ratio: float):
        """Update cache hit ratio (0-1)."""
        self.cache_hit_ratio.set(ratio)

    def update_cache_size(self, size_bytes: int):
        """Update cache size in bytes."""
        self.cache_size_bytes.set(size_bytes)

    # Business Metrics Methods
    def record_scraping_job(
        self,
        source: str,
        status: str,
        duration_seconds: float
    ):
        """Record scraping job metrics."""
        self.scraping_jobs_total.labels(
            source=source,
            status=status
        ).inc()

        self.scraping_job_duration_seconds.labels(
            source=source
        ).observe(duration_seconds)

    def record_travel_advisory(self, source: str, country: str):
        """Record travel advisory processing."""
        self.travel_advisories_processed_total.labels(
            source=source,
            country=country
        ).inc()

    def record_location_event(self, event_type: str, country: str):
        """Record location event processing."""
        self.location_events_total.labels(
            event_type=event_type,
            country=country
        ).inc()

    def record_alert_sent(
        self,
        alert_type: str,
        severity: str,
        channel: str,
        delivery_duration_seconds: float
    ):
        """Record alert delivery metrics."""
        self.alerts_sent_total.labels(
            alert_type=alert_type,
            severity=severity,
            channel=channel
        ).inc()

        self.alert_delivery_duration_seconds.labels(
            channel=channel
        ).observe(delivery_duration_seconds)

    def update_active_users(self, time_window: str, count: int):
        """Update active users gauge."""
        self.active_users.labels(time_window=time_window).set(count)

    # External API Metrics Methods
    def record_external_api_request(
        self,
        api_name: str,
        status_code: int,
        duration_seconds: float,
        success: bool = True
    ):
        """Record external API request metrics."""
        self.external_api_requests_total.labels(
            api_name=api_name,
            status_code=status_code
        ).inc()

        self.external_api_duration_seconds.labels(
            api_name=api_name
        ).observe(duration_seconds)

        if not success:
            self.external_api_errors_total.labels(
                api_name=api_name,
                error_type="http_error"
            ).inc()

    def record_external_api_error(self, api_name: str, error_type: str):
        """Record external API error."""
        self.external_api_errors_total.labels(
            api_name=api_name,
            error_type=error_type
        ).inc()

    def update_circuit_breaker_state(self, api_name: str, state: str):
        """Update circuit breaker state."""
        state_mapping = {
            "closed": 0.0,
            "open": 1.0,
            "half-open": 0.5
        }
        self.circuit_breaker_state.labels(
            api_name=api_name
        ).set(state_mapping.get(state, 0.0))

    # System Metrics Methods
    def update_system_metrics(self):
        """Update system resource metrics."""
        try:
            import psutil
            import os

            # Memory metrics
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()

            self.memory_usage_bytes.labels(type="rss").set(memory_info.rss)
            self.memory_usage_bytes.labels(type="vms").set(memory_info.vms)

            # CPU metrics
            cpu_percent = process.cpu_percent()
            self.cpu_usage_percent.set(cpu_percent)

        except ImportError:
            logger.warning("psutil not available for system metrics")
        except Exception as e:
            logger.error("Error updating system metrics", error=str(e))

    def update_background_tasks(self, task_type: str, count: int):
        """Update background tasks gauge."""
        self.background_tasks_active.labels(task_type=task_type).set(count)

    # Custom Metrics Methods
    def create_custom_metric(
        self,
        name: str,
        metric_type: MetricType,
        description: str,
        labels: Optional[List[str]] = None,
        **kwargs
    ):
        """Create a custom metric."""
        if name in self._custom_metrics:
            logger.warning(f"Custom metric {name} already exists")
            return self._custom_metrics[name]

        labels = labels or []

        if metric_type == MetricType.COUNTER:
            metric = Counter(name, description, labels, registry=self.registry)
        elif metric_type == MetricType.HISTOGRAM:
            buckets = kwargs.get('buckets', [0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0])
            metric = Histogram(name, description, labels, buckets=buckets, registry=self.registry)
        elif metric_type == MetricType.GAUGE:
            metric = Gauge(name, description, labels, registry=self.registry)
        elif metric_type == MetricType.SUMMARY:
            metric = Summary(name, description, labels, registry=self.registry)
        elif metric_type == MetricType.INFO:
            metric = Info(name, description, registry=self.registry)
        else:
            raise ValueError(f"Unsupported metric type: {metric_type}")

        self._custom_metrics[name] = metric
        logger.info(f"Created custom metric: {name} ({metric_type})")
        return metric

    def get_custom_metric(self, name: str):
        """Get a custom metric by name."""
        return self._custom_metrics.get(name)

    # Statistics and Reporting
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        with self._lock:
            durations = list(self._request_durations)

        if not durations:
            return {}

        durations.sort()
        length = len(durations)

        return {
            "request_count": length,
            "avg_duration_ms": sum(durations) * 1000 / length,
            "p50_duration_ms": durations[int(length * 0.5)] * 1000,
            "p90_duration_ms": durations[int(length * 0.9)] * 1000,
            "p95_duration_ms": durations[int(length * 0.95)] * 1000,
            "p99_duration_ms": durations[int(length * 0.99)] * 1000,
            "min_duration_ms": durations[0] * 1000,
            "max_duration_ms": durations[-1] * 1000
        }

    def generate_metrics(self) -> str:
        """Generate Prometheus metrics in text format."""
        return generate_latest(self.registry).decode('utf-8')

    def get_content_type(self) -> str:
        """Get the content type for metrics endpoint."""
        return CONTENT_TYPE_LATEST


class MetricsMiddleware:
    """Middleware for automatic HTTP metrics collection."""

    def __init__(self, app, metrics: ApplicationMetrics):
        self.app = app
        self.metrics = metrics

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")
        path = scope.get("path", "")

        # Skip metrics endpoint to avoid recursion
        if path == settings.METRICS_PATH:
            await self.app(scope, receive, send)
            return

        # Normalize endpoint path (remove query parameters, IDs, etc.)
        endpoint = self._normalize_endpoint(path)

        self.metrics.increment_http_requests_in_progress()
        start_time = time.time()

        try:
            # Get request size if available
            request_size = 0
            if "content-length" in dict(scope.get("headers", [])):
                try:
                    request_size = int(dict(scope["headers"])[b"content-length"])
                except (ValueError, KeyError):
                    pass

            # Process request
            status_code = 200
            response_size = 0

            async def send_wrapper(message):
                nonlocal status_code, response_size
                if message["type"] == "http.response.start":
                    status_code = message.get("status", 200)
                elif message["type"] == "http.response.body":
                    body = message.get("body", b"")
                    response_size += len(body)
                await send(message)

            await self.app(scope, receive, send_wrapper)

            # Record metrics
            duration = time.time() - start_time
            self.metrics.record_http_request(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                duration_seconds=duration,
                request_size_bytes=request_size,
                response_size_bytes=response_size
            )

        except Exception as e:
            # Record error metrics
            duration = time.time() - start_time
            self.metrics.record_http_request(
                method=method,
                endpoint=endpoint,
                status_code=500,
                duration_seconds=duration
            )
            raise

        finally:
            self.metrics.decrement_http_requests_in_progress()

    def _normalize_endpoint(self, path: str) -> str:
        """Normalize endpoint path for metrics."""
        # Remove query parameters
        if "?" in path:
            path = path.split("?")[0]

        # Replace common ID patterns
        import re

        # UUID patterns
        path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{id}', path)

        # Numeric IDs
        path = re.sub(r'/\d+', '/{id}', path)

        # Common patterns
        path = re.sub(r'/[A-Z]{2,3}$', '/{country_code}', path)  # Country codes

        return path


# Global metrics instance
app_metrics = ApplicationMetrics()


def get_metrics() -> ApplicationMetrics:
    """Get the global metrics instance."""
    return app_metrics


async def update_system_metrics_periodically():
    """Periodically update system metrics in the background."""
    while True:
        try:
            app_metrics.update_system_metrics()
            await asyncio.sleep(30)  # Update every 30 seconds
        except Exception as e:
            logger.error("Error updating system metrics", error=str(e))
            await asyncio.sleep(60)  # Wait longer on error