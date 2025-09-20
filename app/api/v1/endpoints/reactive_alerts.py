"""
Reactive Alert Endpoints - Only triggers when users enter new countries.
No advance setup required.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import logging

from app.core.database import get_session
from app.services.reactive_alert_service import ReactiveAlertService
from app.schemas.location import UserLocationUpdate
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/location-update")
async def process_location_update(
    location_update: UserLocationUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session)
):
    """
    Process user location update and trigger alerts if they enter a new country.
    
    This is the main endpoint for the reactive system. Users only need to:
    1. Send their GPS coordinates
    2. Get comprehensive alerts if they enter a new country
    
    No advance setup, country selection, or alert configuration required.
    """
    try:
        service = ReactiveAlertService(db)
        
        result = await service.process_user_location_update(
            user_id=location_update.user_id,
            latitude=location_update.latitude,
            longitude=location_update.longitude,
            accuracy=location_update.accuracy
        )

        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )

        # Schedule background tasks for analytics and notifications
        if result.get("is_new_country"):
            background_tasks.add_task(
                _process_new_country_analytics,
                location_update.user_id,
                result["country_detected"]["code"],
                len(result["alerts_triggered"])
            )

        return {
            "success": True,
            "data": result,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing location update: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing location update"
        )


@router.get("/travel-history/{user_id}")
async def get_user_travel_history(
    user_id: int,
    db: AsyncSession = Depends(get_session)
):
    """
    Get user's travel history - all countries they've entered.
    """
    try:
        service = ReactiveAlertService(db)
        history = await service.get_user_travel_history(user_id)
        
        return {
            "success": True,
            "user_id": user_id,
            "travel_history": history,
            "total_countries": len(history),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting travel history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving travel history"
        )


@router.get("/country-summary/{country_code}")
async def get_country_entry_summary(
    country_code: str,
    db: AsyncSession = Depends(get_session)
):
    """
    Get summary of recent entries to a specific country.
    Useful for analytics and understanding travel patterns.
    """
    try:
        service = ReactiveAlertService(db)
        summary = await service.get_country_entry_summary(country_code.upper())
        
        return {
            "success": True,
            "summary": summary,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting country summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving country summary"
        )


@router.post("/test-country-entry/{country_code}")
async def test_country_entry(
    country_code: str,
    user_id: int,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    db: AsyncSession = Depends(get_session)
):
    """
    Test endpoint to simulate country entry without GPS.
    Useful for testing and demonstration purposes.
    """
    try:
        # Use default coordinates for the country if not provided
        if latitude is None or longitude is None:
            # Default coordinates for major cities
            default_coords = {
                "US": (40.7128, -74.0060),  # New York
                "FR": (48.8566, 2.3522),    # Paris
                "GB": (51.5074, -0.1278),   # London
                "DE": (52.5200, 13.4050),   # Berlin
                "JP": (35.6762, 139.6503),  # Tokyo
                "CA": (43.6532, -79.3832),  # Toronto
                "AU": (-33.8688, 151.2093), # Sydney
                "BR": (-23.5505, -46.6333), # São Paulo
                "IN": (28.6139, 77.2090),   # New Delhi
                "CN": (39.9042, 116.4074),  # Beijing
            }
            latitude, longitude = default_coords.get(country_code.upper(), (0.0, 0.0))

        service = ReactiveAlertService(db)
        
        result = await service.process_user_location_update(
            user_id=user_id,
            latitude=latitude,
            longitude=longitude,
            accuracy=10.0
        )

        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )

        return {
            "success": True,
            "message": f"Tested country entry for {country_code}",
            "data": result,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing country entry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error testing country entry"
        )


# Background task functions
async def _process_new_country_analytics(
    user_id: int,
    country_code: str,
    alerts_count: int
):
    """Background task to process analytics for new country entries."""
    logger.info(
        f"Processing new country analytics: User {user_id} entered {country_code}, "
        f"triggered {alerts_count} alerts"
    )
    
    # In production, this would:
    # - Update user travel patterns
    # - Calculate country popularity metrics
    # - Update ML models for better country detection
    # - Generate personalized recommendations
    # - Send analytics events to monitoring systems
