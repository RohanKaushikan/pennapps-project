from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
import logging

from app.core.database import get_session
from app.models.alert import Alert
from app.models.country import Country
from app.models.source import Source
from app.models.user import User
from app.models.user_alert import UserAlert
from app.schemas.alert import (
    AlertResponse,
    AlertDetailResponse,
    AlertListResponse,
    AlertCreateInternal,
    AlertUpdateInternal,
    AlertFilter,
    AlertSort,
    PaginationParams,
    UserAlertAction
)
from app.schemas.common import MessageResponse
from app.utils.query_helpers import (
    AlertQueryBuilder,
    build_pagination_response,
    format_alert_with_relations,
    get_alert_statistics
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=AlertListResponse)
async def get_alerts(
    # Pagination
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),

    # Sorting
    sort_by: str = Query("created_at", regex="^(created_at|updated_at|risk_level|expires_at|title)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),

    # Risk level filters
    risk_level: Optional[int] = Query(None, ge=1, le=5, description="Exact risk level"),
    min_risk_level: Optional[int] = Query(None, ge=1, le=5, description="Minimum risk level"),
    max_risk_level: Optional[int] = Query(None, ge=1, le=5, description="Maximum risk level"),

    # Geographic filters
    country_ids: Optional[str] = Query(None, description="Comma-separated country IDs"),
    country_codes: Optional[str] = Query(None, description="Comma-separated country codes"),
    source_ids: Optional[str] = Query(None, description="Comma-separated source IDs"),

    # Category filters
    categories: Optional[str] = Query(None, description="Comma-separated categories to include"),
    exclude_categories: Optional[str] = Query(None, description="Comma-separated categories to exclude"),

    # Date filters
    created_after: Optional[datetime] = Query(None, description="Alerts created after this date"),
    created_before: Optional[datetime] = Query(None, description="Alerts created before this date"),
    expires_after: Optional[datetime] = Query(None, description="Alerts expiring after this date"),
    expires_before: Optional[datetime] = Query(None, description="Alerts expiring before this date"),

    # Status filters
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    has_expiry: Optional[bool] = Query(None, description="Filter alerts with/without expiry dates"),

    # Search
    search: Optional[str] = Query(None, min_length=3, description="Search in title and description"),

    # User-specific filters
    user_id: Optional[int] = Query(None, description="Filter alerts for specific user"),
    is_read: Optional[bool] = Query(None, description="Filter by read status for user"),

    db: AsyncSession = Depends(get_session)
):
    """
    Get all alerts with comprehensive filtering, pagination, and sorting.

    This endpoint supports extensive filtering options:
    - Risk level filtering (exact, min, max)
    - Geographic filtering (countries, sources)
    - Category inclusion/exclusion
    - Date range filtering
    - Text search
    - User-specific filtering
    """
    try:
        # Parse comma-separated filters
        parsed_filters = AlertFilter(
            risk_level=risk_level,
            min_risk_level=min_risk_level,
            max_risk_level=max_risk_level,
            country_ids=[int(x) for x in country_ids.split(",")] if country_ids else None,
            country_codes=country_codes.split(",") if country_codes else None,
            source_ids=[int(x) for x in source_ids.split(",")] if source_ids else None,
            categories=categories,
            exclude_categories=exclude_categories,
            created_after=created_after,
            created_before=created_before,
            expires_after=expires_after,
            expires_before=expires_before,
            is_active=is_active,
            has_expiry=has_expiry,
            search=search,
            user_id=user_id,
            is_read=is_read
        )

        sort_params = AlertSort(sort_by=sort_by, sort_order=sort_order)
        pagination = PaginationParams(page=page, per_page=per_page)

        # Build and execute query
        query_builder = AlertQueryBuilder(db)
        query = query_builder.build_query(
            filters=parsed_filters,
            sort_params=sort_params,
            include_relations=True,
            user_id=user_id
        )

        results, total_count = await query_builder.get_paginated_results(query, pagination)

        # Format results
        formatted_alerts = []
        for result in results:
            if user_id and len(result) == 2:
                alert, user_alert = result
            else:
                alert = result[0] if isinstance(result, tuple) else result
                user_alert = None

            formatted_alert = format_alert_with_relations(
                alert=alert,
                include_country=True,
                include_source=True,
                user_alert=user_alert
            )
            formatted_alerts.append(AlertResponse(**formatted_alert))

        # Build pagination metadata
        pagination_data = build_pagination_response(formatted_alerts, total_count, pagination)

        # Build filters applied metadata
        filters_applied = {k: v for k, v in parsed_filters.dict().items() if v is not None}

        return AlertListResponse(
            alerts=formatted_alerts,
            pagination=pagination_data,
            filters_applied=filters_applied,
            total_count=total_count
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid filter parameters: {e}"
        )
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching alerts"
        )


