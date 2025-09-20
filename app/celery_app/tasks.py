import asyncio
import time
import traceback
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from celery import Task
from celery.exceptions import Retry, WorkerLostError
from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from .celery import celery_app
from app.core.database import get_session
from app.services.scraping_service import ScrapingService
from app.models.scraping_job import (
    ScrapingJob, JobStatus, JobPriority, JobMetrics,
    DeadLetterJob, SchedulerHealth, RateLimitTracker
)
from app.models.travel_advisory import TravelAdvisory, ContentChangeEvent

logger = structlog.get_logger(__name__)


class BaseScrapingTask(Task):
    """Base task class with common functionality for scraping tasks."""

    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3, 'countdown': 60}
    retry_backoff = True
    retry_backoff_max = 600  # 10 minutes max
    retry_jitter = True

    def __call__(self, *args, **kwargs):
        """Override to add job tracking and error handling."""
        job_id = None
        start_time = time.time()
        process = psutil.Process()

        try:
            # Create job record
            job_id = asyncio.run(self._create_job_record(*args, **kwargs))

            # Update job status to started
            asyncio.run(self._update_job_status(job_id, JobStatus.STARTED, started_at=datetime.utcnow()))

            # Execute the task
            result = super().__call__(*args, **kwargs)

            # Calculate metrics
            end_time = time.time()
            duration = end_time - start_time
            memory_usage = process.memory_info().rss / 1024 / 1024  # MB

            # Update job with success
            asyncio.run(self._update_job_status(
                job_id, JobStatus.SUCCESS,
                completed_at=datetime.utcnow(),
                result=result,
                duration_seconds=duration,
                memory_usage_mb=memory_usage
            ))

            return result

        except Exception as exc:
            end_time = time.time()
            duration = end_time - start_time

            # Handle retry logic
            if self.request.retries < self.max_retries:
                retry_count = self.request.retries + 1

                if job_id:
                    asyncio.run(self._update_job_status(
                        job_id, JobStatus.RETRY,
                        retry_count=retry_count,
                        error_message=str(exc),
                        duration_seconds=duration
                    ))

                logger.warning(
                    "Task failed, retrying",
                    task_name=self.name,
                    job_id=str(job_id),
                    retry_count=retry_count,
                    error=str(exc)
                )

                raise self.retry(exc=exc)
            else:
                # Max retries reached, move to dead letter queue
                if job_id:
                    asyncio.run(self._handle_final_failure(job_id, exc, duration))

                logger.error(
                    "Task failed permanently",
                    task_name=self.name,
                    job_id=str(job_id),
                    error=str(exc),
                    traceback=traceback.format_exc()
                )

                raise exc

    async def _create_job_record(self, *args, **kwargs) -> str:
        """Create a job record in the database."""
        async with get_session() as session:
            job = ScrapingJob(
                celery_task_id=self.request.id,
                task_name=self.name,
                queue_name=self.request.delivery_info.get('routing_key', 'unknown'),
                priority=JobPriority(kwargs.get('priority', 5)),
                job_config={'args': args, 'kwargs': kwargs}
            )

            # Extract source and country if available
            if len(args) > 0:
                job.source = args[0] if isinstance(args[0], str) else None
            if len(args) > 1:
                job.country = args[1] if isinstance(args[1], str) else None

            session.add(job)
            await session.commit()
            return str(job.id)

    async def _update_job_status(self, job_id: str, status: JobStatus, **kwargs):
        """Update job status and metrics."""
        async with get_session() as session:
            query = select(ScrapingJob).where(ScrapingJob.id == job_id)
            result = await session.execute(query)
            job = result.scalar_one_or_none()

            if job:
                job.status = status
                for key, value in kwargs.items():
                    if hasattr(job, key):
                        setattr(job, key, value)

                await session.commit()

    async def _handle_final_failure(self, job_id: str, exc: Exception, duration: float):
        """Handle final task failure and move to dead letter queue."""
        async with get_session() as session:
            # Update original job
            query = select(ScrapingJob).where(ScrapingJob.id == job_id)
            result = await session.execute(query)
            job = result.scalar_one_or_none()

            if job:
                job.status = JobStatus.DEAD_LETTER
                job.completed_at = datetime.utcnow()
                job.error_message = str(exc)
                job.traceback = traceback.format_exc()
                job.duration_seconds = duration

                # Create dead letter record
                dead_letter = DeadLetterJob(
                    original_job_id=job.id,
                    celery_task_id=job.celery_task_id,
                    task_name=job.task_name,
                    original_args=job.job_config.get('args', []),
                    original_kwargs=job.job_config.get('kwargs', {}),
                    failure_reason=str(exc),
                    final_error_message=str(exc),
                    final_traceback=traceback.format_exc(),
                    total_retry_attempts=job.retry_count,
                    manual_intervention_required=True
                )

                session.add(dead_letter)
                await session.commit()


