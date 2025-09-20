import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
import asyncpg
import redis.asyncio as redis
import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.core.logging import get_logger

logger = get_logger("app.health")


class HealthStatus(str, Enum):
    """Health check status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth:
    """Health status for a single component."""

    def __init__(
        self,
        name: str,
        status: HealthStatus,
        response_time_ms: Optional[float] = None,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.status = status
        self.response_time_ms = response_time_ms
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "name": self.name,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
        }

        if self.response_time_ms is not None:
            result["response_time_ms"] = round(self.response_time_ms, 2)

        if self.message:
            result["message"] = self.message

        if self.details:
            result["details"] = self.details

        return result


class HealthChecker:
    """
    Comprehensive health checking system for all application components.

    Performs checks on database, Redis, external APIs, and other critical services.
    """

    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self.register_default_checks()

    def register_check(self, name: str, check_func: Callable):
        """Register a custom health check function."""
        self.checks[name] = check_func
        logger.debug(f"Registered health check: {name}")

    def register_default_checks(self):
        """Register default health checks for core components."""
        self.checks = {
            "database": self.check_database,
            "redis": self.check_redis,
            "external_apis": self.check_external_apis,
            "disk_space": self.check_disk_space,
            "memory": self.check_memory,
            "configuration": self.check_configuration,
        }

    async def check_all(self) -> Dict[str, Any]:
        """
        Run all health checks and return comprehensive status.

        Returns:
            Dictionary with overall status and individual component results
        """
        start_time = time.time()
        results = {}
        component_statuses = []

        # Run all checks concurrently
        check_tasks = [
            self.run_single_check(name, check_func)
            for name, check_func in self.checks.items()
        ]

        check_results = await asyncio.gather(*check_tasks, return_exceptions=True)

        # Process results
        for i, (name, _) in enumerate(self.checks.items()):
            result = check_results[i]
            if isinstance(result, Exception):
                component_health = ComponentHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check failed: {str(result)}"
                )
            else:
                component_health = result

            results[name] = component_health.to_dict()
            component_statuses.append(component_health.status)

        # Determine overall status
        overall_status = self.determine_overall_status(component_statuses)

        # Calculate total response time
        total_response_time = (time.time() - start_time) * 1000

        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "response_time_ms": round(total_response_time, 2),
            "environment": settings.ENVIRONMENT,
            "version": settings.APP_VERSION,
            "components": results,
            "summary": self.generate_summary(results)
        }

    async def run_single_check(self, name: str, check_func: Callable) -> ComponentHealth:
        """Run a single health check with timing and error handling."""
        start_time = time.time()

        try:
            result = await check_func()
            response_time = (time.time() - start_time) * 1000

            if isinstance(result, ComponentHealth):
                result.response_time_ms = response_time
                return result
            else:
                # Assume successful check if not ComponentHealth object
                return ComponentHealth(
                    name=name,
                    status=HealthStatus.HEALTHY,
                    response_time_ms=response_time
                )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Health check failed for {name}", error=str(e))

            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message=str(e)
            )

    def determine_overall_status(self, component_statuses: List[HealthStatus]) -> HealthStatus:
        """Determine overall system health based on component statuses."""
        if not component_statuses:
            return HealthStatus.UNHEALTHY

        unhealthy_count = component_statuses.count(HealthStatus.UNHEALTHY)
        degraded_count = component_statuses.count(HealthStatus.DEGRADED)

        # If any critical components are unhealthy, system is unhealthy
        if unhealthy_count > 0:
            return HealthStatus.UNHEALTHY

        # If any components are degraded, system is degraded
        if degraded_count > 0:
            return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY

    def generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of health check results."""
        total_components = len(results)
        healthy_count = sum(1 for r in results.values() if r["status"] == "healthy")
        degraded_count = sum(1 for r in results.values() if r["status"] == "degraded")
        unhealthy_count = sum(1 for r in results.values() if r["status"] == "unhealthy")

        return {
            "total_components": total_components,
            "healthy": healthy_count,
            "degraded": degraded_count,
            "unhealthy": unhealthy_count,
            "health_percentage": round((healthy_count / total_components) * 100, 1) if total_components > 0 else 0
        }

    async def check_database(self) -> ComponentHealth:
        """Check database connectivity and performance."""
        try:
            async with get_session() as session:
                # Test basic connectivity
                start_time = time.time()
                result = await session.execute(text("SELECT 1"))
                query_time = (time.time() - start_time) * 1000

                # Test more complex query
                start_time = time.time()
                count_result = await session.execute(text("SELECT COUNT(*) FROM information_schema.tables"))
                complex_query_time = (time.time() - start_time) * 1000

                details = {
                    "simple_query_time_ms": round(query_time, 2),
                    "complex_query_time_ms": round(complex_query_time, 2),
                    "pool_size": settings.DB_POOL_SIZE,
                    "max_overflow": settings.DB_MAX_OVERFLOW
                }

                # Determine status based on performance
                if query_time > 1000:  # 1 second
                    status = HealthStatus.UNHEALTHY
                    message = "Database queries are very slow"
                elif query_time > 500:  # 500ms
                    status = HealthStatus.DEGRADED
                    message = "Database queries are slower than expected"
                else:
                    status = HealthStatus.HEALTHY
                    message = "Database is responding normally"

                return ComponentHealth(
                    name="database",
                    status=status,
                    message=message,
                    details=details
                )

        except Exception as e:
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}"
            )

    async def check_redis(self) -> ComponentHealth:
        """Check Redis connectivity and performance."""
        try:
            # Parse Redis URL
            redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_timeout=settings.REDIS_TIMEOUT
            )

            # Test basic connectivity
            start_time = time.time()
            pong = await redis_client.ping()
            ping_time = (time.time() - start_time) * 1000

            # Test set/get operations
            test_key = f"health_check_{int(time.time())}"
            test_value = "health_check_value"

            start_time = time.time()
            await redis_client.set(test_key, test_value, ex=60)  # Expire in 60 seconds
            retrieved_value = await redis_client.get(test_key)
            await redis_client.delete(test_key)
            operation_time = (time.time() - start_time) * 1000

            await redis_client.close()

            details = {
                "ping_time_ms": round(ping_time, 2),
                "operation_time_ms": round(operation_time, 2),
                "ping_response": pong,
                "set_get_test": retrieved_value == test_value
            }

            # Determine status based on performance
            if ping_time > 1000:  # 1 second
                status = HealthStatus.UNHEALTHY
                message = "Redis is very slow to respond"
            elif ping_time > 200:  # 200ms
                status = HealthStatus.DEGRADED
                message = "Redis is slower than expected"
            else:
                status = HealthStatus.HEALTHY
                message = "Redis is responding normally"

            return ComponentHealth(
                name="redis",
                status=status,
                message=message,
                details=details
            )

        except Exception as e:
            return ComponentHealth(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis connection failed: {str(e)}"
            )

    async def check_external_apis(self) -> ComponentHealth:
        """Check external API connectivity."""
        api_results = {}
        overall_status = HealthStatus.HEALTHY

        # Test APIs that are enabled
        if settings.ENABLE_API_CLIENTS:
            # Test US State Department API
            if settings.US_STATE_DEPT_API_KEY:
                api_results["us_state_dept"] = await self.test_external_api(
                    "US State Department",
                    "https://travel.state.gov",
                    timeout=10
                )

            # Test UK Foreign Office API
            if settings.UK_FOREIGN_OFFICE_API_KEY:
                api_results["uk_foreign_office"] = await self.test_external_api(
                    "UK Foreign Office",
                    "https://www.gov.uk",
                    timeout=10
                )

        # Determine overall external API status
        if api_results:
            statuses = [result["status"] for result in api_results.values()]
            if "unhealthy" in statuses:
                overall_status = HealthStatus.DEGRADED  # External APIs are not critical
            elif "degraded" in statuses:
                overall_status = HealthStatus.DEGRADED

        return ComponentHealth(
            name="external_apis",
            status=overall_status,
            message=f"Checked {len(api_results)} external APIs",
            details=api_results
        )

    async def test_external_api(self, name: str, url: str, timeout: int = 10) -> Dict[str, Any]:
        """Test connectivity to a single external API."""
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                start_time = time.time()
                response = await client.get(url)
                response_time = (time.time() - start_time) * 1000

                if response.status_code < 400:
                    status = "healthy"
                    message = f"API responded with status {response.status_code}"
                else:
                    status = "degraded"
                    message = f"API responded with status {response.status_code}"

                return {
                    "status": status,
                    "response_time_ms": round(response_time, 2),
                    "status_code": response.status_code,
                    "message": message
                }

        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Failed to connect to {name}: {str(e)}"
            }

    async def check_disk_space(self) -> ComponentHealth:
        """Check available disk space."""
        try:
            import shutil
            import os

            # Check disk space for current directory
            total, used, free = shutil.disk_usage(os.getcwd())

            # Convert to GB
            total_gb = total / (1024**3)
            used_gb = used / (1024**3)
            free_gb = free / (1024**3)
            usage_percent = (used / total) * 100

            details = {
                "total_gb": round(total_gb, 2),
                "used_gb": round(used_gb, 2),
                "free_gb": round(free_gb, 2),
                "usage_percent": round(usage_percent, 1)
            }

            # Determine status based on usage
            if usage_percent > 95:
                status = HealthStatus.UNHEALTHY
                message = f"Disk usage critical: {usage_percent:.1f}%"
            elif usage_percent > 85:
                status = HealthStatus.DEGRADED
                message = f"Disk usage high: {usage_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk usage normal: {usage_percent:.1f}%"

            return ComponentHealth(
                name="disk_space",
                status=status,
                message=message,
                details=details
            )

        except Exception as e:
            return ComponentHealth(
                name="disk_space",
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check disk space: {str(e)}"
            )

    async def check_memory(self) -> ComponentHealth:
        """Check memory usage."""
        try:
            import psutil

            # Get memory information
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()

            details = {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_percent": memory.percent,
                "swap_total_gb": round(swap.total / (1024**3), 2),
                "swap_used_percent": swap.percent
            }

            # Determine status based on usage
            if memory.percent > 95:
                status = HealthStatus.UNHEALTHY
                message = f"Memory usage critical: {memory.percent:.1f}%"
            elif memory.percent > 85:
                status = HealthStatus.DEGRADED
                message = f"Memory usage high: {memory.percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory usage normal: {memory.percent:.1f}%"

            return ComponentHealth(
                name="memory",
                status=status,
                message=message,
                details=details
            )

        except ImportError:
            return ComponentHealth(
                name="memory",
                status=HealthStatus.DEGRADED,
                message="psutil not available for memory monitoring"
            )
        except Exception as e:
            return ComponentHealth(
                name="memory",
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check memory: {str(e)}"
            )

    async def check_configuration(self) -> ComponentHealth:
        """Check application configuration."""
        try:
            issues = []
            warnings = []

            # Check critical configuration
            if settings.SECRET_KEY == "dev-secret-key-change-in-production" and settings.is_production:
                issues.append("Default secret key in production")

            if settings.JWT_SECRET_KEY == "jwt-secret-key-change-in-production" and settings.is_production:
                issues.append("Default JWT secret key in production")

            if settings.DEBUG and settings.is_production:
                issues.append("Debug mode enabled in production")

            # Check warnings
            if not settings.SENTRY_DSN and settings.is_production:
                warnings.append("Sentry not configured for error tracking")

            if not settings.REDIS_URL:
                warnings.append("Redis not configured")

            details = {
                "environment": settings.ENVIRONMENT,
                "debug_mode": settings.DEBUG,
                "features_enabled": {
                    "scraping": settings.ENABLE_SCRAPING,
                    "api_clients": settings.ENABLE_API_CLIENTS,
                    "notifications": settings.ENABLE_NOTIFICATIONS,
                    "location_processing": settings.ENABLE_LOCATION_PROCESSING,
                },
                "issues": issues,
                "warnings": warnings
            }

            # Determine status
            if issues:
                status = HealthStatus.UNHEALTHY
                message = f"Configuration issues detected: {len(issues)} critical"
            elif warnings:
                status = HealthStatus.DEGRADED
                message = f"Configuration warnings: {len(warnings)} items"
            else:
                status = HealthStatus.HEALTHY
                message = "Configuration is valid"

            return ComponentHealth(
                name="configuration",
                status=status,
                message=message,
                details=details
            )

        except Exception as e:
            return ComponentHealth(
                name="configuration",
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check configuration: {str(e)}"
            )


# Global health checker instance
health_checker = HealthChecker()


async def get_health_status() -> Dict[str, Any]:
    """Get comprehensive health status for the application."""
    return await health_checker.check_all()


async def get_readiness_status() -> Dict[str, Any]:
    """
    Get readiness status (subset of health checks for critical components).

    Used for Kubernetes readiness probes.
    """
    critical_checks = ["database", "redis", "configuration"]
    start_time = time.time()
    results = {}

    for check_name in critical_checks:
        if check_name in health_checker.checks:
            try:
                result = await health_checker.run_single_check(
                    check_name,
                    health_checker.checks[check_name]
                )
                results[check_name] = result.to_dict()
            except Exception as e:
                results[check_name] = {
                    "name": check_name,
                    "status": "unhealthy",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }

    # Determine overall readiness
    statuses = [r["status"] for r in results.values()]
    if "unhealthy" in statuses:
        overall_status = "unhealthy"
    elif "degraded" in statuses:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    response_time = (time.time() - start_time) * 1000

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "response_time_ms": round(response_time, 2),
        "components": results
    }


async def get_liveness_status() -> Dict[str, Any]:
    """
    Get liveness status (basic application health).

    Used for Kubernetes liveness probes.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }