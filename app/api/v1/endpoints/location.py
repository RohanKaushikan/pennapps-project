from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
import logging

from app.core.database import get_session
from app.models.user import User
from app.models.country import Country
from app.models.alert import Alert
from app.models.user_alert import UserAlert
from app.services.location_service import LocationService
from app.schemas.location import (
    LocationRequest,
    UserLocationUpdate,
    LocationAlertResponse,
    ImmediateAlertResponse,
    EntryBriefResponse,
    LocationProcessingResponse,
    CountryDetection,
    AlertSummary
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/alerts/location", response_model=LocationAlertResponse)
async def trigger_location_alerts(
    location_request: LocationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session)
):
    """
    Trigger alerts when user enters a country.
    Accepts either lat/lng coordinates or country code.
    """
    try:
        # Validate input
        location_request.validate_input()

        location_service = LocationService(db)

        # Detect country from coordinates or use provided country code
        if location_request.latitude is not None and location_request.longitude is not None:
            detection_result = await location_service.detect_country_from_coordinates(
                location_request.latitude,
                location_request.longitude
            )
        else:
            # Use provided country code
            country = await location_service.get_country_by_code(location_request.country_code)
            if not country:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Country with code {location_request.country_code} not found"
                )

            detection_result = CountryDetection(
                country_code=country.code,
                country_name=country.name,
                confidence=1.0,
                is_border_region=False
            )

        if not detection_result.country_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not determine country from provided location"
            )

        # Get alerts for the detected country
        alerts = await location_service.get_critical_alerts_for_country(
            detection_result.country_code,
            risk_level_threshold=2  # Get medium+ risk alerts
        )

        # Format alerts for response
        formatted_alerts = []
        highest_risk = 0

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
            highest_risk = max(highest_risk, alert.risk_level)

        # Generate recommendations based on alerts and location
        recommendations = []
        if highest_risk >= 4:
            recommendations.append("🚨 CRITICAL: Immediate attention required")
            recommendations.append("📞 Contact your embassy or consulate")
        elif highest_risk >= 3:
            recommendations.append("⚠️ HIGH RISK: Exercise increased caution")
            recommendations.append("📋 Review all alerts before proceeding")
        elif detection_result.is_border_region:
            recommendations.append("🗺️ You are near a border region")
            recommendations.append("📄 Ensure you have proper documentation")

        if len(alerts) == 0:
            recommendations.append("✅ No active alerts for this location")
            recommendations.append("🛡️ Standard travel precautions recommended")

        # Schedule background processing for notifications
        if len(alerts) > 0:
            background_tasks.add_task(
                _process_location_notifications,
                detection_result.country_code,
                len(alerts),
                highest_risk
            )

        return LocationAlertResponse(
            country_detection=detection_result,
            triggered_alerts=formatted_alerts,
            alert_count=len(alerts),
            highest_risk_level=highest_risk,
            processing_timestamp=datetime.utcnow(),
            recommendations=recommendations
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error processing location alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing location request"
        )


@router.get("/alerts/country/{country_code}/immediate", response_model=ImmediateAlertResponse)
async def get_immediate_alerts(
    country_code: str,
    db: AsyncSession = Depends(get_session)
):
    """
    Get critical alerts for immediate country entry.
    Returns only high-priority alerts (risk level 4+).
    """
    try:
        location_service = LocationService(db)

        # Get country information
        country = await location_service.get_country_by_code(country_code.upper())
        if not country:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Country with code {country_code} not found"
            )

        # Get immediate/critical alerts
        critical_alerts = await location_service.get_immediate_alerts_for_country(country_code.upper())

        # Format alerts
        formatted_alerts = []
        for alert in critical_alerts:
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

        # Determine risk assessment
        alert_count = len(critical_alerts)
        if alert_count >= 3:
            risk_assessment = "CRITICAL"
        elif alert_count >= 2:
            risk_assessment = "HIGH"
        elif alert_count >= 1:
            risk_assessment = "MEDIUM"
        else:
            risk_assessment = "LOW"

        # Generate immediate actions
        immediate_actions = []
        if critical_alerts:
            immediate_actions.extend([
                "🚨 Review all critical alerts immediately",
                "📞 Consider contacting your embassy",
                "📋 Verify all travel documentation",
                "🗺️ Plan alternative routes if necessary"
            ])

            # Add category-specific actions
            categories = set()
            for alert in critical_alerts:
                categories.update(alert.categories)

            if 'safety' in categories:
                immediate_actions.append("🛡️ Avoid high-risk areas mentioned in alerts")
            if 'legal' in categories:
                immediate_actions.append("⚖️ Ensure compliance with local laws")
            if 'health' in categories:
                immediate_actions.append("🏥 Check health requirements and medical facilities")
        else:
            immediate_actions.append("✅ No critical alerts - proceed with standard precautions")

        return ImmediateAlertResponse(
            country_code=country.code,
            country_name=country.name,
            critical_alerts=formatted_alerts,
            alert_count=alert_count,
            risk_assessment=risk_assessment,
            immediate_actions=immediate_actions,
            generated_at=datetime.utcnow()
        )

    except Exception as e:
        logger.error(f"Error fetching immediate alerts for {country_code}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching immediate alerts"
        )


