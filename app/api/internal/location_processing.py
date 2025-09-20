from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
import structlog

from app.schemas.location_schemas import (
    CountryEntryRequest, CountryEntryResponse,
    GeofenceTriggerRequest, GeofenceTriggerResponse,
    CountryBriefResponse, EmergencyAlertRequest, EmergencyAlertResponse,
    HealthCheckResponse, LocationProcessingStats
)
from app.services.location_processing_service import LocationProcessingService
from app.api_clients.unified_api_service import UnifiedAPIService
from app.core.database import get_session
from app.models.location_event import LocationEvent, LocationAlert
from sqlalchemy import select, func, and_

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/internal", tags=["Location Processing"])

# Dependency for location processing service
async def get_location_service():
    """Get location processing service instance."""
    api_service = UnifiedAPIService()
    await api_service.initialize_clients()
    return LocationProcessingService(api_service=api_service)


@router.post(
    "/process-entry",
    response_model=CountryEntryResponse,
    summary="Process country entry event",
    description="""
    Process user country entry and generate immediate alerts.

    This endpoint handles real-time country entry events, automatically:
    - Records the location event
    - Fetches current travel advisories
    - Generates appropriate alerts based on risk levels
    - Checks for geofence triggers
    - Sends immediate notifications
    - Returns entry recommendations

    Designed for mobile apps to call when detecting country border crossings.
    """
)
async def process_country_entry(
    request: CountryEntryRequest,
    background_tasks: BackgroundTasks,
    location_service: LocationProcessingService = Depends(get_location_service)
) -> CountryEntryResponse:
    """
    Process user country entry and generate immediate alerts.

    Args:
        request: Country entry request data
        background_tasks: FastAPI background tasks
        location_service: Location processing service

    Returns:
        Processing result with alerts and recommendations
    """
    try:
        logger.info(
            "Processing country entry",
            user_id=request.user_id,
            country=request.country_name,
            country_code=request.country_code
        )

        # Process the country entry
        result = await location_service.process_country_entry(
            user_id=request.user_id,
            latitude=request.coordinates.latitude,
            longitude=request.coordinates.longitude,
            country_code=request.country_code,
            country_name=request.country_name,
            device_id=request.device_id,
            previous_country_code=request.previous_country_code,
            accuracy_meters=request.coordinates.accuracy_meters,
            metadata=request.metadata
        )

        # Schedule background tasks for additional processing
        background_tasks.add_task(
            _update_user_location_history,
            request.user_id,
            request.country_code
        )

        return CountryEntryResponse(**result)

    except Exception as e:
        logger.error("Error processing country entry", error=str(e), user_id=request.user_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process country entry: {str(e)}"
        )


@router.post(
    "/geofence-trigger",
    response_model=GeofenceTriggerResponse,
    summary="Handle geofencing events",
    description="""
    Handle geofencing events from mobile applications.

    This endpoint processes geofence triggers when users enter or exit
    predefined geographic zones such as:
    - Border crossings
    - Airport perimeters
    - Embassy locations
    - High-risk areas
    - Tourist zones

    Automatically generates location-specific alerts and notifications.
    """
)
async def handle_geofence_trigger(
    request: GeofenceTriggerRequest,
    background_tasks: BackgroundTasks,
    location_service: LocationProcessingService = Depends(get_location_service)
) -> GeofenceTriggerResponse:
    """
    Handle geofencing events from mobile app.

    Args:
        request: Geofence trigger request data
        background_tasks: FastAPI background tasks
        location_service: Location processing service

    Returns:
        Processing result with triggered alerts
    """
    try:
        logger.info(
            "Processing geofence trigger",
            user_id=request.user_id,
            geofence_id=request.geofence_id,
            event_type=request.event_type
        )

        # Process the geofence trigger
        result = await location_service.process_geofence_trigger(
            user_id=request.user_id,
            latitude=request.coordinates.latitude,
            longitude=request.coordinates.longitude,
            geofence_id=request.geofence_id,
            event_type=request.event_type,
            device_id=request.device_id,
            metadata=request.metadata
        )

        # Schedule background analytics update
        background_tasks.add_task(
            _update_geofence_analytics,
            request.geofence_id,
            request.event_type
        )

        return GeofenceTriggerResponse(**result)

    except Exception as e:
        logger.error("Error processing geofence trigger", error=str(e), user_id=request.user_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process geofence trigger: {str(e)}"
        )


