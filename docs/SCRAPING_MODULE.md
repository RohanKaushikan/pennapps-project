# Travel Advisory Scraping Module

A comprehensive web scraping system for government travel advisory sources with built-in rate limiting, error handling, content change detection, and database storage.

## Features

### 🌐 Multi-Source Support
- **US State Department** - Travel Advisories with 4-level risk system
- **UK Foreign Office** - Travel Advice with specific advisory language
- **Canadian Government** - Travel Advisories and health information

### 🛡️ Robust Architecture
- **Rate Limiting** - Respects server resources with configurable delays
- **Error Handling** - Comprehensive retry mechanisms with exponential backoff
- **Robots.txt Compliance** - Automatically respects website scraping policies
- **Content Validation** - Ensures data quality and completeness

### 🔍 Change Detection
- **Content Hashing** - SHA256 hashing for precise change detection
- **Risk Level Monitoring** - Tracks changes in travel advisory levels
- **Change Events** - Detailed logging of all content modifications
- **Historical Tracking** - Maintains complete change history

### 💾 Database Integration
- **Async SQLAlchemy** - High-performance database operations
- **Comprehensive Models** - Travel advisories, scraping logs, change events
- **Indexing** - Optimized for fast queries and reporting
- **Migration Support** - Alembic integration for schema management

## Quick Start

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run database migrations:
```bash
alembic upgrade head
```

### Basic Usage

#### CLI Interface

```bash
# Scrape all sources
python -m app.cli.scraping_cli scrape

# Scrape specific source
python -m app.cli.scraping_cli scrape --source us_state_dept

# Scrape specific country
python -m app.cli.scraping_cli scrape --source uk_foreign_office --country france

# View recent changes
python -m app.cli.scraping_cli changes --limit 20

# Get country information
python -m app.cli.scraping_cli country-info japan

# List available sources
python -m app.cli.scraping_cli sources
```

#### Programmatic Usage

```python
import asyncio
from app.core.database import get_session
from app.services.scraping_service import ScrapingService

async def scrape_example():
    scraping_service = ScrapingService()

    async with get_session() as session:
        # Scrape all sources
        results = await scraping_service.scrape_all_sources(session)
        print(f"Scraped {results['total_new']} new advisories")

        # Scrape specific country
        advisory = await scraping_service.scrape_country_from_source(
            session, 'us_state_dept', 'France'
        )
        if advisory:
            print(f"Risk Level: {advisory.risk_level}")

    await scraping_service.close_scrapers()

asyncio.run(scrape_example())
```

#### Run Example Script

```bash
python scripts/scraping_example.py
```

## Architecture Overview

### Components

#### 1. Base Scraper (`app/scrapers/base_scraper.py`)
- Abstract base class with common functionality
- Rate limiting, retry logic, robots.txt compliance
- Content validation and risk level extraction
- Extensible design for adding new sources

#### 2. Source-Specific Scrapers
- **US State Department** (`us_state_dept_scraper.py`)
- **UK Foreign Office** (`uk_foreign_office_scraper.py`)
- **Canadian Government** (`canada_travel_scraper.py`)

#### 3. Scraping Service (`app/services/scraping_service.py`)
- High-level interface for scraping operations
- Database integration and change detection
- Session management and logging

#### 4. Database Models (`app/models/travel_advisory.py`)
- `TravelAdvisory` - Core advisory data
- `ScrapingLog` - Scraping session tracking
- `ContentChangeEvent` - Change detection events

#### 5. CLI Interface (`app/cli/scraping_cli.py`)
- Command-line interface for operations
- Interactive progress reporting
- Error handling and user feedback

### Data Flow

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Government    │    │    Scrapers      │    │    Database     │
│   Websites      │◄──►│                  │◄──►│                 │
│                 │    │ • Rate Limiting  │    │ • Travel        │
│ • US State Dept │    │ • Error Handling │    │   Advisories    │
│ • UK Foreign    │    │ • Content Parse  │    │ • Change Events │
│ • Canada Travel │    │ • Change Detect  │    │ • Scraping Logs │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   CLI / API      │
                       │                  │
                       │ • Status Reports │
                       │ • Data Queries   │
                       │ • Change Alerts  │
                       └──────────────────┘
```

## Configuration

### Scraper Configuration

Each scraper can be configured with:

```python
config = ScrapingConfig(
    base_url="https://example.com",
    rate_limit_delay=1.0,      # Seconds between requests
    max_retries=3,             # Number of retry attempts
    retry_delay=2.0,           # Base delay for retries
    timeout=30,                # Request timeout in seconds
    user_agent="Custom Bot",   # User agent string
    respect_robots_txt=True,   # Whether to check robots.txt
    headers={}                 # Additional HTTP headers
)
```

### Database Configuration

Configure database connection in `app/core/config.py`:

```python
DATABASE_URL = "postgresql+asyncpg://user:password@localhost/dbname"
```

## Extending the System

### Adding New Sources

1. Create a new scraper class inheriting from `BaseScraper`:

```python
from app.scrapers.base_scraper import BaseScraper, ScrapedContent

