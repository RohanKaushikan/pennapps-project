import asyncio
import time
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy import event, text
from sqlalchemy.engine import Engine

from app.core.config import settings
from app.core.logging import get_logger, DatabaseQueryLogger

logger = get_logger("app.database")

# Database connection pool configuration
ENGINE_CONFIG = {
    "echo": settings.DB_ECHO,
    "future": True,
    "pool_pre_ping": True,
    "pool_size": settings.DB_POOL_SIZE,
    "max_overflow": settings.DB_MAX_OVERFLOW,
    "pool_timeout": settings.DB_POOL_TIMEOUT,
    "pool_recycle": settings.DB_POOL_RECYCLE,
    "poolclass": QueuePool,
    # Connection pool settings for production
    "connect_args": {
        "command_timeout": 30,
        "server_settings": {
            "application_name": f"{settings.APP_NAME}_{settings.ENVIRONMENT}",
            "jit": "off",  # Disable JIT for consistent performance
        }
    } if settings.is_production else {}
}

# Create async engine with optimized settings
engine = create_async_engine(
    settings.get_database_url(),
    **ENGINE_CONFIG
)

# Create async session factory with optimized settings
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Create declarative base
Base = declarative_base()


# Database event listeners for monitoring
@event.listens_for(engine.sync_engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Record query start time."""
    context._query_start_time = time.time()


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log query performance."""
    if hasattr(context, '_query_start_time'):
        duration = (time.time() - context._query_start_time) * 1000
        DatabaseQueryLogger.log_query(statement, parameters, duration)


@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set database-specific optimizations."""
    if "postgresql" in settings.DATABASE_URL:
        # PostgreSQL-specific optimizations
        with dbapi_connection.cursor() as cursor:
            # Set connection-level parameters for performance
            cursor.execute("SET statement_timeout = '30s'")
            cursor.execute("SET lock_timeout = '10s'")
            cursor.execute("SET idle_in_transaction_session_timeout = '60s'")


class DatabaseManager:
    """
    Database connection manager with health monitoring and connection pooling.

    Provides advanced database management features including:
    - Connection pool monitoring
    - Health checks
    - Performance metrics
    - Connection lifecycle management
    """

    def __init__(self):
        self.engine = engine
        self.session_factory = AsyncSessionLocal
        self._connection_pool_stats = {}
        self._last_health_check = None
        self._health_check_interval = 60  # seconds

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session with monitoring and error handling.

        Yields:
            AsyncSession: Database session with automatic cleanup
        """
        session_start_time = time.time()

        async with self.session_factory() as session:
            try:
                # Update connection pool stats
                await self._update_pool_stats()

                yield session

                # Commit if no exception occurred
                await session.commit()

            except Exception as e:
                # Rollback on any exception
                await session.rollback()
                logger.error(
                    "Database session error",
                    error=str(e),
                    session_duration_ms=(time.time() - session_start_time) * 1000
                )
                raise
            finally:
                # Session cleanup is handled by async context manager
                session_duration = (time.time() - session_start_time) * 1000
                if session_duration > 5000:  # Log slow sessions
                    logger.warning(
                        "Slow database session",
                        duration_ms=session_duration
                    )

    async def _update_pool_stats(self):
        """Update connection pool statistics."""
        try:
            pool = self.engine.pool
            self._connection_pool_stats = {
                "pool_size": pool.size(),
                "pool_capacity": getattr(pool, '_pool', {}).get('capacity', 0),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalidated": pool.invalidated(),
                "timestamp": time.time()
            }
        except Exception as e:
            logger.warning("Error updating pool stats", error=str(e))

    def get_pool_stats(self) -> dict:
        """Get current connection pool statistics."""
        return self._connection_pool_stats.copy()

    async def health_check(self) -> dict:
        """
        Perform comprehensive database health check.

        Returns:
            dict: Health check results with performance metrics
        """
        health_data = {
            "healthy": False,
            "timestamp": time.time(),
            "checks": {}
        }

        try:
            # Basic connectivity check
            start_time = time.time()
            async with self.get_session() as session:
                result = await session.execute(text("SELECT 1"))
                connectivity_time = (time.time() - start_time) * 1000

                health_data["checks"]["connectivity"] = {
                    "status": "healthy",
                    "response_time_ms": connectivity_time
                }

            # Connection pool check
            pool_stats = self.get_pool_stats()
            pool_utilization = (
                pool_stats.get("checked_out", 0) /
                max(pool_stats.get("pool_size", 1), 1)
            ) * 100

            health_data["checks"]["connection_pool"] = {
                "status": "healthy" if pool_utilization < 90 else "degraded",
                "utilization_percent": pool_utilization,
                "stats": pool_stats
            }

            # Performance check with complex query
            start_time = time.time()
            async with self.get_session() as session:
                await session.execute(
                    text("SELECT COUNT(*) FROM information_schema.tables")
                )
                performance_time = (time.time() - start_time) * 1000

            health_data["checks"]["performance"] = {
                "status": "healthy" if performance_time < 1000 else "degraded",
                "response_time_ms": performance_time
            }

            # Overall health determination
            all_checks_healthy = all(
                check.get("status") == "healthy"
                for check in health_data["checks"].values()
            )

            health_data["healthy"] = all_checks_healthy
            self._last_health_check = time.time()

        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            health_data["checks"]["error"] = {
                "status": "unhealthy",
                "error": str(e)
            }

        return health_data

    async def close_connections(self):
        """Close all database connections."""
        try:
            await self.engine.dispose()
            logger.info("Database connections closed")
        except Exception as e:
            logger.error("Error closing database connections", error=str(e))

    @asynccontextmanager
    async def transaction(self):
        """
        Context manager for database transactions with automatic rollback.

        Usage:
            async with db_manager.transaction() as session:
                # Database operations here
                pass
        """
        async with self.get_session() as session:
            async with session.begin():
                yield session


# Global database manager instance
db_manager = DatabaseManager()


# Convenience functions for backward compatibility
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.

    Yields:
        AsyncSession: Database session
    """
    async for session in db_manager.get_session():
        yield session


async def create_tables() -> None:
    """
    Create database tables.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables() -> None:
    """
    Drop database tables.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def get_database_health() -> dict:
    """Get database health status."""
    return await db_manager.health_check()


def get_database_pool_stats() -> dict:
    """Get database connection pool statistics."""
    return db_manager.get_pool_stats()


# Database metrics collection for monitoring
class DatabaseMetrics:
    """Collect and expose database metrics."""

    def __init__(self):
        self.query_count = 0
        self.total_query_time = 0.0
        self.slow_query_count = 0
        self.error_count = 0

    def record_query(self, duration_ms: float, success: bool = True):
        """Record query metrics."""
        self.query_count += 1
        self.total_query_time += duration_ms

        if duration_ms > 1000:  # Queries over 1 second
            self.slow_query_count += 1

        if not success:
            self.error_count += 1

    def get_metrics(self) -> dict:
        """Get current metrics."""
        return {
            "total_queries": self.query_count,
            "average_query_time_ms": (
                self.total_query_time / self.query_count
                if self.query_count > 0 else 0
            ),
            "slow_queries": self.slow_query_count,
            "error_count": self.error_count,
            "error_rate": (
                self.error_count / self.query_count
                if self.query_count > 0 else 0
            )
        }

    def reset(self):
        """Reset all metrics."""
        self.query_count = 0
        self.total_query_time = 0.0
        self.slow_query_count = 0
        self.error_count = 0


# Global database metrics instance
db_metrics = DatabaseMetrics()