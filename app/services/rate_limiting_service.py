import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_session
from app.models.scraping_job import RateLimitTracker

logger = structlog.get_logger(__name__)


class RateLimitingService:
    """Service for managing and enforcing rate limits across scraping sources."""

    def __init__(self):
        self.source_configs = {
            'us_state_dept': {
                'requests_per_hour': 60,
                'burst_limit': 10,  # Allow burst of 10 requests
                'min_delay_seconds': 1.5,
                'respectful_hours': (9, 17),  # 9 AM to 5 PM EST (be extra respectful)
            },
            'uk_foreign_office': {
                'requests_per_hour': 120,
                'burst_limit': 15,
                'min_delay_seconds': 1.0,
                'respectful_hours': (9, 17),  # 9 AM to 5 PM GMT
            },
            'canada_travel': {
                'requests_per_hour': 100,
                'burst_limit': 12,
                'min_delay_seconds': 1.2,
                'respectful_hours': (9, 17),  # 9 AM to 5 PM EST/PST
            }
        }

        # In-memory tracking for burst limiting
        self._request_timestamps: Dict[str, list] = {}
        self._last_request_time: Dict[str, float] = {}

    async def can_make_request(self, source: str) -> Tuple[bool, Optional[float]]:
        """
        Check if a request can be made for the given source.

        Args:
            source: Source name to check

        Returns:
            Tuple of (can_make_request, delay_seconds)
            If can_make_request is False, delay_seconds indicates how long to wait
        """
        if source not in self.source_configs:
            logger.warning("Unknown source for rate limiting", source=source)
            return True, None

        config = self.source_configs[source]

        # Check hourly limit
        async with get_session() as session:
            hourly_allowed, wait_time = await self._check_hourly_limit(session, source, config)
            if not hourly_allowed:
                return False, wait_time

        # Check burst limit
        burst_allowed, burst_wait = self._check_burst_limit(source, config)
        if not burst_allowed:
            return False, burst_wait

        # Check minimum delay
        min_delay_ok, min_wait = self._check_minimum_delay(source, config)
        if not min_delay_ok:
            return False, min_wait

        # Check if we're in respectful hours (be extra careful during business hours)
        respectful_delay = self._get_respectful_delay(source, config)
        if respectful_delay > 0:
            return False, respectful_delay

        return True, None

    async def record_request(self, source: str, response_time_ms: Optional[float] = None):
        """
        Record that a request was made for rate limiting tracking.

        Args:
            source: Source name
            response_time_ms: Response time in milliseconds (optional)
        """
        now = time.time()
        current_time = datetime.utcnow()

        # Update in-memory tracking
        if source not in self._request_timestamps:
            self._request_timestamps[source] = []

        self._request_timestamps[source].append(now)
        self._last_request_time[source] = now

        # Clean old timestamps (keep only last hour)
        hour_ago = now - 3600
        self._request_timestamps[source] = [
            ts for ts in self._request_timestamps[source] if ts > hour_ago
        ]

        # Update database tracking
        async with get_session() as session:
            await self._update_database_tracking(session, source, response_time_ms)

    async def _check_hourly_limit(
        self,
        session: AsyncSession,
        source: str,
        config: Dict
    ) -> Tuple[bool, Optional[float]]:
        """Check if hourly rate limit allows the request."""
        now = datetime.utcnow()
        window_start = now.replace(minute=0, second=0, microsecond=0)

        # Get or create rate limit tracker
        query = select(RateLimitTracker).where(
            and_(
                RateLimitTracker.source == source,
                RateLimitTracker.time_window_start == window_start
            )
        )
        result = await session.execute(query)
        tracker = result.scalar_one_or_none()

        if not tracker:
            # Create new tracker
            tracker = RateLimitTracker(
                source=source,
                time_window_start=window_start,
                time_window_end=window_start + timedelta(hours=1),
                requests_allowed=config['requests_per_hour'],
                requests_made=0
            )
            session.add(tracker)
            await session.commit()

        # Check if we've exceeded the hourly limit
        if tracker.requests_made >= tracker.requests_allowed:
            # Calculate time until next hour
            next_hour = window_start + timedelta(hours=1)
            wait_seconds = (next_hour - now).total_seconds()
            return False, wait_seconds

        return True, None

    def _check_burst_limit(self, source: str, config: Dict) -> Tuple[bool, Optional[float]]:
        """Check if burst limit allows the request."""
        if source not in self._request_timestamps:
            return True, None

        # Check requests in last minute for burst limiting
        now = time.time()
        minute_ago = now - 60
        recent_requests = [
            ts for ts in self._request_timestamps[source] if ts > minute_ago
        ]

        if len(recent_requests) >= config['burst_limit']:
            # Wait until oldest request in burst window expires
            oldest_in_burst = min(recent_requests)
            wait_seconds = 60 - (now - oldest_in_burst)
            return False, max(1, wait_seconds)

        return True, None

    def _check_minimum_delay(self, source: str, config: Dict) -> Tuple[bool, Optional[float]]:
        """Check if minimum delay between requests is satisfied."""
        if source not in self._last_request_time:
            return True, None

        now = time.time()
        last_request = self._last_request_time[source]
        time_since_last = now - last_request

        min_delay = config['min_delay_seconds']
        if time_since_last < min_delay:
            wait_seconds = min_delay - time_since_last
            return False, wait_seconds

        return True, None

    def _get_respectful_delay(self, source: str, config: Dict) -> float:
        """Get additional delay during respectful hours."""
        respectful_hours = config.get('respectful_hours')
        if not respectful_hours:
            return 0

        now = datetime.utcnow()
        current_hour = now.hour

        start_hour, end_hour = respectful_hours
        if start_hour <= current_hour <= end_hour:
            # During business hours, add extra delay
            base_delay = config['min_delay_seconds']
            return base_delay * 1.5  # 50% longer delay during business hours

        return 0

    async def _update_database_tracking(
        self,
        session: AsyncSession,
        source: str,
        response_time_ms: Optional[float]
    ):
        """Update database rate limiting tracking."""
        now = datetime.utcnow()
        window_start = now.replace(minute=0, second=0, microsecond=0)

        # Get existing tracker
        query = select(RateLimitTracker).where(
            and_(
                RateLimitTracker.source == source,
                RateLimitTracker.time_window_start == window_start
            )
        )
        result = await session.execute(query)
        tracker = result.scalar_one_or_none()

        if tracker:
            # Update existing tracker
            tracker.requests_made += 1

            # Update average response time
            if response_time_ms:
                if tracker.avg_response_time_ms:
                    # Calculate rolling average
                    total_requests = tracker.requests_made
                    old_total = tracker.avg_response_time_ms * (total_requests - 1)
                    tracker.avg_response_time_ms = (old_total + response_time_ms) / total_requests
                else:
                    tracker.avg_response_time_ms = response_time_ms

            await session.commit()

    async def get_rate_limit_status(self, source: Optional[str] = None) -> Dict[str, Dict]:
        """
        Get current rate limiting status for sources.

        Args:
            source: Specific source to check, or None for all sources

        Returns:
            Dict mapping source names to their rate limit status
        """
        status = {}
        sources_to_check = [source] if source else list(self.source_configs.keys())

        async with get_session() as session:
            now = datetime.utcnow()
            window_start = now.replace(minute=0, second=0, microsecond=0)

            for src in sources_to_check:
                config = self.source_configs[src]

                # Get database tracking
                query = select(RateLimitTracker).where(
                    and_(
                        RateLimitTracker.source == src,
                        RateLimitTracker.time_window_start == window_start
                    )
                )
                result = await session.execute(query)
                tracker = result.scalar_one_or_none()

                # Get in-memory tracking
                recent_requests = 0
                if src in self._request_timestamps:
                    minute_ago = time.time() - 60
                    recent_requests = len([
                        ts for ts in self._request_timestamps[src] if ts > minute_ago
                    ])

                requests_made = tracker.requests_made if tracker else 0
                requests_allowed = config['requests_per_hour']

                status[src] = {
                    'hourly_usage': {
                        'requests_made': requests_made,
                        'requests_allowed': requests_allowed,
                        'usage_percent': (requests_made / requests_allowed * 100) if requests_allowed > 0 else 0,
                        'remaining': max(0, requests_allowed - requests_made)
                    },
                    'burst_usage': {
                        'recent_requests': recent_requests,
                        'burst_limit': config['burst_limit'],
                        'burst_available': max(0, config['burst_limit'] - recent_requests)
                    },
                    'config': {
                        'min_delay_seconds': config['min_delay_seconds'],
                        'respectful_hours': config['respectful_hours']
                    },
                    'avg_response_time_ms': tracker.avg_response_time_ms if tracker else None,
                    'window_start': window_start.isoformat(),
                    'window_end': (window_start + timedelta(hours=1)).isoformat()
                }

        return status

    async def adjust_rate_limits(self, source: str, **kwargs):
        """
        Dynamically adjust rate limits for a source.

        Args:
            source: Source to adjust
            **kwargs: Rate limit parameters to update
        """
        if source not in self.source_configs:
            raise ValueError(f"Unknown source: {source}")

        config = self.source_configs[source]
        for key, value in kwargs.items():
            if key in config:
                old_value = config[key]
                config[key] = value
                logger.info(
                    "Rate limit adjusted",
                    source=source,
                    parameter=key,
                    old_value=old_value,
                    new_value=value
                )
            else:
                logger.warning("Unknown rate limit parameter", source=source, parameter=key)

    async def cleanup_old_tracking_data(self, days_to_keep: int = 7):
        """Clean up old rate limiting tracking data."""
        async with get_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

            query = select(RateLimitTracker).where(
                RateLimitTracker.time_window_start < cutoff_date
            )
            result = await session.execute(query)
            old_trackers = result.scalars().all()

            deleted_count = 0
            for tracker in old_trackers:
                await session.delete(tracker)
                deleted_count += 1

            await session.commit()

            logger.info("Cleaned up old rate limit tracking data", deleted_count=deleted_count)
            return deleted_count

    def get_recommended_delay(self, source: str) -> float:
        """Get recommended delay before next request."""
        if source not in self.source_configs:
            return 1.0  # Default 1 second

        config = self.source_configs[source]
        base_delay = config['min_delay_seconds']

        # Add respectful hours adjustment
        respectful_delay = self._get_respectful_delay(source, config)

        return max(base_delay, respectful_delay)


# Global rate limiting service instance
rate_limiting_service = RateLimitingService()