@router.get(
    "/country-brief/{country_code}",
    response_model=CountryBriefResponse,
    summary="Generate comprehensive country brief",
    description="""
    Generate a comprehensive entry brief for a specific country.

    This endpoint compiles information from multiple sources including:
    - Current travel advisories from all government sources
    - Entry requirements and visa information
    - Emergency contact details
    - Health and safety recommendations
    - Local customs and regulations

    Results are cached for performance and automatically updated based on
    advisory changes and data freshness requirements.
    """
)
async def get_country_brief(
    country_code: str,
    force_refresh: bool = False,
    location_service: LocationProcessingService = Depends(get_location_service)
) -> CountryBriefResponse:
    """
    Generate comprehensive country entry brief.

    Args:
        country_code: ISO 3166-1 alpha-3 country code
        force_refresh: Force regeneration even if cached brief exists
        location_service: Location processing service

    Returns:
        Comprehensive country brief with travel advisories and recommendations
    """
    try:
        # Validate country code format
        if len(country_code) not in [2, 3]:
            raise HTTPException(
                status_code=400,
                detail="Country code must be 2 or 3 characters"
            )

        country_code = country_code.upper()

        logger.info(
            "Generating country brief",
            country_code=country_code,
            force_refresh=force_refresh
        )

        # Generate the country brief
        result = await location_service.generate_country_brief(
            country_code=country_code,
            force_refresh=force_refresh
        )

        return CountryBriefResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error generating country brief", error=str(e), country_code=country_code)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate country brief: {str(e)}"
        )


@router.post(
    "/emergency-alerts",
    response_model=EmergencyAlertResponse,
    summary="Broadcast emergency alerts",
    description="""
    Push critical alerts to users in specific locations.

    This endpoint enables broadcasting emergency alerts to users based on:
    - Country location targeting
    - Regional/city targeting (optional)
    - Radius-based geographic targeting (optional)

    Alert types include:
    - Natural disaster warnings
    - Security threats
    - Health emergencies
    - Infrastructure disruptions
    - Evacuation notices

    Alerts are delivered through multiple channels with priority routing
    based on severity level.
    """
)
async def broadcast_emergency_alert(
    request: EmergencyAlertRequest,
    background_tasks: BackgroundTasks,
    location_service: LocationProcessingService = Depends(get_location_service)
) -> EmergencyAlertResponse:
    """
    Push critical alerts to users in specific locations.

    Args:
        request: Emergency alert broadcast request
        background_tasks: FastAPI background tasks
        location_service: Location processing service

    Returns:
        Broadcast result with delivery statistics
    """
    try:
        logger.info(
            "Broadcasting emergency alert",
            title=request.title,
            severity=request.severity.value,
            target_countries=request.target_countries
        )

        # Broadcast the emergency alert
        result = await location_service.broadcast_emergency_alert(
            title=request.title,
            message=request.message,
            severity=request.severity,
            target_countries=request.target_countries,
            alert_type=request.alert_type,
            target_regions=request.target_regions,
            radius_km=request.radius_km,
            expires_hours=request.expires_hours,
            issued_by=request.issued_by
        )

        # Schedule background tasks for additional processing
        background_tasks.add_task(
            _track_emergency_alert_effectiveness,
            result.get("broadcast_id")
        )

        return EmergencyAlertResponse(**result)

    except Exception as e:
        logger.error("Error broadcasting emergency alert", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to broadcast emergency alert: {str(e)}"
        )


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Location processing health check",
    description="""
    Check the health and performance of location processing services.

    Returns status information for:
    - Location processing service
    - API clients (travel advisory sources)
    - Database connectivity
    - Notification services
    - Processing performance metrics
    """
)
async def health_check() -> HealthCheckResponse:
    """
    Check health of location processing services.

    Returns:
        Health status with service details and metrics
    """
    try:
        # Check service health
        services_status = {}

        # Check database connectivity
        try:
            async with get_session() as session:
                await session.execute(select(1))
            services_status["database"] = True
        except Exception:
            services_status["database"] = False

        # Check API clients
        try:
            api_service = UnifiedAPIService()
            await api_service.initialize_clients()
            health_status = await api_service.health_check()
            services_status.update(health_status)
            await api_service.close()
        except Exception:
            services_status["api_clients"] = False

        # Get processing statistics
        processing_stats = await _get_processing_statistics()

        # Determine overall status
        overall_status = "healthy" if all(services_status.values()) else "degraded"

        return HealthCheckResponse(
            status=overall_status,
            timestamp=datetime.utcnow(),
            services=services_status,
            processing_stats=processing_stats
        )

    except Exception as e:
        logger.error("Error during health check", error=str(e))
        return HealthCheckResponse(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            services={"error": False},
            processing_stats=LocationProcessingStats(
                time_period_hours=24,
                total_events=0,
                country_entries=0,
                geofence_triggers=0,
                alerts_generated=0,
                average_processing_time_ms=0.0,
                error_rate=100.0
            )
        )


