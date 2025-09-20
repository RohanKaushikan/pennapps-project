#!/usr/bin/env python3
"""
Example script demonstrating how to use the travel advisory scraping module.

This script shows how to:
1. Set up the scraping service
2. Scrape data from individual sources
3. Scrape specific countries
4. Monitor changes
5. Access scraped data

Usage:
    python scripts/scraping_example.py
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session, create_tables
from app.services.scraping_service import ScrapingService
from app.models.travel_advisory import TravelAdvisory, ContentChangeEvent


async def setup_database():
    """Set up the database tables if they don't exist."""
    print("🔧 Setting up database tables...")
    await create_tables()
    print("✅ Database setup complete")


async def example_scrape_all_sources():
    """Example: Scrape all travel advisories from all sources."""
    print("\n" + "="*60)
    print("📡 EXAMPLE 1: Scraping all sources")
    print("="*60)

    scraping_service = ScrapingService()

    try:
        async with get_session() as session:
            print("🌍 Starting comprehensive scrape of all government sources...")
            print("   This may take several minutes...")

            start_time = datetime.utcnow()
            results = await scraping_service.scrape_all_sources(session)
            end_time = datetime.utcnow()

            print(f"\n✅ Scraping completed in {(end_time - start_time).total_seconds():.2f} seconds")
            print(f"📊 Session ID: {results['session_id']}")
            print(f"📈 Summary:")
            print(f"   - New advisories: {results['total_new']}")
            print(f"   - Updated advisories: {results['total_updated']}")
            print(f"   - Errors: {results['total_errors']}")

            print(f"\n📋 Per-source breakdown:")
            for source, source_results in results['sources'].items():
                status_icon = "✅" if source_results['status'] == 'completed' else "❌"
                print(f"   {status_icon} {source}:")
                print(f"      - Status: {source_results['status']}")
                print(f"      - Total scraped: {source_results['total_scraped']}")
                print(f"      - New: {source_results['new_content']}")
                print(f"      - Updated: {source_results['updated_content']}")
                print(f"      - Errors: {source_results['errors']}")
                print(f"      - Duration: {source_results['duration_seconds']:.2f}s")

    finally:
        await scraping_service.close_scrapers()


async def example_scrape_single_source():
    """Example: Scrape a single source."""
    print("\n" + "="*60)
    print("🇺🇸 EXAMPLE 2: Scraping US State Department only")
    print("="*60)

    scraping_service = ScrapingService()

    try:
        async with get_session() as session:
            print("🔄 Scraping US State Department travel advisories...")

            results = await scraping_service.scrape_single_source(session, 'us_state_dept')

            status_icon = "✅" if results['status'] == 'completed' else "❌"
            print(f"\n{status_icon} US State Department scraping {results['status']}")
            print(f"📊 Results:")
            print(f"   - Total scraped: {results['total_scraped']}")
            print(f"   - New content: {results['new_content']}")
            print(f"   - Updated content: {results['updated_content']}")
            print(f"   - Errors: {results['errors']}")
            print(f"   - Duration: {results['duration_seconds']:.2f}s")

    finally:
        await scraping_service.close_scrapers()


async def example_scrape_specific_country():
    """Example: Scrape a specific country from a specific source."""
    print("\n" + "="*60)
    print("🇫🇷 EXAMPLE 3: Scraping France from UK Foreign Office")
    print("="*60)

    scraping_service = ScrapingService()

    try:
        async with get_session() as session:
            print("🔍 Scraping France travel advisory from UK Foreign Office...")

            advisory = await scraping_service.scrape_country_from_source(
                session, 'uk_foreign_office', 'France'
            )

            if advisory:
                print("✅ Successfully scraped France advisory")
                print(f"📄 Title: {advisory.title}")
                print(f"⚠️  Risk Level: {advisory.risk_level or 'Not specified'}")
                print(f"🔗 URL: {advisory.url}")
                print(f"📅 Last Updated (Source): {advisory.last_updated_source or 'Not specified'}")
                print(f"🕒 Scraped At: {advisory.scraped_at}")

                # Show content preview
                content_preview = advisory.content[:300] + "..." if len(advisory.content) > 300 else advisory.content
                print(f"📝 Content Preview:\n{content_preview}")
            else:
                print("❌ Failed to scrape France advisory")

    finally:
        await scraping_service.close_scrapers()


