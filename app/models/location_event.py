import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import Column, String, Float, DateTime, Text, JSON, Enum as SQLEnum, Boolean, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

from app.core.database import Base


class LocationEventType(str, Enum):
    """Types of location events."""
    COUNTRY_ENTRY = "country_entry"
    COUNTRY_EXIT = "country_exit"
    GEOFENCE_ENTER = "geofence_enter"
    GEOFENCE_EXIT = "geofence_exit"
    EMERGENCY_AREA = "emergency_area"
    BORDER_CROSSING = "border_crossing"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Types of alerts."""
    TRAVEL_ADVISORY = "travel_advisory"
    SAFETY_WARNING = "safety_warning"
    EMERGENCY_ALERT = "emergency_alert"
    ENTRY_REQUIREMENTS = "entry_requirements"
    HEALTH_ADVISORY = "health_advisory"
    WEATHER_WARNING = "weather_warning"


class LocationEvent(Base):
    """Model for tracking location events and user movements."""
    __tablename__ = "location_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    device_id = Column(String(255), nullable=True, index=True)
    event_type = Column(SQLEnum(LocationEventType), nullable=False)

    # Location data
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy_meters = Column(Float, nullable=True)
    altitude = Column(Float, nullable=True)

    # Geographic information
    country_code = Column(String(3), nullable=False, index=True)
    country_name = Column(String(255), nullable=False)
    region = Column(String(255), nullable=True)
    city = Column(String(255), nullable=True)

    # Previous location (for transitions)
    previous_country_code = Column(String(3), nullable=True)
    previous_country_name = Column(String(255), nullable=True)

    # Event metadata
    timestamp = Column(DateTime(timezone=True), nullable=False, default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    processing_time_ms = Column(Float, nullable=True)

    # Additional data
    event_metadata = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class LocationAlert(Base):
    """Model for location-triggered alerts."""
    __tablename__ = "location_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    location_event_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)

    # Alert details
    alert_type = Column(SQLEnum(AlertType), nullable=False)
    severity = Column(SQLEnum(AlertSeverity), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    # Location context
    country_code = Column(String(3), nullable=False, index=True)
    country_name = Column(String(255), nullable=False)
    location_data = Column(JSON, nullable=True)

    # Alert metadata
    source = Column(String(100), nullable=False)  # us_state_department, uk_foreign_office, etc.
    risk_level = Column(String(50), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Delivery tracking
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    dismissed_at = Column(DateTime(timezone=True), nullable=True)

    # Alert data
    advisory_data = Column(JSON, nullable=True)
    actions_required = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class GeofenceZone(Base):
    """Model for predefined geofence zones."""
    __tablename__ = "geofence_zones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Geographic boundaries
    center_latitude = Column(Float, nullable=False)
    center_longitude = Column(Float, nullable=False)
    radius_meters = Column(Float, nullable=False)

    # Zone configuration
    country_code = Column(String(3), nullable=False, index=True)
    zone_type = Column(String(100), nullable=False)  # border, airport, embassy, danger_zone, etc.
    is_active = Column(Boolean, default=True)

    # Alert configuration
    entry_alert_enabled = Column(Boolean, default=True)
    exit_alert_enabled = Column(Boolean, default=False)
    alert_template = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class CountryBrief(Base):
    """Model for storing generated country briefs."""
    __tablename__ = "country_briefs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country_code = Column(String(3), nullable=False, index=True)
    country_name = Column(String(255), nullable=False)

    # Brief content
    brief_data = Column(JSON, nullable=False)
    summary = Column(Text, nullable=False)

    # Generation metadata
    generated_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    data_sources = Column(JSON, nullable=True)  # Sources used to generate brief
    version = Column(String(50), nullable=False, default="1.0")

    # Validity
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_current = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class EmergencyBroadcast(Base):
    """Model for emergency broadcast alerts."""
    __tablename__ = "emergency_broadcasts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Broadcast details
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(SQLEnum(AlertSeverity), nullable=False)
    alert_type = Column(SQLEnum(AlertType), nullable=False)

    # Targeting
    target_countries = Column(JSON, nullable=False)  # List of country codes
    target_regions = Column(JSON, nullable=True)  # Optional regions within countries
    radius_km = Column(Float, nullable=True)  # Optional radius for location-based targeting

    # Broadcast metadata
    issued_by = Column(String(255), nullable=False)  # Authority issuing the alert
    source_reference = Column(String(255), nullable=True)  # External reference ID

    # Timing
    issued_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Delivery tracking
    total_recipients = Column(Float, default=0)
    delivered_count = Column(Float, default=0)
    read_count = Column(Float, default=0)

    # Status
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())