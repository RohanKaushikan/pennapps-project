import asyncio
import click
from datetime import datetime, timedelta
from typing import Optional, List
import structlog
from tabulate import tabulate

from app.core.database import get_session
from app.models.scraping_job import (
    ScrapingJob, JobStatus, JobMetrics, DeadLetterJob,
    SchedulerHealth, RateLimitTracker
)
from app.celery_app.tasks import (
    scrape_source, scrape_country, scrape_all_sources,
    monitor_scraping_health, generate_metrics_report,
    cleanup_old_data, process_dead_letter_queue
)
from sqlalchemy import select, and_, desc, func

logger = structlog.get_logger(__name__)


@click.group()
def scheduler():
    """Job scheduler management commands."""
    pass


@scheduler.command()
@click.option('--source', '-s', help='Specific source to scrape')
@click.option('--country', '-c', help='Specific country to scrape (requires --source)')
@click.option('--priority', '-p', default=5, help='Task priority (1-9, default: 5)')
def schedule(source: Optional[str], country: Optional[str], priority: int):
    """
    Schedule scraping jobs manually.

    Examples:
        # Schedule all sources
        python -m app.cli.scheduler_cli schedule

        # Schedule specific source
        python -m app.cli.scheduler_cli schedule --source us_state_dept

        # Schedule specific country
        python -m app.cli.scheduler_cli schedule --source uk_foreign_office --country france
    """
    if country and not source:
        click.echo("❌ Error: --country requires --source", err=True)
        return

    if country and source:
        # Schedule specific country scraping
        click.echo(f"📅 Scheduling {country} scrape from {source} (priority: {priority})")
        task = scrape_country.delay(source, country, priority=priority)
        click.echo(f"✅ Task scheduled with ID: {task.id}")

    elif source:
        # Schedule specific source scraping
        click.echo(f"📅 Scheduling {source} scrape (priority: {priority})")
        task = scrape_source.delay(source, priority=priority)
        click.echo(f"✅ Task scheduled with ID: {task.id}")

    else:
        # Schedule all sources scraping
        click.echo(f"📅 Scheduling all sources scrape (priority: {priority})")
        task = scrape_all_sources.delay(priority=priority)
        click.echo(f"✅ Task scheduled with ID: {task.id}")


@scheduler.command()
@click.option('--limit', '-l', default=20, help='Number of jobs to show')
@click.option('--status', '-s', help='Filter by status (pending, started, success, failure, retry, dead_letter)')
@click.option('--source', help='Filter by source')
def jobs(limit: int, status: Optional[str], source: Optional[str]):
    """Show recent scraping jobs."""
    asyncio.run(_jobs_async(limit, status, source))


async def _jobs_async(limit: int, status: Optional[str], source: Optional[str]):
    """Async implementation of jobs command."""
    async with get_session() as session:
        query = select(ScrapingJob).order_by(desc(ScrapingJob.created_at)).limit(limit)

        if status:
            try:
                status_enum = JobStatus(status.upper())
                query = query.where(ScrapingJob.status == status_enum)
            except ValueError:
                click.echo(f"❌ Invalid status: {status}", err=True)
                return

        if source:
            query = query.where(ScrapingJob.source == source)

        result = await session.execute(query)
        jobs = result.scalars().all()

        if not jobs:
            click.echo("📝 No jobs found")
            return

        # Prepare table data
        table_data = []
        for job in jobs:
            duration = f"{job.duration_seconds:.2f}s" if job.duration_seconds else "N/A"
            created_ago = datetime.utcnow() - job.created_at
            ago_str = _format_timedelta(created_ago)

            status_icon = {
                JobStatus.PENDING: "⏳",
                JobStatus.STARTED: "🔄",
                JobStatus.SUCCESS: "✅",
                JobStatus.FAILURE: "❌",
                JobStatus.RETRY: "🔁",
                JobStatus.DEAD_LETTER: "💀"
            }.get(job.status, "❓")

            table_data.append([
                str(job.id)[:8],
                job.task_name.split('.')[-1],
                job.source or "N/A",
                job.country or "N/A",
                f"{status_icon} {job.status.value}",
                duration,
                ago_str,
                job.retry_count
            ])

        headers = ["Job ID", "Task", "Source", "Country", "Status", "Duration", "Created", "Retries"]
        click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))


@scheduler.command()
@click.option('--hours', '-h', default=24, help='Hours to look back for metrics')
def metrics(hours: int):
    """Show job metrics and statistics."""
    asyncio.run(_metrics_async(hours))


