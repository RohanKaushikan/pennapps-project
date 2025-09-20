from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from app.core.database import get_session
from app.models.user import User
from app.models.user_alert import UserAlert
from app.models.alert import Alert
from app.schemas.user import UserCreate, UserResponse
from app.schemas.common import MessageResponse

router = APIRouter()


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate,
    db: AsyncSession = Depends(get_session)
):
    """
    Create a new user for reactive travel alerts.
    
    No advance setup required - users just need to provide their email.
    The system will automatically send alerts when they enter new countries.
    """
    # Check if user already exists
    result = await db.execute(
        select(User).where(User.email == user.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    # Create new user with minimal preferences - reactive system handles everything
    initial_preferences = {
        "system_type": "reactive",
        "created_at": datetime.utcnow().isoformat(),
        "notification_enabled": True
    }

    db_user = User(
        email=user.email,
        travel_preferences=initial_preferences
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_session)
):
    """
    Get user information including location tracking status.
    """
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


@router.get("/{user_id}/alerts", response_model=List[dict])
async def get_user_alerts(
    user_id: int,
    skip: int = 0,
    limit: int = 50,
    unread_only: bool = False,
    db: AsyncSession = Depends(get_session)
):
    """
    Get alerts for a specific user.
    """
    # Verify user exists
    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    if not user_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Build query for user alerts
    query = select(UserAlert, Alert).join(Alert).where(UserAlert.user_id == user_id)

    if unread_only:
        query = query.where(UserAlert.is_read == False)

    query = query.order_by(UserAlert.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    user_alerts = result.all()

    # Format response
    formatted_alerts = []
    for user_alert, alert in user_alerts:
        alert_dict = {
            "user_alert_id": user_alert.id,
            "alert_id": alert.id,
            "title": alert.title,
            "description": alert.description,
            "risk_level": alert.risk_level,
            "categories": alert.categories,
            "is_read": user_alert.is_read,
            "notified_at": user_alert.notified_at.isoformat() if user_alert.notified_at else None,
            "expires_at": alert.expires_at.isoformat() if alert.expires_at else None,
            "created_at": alert.created_at.isoformat()
        }
        formatted_alerts.append(alert_dict)

    return formatted_alerts


@router.put("/{user_id}/alerts/{alert_id}/read", response_model=MessageResponse)
async def mark_alert_read(
    user_id: int,
    alert_id: int,
    db: AsyncSession = Depends(get_session)
):
    """
    Mark a specific alert as read for a user.
    """
    # Find the user alert
    result = await db.execute(
        select(UserAlert).where(
            UserAlert.user_id == user_id,
            UserAlert.alert_id == alert_id
        )
    )
    user_alert = result.scalar_one_or_none()

    if not user_alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found for this user"
        )

    # Mark as read
    user_alert.is_read = True
    await db.commit()

    return MessageResponse(message="Alert marked as read")


@router.get("/{user_id}/stats", response_model=dict)
async def get_user_stats(
    user_id: int,
    db: AsyncSession = Depends(get_session)
):
    """
    Get user statistics for location tracking and alerts.
    """
    # Verify user exists
    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get alert statistics
    total_alerts_result = await db.execute(
        select(func.count(UserAlert.id)).where(UserAlert.user_id == user_id)
    )
    total_alerts = total_alerts_result.scalar() or 0

    unread_alerts_result = await db.execute(
        select(func.count(UserAlert.id)).where(
            UserAlert.user_id == user_id,
            UserAlert.is_read == False
        )
    )
    unread_alerts = unread_alerts_result.scalar() or 0

    # Get location history count
    location_updates = 0
    if user.travel_preferences and "location_history" in user.travel_preferences:
        location_updates = len(user.travel_preferences["location_history"])

    # Get current location info
    current_location = None
    if user.travel_preferences and "current_location" in user.travel_preferences:
        current_location = user.travel_preferences["current_location"]

    return {
        "user_id": user_id,
        "total_alerts": total_alerts,
        "unread_alerts": unread_alerts,
        "location_updates": location_updates,
        "current_location": current_location,
        "location_tracking_enabled": user.travel_preferences.get("location_tracking_enabled", False) if user.travel_preferences else False,
        "last_active": user.updated_at.isoformat()
    }