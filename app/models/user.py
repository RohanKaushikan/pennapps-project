from typing import List, Optional
from sqlalchemy import String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSON
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )

    travel_preferences: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="JSON field storing user travel preferences like preferred countries, notification settings, etc."
    )

    # Relationships
    country_entries: Mapped[List["UserCountryEntry"]] = relationship(
        "UserCountryEntry",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"