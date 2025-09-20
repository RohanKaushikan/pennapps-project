# Location Processing API

A comprehensive real-time location processing system that provides immediate alert generation, geofence monitoring, and emergency broadcast capabilities for travel applications.

## 🚀 Overview

The Location Processing API provides:
- **Real-time Country Entry Processing** - Immediate alerts when users cross borders
- **Geofence Trigger Handling** - Location-based notifications for predefined zones
- **Country Brief Generation** - Comprehensive entry information with caching
- **Emergency Alert Broadcasting** - Critical alerts targeted by location
- **Multi-channel Notifications** - Push, SMS, email, and WebSocket delivery
- **Performance Monitoring** - Real-time statistics and health checks

## 📋 Architecture

### System Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Mobile Apps    │    │  Location API    │    │  Government     │
│                 │◄──►│     Service      │◄──►│     APIs        │
│ • GPS Events    │    │                  │    │                 │
│ • Geofence      │    │ • Entry Process  │    │ • Travel Data   │
│ • Emergency     │    │ • Alert Gen      │    │ • Advisories    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │  Notification    │
                       │    Services      │
                       │                  │
                       │ • Push Notify    │
                       │ • SMS Alerts     │
                       │ • Email Updates  │
                       │ • WebSocket      │
                       └──────────────────┘
