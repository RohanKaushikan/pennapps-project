# Job Scheduling System

A comprehensive job scheduling system built on Celery for automated travel advisory scraping with advanced monitoring, rate limiting, and failure handling capabilities.

## 🚀 Overview

The job scheduling system provides:
- **Automated Scraping** - Scheduled jobs for regular content updates
- **Priority Queues** - High-priority sources every 2 hours, others every 12 hours
- **Rate Limiting** - Respectful scraping with configurable limits
- **Failure Handling** - Retry logic and dead letter queues
- **Monitoring** - Real-time job tracking and health checks
- **Metrics Collection** - Success/failure rates and performance analytics

## 📋 Architecture

### Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Celery Beat   │    │  Celery Workers  │    │    Database     │
│   (Scheduler)   │───►│                  │◄──►│                 │
│                 │    │ • Scraping Tasks │    │ • Job Tracking  │
│ • High Priority │    │ • Health Checks  │    │ • Metrics       │
│ • Regular Tasks │    │ • Maintenance    │    │ • Dead Letters  │
│ • Health Mon.   │    │ • Reporting      │    │ • Rate Limits   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   Rate Limiting  │
                       │    Service       │
                       │                  │
                       │ • Hourly Limits  │
                       │ • Burst Control  │
                       │ • Respectful     │
                       │   Hours          │
                       └──────────────────┘
```

### Queue Structure

- **scraping_high_priority** - US State Dept, UK Foreign Office (every 2 hours)
- **scraping** - Canadian travel advisories (every 12 hours)
- **monitoring** - Health checks and system monitoring
- **maintenance** - Data cleanup and housekeeping
- **reporting** - Metrics generation and reports
- **dead_letter** - Failed jobs requiring intervention

## 🛠️ Setup and Installation

### Prerequisites

1. **Redis** - Message broker and result backend
```bash
# Install Redis
brew install redis  # macOS
sudo apt install redis-server  # Ubuntu

# Start Redis
redis-server
```

2. **Database** - PostgreSQL with existing travel advisory schema
```bash
# Run migrations
alembic upgrade head
```

### Installation

1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

2. **Configure Environment**
```bash
# Set in your environment or .env file
export CELERY_BROKER_URL="redis://localhost:6379/0"
export CELERY_RESULT_BACKEND="redis://localhost:6379/0"
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost/dbname"
```

## 🚀 Quick Start

### Start the Scheduler

```bash
# Use the convenient startup script
./scripts/start_scheduler.sh start

# Or start components individually
celery -A app.celery_app.celery worker --loglevel=info --concurrency=4
celery -A app.celery_app.celery beat --loglevel=info
flower -A app.celery_app.celery --port=5555  # Optional monitoring
```

### Check Status

```bash
# View service status
./scripts/start_scheduler.sh status

# View recent jobs
python -m app.cli.scheduler_cli jobs

# View metrics
python -m app.cli.scheduler_cli metrics

# Check health
python -m app.cli.scheduler_cli health
```

### Manual Job Scheduling

```bash
# Schedule all sources
python -m app.cli.scheduler_cli schedule

# Schedule specific source
python -m app.cli.scheduler_cli schedule --source us_state_dept

# Schedule specific country
python -m app.cli.scheduler_cli schedule --source uk_foreign_office --country france
```

## 📅 Scheduling Configuration

### Default Schedules

```python
# High-priority sources (every 2 hours)
'scrape-high-priority-sources': {
    'task': 'app.celery_app.tasks.scrape_high_priority_sources',
    'schedule': 7200.0,  # 2 hours
    'options': {'queue': 'scraping_high_priority', 'priority': 9}
}

# Regular sources (every 12 hours)
'scrape-regular-sources': {
    'task': 'app.celery_app.tasks.scrape_regular_sources',
    'schedule': 43200.0,  # 12 hours
    'options': {'queue': 'scraping', 'priority': 5}
}

# Health monitoring (every 30 minutes)
'monitor-scraping-health': {
    'task': 'app.celery_app.tasks.monitor_scraping_health',
    'schedule': 1800.0,  # 30 minutes
    'options': {'queue': 'monitoring', 'priority': 3}
}
```

### Source Priority Configuration

```python
# High-priority sources (every 2 hours)
HIGH_PRIORITY_SOURCES = ['us_state_dept', 'uk_foreign_office']

