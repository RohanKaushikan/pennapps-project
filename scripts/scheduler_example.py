#!/usr/bin/env python3
"""
Example script demonstrating the job scheduling system.

This script shows how to:
1. Start and monitor the scheduler
2. Schedule manual jobs
3. Monitor job progress and metrics
4. Handle failures and dead letter queue
5. Manage rate limiting

Usage:
    python scripts/scheduler_example.py
"""

import asyncio
import time
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.celery_app.tasks import (
    scrape_source, scrape_country, scrape_all_sources,
    monitor_scraping_health, generate_metrics_report
)
from app.core.database import get_session
from app.models.scraping_job import ScrapingJob, JobStatus, JobMetrics, DeadLetterJob
from app.services.rate_limiting_service import rate_limiting_service
from sqlalchemy import select, desc


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "="*60)
    print(f"🔧 {title}")
    print("="*60)


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n📋 {title}")
    print("-" * 50)


async def example_schedule_manual_jobs():
    """Example: Schedule jobs manually and monitor progress."""
    print_header("Manual Job Scheduling Example")

    print("🚀 Scheduling manual scraping jobs...")

    # Schedule different types of jobs
    jobs = []

    # 1. Schedule a specific country from a specific source
    print("1️⃣  Scheduling France from UK Foreign Office...")
    task1 = scrape_country.delay('uk_foreign_office', 'France', priority=7)
    jobs.append(('UK-France', task1))

    # 2. Schedule a full source scrape
    print("2️⃣  Scheduling US State Department full scrape...")
    task2 = scrape_source.delay('us_state_dept', priority=8)
    jobs.append(('US-Full', task2))

    # 3. Schedule all sources (high priority)
    print("3️⃣  Scheduling all sources scrape...")
    task3 = scrape_all_sources.delay(priority=9)
    jobs.append(('All-Sources', task3))

    print(f"\n✅ Scheduled {len(jobs)} jobs:")
    for name, task in jobs:
        print(f"   📋 {name}: {task.id}")

    # Monitor job progress
    print("\n🔍 Monitoring job progress...")
    completed = set()

    while len(completed) < len(jobs):
        for name, task in jobs:
            if task.id in completed:
                continue

            status = task.status
            if status in ['SUCCESS', 'FAILURE', 'REVOKED']:
                completed.add(task.id)
                status_icon = "✅" if status == 'SUCCESS' else "❌"
                print(f"   {status_icon} {name}: {status}")

                if status == 'SUCCESS':
                    try:
                        result = task.result
                        if isinstance(result, dict):
                            print(f"      📊 Result: {result.get('status', 'unknown')}")
                            if 'new_content' in result:
                                print(f"      🆕 New: {result['new_content']}")
                            if 'updated_content' in result:
                                print(f"      🔄 Updated: {result['updated_content']}")
                    except Exception as e:
                        print(f"      ⚠️  Could not fetch result: {e}")
                elif status == 'FAILURE':
                    try:
                        print(f"      ❌ Error: {task.traceback}")
                    except Exception as e:
                        print(f"      ❌ Error info unavailable: {e}")

        if len(completed) < len(jobs):
            time.sleep(5)  # Wait 5 seconds before checking again

    print("\n🎉 All manual jobs completed!")


async def example_monitor_job_metrics():
    """Example: Monitor job metrics and statistics."""
    print_header("Job Metrics Monitoring Example")

    async with get_session() as session:
        # Get recent jobs
        print_section("Recent Jobs (Last 24 Hours)")

        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        query = select(ScrapingJob).where(
            ScrapingJob.created_at >= cutoff_time
        ).order_by(desc(ScrapingJob.created_at)).limit(10)

        result = await session.execute(query)
        recent_jobs = result.scalars().all()

        if recent_jobs:
            print(f"📊 Found {len(recent_jobs)} jobs in the last 24 hours:")
            for job in recent_jobs:
                status_icon = {
                    JobStatus.PENDING: "⏳",
                    JobStatus.STARTED: "🔄",
                    JobStatus.SUCCESS: "✅",
                    JobStatus.FAILURE: "❌",
                    JobStatus.RETRY: "🔁",
                    JobStatus.DEAD_LETTER: "💀"
                }.get(job.status, "❓")

                duration = f"{job.duration_seconds:.2f}s" if job.duration_seconds else "N/A"
                print(f"   {status_icon} {job.task_name.split('.')[-1]} "
                      f"({job.source or 'all'}) - {duration}")

        # Calculate success rate
        if recent_jobs:
            successful = len([j for j in recent_jobs if j.status == JobStatus.SUCCESS])
            success_rate = (successful / len(recent_jobs)) * 100
            print(f"\n📈 Success Rate: {success_rate:.1f}% ({successful}/{len(recent_jobs)})")

        # Check dead letter queue
        print_section("Dead Letter Queue Status")

        dlq_query = select(DeadLetterJob).where(
            DeadLetterJob.processed == False
        ).limit(5)

        dlq_result = await session.execute(dlq_query)
        dead_letters = dlq_result.scalars().all()

        if dead_letters:
            print(f"💀 Found {len(dead_letters)} unprocessed items in dead letter queue:")
            for dl_job in dead_letters:
                print(f"   🔧 {dl_job.task_name.split('.')[-1]} - "
                      f"Retries: {dl_job.total_retry_attempts}")
                if dl_job.manual_intervention_required:
                    print(f"      ⚠️  Manual intervention required")
        else:
            print("✅ Dead letter queue is empty")