@router.post("/users/location", response_model=LocationProcessingResponse)
async def update_user_location(
    location_update: UserLocationUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session)
):
    """
    Update user's current location and trigger location-based processing.
    """
    try:
        # Verify user exists
        result = await db.execute(
            select(User).where(User.id == location_update.user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        location_service = LocationService(db)

        # Detect country from coordinates
        detection_result = await location_service.detect_country_from_coordinates(
            location_update.latitude,
            location_update.longitude
        )

        # Update user's travel preferences with current location
        current_location = {
            "latitude": location_update.latitude,
            "longitude": location_update.longitude,
            "accuracy": location_update.accuracy,
            "timestamp": (location_update.timestamp or datetime.utcnow()).isoformat(),
            "detected_country": detection_result.country_code if detection_result.country_code else None
        }

        # Update user preferences
        if user.travel_preferences is None:
            user.travel_preferences = {}

        user.travel_preferences["current_location"] = current_location

        # Track location history (keep last 5 locations)
        if "location_history" not in user.travel_preferences:
            user.travel_preferences["location_history"] = []

        user.travel_preferences["location_history"].insert(0, current_location)
        user.travel_preferences["location_history"] = user.travel_preferences["location_history"][:5]

        await db.commit()
        await db.refresh(user)

        # Process alerts for detected country
        alerts_triggered = 0
        notifications_sent = 0

        if detection_result.country_code:
            # Get relevant alerts for the country
            alerts = await location_service.get_critical_alerts_for_country(
                detection_result.country_code,
                risk_level_threshold=3  # High priority alerts
            )

            alerts_triggered = len(alerts)

            # Create user-alert relationships for new alerts
            for alert in alerts:
                # Check if user already has this alert
                existing_alert = await db.execute(
                    select(UserAlert).where(
                        UserAlert.user_id == user.id,
                        UserAlert.alert_id == alert.id
                    )
                )

                if not existing_alert.scalar_one_or_none():
                    user_alert = UserAlert(
                        user_id=user.id,
                        alert_id=alert.id,
                        is_read=False,
                        notified_at=datetime.utcnow()
                    )
                    db.add(user_alert)
                    notifications_sent += 1

            await db.commit()

        # Schedule background processing
        background_tasks.add_task(
            _process_user_location_analytics,
            location_update.user_id,
            detection_result.country_code,
            alerts_triggered
        )

        # Calculate next check recommendation (based on movement and risk)
        next_check = datetime.utcnow() + timedelta(minutes=15)  # Default 15 minutes
        if detection_result.is_border_region:
            next_check = datetime.utcnow() + timedelta(minutes=5)  # More frequent near borders
        elif alerts_triggered > 0:
            next_check = datetime.utcnow() + timedelta(minutes=10)  # More frequent with active alerts

        return LocationProcessingResponse(
            user_id=user.id,
            location_updated=True,
            country_detected=detection_result if detection_result.country_code else None,
            alerts_triggered=alerts_triggered,
            notifications_sent=notifications_sent,
            processing_timestamp=datetime.utcnow(),
            next_check_recommended=next_check
        )

    except Exception as e:
        logger.error(f"Error updating user location: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing location update"
        )


@router.get("/alerts/entry-brief/{country_code}", response_model=EntryBriefResponse)
async def get_entry_brief(
    country_code: str,
    db: AsyncSession = Depends(get_session)
):
    """
    Generate a 60-second legal brief for country arrival.
    Provides essential information for immediate country entry.
    """
    try:
        location_service = LocationService(db)

        # Generate comprehensive entry brief
        brief = await location_service.generate_entry_brief(country_code.upper())

        if "error" in brief:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=brief["error"]
            )

        return EntryBriefResponse(**brief)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating entry brief for {country_code}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating entry brief"
        )


# Background task functions
async def _process_location_notifications(
    country_code: str,
    alert_count: int,
    highest_risk: int
):
    """Background task to process location-based notifications."""
    logger.info(
        f"Processing location notifications for {country_code}: "
        f"{alert_count} alerts, highest risk: {highest_risk}"
    )
    # In production, this would:
    # - Send push notifications
    # - Log analytics events
    # - Update user engagement metrics
    # - Trigger email notifications for high-risk alerts


async def _process_user_location_analytics(
    user_id: int,
    country_code: Optional[str],
    alerts_triggered: int
):
    """Background task to process user location analytics."""
    logger.info(
        f"Processing location analytics for user {user_id}: "
        f"country: {country_code}, alerts: {alerts_triggered}"
    )
    # In production, this would:
    # - Update user travel patterns
    # - Calculate location accuracy scores
    # - Generate personalized recommendations
    # - Update ML models for better country detection