```

### Data Flow

1. **Location Event** → GPS coordinates and country detection
2. **Entry Processing** → Travel advisory lookup and analysis
3. **Alert Generation** → Risk-based alert creation
4. **Notification Routing** → Multi-channel delivery based on priority
5. **Tracking & Analytics** → Delivery confirmation and metrics

## 🛠️ API Endpoints

### 1. Process Country Entry

**POST** `/api/internal/process-entry`

Process user country entry and generate immediate alerts.

#### Request Body
```json
{
  "user_id": "user_12345",
  "device_id": "device_67890",
  "coordinates": {
    "latitude": 48.8566,
    "longitude": 2.3522,
    "accuracy_meters": 10.0
  },
  "country_code": "FRA",
  "country_name": "France",
  "previous_country_code": "GBR",
  "metadata": {
    "entry_method": "land_border",
    "transport": "car"
  }
}
```

#### Response
```json
{
  "success": true,
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "country": {
    "code": "FRA",
    "name": "France"
  },
  "alerts": [
    {
      "id": "alert_12345",
      "type": "travel_advisory",
      "severity": "medium",
      "title": "Travel Advisory: France",
      "message": "Exercise increased caution due to...",
      "country_code": "FRA",
      "source": "us_state_department"
    }
  ],
  "processing_time_ms": 245.7,
  "recommendations": [
    {
      "type": "check_requirements",
      "title": "Check Entry Requirements",
      "description": "Verify visa and passport requirements"
    }
  ]
}
```

#### Features
- **Immediate Processing** - Sub-second response times
- **Multi-source Advisories** - Aggregates from all government APIs
- **Contextual Alerts** - Risk-level based alert generation
- **Entry Recommendations** - Actionable guidance for travelers

### 2. Handle Geofence Triggers

**POST** `/api/internal/geofence-trigger`

Handle geofencing events from mobile applications.

#### Request Body
```json
{
  "user_id": "user_12345",
  "device_id": "device_67890",
  "coordinates": {
    "latitude": 48.8663,
    "longitude": 2.3131,
    "accuracy_meters": 5.0
  },
  "geofence_id": "us_embassy_paris_001",
  "event_type": "enter",
  "metadata": {
    "geofence_name": "US Embassy Paris"
  }
}
```

#### Response
```json
{
  "success": true,
  "event_id": "550e8400-e29b-41d4-a716-446655440001",
  "geofence": {
    "id": "us_embassy_paris_001",
    "name": "US Embassy Paris",
    "type": "embassy"
  },
  "event_type": "enter",
  "alerts": [
    {
      "id": "alert_12346",
      "type": "safety_warning",
      "severity": "medium",
      "title": "Entering US Embassy Paris",
      "message": "You are now near the US Embassy. Services available..."
    }
  ],
  "processing_time_ms": 89.3
}
```

#### Geofence Types
- **Border Crossings** - International boundary alerts
- **Embassy Locations** - Consular service notifications
- **Airport Perimeters** - Transit and departure alerts
- **High-risk Areas** - Security warnings
- **Tourist Zones** - Information and recommendations

### 3. Generate Country Brief

**GET** `/api/internal/country-brief/{country_code}`

Generate comprehensive country entry brief.

#### Parameters
- `country_code`: ISO 3166-1 alpha-3 country code
- `force_refresh`: Force regeneration (optional, default: false)

#### Response
```json
{
  "success": true,
  "cached": false,
  "country_code": "FRA",
  "brief": {
    "country_code": "FRA",
    "country_name": "France",
    "summary": "Current travel advisory level: Exercise Increased Caution",
    "travel_advisories": [
      {
        "source": "us_state_department",
        "risk_level": "Level 2 - Exercise Increased Caution",
        "risk_level_standardized": "EXERCISE_CAUTION",
        "content": "Exercise increased caution in France due to...",
        "last_updated": "2024-09-15T10:00:00Z"
      }
    ],
    "entry_requirements": {
      "visa_required": false,
      "passport_validity_months": 3,
      "vaccination_requirements": [],
      "customs_restrictions": ["No firearms", "Limited alcohol"]
    },
    "emergency_contacts": [
      {
        "type": "embassy",
        "name": "US Embassy Paris",
        "phone": "+33-1-43-12-22-22",
        "address": "2 Avenue Gabriel, 75008 Paris"
      }
    ],
    "sources": ["us_state_department", "uk_foreign_office"]
  },
  "generated_at": "2024-09-20T15:30:00Z",
  "processing_time_ms": 1247.5
}
```

#### Caching Strategy
- **6-hour Cache** - Balances freshness with performance
- **Force Refresh** - Option to bypass cache for urgent updates
- **Source Tracking** - Monitors data freshness per government API

### 4. Broadcast Emergency Alerts

**POST** `/api/internal/emergency-alerts`

Push critical alerts to users in specific locations.

#### Request Body
```json
{
  "title": "Weather Emergency: Severe Storm Warning",
  "message": "A severe storm system is approaching your area. Seek immediate shelter and avoid outdoor activities.",
  "severity": "high",
  "alert_type": "weather_warning",
  "target_countries": ["FRA", "DEU", "BEL"],
  "target_regions": ["Ile-de-France", "North Rhine-Westphalia"],
  "radius_km": 50.0,
  "expires_hours": 12,
  "issued_by": "European Weather Service"
}
```

#### Response
```json
{
  "success": true,
  "broadcast_id": "550e8400-e29b-41d4-a716-446655440002",
  "recipients": 1247,
  "target_countries": ["FRA", "DEU", "BEL"],
  "processing_time_ms": 892.4,
  "expires_at": "2024-09-21T03:30:00Z"
}
```

#### Alert Types
- **Emergency Alerts** - Natural disasters, security threats
- **Weather Warnings** - Severe weather conditions
- **Health Advisories** - Disease outbreaks, medical alerts
- **Safety Warnings** - Civil unrest, infrastructure issues
- **Travel Advisories** - Updated government recommendations

#### Targeting Options
- **Country-based** - Target all users in specific countries
- **Region-based** - Target specific states/provinces
- **Radius-based** - Circular geographic targeting
- **Combined Criteria** - Multiple targeting methods

## 🔧 Configuration

### Notification Channels

Configure notification delivery based on alert severity:

```python
# High-priority alerts use all channels
"critical": {
    "channels": ["push", "sms", "websocket", "email"],
    "retry_attempts": 3,
    "retry_delay": 5
}

# Medium-priority alerts use push and websocket
"medium": {
    "channels": ["push", "websocket"],
    "retry_attempts": 2,
    "retry_delay": 10
}
```

### Geofence Zones

Define geographic zones for location-based alerts:

```sql
INSERT INTO geofence_zones (
    name,
    center_latitude,
    center_longitude,
    radius_meters,
    country_code,
    zone_type,
    alert_template
) VALUES (
    'Charles de Gaulle Airport',
    49.0097,
    2.5479,
    2000,
    'FRA',
    'airport',
    '{"title": "Airport Area", "message": "Check departure times"}'
);
```

### Alert Thresholds

Configure when to generate alerts based on risk levels:

```python
RISK_MAPPING = {
    "AVOID_ALL_TRAVEL": "critical",
    "RECONSIDER_TRAVEL": "high",
    "EXERCISE_CAUTION": "medium",
    "NORMAL_PRECAUTIONS": "low"
}
```

## 📊 Monitoring and Analytics

### Health Check

**GET** `/api/internal/health`

```json
{
  "status": "healthy",
  "timestamp": "2024-09-20T15:30:00Z",
  "services": {
    "database": true,
    "us_state_department": true,
    "uk_foreign_office": true
  },
  "processing_stats": {
    "time_period_hours": 24,
    "total_events": 1247,
    "country_entries": 892,
    "geofence_triggers": 355,
    "alerts_generated": 234,
    "average_processing_time_ms": 187.5,
    "error_rate": 1.2
  }
}
```

### Processing Statistics

**GET** `/api/internal/stats?hours=24`

```json
{
  "time_period_hours": 24,
  "total_events": 1247,
  "country_entries": 892,
  "geofence_triggers": 355,
  "alerts_generated": 234,
  "average_processing_time_ms": 187.5,
  "error_rate": 1.2
}
```

## 🚀 Quick Start

### 1. Setup and Dependencies

```bash
# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start Redis for caching
redis-server

