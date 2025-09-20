#!/usr/bin/env python3
"""
Database seeding script for the Travel Legal Alert System.
Run this script to populate the database with sample data.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app.utils.seeder import seed_database


async def main():
    """Main function to run the database seeder."""
    try:
        print("🚀 Travel Legal Alert System - Database Seeder")
        print("=" * 50)

        await seed_database()

        print("=" * 50)
        print("🎉 Database seeding completed successfully!")
        print("\nSample data includes:")
        print("  • 20 countries across different regions")
        print("  • 5 test users with different travel preferences")
        print("  • 10 diverse sources (government, news, embassy, legal)")
        print("  • 10 sample alerts with various risk levels")
        print("  • User-alert relationships for testing notifications")

    except Exception as e:
        print(f"❌ Error during database seeding: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())