# Government API Integration System

A comprehensive system for integrating with official government travel advisory APIs, providing unified data access, caching, monitoring, and error handling.

## 🚀 Overview

The API integration system provides:
- **Unified Interface** - Single API to access multiple government sources
- **Data Normalization** - Standardized format across different APIs
- **Redis Caching** - High-performance caching with configurable TTL
- **Circuit Breaker** - Fault tolerance and automatic recovery
- **Rate Limiting** - Respectful API usage with per-source limits
- **Comprehensive Monitoring** - Performance metrics and health checks
- **Retry Logic** - Automatic retry with exponential backoff

## 📋 Architecture

### Components Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Client Apps    │    │  Unified API     │    │  Government     │
│                 │◄──►│    Service       │◄──►│     APIs        │
│ • Web App       │    │                  │    │                 │
│ • Scheduler     │    │ • Normalization  │    │ • US State Dept │
│ • CLI Tools     │    │ • Caching        │    │ • UK Foreign    │
│                 │    │ • Monitoring     │    │ • Canada Travel │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │  Redis Cache +   │
                       │   Monitoring     │
                       │                  │
                       │ • Response Cache │
                       │ • Rate Limits    │
                       │ • Metrics Store  │
                       │ • Health Status  │
                       └──────────────────┘
```

### Data Flow

1. **Request** → Unified API Service
2. **Cache Check** → Redis (if enabled)
3. **Rate Limiting** → Per-source validation
4. **API Call** → Government endpoint (with circuit breaker)
5. **Normalization** → Standardized data format
6. **Caching** → Store response in Redis
7. **Monitoring** → Record metrics and performance
8. **Response** → Normalized data to client

## 🛠️ Setup and Configuration

### Installation

1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

2. **Redis Setup**
```bash
# Install Redis
brew install redis  # macOS
sudo apt install redis-server  # Ubuntu

# Start Redis
redis-server
```

3. **Environment Configuration**
```bash
# Set in your environment or .env file
export REDIS_URL="redis://localhost:6379/0"
export US_STATE_DEPT_API_KEY="your_api_key"  # Optional
export UK_FOREIGN_OFFICE_API_KEY="your_api_key"  # Optional
```

## 🚀 Quick Start

### Basic Usage

```python
from app.api_clients.unified_api_service import UnifiedAPIService

# Initialize the service
api_service = UnifiedAPIService(redis_url="redis://localhost:6379/0")
await api_service.initialize_clients()

# Get travel advisories for a specific country
response = await api_service.get_country_advisory("France")

# Get all available advisories
response = await api_service.get_travel_advisories()

# Close connections
await api_service.close()
```

### CLI Usage

```bash
# Query APIs
python -m app.cli.api_cli query --country france

# Check API health
python -m app.cli.api_cli health

# View performance metrics
python -m app.cli.api_cli metrics

# Compare sources for a country
python -m app.cli.api_cli country japan --compare

# Generate performance report
python -m app.cli.api_cli report --hours 24
```

## 🌐 Supported APIs

### US State Department

- **Endpoint**: `https://travel.state.gov`
- **Format**: HTML/JSON (varies by endpoint)
- **Risk Levels**: 1-4 scale (Normal → Do Not Travel)
- **Rate Limit**: 60 requests/hour (default)
- **Authentication**: API key (optional)

```python
from app.api_clients.us_state_dept_client import USStateDeptAPIClient

client = USStateDeptAPIClient(api_key="your_key")
advisory = await client.get_country_advisory("France")
```

### UK Foreign Office

- **Endpoint**: `https://www.gov.uk`
- **Format**: JSON via GOV.UK API
- **Risk Levels**: Textual advisories (Advise Against All Travel, etc.)
- **Rate Limit**: 120 requests/hour (default)
- **Authentication**: API key (optional)

```python
from app.api_clients.uk_foreign_office_client import UKForeignOfficeAPIClient

client = UKForeignOfficeAPIClient(api_key="your_key")
advisory = await client.get_country_advisory("Germany")
```

## 📊 Data Normalization

### Standardized Format

All APIs return data in a unified format:

```python
{
    'source': 'us_state_department',
    'country': 'France',
    'title': 'France Travel Advisory',
    'content': 'Exercise increased caution...',
    'risk_level': 'Level 2 - Exercise Increased Caution',
    'risk_level_standardized': 'EXERCISE_CAUTION',
    'last_updated': '2024-09-20T10:00:00Z',
    'source_url': 'https://travel.state.gov/...',
    'scraped_at': '2024-09-20T15:30:00Z',
    'metadata': {
        'emergency_contact': '+33...',
        'entry_requirements': 'Passport required...'
    }
}
```

