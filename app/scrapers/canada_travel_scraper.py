import re
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, urlparse
import structlog
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, ScrapedContent, ScrapingConfig

logger = structlog.get_logger(__name__)


class CanadaTravelScraper(BaseScraper):
    def __init__(self):
        config = ScrapingConfig(
            base_url="https://travel.gc.ca",
            rate_limit_delay=1.2,
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

        advisory_url = f"{self.config.base_url}/destinations/{country_slug}"

        response = await self._fetch_with_retry(advisory_url)
        if not response:
            return None

        content = self._parse_advisory_page(response.text, advisory_url)
        if content and self._validate_content(content):
            return content

        return None

    async def scrape_all_advisories(self) -> List[ScrapedContent]:
        advisories = []

        # Get the main travel destinations page
        main_url = f"{self.config.base_url}/destinations"
        response = await self._fetch_with_retry(main_url)

        if not response:
            logger.error("Failed to fetch main travel destinations page")
            return advisories

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all country links - Canada uses destination patterns
        country_links = soup.find_all('a', href=re.compile(r'/destinations/[^/]+/?$'))

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
            title_elem = soup.find('h1', id='wb-cont')
            if not title_elem:
                title_elem = soup.find('h1') or soup.find('title')
            title = self._clean_text(title_elem.get_text()) if title_elem else "Travel Advisory"

            # Extract country from title or URL
            country = self._extract_country_from_title(title) or self._extract_country_from_url(url)

            # Extract main content
            content_sections = []

            # Canadian government uses specific content structure
            main_content = soup.find('main', {'property': 'mainContentOfPage'})
            if not main_content:
                main_content = soup.find('div', {'id': 'wb-main'}) or soup.find('main')

            if main_content:
                # Remove navigation, footer, and other non-content elements
                for unwanted in main_content.find_all(['nav', 'footer', 'aside', 'script', 'style']):
                    unwanted.decompose()

                # Remove WET (Web Experience Toolkit) elements
                for unwanted_class in ['wb-sl', 'wb-sec', 'pagedetails', 'gc-sub-footer']:
                    for elem in main_content.find_all(class_=unwanted_class):
                        elem.decompose()

                # Extract advisory level and summary
                advisory_elem = soup.find(class_=re.compile(r'advisory|alert|mrgn'))
                if advisory_elem:
                    advisory_text = self._clean_text(advisory_elem.get_text())
                    if advisory_text and len(advisory_text) > 20:
                        content_sections.append(advisory_text)

                # Extract content from sections
                for section in main_content.find_all(['section', 'div'], class_=re.compile(r'mrgn|panel|alert')):
                    section_text = self._clean_text(section.get_text())
                    if section_text and len(section_text) > 20:
                        content_sections.append(section_text)

                # If no specific sections found, extract from all paragraphs and divs
                if not content_sections:
                    for element in main_content.find_all(['p', 'div', 'section']):
                        text = self._clean_text(element.get_text())
                        if text and len(text) > 20:
                            content_sections.append(text)

            # Join all content
            full_content = '\n\n'.join(content_sections)

            # Extract last updated date
            last_updated = self._extract_last_updated(soup)

            # Extract risk level - Canada uses specific advisory levels
            risk_level = self._extract_canada_risk_level(soup, full_content)

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
        # Common mappings for Canadian travel.gc.ca URLs
        country_mappings = {
            'united states': 'united-states',
            'united kingdom': 'united-kingdom',
            'south korea': 'korea-south',
            'north korea': 'korea-north',
            'saudi arabia': 'saudi-arabia',
            'south africa': 'south-africa',
            'new zealand': 'new-zealand',
            'sri lanka': 'sri-lanka',
            'costa rica': 'costa-rica',
            'czech republic': 'czech-republic',
            'dominican republic': 'dominican-republic',
            'el salvador': 'el-salvador',
            'ivory coast': 'cote-divoire',
            'burkina faso': 'burkina-faso',
            'bosnia and herzegovina': 'bosnia-herzegovina',
            'democratic republic of congo': 'congo-democratic-republic',
            'republic of congo': 'congo-republic',
            'central african republic': 'central-african-republic',
        }

        country_lower = country.lower().strip()

        # Check direct mapping first
        if country_lower in country_mappings:
            return country_mappings[country_lower]

        # Create slug with hyphens (Canadian gov style)
        slug = re.sub(r'[^a-zA-Z0-9\s]', '', country_lower)
        slug = re.sub(r'\s+', '-', slug.strip())

        return slug if slug else None

    def _extract_country_from_title(self, title: str) -> Optional[str]:
        # Extract country from Canadian travel advisory title patterns
        patterns = [
            r'^(.+?)\s*[:\-]\s*travel\s+advice',
            r'^Travel\s+advice\s+and\s+advisories\s+for\s+(.+?)$',
            r'^(.+?)\s+travel\s+advice\s+and\s+advisories',
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
        match = re.search(r'/destinations/([^/]+)/?$', path)
        if match:
            slug = match.group(1)
            # Convert slug back to readable name
            return slug.replace('-', ' ').title()

        return None

    def _extract_country_from_link(self, link) -> Optional[str]:
        # Extract country name from link text
        link_text = self._clean_text(link.get_text())
        if link_text:
            # Remove common text patterns
            link_text = re.sub(r'\s*travel\s+advice.*$', '', link_text, flags=re.IGNORECASE)
            link_text = re.sub(r'\s*advisories.*$', '', link_text, flags=re.IGNORECASE)
            return link_text.strip()

        href = link.get('href', '')
        return self._extract_country_from_url(href)

    def _extract_last_updated(self, soup: BeautifulSoup) -> Optional[str]:
        # Canadian gov sites use specific date elements
        date_elem = soup.find('time', {'datetime': True})
        if date_elem:
            return date_elem.get('datetime') or date_elem.get_text()

        # Look for WET framework date patterns
        date_elem = soup.find('dl', class_='dl-horizontal')
        if date_elem:
            date_text = date_elem.get_text()
            date_match = re.search(r'\b(\d{4}-\d{2}-\d{2}|\w+\s+\d{1,2},?\s+\d{4})', date_text)
            if date_match:
                return date_match.group(1)

        # Look for common date patterns
        date_patterns = [
            soup.find(text=re.compile(r'last updated|updated|published|modified', re.IGNORECASE)),
            soup.find(attrs={'class': re.compile(r'date|time|updated|modified', re.IGNORECASE)}),
        ]

        for pattern in date_patterns:
            if pattern:
                if hasattr(pattern, 'get_text'):
                    date_text = pattern.get_text()
                else:
                    date_text = str(pattern)

                date_match = re.search(r'\b(\d{4}-\d{2}-\d{2}|\w+\s+\d{1,2},?\s+\d{4}|\d{1,2}/\d{1,2}/\d{4})', date_text)
                if date_match:
                    return date_match.group(1)

        return None

    def _extract_canada_risk_level(self, soup: BeautifulSoup, content: str) -> Optional[str]:
        # Canadian government uses specific advisory levels

        # Look for advisory level indicators
        advisory_elem = soup.find(class_=re.compile(r'advisory|alert|warning'))
        if advisory_elem:
            advisory_text = self._clean_text(advisory_elem.get_text())
            content = advisory_text + " " + content

        content_lower = content.lower()

        # Canadian-specific advisory patterns
        if any(phrase in content_lower for phrase in [
            'avoid all travel',
            'do not travel'
        ]):
            return 'Avoid All Travel'
        elif any(phrase in content_lower for phrase in [
            'avoid non-essential travel',
            'avoid non essential travel'
        ]):
            return 'Avoid Non-Essential Travel'
        elif any(phrase in content_lower for phrase in [
            'exercise a high degree of caution',
            'high degree of caution'
        ]):
            return 'Exercise High Degree of Caution'
        elif any(phrase in content_lower for phrase in [
            'exercise normal security precautions',
            'normal security precautions',
            'take normal security precautions'
        ]):
            return 'Exercise Normal Precautions'

        # Fallback to generic risk level extraction
        return self._extract_risk_level(content)

    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        metadata = {}

        # Extract any alert or warning sections
        alerts = []
        alert_elems = soup.find_all(class_=re.compile(r'alert|warning|panel-danger|panel-warning'))
        for alert in alert_elems:
            alert_text = self._clean_text(alert.get_text())
            if alert_text and len(alert_text) > 10:
                alerts.append(alert_text)

        if alerts:
            metadata['alerts'] = alerts

        # Extract embassy information
        embassy_elem = soup.find(text=re.compile(r'canadian embassy|canadian consulate|canadian high commission', re.IGNORECASE))
        if embassy_elem:
            metadata['embassy_info'] = self._clean_text(str(embassy_elem))

        # Extract health information
        health_section = soup.find(id=re.compile(r'health', re.IGNORECASE))
        if health_section:
            metadata['health_info'] = self._clean_text(health_section.get_text())

        # Extract entry requirements
        entry_elem = soup.find(text=re.compile(r'entry requirements|visa|passport', re.IGNORECASE))
        if entry_elem:
            metadata['entry_requirements'] = self._clean_text(str(entry_elem))

        # Extract safety and security information
        safety_section = soup.find(id=re.compile(r'safety|security', re.IGNORECASE))
        if safety_section:
            metadata['safety_info'] = self._clean_text(safety_section.get_text())

        return metadata