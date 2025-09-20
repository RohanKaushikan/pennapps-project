from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, ForeignKey, DateTime, String, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class UserCountryEntry(Base):
    """Track when users enter new countries for reactive alerting."""
    __tablename__ = "user_country_entries"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    country_code: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        index=True,
        comment="ISO 3166-1 alpha-2 country code"
    )

    entry_latitude: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="GPS latitude when entering country"
    )

    entry_longitude: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="GPS longitude when entering country"
    )

    entry_accuracy: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="GPS accuracy in meters"
    )

    entry_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="When user entered the country"
    )

    alerts_sent: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether alerts have been sent for this entry"
    )

    alerts_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When alerts were sent"
    )

    exit_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="When user left the country (if tracked)"
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="country_entries"
    )

    def __repr__(self) -> str:
        return f"<UserCountryEntry(id={self.id}, user_id={self.user_id}, country={self.country_code}, entered={self.entry_timestamp})>"
