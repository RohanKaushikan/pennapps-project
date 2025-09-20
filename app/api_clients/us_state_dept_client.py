import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import quote

import structlog

from .base_client import BaseAPIClient, AuthenticationConfig, CacheConfig, APIError

logger = structlog.get_logger(__name__)


class USStateDeptAPIClient(BaseAPIClient):
    """
    US State Department Travel Advisories API client.

    Note: The State Department doesn't have a comprehensive public API for travel advisories,
    so this client combines official endpoints where available and structured data extraction.
    """

    def __init__(self, api_key: Optional[str] = None, redis_url: Optional[str] = None):
        # US State Department uses various endpoints and data sources
        auth_config = AuthenticationConfig(
            auth_type='api_key' if api_key else 'none',
            api_key=api_key,
            api_key_header='X-API-Key'
        )

        cache_config = CacheConfig(
            enabled=True,
            default_ttl=3600,  # 1 hour cache for travel advisories
            key_prefix="us_state_dept_api"
        )

        super().__init__(
            base_url="https://travel.state.gov",
            auth_config=auth_config,
            cache_config=cache_config,
            redis_url=redis_url,
            timeout=30,
            rate_limit_calls=60,  # Conservative rate limiting
            rate_limit_period=3600
        )

        # Country code mapping for API endpoints
        self.country_code_map = self._load_country_codes()

    def _load_country_codes(self) -> Dict[str, str]:
        """Load country name to code mappings."""
        # This would typically be loaded from a more comprehensive source
        return {
            'afghanistan': 'af',
            'albania': 'al',
            'algeria': 'dz',
            'argentina': 'ar',
            'australia': 'au',
            'austria': 'at',
            'belgium': 'be',
            'brazil': 'br',
            'canada': 'ca',
            'china': 'cn',
            'france': 'fr',
            'germany': 'de',
            'india': 'in',
            'italy': 'it',
            'japan': 'jp',
            'mexico': 'mx',
            'russia': 'ru',
            'spain': 'es',
            'turkey': 'tr',
            'united kingdom': 'gb',
            'ukraine': 'ua',
            # Add more mappings as needed
        }

    async def get_travel_advisories(self, country: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get travel advisories from US State Department.

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

            # Method 1: Try structured data endpoint (if available)
            advisory_data = await self._get_structured_advisory(country_lower)

            # Method 2: Try travel advisories JSON feed (if available)
            if not advisory_data:
                advisory_data = await self._get_json_feed_advisory(country_lower)

            # Method 3: Extract from travel advisory page
            if not advisory_data:
                advisory_data = await self._extract_from_page(country_lower)

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

    async def _get_structured_advisory(self, country: str) -> Optional[Dict[str, Any]]:
        """Try to get advisory from structured data endpoint."""
        try:
            country_code = self.country_code_map.get(country)
            if not country_code:
                return None

            # Try various structured data endpoints
            endpoints = [
                f"/api/travel-advisories/{country_code}",
                f"/content/passports/en/alertswarnings/{country_code}.html",
                f"/content/travel/en/traveladvisories/traveladvisories/{self._country_to_slug(country)}.html"
            ]

            for endpoint in endpoints:
                try:
                    response = await self.get(endpoint, cache_ttl=3600)
                    if response.status_code == 200 and response.data:
                        return {
                            'source': 'structured_api',
                            'data': response.data,
                            'url': f"{self.base_url}{endpoint}",
                            'country': country
                        }
                except Exception:
                    continue

            return None

        except Exception as e:
            logger.debug("Structured advisory not available", country=country, error=str(e))
            return None

    async def _get_json_feed_advisory(self, country: str) -> Optional[Dict[str, Any]]:
        """Try to get advisory from JSON feed."""
        try:
            # Some State Department endpoints provide JSON feeds
            endpoints = [
                "/content/travel/en/traveladvisories.json",
                "/api/travel-advisories.json",
                f"/content/travel/en/traveladvisories/{self._country_to_slug(country)}.json"
            ]

            for endpoint in endpoints:
                try:
                    response = await self.get(endpoint, cache_ttl=1800)  # 30 min cache
                    if response.status_code == 200 and response.data:
                        # Parse JSON feed for country data
                        advisory_data = self._parse_json_feed(response.data, country)
                        if advisory_data:
                            return {
                                'source': 'json_feed',
                                'data': advisory_data,
                                'url': f"{self.base_url}{endpoint}",
                                'country': country
                            }
                except Exception:
                    continue

            return None

        except Exception as e:
            logger.debug("JSON feed advisory not available", country=country, error=str(e))
            return None

    async def _extract_from_page(self, country: str) -> Optional[Dict[str, Any]]:
        """Extract advisory data from HTML page."""
        try:
            country_slug = self._country_to_slug(country)
            if not country_slug:
                return None

            # Try to get the travel advisory page
            endpoint = f"/content/travel/en/traveladvisories/traveladvisories/{country_slug}.html"

            response = await self.get(endpoint, cache_ttl=3600)
            if response.status_code != 200:
                return None

            # If we got HTML content, we'd need to parse it
            # For now, return the raw data for processing by the scraper
            return {
                'source': 'html_page',
                'data': response.data,
                'url': f"{self.base_url}{endpoint}",
                'country': country
            }

        except Exception as e:
            logger.debug("Page extraction failed", country=country, error=str(e))
            return None

    async def _get_all_advisories(self) -> List[Dict[str, Any]]:
        """Get all available travel advisories."""
        try:
            advisories = []

            # Try to get advisory list from various endpoints
            endpoints = [
                "/content/travel/en/traveladvisories.json",
                "/api/travel-advisories",
                "/content/travel/en/traveladvisories/traveladvisories.html"
            ]

            for endpoint in endpoints:
                try:
                    response = await self.get(endpoint, cache_ttl=1800)
                    if response.status_code == 200 and response.data:
                        parsed_advisories = self._parse_advisories_list(response.data)
                        advisories.extend(parsed_advisories)
                        break  # Use first successful endpoint
                except Exception:
                    continue

            # If no structured data available, use known countries
            if not advisories:
                advisories = await self._get_advisories_for_known_countries()

            return advisories

        except Exception as e:
            logger.error("Error getting all advisories", error=str(e))
            return []

    async def _get_advisories_for_known_countries(self) -> List[Dict[str, Any]]:
        """Get advisories for known countries when no list endpoint available."""
        advisories = []

        # Get advisories for major countries
        major_countries = [
            'china', 'russia', 'iran', 'afghanistan', 'syria', 'iraq',
            'mexico', 'france', 'germany', 'united kingdom', 'canada',
            'australia', 'japan', 'india', 'brazil', 'turkey'
        ]

        for country in major_countries:
            try:
                advisory = await self.get_country_advisory(country)
                if advisory:
                    advisories.append(advisory)
            except Exception as e:
                logger.debug("Error getting advisory for country", country=country, error=str(e))

        return advisories

    def _parse_json_feed(self, json_data: Dict[str, Any], country: str) -> Optional[Dict[str, Any]]:
        """Parse JSON feed data for specific country."""
        try:
            # Handle different JSON feed structures
            if isinstance(json_data, dict):
                # Look for country data in various structures
                advisories = json_data.get('advisories', [])
                if isinstance(advisories, list):
                    for advisory in advisories:
                        if self._matches_country(advisory, country):
                            return advisory

                # Check if this is a single country advisory
                if self._matches_country(json_data, country):
                    return json_data

            return None

        except Exception as e:
            logger.debug("Error parsing JSON feed", error=str(e))
            return None

    def _parse_advisories_list(self, data: Any) -> List[Dict[str, Any]]:
        """Parse list of advisories from various data formats."""
        try:
            advisories = []

            if isinstance(data, dict):
                # Handle different response structures
                if 'advisories' in data:
                    advisories_data = data['advisories']
                elif 'data' in data:
                    advisories_data = data['data']
                else:
                    advisories_data = [data]
            elif isinstance(data, list):
                advisories_data = data
            else:
                return []

            for item in advisories_data:
                if isinstance(item, dict):
                    normalized = self.normalize_advisory_data({
                        'source': 'api_list',
                        'data': item,
                        'url': self.base_url
                    })
                    advisories.append(normalized)

            return advisories

        except Exception as e:
            logger.debug("Error parsing advisories list", error=str(e))
            return []

    def _matches_country(self, advisory_data: Dict[str, Any], country: str) -> bool:
        """Check if advisory data matches the specified country."""
        country_lower = country.lower()

        # Check various fields that might contain country name
        fields_to_check = ['country', 'name', 'title', 'location', 'country_name']

        for field in fields_to_check:
            if field in advisory_data:
                value = str(advisory_data[field]).lower()
                if country_lower in value or value in country_lower:
                    return True

        return False

    def _country_to_slug(self, country: str) -> Optional[str]:
        """Convert country name to URL slug format."""
        if not country:
            return None

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

    def normalize_advisory_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize US State Department advisory data to standard format.

        Args:
            raw_data: Raw advisory data from API

        Returns:
            Normalized advisory data
        """
        try:
            data = raw_data.get('data', {})
            source_url = raw_data.get('url', f"{self.base_url}/travel-advisories")

            # Extract basic information
            country = raw_data.get('country', '')
            title = data.get('title', f"Travel Advisory - {country}")

            # Extract risk level (US uses 1-4 level system)
            risk_level = self._extract_risk_level(data)

            # Extract content
            content = self._extract_content(data)

            # Extract last updated date
            last_updated = self._extract_last_updated(data)

            # Extract additional metadata
            metadata = {
                'source': 'us_state_department',
                'source_type': raw_data.get('source', 'api'),
                'api_response': data,
                'risk_level_numeric': self._extract_numeric_risk_level(risk_level),
                'emergency_contact': self._extract_emergency_contact(data),
                'entry_requirements': self._extract_entry_requirements(data),
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
                'title': 'Travel Advisory',
                'content': str(raw_data),
                'risk_level': None,
                'last_updated': None,
                'source_url': raw_data.get('url', ''),
                'metadata': {'source': 'us_state_department', 'error': str(e)},
                'scraped_at': datetime.utcnow().isoformat(),
            }

    def _extract_risk_level(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract risk level from advisory data."""
        # Look for risk level in various formats
        risk_fields = ['level', 'advisory_level', 'risk_level', 'warning_level']

        for field in risk_fields:
            if field in data:
                level = data[field]
                if isinstance(level, (int, str)):
                    return self._normalize_risk_level(str(level))

        # Look in text content for level indicators
        text_fields = ['content', 'description', 'summary', 'advisory']
        for field in text_fields:
            if field in data:
                text = str(data[field]).lower()
                if 'level 4' in text or 'do not travel' in text:
                    return 'Level 4 - Do Not Travel'
                elif 'level 3' in text or 'reconsider travel' in text:
                    return 'Level 3 - Reconsider Travel'
                elif 'level 2' in text or 'exercise increased caution' in text:
                    return 'Level 2 - Exercise Increased Caution'
                elif 'level 1' in text or 'exercise normal precautions' in text:
                    return 'Level 1 - Exercise Normal Precautions'

        return None

    def _normalize_risk_level(self, level: str) -> str:
        """Normalize risk level to standard format."""
        level_lower = level.lower().strip()

        level_map = {
            '1': 'Level 1 - Exercise Normal Precautions',
            '2': 'Level 2 - Exercise Increased Caution',
            '3': 'Level 3 - Reconsider Travel',
            '4': 'Level 4 - Do Not Travel',
            'level 1': 'Level 1 - Exercise Normal Precautions',
            'level 2': 'Level 2 - Exercise Increased Caution',
            'level 3': 'Level 3 - Reconsider Travel',
            'level 4': 'Level 4 - Do Not Travel',
        }

        return level_map.get(level_lower, level)

    def _extract_numeric_risk_level(self, risk_level: Optional[str]) -> Optional[int]:
        """Extract numeric risk level (1-4)."""
        if not risk_level:
            return None

        if 'level 1' in risk_level.lower():
            return 1
        elif 'level 2' in risk_level.lower():
            return 2
        elif 'level 3' in risk_level.lower():
            return 3
        elif 'level 4' in risk_level.lower():
            return 4

        return None

    def _extract_content(self, data: Dict[str, Any]) -> str:
        """Extract content from advisory data."""
        content_fields = ['content', 'description', 'advisory', 'summary', 'text']

        for field in content_fields:
            if field in data and data[field]:
                content = str(data[field])
                if len(content.strip()) > 20:  # Meaningful content
                    return content.strip()

        # If no specific content field, combine available fields
        combined_content = []
        for key, value in data.items():
            if isinstance(value, str) and len(value.strip()) > 20:
                combined_content.append(f"{key}: {value}")

        return '\n\n'.join(combined_content) if combined_content else str(data)

    def _extract_last_updated(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract last updated date from advisory data."""
        date_fields = ['last_updated', 'updated', 'date_updated', 'modified', 'published']

        for field in date_fields:
            if field in data and data[field]:
                return str(data[field])

        return None

    def _extract_emergency_contact(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract emergency contact information."""
        contact_fields = ['emergency_contact', 'embassy', 'consulate', 'contact']

        for field in contact_fields:
            if field in data and data[field]:
                return str(data[field])

        return None

    def _extract_entry_requirements(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract entry requirements information."""
        entry_fields = ['entry_requirements', 'visa', 'passport', 'requirements']

        for field in entry_fields:
            if field in data and data[field]:
                return str(data[field])

        return None

    async def health_check(self) -> bool:
        """Check if US State Department API/website is accessible."""
        try:
            # Try main travel advisories page
            response = await self.get("/content/travel/en/traveladvisories", cache_ttl=300)
            return 200 <= response.status_code < 400
        except Exception:
            return False