async def _metrics_async(hours: int):
    """Async implementation of metrics command."""
    async with get_session() as session:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        # Get job statistics
        query = select(ScrapingJob).where(ScrapingJob.created_at >= cutoff_time)
        result = await session.execute(query)
        jobs = result.scalars().all()

        if not jobs:
            click.echo(f"📊 No jobs found in the last {hours} hours")
            return

        # Calculate overall metrics
        total_jobs = len(jobs)
        successful = len([j for j in jobs if j.status == JobStatus.SUCCESS])
        failed = len([j for j in jobs if j.status in [JobStatus.FAILURE, JobStatus.DEAD_LETTER]])
        retried = len([j for j in jobs if j.status == JobStatus.RETRY])
        pending = len([j for j in jobs if j.status == JobStatus.PENDING])
        running = len([j for j in jobs if j.status == JobStatus.STARTED])

        success_rate = (successful / total_jobs * 100) if total_jobs > 0 else 0

        # Duration statistics
        durations = [j.duration_seconds for j in jobs if j.duration_seconds]
        avg_duration = sum(durations) / len(durations) if durations else 0

        click.echo(f"📊 Job Metrics (Last {hours} hours)")
        click.echo("=" * 50)
        click.echo(f"Total Jobs: {total_jobs}")
        click.echo(f"✅ Successful: {successful} ({successful/total_jobs*100:.1f}%)")
        click.echo(f"❌ Failed: {failed} ({failed/total_jobs*100:.1f}%)")
        click.echo(f"🔁 Retried: {retried} ({retried/total_jobs*100:.1f}%)")
        click.echo(f"⏳ Pending: {pending} ({pending/total_jobs*100:.1f}%)")
        click.echo(f"🔄 Running: {running} ({running/total_jobs*100:.1f}%)")
        click.echo(f"📈 Success Rate: {success_rate:.1f}%")
        click.echo(f"⏱️  Average Duration: {avg_duration:.2f}s")

        # Source breakdown
        sources = {}
        for job in jobs:
            source = job.source or "unknown"
            if source not in sources:
                sources[source] = {'total': 0, 'successful': 0, 'failed': 0}

            sources[source]['total'] += 1
            if job.status == JobStatus.SUCCESS:
                sources[source]['successful'] += 1
            elif job.status in [JobStatus.FAILURE, JobStatus.DEAD_LETTER]:
                sources[source]['failed'] += 1

        if sources:
            click.echo("\n📋 Source Breakdown:")
            table_data = []
            for source, stats in sources.items():
                success_rate = (stats['successful'] / stats['total'] * 100) if stats['total'] > 0 else 0
                table_data.append([
                    source,
                    stats['total'],
                    stats['successful'],
                    stats['failed'],
                    f"{success_rate:.1f}%"
                ])

            headers = ["Source", "Total", "Success", "Failed", "Success Rate"]
            click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))


@scheduler.command()
@click.option('--limit', '-l', default=10, help='Number of dead letter jobs to show')
def dead_letters(limit: int):
    """Show jobs in the dead letter queue."""
    asyncio.run(_dead_letters_async(limit))


async def _dead_letters_async(limit: int):
    """Async implementation of dead letters command."""
    async with get_session() as session:
        query = select(DeadLetterJob).order_by(desc(DeadLetterJob.moved_to_dlq_at)).limit(limit)
        result = await session.execute(query)
        dead_jobs = result.scalars().all()

        if not dead_jobs:
            click.echo("📝 No jobs in dead letter queue")
            return

        click.echo(f"💀 Dead Letter Queue ({len(dead_jobs)} jobs)")
        click.echo("=" * 60)

        for job in dead_jobs:
            moved_ago = datetime.utcnow() - job.moved_to_dlq_at
            ago_str = _format_timedelta(moved_ago)

            status_icons = {
                True: "✅" if not job.manual_intervention_required else "🔧",
                False: "⏳"
            }

            click.echo(f"\n🆔 Job ID: {str(job.id)[:8]}")
            click.echo(f"📋 Task: {job.task_name.split('.')[-1]}")
            click.echo(f"⏰ Moved to DLQ: {ago_str} ago")
            click.echo(f"🔄 Retry Attempts: {job.total_retry_attempts}")
            click.echo(f"📊 Processed: {status_icons[job.processed]} {job.processed}")

            if job.manual_intervention_required:
                click.echo(f"🔧 Manual Intervention Required")

            if job.failure_reason:
                reason = job.failure_reason[:100] + "..." if len(job.failure_reason) > 100 else job.failure_reason
                click.echo(f"❌ Failure: {reason}")