class NewSourceScraper(BaseScraper):
    def __init__(self):
        config = ScrapingConfig(
            base_url="https://new-source.gov",
            rate_limit_delay=1.5
        )
        super().__init__(config)

    async def scrape_country_advisory(self, country: str) -> Optional[ScrapedContent]:
        # Implementation for single country
        pass

    async def scrape_all_advisories(self) -> List[ScrapedContent]:
        # Implementation for all countries
        pass

    def _parse_advisory_page(self, html: str, url: str) -> Optional[ScrapedContent]:
        # Parse the HTML content
        pass
```

2. Register in `ScrapingService`:

```python
self.scrapers['new_source'] = NewSourceScraper()
```

3. Add to CLI options and documentation.

### Custom Risk Level Extraction

Override `_extract_risk_level` for source-specific patterns:

```python
def _extract_source_risk_level(self, soup: BeautifulSoup, content: str) -> Optional[str]:
    # Source-specific risk level extraction
    if 'extreme danger' in content.lower():
        return 'Extreme Risk'
    # ... more patterns

    # Fallback to base implementation
    return self._extract_risk_level(content)
```

## Monitoring and Maintenance

### Health Checks

```python
async def check_scraper_health():
    """Check if all sources are accessible."""
    scraping_service = ScrapingService()

    for source_name, scraper in scraping_service.scrapers.items():
        try:
            response = await scraper._fetch_with_retry(scraper.config.base_url)
            status = "✅ OK" if response else "❌ Failed"
            print(f"{source_name}: {status}")
        except Exception as e:
            print(f"{source_name}: ❌ Error - {e}")

    await scraping_service.close_scrapers()
```

### Performance Monitoring

Query scraping logs for performance insights:

```sql
-- Average scraping times by source
SELECT
    source,
    AVG(duration_seconds) as avg_duration,
    COUNT(*) as total_runs,
    SUM(successful_scrapes) as total_success,
    SUM(failed_scrapes) as total_failures
FROM scraping_logs
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY source;

-- Recent content changes
SELECT
    change_type,
    COUNT(*) as count,
    DATE(detected_at) as date
FROM content_change_events
WHERE detected_at >= NOW() - INTERVAL '30 days'
GROUP BY change_type, DATE(detected_at)
ORDER BY date DESC;
```

### Automated Monitoring

Set up scheduled scraping with cron:

```bash
# Run every 6 hours
0 */6 * * * cd /path/to/project && python -m app.cli.scraping_cli scrape

# Generate daily change report
0 9 * * * cd /path/to/project && python -m app.cli.scraping_cli changes --limit 50 > /var/log/travel_changes.log
```

## Error Handling

The system includes comprehensive error handling:

### Network Errors
- Automatic retries with exponential backoff
- Timeout handling
- Connection pooling

### Parsing Errors
- Graceful degradation when content structure changes
- Validation of extracted data
- Logging of parsing failures

### Database Errors
- Transaction rollback on failures
- Connection retry logic
- Data integrity checks

### Rate Limiting
- Respect for server resources
- Adaptive delays based on response times
- Robots.txt compliance

## Best Practices

### Responsible Scraping
1. **Respect Rate Limits** - Use appropriate delays between requests
2. **Check Robots.txt** - Always respect website scraping policies
3. **Monitor Resources** - Keep track of bandwidth and server load
4. **Handle Errors Gracefully** - Don't overwhelm servers with retries

### Data Quality
1. **Validate Content** - Ensure scraped data meets quality standards
2. **Track Changes** - Monitor for unexpected content modifications
3. **Regular Testing** - Verify scrapers work with website updates
4. **Backup Data** - Maintain historical copies of important advisories

### Performance
1. **Async Operations** - Use async/await for better concurrency
2. **Database Indexing** - Optimize queries with proper indexes
3. **Connection Pooling** - Reuse database connections efficiently
4. **Monitoring** - Track scraping performance and success rates

## Troubleshooting

### Common Issues

#### Scraper Fails to Connect
```bash
# Check network connectivity
curl -I https://travel.state.gov

# Check robots.txt
curl https://travel.state.gov/robots.txt

# Test with verbose logging
python -m app.cli.scraping_cli scrape --source us_state_dept --verbose
```

#### Content Not Parsing
1. Check if website structure changed
2. Review HTML manually
3. Update parsing selectors
4. Test with sample HTML

#### Database Connection Issues
```bash
# Test database connection
python -c "from app.core.database import get_session; import asyncio; asyncio.run(get_session().__anext__())"

# Run migrations
alembic upgrade head
```

### Debug Mode

Enable debug logging:

```python
import structlog

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

## Contributing

### Development Setup

1. Clone repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up pre-commit hooks: `pre-commit install`
4. Run tests: `pytest app/tests/`

### Testing

```bash
# Run all tests
pytest app/tests/

# Run specific test file
pytest app/tests/test_scrapers.py

# Run with coverage
pytest --cov=app app/tests/
```

### Code Quality

The project uses:
- **Black** - Code formatting
- **isort** - Import sorting
- **flake8** - Linting
- **mypy** - Type checking

Run quality checks:
```bash
black app/
isort app/
flake8 app/
mypy app/
```

## License

This module is part of the larger travel advisory system and follows the same licensing terms.

---

For more information, see the main project documentation or contact the development team.