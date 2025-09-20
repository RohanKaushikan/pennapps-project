#!/bin/bash

# Travel Advisory Scraper - Scheduler Startup Script
# This script starts the Celery worker and beat scheduler for automated scraping

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PATH="${PROJECT_ROOT}/venv"
LOG_DIR="${PROJECT_ROOT}/logs"
PID_DIR="${PROJECT_ROOT}/pids"

# Create directories if they don't exist
mkdir -p "$LOG_DIR"
mkdir -p "$PID_DIR"

echo -e "${BLUE}🚀 Starting Travel Advisory Scheduler${NC}"
echo "Project Root: $PROJECT_ROOT"

# Function to check if process is running
is_running() {
    local pid_file="$1"
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$pid_file"
            return 1
        fi
    fi
    return 1
}

# Function to start a service
start_service() {
    local service_name="$1"
    local command="$2"
    local pid_file="$PID_DIR/${service_name}.pid"
    local log_file="$LOG_DIR/${service_name}.log"

    if is_running "$pid_file"; then
        echo -e "${YELLOW}⚠️  $service_name is already running${NC}"
        return 0
    fi

    echo -e "${BLUE}▶️  Starting $service_name...${NC}"

    # Start the service in background
    nohup $command > "$log_file" 2>&1 &
    local pid=$!

    # Save PID
    echo $pid > "$pid_file"

    # Wait a moment and check if it's still running
    sleep 2
    if ps -p "$pid" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $service_name started successfully (PID: $pid)${NC}"
        echo "   Log file: $log_file"
    else
        echo -e "${RED}❌ Failed to start $service_name${NC}"
        rm -f "$pid_file"
        return 1
    fi
}

# Function to stop a service
stop_service() {
    local service_name="$1"
    local pid_file="$PID_DIR/${service_name}.pid"

    if is_running "$pid_file"; then
        local pid=$(cat "$pid_file")
        echo -e "${BLUE}⏹️  Stopping $service_name (PID: $pid)...${NC}"

        # Try graceful shutdown first
        kill -TERM "$pid" 2>/dev/null || true

        # Wait up to 10 seconds for graceful shutdown
        for i in {1..10}; do
            if ! ps -p "$pid" > /dev/null 2>&1; then
                echo -e "${GREEN}✅ $service_name stopped gracefully${NC}"
                rm -f "$pid_file"
                return 0
            fi
            sleep 1
        done

        # Force kill if graceful shutdown failed
        echo -e "${YELLOW}⚠️  Force killing $service_name...${NC}"
        kill -KILL "$pid" 2>/dev/null || true
        rm -f "$pid_file"
        echo -e "${GREEN}✅ $service_name stopped${NC}"
    else
        echo -e "${YELLOW}⚠️  $service_name is not running${NC}"
    fi
}

# Function to check service status
status_service() {
    local service_name="$1"
    local pid_file="$PID_DIR/${service_name}.pid"

    if is_running "$pid_file"; then
        local pid=$(cat "$pid_file")
        echo -e "${GREEN}✅ $service_name is running (PID: $pid)${NC}"
    else
        echo -e "${RED}❌ $service_name is not running${NC}"
    fi
}

# Check prerequisites
check_prerequisites() {
    echo -e "${BLUE}🔍 Checking prerequisites...${NC}"

    # Check if virtual environment exists
    if [ ! -d "$VENV_PATH" ]; then
        echo -e "${YELLOW}⚠️  Virtual environment not found at $VENV_PATH${NC}"
        echo "Creating virtual environment..."
        python3 -m venv "$VENV_PATH"
    fi

    # Activate virtual environment
    source "$VENV_PATH/bin/activate"

    # Check if required packages are installed
    if ! python -c "import celery" 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Installing required packages...${NC}"
        pip install -r "$PROJECT_ROOT/requirements.txt"
    fi

    # Check Redis connection
    if ! python -c "import redis; r = redis.Redis(); r.ping()" 2>/dev/null; then
        echo -e "${RED}❌ Cannot connect to Redis. Please ensure Redis is running.${NC}"
        echo "   Start Redis with: redis-server"
        exit 1
    fi

    # Check database connection
    if ! python -c "from app.core.database import get_session; import asyncio; asyncio.run(get_session().__anext__())" 2>/dev/null; then
        echo -e "${RED}❌ Cannot connect to database. Please check your database configuration.${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ Prerequisites check passed${NC}"
}