@celery_app.task(bind=True, base=BaseScrapingTask, name='app.celery_app.tasks.scrape_source')
def scrape_source(self, source_name: str, priority: int = 5) -> Dict[str, Any]:
    """
    Scrape travel advisories from a specific source.

    Args:
        source_name: Name of the source to scrape
        priority: Task priority (1-9)

    Returns:
        Dict containing scraping results
    """
    return asyncio.run(_scrape_source_async(source_name))


async def _scrape_source_async(source_name: str) -> Dict[str, Any]:
    """Async implementation of source scraping."""
    scraping_service = ScrapingService()

    try:
        async with get_session() as session:
            logger.info("Starting source scrape", source=source_name)

            # Track rate limiting
            await _track_rate_limit(session, source_name)

            result = await scraping_service.scrape_single_source(session, source_name)

            logger.info(
                "Source scrape completed",
                source=source_name,
                status=result.get('status'),
                new_content=result.get('new_content', 0),
                updated_content=result.get('updated_content', 0)
            )

            return result

    finally:
        await scraping_service.close_scrapers()


@celery_app.task(bind=True, base=BaseScrapingTask, name='app.celery_app.tasks.scrape_country')
def scrape_country(self, source_name: str, country: str, priority: int = 5) -> Dict[str, Any]:
    """
    Scrape travel advisory for a specific country from a specific source.

    Args:
        source_name: Name of the source to scrape
        country: Country to scrape
        priority: Task priority (1-9)

    Returns:
        Dict containing scraping results
    """
    return asyncio.run(_scrape_country_async(source_name, country))


async def _scrape_country_async(source_name: str, country: str) -> Dict[str, Any]:
    """Async implementation of country scraping."""
    scraping_service = ScrapingService()

    try:
        async with get_session() as session:
            logger.info("Starting country scrape", source=source_name, country=country)

            # Track rate limiting
            await _track_rate_limit(session, source_name)

            advisory = await scraping_service.scrape_country_from_source(session, source_name, country)

            if advisory:
                result = {
                    'status': 'success',
                    'advisory_id': str(advisory.id),
                    'title': advisory.title,
                    'risk_level': advisory.risk_level,
                    'content_hash': advisory.content_hash
                }
            else:
                result = {
                    'status': 'failed',
                    'error': f'No advisory found for {country} from {source_name}'
                }

            logger.info("Country scrape completed", source=source_name, country=country, status=result['status'])

            return result

    finally:
        await scraping_service.close_scrapers()


@celery_app.task(bind=True, base=BaseScrapingTask, name='app.celery_app.tasks.scrape_all_sources')
def scrape_all_sources(self, priority: int = 9) -> Dict[str, Any]:
    """
    Scrape travel advisories from all sources.

    Args:
        priority: Task priority (1-9)

    Returns:
        Dict containing scraping results for all sources
    """
    return asyncio.run(_scrape_all_sources_async())


async def _scrape_all_sources_async() -> Dict[str, Any]:
    """Async implementation of all sources scraping."""
    scraping_service = ScrapingService()

    try:
        async with get_session() as session:
            logger.info("Starting all sources scrape")

            result = await scraping_service.scrape_all_sources(session)

            logger.info(
                "All sources scrape completed",
                total_new=result.get('total_new', 0),
                total_updated=result.get('total_updated', 0),
                total_errors=result.get('total_errors', 0)
            )

            return result

    finally:
        await scraping_service.close_scrapers()


@celery_app.task(bind=True, name='app.celery_app.tasks.scrape_high_priority_sources')
def scrape_high_priority_sources(self) -> Dict[str, Any]:
    """Scrape high-priority sources (every 2 hours)."""
    high_priority_sources = ['us_state_dept', 'uk_foreign_office']  # Configure as needed

    results = {}
    for source in high_priority_sources:
        try:
            result = scrape_source.delay(source, priority=9)
            results[source] = {'task_id': result.id, 'status': 'queued'}
        except Exception as e:
            results[source] = {'status': 'error', 'error': str(e)}

    return results


