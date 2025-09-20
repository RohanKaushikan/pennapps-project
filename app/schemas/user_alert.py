from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from .common import BaseSchema


class UserAlertBase(BaseSchema):
    """Base user alert schema with common fields."""
    user_id: int = Field(..., gt=0)
    alert_id: int = Field(..., gt=0)
    is_read: bool = False
    notified_at: Optional[datetime] = Field(
        None,
        description="When the user was notified about this alert"
    )


class UserAlertCreate(UserAlertBase):
    """Schema for creating a new user alert."""
    pass


class UserAlertUpdate(BaseSchema):
    """Schema for updating user alert information."""
    is_read: Optional[bool] = None
    notified_at: Optional[datetime] = None


class UserAlertInDB(UserAlertBase):
    """Schema for user alert data in database."""
    id: int
    created_at: datetime
    updated_at: datetime


class UserAlertResponse(UserAlertBase):
    """Schema for user alert data in API responses."""
    id: int
    created_at: datetime
    updated_at: datetime


class UserAlertWithRelations(UserAlertResponse):
    """Schema for user alert data with related entities."""
    user: Optional[dict] = None    # UserResponse
    alert: Optional[dict] = None   # AlertResponse