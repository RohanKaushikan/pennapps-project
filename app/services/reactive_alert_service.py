"""
Reactive Alert Service - Triggers alerts only when users enter new countries.
No advance setup required - completely reactive to location changes.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.models.user import User
from app.models.country import Country
from app.models.alert import Alert
from app.models.user_country_entry import UserCountryEntry
from app.services.location_service import LocationService
from app.core.logging import get_logger

logger = get_logger(__name__)


class ReactiveAlertService:
    """Service for reactive country entry detection and alerting."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.location_service = LocationService(db)

    async def process_user_location_update(
        self, 
        user_id: int, 
        latitude: float, 
        longitude: float,
        accuracy: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Process user location update and trigger alerts if they enter a new country.
        This is the main entry point for reactive alerting.
        """
        try:
            # Get user
            user_result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            if not user:
                return {"error": "User not found"}

            # Detect country from coordinates
            detection_result = await self.location_service.detect_country_from_coordinates(
                latitude, longitude
            )

            if not detection_result.country_code:
                return {
                    "success": False,
                    "message": "Could not determine country from coordinates",
                    "country_detected": None
                }

            # Check if this is a new country entry
            is_new_country = await self._is_new_country_entry(
                user_id, detection_result.country_code
            )

            result = {
                "success": True,
                "user_id": user_id,
                "country_detected": {
                    "code": detection_result.country_code,
                    "name": detection_result.country_name,
                    "confidence": detection_result.confidence,
                    "is_border_region": detection_result.is_border_region
                },
                "is_new_country": is_new_country,
                "alerts_triggered": [],
                "notifications_sent": 0
            }

            if is_new_country:
                # Record the country entry
                entry = await self._record_country_entry(
                    user_id, detection_result.country_code, 
                    latitude, longitude, accuracy
                )

                # Get and send alerts for this country
                alerts_result = await self._get_and_send_country_alerts(
                    user_id, detection_result.country_code
                )

                result.update({
                    "entry_recorded": True,
                    "entry_id": entry.id,
                    "alerts_triggered": alerts_result["alerts"],
                    "notifications_sent": alerts_result["count"],
                    "message": f"Welcome to {detection_result.country_name}! Alerts sent."
                })
            else:
                result.update({
                    "entry_recorded": False,
                    "message": f"Already in {detection_result.country_name}"
                })

            return result

        except Exception as e:
            logger.error(f"Error processing user location update: {e}")
            return {"error": str(e)}

    async def _is_new_country_entry(self, user_id: int, country_code: str) -> bool:
        """Check if this is a new country entry for the user."""
        # Look for recent entries to this country (within last 24 hours)
        recent_threshold = datetime.utcnow() - timedelta(hours=24)
        
        recent_entry = await self.db.execute(
            select(UserCountryEntry).where(
                and_(
                    UserCountryEntry.user_id == user_id,
                    UserCountryEntry.country_code == country_code.upper(),
                    UserCountryEntry.entry_timestamp >= recent_threshold
                )
            )
        )

        return recent_entry.scalar_one_or_none() is None

    async def _record_country_entry(
        self, 
        user_id: int, 
        country_code: str, 
        latitude: float, 
        longitude: float,
        accuracy: Optional[float]
    ) -> UserCountryEntry:
        """Record a new country entry for the user."""
        entry = UserCountryEntry(
            user_id=user_id,
            country_code=country_code.upper(),
            entry_latitude=latitude,
            entry_longitude=longitude,
            entry_accuracy=accuracy,
            entry_timestamp=datetime.utcnow(),
            alerts_sent=False
        )

        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)

        logger.info(f"Recorded country entry: User {user_id} entered {country_code}")
        return entry

    async def _get_and_send_country_alerts(
        self, 
        user_id: int, 
        country_code: str
    ) -> Dict[str, Any]:
        """Get all relevant alerts for the country and send notifications."""
        try:
            # Get all active alerts for this country
            alerts_result = await self.db.execute(
                select(Alert).where(
                    and_(
                        Alert.country_id == Country.id,
                        Country.code == country_code.upper(),
                        Alert.expires_at > datetime.utcnow()
                    )
                )
            )
            alerts = alerts_result.scalars().all()

            # Format alerts for response
            formatted_alerts = []
            for alert in alerts:
                alert_dict = {
                    "id": alert.id,
                    "title": alert.title,
                    "description": alert.description,
                    "risk_level": alert.risk_level,
                    "categories": alert.categories,
                    "expires_at": alert.expires_at.isoformat() if alert.expires_at else None,
                    "created_at": alert.created_at.isoformat()
                }
                formatted_alerts.append(alert_dict)

            # Mark alerts as sent in the country entry
            await self._mark_alerts_sent(user_id, country_code)

            # TODO: In production, this would send actual push notifications, SMS, etc.
            logger.info(f"Would send {len(alerts)} alerts to user {user_id} for {country_code}")

            return {
                "alerts": formatted_alerts,
                "count": len(alerts)
            }

        except Exception as e:
            logger.error(f"Error getting country alerts: {e}")
            return {"alerts": [], "count": 0}

    async def _mark_alerts_sent(self, user_id: int, country_code: str):
        """Mark that alerts have been sent for this country entry."""
        await self.db.execute(
            select(UserCountryEntry).where(
                and_(
                    UserCountryEntry.user_id == user_id,
                    UserCountryEntry.country_code == country_code.upper(),
                    UserCountryEntry.alerts_sent == False
                )
            )
        )

        # Update the most recent entry
        entry_result = await self.db.execute(
            select(UserCountryEntry).where(
                and_(
                    UserCountryEntry.user_id == user_id,
                    UserCountryEntry.country_code == country_code.upper(),
                    UserCountryEntry.alerts_sent == False
                )
            ).order_by(UserCountryEntry.entry_timestamp.desc()).limit(1)
        )
        
        entry = entry_result.scalar_one_or_none()
        if entry:
            entry.alerts_sent = True
            entry.alerts_sent_at = datetime.utcnow()
            await self.db.commit()

    async def get_user_travel_history(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user's travel history with country entries."""
        entries_result = await self.db.execute(
            select(UserCountryEntry).where(
                UserCountryEntry.user_id == user_id
            ).order_by(UserCountryEntry.entry_timestamp.desc())
        )
        
        entries = entries_result.scalars().all()
        
        formatted_entries = []
        for entry in entries:
            entry_dict = {
                "id": entry.id,
                "country_code": entry.country_code,
                "entry_timestamp": entry.entry_timestamp.isoformat(),
                "exit_timestamp": entry.exit_timestamp.isoformat() if entry.exit_timestamp else None,
                "location": {
                    "latitude": entry.entry_latitude,
                    "longitude": entry.entry_longitude,
                    "accuracy": entry.entry_accuracy
                },
                "alerts_sent": entry.alerts_sent,
                "alerts_sent_at": entry.alerts_sent_at.isoformat() if entry.alerts_sent_at else None
            }
            formatted_entries.append(entry_dict)

        return formatted_entries

    async def get_country_entry_summary(self, country_code: str) -> Dict[str, Any]:
        """Get summary of recent entries to a country."""
        # Count entries in last 7 days
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        count_result = await self.db.execute(
            select(func.count(UserCountryEntry.id)).where(
                and_(
                    UserCountryEntry.country_code == country_code.upper(),
                    UserCountryEntry.entry_timestamp >= week_ago
                )
            )
        )
        
        recent_entries = count_result.scalar() or 0
        
        # Get unique users who entered
        users_result = await self.db.execute(
            select(func.count(func.distinct(UserCountryEntry.user_id))).where(
                and_(
                    UserCountryEntry.country_code == country_code.upper(),
                    UserCountryEntry.entry_timestamp >= week_ago
                )
            )
        )
        
        unique_users = users_result.scalar() or 0

        return {
            "country_code": country_code,
            "recent_entries_7_days": recent_entries,
            "unique_users_7_days": unique_users,
            "last_updated": datetime.utcnow().isoformat()
        }