async def example_rate_limiting_monitoring():
    """Example: Monitor rate limiting status."""
    print_header("Rate Limiting Monitoring Example")

    print_section("Current Rate Limit Status")

    # Get rate limiting status for all sources
    status = await rate_limiting_service.get_rate_limit_status()

    for source, source_status in status.items():
        hourly = source_status['hourly_usage']
        burst = source_status['burst_usage']

        # Status indicators
        hourly_pct = hourly['usage_percent']
        status_icon = "🔴" if hourly_pct >= 90 else "🟡" if hourly_pct >= 70 else "🟢"

        print(f"\n{status_icon} {source.replace('_', ' ').title()}:")
        print(f"   📊 Hourly: {hourly['requests_made']}/{hourly['requests_allowed']} "
              f"({hourly_pct:.1f}%)")
        print(f"   💥 Burst: {burst['recent_requests']}/{burst['burst_limit']} "
              f"(last minute)")
        print(f"   ⏰ Min Delay: {source_status['config']['min_delay_seconds']}s")

        if source_status['avg_response_time_ms']:
            print(f"   📡 Avg Response: {source_status['avg_response_time_ms']:.1f}ms")

    # Demonstrate rate limit checking
    print_section("Rate Limit Checking Example")

    for source in ['us_state_dept', 'uk_foreign_office', 'canada_travel']:
        can_request, delay = await rate_limiting_service.can_make_request(source)

        if can_request:
            print(f"✅ {source}: Can make request now")
        else:
            print(f"⏳ {source}: Must wait {delay:.1f} seconds")


async def example_health_monitoring():
    """Example: Trigger and monitor health checks."""
    print_header("Health Monitoring Example")

    print_section("Triggering Health Check")

    # Trigger a health monitoring task
    print("🏥 Scheduling health check...")
    health_task = monitor_scraping_health.delay()
    print(f"📋 Health check task: {health_task.id}")

    # Wait for completion
    print("⏳ Waiting for health check to complete...")
    timeout = 60  # 1 minute timeout
    start_time = time.time()

    while time.time() - start_time < timeout:
        status = health_task.status
        if status in ['SUCCESS', 'FAILURE']:
            break
        time.sleep(2)

    if health_task.status == 'SUCCESS':
        print("✅ Health check completed successfully")
        try:
            result = health_task.result
            print(f"📊 Health check results: {result}")
        except Exception as e:
            print(f"⚠️  Could not fetch health check results: {e}")
    else:
        print(f"❌ Health check failed or timed out: {health_task.status}")


async def example_metrics_generation():
    """Example: Generate metrics reports."""
    print_header("Metrics Generation Example")

    print_section("Generating Metrics Report")

    # Generate a metrics report for the last 6 hours
    print("📊 Generating metrics report for last 6 hours...")
    metrics_task = generate_metrics_report.delay(hours_back=6)
    print(f"📋 Metrics task: {metrics_task.id}")

    # Wait for completion
    print("⏳ Waiting for metrics generation to complete...")
    timeout = 30  # 30 seconds timeout
    start_time = time.time()

    while time.time() - start_time < timeout:
        status = metrics_task.status
        if status in ['SUCCESS', 'FAILURE']:
            break
        time.sleep(2)

    if metrics_task.status == 'SUCCESS':
        print("✅ Metrics report generated successfully")
        try:
            result = metrics_task.result
            print(f"📈 Metrics summary: {result}")
        except Exception as e:
            print(f"⚠️  Could not fetch metrics results: {e}")
    else:
        print(f"❌ Metrics generation failed or timed out: {metrics_task.status}")


