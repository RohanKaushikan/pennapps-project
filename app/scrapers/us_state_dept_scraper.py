import re
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, urlparse
import structlog
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, ScrapedContent, ScrapingConfig

logger = structlog.get_logger(__name__)


class USStateDeptScraper(BaseScraper):
    def __init__(self):
        config = ScrapingConfig(
            base_url="https://travel.state.gov",
            rate_limit_delay=1.5,
            max_retries=3,
            timeout=30,
            user_agent="TravelAdvisoryBot/1.0 (Travel Advisory Aggregator)"
        )
        super().__init__(config)

    async def scrape_country_advisory(self, country: str) -> Optional[ScrapedContent]:
        country_slug = self._country_to_slug(country)
        if not country_slug:
            logger.warning("Could not convert country to URL slug", country=country)
            return None

        advisory_url = f"{self.config.base_url}/content/travel/en/traveladvisories/traveladvisories/{country_slug}.html"

        response = await self._fetch_with_retry(advisory_url)
        if not response:
            return None

        content = self._parse_advisory_page(response.text, advisory_url)
        if content and self._validate_content(content):
            return content

        return None

    async def scrape_all_advisories(self) -> List[ScrapedContent]:
        advisories = []

        # First, get the main travel advisories page to find all country links
        main_url = f"{self.config.base_url}/content/travel/en/traveladvisories/traveladvisories.html"
        response = await self._fetch_with_retry(main_url)

        if not response:
            logger.error("Failed to fetch main travel advisories page")
            return advisories

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all country advisory links
        country_links = soup.find_all('a', href=re.compile(r'/content/travel/en/traveladvisories/traveladvisories/.*\.html'))

        logger.info(f"Found {len(country_links)} country advisory links")

        for link in country_links:
            country_url = urljoin(str(self.config.base_url), link.get('href'))
            country_name = self._extract_country_from_link(link)

            if not country_name:
                continue

            logger.info("Scraping advisory", country=country_name, url=country_url)

            response = await self._fetch_with_retry(country_url)
            if response:
                content = self._parse_advisory_page(response.text, country_url)
                if content and self._validate_content(content):
                    advisories.append(content)

        logger.info(f"Successfully scraped {len(advisories)} travel advisories")
        return advisories

    def _parse_advisory_page(self, html: str, url: str) -> Optional[ScrapedContent]:
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Extract title
            title_elem = soup.find('h1') or soup.find('title')
            title = self._clean_text(title_elem.get_text()) if title_elem else "Travel Advisory"

            # Extract country from title or URL
            country = self._extract_country_from_title(title) or self._extract_country_from_url(url)

            # Extract main content
            content_sections = []

            # Look for the main content area
            main_content = soup.find('div', class_=re.compile(r'tsg-rwd-content-page-content|main-content|content'))
            if not main_content:
                main_content = soup.find('main') or soup.find('div', {'id': 'content'})

            if main_content:
                # Remove navigation, footer, and other non-content elements
                for unwanted in main_content.find_all(['nav', 'footer', 'aside', 'script', 'style']):
                    unwanted.decompose()

                # Extract text from paragraphs and key sections
                for element in main_content.find_all(['p', 'div', 'section', 'article']):
                    text = self._clean_text(element.get_text())
                    if text and len(text) > 20:  # Filter out very short text
                        content_sections.append(text)

            # Join all content
            full_content = '\n\n'.join(content_sections)

            # Extract last updated date
            last_updated = self._extract_last_updated(soup)

            # Extract risk level
            risk_level = self._extract_risk_level(full_content)

            # Extract additional metadata
            metadata = self._extract_metadata(soup)

            # Calculate content hash
            content_hash = self._calculate_content_hash(full_content)

            return ScrapedContent(
                url=url,
                title=title,
                content=full_content,
                content_hash=content_hash,
                last_updated=last_updated,
                country=country,
                risk_level=risk_level,
                metadata=metadata,
                scraped_at=__import__('time').time()
            )

        except Exception as e:
            logger.error("Error parsing advisory page", url=url, error=str(e))
            return None

    def _country_to_slug(self, country: str) -> Optional[str]:
        # Common mappings for US State Department URLs
        country_mappings = {
            'united states': 'unitedstates',
            'united kingdom': 'unitedkingdom',
            'south korea': 'southkorea',
            'north korea': 'northkorea',
            'saudi arabia': 'saudiarabia',
            'south africa': 'southafrica',
            'new zealand': 'newzealand',
            'sri lanka': 'srilanka',
            'costa rica': 'costarica',
            'puerto rico': 'puertorico',
            'czech republic': 'czechrepublic',
            'dominican republic': 'dominicanrepublic',
            'el salvador': 'elsalvador',
            'ivory coast': 'ivorycoast',
            'burkina faso': 'burkinafaso',
        }

        country_lower = country.lower().strip()

        # Check direct mapping first
        if country_lower in country_mappings:
            return country_mappings[country_lower]

        # Remove common words and create slug
        slug = re.sub(r'[^a-zA-Z0-9\s]', '', country_lower)
        slug = re.sub(r'\s+', '', slug)

        return slug if slug else None

    def _extract_country_from_title(self, title: str) -> Optional[str]:
        # Extract country from title patterns like "Country Travel Advisory"
        patterns = [
            r'^(.+?)\s+Travel\s+Advisory',
            r'^Travel\s+Advisory\s*[:\-]\s*(.+?)$',
            r'^(.+?)\s*[:\-]\s*Travel',
        ]

        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                country = match.group(1).strip()
                # Clean up common prefixes/suffixes
                country = re.sub(r'^(the\s+)', '', country, flags=re.IGNORECASE)
                return country

        return None

    def _extract_country_from_url(self, url: str) -> Optional[str]:
        # Extract country from URL path
        path = urlparse(url).path
        match = re.search(r'/traveladvisories/([^/]+)\.html', path)
        if match:
            slug = match.group(1)
            # Convert slug back to readable name
            return slug.replace('', ' ').title()

        return None

    def _extract_country_from_link(self, link) -> Optional[str]:
        # Extract country name from link text or href
        link_text = self._clean_text(link.get_text())
        if link_text:
            return link_text.strip()

        href = link.get('href', '')
        return self._extract_country_from_url(href)

    def _extract_last_updated(self, soup: BeautifulSoup) -> Optional[str]:
        # Look for common date patterns
        date_patterns = [
            soup.find(text=re.compile(r'last updated|updated|published', re.IGNORECASE)),
            soup.find('time'),
            soup.find(attrs={'class': re.compile(r'date|time|updated', re.IGNORECASE)}),
            soup.find(attrs={'id': re.compile(r'date|time|updated', re.IGNORECASE)})
        ]

        for pattern in date_patterns:
            if pattern:
                if hasattr(pattern, 'get_text'):
                    date_text = pattern.get_text()
                else:
                    date_text = str(pattern)

                # Extract date from text
                date_match = re.search(r'\b(\w+\s+\d{1,2},?\s+\d{4}|\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})', date_text)
                if date_match:
                    return date_match.group(1)

        return None

    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        metadata = {}

        # Extract summary if available
        summary_elem = soup.find(attrs={'class': re.compile(r'summary|excerpt|description', re.IGNORECASE)})
        if summary_elem:
            metadata['summary'] = self._clean_text(summary_elem.get_text())

        # Extract any warning boxes or important notices
        warnings = []
        warning_elems = soup.find_all(attrs={'class': re.compile(r'warning|alert|notice|important', re.IGNORECASE)})
        for warning in warning_elems:
            warning_text = self._clean_text(warning.get_text())
            if warning_text and len(warning_text) > 10:
                warnings.append(warning_text)

        if warnings:
            metadata['warnings'] = warnings

        # Extract any emergency contact information
        contact_elem = soup.find(text=re.compile(r'embassy|consulate|emergency contact', re.IGNORECASE))
        if contact_elem:
            metadata['emergency_contact'] = self._clean_text(str(contact_elem))

        return metadata