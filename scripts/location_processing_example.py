#!/usr/bin/env python3
"""
Location Processing API Example

This script demonstrates the location-triggered processing APIs for:
- Country entry processing with immediate alert generation
- Geofence trigger handling
- Country brief generation
- Emergency alert broadcasting

Run with: python scripts/location_processing_example.py
"""

import asyncio
import httpx
import json
from datetime import datetime
from typing import Dict, Any


class LocationProcessingDemo:
    """Demonstration of location processing APIs."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def demo_country_entry_processing(self):
        """Demonstrate country entry processing."""
        print("\n" + "="*60)
        print("🌍 COUNTRY ENTRY PROCESSING DEMO")
        print("="*60)

        # Simulate user entering France
        entry_request = {
            "user_id": "demo_user_123",
            "device_id": "device_456",
            "coordinates": {
                "latitude": 48.8566,  # Paris coordinates
                "longitude": 2.3522,
                "accuracy_meters": 10.0
            },
            "country_code": "FRA",
            "country_name": "France",
            "previous_country_code": "GBR",
            "metadata": {
                "entry_method": "land_border",
                "demo": True
            }
        }

        print(f"📍 Processing entry to {entry_request['country_name']}...")
        print(f"   User: {entry_request['user_id']}")
        print(f"   Location: {entry_request['coordinates']['latitude']}, {entry_request['coordinates']['longitude']}")
        print(f"   Previous country: {entry_request['previous_country_code']}")

        try:
            response = await self.client.post(
                f"{self.base_url}/api/internal/process-entry",
                json=entry_request
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✅ Entry processed successfully!")
                print(f"   Event ID: {result.get('event_id')}")
                print(f"   Processing time: {result.get('processing_time_ms', 0):.2f}ms")
                print(f"   Alerts generated: {len(result.get('alerts', []))}")

                # Display alerts
                for i, alert in enumerate(result.get('alerts', []), 1):
                    print(f"\n   🚨 Alert {i}:")
                    print(f"      Type: {alert.get('type')}")
                    print(f"      Severity: {alert.get('severity')}")
                    print(f"      Title: {alert.get('title')}")
                    print(f"      Source: {alert.get('source')}")

                # Display recommendations
                recommendations = result.get('recommendations', [])
                if recommendations:
                    print(f"\n   💡 Entry Recommendations:")
                    for rec in recommendations:
                        print(f"      • {rec.get('title')}: {rec.get('description')}")

            else:
                print(f"❌ Entry processing failed: {response.status_code}")
                print(f"   Error: {response.text}")

        except Exception as e:
            print(f"❌ Error processing entry: {str(e)}")

    async def demo_geofence_trigger(self):
        """Demonstrate geofence trigger handling."""
        print("\n" + "="*60)
        print("🏛️ GEOFENCE TRIGGER DEMO")
        print("="*60)

        # First, we'd need to create a geofence zone, but for demo purposes
        # we'll simulate entering a predefined zone near the US Embassy in Paris
        geofence_request = {
            "user_id": "demo_user_123",
            "device_id": "device_456",
            "coordinates": {
                "latitude": 48.8663,  # Near US Embassy Paris
                "longitude": 2.3131,
                "accuracy_meters": 5.0
            },
            "geofence_id": "us_embassy_paris_001",
            "event_type": "enter",
            "metadata": {
                "geofence_name": "US Embassy Paris",
                "demo": True
            }
        }

        print(f"🚪 Processing geofence trigger...")
        print(f"   User: {geofence_request['user_id']}")
        print(f"   Geofence: {geofence_request['geofence_id']}")
        print(f"   Event: {geofence_request['event_type']}")

        try:
            response = await self.client.post(
                f"{self.base_url}/api/internal/geofence-trigger",
                json=geofence_request
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✅ Geofence trigger processed!")
                print(f"   Event ID: {result.get('event_id')}")
                print(f"   Processing time: {result.get('processing_time_ms', 0):.2f}ms")

                geofence_info = result.get('geofence', {})
                if geofence_info:
                    print(f"   Geofence: {geofence_info.get('name')} ({geofence_info.get('type')})")

                alerts = result.get('alerts', [])
                if alerts:
                    print(f"   Alerts triggered: {len(alerts)}")
                    for alert in alerts:
                        print(f"      • {alert.get('title')}")
                else:
                    print("   No alerts triggered for this geofence")

            else:
                print(f"❌ Geofence processing failed: {response.status_code}")
                print(f"   Error: {response.text}")

        except Exception as e:
            print(f"❌ Error processing geofence: {str(e)}")

    async def demo_country_brief_generation(self):
        """Demonstrate country brief generation."""
        print("\n" + "="*60)
        print("📋 COUNTRY BRIEF GENERATION DEMO")
        print("="*60)

        countries_to_brief = ["FRA", "DEU", "JPN"]

        for country_code in countries_to_brief:
            print(f"\n📖 Generating brief for {country_code}...")

            try:
                response = await self.client.get(
                    f"{self.base_url}/api/internal/country-brief/{country_code}",
                    params={"force_refresh": False}
                )

                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Brief generated successfully!")
                    print(f"   Country: {country_code}")
                    print(f"   Cached: {result.get('cached', False)}")
                    print(f"   Processing time: {result.get('processing_time_ms', 0):.2f}ms")
                    print(f"   Generated: {result.get('generated_at')}")

                    brief = result.get('brief', {})
                    if brief:
                        print(f"   Country name: {brief.get('country_name')}")
                        print(f"   Summary: {brief.get('summary')}")

                        advisories = brief.get('travel_advisories', [])
                        if advisories:
                            print(f"   Travel advisories ({len(advisories)}):")
                            for advisory in advisories:
                                print(f"      • {advisory.get('source')}: {advisory.get('risk_level')}")

                        sources = brief.get('sources', [])
                        if sources:
                            print(f"   Data sources: {', '.join(sources)}")

                else:
                    print(f"❌ Brief generation failed: {response.status_code}")
                    print(f"   Error: {response.text}")

            except Exception as e:
                print(f"❌ Error generating brief: {str(e)}")

    async def demo_emergency_alert_broadcast(self):
        """Demonstrate emergency alert broadcasting."""
        print("\n" + "="*60)
        print("🚨 EMERGENCY ALERT BROADCAST DEMO")
        print("="*60)

        # Simulate emergency alert for multiple countries
        alert_request = {
            "title": "Weather Emergency: Severe Storm Warning",
            "message": "A severe storm system is approaching your area. Seek immediate shelter and avoid outdoor activities. Monitor local news for updates.",
            "severity": "high",
            "alert_type": "weather_warning",
            "target_countries": ["FRA", "DEU", "BEL"],
            "target_regions": ["Ile-de-France", "North Rhine-Westphalia"],
            "expires_hours": 12,
            "issued_by": "European Weather Service Demo"
        }

        print(f"📢 Broadcasting emergency alert...")
        print(f"   Title: {alert_request['title']}")
        print(f"   Severity: {alert_request['severity']}")
        print(f"   Target countries: {', '.join(alert_request['target_countries'])}")
        print(f"   Expires in: {alert_request['expires_hours']} hours")

        try:
            response = await self.client.post(
                f"{self.base_url}/api/internal/emergency-alerts",
                json=alert_request
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✅ Emergency alert broadcast successfully!")
                print(f"   Broadcast ID: {result.get('broadcast_id')}")
                print(f"   Recipients: {result.get('recipients', 0)}")
                print(f"   Processing time: {result.get('processing_time_ms', 0):.2f}ms")
                print(f"   Expires: {result.get('expires_at')}")

                if result.get('recipients', 0) == 0:
                    print("   ℹ️  No active users found in target areas")

            else:
                print(f"❌ Alert broadcast failed: {response.status_code}")
                print(f"   Error: {response.text}")

        except Exception as e:
            print(f"❌ Error broadcasting alert: {str(e)}")

    async def demo_health_check(self):
        """Demonstrate health check endpoint."""
        print("\n" + "="*60)
        print("🏥 SYSTEM HEALTH CHECK")
        print("="*60)

        try:
            response = await self.client.get(f"{self.base_url}/api/internal/health")

            if response.status_code == 200:
                result = response.json()
                print(f"✅ Health check completed!")
                print(f"   Overall status: {result.get('status')}")
                print(f"   Timestamp: {result.get('timestamp')}")

                services = result.get('services', {})
                print(f"\n   🔧 Service Status:")
                for service, status in services.items():
                    status_icon = "✅" if status else "❌"
                    print(f"      {status_icon} {service}: {'Healthy' if status else 'Unhealthy'}")

                stats = result.get('processing_stats', {})
                if stats:
                    print(f"\n   📊 Processing Statistics (last {stats.get('time_period_hours', 24)}h):")
                    print(f"      Total events: {stats.get('total_events', 0)}")
                    print(f"      Country entries: {stats.get('country_entries', 0)}")
                    print(f"      Geofence triggers: {stats.get('geofence_triggers', 0)}")
                    print(f"      Alerts generated: {stats.get('alerts_generated', 0)}")
                    print(f"      Avg processing time: {stats.get('average_processing_time_ms', 0):.2f}ms")
                    print(f"      Error rate: {stats.get('error_rate', 0):.2f}%")

            else:
                print(f"❌ Health check failed: {response.status_code}")
                print(f"   Error: {response.text}")

        except Exception as e:
            print(f"❌ Error during health check: {str(e)}")

    async def demo_processing_statistics(self):
        """Demonstrate processing statistics endpoint."""
        print("\n" + "="*60)
        print("📊 PROCESSING STATISTICS")
        print("="*60)

        try:
            response = await self.client.get(
                f"{self.base_url}/api/internal/stats",
                params={"hours": 24}
            )

            if response.status_code == 200:
                stats = response.json()
                print(f"✅ Statistics retrieved!")
                print(f"   Time period: {stats.get('time_period_hours', 24)} hours")
                print(f"   Total events processed: {stats.get('total_events', 0)}")
                print(f"   Country entry events: {stats.get('country_entries', 0)}")
                print(f"   Geofence trigger events: {stats.get('geofence_triggers', 0)}")
                print(f"   Alerts generated: {stats.get('alerts_generated', 0)}")
                print(f"   Average processing time: {stats.get('average_processing_time_ms', 0):.2f}ms")
                print(f"   Error rate: {stats.get('error_rate', 0):.2f}%")

            else:
                print(f"❌ Statistics retrieval failed: {response.status_code}")
                print(f"   Error: {response.text}")

        except Exception as e:
            print(f"❌ Error retrieving statistics: {str(e)}")


async def main():
    """Run the location processing demonstration."""
    print("🚀 Location Processing API Demonstration")
    print("This demo showcases real-time location processing and alert generation")

    demo = LocationProcessingDemo()

    try:
        # Run all demonstrations
        await demo.demo_health_check()
        await demo.demo_country_entry_processing()
        await demo.demo_geofence_trigger()
        await demo.demo_country_brief_generation()
        await demo.demo_emergency_alert_broadcast()
        await demo.demo_processing_statistics()

        print("\n" + "="*60)
        print("🎉 DEMONSTRATION COMPLETED")
        print("="*60)
        print("All location processing APIs have been demonstrated!")
        print("\nKey Features Showcased:")
        print("• Real-time country entry processing with immediate alerts")
        print("• Geofence trigger handling for location-based notifications")
        print("• Comprehensive country brief generation with caching")
        print("• Emergency alert broadcasting to targeted geographic areas")
        print("• System health monitoring and processing statistics")
        print("\nFor production use:")
        print("• Configure proper authentication and authorization")
        print("• Set up real notification channels (push, SMS, email)")
        print("• Create geofence zones for your specific use cases")
        print("• Monitor system performance and adjust thresholds")

    except KeyboardInterrupt:
        print("\n\n⚠️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
    finally:
        await demo.close()


if __name__ == "__main__":
    asyncio.run(main())