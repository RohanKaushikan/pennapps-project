import asyncio
import hashlib
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from urllib.robotparser import RobotFileParser
import structlog
import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, HttpUrl
import re

logger = structlog.get_logger(__name__)


class ScrapedContent(BaseModel):
    url: HttpUrl
    title: str
    content: str
    content_hash: str
    last_updated: Optional[str] = None
    country: Optional[str] = None
    risk_level: Optional[str] = None
    metadata: Dict[str, Any] = {}
    scraped_at: float

    class Config:
        json_encoders = {
            HttpUrl: str
        }


class ScrapingConfig(BaseModel):
    base_url: HttpUrl
    rate_limit_delay: float = 1.0
    max_retries: int = 3
    retry_delay: float = 2.0
    timeout: int = 30
    user_agent: str = "TravelAdvisoryBot/1.0 (+https://example.com/bot)"
    respect_robots_txt: bool = True
    headers: Dict[str, str] = {}

    class Config:
        json_encoders = {
            HttpUrl: str
        }


class BaseScraper(ABC):
    def __init__(self, config: ScrapingConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.timeout),
            headers={
                "User-Agent": self.config.user_agent,
                **self.config.headers
            }
        )
        self._last_request_time = 0
        self.robots_parser = None
        self._setup_robots_parser()

    def _setup_robots_parser(self):
        if self.config.respect_robots_txt:
            try:
                robots_url = f"{self.config.base_url.rstrip('/')}/robots.txt"
                self.robots_parser = RobotFileParser()
                self.robots_parser.set_url(robots_url)
                self.robots_parser.read()
            except Exception as e:
                logger.warning("Could not fetch robots.txt", error=str(e), url=robots_url)

    def _can_fetch(self, url: str) -> bool:
        if not self.robots_parser:
            return True
        return self.robots_parser.can_fetch(self.config.user_agent, url)

    async def _rate_limit(self):
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self.config.rate_limit_delay:
            sleep_time = self.config.rate_limit_delay - time_since_last
            await asyncio.sleep(sleep_time)
        self._last_request_time = time.time()

    async def _fetch_with_retry(self, url: str) -> Optional[httpx.Response]:
        for attempt in range(self.config.max_retries):
            try:
                await self._rate_limit()

                if not self._can_fetch(url):
                    logger.warning("Robots.txt disallows fetching", url=url)
                    return None

                response = await self.client.get(url)
                response.raise_for_status()

                logger.info("Successfully fetched URL", url=url, status_code=response.status_code)
                return response

            except httpx.HTTPStatusError as e:
                logger.warning(
                    "HTTP error fetching URL",
                    url=url,
                    status_code=e.response.status_code,
                    attempt=attempt + 1
                )
                if e.response.status_code == 404:
                    break

            except Exception as e:
                logger.warning(
                    "Error fetching URL",
                    url=url,
                    error=str(e),
                    attempt=attempt + 1
                )

            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(self.config.retry_delay * (2 ** attempt))

        logger.error("Failed to fetch URL after all retries", url=url)
        return None

    def _calculate_content_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""

        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())

        # Remove common HTML entities that might have been missed
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")

        return text.strip()

    def _extract_risk_level(self, text: str) -> Optional[str]:
        risk_patterns = [
            r'level\s*(\d+)',
            r'risk\s*level\s*[:\-]?\s*(\w+)',
            r'travel\s*advisory\s*[:\-]?\s*(\w+)',
            r'(?:do not travel|avoid all travel)',
            r'(?:exercise increased caution|heightened caution)',
            r'(?:reconsider travel)',
            r'(?:exercise normal precautions|normal precautions)'
        ]

        text_lower = text.lower()

        for pattern in risk_patterns:
            match = re.search(pattern, text_lower)
            if match:
                if 'do not travel' in text_lower or 'avoid all travel' in text_lower:
                    return 'Level 4 - Do Not Travel'
                elif 'reconsider travel' in text_lower:
                    return 'Level 3 - Reconsider Travel'
                elif 'exercise increased caution' in text_lower or 'heightened caution' in text_lower:
                    return 'Level 2 - Exercise Increased Caution'
                elif 'exercise normal precautions' in text_lower or 'normal precautions' in text_lower:
                    return 'Level 1 - Exercise Normal Precautions'
                elif match.group(1) if match.groups() else None:
                    level = match.group(1)
                    if level.isdigit():
                        level_map = {
                            '1': 'Level 1 - Exercise Normal Precautions',
                            '2': 'Level 2 - Exercise Increased Caution',
                            '3': 'Level 3 - Reconsider Travel',
                            '4': 'Level 4 - Do Not Travel'
                        }
                        return level_map.get(level)
                    else:
                        return level.title()

        return None

    def _validate_content(self, content: ScrapedContent) -> bool:
        if not content.title or not content.content:
            logger.warning("Content validation failed: missing title or content", url=str(content.url))
            return False

        if len(content.content) < 100:
            logger.warning("Content validation failed: content too short", url=str(content.url), length=len(content.content))
            return False

        return True

    @abstractmethod
    async def scrape_country_advisory(self, country: str) -> Optional[ScrapedContent]:
        pass

    @abstractmethod
    async def scrape_all_advisories(self) -> List[ScrapedContent]:
        pass

    @abstractmethod
    def _parse_advisory_page(self, html: str, url: str) -> Optional[ScrapedContent]:
        pass

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()