@celery_app.task(bind=True, name='app.celery_app.tasks.scrape_regular_sources')
def scrape_regular_sources(self) -> Dict[str, Any]:
    """Scrape regular sources (every 12 hours)."""
    regular_sources = ['canada_travel']  # Configure as needed

    results = {}
    for source in regular_sources:
        try:
            result = scrape_source.delay(source, priority=5)
            results[source] = {'task_id': result.id, 'status': 'queued'}
        except Exception as e:
            results[source] = {'status': 'error', 'error': str(e)}

    return results


@celery_app.task(bind=True, name='app.celery_app.tasks.monitor_scraping_health')
def monitor_scraping_health(self) -> Dict[str, Any]:
    """Monitor the health of the scraping system."""
    return asyncio.run(_monitor_health_async())


async def _monitor_health_async() -> Dict[str, Any]:
    """Async implementation of health monitoring."""
    health_results = {}

    async with get_session() as session:
        # Check recent job success rates
        cutoff_time = datetime.utcnow() - timedelta(hours=1)

        query = select(ScrapingJob).where(ScrapingJob.created_at >= cutoff_time)
        result = await session.execute(query)
        recent_jobs = result.scalars().all()

        if recent_jobs:
            total_jobs = len(recent_jobs)
            successful_jobs = len([job for job in recent_jobs if job.status == JobStatus.SUCCESS])
            failed_jobs = len([job for job in recent_jobs if job.status in [JobStatus.FAILURE, JobStatus.DEAD_LETTER]])

            success_rate = successful_jobs / total_jobs if total_jobs > 0 else 0

            health_status = 'healthy' if success_rate >= 0.8 else 'degraded' if success_rate >= 0.5 else 'unhealthy'
        else:
            health_status = 'unknown'
            success_rate = None

        # Record health check
        health_check = SchedulerHealth(
            check_type='scraping_jobs',
            status=health_status,
            details={
                'recent_jobs_count': len(recent_jobs),
                'success_rate': success_rate,
                'check_period_hours': 1
            }
        )

        session.add(health_check)
        await session.commit()

        health_results['scraping_jobs'] = {
            'status': health_status,
            'success_rate': success_rate,
            'recent_jobs': len(recent_jobs)
        }

    return health_results


@celery_app.task(bind=True, name='app.celery_app.tasks.generate_metrics_report')
def generate_metrics_report(self, hours_back: int = 6) -> Dict[str, Any]:
    """Generate metrics report for the specified time period."""
    return asyncio.run(_generate_metrics_async(hours_back))


async def _generate_metrics_async(hours_back: int) -> Dict[str, Any]:
    """Async implementation of metrics generation."""
    async with get_session() as session:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        period_start = cutoff_time
        period_end = datetime.utcnow()

        # Query jobs in period
        query = select(ScrapingJob).where(ScrapingJob.created_at >= cutoff_time)
        result = await session.execute(query)
        jobs = result.scalars().all()

        # Calculate metrics by source
        sources_metrics = {}

        for job in jobs:
            source = job.source or 'unknown'

            if source not in sources_metrics:
                sources_metrics[source] = {
                    'total_jobs': 0,
                    'successful_jobs': 0,
                    'failed_jobs': 0,
                    'retried_jobs': 0,
                    'dead_letter_jobs': 0,
                    'durations': []
                }

            metrics = sources_metrics[source]
            metrics['total_jobs'] += 1

            if job.status == JobStatus.SUCCESS:
                metrics['successful_jobs'] += 1
            elif job.status in [JobStatus.FAILURE, JobStatus.DEAD_LETTER]:
                metrics['failed_jobs'] += 1
            elif job.status == JobStatus.RETRY:
                metrics['retried_jobs'] += 1
            elif job.status == JobStatus.DEAD_LETTER:
                metrics['dead_letter_jobs'] += 1

            if job.duration_seconds:
                metrics['durations'].append(job.duration_seconds)

        # Save metrics to database
        for source, metrics in sources_metrics.items():
            durations = metrics['durations']

            job_metrics = JobMetrics(
                period_start=period_start,
                period_end=period_end,
                source=source,
                total_jobs=metrics['total_jobs'],
                successful_jobs=metrics['successful_jobs'],
                failed_jobs=metrics['failed_jobs'],
                retried_jobs=metrics['retried_jobs'],
                dead_letter_jobs=metrics['dead_letter_jobs'],
                avg_duration_seconds=sum(durations) / len(durations) if durations else None,
                min_duration_seconds=min(durations) if durations else None,
                max_duration_seconds=max(durations) if durations else None,
                success_rate=metrics['successful_jobs'] / metrics['total_jobs'] if metrics['total_jobs'] > 0 else None
            )

            session.add(job_metrics)

        await session.commit()

        return {
            'period': f'{period_start} to {period_end}',
            'sources_metrics': {
                source: {k: v for k, v in metrics.items() if k != 'durations'}
                for source, metrics in sources_metrics.items()
            }
        }