async def example_failure_simulation():
    """Example: Demonstrate failure handling."""
    print_header("Failure Handling Example")

    print_section("Simulating Job Failure")
    print("⚠️  Note: This will attempt to scrape a non-existent country to demonstrate failure handling")

    # Schedule a job that will likely fail
    print("🔧 Scheduling job with invalid country...")
    fail_task = scrape_country.delay('us_state_dept', 'NonExistentCountry', priority=5)
    print(f"📋 Failure simulation task: {fail_task.id}")

    # Monitor the failure and retry process
    print("👀 Monitoring failure and retry process...")
    retries_seen = set()

    for attempt in range(30):  # Check for up to 5 minutes
        status = fail_task.status

        if status == 'RETRY':
            if attempt not in retries_seen:
                retries_seen.add(attempt)
                print(f"🔁 Retry attempt detected (check #{attempt + 1})")

        elif status in ['SUCCESS', 'FAILURE', 'REVOKED']:
            print(f"🏁 Final status: {status}")
            if status == 'FAILURE':
                print("💀 Job will be moved to dead letter queue after all retries")
            break

        time.sleep(10)  # Check every 10 seconds

    print(f"📊 Total retry checks observed: {len(retries_seen)}")


def print_scheduler_commands():
    """Print useful scheduler management commands."""
    print_header("Useful Scheduler Commands")

    commands = [
        ("Start scheduler", "./scripts/start_scheduler.sh start"),
        ("Check status", "./scripts/start_scheduler.sh status"),
        ("View logs", "./scripts/start_scheduler.sh logs celery-worker"),
        ("Stop scheduler", "./scripts/start_scheduler.sh stop"),
        ("View jobs", "python -m app.cli.scheduler_cli jobs"),
        ("View metrics", "python -m app.cli.scheduler_cli metrics"),
        ("Check health", "python -m app.cli.scheduler_cli health"),
        ("View rate limits", "python -m app.cli.scheduler_cli rate-limits"),
        ("Schedule manual job", "python -m app.cli.scheduler_cli schedule --source us_state_dept"),
        ("Monitor Flower UI", "http://localhost:5555"),
    ]

    for description, command in commands:
        print(f"📋 {description}:")
        print(f"   💻 {command}")


async def main():
    """Run all examples."""
    print("🎯 Job Scheduling System - Example Usage")
    print("=" * 60)
    print("This script demonstrates the capabilities of the job scheduling system.")
    print("It will show job scheduling, monitoring, and failure handling.")
    print()

    # Check if user wants to run examples
    response = input("Do you want to run the interactive examples? This will schedule real jobs. (y/N): ")
    if response.lower() not in ['y', 'yes']:
        print_scheduler_commands()
        print("\n👋 Goodbye!")
        return

    try:
        # Run examples in sequence
        print("\n🚀 Starting job scheduling examples...")

        # Example 1: Schedule manual jobs
        await example_schedule_manual_jobs()

        # Wait a moment between examples
        print("\n⏸️  Waiting 30 seconds before next example...")
        time.sleep(30)

        # Example 2: Monitor metrics
        await example_monitor_job_metrics()

        # Example 3: Rate limiting monitoring
        await example_rate_limiting_monitoring()

        # Example 4: Health monitoring
        await example_health_monitoring()

        # Example 5: Metrics generation
        await example_metrics_generation()

        # Ask if user wants to see failure handling
        response = input("\nDo you want to see failure handling (will create a failing job)? (y/N): ")
        if response.lower() in ['y', 'yes']:
            await example_failure_simulation()

        print_header("Examples Completed Successfully!")
        print("🎉 All examples have been completed.")
        print("💡 Use the CLI commands to manage the scheduler:")
        print_scheduler_commands()

    except KeyboardInterrupt:
        print("\n⏹️  Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Check if scheduler is likely running
    print("🔍 Checking if scheduler components are available...")

    try:
        # Try to connect to Redis
        import redis
        r = redis.Redis()
        r.ping()
        print("✅ Redis connection successful")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("   Please start Redis: redis-server")
        sys.exit(1)

    try:
        # Try to import Celery app
        from app.celery_app.celery import celery_app
        print("✅ Celery app import successful")
    except Exception as e:
        print(f"❌ Celery app import failed: {e}")
        sys.exit(1)

    print("🟢 Prerequisites check passed")
    print("\n⚠️  Note: Make sure the Celery worker and beat scheduler are running:")
    print("   ./scripts/start_scheduler.sh start")
    print()

    # Run the main example
    asyncio.run(main())