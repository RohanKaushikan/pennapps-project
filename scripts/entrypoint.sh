#!/bin/bash
set -e

# Default values
DEFAULT_WORKERS=${WORKERS:-4}
DEFAULT_PORT=${PORT:-8000}
DEFAULT_HOST=${HOST:-0.0.0.0}

# Log startup information
echo "🚀 Starting Travel Alert System"
echo "Environment: ${ENVIRONMENT:-development}"
echo "Workers: ${DEFAULT_WORKERS}"
echo "Port: ${DEFAULT_PORT}"
echo "Host: ${DEFAULT_HOST}"

# Function to wait for a service
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local timeout=${4:-30}

    echo "⏳ Waiting for $service_name at $host:$port..."

    for i in $(seq 1 $timeout); do
        if nc -z "$host" "$port" 2>/dev/null; then
            echo "✅ $service_name is ready!"
            return 0
        fi
        echo "   Attempt $i/$timeout: $service_name not ready yet..."
        sleep 1
    done

    echo "❌ Timeout waiting for $service_name"
    return 1
}

# Function to extract host and port from URL
extract_host_port() {
    local url=$1
    # Remove protocol
    url=${url#*://}
    # Extract host:port
    echo $url | cut -d'/' -f1
}

# Wait for database if DATABASE_URL is set
if [ -n "$DATABASE_URL" ]; then
    DB_HOST_PORT=$(extract_host_port "$DATABASE_URL" | cut -d'@' -f2)
    if [ -n "$DB_HOST_PORT" ]; then
        DB_HOST=$(echo $DB_HOST_PORT | cut -d':' -f1)
        DB_PORT=$(echo $DB_HOST_PORT | cut -d':' -f2)
        wait_for_service "$DB_HOST" "$DB_PORT" "PostgreSQL" 60
    fi
fi

# Wait for Redis if REDIS_URL is set
if [ -n "$REDIS_URL" ]; then
    REDIS_HOST_PORT=$(extract_host_port "$REDIS_URL")
    if [ -n "$REDIS_HOST_PORT" ]; then
        REDIS_HOST=$(echo $REDIS_HOST_PORT | cut -d':' -f1)
        REDIS_PORT=$(echo $REDIS_HOST_PORT | cut -d':' -f2)
        wait_for_service "$REDIS_HOST" "$REDIS_PORT" "Redis" 30
    fi
fi

# Run database migrations if in production and AUTO_MIGRATE is enabled
if [ "$ENVIRONMENT" = "production" ] && [ "$AUTO_MIGRATE" = "true" ]; then
    echo "🔄 Running database migrations..."
    alembic upgrade head
    echo "✅ Database migrations completed"
fi

# Pre-flight checks
echo "🔍 Running pre-flight checks..."

# Check if we can import the application
python -c "from app.main import app; print('✅ Application imports successfully')" || {
    echo "❌ Failed to import application"
    exit 1
}

# Validate critical environment variables for production
if [ "$ENVIRONMENT" = "production" ]; then
    echo "🔒 Validating production configuration..."

    if [ "$SECRET_KEY" = "dev-secret-key-change-in-production" ]; then
        echo "❌ Default SECRET_KEY detected in production!"
        exit 1
    fi

    if [ "$JWT_SECRET_KEY" = "jwt-secret-key-change-in-production" ]; then
        echo "❌ Default JWT_SECRET_KEY detected in production!"
        exit 1
    fi

    if [ "$DEBUG" = "true" ]; then
        echo "⚠️  DEBUG mode is enabled in production (not recommended)"
    fi

    echo "✅ Production configuration validated"
fi

echo "✅ Pre-flight checks completed"

# Handle different commands
case "$1" in
    "web")
        echo "🌐 Starting web server..."
        exec gunicorn app.main:app \
            --worker-class uvicorn.workers.UvicornWorker \
            --workers $DEFAULT_WORKERS \
            --bind $DEFAULT_HOST:$DEFAULT_PORT \
            --max-requests 1000 \
            --max-requests-jitter 100 \
            --timeout 30 \
            --keep-alive 5 \
            --access-logfile - \
            --error-logfile - \
            --log-level info \
            --preload
        ;;
    "worker")
        echo "👷 Starting Celery worker..."
        exec celery -A app.celery_app.celery worker \
            --loglevel=info \
            --concurrency=${WORKER_CONCURRENCY:-4} \
            --max-tasks-per-child=${WORKER_MAX_TASKS_PER_CHILD:-1000}
        ;;
    "beat")
        echo "⏰ Starting Celery beat scheduler..."
        exec celery -A app.celery_app.celery beat \
            --loglevel=info \
            --schedule=/tmp/celerybeat-schedule
        ;;
    "flower")
        echo "🌸 Starting Flower monitoring..."
        exec celery -A app.celery_app.celery flower \
            --port=5555 \
            --broker=${REDIS_URL}
        ;;
    "migrate")
        echo "🔄 Running database migrations..."
        exec alembic upgrade head
        ;;
    "shell")
        echo "🐚 Starting Python shell..."
        exec python -c "
import asyncio
from app.main import app
from app.core.database import get_session
from app.core.config import settings
print('Travel Alert System Shell')
print('Available: app, get_session, settings, asyncio')
"
        ;;
    "dev")
        echo "🔧 Starting development server..."
        exec uvicorn app.main:app \
            --host $DEFAULT_HOST \
            --port $DEFAULT_PORT \
            --reload \
            --log-level debug
        ;;
    "test")
        echo "🧪 Running tests..."
        exec pytest "${@:2}"
        ;;
    *)
        # Default: run the provided command
        echo "🎯 Executing custom command: $*"
        exec "$@"
        ;;
esac