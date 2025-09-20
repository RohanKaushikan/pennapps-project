from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator
from .common import BaseSchema


class AlertBase(BaseSchema):
    """Base alert schema with common fields."""
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1)
    country_id: int = Field(..., gt=0)
    source_id: int = Field(..., gt=0)
    risk_level: int = Field(..., ge=1, le=5, description="Risk level from 1 (low) to 5 (critical)")
    expires_at: Optional[datetime] = Field(None, description="When this alert expires")
    categories: List[str] = Field(
        default=[],
        description="Array of categories like visa, legal, safety, health"
    )
    raw_content: Optional[str] = Field(
        None,
        description="Original content from the source before processing"
    )

    @validator("categories", pre=True)
    def validate_categories(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [cat.strip() for cat in v.split(",") if cat.strip()]
        return v


class AlertCreate(AlertBase):
    """Schema for creating a new alert."""
    pass


class AlertUpdate(BaseSchema):
    """Schema for updating alert information."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = Field(None, min_length=1)
    country_id: Optional[int] = Field(None, gt=0)
    source_id: Optional[int] = Field(None, gt=0)
    risk_level: Optional[int] = Field(None, ge=1, le=5)
    expires_at: Optional[datetime] = None
    categories: Optional[List[str]] = None
    raw_content: Optional[str] = None

    @validator("categories", pre=True)
    def validate_categories(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            return [cat.strip() for cat in v.split(",") if cat.strip()]
        return v


class AlertInDB(AlertBase):
    """Schema for alert data in database."""
    id: int
    created_at: datetime
    updated_at: datetime


class AlertResponse(AlertBase):
    """Schema for alert data in API responses."""
    id: int
    created_at: datetime
    updated_at: datetime


class AlertWithRelations(AlertResponse):
    """Schema for alert data with related entities."""
    country: Optional[dict] = None  # CountryResponse
    source: Optional[dict] = None   # SourceResponse


class AlertSummary(BaseSchema):
    """Schema for alert summary data."""
    id: int
    title: str
    risk_level: int
    country_id: int
    created_at: datetime


class AlertStats(BaseSchema):
    """Schema for alert statistics."""
    total_alerts: int = 0
    active_alerts: int = 0
    by_risk_level: dict = {}
    by_category: dict = {}
    by_country: dict = {}
    recent_alerts: List[AlertSummary] = []


class AlertFilter(BaseSchema):
    """Schema for alert filtering with comprehensive query parameters."""
    # Risk and priority filters
    risk_level: Optional[int] = Field(None, ge=1, le=5, description="Exact risk level")
    min_risk_level: Optional[int] = Field(None, ge=1, le=5, description="Minimum risk level")
    max_risk_level: Optional[int] = Field(None, ge=1, le=5, description="Maximum risk level")

    # Geographic filters
    country_ids: Optional[List[int]] = Field(None, description="List of country IDs")
    country_codes: Optional[List[str]] = Field(None, description="List of country codes")
    source_ids: Optional[List[int]] = Field(None, description="List of source IDs")

    # Category filters
    categories: Optional[List[str]] = Field(None, description="Alert categories to include")
    exclude_categories: Optional[List[str]] = Field(None, description="Alert categories to exclude")

    # Date range filters
    created_after: Optional[datetime] = Field(None, description="Alerts created after this date")
    created_before: Optional[datetime] = Field(None, description="Alerts created before this date")
    expires_after: Optional[datetime] = Field(None, description="Alerts expiring after this date")
    expires_before: Optional[datetime] = Field(None, description="Alerts expiring before this date")

    # Active/expired filters
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    has_expiry: Optional[bool] = Field(None, description="Filter alerts with/without expiry dates")

    # Text search
    search: Optional[str] = Field(None, min_length=3, description="Search in title and description")

    # User-specific filters
    user_id: Optional[int] = Field(None, description="Filter alerts for specific user")
    is_read: Optional[bool] = Field(None, description="Filter by read status for user")

    @validator("categories", "exclude_categories", pre=True)
    def validate_categories_list(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            return [cat.strip().lower() for cat in v.split(",") if cat.strip()]
        return [cat.lower() for cat in v if cat]

    @validator("country_codes", pre=True)
    def validate_country_codes(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            return [code.strip().upper() for code in v.split(",") if code.strip()]
        return [code.upper() for code in v if code]


class AlertSort(BaseSchema):
    """Schema for alert sorting options."""
    sort_by: str = Field(
        "created_at",
        pattern="^(created_at|updated_at|risk_level|expires_at|title)$",
        description="Field to sort by"
    )
    sort_order: str = Field(
        "desc",
        pattern="^(asc|desc)$",
        description="Sort order"
    )


class PaginationParams(BaseSchema):
    """Schema for pagination parameters."""
    page: int = Field(1, ge=1, description="Page number")
    per_page: int = Field(20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page

    @property
    def limit(self) -> int:
        return self.per_page


class AlertListResponse(BaseSchema):
    """Schema for paginated alert list responses."""
    alerts: List[AlertResponse]
    pagination: dict
    filters_applied: dict
    total_count: int


class AlertDetailResponse(AlertResponse):
    """Schema for detailed alert responses with related data."""
    country: Optional[dict] = None
    source: Optional[dict] = None
    user_status: Optional[dict] = None  # For user-specific data like read status


class AlertCreateInternal(BaseSchema):
    """Schema for internal alert creation (admin/system use)."""
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1)
    country_id: int = Field(..., gt=0)
    source_id: int = Field(..., gt=0)
    risk_level: int = Field(..., ge=1, le=5)
    expires_at: Optional[datetime] = None
    categories: List[str] = Field(default=[])
    raw_content: Optional[str] = None

    # Additional fields for internal creation
    priority: str = Field("medium", pattern="^(low|medium|high|urgent)$")
    auto_notify_users: bool = Field(True, description="Automatically notify relevant users")

    @validator("categories", pre=True)
    def validate_categories(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [cat.strip().lower() for cat in v.split(",") if cat.strip()]
        return [cat.lower() for cat in v if cat]


class AlertUpdateInternal(BaseSchema):
    """Schema for internal alert updates."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = Field(None, min_length=1)
    risk_level: Optional[int] = Field(None, ge=1, le=5)
    expires_at: Optional[datetime] = None
    categories: Optional[List[str]] = None
    raw_content: Optional[str] = None
    is_active: Optional[bool] = None

    @validator("categories", pre=True)
    def validate_categories(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            return [cat.strip().lower() for cat in v.split(",") if cat.strip()]
        return [cat.lower() for cat in v if cat]


class UserAlertAction(BaseSchema):
    """Schema for user actions on alerts."""
    user_id: int = Field(..., gt=0)
    action: str = Field(..., pattern="^(mark_read|mark_unread|dismiss|save)$")
    notes: Optional[str] = Field(None, max_length=500)