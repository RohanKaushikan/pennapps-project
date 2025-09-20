import asyncio
import click
import json
from datetime import datetime
from typing import Optional
import structlog
from tabulate import tabulate

from app.api_clients.unified_api_service import UnifiedAPIService
from app.services.api_monitoring_service import api_monitoring_service

logger = structlog.get_logger(__name__)


@click.group()
def api():
    """Government API client management commands."""
    pass


@api.command()
@click.option('--country', '-c', help='Specific country to query')
@click.option('--source', '-s', help='Specific API source to use')
@click.option('--format', 'output_format', default='table', type=click.Choice(['table', 'json']), help='Output format')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def query(country: Optional[str], source: Optional[str], output_format: str, verbose: bool):
    """
    Query government travel advisory APIs.

    Examples:
        # Get all advisories
        python -m app.cli.api_cli query

        # Get specific country
        python -m app.cli.api_cli query --country france

        # Use specific source
        python -m app.cli.api_cli query --country japan --source us_state_department
    """
    asyncio.run(_query_async(country, source, output_format, verbose))


async def _query_async(country: Optional[str], source: Optional[str], output_format: str, verbose: bool):
    """Async implementation of query command."""
    try:
        # Initialize unified API service
        api_service = UnifiedAPIService()
        await api_service.initialize_clients()

        click.echo("🌍 Querying government travel advisory APIs...")

        if verbose:
            click.echo(f"   Country: {country or 'All'}")
            click.echo(f"   Source: {source or 'All enabled sources'}")

        # Make API request
        sources = [source] if source else None
        response = await api_service.get_travel_advisories(
            country=country,
            sources=sources
        )

        # Display results
        if output_format == 'json':
            click.echo(json.dumps(response.dict(), indent=2, default=str))
        else:
            _display_response_table(response, verbose)

        await api_service.close()

    except Exception as e:
        click.echo(f"❌ Error querying APIs: {str(e)}", err=True)
        if verbose:
            logger.exception("API query failed")


def _display_response_table(response, verbose: bool):
    """Display API response in table format."""
    if not response.success:
        click.echo("❌ API request failed")
        if response.errors:
            click.echo("Errors:")
            for source, error in response.errors.items():
                click.echo(f"   {source}: {error}")
        return

    click.echo(f"✅ Retrieved {len(response.data)} advisories")
    click.echo(f"📊 Sources used: {', '.join(response.sources_used)}")
    click.echo(f"⏱️  Response time: {response.response_time_ms:.2f}ms")

    if response.cache_hit:
        click.echo("💾 Cache hit")

    if not response.data:
        click.echo("📝 No advisory data found")
        return

    # Prepare table data
    table_data = []
    for advisory in response.data:
        risk_level = advisory.get('risk_level', 'N/A')
        if len(risk_level) > 30:
            risk_level = risk_level[:30] + "..."

        last_updated = advisory.get('last_updated', 'N/A')
        if last_updated and len(last_updated) > 20:
            last_updated = last_updated[:20] + "..."

        table_data.append([
            advisory.get('country', 'Unknown'),
            advisory.get('source', 'Unknown'),
            risk_level,
            last_updated,
            advisory.get('risk_level_standardized', 'N/A')
        ])

    headers = ["Country", "Source", "Risk Level", "Last Updated", "Standardized"]
    click.echo("\n" + tabulate(table_data, headers=headers, tablefmt="grid"))

    if verbose and response.data:
        click.echo("\n📄 Sample Advisory Content:")
        first_advisory = response.data[0]
        content = first_advisory.get('content', '')
        if len(content) > 300:
            content = content[:300] + "..."
        click.echo(content)


@api.command()
@click.option('--source', '-s', help='Check specific source only')
def health(source: Optional[str]):
    """Check health of API sources."""
    asyncio.run(_health_async(source))


async def _health_async(source: Optional[str]):
    """Async implementation of health command."""
    try:
        # Initialize unified API service
        api_service = UnifiedAPIService()
        await api_service.initialize_clients()

        click.echo("🏥 Checking API health...")

        # Perform health checks
        health_status = await api_service.health_check()

        # Display results
        click.echo("\n📊 API Health Status:")
        table_data = []

        for src, is_healthy in health_status.items():
            if source and src != source:
                continue

            status_icon = "✅" if is_healthy else "❌"
            status_text = "Healthy" if is_healthy else "Unhealthy"

            table_data.append([
                src.replace('_', ' ').title(),
                f"{status_icon} {status_text}"
            ])

        headers = ["Source", "Status"]
        click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))

        await api_service.close()

    except Exception as e:
        click.echo(f"❌ Error checking API health: {str(e)}", err=True)


