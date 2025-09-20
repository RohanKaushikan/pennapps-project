from typing import List
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Country(Base):
    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    code: Mapped[str] = mapped_column(
        String(2),
        unique=True,
        nullable=False,
        index=True,
        comment="ISO 3166-1 alpha-2 country code"
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )

    region: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Geographic region (e.g., Europe, Asia, North America)"
    )

    # Relationships
    sources: Mapped[List["Source"]] = relationship(
        "Source",
        back_populates="country",
        cascade="all, delete-orphan"
    )

    alerts: Mapped[List["Alert"]] = relationship(
        "Alert",
        back_populates="country",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Country(id={self.id}, code={self.code}, name={self.name})>"