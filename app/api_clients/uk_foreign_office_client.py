import re
from datetime import datetime
from typing import Dict, List, Optional, Any

import structlog

from .base_client import BaseAPIClient, AuthenticationConfig, CacheConfig, APIError

logger = structlog.get_logger(__name__)


class UKForeignOfficeAPIClient(BaseAPIClient):
    """
    UK Foreign, Commonwealth & Development Office (FCDO) Travel Advice API client.

    Uses the official UK government API where available and structured data extraction.
    """

    def __init__(self, api_key: Optional[str] = None, redis_url: Optional[str] = None):
        # UK government APIs sometimes use API keys
        auth_config = AuthenticationConfig(
            auth_type='api_key' if api_key else 'none',
            api_key=api_key,
            api_key_header='Authorization'  # UK gov APIs often use Authorization header
        )

        cache_config = CacheConfig(
            enabled=True,
            default_ttl=3600,  # 1 hour cache
            key_prefix="uk_fcdo_api"
        )

        super().__init__(
            base_url="https://www.gov.uk",
            auth_config=auth_config,
            cache_config=cache_config,
            redis_url=redis_url,
            timeout=30,
            rate_limit_calls=120,  # UK gov sites are generally more permissive
            rate_limit_period=3600
        )

        # Alternative API endpoints
        self.api_endpoints = [
            "https://www.gov.uk/api/content",
            "https://www.gov.uk/api/search.json",
            "https://api.gov.uk/foreign-travel-advice"  # Potential future endpoint
        ]

    async def get_travel_advisories(self, country: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get travel advisories from UK FCDO.

        Args:
            country: Specific country name (optional)

        Returns:
            List of normalized travel advisory data
        """
        try:
            advisories = []

            if country:
                # Get specific country advisory
                advisory = await self.get_country_advisory(country)
                if advisory:
                    advisories.append(advisory)
            else:
                # Get all available advisories
                advisories = await self._get_all_advisories()

            logger.info(
                "Retrieved travel advisories",
                count=len(advisories),
                country=country,
                client=self.__class__.__name__
            )

            return advisories

        except Exception as e:
            logger.error(
                "Error retrieving travel advisories",
                error=str(e),
                country=country,
                client=self.__class__.__name__
            )
            raise APIError(f"Failed to retrieve travel advisories: {str(e)}")

    async def get_country_advisory(self, country: str) -> Optional[Dict[str, Any]]:
        """
        Get travel advisory for a specific country.

        Args:
            country: Country name

        Returns:
            Normalized travel advisory data or None if not found
        """
        try:
            country_lower = country.lower().strip()

            # Try different endpoints and data sources
            advisory_data = None

            # Method 1: Try GOV.UK Content API
            advisory_data = await self._get_content_api_advisory(country_lower)

            # Method 2: Try search API
            if not advisory_data:
                advisory_data = await self._get_search_api_advisory(country_lower)

            # Method 3: Try direct page access
            if not advisory_data:
                advisory_data = await self._get_direct_page_advisory(country_lower)

            if advisory_data:
                normalized_data = self.normalize_advisory_data(advisory_data)
                logger.info(
                    "Retrieved country advisory",
                    country=country,
                    risk_level=normalized_data.get('risk_level'),
                    client=self.__class__.__name__
                )
                return normalized_data

            logger.warning("No advisory found for country", country=country, client=self.__class__.__name__)
            return None

        except Exception as e:
            logger.error(
                "Error retrieving country advisory",
                error=str(e),
                country=country,
                client=self.__class__.__name__
            )
            return None

    async def _get_content_api_advisory(self, country: str) -> Optional[Dict[str, Any]]:
        """Try to get advisory from GOV.UK Content API."""
        try:
            country_slug = self._country_to_slug(country)
            if not country_slug:
                return None

            # Try GOV.UK Content API
            endpoint = f"/api/content/foreign-travel-advice/{country_slug}"

            response = await self.get(endpoint, cache_ttl=3600)
            if response.status_code == 200 and response.data:
                return {
                    'source': 'content_api',
                    'data': response.data,
                    'url': f"{self.base_url}/foreign-travel-advice/{country_slug}",
                    'country': country
                }

            return None

        except Exception as e:
            logger.debug("Content API advisory not available", country=country, error=str(e))
            return None

    async def _get_search_api_advisory(self, country: str) -> Optional[Dict[str, Any]]:
        """Try to get advisory from GOV.UK Search API."""
        try:
            # Search for travel advice pages
            search_params = {
                'q': f"foreign travel advice {country}",
                'filter_format': 'travel_advice',
                'count': 5
            }

            response = await self.get("/api/search.json", params=search_params, cache_ttl=1800)
            if response.status_code == 200 and response.data:
                results = response.data.get('results', [])

                # Find the most relevant result
                for result in results:
                    if self._is_relevant_travel_advice(result, country):
                        # Get detailed content for this result
                        content_url = result.get('link', '')
                        if content_url.startswith('/'):
                            content_url = content_url[1:]  # Remove leading slash

                        detailed_data = await self._get_detailed_content(content_url)
                        if detailed_data:
                            return {
                                'source': 'search_api',
                                'data': detailed_data,
                                'url': f"{self.base_url}/{content_url}",
                                'country': country,
                                'search_result': result
                            }

            return None

        except Exception as e:
            logger.debug("Search API advisory not available", country=country, error=str(e))
            return None

    async def _get_direct_page_advisory(self, country: str) -> Optional[Dict[str, Any]]:
        """Try to get advisory by accessing the page directly."""
        try:
            country_slug = self._country_to_slug(country)
            if not country_slug:
                return None

            # Try direct page access
            endpoint = f"/foreign-travel-advice/{country_slug}"

            response = await self.get(endpoint, cache_ttl=3600)
            if response.status_code == 200:
                return {
                    'source': 'direct_page',
                    'data': response.data,
                    'url': f"{self.base_url}{endpoint}",
                    'country': country
                }

            return None

        except Exception as e:
            logger.debug("Direct page advisory not available", country=country, error=str(e))
            return None

    async def _get_detailed_content(self, content_path: str) -> Optional[Dict[str, Any]]:
        """Get detailed content from a content path."""
        try:
            # Try Content API first
            api_endpoint = f"/api/content/{content_path}"
            response = await self.get(api_endpoint, cache_ttl=3600)

            if response.status_code == 200 and response.data:
                return response.data

            return None

        except Exception as e:
            logger.debug("Error getting detailed content", path=content_path, error=str(e))
            return None

    async def _get_all_advisories(self) -> List[Dict[str, Any]]:
        """Get all available travel advisories."""
        try:
            advisories = []

            # Method 1: Use search API to find all travel advice pages
            search_params = {
                'q': 'foreign travel advice',
                'filter_format': 'travel_advice',
                'count': 100,  # Get up to 100 results
                'order': 'title'
            }

            response = await self.get("/api/search.json", params=search_params, cache_ttl=1800)
            if response.status_code == 200 and response.data:
                results = response.data.get('results', [])

                for result in results:
                    try:
                        country = self._extract_country_from_result(result)
                        if country:
                            advisory = await self.get_country_advisory(country)
                            if advisory:
                                advisories.append(advisory)
                    except Exception as e:
                        logger.debug("Error processing search result", result=result, error=str(e))

            # Method 2: If search API doesn't work, try known countries
            if not advisories:
                advisories = await self._get_advisories_for_known_countries()

            return advisories

        except Exception as e:
            logger.error("Error getting all advisories", error=str(e))
            return []

    async def _get_advisories_for_known_countries(self) -> List[Dict[str, Any]]:
        """Get advisories for known countries."""
        advisories = []

        # Major countries that typically have travel advice
        major_countries = [
            'afghanistan', 'albania', 'algeria', 'argentina', 'australia',
            'austria', 'bangladesh', 'belgium', 'brazil', 'canada',
            'china', 'egypt', 'france', 'germany', 'india',
            'iran', 'iraq', 'ireland', 'israel', 'italy',
            'japan', 'jordan', 'kenya', 'libya', 'mexico',
            'morocco', 'netherlands', 'pakistan', 'russia', 'saudi-arabia',
            'south-africa', 'spain', 'syria', 'thailand', 'turkey',
            'ukraine', 'united-states', 'venezuela'
        ]

        for country in major_countries:
            try:
                advisory = await self.get_country_advisory(country)
                if advisory:
                    advisories.append(advisory)
            except Exception as e:
                logger.debug("Error getting advisory for country", country=country, error=str(e))

        return advisories

    def _is_relevant_travel_advice(self, result: Dict[str, Any], country: str) -> bool:
        """Check if search result is relevant travel advice for the country."""
        title = result.get('title', '').lower()
        link = result.get('link', '').lower()
        country_lower = country.lower()

        # Check if country name is in title or link
        return (country_lower in title or
                country_lower in link or
                self._country_to_slug(country) in link)

    def _extract_country_from_result(self, result: Dict[str, Any]) -> Optional[str]:
        """Extract country name from search result."""
        title = result.get('title', '')
        link = result.get('link', '')

        # Extract from title (e.g., "France travel advice")
        title_match = re.search(r'^(.+?)\s+travel\s+advice', title, re.IGNORECASE)
        if title_match:
            return title_match.group(1).strip()

        # Extract from link (e.g., "/foreign-travel-advice/france")
        link_match = re.search(r'/foreign-travel-advice/([^/]+)', link)
        if link_match:
            slug = link_match.group(1)
            return self._slug_to_country(slug)

        return None

    def _country_to_slug(self, country: str) -> Optional[str]:
        """Convert country name to UK government URL slug format."""
        if not country:
            return None

        # Common mappings for UK government URLs
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

    def _slug_to_country(self, slug: str) -> str:
        """Convert URL slug to country name."""
        if not slug:
            return ""

        # Reverse common mappings
        slug_mappings = {
            'usa': 'United States',
            'uk': 'United Kingdom',
            'south-korea': 'South Korea',
            'north-korea': 'North Korea',
            'saudi-arabia': 'Saudi Arabia',
            'south-africa': 'South Africa',
            'new-zealand': 'New Zealand',
            'sri-lanka': 'Sri Lanka',
            'costa-rica': 'Costa Rica',
            'czech-republic': 'Czech Republic',
            'dominican-republic': 'Dominican Republic',
            'el-salvador': 'El Salvador',
            'cote-divoire': 'Ivory Coast',
            'burkina-faso': 'Burkina Faso',
            'bosnia-and-herzegovina': 'Bosnia and Herzegovina',
            'democratic-republic-of-congo': 'Democratic Republic of Congo',
        }

        if slug in slug_mappings:
            return slug_mappings[slug]

        # Convert slug back to readable name
        return slug.replace('-', ' ').title()

    def normalize_advisory_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize UK FCDO advisory data to standard format.

        Args:
            raw_data: Raw advisory data from API

        Returns:
            Normalized advisory data
        """
        try:
            data = raw_data.get('data', {})
            source_url = raw_data.get('url', f"{self.base_url}/foreign-travel-advice")

            # Extract basic information
            country = raw_data.get('country', '')
            title = self._extract_title(data)

            # Extract risk level (UK uses different terminology)
            risk_level = self._extract_uk_risk_level(data)

            # Extract content
            content = self._extract_content(data)

            # Extract last updated date
            last_updated = self._extract_last_updated(data)

            # Extract additional metadata
            metadata = {
                'source': 'uk_foreign_office',
                'source_type': raw_data.get('source', 'api'),
                'api_response': data,
                'summary': self._extract_summary(data),
                'alerts': self._extract_alerts(data),
                'health_info': self._extract_health_info(data),
                'emergency_contact': self._extract_emergency_contact(data),
            }

            normalized_data = {
                'country': country.title(),
                'title': title,
                'content': content,
                'risk_level': risk_level,
                'last_updated': last_updated,
                'source_url': source_url,
                'metadata': metadata,
                'scraped_at': datetime.utcnow().isoformat(),
            }

            return normalized_data

        except Exception as e:
            logger.error("Error normalizing advisory data", error=str(e), raw_data=raw_data)
            # Return minimal normalized data
            return {
                'country': raw_data.get('country', 'Unknown'),
                'title': 'Travel Advice',
                'content': str(raw_data),
                'risk_level': None,
                'last_updated': None,
                'source_url': raw_data.get('url', ''),
                'metadata': {'source': 'uk_foreign_office', 'error': str(e)},
                'scraped_at': datetime.utcnow().isoformat(),
            }

    def _extract_title(self, data: Dict[str, Any]) -> str:
        """Extract title from advisory data."""
        title_fields = ['title', 'name', 'display_name']

        for field in title_fields:
            if field in data and data[field]:
                return str(data[field])

        return "Travel Advice"

    def _extract_uk_risk_level(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract UK-specific risk level from advisory data."""
        # Look for UK-specific advisory language
        content_text = str(data).lower()

        # UK Foreign Office uses specific phrases
        if 'advise against all travel' in content_text:
            return 'Advise Against All Travel'
        elif 'advise against all but essential travel' in content_text:
            return 'Advise Against All But Essential Travel'
        elif 'advise against travel to parts' in content_text:
            return 'Advise Against Travel To Parts'
        elif 'see our travel advice before travelling' in content_text:
            return 'See Travel Advice Before Travelling'

        # Look for specific fields
        risk_fields = ['advice_level', 'warning_level', 'status']
        for field in risk_fields:
            if field in data and data[field]:
                return str(data[field])

        return None

    def _extract_content(self, data: Dict[str, Any]) -> str:
        """Extract content from advisory data."""
        # UK gov.uk uses specific content structures
        content_parts = []

        # Look for structured content
        if 'parts' in data:
            parts = data['parts']
            if isinstance(parts, list):
                for part in parts:
                    if isinstance(part, dict) and 'body' in part:
                        content_parts.append(str(part['body']))

        # Look for description/summary
        if 'description' in data:
            content_parts.append(str(data['description']))

        # Look for details
        if 'details' in data:
            details = data['details']
            if isinstance(details, dict):
                for key, value in details.items():
                    if isinstance(value, str) and len(value.strip()) > 20:
                        content_parts.append(f"{key}: {value}")

        # If no structured content, combine available text fields
        if not content_parts:
            text_fields = ['body', 'summary', 'content', 'text']
            for field in text_fields:
                if field in data and isinstance(data[field], str):
                    content_parts.append(data[field])

        return '\n\n'.join(content_parts) if content_parts else str(data)

    def _extract_summary(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract summary from advisory data."""
        summary_fields = ['description', 'summary', 'excerpt']

        for field in summary_fields:
            if field in data and data[field]:
                return str(data[field])

        return None

    def _extract_alerts(self, data: Dict[str, Any]) -> List[str]:
        """Extract alert messages from advisory data."""
        alerts = []

        # Look for alerts in various structures
        if 'alerts' in data:
            alert_data = data['alerts']
            if isinstance(alert_data, list):
                alerts.extend([str(alert) for alert in alert_data])
            elif isinstance(alert_data, str):
                alerts.append(alert_data)

        return alerts

    def _extract_health_info(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract health information from advisory data."""
        health_fields = ['health', 'health_info', 'medical']

        for field in health_fields:
            if field in data and data[field]:
                return str(data[field])

        return None

    def _extract_emergency_contact(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract emergency contact information."""
        contact_fields = ['emergency_contact', 'british_embassy', 'consulate', 'contact']

        for field in contact_fields:
            if field in data and data[field]:
                return str(data[field])

        return None

    def _extract_last_updated(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract last updated date from advisory data."""
        date_fields = ['updated_at', 'first_published_at', 'public_updated_at', 'last_updated']

        for field in date_fields:
            if field in data and data[field]:
                return str(data[field])

        return None

    async def health_check(self) -> bool:
        """Check if UK Foreign Office API/website is accessible."""
        try:
            # Try main foreign travel advice page
            response = await self.get("/foreign-travel-advice", cache_ttl=300)
            return 200 <= response.status_code < 400
        except Exception:
            return False