### Risk Level Standardization

Different sources use different risk level formats. The system normalizes them:

| US State Dept | UK Foreign Office | Standardized |
|---------------|-------------------|--------------|
| Level 1 | See Travel Advice | `NORMAL_PRECAUTIONS` |
| Level 2 | Advise Against Travel To Parts | `EXERCISE_CAUTION` |
| Level 3 | Advise Against All But Essential | `RECONSIDER_TRAVEL` |
| Level 4 | Advise Against All Travel | `AVOID_ALL_TRAVEL` |

## 💾 Caching System

### Redis Caching

```python
from app.api_clients.base_client import CacheConfig

cache_config = CacheConfig(
    enabled=True,
    default_ttl=3600,  # 1 hour
    key_prefix="travel_api",
    max_key_length=250
)
```

### Cache Strategies

- **Response Caching** - Cache API responses by endpoint and parameters
- **TTL Management** - Configurable time-to-live per endpoint type
- **Cache Keys** - MD5 hash of request parameters for efficient lookup
- **Cache Invalidation** - Manual and automatic cache clearing

### Performance Benefits

- **Response Time** - 10-100x faster for cached responses
- **API Quotas** - Reduced API usage and costs
- **Reliability** - Fallback when APIs are temporarily unavailable

## 🔧 Circuit Breaker Pattern

### Configuration

```python
from app.api_clients.base_client import CircuitBreakerConfig

circuit_config = CircuitBreakerConfig(
    failure_threshold=5,      # Open after 5 failures
    recovery_timeout=60,      # Try again after 60 seconds
    expected_exception=APITemporaryError
)
```

### States

1. **Closed** - Normal operation, requests pass through
2. **Open** - Circuit breaker activated, requests fail fast
3. **Half-Open** - Testing if service recovered

### Benefits

- **Fast Failure** - Immediate response when service is down
- **Automatic Recovery** - Periodic testing for service restoration
- **Resource Protection** - Prevents cascade failures

## 🚦 Rate Limiting

### Per-Source Configuration

```python
# US State Department: Conservative approach
rate_limit_calls=60,        # 60 requests per hour
rate_limit_period=3600      # 1 hour window

# UK Foreign Office: More permissive
rate_limit_calls=120,       # 120 requests per hour
rate_limit_period=3600      # 1 hour window
```

### Implementation

- **Rolling Windows** - Sliding time window for rate limit tracking
- **Per-Source Limits** - Different limits for different APIs
- **Backoff Strategy** - Wait when limits are reached
- **Monitoring** - Track rate limit usage and violations

## 📈 Monitoring and Metrics

### Performance Metrics

```python
from app.services.api_monitoring_service import api_monitoring_service

# Record API request
api_monitoring_service.record_api_request(
    source='us_state_department',
    response_time_ms=150.5,
    success=True,
    cached=False
)

# Get metrics summary
metrics = api_monitoring_service.get_metrics_summary()
```

### Tracked Metrics

- **Request Counts** - Total, successful, failed requests
- **Response Times** - Average, min, max, percentiles
- **Error Rates** - Percentage and types of errors
- **Cache Performance** - Hit/miss rates
- **Rate Limiting** - Usage and violations
- **Circuit Breaker** - Open/close events

### Health Monitoring

```python
# Check API health
health_status = await api_service.health_check()

# Get detailed health report
health_report = api_monitoring_service.get_health_summary()
```

### Alerting

Automatic alerts for:
- Error rate > 10%
- Response time > 5 seconds
- 5+ consecutive failures
- Uptime < 95%

## 🛡️ Error Handling

### Error Types

```python
from app.api_clients.base_client import (
    APIError,              # Base error
    APIRateLimitError,     # Rate limit exceeded
    APIAuthenticationError,# Auth failure
    APITemporaryError      # Temporary/retryable error
)
```

### Retry Strategy

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(APITemporaryError)
)
async def make_api_request():
    # API call logic
    pass
```

### Error Recovery

1. **Automatic Retry** - Exponential backoff for temporary errors
2. **Circuit Breaker** - Fast failure when service is down
3. **Fallback Sources** - Try alternative APIs
4. **Graceful Degradation** - Return partial data when possible

## 🔐 Authentication

### API Key Authentication

```python
from app.api_clients.base_client import AuthenticationConfig

auth_config = AuthenticationConfig(
    auth_type='api_key',
    api_key='your_api_key',
    api_key_header='X-API-Key'
)
```

### Supported Auth Types

- **API Key** - Header or query parameter
- **Bearer Token** - OAuth or JWT tokens
- **Basic Auth** - Username/password
- **None** - Public APIs

### Security Best Practices

- Store API keys in environment variables
- Use different keys for different environments
- Rotate keys regularly
- Monitor key usage and quotas

## 🚀 Advanced Usage

### Custom API Sources

Add new government API sources:

```python
from app.api_clients.base_client import BaseAPIClient

