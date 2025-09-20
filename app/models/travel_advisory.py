from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base
import uuid


class TravelAdvisory(Base):
    __tablename__ = "travel_advisories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(String(2048), nullable=False)
    source = Column(String(100), nullable=False)  # 'us_state_dept', 'uk_foreign_office', 'canada_travel'
    country = Column(String(100), nullable=False)
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)
    risk_level = Column(String(200), nullable=True)
    last_updated_source = Column(String(100), nullable=True)  # Date from the source website
    advisory_metadata = Column(JSON, nullable=True)

    # Timestamps
    scraped_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Status fields
    is_active = Column(Boolean, default=True)
    content_changed = Column(Boolean, default=False)

    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_travel_advisories_country_source', 'country', 'source'),
        Index('idx_travel_advisories_content_hash', 'content_hash'),
        Index('idx_travel_advisories_scraped_at', 'scraped_at'),
        Index('idx_travel_advisories_risk_level', 'risk_level'),
        Index('idx_travel_advisories_url', 'url'),
    )

    def __repr__(self):
        return f"<TravelAdvisory(country='{self.country}', source='{self.source}', risk_level='{self.risk_level}')>"


class ScrapingLog(Base):
    __tablename__ = "scraping_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String(100), nullable=False)
    scraping_session_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(String(50), nullable=False)  # 'started', 'completed', 'failed', 'partial'
    total_countries = Column(Integer, nullable=True)
    successful_scrapes = Column(Integer, nullable=True)
    failed_scrapes = Column(Integer, nullable=True)
    new_content_count = Column(Integer, nullable=True)
    updated_content_count = Column(Integer, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    advisory_metadata = Column(JSON, nullable=True)

    # Timestamps
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_scraping_logs_source', 'source'),
        Index('idx_scraping_logs_session_id', 'scraping_session_id'),
        Index('idx_scraping_logs_started_at', 'started_at'),
        Index('idx_scraping_logs_status', 'status'),
    )

    def __repr__(self):
        return f"<ScrapingLog(source='{self.source}', status='{self.status}', started_at='{self.started_at}')>"


class ContentChangeEvent(Base):
    __tablename__ = "content_change_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    advisory_id = Column(UUID(as_uuid=True), nullable=False)
    change_type = Column(String(50), nullable=False)  # 'new', 'updated', 'deleted', 'risk_level_changed'
    previous_hash = Column(String(64), nullable=True)
    new_hash = Column(String(64), nullable=True)
    previous_risk_level = Column(String(200), nullable=True)
    new_risk_level = Column(String(200), nullable=True)
    change_summary = Column(Text, nullable=True)
    advisory_metadata = Column(JSON, nullable=True)

    # Timestamps
    detected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_content_change_events_advisory_id', 'advisory_id'),
        Index('idx_content_change_events_change_type', 'change_type'),
        Index('idx_content_change_events_detected_at', 'detected_at'),
    )

    def __repr__(self):
        return f"<ContentChangeEvent(advisory_id='{self.advisory_id}', change_type='{self.change_type}', detected_at='{self.detected_at}')>"