@router.get("/{alert_id}", response_model=AlertDetailResponse)
async def get_alert(
    alert_id: int,
    user_id: Optional[int] = Query(None, description="Include user-specific data"),
    db: AsyncSession = Depends(get_session)
):
    """
    Get a specific alert by ID with detailed information.
    Optionally includes user-specific data like read status.
    """
    try:
        # Get alert with relations
        query = (
            select(Alert)
            .options(
                selectinload(Alert.country),
                selectinload(Alert.source)
            )
            .where(Alert.id == alert_id)
        )

        result = await db.execute(query)
        alert = result.scalar_one_or_none()

        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )

        # Get user-specific data if requested
        user_alert = None
        if user_id:
            user_alert_result = await db.execute(
                select(UserAlert).where(
                    UserAlert.user_id == user_id,
                    UserAlert.alert_id == alert_id
                )
            )
            user_alert = user_alert_result.scalar_one_or_none()

        # Format response
        formatted_alert = format_alert_with_relations(
            alert=alert,
            include_country=True,
            include_source=True,
            user_alert=user_alert
        )

        return AlertDetailResponse(**formatted_alert)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching alert {alert_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching alert"
        )


@router.post("/", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert: AlertCreateInternal,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session)
):
    """
    Create a new alert (for internal/admin use).
    Automatically processes user notifications if enabled.
    """
    try:
        # Verify country and source exist
        country_result = await db.execute(
            select(Country).where(Country.id == alert.country_id)
        )
        country = country_result.scalar_one_or_none()
        if not country:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Country not found"
            )

        source_result = await db.execute(
            select(Source).where(Source.id == alert.source_id)
        )
        source = source_result.scalar_one_or_none()
        if not source:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source not found"
            )

        # Create new alert
        db_alert = Alert(
            title=alert.title,
            description=alert.description,
            country_id=alert.country_id,
            source_id=alert.source_id,
            risk_level=alert.risk_level,
            expires_at=alert.expires_at,
            categories=alert.categories,
            raw_content=alert.raw_content
        )

        db.add(db_alert)
        await db.commit()
        await db.refresh(db_alert)

        # Schedule user notifications if enabled
        if alert.auto_notify_users:
            background_tasks.add_task(
                _process_alert_notifications,
                db_alert.id,
                alert.risk_level
            )

        return AlertResponse(**format_alert_with_relations(db_alert))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating alert"
        )