# Regular sources (every 12 hours)
REGULAR_SOURCES = ['canada_travel']
```

## 🚦 Rate Limiting

### Per-Source Limits

```python
source_configs = {
    'us_state_dept': {
        'requests_per_hour': 60,
        'burst_limit': 10,
        'min_delay_seconds': 1.5,
        'respectful_hours': (9, 17),  # 9 AM to 5 PM EST
    },
    'uk_foreign_office': {
        'requests_per_hour': 120,
        'burst_limit': 15,
        'min_delay_seconds': 1.0,
        'respectful_hours': (9, 17),  # 9 AM to 5 PM GMT
    },
    'canada_travel': {
        'requests_per_hour': 100,
        'burst_limit': 12,
        'min_delay_seconds': 1.2,
        'respectful_hours': (9, 17),  # 9 AM to 5 PM EST/PST
    }
}
```

### Rate Limiting Features

- **Hourly Limits** - Maximum requests per hour per source
- **Burst Protection** - Prevent rapid-fire requests
- **Minimum Delays** - Ensure respectful spacing between requests
- **Business Hours** - Extra delays during government office hours
- **Dynamic Adjustment** - Runtime configuration changes

### Monitoring Rate Limits

```bash
# View current rate limit status
python -m app.cli.scheduler_cli rate-limits

# View specific source
python -m app.cli.scheduler_cli rate-limits --source us_state_dept
```

## 🔄 Retry Logic and Dead Letter Queues

### Retry Configuration

```python
class BaseScrapingTask(Task):
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3, 'countdown': 60}
    retry_backoff = True
    retry_backoff_max = 600  # 10 minutes max
    retry_jitter = True
```

### Retry Flow

1. **Initial Failure** - Task fails, marked for retry
2. **Exponential Backoff** - Delays: 60s, 120s, 240s, etc.
3. **Jitter** - Random variation to prevent thundering herd
4. **Max Retries** - After 3 attempts, move to dead letter queue

### Dead Letter Queue Processing

```bash
# View dead letter queue
python -m app.cli.scheduler_cli dead-letters

# Process dead letters (automatic retry if possible)
python -m app.cli.scheduler_cli process-dlq
```

### Manual Intervention

For jobs requiring manual intervention:
1. Review failure reason in dead letter queue
2. Fix underlying issue (network, parsing, etc.)
3. Requeue job or mark as resolved

## 📊 Monitoring and Metrics

### Job Tracking

Every job is tracked with:
- **Status** - pending, started, success, failure, retry, dead_letter
- **Performance** - duration, memory usage, retry count
- **Metadata** - task configuration, error messages, tracebacks

### Metrics Collection

```bash
# View job metrics
python -m app.cli.scheduler_cli metrics --hours 24

# Generate metrics report
python -m app.cli.scheduler_cli generate-report --hours 6

# View recent jobs
python -m app.cli.scheduler_cli jobs --limit 50
```

### Health Monitoring

```bash
# Check system health
python -m app.cli.scheduler_cli health

# Automated health checks run every 30 minutes
# - Job success rates
# - Queue lengths
# - Worker availability
# - Database connectivity
```

### Flower Monitoring

Access web-based monitoring at `http://localhost:5555`
- Real-time task monitoring
- Worker status and statistics
- Task history and results
- Queue management

## 🛡️ Failure Handling

### Failure Types

1. **Network Errors** - Connection timeouts, DNS failures
2. **Parsing Errors** - Website structure changes
3. **Database Errors** - Connection issues, constraint violations
4. **Rate Limiting** - Exceeded configured limits
5. **Resource Errors** - Memory, disk space issues

### Failure Recovery

```python
# Automatic retry with exponential backoff
@celery_app.task(bind=True, base=BaseScrapingTask)
def scrape_source(self, source_name: str):
    try:
        # Scraping logic
        return result
    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        else:
            # Move to dead letter queue
            raise exc
```

### Manual Recovery

```bash
# Review failed jobs
python -m app.cli.scheduler_cli jobs --status failure

# Check dead letter queue
python -m app.cli.scheduler_cli dead-letters

# Reprocess recoverable failures
python -m app.cli.scheduler_cli process-dlq
```

## 🔧 Configuration and Customization

### Celery Configuration

```python
# app/celery_app/celery.py
celery_app.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # 55 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)
```

### Rate Limiting Customization

```python
from app.services.rate_limiting_service import rate_limiting_service

# Adjust rate limits at runtime
await rate_limiting_service.adjust_rate_limits(
    'us_state_dept',
    requests_per_hour=80,
    min_delay_seconds=2.0
)
```

### Custom Schedules

```python
# Add custom scheduled task
celery_app.conf.beat_schedule['custom-task'] = {
    'task': 'app.celery_app.tasks.custom_scraping_task',
    'schedule': crontab(hour=6, minute=0),  # Daily at 6 AM
    'options': {'queue': 'scraping', 'priority': 7}
}
```

## 🚨 Troubleshooting

### Common Issues

#### Workers Not Starting
```bash
# Check Redis connection
redis-cli ping

# Check logs
tail -f logs/celery-worker.log

# Restart workers
./scripts/start_scheduler.sh restart
```

#### Tasks Not Being Scheduled
```bash
# Check Beat scheduler
tail -f logs/celery-beat.log

# Verify schedule configuration
python -c "from app.celery_app.celery import celery_app; print(celery_app.conf.beat_schedule)"
```