@celery_app.task(bind=True, name='app.celery_app.tasks.cleanup_old_data')
def cleanup_old_data(self, days_to_keep: int = 30) -> Dict[str, Any]:
    """Clean up old job records and metrics."""
    return asyncio.run(_cleanup_old_data_async(days_to_keep))


async def _cleanup_old_data_async(days_to_keep: int) -> Dict[str, Any]:
    """Async implementation of data cleanup."""
    async with get_session() as session:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        cleanup_results = {}

        # Clean up old successful jobs (keep failures longer for analysis)
        query = select(ScrapingJob).where(
            and_(
                ScrapingJob.created_at < cutoff_date,
                ScrapingJob.status == JobStatus.SUCCESS
            )
        )
        result = await session.execute(query)
        old_jobs = result.scalars().all()

        for job in old_jobs:
            await session.delete(job)

        cleanup_results['deleted_jobs'] = len(old_jobs)

        # Clean up old metrics (keep for longer period)
        metrics_cutoff = datetime.utcnow() - timedelta(days=days_to_keep * 3)
        query = select(JobMetrics).where(JobMetrics.created_at < metrics_cutoff)
        result = await session.execute(query)
        old_metrics = result.scalars().all()

        for metric in old_metrics:
            await session.delete(metric)

        cleanup_results['deleted_metrics'] = len(old_metrics)

        await session.commit()

        return cleanup_results


@celery_app.task(bind=True, name='app.celery_app.tasks.process_dead_letter_queue')
def process_dead_letter_queue(self) -> Dict[str, Any]:
    """Process items in the dead letter queue."""
    return asyncio.run(_process_dead_letter_async())


async def _process_dead_letter_async() -> Dict[str, Any]:
    """Async implementation of dead letter queue processing."""
    async with get_session() as session:
        # Get unprocessed dead letter jobs
        query = select(DeadLetterJob).where(
            and_(
                DeadLetterJob.processed == False,
                DeadLetterJob.manual_intervention_required == False
            )
        ).limit(10)  # Process in batches

        result = await session.execute(query)
        dead_letters = result.scalars().all()

        processed_count = 0
        requeued_count = 0

        for dl_job in dead_letters:
            try:
                # Simple retry logic - could be more sophisticated
                if dl_job.total_retry_attempts < 5:
                    # Attempt to requeue the job
                    task_name = dl_job.task_name
                    args = dl_job.original_args
                    kwargs = dl_job.original_kwargs

                    # Use Celery's apply_async to requeue
                    celery_app.send_task(task_name, args=args, kwargs=kwargs)

                    dl_job.requeued = True
                    dl_job.processed = True
                    requeued_count += 1
                else:
                    # Too many failures, mark for manual intervention
                    dl_job.manual_intervention_required = True
                    dl_job.processed = True

                processed_count += 1

            except Exception as e:
                logger.error("Error processing dead letter job", dl_job_id=str(dl_job.id), error=str(e))
                dl_job.manual_intervention_required = True
                dl_job.processed = True

        await session.commit()

        return {
            'processed': processed_count,
            'requeued': requeued_count,
            'manual_intervention_required': processed_count - requeued_count
        }


async def _track_rate_limit(session: AsyncSession, source: str):
    """Track rate limiting for a source."""
    now = datetime.utcnow()
    window_start = now.replace(minute=0, second=0, microsecond=0)  # Hourly windows
    window_end = window_start + timedelta(hours=1)

    # Find or create rate limit tracker
    query = select(RateLimitTracker).where(
        and_(
            RateLimitTracker.source == source,
            RateLimitTracker.time_window_start == window_start
        )
    )
    result = await session.execute(query)
    tracker = result.scalar_one_or_none()

    if not tracker:
        # Create new tracker with default limits
        source_limits = {
            'us_state_dept': 60,  # 60 requests per hour
            'uk_foreign_office': 120,  # 120 requests per hour
            'canada_travel': 100  # 100 requests per hour
        }

        tracker = RateLimitTracker(
            source=source,
            time_window_start=window_start,
            time_window_end=window_end,
            requests_allowed=source_limits.get(source, 60)
        )
        session.add(tracker)

    # Increment request count
    tracker.requests_made += 1

    await session.commit()