@scheduler.command()
def health():
    """Check scheduler and worker health."""
    asyncio.run(_health_async())


async def _health_async():
    """Async implementation of health command."""
    click.echo("🏥 Scheduler Health Check")
    click.echo("=" * 40)

    # Trigger health monitoring task
    task = monitor_scraping_health.delay()
    click.echo(f"📊 Health check scheduled: {task.id}")

    # Show recent health status
    async with get_session() as session:
        query = select(SchedulerHealth).order_by(desc(SchedulerHealth.checked_at)).limit(5)
        result = await session.execute(query)
        health_checks = result.scalars().all()

        if health_checks:
            click.echo("\n📈 Recent Health Checks:")
            table_data = []

            for check in health_checks:
                checked_ago = datetime.utcnow() - check.checked_at
                ago_str = _format_timedelta(checked_ago)

                status_icon = {
                    'healthy': '✅',
                    'degraded': '⚠️',
                    'unhealthy': '❌',
                    'unknown': '❓'
                }.get(check.status, '❓')

                table_data.append([
                    check.check_type,
                    f"{status_icon} {check.status}",
                    ago_str,
                    check.details.get('success_rate', 'N/A') if check.details else 'N/A'
                ])

            headers = ["Check Type", "Status", "Checked", "Success Rate"]
            click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))


@scheduler.command()
@click.option('--hours', '-h', default=6, help='Generate metrics for last N hours')
def generate_report(hours: int):
    """Generate metrics report."""
    click.echo(f"📊 Generating metrics report for last {hours} hours...")
    task = generate_metrics_report.delay(hours_back=hours)
    click.echo(f"✅ Report generation scheduled: {task.id}")


@scheduler.command()
@click.option('--days', '-d', default=30, help='Keep data for N days')
@click.option('--dry-run', is_flag=True, help='Show what would be deleted without deleting')
def cleanup(days: int, dry_run: bool):
    """Clean up old job data."""
    if dry_run:
        click.echo(f"🔍 Dry run: Would clean up data older than {days} days")
        # TODO: Implement dry run logic
    else:
        click.echo(f"🧹 Cleaning up data older than {days} days...")
        task = cleanup_old_data.delay(days_to_keep=days)
        click.echo(f"✅ Cleanup scheduled: {task.id}")


@scheduler.command()
def process_dlq():
    """Process dead letter queue."""
    click.echo("🔄 Processing dead letter queue...")
    task = process_dead_letter_queue.delay()
    click.echo(f"✅ DLQ processing scheduled: {task.id}")


@scheduler.command()
@click.option('--source', help='Show rate limits for specific source')
def rate_limits(source: Optional[str]):
    """Show current rate limiting status."""
    asyncio.run(_rate_limits_async(source))


async def _rate_limits_async(source: Optional[str]):
    """Async implementation of rate limits command."""
    async with get_session() as session:
        # Get current hour window
        now = datetime.utcnow()
        window_start = now.replace(minute=0, second=0, microsecond=0)

        query = select(RateLimitTracker).where(
            RateLimitTracker.time_window_start == window_start
        )

        if source:
            query = query.where(RateLimitTracker.source == source)

        result = await session.execute(query)
        trackers = result.scalars().all()

        if not trackers:
            click.echo("📊 No rate limit data for current hour")
            return

        click.echo("🚦 Rate Limiting Status (Current Hour)")
        click.echo("=" * 50)

        table_data = []
        for tracker in trackers:
            usage_percent = (tracker.requests_made / tracker.requests_allowed * 100) if tracker.requests_allowed > 0 else 0
            remaining = max(0, tracker.requests_allowed - tracker.requests_made)

            status_icon = "🔴" if usage_percent >= 90 else "🟡" if usage_percent >= 70 else "🟢"

            table_data.append([
                tracker.source,
                f"{tracker.requests_made}/{tracker.requests_allowed}",
                f"{usage_percent:.1f}%",
                remaining,
                status_icon
            ])

        headers = ["Source", "Used/Allowed", "Usage %", "Remaining", "Status"]
        click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))


def _format_timedelta(td: timedelta) -> str:
    """Format timedelta in human-readable format."""
    total_seconds = int(td.total_seconds())

    if total_seconds < 60:
        return f"{total_seconds}s"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}m {seconds}s"
    elif total_seconds < 86400:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours}h {minutes}m"
    else:
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        return f"{days}d {hours}h"


if __name__ == '__main__':
    scheduler()