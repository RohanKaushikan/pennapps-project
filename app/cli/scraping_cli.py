import asyncio
import click
from datetime import datetime
from typing import Optional
import structlog

from app.core.database import get_session
from app.services.scraping_service import ScrapingService

logger = structlog.get_logger(__name__)


@click.group()
def scraping():
    """Travel advisory scraping commands."""
    pass


@scraping.command()
@click.option('--source', '-s', help='Specific source to scrape (us_state_dept, uk_foreign_office, canada_travel)')
@click.option('--country', '-c', help='Specific country to scrape')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def scrape(source: Optional[str], country: Optional[str], verbose: bool):
    """
    Scrape travel advisories from government sources.

    Examples:
        # Scrape all sources
        python -m app.cli.scraping_cli scrape

        # Scrape specific source
        python -m app.cli.scraping_cli scrape --source us_state_dept

        # Scrape specific country from specific source
        python -m app.cli.scraping_cli scrape --source uk_foreign_office --country france
    """
    asyncio.run(_scrape_async(source, country, verbose))


async def _scrape_async(source: Optional[str], country: Optional[str], verbose: bool):
    """Async implementation of the scrape command."""
    if verbose:
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    scraping_service = ScrapingService()

    try:
        async with get_session() as session:
            start_time = datetime.utcnow()

            if country and source:
                # Scrape specific country from specific source
                click.echo(f"🌍 Scraping {country} from {source}...")
                result = await scraping_service.scrape_country_from_source(session, source, country)

                if result:
                    click.echo(f"✅ Successfully scraped {country} from {source}")
                    click.echo(f"   Title: {result.title}")
                    click.echo(f"   Risk Level: {result.risk_level}")
                    click.echo(f"   Last Updated: {result.last_updated_source}")
                else:
                    click.echo(f"❌ Failed to scrape {country} from {source}")

            elif source:
                # Scrape specific source
                click.echo(f"🔄 Scraping all advisories from {source}...")
                result = await scraping_service.scrape_single_source(session, source)

                _display_scraping_results(result, source)

            else:
                # Scrape all sources
                click.echo("🔄 Scraping all travel advisory sources...")
                results = await scraping_service.scrape_all_sources(session)

                _display_all_results(results)

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            click.echo(f"⏱️  Total execution time: {duration:.2f} seconds")

    except Exception as e:
        click.echo(f"❌ Error during scraping: {str(e)}", err=True)
        if verbose:
            logger.exception("Scraping failed")
        raise click.Abort()
    finally:
        await scraping_service.close_scrapers()


def _display_scraping_results(result: dict, source: str):
    """Display results for a single source."""
    status = result.get('status', 'unknown')

    if status == 'completed':
        click.echo(f"✅ {source} scraping completed successfully")
    else:
        click.echo(f"❌ {source} scraping failed")

    click.echo(f"   Total scraped: {result.get('total_scraped', 0)}")
    click.echo(f"   New content: {result.get('new_content', 0)}")
    click.echo(f"   Updated content: {result.get('updated_content', 0)}")
    click.echo(f"   Errors: {result.get('errors', 0)}")
    click.echo(f"   Duration: {result.get('duration_seconds', 0):.2f}s")

    if result.get('error'):
        click.echo(f"   Error: {result['error']}")


def _display_all_results(results: dict):
    """Display results for all sources."""
    click.echo(f"📊 Scraping session {results['session_id']} completed")
    click.echo(f"   Total new content: {results['total_new']}")
    click.echo(f"   Total updated content: {results['total_updated']}")
    click.echo(f"   Total errors: {results['total_errors']}")
    click.echo()

    for source_name, source_result in results['sources'].items():
        click.echo(f"📋 {source_name}:")
        click.echo(f"   Status: {source_result.get('status', 'unknown')}")
        click.echo(f"   Scraped: {source_result.get('total_scraped', 0)}")
        click.echo(f"   New: {source_result.get('new_content', 0)}")
        click.echo(f"   Updated: {source_result.get('updated_content', 0)}")
        click.echo(f"   Errors: {source_result.get('errors', 0)}")
        click.echo(f"   Duration: {source_result.get('duration_seconds', 0):.2f}s")

        if source_result.get('error'):
            click.echo(f"   Error: {source_result['error']}")
        click.echo()


