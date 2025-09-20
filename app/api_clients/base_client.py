import asyncio
import hashlib
import json
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from urllib.parse import urljoin, urlparse

import aioredis
import httpx
import structlog
from pydantic import BaseModel, Field
from pybreaker import CircuitBreaker
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = structlog.get_logger(__name__)


class APIError(Exception):
    """Base exception for API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}
        self.timestamp = datetime.utcnow()


class APIRateLimitError(APIError):
    """Raised when API rate limit is exceeded."""

    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class APIAuthenticationError(APIError):
    """Raised when API authentication fails."""
    pass


class APITemporaryError(APIError):
    """Raised for temporary API errors that should be retried."""
    pass


class APIResponse(BaseModel):
    """Standardized API response model."""

    status_code: int
    data: Dict[str, Any] = Field(default_factory=dict)
    headers: Dict[str, str] = Field(default_factory=dict)
    cached: bool = False
    cache_ttl: Optional[int] = None
    response_time_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AuthenticationConfig(BaseModel):
    """Configuration for API authentication."""

    auth_type: str  # 'api_key', 'oauth', 'basic', 'bearer', 'none'
    api_key: Optional[str] = None
    api_key_header: str = "X-API-Key"
    username: Optional[str] = None
    password: Optional[str] = None
    bearer_token: Optional[str] = None
    oauth_token: Optional[str] = None
    oauth_token_secret: Optional[str] = None


class CacheConfig(BaseModel):
    """Configuration for caching."""

    enabled: bool = True
    default_ttl: int = 3600  # 1 hour
    key_prefix: str = "api_cache"
    max_key_length: int = 250


class CircuitBreakerConfig(BaseModel):
    """Configuration for circuit breaker."""

    failure_threshold: int = 5
    recovery_timeout: int = 60
    expected_exception: type = APITemporaryError


class BaseAPIClient(ABC):
    """Base class for all API clients with common functionality."""

    def __init__(
        self,
        base_url: str,
        auth_config: Optional[AuthenticationConfig] = None,
        cache_config: Optional[CacheConfig] = None,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        redis_url: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        rate_limit_calls: int = 100,
        rate_limit_period: int = 3600
    ):
        self.base_url = base_url.rstrip('/')
        self.auth_config = auth_config or AuthenticationConfig(auth_type='none')
        self.cache_config = cache_config or CacheConfig()
        self.circuit_breaker_config = circuit_breaker_config or CircuitBreakerConfig()
        self.timeout = timeout
        self.max_retries = max_retries

        # Rate limiting
        self.rate_limit_calls = rate_limit_calls
        self.rate_limit_period = rate_limit_period
        self._rate_limit_window_start = time.time()
        self._rate_limit_calls_made = 0

        # HTTP client setup
        self._setup_http_client()

        # Circuit breaker setup
        self._setup_circuit_breaker()

        # Cache setup
        self.redis_client = None
        if redis_url and self.cache_config.enabled:
            asyncio.create_task(self._setup_redis(redis_url))

    def _setup_http_client(self):
        """Set up the HTTP client with authentication."""
        headers = {
            'User-Agent': 'TravelAdvisoryAPI/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

        # Add authentication headers
        if self.auth_config.auth_type == 'api_key' and self.auth_config.api_key:
            headers[self.auth_config.api_key_header] = self.auth_config.api_key
        elif self.auth_config.auth_type == 'bearer' and self.auth_config.bearer_token:
            headers['Authorization'] = f'Bearer {self.auth_config.bearer_token}'

        # Create auth object for basic auth
        auth = None
        if self.auth_config.auth_type == 'basic':
            auth = httpx.BasicAuth(
                self.auth_config.username,
                self.auth_config.password
            )

        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers=headers,
            auth=auth,
            follow_redirects=True
        )

    def _setup_circuit_breaker(self):
        """Set up circuit breaker for fault tolerance."""
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=self.circuit_breaker_config.failure_threshold,
            recovery_timeout=self.circuit_breaker_config.recovery_timeout,
            expected_exception=self.circuit_breaker_config.expected_exception
        )

    async def _setup_redis(self, redis_url: str):
        """Set up Redis connection for caching."""
        try:
            self.redis_client = aioredis.from_url(redis_url)
            await self.redis_client.ping()
            logger.info("Redis cache connection established", client=self.__class__.__name__)
        except Exception as e:
            logger.warning("Failed to connect to Redis cache", error=str(e), client=self.__class__.__name__)
            self.redis_client = None

    async def _check_rate_limit(self):
        """Check and enforce rate limiting."""
        current_time = time.time()

        # Reset window if period has passed
        if current_time - self._rate_limit_window_start >= self.rate_limit_period:
            self._rate_limit_window_start = current_time
            self._rate_limit_calls_made = 0

        # Check if we've exceeded rate limit
        if self._rate_limit_calls_made >= self.rate_limit_calls:
            wait_time = self.rate_limit_period - (current_time - self._rate_limit_window_start)
            if wait_time > 0:
                logger.warning(
                    "Rate limit exceeded, waiting",
                    client=self.__class__.__name__,
                    wait_time=wait_time
                )
                await asyncio.sleep(wait_time)
                # Reset after waiting
                self._rate_limit_window_start = time.time()
                self._rate_limit_calls_made = 0

        self._rate_limit_calls_made += 1

    def _generate_cache_key(self, method: str, url: str, params: Optional[Dict] = None) -> str:
        """Generate a cache key for the request."""
        key_data = {
            'method': method,
            'url': url,
            'params': params or {},
            'client': self.__class__.__name__
        }

        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        cache_key = f"{self.cache_config.key_prefix}:{key_hash}"

        # Ensure key length doesn't exceed Redis limits
        if len(cache_key) > self.cache_config.max_key_length:
            cache_key = cache_key[:self.cache_config.max_key_length]

        return cache_key

    async def _get_cached_response(self, cache_key: str) -> Optional[APIResponse]:
        """Get cached response if available."""
        if not self.redis_client or not self.cache_config.enabled:
            return None

        try:
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                response = APIResponse.parse_obj(data)
                response.cached = True

                logger.debug("Cache hit", cache_key=cache_key, client=self.__class__.__name__)
                return response
        except Exception as e:
            logger.warning("Error retrieving from cache", error=str(e), cache_key=cache_key)

        return None

    async def _cache_response(self, cache_key: str, response: APIResponse, ttl: Optional[int] = None):
        """Cache the API response."""
        if not self.redis_client or not self.cache_config.enabled:
            return

        try:
            ttl = ttl or self.cache_config.default_ttl
            response_data = response.dict()
            response_data['cached'] = False  # Store as non-cached

            await self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(response_data, default=str)
            )

            logger.debug("Response cached", cache_key=cache_key, ttl=ttl, client=self.__class__.__name__)
        except Exception as e:
            logger.warning("Error caching response", error=str(e), cache_key=cache_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((APITemporaryError, httpx.RequestError, httpx.TimeoutException))
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        cache_ttl: Optional[int] = None
    ) -> APIResponse:
        """Make HTTP request with retry logic and caching."""
        url = urljoin(self.base_url, endpoint.lstrip('/'))

        # Check rate limiting
        await self._check_rate_limit()

        # Check cache first
        cache_key = self._generate_cache_key(method, url, params)
        cached_response = await self._get_cached_response(cache_key)
        if cached_response:
            return cached_response

        # Prepare request
        request_headers = dict(self.http_client.headers)
        if headers:
            request_headers.update(headers)

        start_time = time.time()

        try:
            # Use circuit breaker
            async def make_http_request():
                response = await self.http_client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                    headers=request_headers
                )
                return response

            response = await self.circuit_breaker(make_http_request)
            response_time_ms = (time.time() - start_time) * 1000

            # Handle HTTP errors
            if response.status_code == 401:
                raise APIAuthenticationError(
                    "Authentication failed",
                    status_code=response.status_code,
                    response_data=response.json() if response.content else {}
                )
            elif response.status_code == 429:
                retry_after = response.headers.get('Retry-After')
                raise APIRateLimitError(
                    "Rate limit exceeded",
                    status_code=response.status_code,
                    retry_after=int(retry_after) if retry_after else None
                )
            elif 500 <= response.status_code < 600:
                raise APITemporaryError(
                    f"Server error: {response.status_code}",
                    status_code=response.status_code,
                    response_data=response.json() if response.content else {}
                )
            elif 400 <= response.status_code < 500:
                raise APIError(
                    f"Client error: {response.status_code}",
                    status_code=response.status_code,
                    response_data=response.json() if response.content else {}
                )

            # Parse response
            try:
                response_data = response.json() if response.content else {}
            except json.JSONDecodeError:
                response_data = {'raw_content': response.text}

            api_response = APIResponse(
                status_code=response.status_code,
                data=response_data,
                headers=dict(response.headers),
                response_time_ms=response_time_ms
            )

            # Cache successful responses
            if 200 <= response.status_code < 300:
                await self._cache_response(cache_key, api_response, cache_ttl)

            logger.info(
                "API request completed",
                method=method,
                url=url,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                client=self.__class__.__name__
            )

            return api_response

        except httpx.TimeoutException as e:
            logger.warning("API request timeout", url=url, client=self.__class__.__name__)
            raise APITemporaryError(f"Request timeout: {str(e)}")

        except httpx.RequestError as e:
            logger.warning("API request error", url=url, error=str(e), client=self.__class__.__name__)
            raise APITemporaryError(f"Request error: {str(e)}")

    async def get(self, endpoint: str, params: Optional[Dict] = None, **kwargs) -> APIResponse:
        """Make GET request."""
        return await self._make_request('GET', endpoint, params=params, **kwargs)

    async def post(self, endpoint: str, data: Optional[Dict] = None, **kwargs) -> APIResponse:
        """Make POST request."""
        return await self._make_request('POST', endpoint, data=data, **kwargs)

    async def put(self, endpoint: str, data: Optional[Dict] = None, **kwargs) -> APIResponse:
        """Make PUT request."""
        return await self._make_request('PUT', endpoint, data=data, **kwargs)

    async def delete(self, endpoint: str, **kwargs) -> APIResponse:
        """Make DELETE request."""
        return await self._make_request('DELETE', endpoint, **kwargs)

    @abstractmethod
    async def get_travel_advisories(self, country: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get travel advisories. Must be implemented by subclasses."""
        pass

    @abstractmethod
    async def get_country_advisory(self, country: str) -> Optional[Dict[str, Any]]:
        """Get travel advisory for specific country. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def normalize_advisory_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize raw API data to standard format. Must be implemented by subclasses."""
        pass

    async def health_check(self) -> bool:
        """Check if the API is healthy."""
        try:
            response = await self.get('/', cache_ttl=60)  # Cache health checks for 1 minute
            return 200 <= response.status_code < 400
        except Exception as e:
            logger.warning("API health check failed", error=str(e), client=self.__class__.__name__)
            return False

    async def close(self):
        """Close the HTTP client and Redis connection."""
        if self.http_client:
            await self.http_client.aclose()

        if self.redis_client:
            await self.redis_client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()