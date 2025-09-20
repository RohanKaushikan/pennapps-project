import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
from dataclasses import dataclass, field
import structlog
from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.scraping_job import ScrapingJob, JobStatus

logger = structlog.get_logger(__name__)


@dataclass
class APIMetrics:
    """Metrics for API performance tracking."""
    source: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    rate_limit_hits: int = 0
    circuit_breaker_opens: int = 0
    last_request_time: Optional[datetime] = None
    error_types: Dict[str, int] = field(default_factory=dict)
    response_times: deque = field(default_factory=lambda: deque(maxlen=1000))


@dataclass
class APIHealthStatus:
    """Health status for an API source."""
    source: str
    is_healthy: bool
    last_check: datetime
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    consecutive_failures: int = 0
    uptime_percentage: float = 100.0


class APIMonitoringService:
    """
    Service for monitoring API performance, health, and metrics.

    Tracks response times, error rates, cache performance, and provides
    health checks and alerting capabilities.
    """

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url
        self.metrics: Dict[str, APIMetrics] = {}
        self.health_status: Dict[str, APIHealthStatus] = {}
        self.alert_thresholds = {
            'error_rate_threshold': 0.1,  # 10% error rate
            'response_time_threshold': 5000,  # 5 seconds
            'consecutive_failures_threshold': 5,
            'uptime_threshold': 0.95  # 95% uptime
        }
        self.monitoring_enabled = True

    def record_api_request(
        self,
        source: str,
        response_time_ms: float,
        success: bool,
        error_type: Optional[str] = None,
        cached: bool = False,
        rate_limited: bool = False
    ):
        """
        Record metrics for an API request.

        Args:
            source: API source name
            response_time_ms: Response time in milliseconds
            success: Whether the request was successful
            error_type: Type of error if request failed
            cached: Whether response was cached
            rate_limited: Whether request was rate limited
        """
        if not self.monitoring_enabled:
            return

        try:
            if source not in self.metrics:
                self.metrics[source] = APIMetrics(source=source)

            metrics = self.metrics[source]

            # Update basic counters
            metrics.total_requests += 1
            metrics.last_request_time = datetime.utcnow()

            if success:
                metrics.successful_requests += 1
            else:
                metrics.failed_requests += 1
                if error_type:
                    metrics.error_types[error_type] = metrics.error_types.get(error_type, 0) + 1

            # Update response time metrics
            if response_time_ms > 0:
                metrics.response_times.append(response_time_ms)
                metrics.min_response_time = min(metrics.min_response_time, response_time_ms)
                metrics.max_response_time = max(metrics.max_response_time, response_time_ms)

                # Calculate running average
                total_time = metrics.average_response_time * (metrics.total_requests - 1) + response_time_ms
                metrics.average_response_time = total_time / metrics.total_requests

            # Update cache metrics
            if cached:
                metrics.cache_hits += 1
            else:
                metrics.cache_misses += 1

            # Update rate limiting metrics
            if rate_limited:
                metrics.rate_limit_hits += 1

            logger.debug(
                "API request metrics recorded",
                source=source,
                response_time_ms=response_time_ms,
                success=success,
                cached=cached
            )

        except Exception as e:
            logger.error("Error recording API metrics", error=str(e), source=source)

    def record_circuit_breaker_open(self, source: str):
        """Record circuit breaker opening."""
        if source in self.metrics:
            self.metrics[source].circuit_breaker_opens += 1

    async def check_api_health(self, source: str, api_client) -> APIHealthStatus:
        """
        Check health of a specific API source.

        Args:
            source: API source name
            api_client: API client instance

        Returns:
            Health status for the source
        """
        start_time = time.time()
        current_time = datetime.utcnow()

        try:
            # Perform health check
            is_healthy = await api_client.health_check()
            response_time_ms = (time.time() - start_time) * 1000

            # Update or create health status
            if source in self.health_status:
                health = self.health_status[source]
                health.is_healthy = is_healthy
                health.last_check = current_time
                health.response_time_ms = response_time_ms

                if is_healthy:
                    health.consecutive_failures = 0
                    health.error_message = None
                else:
                    health.consecutive_failures += 1
                    health.error_message = "Health check failed"
            else:
                health = APIHealthStatus(
                    source=source,
                    is_healthy=is_healthy,
                    last_check=current_time,
                    response_time_ms=response_time_ms,
                    consecutive_failures=0 if is_healthy else 1,
                    error_message=None if is_healthy else "Health check failed"
                )
                self.health_status[source] = health

            # Calculate uptime percentage (last 24 hours)
            await self._calculate_uptime(source)

            logger.info(
                "API health check completed",
                source=source,
                healthy=is_healthy,
                response_time_ms=response_time_ms
            )

            return health

        except Exception as e:
            logger.error("API health check failed", source=source, error=str(e))

            # Record failed health check
            response_time_ms = (time.time() - start_time) * 1000

            if source in self.health_status:
                health = self.health_status[source]
                health.is_healthy = False
                health.last_check = current_time
                health.response_time_ms = response_time_ms
                health.consecutive_failures += 1
                health.error_message = str(e)
            else:
                health = APIHealthStatus(
                    source=source,
                    is_healthy=False,
                    last_check=current_time,
                    response_time_ms=response_time_ms,
                    consecutive_failures=1,
                    error_message=str(e)
                )
                self.health_status[source] = health

            return health

    async def _calculate_uptime(self, source: str):
        """Calculate uptime percentage for the last 24 hours."""
        try:
            async with get_session() as session:
                # Get recent jobs for this source
                cutoff_time = datetime.utcnow() - timedelta(hours=24)

                query = select(ScrapingJob).where(
                    and_(
                        ScrapingJob.source == source,
                        ScrapingJob.created_at >= cutoff_time
                    )
                )

                result = await session.execute(query)
                jobs = result.scalars().all()

                if jobs:
                    successful_jobs = len([j for j in jobs if j.status == JobStatus.SUCCESS])
                    uptime_percentage = (successful_jobs / len(jobs)) * 100

                    if source in self.health_status:
                        self.health_status[source].uptime_percentage = uptime_percentage

        except Exception as e:
            logger.warning("Error calculating uptime", source=source, error=str(e))

    def get_metrics_summary(self, source: Optional[str] = None) -> Dict[str, Any]:
        """
        Get metrics summary for all sources or a specific source.

        Args:
            source: Specific source name (optional)

        Returns:
            Dictionary containing metrics summary
        """
        if source and source in self.metrics:
            return self._format_metrics(self.metrics[source])

        summary = {}
        for src, metrics in self.metrics.items():
            summary[src] = self._format_metrics(metrics)

        return summary

    def _format_metrics(self, metrics: APIMetrics) -> Dict[str, Any]:
        """Format metrics for output."""
        error_rate = (metrics.failed_requests / metrics.total_requests) if metrics.total_requests > 0 else 0
        cache_hit_rate = (metrics.cache_hits / (metrics.cache_hits + metrics.cache_misses)) if (metrics.cache_hits + metrics.cache_misses) > 0 else 0

        # Calculate percentiles for response times
        response_times = list(metrics.response_times)
        percentiles = {}
        if response_times:
            response_times.sort()
            percentiles = {
                'p50': self._percentile(response_times, 50),
                'p90': self._percentile(response_times, 90),
                'p95': self._percentile(response_times, 95),
                'p99': self._percentile(response_times, 99)
            }

        return {
            'source': metrics.source,
            'total_requests': metrics.total_requests,
            'successful_requests': metrics.successful_requests,
            'failed_requests': metrics.failed_requests,
            'error_rate': round(error_rate * 100, 2),
            'average_response_time_ms': round(metrics.average_response_time, 2),
            'min_response_time_ms': metrics.min_response_time if metrics.min_response_time != float('inf') else None,
            'max_response_time_ms': metrics.max_response_time,
            'response_time_percentiles': percentiles,
            'cache_hit_rate': round(cache_hit_rate * 100, 2),
            'cache_hits': metrics.cache_hits,
            'cache_misses': metrics.cache_misses,
            'rate_limit_hits': metrics.rate_limit_hits,
            'circuit_breaker_opens': metrics.circuit_breaker_opens,
            'last_request_time': metrics.last_request_time.isoformat() if metrics.last_request_time else None,
            'error_types': dict(metrics.error_types)
        }

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile for a list of values."""
        if not data:
            return 0.0

        k = (len(data) - 1) * percentile / 100
        f = int(k)
        c = k - f

        if f + 1 < len(data):
            return data[f] + (c * (data[f + 1] - data[f]))
        else:
            return data[f]

    def get_health_summary(self, source: Optional[str] = None) -> Dict[str, Any]:
        """
        Get health summary for all sources or a specific source.

        Args:
            source: Specific source name (optional)

        Returns:
            Dictionary containing health summary
        """
        if source and source in self.health_status:
            return self._format_health_status(self.health_status[source])

        summary = {}
        for src, health in self.health_status.items():
            summary[src] = self._format_health_status(health)

        return summary

    def _format_health_status(self, health: APIHealthStatus) -> Dict[str, Any]:
        """Format health status for output."""
        return {
            'source': health.source,
            'is_healthy': health.is_healthy,
            'last_check': health.last_check.isoformat(),
            'response_time_ms': health.response_time_ms,
            'error_message': health.error_message,
            'consecutive_failures': health.consecutive_failures,
            'uptime_percentage': round(health.uptime_percentage, 2)
        }

    def check_alerts(self) -> List[Dict[str, Any]]:
        """
        Check for alert conditions based on thresholds.

        Returns:
            List of active alerts
        """
        alerts = []

        for source, metrics in self.metrics.items():
            # Check error rate
            error_rate = (metrics.failed_requests / metrics.total_requests) if metrics.total_requests > 0 else 0
            if error_rate > self.alert_thresholds['error_rate_threshold']:
                alerts.append({
                    'type': 'high_error_rate',
                    'source': source,
                    'value': round(error_rate * 100, 2),
                    'threshold': round(self.alert_thresholds['error_rate_threshold'] * 100, 2),
                    'message': f"High error rate: {round(error_rate * 100, 2)}%"
                })

            # Check response time
            if metrics.average_response_time > self.alert_thresholds['response_time_threshold']:
                alerts.append({
                    'type': 'slow_response_time',
                    'source': source,
                    'value': round(metrics.average_response_time, 2),
                    'threshold': self.alert_thresholds['response_time_threshold'],
                    'message': f"Slow response time: {round(metrics.average_response_time, 2)}ms"
                })

        for source, health in self.health_status.items():
            # Check consecutive failures
            if health.consecutive_failures >= self.alert_thresholds['consecutive_failures_threshold']:
                alerts.append({
                    'type': 'consecutive_failures',
                    'source': source,
                    'value': health.consecutive_failures,
                    'threshold': self.alert_thresholds['consecutive_failures_threshold'],
                    'message': f"Consecutive failures: {health.consecutive_failures}"
                })

            # Check uptime
            uptime_rate = health.uptime_percentage / 100
            if uptime_rate < self.alert_thresholds['uptime_threshold']:
                alerts.append({
                    'type': 'low_uptime',
                    'source': source,
                    'value': round(health.uptime_percentage, 2),
                    'threshold': round(self.alert_thresholds['uptime_threshold'] * 100, 2),
                    'message': f"Low uptime: {round(health.uptime_percentage, 2)}%"
                })

        return alerts

    def reset_metrics(self, source: Optional[str] = None):
        """
        Reset metrics for all sources or a specific source.

        Args:
            source: Specific source name (optional)
        """
        if source and source in self.metrics:
            self.metrics[source] = APIMetrics(source=source)
            logger.info("Metrics reset", source=source)
        else:
            self.metrics.clear()
            logger.info("All metrics reset")

    def configure_alert_thresholds(self, **kwargs):
        """
        Configure alert thresholds.

        Args:
            **kwargs: Threshold parameters to update
        """
        for key, value in kwargs.items():
            if key in self.alert_thresholds:
                old_value = self.alert_thresholds[key]
                self.alert_thresholds[key] = value
                logger.info(
                    "Alert threshold updated",
                    parameter=key,
                    old_value=old_value,
                    new_value=value
                )

    def enable_monitoring(self):
        """Enable metrics collection."""
        self.monitoring_enabled = True
        logger.info("API monitoring enabled")

    def disable_monitoring(self):
        """Disable metrics collection."""
        self.monitoring_enabled = False
        logger.info("API monitoring disabled")

    async def export_metrics_to_database(self):
        """Export current metrics to database for historical analysis."""
        try:
            # This would integrate with the existing JobMetrics model
            # to store API performance data alongside job metrics
            pass
        except Exception as e:
            logger.error("Error exporting metrics to database", error=str(e))

    def get_performance_report(self, hours_back: int = 24) -> Dict[str, Any]:
        """
        Generate a comprehensive performance report.

        Args:
            hours_back: Number of hours to include in the report

        Returns:
            Performance report dictionary
        """
        report = {
            'report_timestamp': datetime.utcnow().isoformat(),
            'period_hours': hours_back,
            'metrics_summary': self.get_metrics_summary(),
            'health_summary': self.get_health_summary(),
            'active_alerts': self.check_alerts(),
            'alert_thresholds': self.alert_thresholds,
            'monitoring_enabled': self.monitoring_enabled
        }

        # Add overall statistics
        total_requests = sum(m.total_requests for m in self.metrics.values())
        total_successful = sum(m.successful_requests for m in self.metrics.values())
        total_failed = sum(m.failed_requests for m in self.metrics.values())

        report['overall_statistics'] = {
            'total_requests': total_requests,
            'total_successful': total_successful,
            'total_failed': total_failed,
            'overall_error_rate': round((total_failed / total_requests * 100) if total_requests > 0 else 0, 2),
            'healthy_sources': len([h for h in self.health_status.values() if h.is_healthy]),
            'total_sources': len(self.health_status)
        }

        return report


# Global monitoring service instance
api_monitoring_service = APIMonitoringService()