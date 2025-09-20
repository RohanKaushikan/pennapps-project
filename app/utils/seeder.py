"""
Database seeder for the Travel Legal Alert System.
Provides sample data for testing and development.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import User, Country, Source, Alert, UserAlert


class DatabaseSeeder:
    """Database seeder class for populating sample data."""

    def __init__(self):
        self.session: AsyncSession = None

    async def seed_all(self) -> None:
        """Seed all tables with sample data."""
        async with AsyncSessionLocal() as session:
            self.session = session
            try:
                print("🌱 Starting database seeding...")

                # Check if data already exists
                if await self._data_exists():
                    print("📋 Sample data already exists. Skipping seeding.")
                    return

                # Seed in order of dependencies
                countries = await self._seed_countries()
                users = await self._seed_users()
                sources = await self._seed_sources(countries)
                alerts = await self._seed_alerts(countries, sources)
                await self._seed_user_alerts(users, alerts)

                await session.commit()
                print("✅ Database seeding completed successfully!")

            except Exception as e:
                await session.rollback()
                print(f"❌ Error during seeding: {e}")
                raise

    async def _data_exists(self) -> bool:
        """Check if sample data already exists."""
        result = await self.session.execute(select(Country))
        return len(result.scalars().all()) > 0

    async def _seed_countries(self) -> List[Country]:
        """Seed countries table with sample data."""
        print("🌍 Seeding countries...")

        countries_data = [
            {"code": "US", "name": "United States", "region": "North America"},
            {"code": "CA", "name": "Canada", "region": "North America"},
            {"code": "GB", "name": "United Kingdom", "region": "Europe"},
            {"code": "FR", "name": "France", "region": "Europe"},
            {"code": "DE", "name": "Germany", "region": "Europe"},
            {"code": "JP", "name": "Japan", "region": "Asia"},
            {"code": "AU", "name": "Australia", "region": "Oceania"},
            {"code": "BR", "name": "Brazil", "region": "South America"},
            {"code": "IN", "name": "India", "region": "Asia"},
            {"code": "CN", "name": "China", "region": "Asia"},
            {"code": "MX", "name": "Mexico", "region": "North America"},
            {"code": "ES", "name": "Spain", "region": "Europe"},
            {"code": "IT", "name": "Italy", "region": "Europe"},
            {"code": "RU", "name": "Russia", "region": "Europe/Asia"},
            {"code": "ZA", "name": "South Africa", "region": "Africa"},
            {"code": "EG", "name": "Egypt", "region": "Africa"},
            {"code": "TH", "name": "Thailand", "region": "Asia"},
            {"code": "TR", "name": "Turkey", "region": "Europe/Asia"},
            {"code": "AR", "name": "Argentina", "region": "South America"},
            {"code": "NG", "name": "Nigeria", "region": "Africa"},
        ]

        countries = []
        for data in countries_data:
            country = Country(**data)
            self.session.add(country)
            countries.append(country)

        await self.session.flush()  # Get IDs without committing
        print(f"   ✓ Added {len(countries)} countries")
        return countries

    async def _seed_users(self) -> List[User]:
        """Seed users table with sample data."""
        print("👥 Seeding users...")

        users_data = [
            {
                "email": "john.doe@example.com",
                "travel_preferences": {
                    "preferred_countries": ["US", "CA", "GB"],
                    "risk_tolerance": "medium",
                    "notification_frequency": "daily",
                    "categories_of_interest": ["visa", "legal", "safety"]
                }
            },
            {
                "email": "jane.smith@example.com",
                "travel_preferences": {
                    "preferred_countries": ["FR", "IT", "ES"],
                    "risk_tolerance": "low",
                    "notification_frequency": "immediate",
                    "categories_of_interest": ["legal", "health", "safety"]
                }
            },
            {
                "email": "bob.wilson@example.com",
                "travel_preferences": {
                    "preferred_countries": ["JP", "TH", "AU"],
                    "risk_tolerance": "high",
                    "notification_frequency": "weekly",
                    "categories_of_interest": ["visa", "safety"]
                }
            },
            {
                "email": "alice.johnson@example.com",
                "travel_preferences": {
                    "preferred_countries": ["DE", "FR", "GB"],
                    "risk_tolerance": "medium",
                    "notification_frequency": "daily",
                    "categories_of_interest": ["legal", "visa", "health"]
                }
            },
            {
                "email": "mike.brown@example.com",
                "travel_preferences": {
                    "preferred_countries": ["BR", "AR", "MX"],
                    "risk_tolerance": "medium",
                    "notification_frequency": "daily",
                    "categories_of_interest": ["safety", "legal"]
                }
            }
        ]

        users = []
        for data in users_data:
            user = User(**data)
            self.session.add(user)
            users.append(user)

        await self.session.flush()
        print(f"   ✓ Added {len(users)} users")
        return users

    async def _seed_sources(self, countries: List[Country]) -> List[Source]:
        """Seed sources table with sample data."""
        print("📰 Seeding sources...")

        # Create a mapping of country codes to country objects
        country_map = {country.code: country for country in countries}

        sources_data = [
            {
                "name": "US State Department",
                "url": "https://travel.state.gov",
                "country_id": country_map["US"].id,
                "source_type": "government",
                "is_active": True,
                "last_scraped": datetime.utcnow() - timedelta(hours=2)
            },
            {
                "name": "UK Foreign Office",
                "url": "https://www.gov.uk/foreign-travel-advice",
                "country_id": country_map["GB"].id,
                "source_type": "government",
                "is_active": True,
                "last_scraped": datetime.utcnow() - timedelta(hours=1)
            },
            {
                "name": "CNN International",
                "url": "https://edition.cnn.com",
                "country_id": country_map["US"].id,
                "source_type": "news",
                "is_active": True,
                "last_scraped": datetime.utcnow() - timedelta(minutes=30)
            },
            {
                "name": "BBC News",
                "url": "https://www.bbc.com/news",
                "country_id": country_map["GB"].id,
                "source_type": "news",
                "is_active": True,
                "last_scraped": datetime.utcnow() - timedelta(minutes=45)
            },
            {
                "name": "French Ministry of Foreign Affairs",
                "url": "https://www.diplomatie.gouv.fr",
                "country_id": country_map["FR"].id,
                "source_type": "government",
                "is_active": True,
                "last_scraped": datetime.utcnow() - timedelta(hours=3)
            },
            {
                "name": "German Federal Foreign Office",
                "url": "https://www.auswaertiges-amt.de",
                "country_id": country_map["DE"].id,
                "source_type": "government",
                "is_active": True,
                "last_scraped": datetime.utcnow() - timedelta(hours=4)
            },
            {
                "name": "Japan Ministry of Foreign Affairs",
                "url": "https://www.mofa.go.jp",
                "country_id": country_map["JP"].id,
                "source_type": "government",
                "is_active": True,
                "last_scraped": datetime.utcnow() - timedelta(hours=6)
            },
            {
                "name": "Australian Embassy Thailand",
                "url": "https://thailand.embassy.gov.au",
                "country_id": country_map["AU"].id,
                "source_type": "embassy",
                "is_active": True,
                "last_scraped": datetime.utcnow() - timedelta(hours=8)
            },
            {
                "name": "Canadian Embassy Mexico",
                "url": "https://www.canadainternational.gc.ca/mexico-mexique",
                "country_id": country_map["CA"].id,
                "source_type": "embassy",
                "is_active": True,
                "last_scraped": datetime.utcnow() - timedelta(hours=5)
            },
            {
                "name": "Legal News Network",
                "url": "https://legalnews.example.com",
                "country_id": country_map["US"].id,
                "source_type": "legal",
                "is_active": True,
                "last_scraped": datetime.utcnow() - timedelta(hours=1)
            }
        ]

        sources = []
        for data in sources_data:
            source = Source(**data)
            self.session.add(source)
            sources.append(source)

        await self.session.flush()
        print(f"   ✓ Added {len(sources)} sources")
        return sources

    async def _seed_alerts(self, countries: List[Country], sources: List[Source]) -> List[Alert]:
        """Seed alerts table with sample data."""
        print("🚨 Seeding alerts...")

        # Create mappings
        country_map = {country.code: country for country in countries}
        source_map = {source.name: source for source in sources}

        alerts_data = [
            {
                "title": "New Visa Requirements for European Union Citizens",
                "description": "Starting January 2024, EU citizens traveling to the United States will need to apply for an updated ESTA authorization. This new requirement includes additional background checks and biometric data collection.",
                "country_id": country_map["US"].id,
                "source_id": source_map["US State Department"].id,
                "risk_level": 2,
                "expires_at": datetime.utcnow() + timedelta(days=90),
                "categories": ["visa", "legal"],
                "raw_content": "The U.S. Department of Homeland Security announces new enhanced screening procedures for ESTA applications..."
            },
            {
                "title": "COVID-19 Health Certificate No Longer Required",
                "description": "The UK government has officially removed the requirement for COVID-19 health certificates for all international travelers effective immediately.",
                "country_id": country_map["GB"].id,
                "source_id": source_map["UK Foreign Office"].id,
                "risk_level": 1,
                "expires_at": None,
                "categories": ["health", "legal"],
                "raw_content": "Her Majesty's Government announces the lifting of all COVID-19 related travel restrictions..."
            },
            {
                "title": "Severe Weather Warning - Typhoon Approaching",
                "description": "A Category 4 typhoon is expected to make landfall in Japan within 48 hours. All non-essential travel to affected regions should be postponed.",
                "country_id": country_map["JP"].id,
                "source_id": source_map["Japan Ministry of Foreign Affairs"].id,
                "risk_level": 4,
                "expires_at": datetime.utcnow() + timedelta(days=7),
                "categories": ["safety", "weather"],
                "raw_content": "Japan Meteorological Agency issues emergency weather warning for Typhoon..."
            },
            {
                "title": "New Tax Regulations for Digital Nomads",
                "description": "France has introduced new tax regulations affecting digital nomads and remote workers. Foreign nationals working remotely while in France may be subject to additional tax obligations.",
                "country_id": country_map["FR"].id,
                "source_id": source_map["French Ministry of Foreign Affairs"].id,
                "risk_level": 2,
                "expires_at": datetime.utcnow() + timedelta(days=180),
                "categories": ["legal", "tax"],
                "raw_content": "The French Ministry of Finance announces new taxation rules for remote workers..."
            },
            {
                "title": "Embassy Service Disruption",
                "description": "The Australian Embassy in Thailand will be closed for essential maintenance from March 15-17. Emergency services will remain available.",
                "country_id": country_map["TH"].id,
                "source_id": source_map["Australian Embassy Thailand"].id,
                "risk_level": 1,
                "expires_at": datetime.utcnow() + timedelta(days=30),
                "categories": ["embassy", "services"],
                "raw_content": "Notice: The Australian Embassy Bangkok will be temporarily closed for maintenance..."
            },
            {
                "title": "Updated Entry Requirements for Canadian Citizens",
                "description": "Mexico has updated entry requirements for Canadian citizens. A valid passport is now required for all entries, including land border crossings.",
                "country_id": country_map["MX"].id,
                "source_id": source_map["Canadian Embassy Mexico"].id,
                "risk_level": 2,
                "expires_at": None,
                "categories": ["visa", "legal"],
                "raw_content": "Mexico's National Immigration Institute announces updated documentation requirements..."
            },
            {
                "title": "Political Unrest - Avoid Central Districts",
                "description": "Ongoing political demonstrations in central areas. Travelers are advised to avoid government buildings and large gatherings.",
                "country_id": country_map["TH"].id,
                "source_id": source_map["BBC News"].id,
                "risk_level": 3,
                "expires_at": datetime.utcnow() + timedelta(days=14),
                "categories": ["safety", "political"],
                "raw_content": "Reports of peaceful protests in Bangkok city center continue for the third consecutive day..."
            },
            {
                "title": "New Environmental Protection Laws",
                "description": "Germany has enacted strict new environmental protection laws that may affect industrial activities and vehicle emissions standards for visitors.",
                "country_id": country_map["DE"].id,
                "source_id": source_map["German Federal Foreign Office"].id,
                "risk_level": 1,
                "expires_at": datetime.utcnow() + timedelta(days=365),
                "categories": ["legal", "environment"],
                "raw_content": "The German Bundestag passes comprehensive environmental protection legislation..."
            },
            {
                "title": "Currency Exchange Rate Volatility",
                "description": "Significant fluctuations in the Brazilian Real may affect travel budgets. Consider using established exchange services.",
                "country_id": country_map["BR"].id,
                "source_id": source_map["CNN International"].id,
                "risk_level": 2,
                "expires_at": datetime.utcnow() + timedelta(days=60),
                "categories": ["economic", "finance"],
                "raw_content": "Brazilian Central Bank implements new monetary policy measures affecting exchange rates..."
            },
            {
                "title": "New Legal Requirements for Foreign Workers",
                "description": "Updated work permit requirements for foreign nationals. New documentation must be submitted within 30 days of arrival.",
                "country_id": country_map["US"].id,
                "source_id": source_map["Legal News Network"].id,
                "risk_level": 3,
                "expires_at": datetime.utcnow() + timedelta(days=120),
                "categories": ["legal", "work", "visa"],
                "raw_content": "U.S. Department of Labor announces updated foreign worker documentation requirements..."
            }
        ]

        alerts = []
        for data in alerts_data:
            alert = Alert(**data)
            self.session.add(alert)
            alerts.append(alert)

        await self.session.flush()
        print(f"   ✓ Added {len(alerts)} alerts")
        return alerts

    async def _seed_user_alerts(self, users: List[User], alerts: List[Alert]) -> None:
        """Seed user_alerts table with sample data."""
        print("🔔 Seeding user alerts...")

        # Create some user-alert relationships
        user_alerts_data = [
            # John Doe (user 0) gets alerts for US, CA, GB
            {"user_id": users[0].id, "alert_id": alerts[0].id, "is_read": False, "notified_at": datetime.utcnow() - timedelta(hours=2)},
            {"user_id": users[0].id, "alert_id": alerts[1].id, "is_read": True, "notified_at": datetime.utcnow() - timedelta(hours=5)},
            {"user_id": users[0].id, "alert_id": alerts[9].id, "is_read": False, "notified_at": datetime.utcnow() - timedelta(minutes=30)},

            # Jane Smith (user 1) gets alerts for FR, IT, ES
            {"user_id": users[1].id, "alert_id": alerts[3].id, "is_read": False, "notified_at": datetime.utcnow() - timedelta(hours=1)},
            {"user_id": users[1].id, "alert_id": alerts[7].id, "is_read": True, "notified_at": datetime.utcnow() - timedelta(hours=3)},

            # Bob Wilson (user 2) gets alerts for JP, TH, AU
            {"user_id": users[2].id, "alert_id": alerts[2].id, "is_read": False, "notified_at": datetime.utcnow() - timedelta(minutes=45)},
            {"user_id": users[2].id, "alert_id": alerts[4].id, "is_read": True, "notified_at": datetime.utcnow() - timedelta(hours=6)},
            {"user_id": users[2].id, "alert_id": alerts[6].id, "is_read": False, "notified_at": datetime.utcnow() - timedelta(hours=2)},

            # Alice Johnson (user 3) gets alerts for DE, FR, GB
            {"user_id": users[3].id, "alert_id": alerts[1].id, "is_read": True, "notified_at": datetime.utcnow() - timedelta(hours=4)},
            {"user_id": users[3].id, "alert_id": alerts[3].id, "is_read": False, "notified_at": datetime.utcnow() - timedelta(hours=1)},
            {"user_id": users[3].id, "alert_id": alerts[7].id, "is_read": False, "notified_at": datetime.utcnow() - timedelta(minutes=20)},

            # Mike Brown (user 4) gets alerts for BR, AR, MX
            {"user_id": users[4].id, "alert_id": alerts[5].id, "is_read": False, "notified_at": datetime.utcnow() - timedelta(hours=3)},
            {"user_id": users[4].id, "alert_id": alerts[8].id, "is_read": True, "notified_at": datetime.utcnow() - timedelta(hours=7)},
        ]

        user_alerts = []
        for data in user_alerts_data:
            user_alert = UserAlert(**data)
            self.session.add(user_alert)
            user_alerts.append(user_alert)

        await self.session.flush()
        print(f"   ✓ Added {len(user_alerts)} user alerts")


async def seed_database():
    """Main function to seed the database."""
    seeder = DatabaseSeeder()
    await seeder.seed_all()


# CLI script entry point
if __name__ == "__main__":
    asyncio.run(seed_database())