async def example_monitor_changes():
    """Example: Monitor recent content changes."""
    print("\n" + "="*60)
    print("📊 EXAMPLE 4: Monitoring recent changes")
    print("="*60)

    scraping_service = ScrapingService()

    try:
        async with get_session() as session:
            print("🔍 Checking for recent content changes...")

            changes = await scraping_service.get_recent_changes(session, limit=10)

            if not changes:
                print("📝 No recent changes found")
                return

            print(f"📈 Found {len(changes)} recent changes:")

            for i, change in enumerate(changes, 1):
                change_icons = {
                    'new': '🆕',
                    'updated': '🔄',
                    'risk_level_changed': '⚠️',
                    'deleted': '🗑️'
                }

                icon = change_icons.get(change.change_type, '📝')
                print(f"\n{i}. {icon} {change.change_type.replace('_', ' ').title()}")
                print(f"   📅 Detected: {change.detected_at}")
                print(f"   🆔 Advisory ID: {change.advisory_id}")

                if change.previous_risk_level and change.new_risk_level:
                    print(f"   ⚠️  Risk Level Change: {change.previous_risk_level} → {change.new_risk_level}")

                if change.change_summary:
                    print(f"   📝 Summary: {change.change_summary}")

    finally:
        await scraping_service.close_scrapers()


async def example_query_country_data():
    """Example: Query all advisories for a specific country."""
    print("\n" + "="*60)
    print("🔍 EXAMPLE 5: Querying all advisories for Japan")
    print("="*60)

    scraping_service = ScrapingService()

    try:
        async with get_session() as session:
            print("🇯🇵 Retrieving all travel advisories for Japan...")

            advisories = await scraping_service.get_advisories_by_country(session, 'Japan')

            if not advisories:
                print("❌ No advisories found for Japan")
                return

            print(f"📊 Found {len(advisories)} advisory(ies) for Japan:")

            source_flags = {
                'us_state_dept': '🇺🇸',
                'uk_foreign_office': '🇬🇧',
                'canada_travel': '🇨🇦'
            }

            for advisory in advisories:
                flag = source_flags.get(advisory.source, '🏛️')
                print(f"\n{flag} {advisory.source.replace('_', ' ').title()}")
                print(f"   📄 Title: {advisory.title}")
                print(f"   ⚠️  Risk Level: {advisory.risk_level or 'Not specified'}")
                print(f"   📅 Last Updated: {advisory.last_updated_source or 'Not specified'}")
                print(f"   🕒 Scraped: {advisory.scraped_at}")
                print(f"   🔗 URL: {advisory.url}")

                # Show metadata if available
                if advisory.metadata:
                    if advisory.metadata.get('summary'):
                        summary = advisory.metadata['summary'][:200] + "..." if len(advisory.metadata['summary']) > 200 else advisory.metadata['summary']
                        print(f"   📝 Summary: {summary}")

                    if advisory.metadata.get('warnings'):
                        print(f"   ⚠️  Warnings: {len(advisory.metadata['warnings'])} warning(s)")

    finally:
        await scraping_service.close_scrapers()


async def main():
    """Run all examples."""
    print("🌍 Travel Advisory Scraping Module - Example Usage")
    print("=" * 60)
    print("This script demonstrates the capabilities of the travel advisory scraping module.")
    print("It will scrape data from government sources and show various usage patterns.")
    print()

    # Check if user wants to run examples
    response = input("Do you want to run the examples? This will make HTTP requests to government websites. (y/N): ")
    if response.lower() not in ['y', 'yes']:
        print("👋 Goodbye!")
        return

    try:
        # Set up database
        await setup_database()

        # Run examples in sequence
        await example_scrape_specific_country()
        await example_scrape_single_source()
        await example_monitor_changes()
        await example_query_country_data()

        # Ask if user wants to run full scrape (takes longer)
        print("\n" + "="*60)
        response = input("Do you want to run a full scrape of all sources? This may take several minutes. (y/N): ")
        if response.lower() in ['y', 'yes']:
            await example_scrape_all_sources()

        print("\n" + "="*60)
        print("✅ All examples completed successfully!")
        print("💡 You can now use the CLI interface: python -m app.cli.scraping_cli --help")
        print("📚 Check the documentation for more advanced usage patterns.")

    except KeyboardInterrupt:
        print("\n⏹️  Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())