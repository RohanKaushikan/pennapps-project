from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from .common import BaseSchema


class UserBase(BaseSchema):
    """Base user schema with common fields."""
    email: EmailStr
    travel_preferences: Optional[dict] = Field(
        None,
        description="JSON object containing user travel preferences"
    )


class UserCreate(UserBase):
    """Schema for creating a new user."""
    pass


class UserUpdate(BaseSchema):
    """Schema for updating user information."""
    email: Optional[EmailStr] = None
    travel_preferences: Optional[dict] = None


class UserInDB(UserBase):
    """Schema for user data in database."""
    id: int
    created_at: datetime
    updated_at: datetime


class UserResponse(UserBase):
    """Schema for user data in API responses."""
    id: int
    created_at: datetime
    updated_at: datetime