@router.get("/country/{country_code}", response_model=AlertListResponse)
async def get_country_alerts(
    country_code: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at", regex="^(created_at|updated_at|risk_level|expires_at|title)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    risk_level: Optional[int] = Query(None, ge=1, le=5),
    min_risk_level: Optional[int] = Query(None, ge=1, le=5),
    categories: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None, min_length=3),
    user_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_session)
):
    """
    Get alerts for a specific country with filtering and pagination.
    """
    try:
        # Verify country exists
        country_result = await db.execute(
            select(Country).where(Country.code == country_code.upper())
        )
        country = country_result.scalar_one_or_none()
        if not country:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Country not found"
            )

        # Build filters
        filters = AlertFilter(
            risk_level=risk_level,
            min_risk_level=min_risk_level,
            categories=categories,
            is_active=is_active,
            search=search,
            user_id=user_id,
            country_ids=[country.id]  # Force filter to this country
        )

        sort_params = AlertSort(sort_by=sort_by, sort_order=sort_order)
        pagination = PaginationParams(page=page, per_page=per_page)

        # Build and execute query
        query_builder = AlertQueryBuilder(db)
        results, total_count = await query_builder.get_country_alerts(
            country_code=country_code,
            filters=filters,
            sort_params=sort_params,
            pagination=pagination
        )

        # Format results
        formatted_alerts = []
        for alert in results:
            formatted_alert = format_alert_with_relations(alert, include_source=True)
            formatted_alerts.append(AlertResponse(**formatted_alert))

        pagination_data = build_pagination_response(formatted_alerts, total_count, pagination)
        filters_applied = {k: v for k, v in filters.dict().items() if v is not None}

        return AlertListResponse(
            alerts=formatted_alerts,
            pagination=pagination_data,
            filters_applied=filters_applied,
            total_count=total_count
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching alerts for country {country_code}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching country alerts"
        )


@router.post("/{alert_id}/mark-read", response_model=MessageResponse)
async def mark_alert_read(
    alert_id: int,
    user_action: UserAlertAction,
    db: AsyncSession = Depends(get_session)
):
    """
    Mark alert as read for a specific user.
    Creates user-alert relationship if it doesn't exist.
    """
    try:
        # Verify alert exists
        alert_result = await db.execute(
            select(Alert).where(Alert.id == alert_id)
        )
        alert = alert_result.scalar_one_or_none()
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )

        # Verify user exists
        user_result = await db.execute(
            select(User).where(User.id == user_action.user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get or create user-alert relationship
        user_alert_result = await db.execute(
            select(UserAlert).where(
                UserAlert.user_id == user_action.user_id,
                UserAlert.alert_id == alert_id
            )
        )
        user_alert = user_alert_result.scalar_one_or_none()

        if not user_alert:
            # Create new user-alert relationship
            user_alert = UserAlert(
                user_id=user_action.user_id,
                alert_id=alert_id,
                is_read=False,
                notified_at=datetime.utcnow()
            )
            db.add(user_alert)

        # Update based on action
        if user_action.action == "mark_read":
            user_alert.is_read = True
        elif user_action.action == "mark_unread":
            user_alert.is_read = False

        await db.commit()

        action_message = {
            "mark_read": "Alert marked as read",
            "mark_unread": "Alert marked as unread",
            "dismiss": "Alert dismissed",
            "save": "Alert saved"
        }

        return MessageResponse(
            message=action_message.get(user_action.action, "Action completed")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating alert {alert_id} for user {user_action.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating alert status"
        )


@router.get("/stats/overview", response_model=dict)
async def get_alert_stats(
    country_codes: Optional[str] = Query(None, description="Filter stats by country codes"),
    risk_level: Optional[int] = Query(None, ge=1, le=5),
    categories: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_session)
):
    """
    Get comprehensive alert statistics with optional filtering.
    """
    try:
        # Build filters for statistics
        filters = AlertFilter(
            country_codes=country_codes.split(",") if country_codes else None,
            risk_level=risk_level,
            categories=categories
        )

        stats = await get_alert_statistics(db, filters)
        return stats

    except Exception as e:
        logger.error(f"Error generating alert statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating statistics"
        )


# Background task functions
async def _process_alert_notifications(alert_id: int, risk_level: int):
    """Background task to process alert notifications to relevant users."""
    logger.info(f"Processing notifications for alert {alert_id} with risk level {risk_level}")
    # In production, this would:
    # - Find users interested in the country/categories
    # - Create UserAlert relationships
    # - Send push notifications based on user preferences
    # - Log notification events


from sqlalchemy.orm import selectinload