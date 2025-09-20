from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class MessageResponse(BaseModel):
    """Standard message response schema."""
    message: str
    success: bool = True


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response schema."""
    items: List[T]
    total: int
    page: int = Field(ge=1, description="Current page number")
    per_page: int = Field(ge=1, le=100, description="Items per page")
    pages: int = Field(ge=1, description="Total number of pages")
    has_next: bool
    has_prev: bool

    class Config:
        from_attributes = True


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    class Config:
        from_attributes = True
        validate_assignment = True
        arbitrary_types_allowed = True