from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl
from .common import BaseSchema


class SourceBase(BaseSchema):
    """Base source schema with common fields."""
    name: str = Field(..., min_length=1, max_length=200)
    url: HttpUrl
    country_id: int = Field(..., gt=0)
    source_type: str = Field(
        ...,
        pattern="^(government|news|legal|embassy|ngo)$",
        description="Type of source"
    )
    is_active: bool = True


class SourceCreate(SourceBase):
    """Schema for creating a new source."""
    pass


class SourceUpdate(BaseSchema):
    """Schema for updating source information."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    url: Optional[HttpUrl] = None
    country_id: Optional[int] = Field(None, gt=0)
    source_type: Optional[str] = Field(
        None,
        pattern="^(government|news|legal|embassy|ngo)$"
    )
    is_active: Optional[bool] = None


class SourceInDB(SourceBase):
    """Schema for source data in database."""
    id: int
    last_scraped: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class SourceResponse(SourceBase):
    """Schema for source data in API responses."""
    id: int
    last_scraped: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class SourceWithStats(SourceResponse):
    """Schema for source data with statistics."""
    total_alerts: int = 0
    alerts_last_30_days: int = 0
    last_alert_date: Optional[datetime] = None