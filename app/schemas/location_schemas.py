from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator
from enum import Enum

from app.models.location_event import LocationEventType, AlertSeverity, AlertType


class LocationCoordinates(BaseModel):
    """Schema for geographic coordinates."""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")
    accuracy_meters: Optional[float] = Field(None, ge=0, description="GPS accuracy in meters")
    altitude: Optional[float] = Field(None, description="Altitude in meters")


class CountryEntryRequest(BaseModel):
    """Schema for country entry processing request."""
    user_id: str = Field(..., min_length=1, description="User identifier")
    device_id: Optional[str] = Field(None, description="Device identifier")
    coordinates: LocationCoordinates
    country_code: str = Field(..., min_length=2, max_length=3, description="ISO country code")
    country_name: str = Field(..., min_length=1, description="Full country name")
    previous_country_code: Optional[str] = Field(None, max_length=3, description="Previous country code")
    timestamp: Optional[datetime] = Field(None, description="Event timestamp (defaults to now)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional event metadata")

    @validator('country_code', 'previous_country_code')
    def validate_country_code(cls, v):
        if v and len(v) not in [2, 3]:
            raise ValueError('Country code must be 2 or 3 characters')
        return v.upper() if v else v


class GeofenceTriggerRequest(BaseModel):
    """Schema for geofence trigger request."""
    user_id: str = Field(..., min_length=1, description="User identifier")
    device_id: Optional[str] = Field(None, description="Device identifier")
    coordinates: LocationCoordinates
    geofence_id: str = Field(..., description="Geofence zone identifier")
    event_type: str = Field(..., description="Trigger type: 'enter' or 'exit'")
    timestamp: Optional[datetime] = Field(None, description="Event timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional event metadata")

    @validator('event_type')
    def validate_event_type(cls, v):
        if v.lower() not in ['enter', 'exit']:
            raise ValueError('Event type must be "enter" or "exit"')
        return v.lower()


class EmergencyAlertRequest(BaseModel):
    """Schema for emergency alert broadcast request."""
    title: str = Field(..., min_length=1, max_length=255, description="Alert title")
    message: str = Field(..., min_length=1, description="Alert message")
    severity: AlertSeverity = Field(..., description="Alert severity level")
    alert_type: AlertType = Field(AlertType.EMERGENCY_ALERT, description="Alert type")
    target_countries: List[str] = Field(..., min_items=1, description="Target country codes")
    target_regions: Optional[List[str]] = Field(None, description="Target regions (optional)")
    radius_km: Optional[float] = Field(None, ge=0, description="Alert radius in kilometers")
    expires_hours: int = Field(24, ge=1, le=168, description="Hours until alert expires")
    issued_by: str = Field("System", description="Authority issuing the alert")

    @validator('target_countries')
    def validate_country_codes(cls, v):
        return [code.upper() for code in v]


class AlertResponse(BaseModel):
    """Schema for alert response."""
    id: str = Field(..., description="Alert identifier")
    type: str = Field(..., description="Alert type")
    severity: str = Field(..., description="Alert severity")
    title: str = Field(..., description="Alert title")
    message: str = Field(..., description="Alert message")
    country_code: str = Field(..., description="Country code")
    source: str = Field(..., description="Alert source")
    created_at: Optional[str] = Field(None, description="Creation timestamp")


class CountryEntryResponse(BaseModel):
    """Schema for country entry processing response."""
    success: bool = Field(..., description="Processing success status")
    event_id: Optional[str] = Field(None, description="Location event identifier")
    country: Optional[Dict[str, str]] = Field(None, description="Country information")
    alerts: List[AlertResponse] = Field([], description="Generated alerts")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    recommendations: List[Dict[str, Any]] = Field([], description="Entry recommendations")
    error: Optional[str] = Field(None, description="Error message if processing failed")


class GeofenceTriggerResponse(BaseModel):
    """Schema for geofence trigger response."""
    success: bool = Field(..., description="Processing success status")
    event_id: Optional[str] = Field(None, description="Location event identifier")
    geofence: Optional[Dict[str, str]] = Field(None, description="Geofence information")
    event_type: Optional[str] = Field(None, description="Trigger event type")
    alerts: List[AlertResponse] = Field([], description="Triggered alerts")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    error: Optional[str] = Field(None, description="Error message if processing failed")


class TravelAdvisoryInfo(BaseModel):
    """Schema for travel advisory information."""
    source: str = Field(..., description="Advisory source")
    risk_level: Optional[str] = Field(None, description="Original risk level")
    risk_level_standardized: Optional[str] = Field(None, description="Standardized risk level")
    content: Optional[str] = Field(None, description="Advisory content")
    last_updated: Optional[str] = Field(None, description="Last update timestamp")


class EmergencyContactInfo(BaseModel):
    """Schema for emergency contact information."""
    type: str = Field(..., description="Contact type (embassy, police, medical)")
    name: str = Field(..., description="Contact name")
    phone: Optional[str] = Field(None, description="Phone number")
    address: Optional[str] = Field(None, description="Address")
    hours: Optional[str] = Field(None, description="Operating hours")


