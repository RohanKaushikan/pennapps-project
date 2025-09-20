import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from bs4 import BeautifulSoup
import httpx

from app.scrapers.base_scraper import BaseScraper, ScrapedContent, ScrapingConfig
from app.scrapers.us_state_dept_scraper import USStateDeptScraper
from app.scrapers.uk_foreign_office_scraper import UKForeignOfficeScraper
from app.scrapers.canada_travel_scraper import CanadaTravelScraper


class TestBaseScraper:
    """Test cases for the base scraper functionality."""

    @pytest.fixture
    def mock_config(self):
        return ScrapingConfig(
            base_url="https://example.com",
            rate_limit_delay=0.1,
            max_retries=2,
            timeout=10
        )

    @pytest.fixture
    def mock_scraper(self, mock_config):
        class MockScraper(BaseScraper):
            async def scrape_country_advisory(self, country):
                return None

            async def scrape_all_advisories(self):
                return []

            def _parse_advisory_page(self, html, url):
                return None

        return MockScraper(mock_config)

    def test_content_hash_calculation(self, mock_scraper):
        """Test that content hashing works correctly."""
        content1 = "This is test content"
        content2 = "This is test content"
        content3 = "This is different content"

        hash1 = mock_scraper._calculate_content_hash(content1)
        hash2 = mock_scraper._calculate_content_hash(content2)
        hash3 = mock_scraper._calculate_content_hash(content3)

        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 64  # SHA256 hex length

    def test_text_cleaning(self, mock_scraper):
        """Test text cleaning functionality."""
        dirty_text = "  This   has   extra    spaces  \n\n\t  "
        clean_text = mock_scraper._clean_text(dirty_text)
        assert clean_text == "This has extra spaces"

        html_entities = "&nbsp;&amp;&lt;&gt;&quot;&#39;"
        clean_entities = mock_scraper._clean_text(html_entities)
        assert clean_entities == " &<>\"'"

    def test_risk_level_extraction(self, mock_scraper):
        """Test risk level extraction from content."""
        test_cases = [
            ("Do not travel to this country", "Level 4 - Do Not Travel"),
            ("Reconsider travel due to safety", "Level 3 - Reconsider Travel"),
            ("Exercise increased caution when traveling", "Level 2 - Exercise Increased Caution"),
            ("Exercise normal precautions", "Level 1 - Exercise Normal Precautions"),
            ("Level 2 advisory in effect", "Level 2 - Exercise Increased Caution"),
            ("No specific warnings", None)
        ]

        for content, expected in test_cases:
            result = mock_scraper._extract_risk_level(content)
            assert result == expected

    def test_content_validation(self, mock_scraper):
        """Test content validation logic."""
        valid_content = ScrapedContent(
            url="https://example.com/test",
            title="Test Advisory",
            content="This is a valid content that is longer than 100 characters and should pass validation checks.",
            content_hash="test_hash",
            scraped_at=1234567890.0
        )

        invalid_content_short = ScrapedContent(
            url="https://example.com/test",
            title="Test Advisory",
            content="Short",
            content_hash="test_hash",
            scraped_at=1234567890.0
        )

        invalid_content_no_title = ScrapedContent(
            url="https://example.com/test",
            title="",
            content="This is a valid content that is longer than 100 characters and should pass validation checks.",
            content_hash="test_hash",
            scraped_at=1234567890.0
        )

        assert mock_scraper._validate_content(valid_content) == True
        assert mock_scraper._validate_content(invalid_content_short) == False
        assert mock_scraper._validate_content(invalid_content_no_title) == False

    @pytest.mark.asyncio
    async def test_rate_limiting(self, mock_scraper):
        """Test that rate limiting works correctly."""
        import time

        start_time = time.time()
        await mock_scraper._rate_limit()
        await mock_scraper._rate_limit()
        end_time = time.time()

        # Should take at least the rate limit delay
        assert end_time - start_time >= mock_scraper.config.rate_limit_delay


class TestUSStateDeptScraper:
    """Test cases for US State Department scraper."""

    @pytest.fixture
    def scraper(self):
        return USStateDeptScraper()

    def test_country_to_slug_mapping(self, scraper):
        """Test country name to URL slug conversion."""
        test_cases = [
            ("United States", "unitedstates"),
            ("United Kingdom", "unitedkingdom"),
            ("South Korea", "southkorea"),
            ("France", "france"),
            ("Democratic Republic of Congo", "democraticrepublicofcongo")
        ]

        for country, expected_slug in test_cases:
            result = scraper._country_to_slug(country)
            assert result == expected_slug

    def test_country_extraction_from_title(self, scraper):
        """Test country extraction from page titles."""
        test_cases = [
            ("France Travel Advisory", "France"),
            ("Travel Advisory: Germany", "Germany"),
            ("United Kingdom Travel Advisory", "United Kingdom"),
            ("The Netherlands Travel Advisory", "Netherlands")
        ]

        for title, expected_country in test_cases:
            result = scraper._extract_country_from_title(title)
            assert result == expected_country

    def test_parse_advisory_page(self, scraper):
        """Test parsing of US State Department advisory pages."""
        sample_html = """
        <html>
            <head><title>France Travel Advisory</title></head>
            <body>
                <h1>France Travel Advisory</h1>
                <div class="tsg-rwd-content-page-content">
                    <p>Exercise increased caution in France due to terrorism and civil unrest.</p>
                    <p>Terrorists may attack with little or no warning, targeting tourist locations.</p>
                </div>
                <p>Last Updated: March 15, 2024</p>
            </body>
        </html>
        """

        result = scraper._parse_advisory_page(sample_html, "https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories/france.html")

        assert result is not None
        assert result.title == "France Travel Advisory"
        assert "Exercise increased caution" in result.content
        assert result.risk_level == "Level 2 - Exercise Increased Caution"
        assert result.content_hash is not None


