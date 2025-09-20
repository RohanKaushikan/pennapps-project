from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, Index, Boolean, Enum
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base
import uuid
import enum


class JobStatus(enum.Enum):
    PENDING = "pending"
    STARTED = "started"
    RETRY = "retry"
    FAILURE = "failure"
    SUCCESS = "success"
    REVOKED = "revoked"
    DEAD_LETTER = "dead_letter"


class JobPriority(enum.Enum):
    LOW = 1
    NORMAL = 5
    HIGH = 7
    CRITICAL = 9


class ScrapingJob(Base):
    __tablename__ = "scraping_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    celery_task_id = Column(String(255), nullable=False, unique=True)
    task_name = Column(String(255), nullable=False)
    source = Column(String(100), nullable=True)  # Specific source being scraped
    country = Column(String(100), nullable=True)  # Specific country (if applicable)

    # Job metadata
    priority = Column(Enum(JobPriority), default=JobPriority.NORMAL)
    queue_name = Column(String(100), nullable=False)
    scheduled_at = Column(DateTime, nullable=True)  # For scheduled jobs
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Status tracking
    status = Column(Enum(JobStatus), default=JobStatus.PENDING)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # Results and errors
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    traceback = Column(Text, nullable=True)

    # Performance metrics
    duration_seconds = Column(Float, nullable=True)
    memory_usage_mb = Column(Float, nullable=True)

    # Job configuration
    job_config = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_scraping_jobs_celery_task_id', 'celery_task_id'),
        Index('idx_scraping_jobs_status', 'status'),
        Index('idx_scraping_jobs_source', 'source'),
        Index('idx_scraping_jobs_priority', 'priority'),
        Index('idx_scraping_jobs_scheduled_at', 'scheduled_at'),
        Index('idx_scraping_jobs_created_at', 'created_at'),
        Index('idx_scraping_jobs_task_name', 'task_name'),
    )

    def __repr__(self):
        return f"<ScrapingJob(task_name='{self.task_name}', status='{self.status.value}', source='{self.source}')>"


class JobMetrics(Base):
    __tablename__ = "job_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Time period for metrics
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Source-specific metrics
    source = Column(String(100), nullable=True)

    # Aggregated metrics
    total_jobs = Column(Integer, default=0)
    successful_jobs = Column(Integer, default=0)
    failed_jobs = Column(Integer, default=0)
    retried_jobs = Column(Integer, default=0)
    dead_letter_jobs = Column(Integer, default=0)

    # Performance metrics
    avg_duration_seconds = Column(Float, nullable=True)
    min_duration_seconds = Column(Float, nullable=True)
    max_duration_seconds = Column(Float, nullable=True)
    avg_memory_usage_mb = Column(Float, nullable=True)

    # Success rate
    success_rate = Column(Float, nullable=True)

    # Content metrics
    new_advisories_count = Column(Integer, default=0)
    updated_advisories_count = Column(Integer, default=0)

    # Additional metrics
    job_metadata = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_job_metrics_period', 'period_start', 'period_end'),
        Index('idx_job_metrics_source', 'source'),
        Index('idx_job_metrics_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<JobMetrics(source='{self.source}', period='{self.period_start} - {self.period_end}', success_rate={self.success_rate})>"


class DeadLetterJob(Base):
    __tablename__ = "dead_letter_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_job_id = Column(UUID(as_uuid=True), nullable=False)
    celery_task_id = Column(String(255), nullable=False)
    task_name = Column(String(255), nullable=False)

    # Original job details
    original_args = Column(JSON, nullable=True)
    original_kwargs = Column(JSON, nullable=True)

    # Failure information
    failure_reason = Column(Text, nullable=False)
    final_error_message = Column(Text, nullable=True)
    final_traceback = Column(Text, nullable=True)
    total_retry_attempts = Column(Integer, default=0)

    # Processing status
    processed = Column(Boolean, default=False)
    requeued = Column(Boolean, default=False)
    manual_intervention_required = Column(Boolean, default=False)

    # Resolution
    resolution_notes = Column(Text, nullable=True)
    resolved_by = Column(String(100), nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    # Timestamps
    moved_to_dlq_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_dead_letter_jobs_processed', 'processed'),
        Index('idx_dead_letter_jobs_task_name', 'task_name'),
        Index('idx_dead_letter_jobs_moved_at', 'moved_to_dlq_at'),
        Index('idx_dead_letter_jobs_manual_intervention', 'manual_intervention_required'),
    )

    def __repr__(self):
        return f"<DeadLetterJob(task_name='{self.task_name}', processed={self.processed}, manual_intervention={self.manual_intervention_required})>"


class SchedulerHealth(Base):
    __tablename__ = "scheduler_health"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Health check details
    check_type = Column(String(100), nullable=False)  # 'beat', 'worker', 'broker', 'backend'
    status = Column(String(50), nullable=False)  # 'healthy', 'unhealthy', 'degraded'

    # Metrics
    response_time_ms = Column(Float, nullable=True)
    queue_length = Column(Integer, nullable=True)
    active_workers = Column(Integer, nullable=True)

    # Details
    details = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    # Timestamps
    checked_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_scheduler_health_check_type', 'check_type'),
        Index('idx_scheduler_health_status', 'status'),
        Index('idx_scheduler_health_checked_at', 'checked_at'),
    )

    def __repr__(self):
        return f"<SchedulerHealth(check_type='{self.check_type}', status='{self.status}', checked_at='{self.checked_at}')>"


class RateLimitTracker(Base):
    __tablename__ = "rate_limit_tracker"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Rate limiting details
    source = Column(String(100), nullable=False)
    time_window_start = Column(DateTime, nullable=False)
    time_window_end = Column(DateTime, nullable=False)

    # Counters
    requests_made = Column(Integer, default=0)
    requests_allowed = Column(Integer, nullable=False)
    requests_blocked = Column(Integer, default=0)

    # Performance
    avg_response_time_ms = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_rate_limit_tracker_source', 'source'),
        Index('idx_rate_limit_tracker_window', 'time_window_start', 'time_window_end'),
        Index('idx_rate_limit_tracker_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<RateLimitTracker(source='{self.source}', requests={self.requests_made}/{self.requests_allowed})>"