class EntryRequirementInfo(BaseModel):
    """Schema for entry requirement information."""
    visa_required: Optional[bool] = Field(None, description="Visa requirement status")
    passport_validity_months: Optional[int] = Field(None, description="Required passport validity")
    vaccination_requirements: List[str] = Field([], description="Required vaccinations")
    customs_restrictions: List[str] = Field([], description="Customs restrictions")
    currency_restrictions: Optional[str] = Field(None, description="Currency restrictions")


class CountryBriefData(BaseModel):
    """Schema for comprehensive country brief data."""
    country_code: str = Field(..., description="ISO country code")
    country_name: str = Field(..., description="Full country name")
    summary: str = Field(..., description="Brief summary")
    travel_advisories: List[TravelAdvisoryInfo] = Field([], description="Travel advisories")
    entry_requirements: EntryRequirementInfo = Field(..., description="Entry requirements")
    emergency_contacts: List[EmergencyContactInfo] = Field([], description="Emergency contacts")
    health_info: Dict[str, Any] = Field({}, description="Health and medical information")
    sources: List[str] = Field([], description="Data sources used")


class CountryBriefResponse(BaseModel):
    """Schema for country brief response."""
    success: bool = Field(..., description="Generation success status")
    cached: bool = Field(..., description="Whether response was cached")
    country_code: str = Field(..., description="ISO country code")
    brief: Optional[CountryBriefData] = Field(None, description="Country brief data")
    summary: Optional[str] = Field(None, description="Brief summary")
    generated_at: Optional[str] = Field(None, description="Generation timestamp")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    error: Optional[str] = Field(None, description="Error message if generation failed")


class EmergencyAlertResponse(BaseModel):
    """Schema for emergency alert broadcast response."""
    success: bool = Field(..., description="Broadcast success status")
    broadcast_id: Optional[str] = Field(None, description="Broadcast identifier")
    recipients: int = Field(0, description="Number of recipients")
    target_countries: List[str] = Field([], description="Target countries")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    expires_at: Optional[str] = Field(None, description="Alert expiration timestamp")
    error: Optional[str] = Field(None, description="Error message if broadcast failed")


class NotificationDeliveryResult(BaseModel):
    """Schema for notification delivery result."""
    success: bool = Field(..., description="Delivery success status")
    alert_id: str = Field(..., description="Alert identifier")
    channels_attempted: List[str] = Field([], description="Notification channels attempted")
    channels_successful: List[str] = Field([], description="Successful notification channels")
    delivery_results: Dict[str, bool] = Field({}, description="Per-channel delivery results")
    emergency: bool = Field(False, description="Whether this was an emergency notification")
    error: Optional[str] = Field(None, description="Error message if delivery failed")


class LocationEventInfo(BaseModel):
    """Schema for location event information."""
    id: str = Field(..., description="Event identifier")
    user_id: str = Field(..., description="User identifier")
    event_type: LocationEventType = Field(..., description="Event type")
    coordinates: LocationCoordinates = Field(..., description="Event coordinates")
    country_code: str = Field(..., description="Country code")
    country_name: str = Field(..., description="Country name")
    timestamp: datetime = Field(..., description="Event timestamp")
    processed_at: Optional[datetime] = Field(None, description="Processing timestamp")
    processing_time_ms: Optional[float] = Field(None, description="Processing time")


class GeofenceZoneInfo(BaseModel):
    """Schema for geofence zone information."""
    id: str = Field(..., description="Zone identifier")
    name: str = Field(..., description="Zone name")
    description: Optional[str] = Field(None, description="Zone description")
    center_coordinates: LocationCoordinates = Field(..., description="Zone center coordinates")
    radius_meters: float = Field(..., description="Zone radius in meters")
    country_code: str = Field(..., description="Country code")
    zone_type: str = Field(..., description="Zone type")
    is_active: bool = Field(..., description="Zone active status")
    entry_alert_enabled: bool = Field(..., description="Entry alert enabled")
    exit_alert_enabled: bool = Field(..., description="Exit alert enabled")


class LocationProcessingStats(BaseModel):
    """Schema for location processing statistics."""
    time_period_hours: int = Field(..., description="Statistics time period")
    total_events: int = Field(..., description="Total location events")
    country_entries: int = Field(..., description="Country entry events")
    geofence_triggers: int = Field(..., description="Geofence trigger events")
    alerts_generated: int = Field(..., description="Total alerts generated")
    average_processing_time_ms: float = Field(..., description="Average processing time")
    error_rate: float = Field(..., description="Error rate percentage")


class HealthCheckResponse(BaseModel):
    """Schema for health check response."""
    status: str = Field(..., description="Service health status")
    timestamp: datetime = Field(..., description="Check timestamp")
    services: Dict[str, bool] = Field(..., description="Individual service status")
    processing_stats: LocationProcessingStats = Field(..., description="Processing statistics")
    version: str = Field("1.0", description="API version")