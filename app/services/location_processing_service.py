import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import math
import structlog
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.location_event import (
    LocationEvent, LocationAlert, GeofenceZone, CountryBrief, EmergencyBroadcast,
    LocationEventType, AlertSeverity, AlertType
)
from app.api_clients.unified_api_service import UnifiedAPIService
from app.services.alert_notification_service import AlertNotificationService

logger = structlog.get_logger(__name__)


class LocationProcessingService:
    """
    Service for processing location events and generating real-time alerts.

    Handles country entries, geofence triggers, and emergency alert generation
    with immediate processing and notification capabilities.
    """

    def __init__(self, api_service: Optional[UnifiedAPIService] = None):
        self.api_service = api_service
        self.notification_service = AlertNotificationService()
        self.country_cache = {}  # Simple in-memory cache for country lookups

    async def process_country_entry(
        self,
        user_id: str,
        latitude: float,
        longitude: float,
        country_code: str,
        country_name: str,
        device_id: Optional[str] = None,
        previous_country_code: Optional[str] = None,
        accuracy_meters: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process user country entry and generate immediate alerts.

        Args:
            user_id: User identifier
            latitude: Current latitude
            longitude: Current longitude
            country_code: ISO 3166-1 alpha-3 country code
            country_name: Full country name
            device_id: Device identifier (optional)
            previous_country_code: Previous country if transitioning
            accuracy_meters: GPS accuracy in meters
            metadata: Additional event metadata

        Returns:
            Processing result with alerts and recommendations
        """
        start_time = time.time()

        try:
            async with get_session() as session:
                # Create location event
                location_event = LocationEvent(
                    user_id=user_id,
                    device_id=device_id,
                    event_type=LocationEventType.COUNTRY_ENTRY,
                    latitude=latitude,
                    longitude=longitude,
                    accuracy_meters=accuracy_meters,
                    country_code=country_code,
                    country_name=country_name,
                    previous_country_code=previous_country_code,
                    timestamp=datetime.utcnow(),
                    metadata=metadata or {}
                )

                session.add(location_event)
                await session.flush()  # Get the ID

                # Process the entry and generate alerts
                alerts = await self._generate_country_entry_alerts(
                    session, location_event, user_id, country_code
                )

                # Check for geofence triggers
                geofence_alerts = await self._check_geofence_triggers(
                    session, user_id, latitude, longitude, country_code
                )
                alerts.extend(geofence_alerts)

                # Check for emergency broadcasts
                emergency_alerts = await self._check_emergency_broadcasts(
                    session, user_id, country_code, latitude, longitude
                )
                alerts.extend(emergency_alerts)

                # Update processing metrics
                processing_time = (time.time() - start_time) * 1000
                location_event.processed_at = datetime.utcnow()
                location_event.processing_time_ms = processing_time

                await session.commit()

                # Send immediate notifications
                await self._send_immediate_notifications(alerts)

                logger.info(
                    "Country entry processed",
                    user_id=user_id,
                    country=country_name,
                    country_code=country_code,
                    alerts_generated=len(alerts),
                    processing_time_ms=processing_time
                )

                return {
                    "success": True,
                    "event_id": str(location_event.id),
                    "country": {
                        "code": country_code,
                        "name": country_name
                    },
                    "alerts": [self._format_alert_response(alert) for alert in alerts],
                    "processing_time_ms": processing_time,
                    "recommendations": await self._get_entry_recommendations(country_code)
                }

        except Exception as e:
            logger.error("Error processing country entry", error=str(e), user_id=user_id)
            return {
                "success": False,
                "error": str(e),
                "processing_time_ms": (time.time() - start_time) * 1000
            }

    async def process_geofence_trigger(
        self,
        user_id: str,
        latitude: float,
        longitude: float,
        geofence_id: str,
        event_type: str,  # "enter" or "exit"
        device_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle geofencing events from mobile app.

        Args:
            user_id: User identifier
            latitude: Current latitude
            longitude: Current longitude
            geofence_id: Geofence zone identifier
            event_type: "enter" or "exit"
            device_id: Device identifier
            metadata: Additional event metadata

        Returns:
            Processing result with triggered alerts
        """
        start_time = time.time()

        try:
            async with get_session() as session:
                # Get geofence zone details
                geofence_query = select(GeofenceZone).where(GeofenceZone.id == geofence_id)
                geofence_result = await session.execute(geofence_query)
                geofence = geofence_result.scalar_one_or_none()

                if not geofence:
                    return {
                        "success": False,
                        "error": f"Geofence zone {geofence_id} not found"
                    }

                # Create location event
                location_event_type = (
                    LocationEventType.GEOFENCE_ENTER if event_type == "enter"
                    else LocationEventType.GEOFENCE_EXIT
                )

                location_event = LocationEvent(
                    user_id=user_id,
                    device_id=device_id,
                    event_type=location_event_type,
                    latitude=latitude,
                    longitude=longitude,
                    country_code=geofence.country_code,
                    timestamp=datetime.utcnow(),
                    metadata={
                        "geofence_id": geofence_id,
                        "geofence_name": geofence.name,
                        "geofence_type": geofence.zone_type,
                        **(metadata or {})
                    }
                )

                session.add(location_event)
                await session.flush()

                # Generate geofence-specific alerts
                alerts = []

                if ((event_type == "enter" and geofence.entry_alert_enabled) or
                    (event_type == "exit" and geofence.exit_alert_enabled)):

                    alert = await self._create_geofence_alert(
                        session, location_event, geofence, event_type
                    )
                    if alert:
                        alerts.append(alert)

                # Update processing metrics
                processing_time = (time.time() - start_time) * 1000
                location_event.processed_at = datetime.utcnow()
                location_event.processing_time_ms = processing_time

                await session.commit()

                # Send notifications
                await self._send_immediate_notifications(alerts)

                logger.info(
                    "Geofence trigger processed",
                    user_id=user_id,
                    geofence_name=geofence.name,
                    event_type=event_type,
                    alerts_generated=len(alerts)
                )

                return {
                    "success": True,
                    "event_id": str(location_event.id),
                    "geofence": {
                        "id": geofence_id,
                        "name": geofence.name,
                        "type": geofence.zone_type
                    },
                    "event_type": event_type,
                    "alerts": [self._format_alert_response(alert) for alert in alerts],
                    "processing_time_ms": processing_time
                }

        except Exception as e:
            logger.error("Error processing geofence trigger", error=str(e), user_id=user_id)
            return {
                "success": False,
                "error": str(e),
                "processing_time_ms": (time.time() - start_time) * 1000
            }

    async def generate_country_brief(
        self,
        country_code: str,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Generate comprehensive country entry brief.

        Args:
            country_code: ISO 3166-1 alpha-3 country code
            force_refresh: Force regeneration even if cached brief exists

        Returns:
            Comprehensive country brief with travel advisories and recommendations
        """
        start_time = time.time()

        try:
            async with get_session() as session:
                # Check for existing current brief
                if not force_refresh:
                    brief_query = select(CountryBrief).where(
                        and_(
                            CountryBrief.country_code == country_code,
                            CountryBrief.is_current == True,
                            or_(
                                CountryBrief.expires_at.is_(None),
                                CountryBrief.expires_at > datetime.utcnow()
                            )
                        )
                    )
                    brief_result = await session.execute(brief_query)
                    existing_brief = brief_result.scalar_one_or_none()

                    if existing_brief:
                        logger.info("Using cached country brief", country_code=country_code)
                        return {
                            "success": True,
                            "cached": True,
                            "country_code": country_code,
                            "brief": existing_brief.brief_data,
                            "summary": existing_brief.summary,
                            "generated_at": existing_brief.generated_at.isoformat(),
                            "processing_time_ms": (time.time() - start_time) * 1000
                        }

                # Generate new brief
                if not self.api_service:
                    self.api_service = UnifiedAPIService()
                    await self.api_service.initialize_clients()

                # Get travel advisories
                advisory_response = await self.api_service.get_country_advisory(country_code)

                # Generate comprehensive brief
                brief_data = await self._compile_country_brief(
                    country_code, advisory_response
                )

                # Create brief record
                country_brief = CountryBrief(
                    country_code=country_code,
                    country_name=brief_data["country_name"],
                    brief_data=brief_data,
                    summary=brief_data["summary"],
                    generated_at=datetime.utcnow(),
                    data_sources=brief_data.get("sources", []),
                    expires_at=datetime.utcnow() + timedelta(hours=6)  # 6-hour cache
                )

                # Mark previous briefs as non-current
                await session.execute(
                    select(CountryBrief)
                    .where(CountryBrief.country_code == country_code)
                    .update({"is_current": False})
                )

                session.add(country_brief)
                await session.commit()

                processing_time = (time.time() - start_time) * 1000

                logger.info(
                    "Country brief generated",
                    country_code=country_code,
                    processing_time_ms=processing_time
                )

                return {
                    "success": True,
                    "cached": False,
                    "country_code": country_code,
                    "brief": brief_data,
                    "summary": brief_data["summary"],
                    "generated_at": country_brief.generated_at.isoformat(),
                    "processing_time_ms": processing_time
                }

        except Exception as e:
            logger.error("Error generating country brief", error=str(e), country_code=country_code)
            return {
                "success": False,
                "error": str(e),
                "processing_time_ms": (time.time() - start_time) * 1000
            }

    async def broadcast_emergency_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        target_countries: List[str],
        alert_type: AlertType = AlertType.EMERGENCY_ALERT,
        target_regions: Optional[List[str]] = None,
        radius_km: Optional[float] = None,
        expires_hours: int = 24,
        issued_by: str = "System"
    ) -> Dict[str, Any]:
        """
        Push critical alerts to users in specific locations.

        Args:
            title: Alert title
            message: Alert message
            severity: Alert severity level
            target_countries: List of country codes to target
            alert_type: Type of alert
            target_regions: Optional specific regions
            radius_km: Optional radius for location-based targeting
            expires_hours: Hours until alert expires
            issued_by: Authority issuing the alert

        Returns:
            Broadcast result with delivery statistics
        """
        start_time = time.time()

        try:
            async with get_session() as session:
                # Create emergency broadcast record
                broadcast = EmergencyBroadcast(
                    title=title,
                    message=message,
                    severity=severity,
                    alert_type=alert_type,
                    target_countries=target_countries,
                    target_regions=target_regions,
                    radius_km=radius_km,
                    issued_by=issued_by,
                    expires_at=datetime.utcnow() + timedelta(hours=expires_hours)
                )

                session.add(broadcast)
                await session.flush()

                # Find target users based on recent location events
                target_users = await self._find_target_users(
                    session, target_countries, target_regions, radius_km
                )

                # Create individual alerts for each user
                alerts_created = []
                for user_location in target_users:
                    alert = LocationAlert(
                        user_id=user_location["user_id"],
                        alert_type=alert_type,
                        severity=severity,
                        title=title,
                        message=message,
                        country_code=user_location["country_code"],
                        country_name=user_location["country_name"],
                        source="emergency_broadcast",
                        location_data={
                            "broadcast_id": str(broadcast.id),
                            "latitude": user_location.get("latitude"),
                            "longitude": user_location.get("longitude")
                        },
                        expires_at=broadcast.expires_at
                    )
                    session.add(alert)
                    alerts_created.append(alert)

                # Update broadcast statistics
                broadcast.total_recipients = len(alerts_created)

                await session.commit()

                # Send immediate notifications
                await self._send_emergency_notifications(alerts_created)

                processing_time = (time.time() - start_time) * 1000

                logger.info(
                    "Emergency alert broadcast",
                    broadcast_id=str(broadcast.id),
                    target_countries=target_countries,
                    recipients=len(alerts_created),
                    processing_time_ms=processing_time
                )

                return {
                    "success": True,
                    "broadcast_id": str(broadcast.id),
                    "recipients": len(alerts_created),
                    "target_countries": target_countries,
                    "processing_time_ms": processing_time,
                    "expires_at": broadcast.expires_at.isoformat()
                }

        except Exception as e:
            logger.error("Error broadcasting emergency alert", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "processing_time_ms": (time.time() - start_time) * 1000
            }

    async def _generate_country_entry_alerts(
        self,
        session: AsyncSession,
        location_event: LocationEvent,
        user_id: str,
        country_code: str
    ) -> List[LocationAlert]:
        """Generate alerts specific to country entry."""
        alerts = []

        try:
            # Get travel advisory data
            if not self.api_service:
                self.api_service = UnifiedAPIService()
                await self.api_service.initialize_clients()

            advisory_response = await self.api_service.get_country_advisory(country_code)

            if advisory_response.success and advisory_response.data:
                for advisory in advisory_response.data:
                    severity = self._map_risk_to_severity(
                        advisory.get("risk_level_standardized")
                    )

                    alert = LocationAlert(
                        location_event_id=location_event.id,
                        user_id=user_id,
                        alert_type=AlertType.TRAVEL_ADVISORY,
                        severity=severity,
                        title=f"Travel Advisory: {advisory.get('country', country_code)}",
                        message=self._format_advisory_message(advisory),
                        country_code=country_code,
                        country_name=advisory.get("country", location_event.country_name),
                        source=advisory.get("source", "unknown"),
                        risk_level=advisory.get("risk_level"),
                        advisory_data=advisory
                    )

                    session.add(alert)
                    alerts.append(alert)

        except Exception as e:
            logger.warning("Error generating country entry alerts", error=str(e))

        return alerts

    async def _check_geofence_triggers(
        self,
        session: AsyncSession,
        user_id: str,
        latitude: float,
        longitude: float,
        country_code: str
    ) -> List[LocationAlert]:
        """Check for geofence triggers at the current location."""
        alerts = []

        try:
            # Get active geofences in the country
            geofence_query = select(GeofenceZone).where(
                and_(
                    GeofenceZone.country_code == country_code,
                    GeofenceZone.is_active == True
                )
            )
            geofence_result = await session.execute(geofence_query)
            geofences = geofence_result.scalars().all()

            for geofence in geofences:
                distance = self._calculate_distance(
                    latitude, longitude,
                    geofence.center_latitude, geofence.center_longitude
                )

                if distance <= geofence.radius_meters:
                    # User is within geofence
                    if geofence.entry_alert_enabled and geofence.alert_template:
                        alert_data = geofence.alert_template

                        alert = LocationAlert(
                            user_id=user_id,
                            alert_type=AlertType.SAFETY_WARNING,
                            severity=AlertSeverity.MEDIUM,
                            title=alert_data.get("title", f"Entering {geofence.name}"),
                            message=alert_data.get("message", f"You are now in {geofence.name}"),
                            country_code=country_code,
                            source="geofence_system",
                            location_data={
                                "geofence_id": str(geofence.id),
                                "geofence_name": geofence.name,
                                "distance_meters": distance
                            }
                        )

                        session.add(alert)
                        alerts.append(alert)

        except Exception as e:
            logger.warning("Error checking geofence triggers", error=str(e))

        return alerts

    async def _check_emergency_broadcasts(
        self,
        session: AsyncSession,
        user_id: str,
        country_code: str,
        latitude: float,
        longitude: float
    ) -> List[LocationAlert]:
        """Check for active emergency broadcasts for the user's location."""
        alerts = []

        try:
            # Get active emergency broadcasts
            broadcast_query = select(EmergencyBroadcast).where(
                and_(
                    EmergencyBroadcast.is_active == True,
                    or_(
                        EmergencyBroadcast.expires_at.is_(None),
                        EmergencyBroadcast.expires_at > datetime.utcnow()
                    )
                )
            )
            broadcast_result = await session.execute(broadcast_query)
            broadcasts = broadcast_result.scalars().all()

            for broadcast in broadcasts:
                # Check if user's location matches broadcast criteria
                if country_code in broadcast.target_countries:
                    # Check if user already received this broadcast
                    existing_query = select(LocationAlert).where(
                        and_(
                            LocationAlert.user_id == user_id,
                            LocationAlert.location_data.op('->>')('broadcast_id') == str(broadcast.id)
                        )
                    )
                    existing_result = await session.execute(existing_query)
                    existing_alert = existing_result.scalar_one_or_none()

                    if not existing_alert:
                        alert = LocationAlert(
                            user_id=user_id,
                            alert_type=broadcast.alert_type,
                            severity=broadcast.severity,
                            title=broadcast.title,
                            message=broadcast.message,
                            country_code=country_code,
                            source="emergency_broadcast",
                            location_data={
                                "broadcast_id": str(broadcast.id),
                                "latitude": latitude,
                                "longitude": longitude
                            },
                            expires_at=broadcast.expires_at
                        )

                        session.add(alert)
                        alerts.append(alert)

        except Exception as e:
            logger.warning("Error checking emergency broadcasts", error=str(e))

        return alerts

    async def _create_geofence_alert(
        self,
        session: AsyncSession,
        location_event: LocationEvent,
        geofence: GeofenceZone,
        event_type: str
    ) -> Optional[LocationAlert]:
        """Create a geofence-specific alert."""
        try:
            if not geofence.alert_template:
                return None

            alert_data = geofence.alert_template
            action = "Entering" if event_type == "enter" else "Exiting"

            alert = LocationAlert(
                location_event_id=location_event.id,
                user_id=location_event.user_id,
                alert_type=AlertType.SAFETY_WARNING,
                severity=AlertSeverity.MEDIUM,
                title=alert_data.get("title", f"{action} {geofence.name}"),
                message=alert_data.get("message", f"You are {action.lower()} {geofence.name}"),
                country_code=geofence.country_code,
                source="geofence_system",
                location_data={
                    "geofence_id": str(geofence.id),
                    "geofence_name": geofence.name,
                    "geofence_type": geofence.zone_type,
                    "event_type": event_type
                }
            )

            session.add(alert)
            return alert

        except Exception as e:
            logger.warning("Error creating geofence alert", error=str(e))
            return None

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in meters using Haversine formula."""
        R = 6371000  # Earth radius in meters

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def _map_risk_to_severity(self, risk_level: Optional[str]) -> AlertSeverity:
        """Map standardized risk level to alert severity."""
        if not risk_level:
            return AlertSeverity.LOW

        risk_lower = risk_level.lower()
        if "avoid_all_travel" in risk_lower:
            return AlertSeverity.CRITICAL
        elif "reconsider_travel" in risk_lower:
            return AlertSeverity.HIGH
        elif "exercise_caution" in risk_lower:
            return AlertSeverity.MEDIUM
        else:
            return AlertSeverity.LOW

    def _format_advisory_message(self, advisory: Dict[str, Any]) -> str:
        """Format travel advisory into alert message."""
        content = advisory.get("content", "")
        risk_level = advisory.get("risk_level", "")

        if len(content) > 200:
            content = content[:200] + "..."

        message = f"Travel Advisory: {risk_level}\n\n{content}"
        return message

    def _format_alert_response(self, alert: LocationAlert) -> Dict[str, Any]:
        """Format alert for API response."""
        return {
            "id": str(alert.id),
            "type": alert.alert_type.value,
            "severity": alert.severity.value,
            "title": alert.title,
            "message": alert.message,
            "country_code": alert.country_code,
            "source": alert.source,
            "created_at": alert.created_at.isoformat() if alert.created_at else None
        }

    async def _send_immediate_notifications(self, alerts: List[LocationAlert]):
        """Send immediate notifications for alerts."""
        try:
            notification_tasks = []
            for alert in alerts:
                task = self.notification_service.send_alert_notification(alert)
                notification_tasks.append(task)

            if notification_tasks:
                await asyncio.gather(*notification_tasks, return_exceptions=True)

        except Exception as e:
            logger.warning("Error sending immediate notifications", error=str(e))

    async def _send_emergency_notifications(self, alerts: List[LocationAlert]):
        """Send emergency notifications with high priority."""
        try:
            for alert in alerts:
                await self.notification_service.send_emergency_notification(alert)
        except Exception as e:
            logger.warning("Error sending emergency notifications", error=str(e))

    async def _get_entry_recommendations(self, country_code: str) -> List[Dict[str, Any]]:
        """Get entry recommendations for a country."""
        # This would be expanded with more sophisticated recommendation logic
        recommendations = [
            {
                "type": "check_requirements",
                "title": "Check Entry Requirements",
                "description": "Verify visa and passport requirements"
            },
            {
                "type": "register_embassy",
                "title": "Register with Embassy",
                "description": "Consider registering with your local embassy"
            },
            {
                "type": "travel_insurance",
                "title": "Verify Travel Insurance",
                "description": "Ensure your travel insurance is valid"
            }
        ]
        return recommendations

    async def _compile_country_brief(
        self, country_code: str, advisory_response
    ) -> Dict[str, Any]:
        """Compile comprehensive country brief from multiple sources."""
        brief = {
            "country_code": country_code,
            "country_name": "Unknown",
            "summary": "",
            "travel_advisories": [],
            "entry_requirements": {},
            "emergency_contacts": {},
            "health_info": {},
            "sources": []
        }

        if advisory_response.success and advisory_response.data:
            for advisory in advisory_response.data:
                brief["country_name"] = advisory.get("country", brief["country_name"])
                brief["travel_advisories"].append({
                    "source": advisory.get("source"),
                    "risk_level": advisory.get("risk_level"),
                    "risk_level_standardized": advisory.get("risk_level_standardized"),
                    "content": advisory.get("content"),
                    "last_updated": advisory.get("last_updated")
                })

                if advisory.get("source") not in brief["sources"]:
                    brief["sources"].append(advisory.get("source"))

        # Generate summary
        if brief["travel_advisories"]:
            highest_risk = max(
                brief["travel_advisories"],
                key=lambda x: self._risk_level_priority(x.get("risk_level_standardized"))
            )
            brief["summary"] = f"Current travel advisory level: {highest_risk.get('risk_level', 'Unknown')}"
        else:
            brief["summary"] = "No current travel advisories available"

        return brief

    def _risk_level_priority(self, risk_level: Optional[str]) -> int:
        """Get numeric priority for risk level sorting."""
        if not risk_level:
            return 0

        priorities = {
            "AVOID_ALL_TRAVEL": 4,
            "RECONSIDER_TRAVEL": 3,
            "EXERCISE_CAUTION": 2,
            "NORMAL_PRECAUTIONS": 1
        }
        return priorities.get(risk_level, 0)

    async def _find_target_users(
        self,
        session: AsyncSession,
        target_countries: List[str],
        target_regions: Optional[List[str]] = None,
        radius_km: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Find users matching emergency broadcast criteria."""
        try:
            # Get recent location events for users in target countries
            cutoff_time = datetime.utcnow() - timedelta(hours=1)  # Users active in last hour

            location_query = select(LocationEvent).where(
                and_(
                    LocationEvent.country_code.in_(target_countries),
                    LocationEvent.timestamp >= cutoff_time
                )
            ).order_by(
                LocationEvent.user_id,
                LocationEvent.timestamp.desc()
            )

            location_result = await session.execute(location_query)
            location_events = location_result.scalars().all()

            # Get most recent location per user
            user_locations = {}
            for event in location_events:
                if event.user_id not in user_locations:
                    user_locations[event.user_id] = {
                        "user_id": event.user_id,
                        "country_code": event.country_code,
                        "country_name": event.country_name,
                        "latitude": event.latitude,
                        "longitude": event.longitude,
                        "timestamp": event.timestamp
                    }

            return list(user_locations.values())

        except Exception as e:
            logger.warning("Error finding target users", error=str(e))
            return []