@scraping.command()
@click.option('--limit', '-l', default=20, help='Number of recent changes to show')
def changes(limit: int):
    """Show recent content changes."""
    asyncio.run(_changes_async(limit))


async def _changes_async(limit: int):
    """Async implementation of the changes command."""
    scraping_service = ScrapingService()

    try:
        async with get_session() as session:
            changes = await scraping_service.get_recent_changes(session, limit)

            if not changes:
                click.echo("📝 No recent changes found")
                return

            click.echo(f"📝 Recent {len(changes)} content changes:")
            click.echo()

            for change in changes:
                change_icon = {
                    'new': '🆕',
                    'updated': '🔄',
                    'risk_level_changed': '⚠️',
                    'deleted': '🗑️'
                }.get(change.change_type, '📝')

                click.echo(f"{change_icon} {change.change_type.replace('_', ' ').title()}")
                click.echo(f"   Advisory ID: {change.advisory_id}")
                click.echo(f"   Detected: {change.detected_at}")

                if change.previous_risk_level and change.new_risk_level:
                    click.echo(f"   Risk Level: {change.previous_risk_level} → {change.new_risk_level}")

                if change.change_summary:
                    click.echo(f"   Summary: {change.change_summary}")

                click.echo()

    except Exception as e:
        click.echo(f"❌ Error retrieving changes: {str(e)}", err=True)
        raise click.Abort()
    finally:
        await scraping_service.close_scrapers()


@scraping.command()
@click.argument('country')
def country_info(country: str):
    """Get travel advisories for a specific country from all sources."""
    asyncio.run(_country_info_async(country))


async def _country_info_async(country: str):
    """Async implementation of the country_info command."""
    scraping_service = ScrapingService()

    try:
        async with get_session() as session:
            advisories = await scraping_service.get_advisories_by_country(session, country)

            if not advisories:
                click.echo(f"🔍 No travel advisories found for {country}")
                return

            click.echo(f"🌍 Travel advisories for {country}:")
            click.echo()

            for advisory in advisories:
                source_flag = {
                    'us_state_dept': '🇺🇸',
                    'uk_foreign_office': '🇬🇧',
                    'canada_travel': '🇨🇦'
                }.get(advisory.source, '🏛️')

                click.echo(f"{source_flag} {advisory.source.replace('_', ' ').title()}")
                click.echo(f"   Title: {advisory.title}")
                click.echo(f"   Risk Level: {advisory.risk_level or 'Not specified'}")
                click.echo(f"   Last Updated (Source): {advisory.last_updated_source or 'Not specified'}")
                click.echo(f"   Scraped: {advisory.scraped_at}")
                click.echo(f"   URL: {advisory.url}")

                if advisory.metadata and advisory.metadata.get('summary'):
                    summary = advisory.metadata['summary']
                    if len(summary) > 200:
                        summary = summary[:200] + "..."
                    click.echo(f"   Summary: {summary}")

                click.echo()

    except Exception as e:
        click.echo(f"❌ Error retrieving country info: {str(e)}", err=True)
        raise click.Abort()
    finally:
        await scraping_service.close_scrapers()


@scraping.command()
def sources():
    """List available scraping sources."""
    click.echo("🌐 Available scraping sources:")
    click.echo()
    click.echo("🇺🇸 us_state_dept - US State Department Travel Advisories")
    click.echo("   URL: https://travel.state.gov")
    click.echo("   Coverage: Global travel advisories with 4-level risk system")
    click.echo()
    click.echo("🇬🇧 uk_foreign_office - UK Foreign Office Travel Advice")
    click.echo("   URL: https://www.gov.uk/foreign-travel-advice")
    click.echo("   Coverage: UK government travel advice for all countries")
    click.echo()
    click.echo("🇨🇦 canada_travel - Canadian Government Travel Advisories")
    click.echo("   URL: https://travel.gc.ca")
    click.echo("   Coverage: Canadian government travel advisories and health information")


if __name__ == '__main__':
    scraping()