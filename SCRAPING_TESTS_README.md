# Travel Advisory Scraping Test Scripts

This directory contains scripts for testing the travel advisory scraping functionality.

## Scripts Overview

### 1. `simple_scraping_test.py`
**Purpose**: Tests the scraper classes directly without database integration
**Use Case**: Quick testing of scraper functionality, debugging parsing issues
**Requirements**: No database setup required

### 2. `manual_scraping_test.py` 
**Purpose**: Full integration test with database storage
**Use Case**: Testing complete workflow from scraping to database storage
**Requirements**: Database setup and configuration required

### 3. `test_scraping_service.py`
**Purpose**: Quick test of the scraping service
**Use Case**: Verify the service is working before running full tests
**Requirements**: Database setup required

## Quick Start

### Test Scraper Functionality (No Database Required)

```bash
# Test with default test sources
python simple_scraping_test.py

# Test with custom sources file
python simple_scraping_test.py --sources-file data/sources/government_sources.json

# Enable verbose logging
python simple_scraping_test.py --verbose
```

### Test Full Database Integration

```bash
# Run full integration test (requires database)
python manual_scraping_test.py

# Use custom sources file
python manual_scraping_test.py --sources-file data/sources/government_sources.json

# Enable verbose logging
python manual_scraping_test.py --verbose
```

## Source Configuration

### Source File Format

Sources are configured in JSON files with the following format:

```json
[
  {
    "name": "Source Name",
    "url": "https://example.com",
    "country_code": "US",
    "source_type": "government"
  }
]
```

### Available Source Files

- `data/sources/test_sources.json` - Safe test sources for initial testing
- `data/sources/government_sources.json` - Real government travel advisory sources

### Source Types

- `"government"` - Uses GovernmentAdvisoryScraper with enhanced parsing
- `"generic"` - Uses basic TravelAdvisoryScraper

## Example Usage

### 1. Test Scraper Classes

```bash
# Test with safe sources
python simple_scraping_test.py --sources-file data/sources/test_sources.json
```

**Expected Output:**
```
🧪 SIMPLE TRAVEL ADVISORY SCRAPING TEST
============================================================
⏰ Started at: 2025-09-20 19:43:11

📋 Sources to test:
------------------------------------------------------------
 1. 🌐 Test Source (Safe)
    URL: https://httpbin.org/html
    Type: generic

🚀 Testing scrapers...
------------------------------------------------------------
🔍 Testing Test Source (Safe)...
  ✅ Success: Found 0 advisories
  ⏱️  Duration: 0.07s

📊 TEST RESULTS SUMMARY
============================================================
🎯 Overall Results:
  Sources tested: 1
  Successful tests: 1
  Failed tests: 0
  Success rate: 100.0%
```

### 2. Test Full Integration

```bash
# Test with real sources (requires database)
python manual_scraping_test.py --sources-file data/sources/government_sources.json
```

**Expected Output:**
```
🌍 MANUAL TRAVEL ADVISORY SCRAPING TEST
================================================================================
⏰ Started at: 2025-09-20 19:43:11

📋 Sources to be scraped:
--------------------------------------------------------------------------------
 1. 🏛️ US State Department
    URL: https://travel.state.gov
    Country: US
    Type: government

🚀 Starting scraping process...

📊 SCRAPING RESULTS SUMMARY
================================================================================
🎯 Overall Results:
  Total sources processed: 1
  Successful sources: 1 ✅
  Failed sources: 0 ❌
  Success rate: 100.0%

📈 Content Statistics:
  Total advisories scraped: 5
  New advisories stored: 3
  Duplicates skipped: 2
  Total errors encountered: 0

🎯 Total new alerts added: 3
```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Ensure PostgreSQL is running
   - Check database configuration in `app/core/config.py`
   - Verify database URL is correct

2. **No Advisories Found**
   - This is normal for test sources (httpbin.org, example.com)
   - Try with real government sources for actual content

3. **Network Timeouts**
   - Some government sites may be slow or block automated requests
   - The scrapers include retry logic and timeout handling

4. **Parsing Errors**
   - Different sites have different HTML structures
   - The scrapers use flexible selectors to handle various formats

### Debug Mode

Enable verbose logging for detailed debugging:

```bash
python simple_scraping_test.py --verbose
python manual_scraping_test.py --verbose
```

This will show:
- Detailed HTTP requests
- HTML parsing steps
- Database operations
- Error stack traces

## Source Management

### Adding New Sources

1. Edit the appropriate sources JSON file
2. Add your source with the required fields:
   - `name`: Human-readable source name
   - `url`: Source URL to scrape
   - `country_code`: ISO country code (e.g., "US", "GB")
   - `source_type`: "government" or "generic"

### Testing New Sources

```bash
# Create a test file with your new source
echo '[{"name": "My Source", "url": "https://example.com", "country_code": "US", "source_type": "generic"}]' > my_test_sources.json

# Test the new source
python simple_scraping_test.py --sources-file my_test_sources.json
```

## Performance Considerations

- **Timeout Settings**: Default timeout is 30 seconds per source
- **Retry Logic**: Up to 3 retries with exponential backoff
- **Rate Limiting**: Be respectful of target websites
- **Memory Usage**: Large pages are processed incrementally

## Security Notes

- The scrapers use standard HTTP headers and user agents
- No authentication or cookies are used
- All requests are made over HTTPS when available
- Content is processed locally without external API calls

## Integration with Main System

These test scripts use the same scraper classes as the main application:

- `TravelAdvisoryScraper` - Generic scraper for any website
- `GovernmentAdvisoryScraper` - Specialized scraper for government sites
- `AdvisoryScrapingService` - Service layer with database integration

The scrapers are designed to be production-ready and handle real-world websites with proper error handling and logging.
