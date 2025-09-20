"""
Query helper utilities for filtering, pagination, and sorting.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import Select, func, or_, and_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.alert import Alert
from app.models.country import Country
from app.models.source import Source
from app.models.user_alert import UserAlert
from app.schemas.alert import AlertFilter, AlertSort, PaginationParams


class AlertQueryBuilder:
    """Helper class for building complex alert queries with filtering and pagination."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.base_query = None

    def build_query(
        self,
        filters: AlertFilter,
        sort_params: AlertSort,
        include_relations: bool = False,
        user_id: Optional[int] = None
    ) -> Select:
        """
        Build a comprehensive alert query with filters and sorting.

        Args:
            filters: Filter parameters
            sort_params: Sort parameters
            include_relations: Whether to include country/source relations
            user_id: Include user-specific data (read status, etc.)

        Returns:
            SQLAlchemy Select query
        """
        # Start with base query
        if user_id:
            # Join with UserAlert for user-specific data
            query = (
                select(Alert, UserAlert)
                .outerjoin(UserAlert, and_(
                    UserAlert.alert_id == Alert.id,
                    UserAlert.user_id == user_id
                ))
            )
        else:
            query = select(Alert)

        # Add relations if requested
        if include_relations:
            query = query.options(
                selectinload(Alert.country),
                selectinload(Alert.source)
            )

        # Apply filters
        query = self._apply_filters(query, filters)

        # Apply sorting
        query = self._apply_sorting(query, sort_params)

        return query

    def _apply_filters(self, query: Select, filters: AlertFilter) -> Select:
        """Apply all filters to the query."""
        conditions = []

        # Risk level filters
        if filters.risk_level is not None:
            conditions.append(Alert.risk_level == filters.risk_level)
        if filters.min_risk_level is not None:
            conditions.append(Alert.risk_level >= filters.min_risk_level)
        if filters.max_risk_level is not None:
            conditions.append(Alert.risk_level <= filters.max_risk_level)

        # Geographic filters
        if filters.country_ids:
            conditions.append(Alert.country_id.in_(filters.country_ids))

        if filters.country_codes:
            # Need to join with Country table for country code filtering
            country_subquery = select(Country.id).where(Country.code.in_(filters.country_codes))
            conditions.append(Alert.country_id.in_(country_subquery))

        if filters.source_ids:
            conditions.append(Alert.source_id.in_(filters.source_ids))

        # Category filters
        if filters.categories:
            category_conditions = []
            for category in filters.categories:
                category_conditions.append(Alert.categories.contains([category]))
            conditions.append(or_(*category_conditions))

        if filters.exclude_categories:
            for category in filters.exclude_categories:
                conditions.append(~Alert.categories.contains([category]))

        # Date filters
        if filters.created_after:
            conditions.append(Alert.created_at >= filters.created_after)
        if filters.created_before:
            conditions.append(Alert.created_at <= filters.created_before)
        if filters.expires_after:
            conditions.append(Alert.expires_at >= filters.expires_after)
        if filters.expires_before:
            conditions.append(Alert.expires_at <= filters.expires_before)

        # Active/expired filters
        if filters.is_active is True:
            conditions.append(
                or_(
                    Alert.expires_at.is_(None),
                    Alert.expires_at > func.now()
                )
            )
        elif filters.is_active is False:
            conditions.append(
                and_(
                    Alert.expires_at.is_not(None),
                    Alert.expires_at <= func.now()
                )
            )

        if filters.has_expiry is True:
            conditions.append(Alert.expires_at.is_not(None))
        elif filters.has_expiry is False:
            conditions.append(Alert.expires_at.is_(None))

        # Text search
        if filters.search:
            search_term = f"%{filters.search}%"
            conditions.append(
                or_(
                    Alert.title.ilike(search_term),
                    Alert.description.ilike(search_term)
                )
            )

        # User-specific filters (only if UserAlert is joined)
        if filters.user_id and filters.is_read is not None:
            if filters.is_read:
                conditions.append(UserAlert.is_read == True)
            else:
                conditions.append(
                    or_(
                        UserAlert.is_read == False,
                        UserAlert.id.is_(None)  # Alert not seen by user
                    )
                )

        # Apply all conditions
        if conditions:
            query = query.where(and_(*conditions))

        return query

    def _apply_sorting(self, query: Select, sort_params: AlertSort) -> Select:
        """Apply sorting to the query."""
        sort_column = getattr(Alert, sort_params.sort_by, Alert.created_at)

        if sort_params.sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        # Secondary sort by ID for consistency
        query = query.order_by(desc(Alert.id))

        return query

    async def get_paginated_results(
        self,
        query: Select,
        pagination: PaginationParams
    ) -> Tuple[List[Any], int]:
        """
        Execute paginated query and return results with total count.

        Returns:
            Tuple of (results, total_count)
        """
        # Get total count (without pagination)
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total_count = total_result.scalar()

        # Get paginated results
        paginated_query = query.offset(pagination.offset).limit(pagination.limit)
        result = await self.session.execute(paginated_query)

        return result.all(), total_count

    async def get_country_alerts(
        self,
        country_code: str,
        filters: AlertFilter,
        sort_params: AlertSort,
        pagination: PaginationParams
    ) -> Tuple[List[Alert], int]:
        """Get alerts for a specific country with filtering and pagination."""
        # Start with country-specific query
        query = (
            select(Alert)
            .join(Country)
            .where(Country.code == country_code.upper())
        )

        # Apply additional filters (excluding country filters)
        country_filters = AlertFilter(**filters.dict())
        country_filters.country_codes = None
        country_filters.country_ids = None

        query = self._apply_filters(query, country_filters)
        query = self._apply_sorting(query, sort_params)

        return await self.get_paginated_results(query, pagination)