# Start the API server
uvicorn app.main:app --reload
```

### 2. Basic Usage

```python
import httpx

async def process_country_entry():
    async with httpx.AsyncClient() as client:
        response = await client.post("http://localhost:8000/api/internal/process-entry", json={
            "user_id": "user_123",
            "coordinates": {"latitude": 48.8566, "longitude": 2.3522},
            "country_code": "FRA",
            "country_name": "France"
        })

        result = response.json()
        print(f"Processed entry: {result['success']}")
        print(f"Alerts generated: {len(result['alerts'])}")
```

### 3. Mobile App Integration

```javascript
// React Native example
const processCountryEntry = async (location, country) => {
  try {
    const response = await fetch('https://api.travelapp.com/api/internal/process-entry', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        user_id: userId,
        device_id: deviceId,
        coordinates: {
          latitude: location.coords.latitude,
          longitude: location.coords.longitude,
          accuracy_meters: location.coords.accuracy
        },
        country_code: country.code,
        country_name: country.name
      })
    });

    const result = await response.json();

    // Show alerts to user
    result.alerts.forEach(alert => {
      showNotification(alert.title, alert.message, alert.severity);
    });

  } catch (error) {
    console.error('Entry processing failed:', error);
  }
};
```

## 🔐 Security Considerations

### Authentication
- API endpoints require valid authentication tokens
- Rate limiting prevents abuse and ensures fair usage
- Request validation prevents malicious payloads

### Data Privacy
- Location data is processed but not permanently stored beyond operational needs
- User identifiers are hashed for analytics
- Sensitive information is encrypted in transit and at rest

### Error Handling
- Graceful degradation when external APIs are unavailable
- Retry logic with exponential backoff
- Circuit breaker pattern prevents cascade failures

## 🛡️ Error Handling

### Common Error Responses

```json
{
  "detail": "Country code must be 2 or 3 characters",
  "status_code": 400
}
```

```json
{
  "detail": "Failed to process country entry: API timeout",
  "status_code": 500
}
```

### Error Types
- **400 Bad Request** - Invalid input parameters
- **404 Not Found** - Resource not found (geofence, country)
- **429 Too Many Requests** - Rate limit exceeded
- **500 Internal Server Error** - Processing failures
- **503 Service Unavailable** - External API unavailable

## 📈 Performance Optimization

### Caching Strategy
- **Response Caching** - Cache API responses for 1-6 hours
- **Country Briefs** - Cache comprehensive briefs for 6 hours
- **Geofence Lookups** - In-memory caching for faster checks

### Concurrency
- **Async Processing** - Non-blocking I/O for all operations
- **Concurrent API Calls** - Multiple government APIs called simultaneously
- **Background Tasks** - Long-running operations moved to background

### Monitoring
- **Response Time Tracking** - P50, P90, P95, P99 percentiles
- **Error Rate Monitoring** - Alert when error rate exceeds thresholds
- **Throughput Metrics** - Requests per second and concurrent users

## 🤝 Integration Examples

### Tourism App Integration
```python
# When user crosses border
await process_country_entry(user_location, destination_country)

# Set up geofences for points of interest
await create_geofence("louvre_museum", paris_coords, 100)

# Send alerts for events
await broadcast_emergency_alert("Museum closure", target_countries=["FRA"])
```

### Corporate Travel Integration
```python
# Employee travel tracking
await process_country_entry(employee_id, business_trip_destination)

# Generate travel briefs for managers
brief = await get_country_brief("CHN", force_refresh=True)

# Emergency communications
await broadcast_emergency_alert("Company evacuation", target_employees)
```

---

For more examples and advanced configuration, see the example scripts in the `/scripts` directory.