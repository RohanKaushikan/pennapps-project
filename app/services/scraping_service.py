import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_session
from app.models.travel_advisory import TravelAdvisory, ScrapingLog, ContentChangeEvent
from app.scrapers import BaseScraper, USStateDeptScraper, UKForeignOfficeScraper, CanadaTravelScraper
from app.scrapers.base_scraper import ScrapedContent

logger = structlog.get_logger(__name__)


class ScrapingService:
    def __init__(self):
        self.scrapers: Dict[str, BaseScraper] = {
            'us_state_dept': USStateDeptScraper(),
            'uk_foreign_office': UKForeignOfficeScraper(),
            'canada_travel': CanadaTravelScraper()
        }

    async def scrape_all_sources(self, session: AsyncSession) -> Dict[str, Any]:
        """
        Scrape all travel advisories from all sources and store in database.

        Returns:
            Dict containing scraping results summary
        """
        scraping_session_id = uuid.uuid4()
        results = {
            'session_id': str(scraping_session_id),
            'sources': {},
            'total_new': 0,
            'total_updated': 0,
            'total_errors': 0
        }

        for source_name, scraper in self.scrapers.items():
            logger.info("Starting scrape for source", source=source_name)

            source_result = await self._scrape_source(
                session, source_name, scraper, scraping_session_id
            )
            results['sources'][source_name] = source_result
            results['total_new'] += source_result.get('new_content', 0)
            results['total_updated'] += source_result.get('updated_content', 0)
            results['total_errors'] += source_result.get('errors', 0)

        return results

    async def scrape_single_source(self, session: AsyncSession, source_name: str) -> Dict[str, Any]:
        """
        Scrape travel advisories from a single source.

        Args:
            session: Database session
            source_name: Name of the source to scrape

        Returns:
            Dict containing scraping results
        """
        if source_name not in self.scrapers:
            raise ValueError(f"Unknown source: {source_name}")

        scraping_session_id = uuid.uuid4()
        scraper = self.scrapers[source_name]

        return await self._scrape_source(
            session, source_name, scraper, scraping_session_id
        )

    async def scrape_country_from_source(
        self,
        session: AsyncSession,
        source_name: str,
        country: str
    ) -> Optional[TravelAdvisory]:
        """
        Scrape travel advisory for a specific country from a specific source.

        Args:
            session: Database session
            source_name: Name of the source to scrape
            country: Country name to scrape

        Returns:
            TravelAdvisory object if successful, None otherwise
        """
        if source_name not in self.scrapers:
            raise ValueError(f"Unknown source: {source_name}")

        scraper = self.scrapers[source_name]

        try:
            scraped_content = await scraper.scrape_country_advisory(country)
            if not scraped_content:
                return None

            # Check if content already exists and detect changes
            existing_advisory = await self._get_existing_advisory(
                session, source_name, country
            )

            if existing_advisory:
                if await self._has_content_changed(existing_advisory, scraped_content):
                    await self._update_advisory(session, existing_advisory, scraped_content)
                    return existing_advisory
                else:
                    # Content hasn't changed, just update scraped_at timestamp
                    existing_advisory.scraped_at = datetime.utcnow()
                    await session.commit()
                    return existing_advisory
            else:
                # Create new advisory
                new_advisory = await self._create_advisory(session, source_name, scraped_content)
                return new_advisory

        except Exception as e:
            logger.error("Error scraping country", source=source_name, country=country, error=str(e))
            return None

    async def _scrape_source(
        self,
        session: AsyncSession,
        source_name: str,
        scraper: BaseScraper,
        scraping_session_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Internal method to scrape a single source and handle database operations.
        """
        start_time = datetime.utcnow()

        # Create scraping log entry
        log_entry = ScrapingLog(
            source=source_name,
            scraping_session_id=scraping_session_id,
            status='started',
            started_at=start_time
        )
        session.add(log_entry)
        await session.commit()

        new_content = 0
        updated_content = 0
        errors = 0
        total_scraped = 0

        try:
            # Scrape all advisories from the source
            scraped_contents = await scraper.scrape_all_advisories()
            total_scraped = len(scraped_contents)

            logger.info(
                "Scraped content from source",
                source=source_name,
                total_count=total_scraped
            )

            for scraped_content in scraped_contents:
                try:
                    # Check if content already exists
                    existing_advisory = await self._get_existing_advisory(
                        session, source_name, scraped_content.country
                    )

                    if existing_advisory:
                        if await self._has_content_changed(existing_advisory, scraped_content):
                            await self._update_advisory(session, existing_advisory, scraped_content)
                            updated_content += 1
                        else:
                            # Update scraped_at timestamp even if content hasn't changed
                            existing_advisory.scraped_at = datetime.utcnow()
                    else:
                        await self._create_advisory(session, source_name, scraped_content)
                        new_content += 1

                except Exception as e:
                    logger.error(
                        "Error processing scraped content",
                        source=source_name,
                        country=scraped_content.country,
                        error=str(e)
                    )
                    errors += 1

            await session.commit()

            # Update log entry with success
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            log_entry.status = 'completed'
            log_entry.completed_at = end_time
            log_entry.duration_seconds = duration
            log_entry.total_countries = total_scraped
            log_entry.successful_scrapes = total_scraped - errors
            log_entry.failed_scrapes = errors
            log_entry.new_content_count = new_content
            log_entry.updated_content_count = updated_content

            await session.commit()

            return {
                'status': 'completed',
                'total_scraped': total_scraped,
                'new_content': new_content,
                'updated_content': updated_content,
                'errors': errors,
                'duration_seconds': duration
            }

        except Exception as e:
            logger.error("Error during source scraping", source=source_name, error=str(e))

            # Update log entry with failure
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            log_entry.status = 'failed'
            log_entry.completed_at = end_time
            log_entry.duration_seconds = duration
            log_entry.error_message = str(e)
            log_entry.total_countries = total_scraped
            log_entry.successful_scrapes = total_scraped - errors
            log_entry.failed_scrapes = errors + 1
            log_entry.new_content_count = new_content
            log_entry.updated_content_count = updated_content

            await session.commit()

            return {
                'status': 'failed',
                'total_scraped': total_scraped,
                'new_content': new_content,
                'updated_content': updated_content,
                'errors': errors + 1,
                'duration_seconds': duration,
                'error': str(e)
            }

    async def _get_existing_advisory(
        self,
        session: AsyncSession,
        source: str,
        country: str
    ) -> Optional[TravelAdvisory]:
        """
        Get existing travel advisory for a country and source.
        """
        query = select(TravelAdvisory).where(
            and_(
                TravelAdvisory.source == source,
                TravelAdvisory.country == country,
                TravelAdvisory.is_active == True
            )
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def _has_content_changed(
        self,
        existing: TravelAdvisory,
        new_content: ScrapedContent
    ) -> bool:
        """
        Check if the content has changed based on content hash.
        """
        return existing.content_hash != new_content.content_hash

    async def _create_advisory(
        self,
        session: AsyncSession,
        source: str,
        content: ScrapedContent
    ) -> TravelAdvisory:
        """
        Create a new travel advisory in the database.
        """
        advisory = TravelAdvisory(
            url=str(content.url),
            source=source,
            country=content.country or "Unknown",
            title=content.title,
            content=content.content,
            content_hash=content.content_hash,
            risk_level=content.risk_level,
            last_updated_source=content.last_updated,
            metadata=content.metadata,
            scraped_at=datetime.fromtimestamp(content.scraped_at)
        )

        session.add(advisory)
        await session.commit()

        # Create change event for new content
        change_event = ContentChangeEvent(
            advisory_id=advisory.id,
            change_type='new',
            new_hash=content.content_hash,
            new_risk_level=content.risk_level,
            change_summary=f"New travel advisory created for {content.country}"
        )
        session.add(change_event)
        await session.commit()

        logger.info(
            "Created new travel advisory",
            advisory_id=str(advisory.id),
            source=source,
            country=content.country
        )

        return advisory

    async def _update_advisory(
        self,
        session: AsyncSession,
        existing: TravelAdvisory,
        new_content: ScrapedContent
    ) -> TravelAdvisory:
        """
        Update an existing travel advisory with new content.
        """
        # Store previous values for change tracking
        previous_hash = existing.content_hash
        previous_risk_level = existing.risk_level

        # Update the advisory
        existing.title = new_content.title
        existing.content = new_content.content
        existing.content_hash = new_content.content_hash
        existing.risk_level = new_content.risk_level
        existing.last_updated_source = new_content.last_updated
        existing.metadata = new_content.metadata
        existing.scraped_at = datetime.fromtimestamp(new_content.scraped_at)
        existing.updated_at = datetime.utcnow()
        existing.content_changed = True

        await session.commit()

        # Determine change type
        change_type = 'updated'
        if previous_risk_level != new_content.risk_level:
            change_type = 'risk_level_changed'

        # Create change event
        change_event = ContentChangeEvent(
            advisory_id=existing.id,
            change_type=change_type,
            previous_hash=previous_hash,
            new_hash=new_content.content_hash,
            previous_risk_level=previous_risk_level,
            new_risk_level=new_content.risk_level,
            change_summary=f"Travel advisory updated for {new_content.country}"
        )
        session.add(change_event)
        await session.commit()

        logger.info(
            "Updated travel advisory",
            advisory_id=str(existing.id),
            source=existing.source,
            country=new_content.country,
            change_type=change_type
        )

        return existing

    async def get_recent_changes(
        self,
        session: AsyncSession,
        limit: int = 50
    ) -> List[ContentChangeEvent]:
        """
        Get recent content changes.
        """
        query = select(ContentChangeEvent).order_by(
            desc(ContentChangeEvent.detected_at)
        ).limit(limit)

        result = await session.execute(query)
        return result.scalars().all()

    async def get_advisories_by_country(
        self,
        session: AsyncSession,
        country: str
    ) -> List[TravelAdvisory]:
        """
        Get all travel advisories for a specific country from all sources.
        """
        query = select(TravelAdvisory).where(
            and_(
                TravelAdvisory.country == country,
                TravelAdvisory.is_active == True
            )
        ).order_by(desc(TravelAdvisory.scraped_at))

        result = await session.execute(query)
        return result.scalars().all()

    async def close_scrapers(self):
        """
        Close all scraper connections.
        """
        for scraper in self.scrapers.values():
            await scraper.close()