#### High Memory Usage
```bash
# Monitor worker memory
python -m app.cli.scheduler_cli metrics

# Adjust worker settings
export CELERY_WORKER_MAX_TASKS_PER_CHILD=25
```

#### Rate Limit Issues
```bash
# Check rate limit status
python -m app.cli.scheduler_cli rate-limits

# Adjust limits if needed
# (See rate limiting customization above)
```

### Debug Mode

```bash
# Start workers in debug mode
celery -A app.celery_app.celery worker --loglevel=debug

# Enable task tracing
export CELERY_TRACE_ENABLES=1
```

### Performance Tuning

```python
# Optimize worker concurrency
CELERY_WORKER_CONCURRENCY = 2  # Conservative for I/O bound tasks

# Adjust prefetch
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # One task at a time

# Memory management
CELERY_WORKER_MAX_TASKS_PER_CHILD = 50  # Restart worker after 50 tasks
```

## 🔍 Maintenance

### Regular Maintenance Tasks

```bash
# Clean up old job data (runs automatically daily)
python -m app.cli.scheduler_cli cleanup --days 30

# Generate metrics reports (runs automatically every 6 hours)
python -m app.cli.scheduler_cli generate-report

# Process dead letter queue (runs automatically hourly)
python -m app.cli.scheduler_cli process-dlq
```

### Log Management

```bash
# View logs by service
./scripts/start_scheduler.sh logs celery-worker
./scripts/start_scheduler.sh logs celery-beat
./scripts/start_scheduler.sh logs flower

# Rotate logs (add to cron)
0 2 * * * /usr/sbin/logrotate /path/to/logrotate.conf
```

### Backup and Recovery

```sql
-- Backup job data
pg_dump -t scraping_jobs -t job_metrics -t dead_letter_jobs dbname > scheduler_backup.sql

-- Restore from backup
psql dbname < scheduler_backup.sql
```

## 📈 Performance Monitoring

### Key Metrics

- **Success Rate** - Percentage of successful jobs
- **Average Duration** - Task execution time
- **Queue Length** - Pending tasks per queue
- **Memory Usage** - Worker memory consumption
- **Rate Limit Utilization** - Request usage vs. limits

### Alerting

Set up alerts for:
- Success rate below 80%
- Queue length exceeding 100 tasks
- Worker memory usage above 500MB
- Rate limit utilization above 90%

### Scaling Considerations

```bash
# Scale workers horizontally
celery -A app.celery_app.celery worker --concurrency=8

# Multiple worker instances
celery multi start worker1 worker2 -A app.celery_app.celery --concurrency=4

# Monitor with Flower
flower -A app.celery_app.celery --port=5555
```

## 🔐 Security Considerations

### Redis Security

```bash
# Use Redis AUTH
export CELERY_BROKER_URL="redis://:password@localhost:6379/0"

# Bind Redis to localhost only
redis-server --bind 127.0.0.1
```

### Task Security

```python
# Sanitize task arguments
@celery_app.task
def secure_task(user_input):
    # Validate and sanitize input
    if not isinstance(user_input, str) or len(user_input) > 100:
        raise ValueError("Invalid input")

    # Proceed with task
```

### Network Security

- Use VPN or private networks for production
- Implement firewall rules for Redis and database
- Use SSL/TLS for external connections

## 📚 API Reference

### CLI Commands

```bash
# Job management
python -m app.cli.scheduler_cli schedule [--source SOURCE] [--country COUNTRY]
python -m app.cli.scheduler_cli jobs [--limit N] [--status STATUS] [--source SOURCE]
python -m app.cli.scheduler_cli metrics [--hours N]

# Monitoring
python -m app.cli.scheduler_cli health
python -m app.cli.scheduler_cli dead-letters [--limit N]
python -m app.cli.scheduler_cli rate-limits [--source SOURCE]

# Maintenance
python -m app.cli.scheduler_cli cleanup [--days N]
python -m app.cli.scheduler_cli generate-report [--hours N]
python -m app.cli.scheduler_cli process-dlq
```

### Programmatic API

```python
from app.celery_app.tasks import scrape_source, scrape_country

# Schedule tasks programmatically
task = scrape_source.delay('us_state_dept', priority=8)
result = task.get(timeout=3600)

# Check task status
print(f"Task {task.id} status: {task.status}")
```

## 🤝 Contributing

### Development Setup

1. Fork the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Start Redis: `redis-server`
4. Run migrations: `alembic upgrade head`
5. Start scheduler: `./scripts/start_scheduler.sh start`

### Adding New Tasks

```python
@celery_app.task(bind=True, base=BaseScrapingTask)
def my_custom_task(self, param1: str, param2: int) -> Dict[str, Any]:
    """Custom scraping task."""
    # Implement task logic
    return {'status': 'success', 'data': result}
```

### Testing

```bash
# Run tests
pytest app/tests/test_scheduler.py

# Test with real Redis
CELERY_ALWAYS_EAGER=False pytest app/tests/
```

---

For more information, see the main project documentation or contact the development team.