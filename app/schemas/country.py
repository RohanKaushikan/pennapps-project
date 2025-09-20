from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator
from .common import BaseSchema


class CountryBase(BaseSchema):
    """Base country schema with common fields."""
    code: str = Field(
        ...,
        min_length=2,
        max_length=2,
        pattern="^[A-Z]{2}$",
        description="ISO 3166-1 alpha-2 country code"
    )
    name: str = Field(..., min_length=1, max_length=100)
    region: str = Field(..., min_length=1, max_length=100)

    @validator("code")
    def validate_country_code(cls, v):
        return v.upper()


class CountryCreate(CountryBase):
    """Schema for creating a new country."""
    pass


class CountryUpdate(BaseSchema):
    """Schema for updating country information."""
    code: Optional[str] = Field(
        None,
        min_length=2,
        max_length=2,
        pattern="^[A-Z]{2}$"
    )
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    region: Optional[str] = Field(None, min_length=1, max_length=100)

    @validator("code")
    def validate_country_code(cls, v):
        if v:
            return v.upper()
        return v


class CountryInDB(CountryBase):
    """Schema for country data in database."""
    id: int
    created_at: datetime
    updated_at: datetime


class CountryResponse(CountryBase):
    """Schema for country data in API responses."""
    id: int
    created_at: datetime
    updated_at: datetime


class CountryWithStats(CountryResponse):
    """Schema for country data with statistics."""
    total_alerts: int = 0
    active_alerts: int = 0
    high_risk_alerts: int = 0
    last_alert_date: Optional[datetime] = None