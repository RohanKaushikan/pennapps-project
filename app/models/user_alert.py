from typing import Optional
from sqlalchemy import Boolean, ForeignKey, DateTime, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class UserAlert(Base):
    __tablename__ = "user_alerts"

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

    alert_id: Mapped[int] = mapped_column(
        ForeignKey("alerts.id"),
        nullable=False,
        index=True
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )

    notified_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="When the user was notified about this alert"
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="user_alerts"
    )

    alert: Mapped["Alert"] = relationship(
        "Alert",
        back_populates="user_alerts"
    )

    # Table constraints
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "alert_id",
            name="uq_user_alert"
        ),
    )

    def __repr__(self) -> str:
        return f"<UserAlert(user_id={self.user_id}, alert_id={self.alert_id}, is_read={self.is_read})>"