@api.command()
@click.option('--source', '-s', help='Show metrics for specific source only')
@click.option('--format', 'output_format', default='table', type=click.Choice(['table', 'json']), help='Output format')
def metrics(source: Optional[str], output_format: str):
    """Show API performance metrics."""
    click.echo("📊 API Performance Metrics")
    click.echo("=" * 50)

    # Get metrics from monitoring service
    metrics_summary = api_monitoring_service.get_metrics_summary(source)

    if output_format == 'json':
        click.echo(json.dumps(metrics_summary, indent=2, default=str))
        return

    if not metrics_summary:
        click.echo("📝 No metrics available")
        return

    # Display metrics table
    if source and source in metrics_summary:
        _display_single_source_metrics(metrics_summary[source])
    else:
        _display_all_sources_metrics(metrics_summary)


def _display_single_source_metrics(metrics: dict):
    """Display metrics for a single source."""
    click.echo(f"\n📋 {metrics['source'].replace('_', ' ').title()} Metrics:")

    # Basic statistics
    click.echo(f"   Total Requests: {metrics['total_requests']}")
    click.echo(f"   Successful: {metrics['successful_requests']}")
    click.echo(f"   Failed: {metrics['failed_requests']}")
    click.echo(f"   Error Rate: {metrics['error_rate']}%")

    # Performance metrics
    click.echo(f"\n⏱️  Performance:")
    click.echo(f"   Average Response Time: {metrics['average_response_time_ms']}ms")
    if metrics['min_response_time_ms']:
        click.echo(f"   Min Response Time: {metrics['min_response_time_ms']}ms")
    click.echo(f"   Max Response Time: {metrics['max_response_time_ms']}ms")

    # Response time percentiles
    percentiles = metrics['response_time_percentiles']
    if percentiles:
        click.echo(f"   P50: {percentiles.get('p50', 'N/A')}ms")
        click.echo(f"   P90: {percentiles.get('p90', 'N/A')}ms")
        click.echo(f"   P95: {percentiles.get('p95', 'N/A')}ms")
        click.echo(f"   P99: {percentiles.get('p99', 'N/A')}ms")

    # Cache metrics
    click.echo(f"\n💾 Cache:")
    click.echo(f"   Hit Rate: {metrics['cache_hit_rate']}%")
    click.echo(f"   Hits: {metrics['cache_hits']}")
    click.echo(f"   Misses: {metrics['cache_misses']}")

    # Other metrics
    if metrics['rate_limit_hits'] > 0:
        click.echo(f"\n🚦 Rate Limiting:")
        click.echo(f"   Rate Limit Hits: {metrics['rate_limit_hits']}")

    if metrics['circuit_breaker_opens'] > 0:
        click.echo(f"\n🔌 Circuit Breaker:")
        click.echo(f"   Opens: {metrics['circuit_breaker_opens']}")

    # Error types
    if metrics['error_types']:
        click.echo(f"\n❌ Error Types:")
        for error_type, count in metrics['error_types'].items():
            click.echo(f"   {error_type}: {count}")


def _display_all_sources_metrics(metrics_summary: dict):
    """Display metrics summary for all sources."""
    table_data = []

    for source, metrics in metrics_summary.items():
        table_data.append([
            source.replace('_', ' ').title(),
            metrics['total_requests'],
            f"{metrics['error_rate']}%",
            f"{metrics['average_response_time_ms']:.1f}ms",
            f"{metrics['cache_hit_rate']}%"
        ])

    headers = ["Source", "Requests", "Error Rate", "Avg Response", "Cache Hit"]
    click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))


@api.command()
def alerts():
    """Check for active alerts."""
    click.echo("🚨 Active API Alerts")
    click.echo("=" * 30)

    active_alerts = api_monitoring_service.check_alerts()

    if not active_alerts:
        click.echo("✅ No active alerts")
        return

    for alert in active_alerts:
        alert_icons = {
            'high_error_rate': '📈',
            'slow_response_time': '🐌',
            'consecutive_failures': '💥',
            'low_uptime': '📉'
        }

        icon = alert_icons.get(alert['type'], '⚠️')
        click.echo(f"{icon} {alert['source']}: {alert['message']}")


@api.command()
@click.option('--hours', '-h', default=24, help='Hours to include in report')
@click.option('--format', 'output_format', default='text', type=click.Choice(['text', 'json']), help='Output format')
def report(hours: int, output_format: str):
    """Generate performance report."""
    click.echo(f"📊 API Performance Report (Last {hours} hours)")
    click.echo("=" * 60)

    report_data = api_monitoring_service.get_performance_report(hours_back=hours)

    if output_format == 'json':
        click.echo(json.dumps(report_data, indent=2, default=str))
        return

    # Display text report
    overall = report_data['overall_statistics']
    click.echo(f"\n📈 Overall Statistics:")
    click.echo(f"   Total Requests: {overall['total_requests']}")
    click.echo(f"   Success Rate: {100 - overall['overall_error_rate']:.1f}%")
    click.echo(f"   Healthy Sources: {overall['healthy_sources']}/{overall['total_sources']}")

    # Active alerts
    alerts = report_data['active_alerts']
    if alerts:
        click.echo(f"\n🚨 Active Alerts ({len(alerts)}):")
        for alert in alerts:
            click.echo(f"   • {alert['source']}: {alert['message']}")
    else:
        click.echo(f"\n✅ No active alerts")

    # Per-source summary
    click.echo(f"\n📋 Per-Source Summary:")
    metrics = report_data['metrics_summary']
    if metrics:
        table_data = []
        for source, data in metrics.items():
            table_data.append([
                source.replace('_', ' ').title(),
                data['total_requests'],
                f"{data['error_rate']}%",
                f"{data['average_response_time_ms']:.1f}ms"
            ])

        headers = ["Source", "Requests", "Error Rate", "Avg Response"]
        click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))


