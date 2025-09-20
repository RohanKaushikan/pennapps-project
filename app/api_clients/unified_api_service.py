import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from concurrent.futures import ThreadPoolExecutor
import structlog
from pydantic import BaseModel

from .base_client import APIError, APIResponse
from .us_state_dept_client import USStateDeptAPIClient
from .uk_foreign_office_client import UKForeignOfficeAPIClient
from app.models.travel_advisory import TravelAdvisory

logger = structlog.get_logger(__name__)


class APISourceConfig(BaseModel):
    """Configuration for an API source."""
    name: str
    enabled: bool = True
    priority: int = 1  # Higher number = higher priority
    api_key: Optional[str] = None
    cache_ttl: int = 3600
    timeout: int = 30
    max_retries: int = 3


class UnifiedAPIResponse(BaseModel):
    """Unified response from multiple API sources."""
    success: bool
    data: List[Dict[str, Any]]
    errors: Dict[str, str] = {}
    sources_used: List[str] = []
    cache_hit: bool = False
    response_time_ms: float
    timestamp: datetime


class DataNormalizer:
    """Normalizes data from different API sources to a common format."""

    @staticmethod
    def normalize_travel_advisory(data: Dict[str, Any], source: str) -> Dict[str, Any]:
        """
        Normalize travel advisory data to a common format.

        Args:
            data: Raw data from API
            source: Source identifier

        Returns:
            Normalized data dictionary
        """
        try:
            # Common fields across all sources
            normalized = {
                'source': source,
                'country': data.get('country', ''),
                'title': data.get('title', ''),
                'content': data.get('content', ''),
                'risk_level': data.get('risk_level'),
                'last_updated': data.get('last_updated'),
                'source_url': data.get('source_url', ''),
                'scraped_at': data.get('scraped_at', datetime.utcnow().isoformat()),
                'metadata': data.get('metadata', {})
            }

            # Source-specific normalization
            if source == 'us_state_department':
                normalized = DataNormalizer._normalize_us_data(data, normalized)
            elif source == 'uk_foreign_office':
                normalized = DataNormalizer._normalize_uk_data(data, normalized)

            # Standardize risk level
            normalized['risk_level_standardized'] = DataNormalizer._standardize_risk_level(
                normalized['risk_level'], source
            )

            return normalized

        except Exception as e:
            logger.error("Error normalizing data", error=str(e), source=source, data=data)
            return {
                'source': source,
                'country': data.get('country', 'Unknown'),
                'title': 'Travel Advisory',
                'content': str(data),
                'risk_level': None,
                'risk_level_standardized': None,
                'last_updated': None,
                'source_url': '',
                'scraped_at': datetime.utcnow().isoformat(),
                'metadata': {'error': str(e)}
            }

    @staticmethod
    def _normalize_us_data(data: Dict[str, Any], normalized: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize US State Department specific data."""
        metadata = data.get('metadata', {})

        normalized.update({
            'risk_level_numeric': metadata.get('risk_level_numeric'),
            'emergency_contact': metadata.get('emergency_contact'),
            'entry_requirements': metadata.get('entry_requirements'),
        })

        return normalized

    @staticmethod
    def _normalize_uk_data(data: Dict[str, Any], normalized: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize UK Foreign Office specific data."""
        metadata = data.get('metadata', {})

        normalized.update({
            'summary': metadata.get('summary'),
            'alerts': metadata.get('alerts', []),
            'health_info': metadata.get('health_info'),
            'emergency_contact': metadata.get('emergency_contact'),
        })

        return normalized

    @staticmethod
    def _standardize_risk_level(risk_level: Optional[str], source: str) -> Optional[str]:
        """
        Standardize risk levels across different sources.

        Args:
            risk_level: Original risk level
            source: Source of the data

        Returns:
            Standardized risk level
        """
        if not risk_level:
            return None

        risk_lower = risk_level.lower()

        # Standardized risk levels
        if source == 'us_state_department':
            if 'level 4' in risk_lower or 'do not travel' in risk_lower:
                return 'AVOID_ALL_TRAVEL'
            elif 'level 3' in risk_lower or 'reconsider travel' in risk_lower:
                return 'RECONSIDER_TRAVEL'
            elif 'level 2' in risk_lower or 'increased caution' in risk_lower:
                return 'EXERCISE_CAUTION'
            elif 'level 1' in risk_lower or 'normal precautions' in risk_lower:
                return 'NORMAL_PRECAUTIONS'

        elif source == 'uk_foreign_office':
            if 'advise against all travel' in risk_lower:
                return 'AVOID_ALL_TRAVEL'
            elif 'advise against all but essential travel' in risk_lower:
                return 'RECONSIDER_TRAVEL'
            elif 'advise against travel to parts' in risk_lower:
                return 'EXERCISE_CAUTION'
            elif 'see travel advice' in risk_lower:
                return 'NORMAL_PRECAUTIONS'

        # If no mapping found, return original
        return risk_level


class UnifiedAPIService:
    """
    Unified service for accessing multiple government travel advisory APIs.

    Provides a single interface that abstracts different API formats and provides
    normalized, cached responses with fallback mechanisms.
    """

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url
        self.clients: Dict[str, Any] = {}
        self.source_configs: Dict[str, APISourceConfig] = {}
        self._setup_clients()

    def _setup_clients(self):
        """Set up API clients for different sources."""
        self.source_configs = {
            'us_state_department': APISourceConfig(
                name='US State Department',
                enabled=True,
                priority=3,
                cache_ttl=3600,
                timeout=30
            ),
            'uk_foreign_office': APISourceConfig(
                name='UK Foreign Office',
                enabled=True,
                priority=2,
                cache_ttl=3600,
                timeout=30
            ),
            # Future sources can be added here
            # 'canada_travel': APISourceConfig(...),
            # 'eu_travel_info': APISourceConfig(...),
        }

    async def initialize_clients(self, api_keys: Optional[Dict[str, str]] = None):
        """
        Initialize API clients with configuration.

        Args:
            api_keys: Dictionary mapping source names to API keys
        """
        api_keys = api_keys or {}

        try:
            # Initialize US State Department client
            if self.source_configs['us_state_department'].enabled:
                self.clients['us_state_department'] = USStateDeptAPIClient(
                    api_key=api_keys.get('us_state_department'),
                    redis_url=self.redis_url
                )

            # Initialize UK Foreign Office client
            if self.source_configs['uk_foreign_office'].enabled:
                self.clients['uk_foreign_office'] = UKForeignOfficeAPIClient(
                    api_key=api_keys.get('uk_foreign_office'),
                    redis_url=self.redis_url
                )

            logger.info("API clients initialized", clients=list(self.clients.keys()))

        except Exception as e:
            logger.error("Error initializing API clients", error=str(e))
            raise APIError(f"Failed to initialize API clients: {str(e)}")

    async def get_travel_advisories(
        self,
        country: Optional[str] = None,
        sources: Optional[List[str]] = None,
        use_cache: bool = True,
        fallback_on_error: bool = True
    ) -> UnifiedAPIResponse:
        """
        Get travel advisories from multiple sources.

        Args:
            country: Specific country (optional)
            sources: List of sources to use (optional, defaults to all enabled)
            use_cache: Whether to use cached responses
            fallback_on_error: Whether to continue with other sources if one fails

        Returns:
            Unified response with data from all sources
        """
        start_time = datetime.utcnow()
        sources_to_use = sources or [s for s, config in self.source_configs.items() if config.enabled]

        response = UnifiedAPIResponse(
            success=False,
            data=[],
            sources_used=[],
            response_time_ms=0,
            timestamp=start_time
        )

        # Collect tasks for concurrent execution
        tasks = []
        for source in sources_to_use:
            if source in self.clients:
                task = self._get_source_data(source, country, use_cache)
                tasks.append((source, task))

        if not tasks:
            response.errors['general'] = "No enabled API sources available"
            return response

        # Execute requests concurrently
        results = await self._execute_concurrent_requests(tasks, fallback_on_error)

        # Process results
        all_data = []
        successful_sources = []

        for source, result in results.items():
            if result['success']:
                # Normalize data from this source
                source_data = result['data']
                if isinstance(source_data, list):
                    for item in source_data:
                        normalized = DataNormalizer.normalize_travel_advisory(item, source)
                        all_data.append(normalized)
                else:
                    normalized = DataNormalizer.normalize_travel_advisory(source_data, source)
                    all_data.append(normalized)

                successful_sources.append(source)
                if result.get('cached'):
                    response.cache_hit = True
            else:
                response.errors[source] = result.get('error', 'Unknown error')

        # Sort data by source priority and country
        all_data.sort(key=lambda x: (
            -self.source_configs.get(x['source'], APISourceConfig(name='', priority=0)).priority,
            x.get('country', '')
        ))

        # Set response data
        response.success = len(successful_sources) > 0
        response.data = all_data
        response.sources_used = successful_sources

        # Calculate response time
        end_time = datetime.utcnow()
        response.response_time_ms = (end_time - start_time).total_seconds() * 1000

        logger.info(
            "Unified API request completed",
            country=country,
            sources_requested=sources_to_use,
            sources_successful=successful_sources,
            data_count=len(all_data),
            response_time_ms=response.response_time_ms
        )

        return response

    async def get_country_advisory(
        self,
        country: str,
        sources: Optional[List[str]] = None,
        prefer_source: Optional[str] = None
    ) -> UnifiedAPIResponse:
        """
        Get travel advisory for a specific country.

        Args:
            country: Country name
            sources: List of sources to query
            prefer_source: Preferred source (will be tried first)

        Returns:
            Unified response with country advisory data
        """
        # If preferred source specified, try it first
        if prefer_source and prefer_source in self.clients:
            try:
                response = await self.get_travel_advisories(
                    country=country,
                    sources=[prefer_source],
                    fallback_on_error=False
                )
                if response.success and response.data:
                    return response
            except Exception as e:
                logger.warning("Preferred source failed", source=prefer_source, error=str(e))

        # Try all sources
        return await self.get_travel_advisories(country=country, sources=sources)

    async def _get_source_data(
        self,
        source: str,
        country: Optional[str],
        use_cache: bool
    ) -> Dict[str, Any]:
        """Get data from a specific source."""
        try:
            client = self.clients[source]

            if country:
                data = await client.get_country_advisory(country)
                return {
                    'success': True,
                    'data': data if data else [],
                    'cached': False  # Individual clients handle caching
                }
            else:
                data = await client.get_travel_advisories()
                return {
                    'success': True,
                    'data': data,
                    'cached': False
                }

        except Exception as e:
            logger.warning("Error getting data from source", source=source, error=str(e))
            return {
                'success': False,
                'error': str(e),
                'data': []
            }

    async def _execute_concurrent_requests(
        self,
        tasks: List[tuple],
        fallback_on_error: bool
    ) -> Dict[str, Dict[str, Any]]:
        """Execute API requests concurrently."""
        results = {}

        try:
            # Execute all tasks concurrently
            task_results = await asyncio.gather(
                *[task for _, task in tasks],
                return_exceptions=True
            )

            # Process results
            for i, (source, _) in enumerate(tasks):
                result = task_results[i]

                if isinstance(result, Exception):
                    results[source] = {
                        'success': False,
                        'error': str(result),
                        'data': []
                    }
                else:
                    results[source] = result

        except Exception as e:
            logger.error("Error executing concurrent requests", error=str(e))
            # If concurrent execution fails, try sequential
            if fallback_on_error:
                for source, task in tasks:
                    try:
                        result = await task
                        results[source] = result
                    except Exception as task_error:
                        results[source] = {
                            'success': False,
                            'error': str(task_error),
                            'data': []
                        }

        return results

    async def health_check(self) -> Dict[str, bool]:
        """
        Check health of all API sources.

        Returns:
            Dictionary mapping source names to health status
        """
        health_status = {}

        for source, client in self.clients.items():
            try:
                is_healthy = await client.health_check()
                health_status[source] = is_healthy
            except Exception as e:
                logger.warning("Health check failed for source", source=source, error=str(e))
                health_status[source] = False

        return health_status

    async def get_source_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for each API source."""
        stats = {}

        for source, config in self.source_configs.items():
            client = self.clients.get(source)
            stats[source] = {
                'name': config.name,
                'enabled': config.enabled,
                'priority': config.priority,
                'client_available': client is not None,
                'circuit_breaker_state': getattr(client, 'circuit_breaker', {}).current_state if client else None,
            }

        return stats

    def configure_source(self, source: str, **kwargs):
        """
        Configure a specific source.

        Args:
            source: Source name
            **kwargs: Configuration parameters
        """
        if source in self.source_configs:
            config = self.source_configs[source]
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
                    logger.info("Source configuration updated", source=source, parameter=key, value=value)

    def enable_source(self, source: str):
        """Enable a specific source."""
        if source in self.source_configs:
            self.source_configs[source].enabled = True
            logger.info("Source enabled", source=source)

    def disable_source(self, source: str):
        """Disable a specific source."""
        if source in self.source_configs:
            self.source_configs[source].enabled = False
            logger.info("Source disabled", source=source)

    async def close(self):
        """Close all API clients."""
        for client in self.clients.values():
            try:
                await client.close()
            except Exception as e:
                logger.warning("Error closing client", error=str(e))

        self.clients.clear()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()