#!/usr/bin/env python3
"""
Example script demonstrating the government API integration system.

This script shows how to:
1. Initialize and configure API clients
2. Query travel advisories from multiple sources
3. Compare data across different government APIs
4. Monitor API performance and health
5. Handle errors and fallbacks
6. Cache responses for better performance

Usage:
    python scripts/api_integration_example.py
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.api_clients.unified_api_service import UnifiedAPIService
from app.services.api_monitoring_service import api_monitoring_service


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "="*70)
    print(f"🔧 {title}")
    print("="*70)


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n📋 {title}")
    print("-" * 60)


async def example_basic_api_usage():
    """Example: Basic API usage with unified service."""
    print_header("Basic API Usage Example")

    # Initialize the unified API service
    api_service = UnifiedAPIService(redis_url="redis://localhost:6379/0")

    try:
        # Initialize clients (API keys would come from environment)
        await api_service.initialize_clients()

        print("✅ API clients initialized successfully")

        # Example 1: Get travel advisory for a specific country
        print_section("Single Country Query")
        print("🌍 Getting travel advisory for France...")

        response = await api_service.get_country_advisory("France")

        if response.success and response.data:
            advisory = response.data[0]
            print(f"✅ Retrieved advisory from: {', '.join(response.sources_used)}")
            print(f"📄 Title: {advisory['title']}")
            print(f"⚠️  Risk Level: {advisory.get('risk_level', 'N/A')}")
            print(f"🏷️  Standardized Level: {advisory.get('risk_level_standardized', 'N/A')}")
            print(f"🔗 Source URL: {advisory.get('source_url', 'N/A')}")

            # Show content preview
            content = advisory.get('content', '')
            if content:
                preview = content[:300] + "..." if len(content) > 300 else content
                print(f"📝 Content Preview:\n{preview}")
        else:
            print("❌ No advisory data found")
            if response.errors:
                for source, error in response.errors.items():
                    print(f"   {source}: {error}")

        # Example 2: Get advisories from all sources
        print_section("Multi-Source Query")
        print("🌐 Getting travel advisories from all sources...")

        response = await api_service.get_travel_advisories()

        if response.success:
            print(f"✅ Retrieved {len(response.data)} advisories")
            print(f"📊 Sources: {', '.join(response.sources_used)}")
            print(f"⏱️  Response time: {response.response_time_ms:.2f}ms")

            if response.cache_hit:
                print("💾 Some responses from cache")

            # Show sample data
            if response.data:
                print("\n📋 Sample Advisories:")
                for i, advisory in enumerate(response.data[:3]):  # Show first 3
                    print(f"   {i+1}. {advisory['country']} ({advisory['source']}) - "
                          f"{advisory.get('risk_level_standardized', 'N/A')}")
        else:
            print("❌ Failed to retrieve advisories")

    except Exception as e:
        print(f"❌ Error in basic API usage: {str(e)}")
    finally:
        await api_service.close()


async def example_source_comparison():
    """Example: Compare data from different sources."""
    print_header("Multi-Source Data Comparison")

    api_service = UnifiedAPIService(redis_url="redis://localhost:6379/0")

    try:
        await api_service.initialize_clients()

        # Countries to compare
        countries = ["Japan", "Germany", "Mexico"]

        for country in countries:
            print_section(f"Comparing {country} Advisories")

            # Get data from all sources for this country
            response = await api_service.get_travel_advisories(country=country)

            if response.success and response.data:
                print(f"📊 Found {len(response.data)} advisory(ies) for {country}")

                # Compare risk levels across sources
                for advisory in response.data:
                    source_name = advisory['source'].replace('_', ' ').title()
                    risk_original = advisory.get('risk_level', 'N/A')
                    risk_standard = advisory.get('risk_level_standardized', 'N/A')

                    print(f"   🏛️  {source_name}:")
                    print(f"      Original: {risk_original}")
                    print(f"      Standardized: {risk_standard}")

                # Check for discrepancies
                risk_levels = [adv.get('risk_level_standardized') for adv in response.data]
                unique_levels = set(filter(None, risk_levels))

                if len(unique_levels) > 1:
                    print(f"   ⚠️  Discrepancy detected: {unique_levels}")
                else:
                    print(f"   ✅ Consistent risk level across sources")

            else:
                print(f"❌ No advisories found for {country}")

    except Exception as e:
        print(f"❌ Error in source comparison: {str(e)}")
    finally:
        await api_service.close()


async def example_performance_monitoring():
    """Example: Demonstrate performance monitoring and metrics."""
    print_header("Performance Monitoring Example")

    api_service = UnifiedAPIService(redis_url="redis://localhost:6379/0")

    try:
        await api_service.initialize_clients()

        # Make several API calls to generate metrics
        print_section("Generating API Metrics")
        countries = ["France", "Germany", "Italy", "Spain", "Japan"]

        print("🔄 Making API calls to generate performance data...")
        for i, country in enumerate(countries, 1):
            print(f"   {i}/5: Querying {country}...")
            start_time = time.time()

            response = await api_service.get_country_advisory(country)

            # Record metrics (this would normally be done automatically)
            response_time = (time.time() - start_time) * 1000
            success = response.success

            for source in response.sources_used:
                api_monitoring_service.record_api_request(
                    source=source,
                    response_time_ms=response_time,
                    success=success,
                    cached=response.cache_hit
                )

            # Add some delay between requests
            await asyncio.sleep(0.5)

        # Display metrics
        print_section("Performance Metrics")
        metrics_summary = api_monitoring_service.get_metrics_summary()

        if metrics_summary:
            for source, metrics in metrics_summary.items():
                print(f"\n🏛️  {source.replace('_', ' ').title()}:")
                print(f"   📊 Total Requests: {metrics['total_requests']}")
                print(f"   ✅ Success Rate: {100 - metrics['error_rate']:.1f}%")
                print(f"   ⏱️  Avg Response Time: {metrics['average_response_time_ms']:.2f}ms")
                print(f"   💾 Cache Hit Rate: {metrics['cache_hit_rate']:.1f}%")

                if metrics['response_time_percentiles']:
                    p = metrics['response_time_percentiles']
                    print(f"   📈 Response Time Percentiles:")
                    print(f"      P50: {p.get('p50', 'N/A')}ms")
                    print(f"      P95: {p.get('p95', 'N/A')}ms")
        else:
            print("📝 No metrics available yet")

        # Check for alerts
        print_section("Alert Monitoring")
        alerts = api_monitoring_service.check_alerts()

        if alerts:
            print(f"🚨 Found {len(alerts)} active alert(s):")
            for alert in alerts:
                print(f"   ⚠️  {alert['source']}: {alert['message']}")
        else:
            print("✅ No active alerts")

    except Exception as e:
        print(f"❌ Error in performance monitoring: {str(e)}")
    finally:
        await api_service.close()


async def example_health_monitoring():
    """Example: API health checks and monitoring."""
    print_header("API Health Monitoring Example")

    api_service = UnifiedAPIService(redis_url="redis://localhost:6379/0")

    try:
        await api_service.initialize_clients()

        print_section("API Health Checks")
        print("🏥 Checking health of all API sources...")

        # Perform health checks
        health_status = await api_service.health_check()

        print("📊 Health Status Results:")
        for source, is_healthy in health_status.items():
            status_icon = "✅" if is_healthy else "❌"
            status_text = "Healthy" if is_healthy else "Unhealthy"
            source_name = source.replace('_', ' ').title()

            print(f"   {status_icon} {source_name}: {status_text}")

        # Get detailed health summary
        print_section("Detailed Health Information")
        health_summary = api_monitoring_service.get_health_summary()

        if health_summary:
            for source, health_data in health_summary.items():
                print(f"\n🏛️  {source.replace('_', ' ').title()}:")
                print(f"   Status: {'✅ Healthy' if health_data['is_healthy'] else '❌ Unhealthy'}")
                print(f"   Last Check: {health_data['last_check']}")

                if health_data['response_time_ms']:
                    print(f"   Response Time: {health_data['response_time_ms']:.2f}ms")

                if health_data['error_message']:
                    print(f"   Error: {health_data['error_message']}")

                print(f"   Consecutive Failures: {health_data['consecutive_failures']}")
                print(f"   Uptime: {health_data['uptime_percentage']:.1f}%")

        # API statistics
        print_section("API Source Statistics")
        stats = await api_service.get_source_statistics()

        for source, stat_data in stats.items():
            print(f"\n📋 {stat_data['name']}:")
            print(f"   Enabled: {'✅' if stat_data['enabled'] else '❌'}")
            print(f"   Priority: {stat_data['priority']}")
            print(f"   Client Available: {'✅' if stat_data['client_available'] else '❌'}")

    except Exception as e:
        print(f"❌ Error in health monitoring: {str(e)}")
    finally:
        await api_service.close()


async def example_error_handling():
    """Example: Error handling and fallback mechanisms."""
    print_header("Error Handling and Fallback Example")

    api_service = UnifiedAPIService(redis_url="redis://localhost:6379/0")

    try:
        await api_service.initialize_clients()

        print_section("Testing Error Scenarios")

        # Test 1: Query non-existent country
        print("🔍 Test 1: Querying non-existent country...")
        response = await api_service.get_country_advisory("NonExistentCountry")

        if not response.success:
            print("✅ Correctly handled non-existent country")
            print(f"   Errors: {response.errors}")
        else:
            print("⚠️  Unexpected success for non-existent country")

        # Test 2: Source fallback
        print("\n🔄 Test 2: Testing source fallback...")

        # Disable one source temporarily
        api_service.disable_source('uk_foreign_office')
        print("   Disabled UK Foreign Office temporarily")

        response = await api_service.get_country_advisory("France")

        if response.success:
            print(f"✅ Successfully retrieved data from: {response.sources_used}")
            print("   Fallback mechanism working correctly")
        else:
            print("❌ Fallback failed")

        # Re-enable the source
        api_service.enable_source('uk_foreign_office')
        print("   Re-enabled UK Foreign Office")

        # Test 3: Graceful degradation
        print("\n📉 Test 3: Testing graceful degradation...")

        # This would simulate API errors in a real scenario
        print("   (In a real scenario, this would test with simulated API errors)")

    except Exception as e:
        print(f"❌ Error in error handling example: {str(e)}")
    finally:
        await api_service.close()


async def example_caching_performance():
    """Example: Demonstrate caching performance benefits."""
    print_header("Caching Performance Example")

    api_service = UnifiedAPIService(redis_url="redis://localhost:6379/0")

    try:
        await api_service.initialize_clients()

        print_section("Cache Performance Test")

        country = "Germany"

        # First request (no cache)
        print(f"🔄 First request for {country} (no cache)...")
        start_time = time.time()
        response1 = await api_service.get_country_advisory(country)
        time1 = (time.time() - start_time) * 1000

        print(f"   ⏱️  Response time: {time1:.2f}ms")
        print(f"   💾 Cache hit: {response1.cache_hit}")

        # Second request (should hit cache)
        print(f"\n🔄 Second request for {country} (should hit cache)...")
        start_time = time.time()
        response2 = await api_service.get_country_advisory(country)
        time2 = (time.time() - start_time) * 1000

        print(f"   ⏱️  Response time: {time2:.2f}ms")
        print(f"   💾 Cache hit: {response2.cache_hit}")

        # Performance comparison
        if time1 > 0 and time2 > 0:
            speedup = time1 / time2
            print(f"\n📊 Performance Improvement:")
            print(f"   🚀 Cache speedup: {speedup:.1f}x faster")
            print(f"   💰 Time saved: {time1 - time2:.2f}ms")

    except Exception as e:
        print(f"❌ Error in caching example: {str(e)}")
    finally:
        await api_service.close()


async def example_concurrent_requests():
    """Example: Concurrent API requests for better performance."""
    print_header("Concurrent Requests Example")

    api_service = UnifiedAPIService(redis_url="redis://localhost:6379/0")

    try:
        await api_service.initialize_clients()

        countries = ["France", "Germany", "Italy", "Spain", "Japan"]

        print_section("Sequential vs Concurrent Requests")

        # Sequential requests
        print("🔄 Making sequential requests...")
        start_time = time.time()

        sequential_results = []
        for country in countries:
            response = await api_service.get_country_advisory(country)
            sequential_results.append(response)

        sequential_time = time.time() - start_time

        # Concurrent requests
        print("🚀 Making concurrent requests...")
        start_time = time.time()

        tasks = [
            api_service.get_country_advisory(country)
            for country in countries
        ]
        concurrent_results = await asyncio.gather(*tasks)

        concurrent_time = time.time() - start_time

        # Performance comparison
        print(f"\n📊 Performance Comparison:")
        print(f"   ⏱️  Sequential: {sequential_time:.2f}s")
        print(f"   🚀 Concurrent: {concurrent_time:.2f}s")

        if sequential_time > 0:
            speedup = sequential_time / concurrent_time
            print(f"   📈 Speedup: {speedup:.1f}x faster")

        # Results summary
        successful_sequential = sum(1 for r in sequential_results if r.success)
        successful_concurrent = sum(1 for r in concurrent_results if r.success)

        print(f"\n✅ Results:")
        print(f"   Sequential successful: {successful_sequential}/{len(countries)}")
        print(f"   Concurrent successful: {successful_concurrent}/{len(countries)}")

    except Exception as e:
        print(f"❌ Error in concurrent requests example: {str(e)}")
    finally:
        await api_service.close()


def print_usage_examples():
    """Print useful CLI command examples."""
    print_header("Useful CLI Commands")

    commands = [
        ("Query specific country", "python -m app.cli.api_cli query --country france"),
        ("Compare sources", "python -m app.cli.api_cli country japan --compare"),
        ("Check API health", "python -m app.cli.api_cli health"),
        ("View performance metrics", "python -m app.cli.api_cli metrics"),
        ("Generate report", "python -m app.cli.api_cli report --hours 24"),
        ("List available sources", "python -m app.cli.api_cli sources"),
        ("Check for alerts", "python -m app.cli.api_cli alerts"),
        ("Reset metrics", "python -m app.cli.api_cli reset-metrics"),
    ]

    for description, command in commands:
        print(f"📋 {description}:")
        print(f"   💻 {command}")


async def main():
    """Run all API integration examples."""
    print("🌍 Government API Integration System - Example Usage")
    print("=" * 70)
    print("This script demonstrates the capabilities of the API integration system.")
    print("It will show unified API access, caching, monitoring, and error handling.")
    print()

    # Check prerequisites
    print("🔍 Checking prerequisites...")

    try:
        # Check Redis connection
        import redis
        r = redis.Redis()
        r.ping()
        print("✅ Redis connection successful")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("   Please start Redis: redis-server")
        print("   Or install Redis: brew install redis")
        return

    # Check if user wants to run examples
    response = input("\nDo you want to run the interactive examples? This will make real API requests. (y/N): ")
    if response.lower() not in ['y', 'yes']:
        print_usage_examples()
        print("\n👋 Goodbye!")
        return

    try:
        # Run examples in sequence
        print("\n🚀 Starting API integration examples...")

        # Basic usage
        await example_basic_api_usage()

        # Wait between examples
        print("\n⏸️  Waiting 5 seconds before next example...")
        await asyncio.sleep(5)

        # Source comparison
        await example_source_comparison()

        # Performance monitoring
        await example_performance_monitoring()

        # Health monitoring
        await example_health_monitoring()

        # Caching performance
        await example_caching_performance()

        # Concurrent requests
        await example_concurrent_requests()

        # Error handling
        await example_error_handling()

        print_header("Examples Completed Successfully!")
        print("🎉 All API integration examples have been completed.")
        print("💡 Use the CLI commands to continue exploring:")
        print_usage_examples()

    except KeyboardInterrupt:
        print("\n⏹️  Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Check if API clients can be imported
    try:
        from app.api_clients.unified_api_service import UnifiedAPIService
        print("✅ API clients import successful")
    except Exception as e:
        print(f"❌ API clients import failed: {e}")
        print("   Please check that all dependencies are installed")
        sys.exit(1)

    print("🟢 Prerequisites check passed")
    print()

    # Run the main example
    asyncio.run(main())