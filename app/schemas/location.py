from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator
from .common import BaseSchema


class LocationRequest(BaseSchema):
    """Schema for location-based requests."""
    latitude: Optional[float] = Field(
        None,
        ge=-90,
        le=90,
        description="Latitude coordinate"
    )
    longitude: Optional[float] = Field(
        None,
        ge=-180,
        le=180,
        description="Longitude coordinate"
    )
    country_code: Optional[str] = Field(
        None,
        min_length=2,
        max_length=2,
        description="ISO 2-letter country code"
    )
    accuracy: Optional[float] = Field(
        None,
        ge=0,
        description="Location accuracy in meters"
    )

    @validator("country_code")
    def validate_country_code(cls, v):
        if v:
            return v.upper()
        return v

    @validator("latitude", "longitude")
    def coordinates_together(cls, v, values):
        # If latitude is provided, longitude must also be provided
        if 'latitude' in values and values['latitude'] is not None:
            if v is None:
                raise ValueError("Both latitude and longitude must be provided together")
        return v

    def validate_input(self):
        """Validate that either coordinates OR country_code is provided."""
        has_coordinates = self.latitude is not None and self.longitude is not None
        has_country_code = self.country_code is not None

        if not has_coordinates and not has_country_code:
            raise ValueError("Either coordinates (lat/lng) or country_code must be provided")

        return True


class UserLocationUpdate(BaseSchema):
    """Schema for updating user location."""
    user_id: int = Field(..., gt=0)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy: Optional[float] = Field(None, ge=0)
    timestamp: Optional[datetime] = None


class CountryDetection(BaseSchema):
    """Schema for country detection results."""
    country_code: Optional[str] = None
    country_name: Optional[str] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    is_border_region: bool = False
    distance_to_border: Optional[float] = None


class LocationAlertResponse(BaseSchema):
    """Schema for location-triggered alert responses."""
    country_detection: CountryDetection
    triggered_alerts: List[dict] = []
    alert_count: int = 0
    highest_risk_level: int = 0
    processing_timestamp: datetime
    recommendations: List[str] = []


class ImmediateAlertResponse(BaseSchema):
    """Schema for immediate alert responses."""
    country_code: str
    country_name: str
    critical_alerts: List[dict] = []
    alert_count: int = 0
    risk_assessment: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    immediate_actions: List[str] = []
    generated_at: datetime


class EntryBriefResponse(BaseSchema):
    """Schema for country entry brief responses."""
    country: dict
    generated_at: datetime
    summary: dict
    immediate_actions: List[str] = []
    key_alerts: dict = {}
    quick_tips: List[str] = []
    emergency_info: dict = {}


class LocationProcessingResponse(BaseSchema):
    """Schema for user location processing responses."""
    user_id: int
    location_updated: bool
    country_detected: Optional[CountryDetection] = None
    alerts_triggered: int = 0
    notifications_sent: int = 0
    processing_timestamp: datetime
    next_check_recommended: Optional[datetime] = None


class AlertSummary(BaseSchema):
    """Simplified alert summary for location responses."""
    id: int
    title: str
    risk_level: int
    categories: List[str] = []
    expires_at: Optional[datetime] = None
    created_at: datetime


class EmergencyContact(BaseSchema):
    """Emergency contact information."""
    type: str  # embassy, emergency, medical
    name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    hours: Optional[str] = None


class CountryQuickInfo(BaseSchema):
    """Quick country information for travelers."""
    country_code: str
    country_name: str
    currency: Optional[str] = None
    emergency_number: Optional[str] = None
    time_zone: Optional[str] = None
    language: Optional[str] = None
    driving_side: Optional[str] = None  # left, right


class GeofenceEvent(BaseSchema):
    """Schema for geofence events."""
    event_type: str  # entry, exit, proximity
    country_code: str
    timestamp: datetime
    confidence: float
    trigger_distance: Optional[float] = None


class LocationAnalytics(BaseSchema):
    """Schema for location analytics."""
    total_location_updates: int = 0
    countries_detected: int = 0
    alerts_triggered: int = 0
    border_crossings: int = 0
    average_response_time: float = 0.0
    last_update: Optional[datetime] = None