class CustomGovAPIClient(BaseAPIClient):
    async def get_travel_advisories(self, country=None):
        # Implementation
        pass

    async def get_country_advisory(self, country):
        # Implementation
        pass

    def normalize_advisory_data(self, raw_data):
        # Normalization logic
        pass
```

### Data Pipeline Integration

```python
# Integrate with existing scrapers
from app.services.scraping_service import ScrapingService

async def enhanced_scraping():
    api_service = UnifiedAPIService()
    scraping_service = ScrapingService()

    # Get data from APIs
    api_data = await api_service.get_travel_advisories()

    # Fallback to scraping if API data insufficient
    if not api_data.success:
        scraped_data = await scraping_service.scrape_all_sources()

    # Combine and normalize data
    # Store in database
```

### Webhook Integration

```python
# Set up webhooks for real-time updates
@app.route('/webhook/travel-advisory', methods=['POST'])
async def handle_travel_advisory_webhook():
    data = request.json

    # Process webhook data
    normalized_data = DataNormalizer.normalize_travel_advisory(
        data, source='webhook'
    )

    # Update database
    # Trigger notifications
```

## 📊 Performance Optimization

### Caching Strategies

```python
# Aggressive caching for stable data
await client.get_country_advisory('France', cache_ttl=7200)  # 2 hours

# Short caching for dynamic data
await client.get_country_advisory('Syria', cache_ttl=300)    # 5 minutes

# No caching for real-time data
await client.get_country_advisory('Ukraine', cache_ttl=0)    # No cache
```

### Concurrent Requests

```python
# Fetch multiple countries concurrently
countries = ['France', 'Germany', 'Italy', 'Spain']
tasks = [
    api_service.get_country_advisory(country)
    for country in countries
]

results = await asyncio.gather(*tasks)
```

### Batch Operations

```python
# Efficient batch processing
async def batch_update_advisories():
    api_service = UnifiedAPIService()

    # Get all advisories in one call
    response = await api_service.get_travel_advisories()

    # Process all data together
    for advisory in response.data:
        await store_advisory(advisory)
```

## 🔍 Troubleshooting

### Common Issues

#### API Connection Failures
```bash
# Check API health
python -m app.cli.api_cli health

# Test with verbose output
python -m app.cli.api_cli query --country france --verbose
```

#### Cache Issues
```bash
# Check Redis connection
redis-cli ping

# Clear cache if needed
redis-cli flushdb
```

#### Rate Limiting
```bash
# Check current rate limit status
python -m app.cli.api_cli metrics --source us_state_department

# View rate limit violations
python -m app.cli.api_cli alerts
```

### Debug Mode

```python
import structlog

# Enable debug logging
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
```

### Performance Monitoring

```bash
# Generate performance report
python -m app.cli.api_cli report --hours 24 --format json

# Monitor real-time metrics
watch python -m app.cli.api_cli metrics
```

## 📚 API Reference

### UnifiedAPIService

```python
class UnifiedAPIService:
    async def initialize_clients(api_keys=None)
    async def get_travel_advisories(country=None, sources=None, use_cache=True)
    async def get_country_advisory(country, sources=None, prefer_source=None)
    async def health_check() -> Dict[str, bool]
    async def close()
```

### BaseAPIClient

```python
class BaseAPIClient:
    async def get(endpoint, params=None, **kwargs) -> APIResponse
    async def post(endpoint, data=None, **kwargs) -> APIResponse
    async def health_check() -> bool
    async def close()
```

### CLI Commands

```bash
# Query APIs
python -m app.cli.api_cli query [--country COUNTRY] [--source SOURCE]

# Health checks
python -m app.cli.api_cli health [--source SOURCE]

# Performance metrics
python -m app.cli.api_cli metrics [--source SOURCE]

# Generate reports
python -m app.cli.api_cli report [--hours HOURS]

# Country-specific queries
python -m app.cli.api_cli country COUNTRY [--source SOURCE] [--compare]
```

## 🤝 Contributing

### Adding New API Sources

1. Create client class inheriting from `BaseAPIClient`
2. Implement required abstract methods
3. Add to `UnifiedAPIService`
4. Update documentation and tests

### Testing

```bash
# Run API client tests
pytest app/tests/test_api_clients.py

# Test with real APIs (requires keys)
pytest app/tests/test_api_integration.py --api-keys

# Performance testing
pytest app/tests/test_api_performance.py
```

---

For more information, see the main project documentation or contact the development team.