"""
Location services for geofencing and country detection.
Handles coordinate-based country detection and border crossing logic.
"""

import asyncio
import logging
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.country import Country
from app.models.alert import Alert
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LocationData:
    """Location data structure."""
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    timestamp: Optional[datetime] = None


@dataclass
class CountryDetectionResult:
    """Result of country detection from coordinates."""
    country_code: Optional[str] = None
    country_name: Optional[str] = None
    confidence: float = 0.0
    is_border_region: bool = False
    distance_to_border: Optional[float] = None


class LocationService:
    """Service for handling location-based operations."""

    # Country boundary data (simplified - in production, use a proper GIS service)
    COUNTRY_BOUNDARIES = {
        "US": {
            "bounds": {"north": 49.0, "south": 24.0, "east": -66.0, "west": -125.0},
            "center": {"lat": 39.8283, "lng": -98.5795}
        },
        "CA": {
            "bounds": {"north": 83.0, "south": 41.0, "east": -52.0, "west": -141.0},
            "center": {"lat": 56.1304, "lng": -106.3468}
        },
        "GB": {
            "bounds": {"north": 60.9, "south": 49.9, "east": 1.8, "west": -8.6},
            "center": {"lat": 55.3781, "lng": -3.4360}
        },
        "FR": {
            "bounds": {"north": 51.1, "south": 41.3, "east": 9.6, "west": -5.1},
            "center": {"lat": 46.2276, "lng": 2.2137}
        },
        "DE": {
            "bounds": {"north": 55.1, "south": 47.3, "east": 15.0, "west": 5.9},
            "center": {"lat": 51.1657, "lng": 10.4515}
        },
        "JP": {
            "bounds": {"north": 45.6, "south": 24.2, "east": 153.9, "west": 122.9},
            "center": {"lat": 36.2048, "lng": 138.2529}
        },
        "AU": {
            "bounds": {"north": -9.0, "south": -54.8, "east": 159.1, "west": 112.9},
            "center": {"lat": -25.2744, "lng": 133.7751}
        },
        "BR": {
            "bounds": {"north": 5.3, "south": -33.8, "east": -28.8, "west": -73.9},
            "center": {"lat": -14.2350, "lng": -51.9253}
        },
        "IN": {
            "bounds": {"north": 37.1, "south": 6.4, "east": 97.4, "west": 68.1},
            "center": {"lat": 20.5937, "lng": 78.9629}
        },
        "CN": {
            "bounds": {"north": 53.6, "south": 15.8, "east": 134.8, "west": 73.6},
            "center": {"lat": 35.8617, "lng": 104.1954}
        },
        "MX": {
            "bounds": {"north": 32.7, "south": 14.5, "east": -86.7, "west": -118.4},
            "center": {"lat": 23.6345, "lng": -102.5528}
        },
        "ES": {
            "bounds": {"north": 43.8, "south": 27.6, "east": 4.3, "west": -18.2},
            "center": {"lat": 40.4637, "lng": -3.7492}
        },
        "IT": {
            "bounds": {"north": 47.1, "south": 35.5, "east": 18.5, "west": 6.6},
            "center": {"lat": 41.8719, "lng": 12.5674}
        },
        "RU": {
            "bounds": {"north": 81.9, "south": 41.2, "east": -169.0, "west": 19.6},
            "center": {"lat": 61.5240, "lng": 105.3188}
        },
        "TH": {
            "bounds": {"north": 20.5, "south": 5.6, "east": 105.6, "west": 97.3},
            "center": {"lat": 15.8700, "lng": 100.9925}
        }
    }

    # Border proximity threshold in degrees (approximately 5km)
    BORDER_THRESHOLD = 0.045

    def __init__(self, session: AsyncSession):
        self.session = session

    async def detect_country_from_coordinates(
        self,
        latitude: float,
        longitude: float
    ) -> CountryDetectionResult:
        """
        Detect country from coordinates using simplified boundary checking.
        In production, this would use a proper GIS service like Google Maps API.
        """
        best_match = CountryDetectionResult()
        min_distance = float('inf')

        for country_code, data in self.COUNTRY_BOUNDARIES.items():
            bounds = data["bounds"]
            center = data["center"]

            # Check if coordinates are within country bounds
            if (bounds["south"] <= latitude <= bounds["north"] and
                bounds["west"] <= longitude <= bounds["east"]):

                # Calculate distance to center for confidence
                distance = self._calculate_distance(
                    latitude, longitude,
                    center["lat"], center["lng"]
                )

                if distance < min_distance:
                    min_distance = distance

                    # Check if near border
                    is_near_border = self._is_near_border(latitude, longitude, bounds)

                    # Get country name from database
                    country_name = await self._get_country_name(country_code)

                    best_match = CountryDetectionResult(
                        country_code=country_code,
                        country_name=country_name,
                        confidence=max(0.1, 1.0 - (distance / 1000)),  # Normalize confidence
                        is_border_region=is_near_border,
                        distance_to_border=self._distance_to_border(latitude, longitude, bounds)
                    )

        # If no exact match, try reverse geocoding service
        if not best_match.country_code:
            best_match = await self._reverse_geocode(latitude, longitude)

        return best_match

    async def get_country_by_code(self, country_code: str) -> Optional[Country]:
        """Get country from database by code."""
        result = await self.session.execute(
            select(Country).where(Country.code == country_code.upper())
        )
        return result.scalar_one_or_none()

    async def get_critical_alerts_for_country(
        self,
        country_code: str,
        risk_level_threshold: int = 3
    ) -> List[Alert]:
        """Get critical alerts for a specific country."""
        # Get country
        country = await self.get_country_by_code(country_code)
        if not country:
            return []

        # Get critical alerts
        result = await self.session.execute(
            select(Alert).where(
                Alert.country_id == country.id,
                Alert.risk_level >= risk_level_threshold,
                # Active alerts (not expired)
                (Alert.expires_at.is_(None) | (Alert.expires_at > datetime.utcnow()))
            ).order_by(Alert.risk_level.desc(), Alert.created_at.desc())
        )

        return result.scalars().all()

    async def get_immediate_alerts_for_country(self, country_code: str) -> List[Alert]:
        """Get immediate/critical alerts for country entry."""
        return await self.get_critical_alerts_for_country(country_code, risk_level_threshold=4)

    async def generate_entry_brief(self, country_code: str) -> Dict:
        """Generate a 60-second legal brief for country arrival."""
        country = await self.get_country_by_code(country_code)
        if not country:
            return {"error": "Country not found"}

        # Get all active alerts for the country
        result = await self.session.execute(
            select(Alert).where(
                Alert.country_id == country.id,
                # Active alerts only
                (Alert.expires_at.is_(None) | (Alert.expires_at > datetime.utcnow()))
            ).order_by(Alert.risk_level.desc(), Alert.created_at.desc())
        )
        alerts = result.scalars().all()

        # Categorize alerts
        critical_alerts = [a for a in alerts if a.risk_level >= 4]
        visa_legal_alerts = [a for a in alerts if any(cat in ['visa', 'legal'] for cat in a.categories)]
        safety_alerts = [a for a in alerts if 'safety' in a.categories]
        health_alerts = [a for a in alerts if 'health' in a.categories]

        # Generate brief summary
        brief = {
            "country": {
                "code": country.code,
                "name": country.name,
                "region": country.region
            },
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_alerts": len(alerts),
                "critical_count": len(critical_alerts),
                "risk_level": "HIGH" if critical_alerts else "MEDIUM" if len(alerts) > 3 else "LOW"
            },
            "immediate_actions": self._generate_immediate_actions(alerts),
            "key_alerts": {
                "critical": [self._format_alert_brief(a) for a in critical_alerts[:3]],
                "visa_legal": [self._format_alert_brief(a) for a in visa_legal_alerts[:2]],
                "safety": [self._format_alert_brief(a) for a in safety_alerts[:2]],
                "health": [self._format_alert_brief(a) for a in health_alerts[:2]]
            },
            "quick_tips": self._generate_quick_tips(country_code, alerts),
            "emergency_info": {
                "recommended_actions": self._get_emergency_recommendations(alerts),
                "contact_info": "Contact local embassy or emergency services if needed"
            }
        }

        return brief

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate approximate distance between two coordinates in kilometers."""
        import math

        # Haversine formula (simplified)
        R = 6371  # Earth's radius in kilometers

        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = (math.sin(dlat/2) * math.sin(dlat/2) +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon/2) * math.sin(dlon/2))

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c

        return distance

    def _is_near_border(self, lat: float, lon: float, bounds: Dict) -> bool:
        """Check if coordinates are near country border."""
        return (
            abs(lat - bounds["north"]) < self.BORDER_THRESHOLD or
            abs(lat - bounds["south"]) < self.BORDER_THRESHOLD or
            abs(lon - bounds["east"]) < self.BORDER_THRESHOLD or
            abs(lon - bounds["west"]) < self.BORDER_THRESHOLD
        )

    def _distance_to_border(self, lat: float, lon: float, bounds: Dict) -> float:
        """Calculate approximate distance to nearest border."""
        distances = [
            abs(lat - bounds["north"]),
            abs(lat - bounds["south"]),
            abs(lon - bounds["east"]),
            abs(lon - bounds["west"])
        ]
        return min(distances) * 111  # Convert degrees to kilometers (approximate)

    async def _get_country_name(self, country_code: str) -> Optional[str]:
        """Get country name from database."""
        country = await self.get_country_by_code(country_code)
        return country.name if country else None

    async def _reverse_geocode(self, latitude: float, longitude: float) -> CountryDetectionResult:
        """
        Fallback reverse geocoding using external service.
        In production, integrate with Google Maps, HERE, or similar service.
        """
        # Placeholder implementation - would call external service
        logger.warning(f"No country found for coordinates {latitude}, {longitude}")
        return CountryDetectionResult(
            country_code=None,
            country_name=None,
            confidence=0.0
        )

    def _generate_immediate_actions(self, alerts: List[Alert]) -> List[str]:
        """Generate immediate action items based on alerts."""
        actions = []

        critical_alerts = [a for a in alerts if a.risk_level >= 4]
        if critical_alerts:
            actions.append("🚨 URGENT: Review critical alerts immediately")

        visa_alerts = [a for a in alerts if 'visa' in a.categories]
        if visa_alerts:
            actions.append("📋 Check visa and documentation requirements")

        safety_alerts = [a for a in alerts if 'safety' in a.categories]
        if safety_alerts:
            actions.append("🛡️ Review safety and security guidelines")

        legal_alerts = [a for a in alerts if 'legal' in a.categories]
        if legal_alerts:
            actions.append("⚖️ Be aware of local legal requirements")

        health_alerts = [a for a in alerts if 'health' in a.categories]
        if health_alerts:
            actions.append("🏥 Check health and medical requirements")

        if not actions:
            actions.append("✅ No immediate actions required - safe travels!")

        return actions

    def _format_alert_brief(self, alert: Alert) -> Dict:
        """Format alert for brief display."""
        return {
            "id": alert.id,
            "title": alert.title,
            "risk_level": alert.risk_level,
            "categories": alert.categories,
            "expires_at": alert.expires_at.isoformat() if alert.expires_at else None,
            "summary": alert.description[:200] + "..." if len(alert.description) > 200 else alert.description
        }

    def _generate_quick_tips(self, country_code: str, alerts: List[Alert]) -> List[str]:
        """Generate country-specific quick tips."""
        tips = []

        # Country-specific tips
        country_tips = {
            "US": ["Keep passport accessible", "Be aware of state-specific laws"],
            "CN": ["VPN restrictions apply", "Keep documentation ready"],
            "TH": ["Respect local customs", "Avoid political discussions"],
            "GB": ["Right-hand traffic", "Mind the gap"],
            "JP": ["Bow respectfully", "Remove shoes when required"],
            "FR": ["Greeting with kisses is common", "Respect meal times"],
            "DE": ["Punctuality is important", "Separate waste properly"],
            "AU": ["Check for dangerous wildlife", "Sun protection essential"]
        }

        if country_code in country_tips:
            tips.extend(country_tips[country_code])

        # Alert-based tips
        if any('visa' in a.categories for a in alerts):
            tips.append("📄 Keep all travel documents readily available")

        if any(a.risk_level >= 4 for a in alerts):
            tips.append("⚠️ Consider registering with your embassy")

        return tips[:4]  # Limit to 4 tips for brevity

    def _get_emergency_recommendations(self, alerts: List[Alert]) -> List[str]:
        """Get emergency recommendations based on alerts."""
        recommendations = []

        critical_count = len([a for a in alerts if a.risk_level >= 4])
        if critical_count > 0:
            recommendations.extend([
                "Register with your embassy immediately",
                "Keep emergency contacts accessible",
                "Monitor local news and official channels"
            ])

        if any('safety' in a.categories for a in alerts):
            recommendations.append("Avoid known risk areas mentioned in alerts")

        if any('health' in a.categories for a in alerts):
            recommendations.append("Ensure you have appropriate health coverage")

        return recommendations