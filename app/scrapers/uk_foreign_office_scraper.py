import re
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, urlparse
import structlog
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, ScrapedContent, ScrapingConfig

logger = structlog.get_logger(__name__)


class UKForeignOfficeScraper(BaseScraper):
    def __init__(self):
        config = ScrapingConfig(
            base_url="https://www.gov.uk",
            rate_limit_delay=1.0,
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

        advisory_url = f"{self.config.base_url}/foreign-travel-advice/{country_slug}"

        response = await self._fetch_with_retry(advisory_url)
        if not response:
            return None

        content = self._parse_advisory_page(response.text, advisory_url)
        if content and self._validate_content(content):
            return content

        return None

    async def scrape_all_advisories(self) -> List[ScrapedContent]:
        advisories = []

        # Get the main travel advice page
        main_url = f"{self.config.base_url}/foreign-travel-advice"
        response = await self._fetch_with_retry(main_url)

        if not response:
            logger.error("Failed to fetch main travel advice page")
            return advisories

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all country links - UK gov uses specific patterns
        country_links = soup.find_all('a', href=re.compile(r'/foreign-travel-advice/[^/]+/?$'))

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
            title_elem = soup.find('h1', class_='gem-c-title__text')
            if not title_elem:
                title_elem = soup.find('h1') or soup.find('title')
            title = self._clean_text(title_elem.get_text()) if title_elem else "Travel Advice"

            # Extract country from title or URL
            country = self._extract_country_from_title(title) or self._extract_country_from_url(url)

            # Extract main content
            content_sections = []

            # UK gov.uk uses specific content structure
            main_content = soup.find('div', class_='govuk-grid-column-two-thirds')
            if not main_content:
                main_content = soup.find('main') or soup.find('div', {'id': 'content'})

            if main_content:
                # Remove navigation, related links, and other non-content elements
                for unwanted in main_content.find_all(['nav', 'footer', 'aside', 'script', 'style']):
                    unwanted.decompose()

                # Remove common gov.uk navigation elements
                for unwanted_class in ['gem-c-related-navigation', 'gem-c-contextual-sidebar', 'app-c-contents-list']:
                    for elem in main_content.find_all(class_=unwanted_class):
                        elem.decompose()

                # Extract summary if available
                summary_elem = soup.find('p', class_='gem-c-lead-paragraph')
                if summary_elem:
                    content_sections.append(self._clean_text(summary_elem.get_text()))

                # Extract advisory sections
                advisory_sections = main_content.find_all(['section', 'div'], class_=re.compile(r'gem-c-govspeak|govuk-'))
                for section in advisory_sections:
                    section_text = self._clean_text(section.get_text())
                    if section_text and len(section_text) > 20:
                        content_sections.append(section_text)

                # If no specific sections found, extract from all paragraphs
                if not content_sections:
                    for element in main_content.find_all(['p', 'div', 'section']):
                        text = self._clean_text(element.get_text())
                        if text and len(text) > 20:
                            content_sections.append(text)

            # Join all content
            full_content = '\n\n'.join(content_sections)

            # Extract last updated date
            last_updated = self._extract_last_updated(soup)

            # Extract risk level - UK uses different terminology
            risk_level = self._extract_uk_risk_level(soup, full_content)

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
        # Common mappings for UK Foreign Office URLs
        country_mappings = {
            'united states': 'usa',
            'united kingdom': 'uk',
            'south korea': 'south-korea',
            'north korea': 'north-korea',
            'saudi arabia': 'saudi-arabia',
            'south africa': 'south-africa',
            'new zealand': 'new-zealand',
            'sri lanka': 'sri-lanka',
            'costa rica': 'costa-rica',
            'puerto rico': 'puerto-rico',
            'czech republic': 'czech-republic',
            'dominican republic': 'dominican-republic',
            'el salvador': 'el-salvador',
            'ivory coast': 'cote-divoire',
            'burkina faso': 'burkina-faso',
            'bosnia and herzegovina': 'bosnia-and-herzegovina',
            'democratic republic of congo': 'democratic-republic-of-congo',
            'republic of congo': 'congo',
        }

        country_lower = country.lower().strip()

        # Check direct mapping first
        if country_lower in country_mappings:
            return country_mappings[country_lower]

        # Create slug with hyphens (UK gov style)
        slug = re.sub(r'[^a-zA-Z0-9\s]', '', country_lower)
        slug = re.sub(r'\s+', '-', slug.strip())

        return slug if slug else None

    def _extract_country_from_title(self, title: str) -> Optional[str]:
        # Extract country from UK Foreign Office title patterns
        patterns = [
            r'^(.+?)\s+travel\s+advice',
            r'^Travel\s+advice\s*[:\-]\s*(.+?)$',
            r'^Foreign\s+travel\s+advice\s*[:\-]\s*(.+?)$',
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
        match = re.search(r'/foreign-travel-advice/([^/]+)/?$', path)
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
            return link_text.strip()

        href = link.get('href', '')
        return self._extract_country_from_url(href)

    def _extract_last_updated(self, soup: BeautifulSoup) -> Optional[str]:
        # UK gov.uk uses specific date elements
        date_elem = soup.find('time', {'datetime': True})
        if date_elem:
            return date_elem.get('datetime') or date_elem.get_text()

        # Look for common date patterns in UK format
        date_patterns = [
            soup.find(text=re.compile(r'last updated|updated|published', re.IGNORECASE)),
            soup.find(attrs={'class': re.compile(r'date|time|updated', re.IGNORECASE)}),
        ]

        for pattern in date_patterns:
            if pattern:
                if hasattr(pattern, 'get_text'):
                    date_text = pattern.get_text()
                else:
                    date_text = str(pattern)

                # Extract date from text (UK format: DD Month YYYY)
                date_match = re.search(r'\b(\d{1,2}\s+\w+\s+\d{4}|\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})', date_text)
                if date_match:
                    return date_match.group(1)

        return None

    def _extract_uk_risk_level(self, soup: BeautifulSoup, content: str) -> Optional[str]:
        # UK Foreign Office uses different advisory language

        # Look for specific UK advisory alerts
        alert_elem = soup.find(class_=re.compile(r'alert|warning|advisory'))
        if alert_elem:
            alert_text = self._clean_text(alert_elem.get_text())
            content = alert_text + " " + content

        content_lower = content.lower()

        # UK-specific advisory patterns
        if any(phrase in content_lower for phrase in [
            'advise against all travel',
            'do not travel',
            'advise against all but essential travel'
        ]):
            return 'Advise Against All Travel'
        elif any(phrase in content_lower for phrase in [
            'advise against all but essential travel to parts',
            'advise against travel to parts'
        ]):
            return 'Advise Against Travel To Parts'
        elif any(phrase in content_lower for phrase in [
            'see our travel advice before travelling',
            'check the latest travel advice',
            'no travel restrictions'
        ]):
            return 'See Travel Advice'

        # Fallback to generic risk level extraction
        return self._extract_risk_level(content)

    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        metadata = {}

        # Extract summary from lead paragraph
        summary_elem = soup.find('p', class_='gem-c-lead-paragraph')
        if summary_elem:
            metadata['summary'] = self._clean_text(summary_elem.get_text())

        # Extract any alert boxes
        alerts = []
        alert_elems = soup.find_all(class_=re.compile(r'alert|warning|notice|highlight'))
        for alert in alert_elems:
            alert_text = self._clean_text(alert.get_text())
            if alert_text and len(alert_text) > 10:
                alerts.append(alert_text)

        if alerts:
            metadata['alerts'] = alerts

        # Extract emergency contact information
        contact_section = soup.find(text=re.compile(r'british embassy|british consulate|emergency', re.IGNORECASE))
        if contact_section:
            metadata['emergency_contact'] = self._clean_text(str(contact_section))

        # Extract any health warnings
        health_elem = soup.find(text=re.compile(r'health|medical|vaccination', re.IGNORECASE))
        if health_elem:
            metadata['health_info'] = self._clean_text(str(health_elem))

        return metadata