@api.command()
@click.option('--source', '-s', help='Reset metrics for specific source only')
@click.confirmation_option(prompt='Are you sure you want to reset metrics?')
def reset_metrics(source: Optional[str]):
    """Reset API metrics."""
    api_monitoring_service.reset_metrics(source)

    if source:
        click.echo(f"✅ Metrics reset for {source}")
    else:
        click.echo("✅ All metrics reset")


@api.command()
def sources():
    """List available API sources."""
    click.echo("🌐 Available API Sources:")
    click.echo()

    sources_info = [
        {
            'name': 'US State Department',
            'key': 'us_state_department',
            'url': 'https://travel.state.gov',
            'description': 'US government travel advisories with 4-level risk system'
        },
        {
            'name': 'UK Foreign Office',
            'key': 'uk_foreign_office',
            'url': 'https://www.gov.uk/foreign-travel-advice',
            'description': 'UK government travel advice and warnings'
        }
    ]

    for source in sources_info:
        click.echo(f"🏛️  {source['name']} ({source['key']})")
        click.echo(f"   URL: {source['url']}")
        click.echo(f"   Description: {source['description']}")
        click.echo()


@api.command()
@click.argument('country')
@click.option('--source', '-s', help='Preferred API source')
@click.option('--compare', '-comp', is_flag=True, help='Compare data from all sources')
def country(country: str, source: Optional[str], compare: bool):
    """Get travel advisory for a specific country."""
    asyncio.run(_country_async(country, source, compare))


async def _country_async(country: str, source: Optional[str], compare: bool):
    """Async implementation of country command."""
    try:
        # Initialize unified API service
        api_service = UnifiedAPIService()
        await api_service.initialize_clients()

        click.echo(f"🌍 Getting travel advisory for {country}...")

        if compare:
            # Get data from all sources for comparison
            response = await api_service.get_travel_advisories(country=country)
        else:
            # Get data with optional source preference
            response = await api_service.get_country_advisory(
                country=country,
                prefer_source=source
            )

        if not response.success or not response.data:
            click.echo(f"❌ No travel advisory found for {country}")
            if response.errors:
                click.echo("Errors:")
                for src, error in response.errors.items():
                    click.echo(f"   {src}: {error}")
            return

        # Display results
        if compare and len(response.data) > 1:
            _display_country_comparison(response.data)
        else:
            _display_single_country_advisory(response.data[0])

        await api_service.close()

    except Exception as e:
        click.echo(f"❌ Error getting country advisory: {str(e)}", err=True)


def _display_single_country_advisory(advisory: dict):
    """Display a single country advisory."""
    click.echo(f"\n📄 {advisory['title']}")
    click.echo("=" * 60)
    click.echo(f"Country: {advisory['country']}")
    click.echo(f"Source: {advisory['source'].replace('_', ' ').title()}")
    click.echo(f"Risk Level: {advisory.get('risk_level', 'N/A')}")
    click.echo(f"Standardized Level: {advisory.get('risk_level_standardized', 'N/A')}")
    click.echo(f"Last Updated: {advisory.get('last_updated', 'N/A')}")
    click.echo(f"Source URL: {advisory.get('source_url', 'N/A')}")

    # Show content preview
    content = advisory.get('content', '')
    if content:
        click.echo(f"\n📝 Advisory Content:")
        if len(content) > 500:
            content = content[:500] + "\n... (content truncated)"
        click.echo(content)


def _display_country_comparison(advisories: list):
    """Display comparison of advisories from different sources."""
    click.echo(f"\n🔍 Comparing advisories for {advisories[0]['country']}:")
    click.echo("=" * 60)

    table_data = []
    for advisory in advisories:
        risk_level = advisory.get('risk_level', 'N/A')
        if len(risk_level) > 40:
            risk_level = risk_level[:40] + "..."

        table_data.append([
            advisory['source'].replace('_', ' ').title(),
            advisory.get('risk_level_standardized', 'N/A'),
            risk_level,
            advisory.get('last_updated', 'N/A')[:10] if advisory.get('last_updated') else 'N/A'
        ])

    headers = ["Source", "Standardized Level", "Original Risk Level", "Last Updated"]
    click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))


if __name__ == '__main__':
    api()