def build_pagination_response(
    items: List[Any],
    total_count: int,
    pagination: PaginationParams
) -> Dict[str, Any]:
    """Build pagination metadata for API responses."""
    total_pages = (total_count + pagination.per_page - 1) // pagination.per_page

    return {
        "current_page": pagination.page,
        "per_page": pagination.per_page,
        "total_items": total_count,
        "total_pages": total_pages,
        "has_next": pagination.page < total_pages,
        "has_prev": pagination.page > 1,
        "next_page": pagination.page + 1 if pagination.page < total_pages else None,
        "prev_page": pagination.page - 1 if pagination.page > 1 else None
    }


def format_alert_with_relations(
    alert: Alert,
    include_country: bool = True,
    include_source: bool = True,
    user_alert: Optional[UserAlert] = None
) -> Dict[str, Any]:
    """Format alert with related data for API responses."""
    alert_dict = {
        "id": alert.id,
        "title": alert.title,
        "description": alert.description,
        "risk_level": alert.risk_level,
        "categories": alert.categories,
        "expires_at": alert.expires_at.isoformat() if alert.expires_at else None,
        "created_at": alert.created_at.isoformat(),
        "updated_at": alert.updated_at.isoformat(),
        "raw_content": alert.raw_content
    }

    # Add country information
    if include_country and hasattr(alert, 'country') and alert.country:
        alert_dict["country"] = {
            "id": alert.country.id,
            "code": alert.country.code,
            "name": alert.country.name,
            "region": alert.country.region
        }
    else:
        alert_dict["country_id"] = alert.country_id

    # Add source information
    if include_source and hasattr(alert, 'source') and alert.source:
        alert_dict["source"] = {
            "id": alert.source.id,
            "name": alert.source.name,
            "source_type": alert.source.source_type,
            "url": alert.source.url
        }
    else:
        alert_dict["source_id"] = alert.source_id

    # Add user-specific data
    if user_alert:
        alert_dict["user_status"] = {
            "is_read": user_alert.is_read,
            "notified_at": user_alert.notified_at.isoformat() if user_alert.notified_at else None,
            "user_alert_id": user_alert.id
        }

    return alert_dict


async def get_alert_statistics(
    session: AsyncSession,
    filters: AlertFilter = None
) -> Dict[str, Any]:
    """Get comprehensive alert statistics."""
    base_query = select(Alert)

    if filters:
        query_builder = AlertQueryBuilder(session)
        base_query = query_builder._apply_filters(base_query, filters)

    # Total count
    total_result = await session.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total_count = total_result.scalar()

    # Active count
    active_query = base_query.where(
        or_(
            Alert.expires_at.is_(None),
            Alert.expires_at > func.now()
        )
    )
    active_result = await session.execute(
        select(func.count()).select_from(active_query.subquery())
    )
    active_count = active_result.scalar()

    # Risk level distribution
    risk_distribution = {}
    for risk_level in range(1, 6):
        risk_query = base_query.where(Alert.risk_level == risk_level)
        risk_result = await session.execute(
            select(func.count()).select_from(risk_query.subquery())
        )
        risk_distribution[f"level_{risk_level}"] = risk_result.scalar()

    return {
        "total_alerts": total_count,
        "active_alerts": active_count,
        "expired_alerts": total_count - active_count,
        "risk_distribution": risk_distribution,
        "generated_at": datetime.utcnow().isoformat()
    }


from sqlalchemy import select