# Start all services
start_all() {
    check_prerequisites

    echo -e "${BLUE}🚀 Starting all scheduler services...${NC}"

    # Activate virtual environment
    source "$VENV_PATH/bin/activate"

    # Set environment variables
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

    # Start Celery worker
    start_service "celery-worker" "celery -A app.celery_app.celery worker --loglevel=info --concurrency=4 --queues=scraping,scraping_high_priority,monitoring,maintenance,reporting"

    # Start Celery beat scheduler
    start_service "celery-beat" "celery -A app.celery_app.celery beat --loglevel=info --scheduler=celery.beat:PersistentScheduler"

    # Start Flower monitoring (optional)
    if command -v flower >/dev/null 2>&1; then
        start_service "flower" "flower -A app.celery_app.celery --port=5555"
        echo -e "${BLUE}📊 Flower monitoring available at: http://localhost:5555${NC}"
    fi

    echo -e "${GREEN}🎉 All services started successfully!${NC}"
    echo
    echo -e "${BLUE}📋 Management Commands:${NC}"
    echo "  View jobs:     python -m app.cli.scheduler_cli jobs"
    echo "  View metrics:  python -m app.cli.scheduler_cli metrics"
    echo "  Check health:  python -m app.cli.scheduler_cli health"
    echo "  Stop services: $0 stop"
}

# Stop all services
stop_all() {
    echo -e "${BLUE}⏹️  Stopping all scheduler services...${NC}"

    stop_service "flower"
    stop_service "celery-beat"
    stop_service "celery-worker"

    echo -e "${GREEN}✅ All services stopped${NC}"
}

# Show status of all services
status_all() {
    echo -e "${BLUE}📊 Scheduler Service Status${NC}"
    echo "=========================="

    status_service "celery-worker"
    status_service "celery-beat"
    status_service "flower"

    # Show recent job statistics
    if is_running "$PID_DIR/celery-worker.pid"; then
        echo
        echo -e "${BLUE}📈 Quick Stats (last 24 hours):${NC}"
        python -m app.cli.scheduler_cli metrics --hours 24 2>/dev/null || echo "  (Unable to fetch metrics)"
    fi
}

# Restart all services
restart_all() {
    echo -e "${BLUE}🔄 Restarting all scheduler services...${NC}"
    stop_all
    sleep 2
    start_all
}

# Show logs
show_logs() {
    local service_name="$1"
    local log_file="$LOG_DIR/${service_name}.log"

    if [ -f "$log_file" ]; then
        echo -e "${BLUE}📜 Showing logs for $service_name:${NC}"
        tail -f "$log_file"
    else
        echo -e "${RED}❌ Log file not found: $log_file${NC}"
    fi
}

# Main script logic
case "${1:-start}" in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    restart)
        restart_all
        ;;
    status)
        status_all
        ;;
    logs)
        if [ -n "$2" ]; then
            show_logs "$2"
        else
            echo -e "${YELLOW}Usage: $0 logs <service-name>${NC}"
            echo "Available services: celery-worker, celery-beat, flower"
        fi
        ;;
    *)
        echo -e "${BLUE}Travel Advisory Scheduler Management Script${NC}"
        echo
        echo "Usage: $0 <command>"
        echo
        echo "Commands:"
        echo "  start    Start all scheduler services (default)"
        echo "  stop     Stop all scheduler services"
        echo "  restart  Restart all scheduler services"
        echo "  status   Show status of all services"
        echo "  logs     Show logs for a specific service"
        echo
        echo "Examples:"
        echo "  $0 start"
        echo "  $0 status"
        echo "  $0 logs celery-worker"
        echo "  $0 stop"
        ;;
esac