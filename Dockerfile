# Multi-stage build for optimized production image
FROM python:3.11-slim AS builder

# Set build environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libpq-dev \
        python3-dev \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install requirements
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Production stage
FROM python:3.11-slim AS production

# Set production environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH" \
    ENVIRONMENT=production \
    LOG_LEVEL=INFO \
    METRICS_ENABLED=true

# Install runtime dependencies only
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        curl \
        ca-certificates \
        dumb-init \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get purge -y --auto-remove

# Create application user and group
RUN groupadd -r -g 1000 appuser \
    && useradd -r -u 1000 -g appuser -m -d /home/appuser -s /bin/bash appuser

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Set work directory
WORKDIR /app

# Create application directories with proper permissions
RUN mkdir -p /app/logs /app/data /app/tmp \
    && chown -R appuser:appuser /app

# Copy application code
COPY --chown=appuser:appuser ./app /app/app
COPY --chown=appuser:appuser ./alembic /app/alembic
COPY --chown=appuser:appuser ./alembic.ini /app/
COPY --chown=appuser:appuser ./scripts /app/scripts

# Make scripts executable
RUN chmod +x /app/scripts/*.sh

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check with improved reliability
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Add labels for better container management
LABEL maintainer="Travel Alert System Team" \
      version="1.0.0" \
      description="Travel Legal Alert System API" \
      org.opencontainers.image.source="https://github.com/your-org/travel-alert-system"

# Use dumb-init for proper signal handling
ENTRYPOINT ["dumb-init", "--"]

# Set default command with production optimizations
CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--bind", "0.0.0.0:8000", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--timeout", "30", \
     "--keep-alive", "5", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info"]