class TestUKForeignOfficeScraper:
    """Test cases for UK Foreign Office scraper."""

    @pytest.fixture
    def scraper(self):
        return UKForeignOfficeScraper()

    def test_country_to_slug_mapping(self, scraper):
        """Test country name to URL slug conversion for UK gov format."""
        test_cases = [
            ("United States", "usa"),
            ("South Korea", "south-korea"),
            ("Czech Republic", "czech-republic"),
            ("France", "france")
        ]

        for country, expected_slug in test_cases:
            result = scraper._country_to_slug(country)
            assert result == expected_slug

    def test_uk_risk_level_extraction(self, scraper):
        """Test UK-specific risk level extraction."""
        sample_html = """
        <html>
            <body>
                <div class="gem-c-warning">
                    <p>The FCDO advise against all travel to this country.</p>
                </div>
            </body>
        </html>
        """
        soup = BeautifulSoup(sample_html, 'html.parser')
        content = "The FCDO advise against all travel to this country due to ongoing conflict."

        result = scraper._extract_uk_risk_level(soup, content)
        assert result == "Advise Against All Travel"


class TestCanadaTravelScraper:
    """Test cases for Canadian travel scraper."""

    @pytest.fixture
    def scraper(self):
        return CanadaTravelScraper()

    def test_country_to_slug_mapping(self, scraper):
        """Test country name to URL slug conversion for Canadian format."""
        test_cases = [
            ("United States", "united-states"),
            ("South Korea", "korea-south"),
            ("Democratic Republic of Congo", "congo-democratic-republic"),
            ("France", "france")
        ]

        for country, expected_slug in test_cases:
            result = scraper._country_to_slug(country)
            assert result == expected_slug

    def test_canada_risk_level_extraction(self, scraper):
        """Test Canada-specific risk level extraction."""
        test_cases = [
            ("Avoid all travel to this region", "Avoid All Travel"),
            ("Avoid non-essential travel", "Avoid Non-Essential Travel"),
            ("Exercise a high degree of caution", "Exercise High Degree of Caution"),
            ("Take normal security precautions", "Exercise Normal Precautions")
        ]

        for content, expected_level in test_cases:
            soup = BeautifulSoup("<html><body></body></html>", 'html.parser')
            result = scraper._extract_canada_risk_level(soup, content)
            assert result == expected_level


class TestScrapingIntegration:
    """Integration tests for the scraping system."""

    @pytest.mark.asyncio
    async def test_scraper_http_client_handling(self):
        """Test that scrapers handle HTTP clients correctly."""
        scraper = USStateDeptScraper()

        # Test that client is properly initialized
        assert scraper.client is not None
        assert isinstance(scraper.client, httpx.AsyncClient)

        # Test cleanup
        await scraper.close()

    @pytest.mark.asyncio
    async def test_robots_txt_respect(self):
        """Test that scrapers respect robots.txt when configured."""
        config = ScrapingConfig(
            base_url="https://example.com",
            respect_robots_txt=True
        )

        class TestScraper(BaseScraper):
            async def scrape_country_advisory(self, country):
                return None

            async def scrape_all_advisories(self):
                return []

            def _parse_advisory_page(self, html, url):
                return None

        scraper = TestScraper(config)

        # Mock robots.txt that disallows everything
        with patch.object(scraper, '_can_fetch', return_value=False):
            result = await scraper._fetch_with_retry("https://example.com/test")
            assert result is None

        await scraper.close()

    @pytest.mark.asyncio
    async def test_retry_mechanism(self):
        """Test the retry mechanism for failed requests."""
        config = ScrapingConfig(
            base_url="https://example.com",
            max_retries=2,
            retry_delay=0.1
        )

        class TestScraper(BaseScraper):
            async def scrape_country_advisory(self, country):
                return None

            async def scrape_all_advisories(self):
                return []

            def _parse_advisory_page(self, html, url):
                return None

        scraper = TestScraper(config)

        # Mock client to always fail
        scraper.client.get = AsyncMock(side_effect=httpx.RequestError("Network error"))

        result = await scraper._fetch_with_retry("https://example.com/test")
        assert result is None

        # Verify it was called the right number of times (initial + retries)
        assert scraper.client.get.call_count == config.max_retries

        await scraper.close()


@pytest.mark.asyncio
async def test_concurrent_scraping():
    """Test that multiple scrapers can work concurrently."""
    scrapers = [
        USStateDeptScraper(),
        UKForeignOfficeScraper(),
        CanadaTravelScraper()
    ]

    try:
        # Test that all scrapers can be created and closed concurrently
        tasks = [scraper.close() for scraper in scrapers]
        await asyncio.gather(*tasks)

    except Exception as e:
        pytest.fail(f"Concurrent scraping test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__])