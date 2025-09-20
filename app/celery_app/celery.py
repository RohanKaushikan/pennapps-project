import os
from celery import Celery
from kombu import Queue, Exchange
from app.core.config import settings

# Create Celery instance
celery_app = Celery("travel_advisory_scraper")

# Celery configuration
celery_app.conf.update(
    # Broker settings
    broker_url=getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    result_backend=getattr(settings, 'CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),

    # Task routing
    task_routes={
        'app.celery_app.tasks.scrape_source': {'queue': 'scraping'},
        'app.celery_app.tasks.scrape_country': {'queue': 'scraping'},
        'app.celery_app.tasks.scrape_all_sources': {'queue': 'scraping_high_priority'},
        'app.celery_app.tasks.monitor_scraping_health': {'queue': 'monitoring'},
        'app.celery_app.tasks.cleanup_old_data': {'queue': 'maintenance'},
        'app.celery_app.tasks.generate_metrics_report': {'queue': 'reporting'},
    },

    # Queue definitions
    task_queues=(
        Queue('scraping_high_priority', Exchange('scraping'), routing_key='scraping.high'),
        Queue('scraping', Exchange('scraping'), routing_key='scraping.normal'),
        Queue('monitoring', Exchange('monitoring'), routing_key='monitoring'),
        Queue('maintenance', Exchange('maintenance'), routing_key='maintenance'),
        Queue('reporting', Exchange('reporting'), routing_key='reporting'),
        Queue('dead_letter', Exchange('dead_letter'), routing_key='dead_letter'),
    ),

    # Task execution settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,

    # Result settings
    result_expires=3600,  # 1 hour
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # 55 minutes soft limit

    # Retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,

    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    worker_disable_rate_limits=False,

    # Beat schedule (will be defined separately)
    beat_schedule={},
    beat_scheduler='celery.beat:PersistentScheduler',

    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,

    # Security
    worker_hijack_root_logger=False,
    worker_log_color=False,

    # Rate limiting
    task_annotations={
        'app.celery_app.tasks.scrape_source': {
            'rate_limit': '10/m',  # 10 tasks per minute
        },
        'app.celery_app.tasks.scrape_country': {
            'rate_limit': '30/m',  # 30 tasks per minute
        },
        'app.celery_app.tasks.scrape_all_sources': {
            'rate_limit': '1/h',  # 1 task per hour
        },
    },

    # Dead letter queue settings
    task_reject_on_worker_lost=True,
    task_acks_late=True,
)

# Import tasks to register them
from . import tasks

# Beat schedule configuration
celery_app.conf.beat_schedule = {
    # High-priority sources every 2 hours
    'scrape-high-priority-sources': {
        'task': 'app.celery_app.tasks.scrape_high_priority_sources',
        'schedule': 7200.0,  # 2 hours
        'options': {
            'queue': 'scraping_high_priority',
            'priority': 9,
        }
    },

    # Regular sources every 12 hours
    'scrape-regular-sources': {
        'task': 'app.celery_app.tasks.scrape_regular_sources',
        'schedule': 43200.0,  # 12 hours
        'options': {
            'queue': 'scraping',
            'priority': 5,
        }
    },

    # Health monitoring every 30 minutes
    'monitor-scraping-health': {
        'task': 'app.celery_app.tasks.monitor_scraping_health',
        'schedule': 1800.0,  # 30 minutes
        'options': {
            'queue': 'monitoring',
            'priority': 3,
        }
    },

    # Metrics generation every 6 hours
    'generate-metrics-report': {
        'task': 'app.celery_app.tasks.generate_metrics_report',
        'schedule': 21600.0,  # 6 hours
        'options': {
            'queue': 'reporting',
            'priority': 2,
        }
    },

    # Cleanup old data daily
    'cleanup-old-data': {
        'task': 'app.celery_app.tasks.cleanup_old_data',
        'schedule': 86400.0,  # 24 hours
        'options': {
            'queue': 'maintenance',
            'priority': 1,
        }
    },

    # Dead letter queue processing every hour
    'process-dead-letters': {
        'task': 'app.celery_app.tasks.process_dead_letter_queue',
        'schedule': 3600.0,  # 1 hour
        'options': {
            'queue': 'monitoring',
            'priority': 4,
        }
    },
}