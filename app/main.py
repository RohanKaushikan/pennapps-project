import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
import time

from app.core.config import settings, get_environment_settings
from app.core.database import create_tables, db_manager
from app.core.redis import initialize_redis, close_redis
from app.core.logging import configure_logging, get_logger
from app.core.health import get_health_status, get_readiness_status, get_liveness_status
from app.core.metrics import app_metrics, MetricsMiddleware, update_system_metrics_periodically
from app.core.security import (
    SecurityHeadersMiddleware, RateLimitMiddleware, CSRFProtectionMiddleware,
    CORSConfig
)
from app.api.v1 import api_router
from app.api.internal.location_processing import router as location_router

# Configure logging first
configure_logging()
logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager with comprehensive startup and shutdown.
    """
    # Startup
    logger.info("Starting Travel Legal Alert System", environment=settings.ENVIRONMENT)

    try:
        # Initialize Redis connection
        await initialize_redis()
        logger.info("Redis connection initialized")

        # Create database tables
        await create_tables()
        logger.info("Database tables verified")

        # Start background system metrics collection
        if settings.METRICS_ENABLED:
            metrics_task = asyncio.create_task(update_system_metrics_periodically())
            logger.info("System metrics collection started")

        logger.info("Application startup completed successfully")

        yield

        # Shutdown
        logger.info("Shutting down Travel Legal Alert System")

        # Cancel background tasks
        if settings.METRICS_ENABLED:
            metrics_task.cancel()
            try:
                await metrics_task
            except asyncio.CancelledError:
                pass

        # Close connections
        await close_redis()
        await db_manager.close_connections()

        logger.info("Application shutdown completed")

    except Exception as e:
        logger.error("Error during application lifecycle", error=str(e))
        raise


# Create FastAPI application with production settings
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="A comprehensive system for tracking and alerting users about legal and travel-related changes worldwide",
    openapi_url="/api/v1/openapi.json" if settings.DEBUG else None,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
    # Security settings
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "tryItOutEnabled": True,
    } if settings.DEBUG else {},
)

# Add security middleware (order matters!)
if settings.SECURITY_HEADERS_ENABLED:
    app.add_middleware(SecurityHeadersMiddleware)

if settings.API_RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware)

# CSRF protection for non-API endpoints
app.add_middleware(CSRFProtectionMiddleware)

# Metrics middleware
if settings.METRICS_ENABLED:
    app.add_middleware(MetricsMiddleware, metrics=app_metrics)

# CORS middleware with environment-specific configuration
cors_config = CORSConfig.get_cors_config()
if cors_config and settings.CORS_ENABLED:
    app.add_middleware(CORSMiddleware, **cors_config)

# Trusted host middleware for security
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts_list if settings.is_production else ["*"]
)


# Production health check endpoints
@app.get("/health", tags=["Health"], include_in_schema=settings.DEBUG)
async def health_check():
    """
    Comprehensive health check endpoint.
    Returns detailed status of all application components.
    """
    return await get_health_status()


@app.get("/health/ready", tags=["Health"], include_in_schema=settings.DEBUG)
async def readiness_check():
    """
    Kubernetes readiness probe endpoint.
    Returns status of critical components required for request handling.
    """
    return await get_readiness_status()


@app.get("/health/live", tags=["Health"], include_in_schema=settings.DEBUG)
async def liveness_check():
    """
    Kubernetes liveness probe endpoint.
    Returns basic application health status.
    """
    return await get_liveness_status()


# Metrics endpoint for Prometheus
@app.get("/metrics", response_class=PlainTextResponse, tags=["Monitoring"], include_in_schema=settings.DEBUG)
async def metrics():
    """
    Prometheus metrics endpoint.
    Returns application metrics in Prometheus format.
    """
    if not settings.METRICS_ENABLED:
        return Response(status_code=404)

    return app_metrics.generate_metrics()


@app.get("/info", tags=["System"], include_in_schema=settings.DEBUG)
async def system_info():
    """
    System information endpoint.
    Returns application and environment details.
    """
    return get_environment_settings()


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Enhanced 404 handler with security considerations."""
    logger.warning(
        "Resource not found",
        path=request.url.path,
        method=request.method,
        client_ip=request.client.host if request.client else "unknown"
    )

    return JSONResponse(
        status_code=404,
        content={
            "detail": "The requested resource was not found",
            "path": str(request.url.path),
            "method": request.method,
            "timestamp": time.time()
        }
    )


@app.exception_handler(429)
async def rate_limit_handler(request: Request, exc):
    """Rate limit exceeded handler."""
    logger.warning(
        "Rate limit exceeded",
        path=request.url.path,
        client_ip=request.client.host if request.client else "unknown"
    )

    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded",
            "message": "Too many requests. Please try again later."
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Enhanced 500 handler with error tracking."""
    logger.error(
        "Internal server error",
        error=str(exc),
        path=request.url.path,
        method=request.method,
        client_ip=request.client.host if request.client else "unknown"
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error occurred",
            "message": "Please try again later or contact support",
            "timestamp": time.time()
        }
    )


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with environment-aware information.
    """
    response_data = {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": time.time()
    }

    # Add development-specific information
    if settings.DEBUG:
        response_data.update({
            "docs_url": "/docs",
            "redoc_url": "/redoc",
            "health_check": "/health",
            "metrics": "/metrics" if settings.METRICS_ENABLED else None
        })

    return response_data


# Include API routers
app.include_router(api_router, prefix="/api/v1")
app.include_router(location_router)

# Add startup event for additional initialization
@app.on_event("startup")
async def startup_event():
    """Additional startup tasks."""
    logger.info(
        "Application ready to serve requests",
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG,
        metrics_enabled=settings.METRICS_ENABLED,
        security_headers=settings.SECURITY_HEADERS_ENABLED
    )


if __name__ == "__main__":
    import uvicorn

    # Production-ready uvicorn configuration
    uvicorn_config = {
        "app": "app.main:app",
        "host": settings.HOST,
        "port": settings.PORT,
        "reload": settings.DEBUG,
        "log_level": settings.LOG_LEVEL.lower(),
        "access_log": True,
        "server_header": False,  # Don't expose server information
        "date_header": False,    # Don't expose server date
    }

    # Add production-specific settings
    if settings.is_production:
        uvicorn_config.update({
            "workers": 1,  # Use gunicorn for multiple workers in production
            "loop": "uvloop",  # Use uvloop for better performance
            "http": "httptools",  # Use httptools for better performance
        })

    uvicorn.run(**uvicorn_config)