@router.get(
    "/stats",
    summary="Get location processing statistics",
    description="Get detailed statistics about location processing performance and usage."
)
async def get_processing_statistics(
    hours: int = 24
) -> Dict[str, Any]:
    """
    Get location processing statistics.

    Args:
        hours: Time period in hours to analyze

    Returns:
        Detailed processing statistics
    """
    try:
        return await _get_processing_statistics(hours)
    except Exception as e:
        logger.error("Error getting processing statistics", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get statistics: {str(e)}"
        )


# Background task functions

async def _update_user_location_history(user_id: str, country_code: str):
    """Update user location history in background."""
    try:
        # This would implement user location tracking logic
        logger.debug(
            "Updating user location history",
            user_id=user_id,
            country_code=country_code
        )
    except Exception as e:
        logger.warning("Error updating user location history", error=str(e))


async def _update_geofence_analytics(geofence_id: str, event_type: str):
    """Update geofence analytics in background."""
    try:
        # This would implement geofence usage analytics
        logger.debug(
            "Updating geofence analytics",
            geofence_id=geofence_id,
            event_type=event_type
        )
    except Exception as e:
        logger.warning("Error updating geofence analytics", error=str(e))


async def _track_emergency_alert_effectiveness(broadcast_id: Optional[str]):
    """Track emergency alert effectiveness in background."""
    try:
        if broadcast_id:
            # This would implement alert effectiveness tracking
            logger.debug("Tracking alert effectiveness", broadcast_id=broadcast_id)
    except Exception as e:
        logger.warning("Error tracking alert effectiveness", error=str(e))


async def _get_processing_statistics(hours: int = 24) -> LocationProcessingStats:
    """Get processing statistics for the specified time period."""
    try:
        async with get_session() as session:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)

            # Count location events by type
            events_query = select(
                func.count(LocationEvent.id).label('total'),
                func.count(LocationEvent.id).filter(
                    LocationEvent.event_type.in_(['country_entry', 'country_exit'])
                ).label('country_entries'),
                func.count(LocationEvent.id).filter(
                    LocationEvent.event_type.in_(['geofence_enter', 'geofence_exit'])
                ).label('geofence_triggers'),
                func.avg(LocationEvent.processing_time_ms).label('avg_processing_time')
            ).where(LocationEvent.created_at >= cutoff_time)

            events_result = await session.execute(events_query)
            events_stats = events_result.first()

            # Count alerts generated
            alerts_query = select(func.count(LocationAlert.id)).where(
                LocationAlert.created_at >= cutoff_time
            )
            alerts_result = await session.execute(alerts_query)
            alerts_count = alerts_result.scalar() or 0

            # Calculate error rate (events without successful processing)
            error_query = select(func.count(LocationEvent.id)).where(
                and_(
                    LocationEvent.created_at >= cutoff_time,
                    LocationEvent.processed_at.is_(None)
                )
            )
            error_result = await session.execute(error_query)
            error_count = error_result.scalar() or 0

            total_events = events_stats.total or 0
            error_rate = (error_count / total_events * 100) if total_events > 0 else 0

            return LocationProcessingStats(
                time_period_hours=hours,
                total_events=total_events,
                country_entries=events_stats.country_entries or 0,
                geofence_triggers=events_stats.geofence_triggers or 0,
                alerts_generated=alerts_count,
                average_processing_time_ms=float(events_stats.avg_processing_time or 0),
                error_rate=round(error_rate, 2)
            )

    except Exception as e:
        logger.error("Error getting processing statistics", error=str(e))
        return LocationProcessingStats(
            time_period_hours=hours,
            total_events=0,
            country_entries=0,
            geofence_triggers=0,
            alerts_generated=0,
            average_processing_time_ms=0.0,
            error_rate=0.0
        )