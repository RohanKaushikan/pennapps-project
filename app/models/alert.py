from typing import List, Optional
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ARRAY
from app.core.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    country_id: Mapped[int] = mapped_column(
        ForeignKey("countries.id"),
        nullable=False,
        index=True
    )

    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id"),
        nullable=False,
        index=True
    )

    risk_level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Risk level from 1 (low) to 5 (critical)"
    )

    expires_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="When this alert expires and becomes inactive"
    )

    categories: Mapped[List[str]] = mapped_column(
        ARRAY(String(50)),
        nullable=False,
        default=[],
        comment="Array of categories like visa, legal, safety, health"
    )

    raw_content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Original content from the source before processing"
    )

    # Relationships
    country: Mapped["Country"] = relationship(
        "Country",
        back_populates="alerts"
    )

    source: Mapped["Source"] = relationship(
        "Source",
        back_populates="alerts"
    )

    user_alerts: Mapped[List["UserAlert"]] = relationship(
        "UserAlert",
        back_populates="alert",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Alert(id={self.id}, title={self.title[:50]}..., risk_level={self.risk_level})>"