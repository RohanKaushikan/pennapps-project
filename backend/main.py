from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import feedparser
import requests
from datetime import datetime, timedelta
import hashlib
from collections import defaultdict, Counter
import statistics
import asyncio
from typing import List, Dict, Any, Optional
import sqlite3
import json
import threading
from urllib.parse import quote_plus

# Initialize FastAPI app
app = FastAPI(
    title="Travel News Anomaly Detection API",
    description="Detects unusual spikes in travel/visa news by country",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:3003", "http://localhost:3004"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
DB_PATH = "news_data.db"
db_lock = threading.Lock()

def init_db():
    """Initialize SQLite database"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS news_items (
                id TEXT PRIMARY KEY,
                country_code TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                source TEXT NOT NULL
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS hourly_counts (
                country_code TEXT NOT NULL,
                hour_timestamp TEXT NOT NULL,
                count INTEGER NOT NULL,
                baseline REAL,
                spike_factor REAL,
                is_anomaly BOOLEAN DEFAULT FALSE,
                PRIMARY KEY(country_code, hour_timestamp)
            )
        ''')
        conn.commit()

# Initialize database on startup
init_db()

# Country configurations with RSS feeds and search queries
COUNTRIES = {
    "NP": {
        "name": "Nepal",
        "flag": "🇳🇵",
        "feeds": [
            "https://news.google.com/rss/search?q=Nepal+(visa+OR+entry+OR+immigration+OR+border+OR+travel+advisory)&hl=en-US&gl=US&ceid=US:en"
        ]
    },
    "IT": {
        "name": "Italy", 
        "flag": "🇮🇹",
        "feeds": [
            "https://news.google.com/rss/search?q=Italy+(visa+OR+entry+OR+immigration+OR+border+OR+travel+advisory)&hl=en-US&gl=US&ceid=US:en"
        ]
    },
    "RU": {
        "name": "Russia",
        "flag": "🇷🇺", 
        "feeds": [
            "https://news.google.com/rss/search?q=Russia+(visa+OR+entry+OR+immigration+OR+border+OR+travel+advisory)&hl=en-US&gl=US&ceid=US:en"
        ]
    }
}

# Travel information data for each country
TRAVEL_DATA = {
    "NP": {
        "name": "Nepal",
        "welcome": [
            {
                "icon": "🏔️",
                "title": "Welcome to Nepal!",
                "message": "Namaste! Your adventure in the Himalayas begins here."
            },
            {
                "icon": "🙏",
                "title": "Cultural Experience",
                "message": "Discover ancient temples, vibrant festivals, and warm hospitality."
            }
        ],
        "transport": [
            "Domestic flights connect major cities - book in advance",
            "Local buses are cheap but can be crowded and slow",
            "Taxis are available in cities - negotiate fare before boarding",
            "Walking is common in Kathmandu - watch for traffic"
        ],
        "culture": [
            "Remove shoes before entering temples and homes",
            "Use your right hand for eating and giving/receiving items",
            "Dress modestly, especially when visiting religious sites",
            "Respect the local customs and traditions"
        ],
        "language": [
            {
                "native": "नमस्ते (Namaste)",
                "meaning": "Hello / Goodbye (with folded hands)"
            },
            {
                "native": "धन्यवाद (Dhanyabad)",
                "meaning": "Thank you"
            },
            {
                "native": "माफ गर्नुहोस् (Maaf garnuhos)",
                "meaning": "Excuse me / Sorry"
            },
            {
                "native": "अंग्रेजी बोल्नुहुन्छ? (Angreji bolnuhunchha?)",
                "meaning": "Do you speak English?"
            }
        ]
    },
    "IT": {
        "name": "Italy",
        "welcome": [
            {
                "icon": "🍝",
                "title": "Benvenuto in Italia!",
                "message": "Welcome to Italy! Experience art, history, and incredible cuisine."
            },
            {
                "icon": "🏛️",
                "title": "Cultural Heritage",
                "message": "Explore ancient ruins, Renaissance art, and charming villages."
            }
        ],
        "transport": [
            "High-speed trains (Frecciarossa) connect major cities efficiently",
            "Regional trains are slower but more affordable",
            "Metro systems in Rome, Milan, and Naples",
            "Taxis are expensive - use apps like Uber or local services"
        ],
        "culture": [
            "Dress well - Italians take pride in appearance",
            "Greet with a kiss on both cheeks among friends",
            "Don't order cappuccino after 11 AM - it's considered odd",
            "Tipping is not mandatory but appreciated for good service"
        ],
        "language": [
            {
                "native": "Ciao",
                "meaning": "Hello / Goodbye (informal)"
            },
            {
                "native": "Grazie",
                "meaning": "Thank you"
            },
            {
                "native": "Scusi",
                "meaning": "Excuse me"
            },
            {
                "native": "Parla inglese?",
                "meaning": "Do you speak English?"
            }
        ]
    },
    "RU": {
        "name": "Russia",
        "welcome": [
            {
                "icon": "❄️",
                "title": "Добро пожаловать в Россию!",
                "message": "Welcome to Russia! Discover vast landscapes and rich culture."
            },
            {
                "icon": "🏰",
                "title": "Historical Heritage",
                "message": "Explore magnificent palaces, museums, and architectural wonders."
            }
        ],
        "transport": [
            "Metro systems in major cities are efficient and beautiful",
            "Long-distance trains connect cities across the country",
            "Marshrutkas (minibuses) are common for local transport",
            "Taxis can be ordered via apps like Yandex.Taxi"
        ],
        "culture": [
            "Remove outdoor shoes when entering homes",
            "Bring flowers (odd numbers only) when visiting someone",
            "Don't shake hands across a threshold - it's considered bad luck",
            "Dress formally for cultural events and restaurants"
        ],
        "language": [
            {
                "native": "Привет (Privet)",
                "meaning": "Hello (informal)"
            },
            {
                "native": "Спасибо (Spasibo)",
                "meaning": "Thank you"
            },
            {
                "native": "Извините (Izvinite)",
                "meaning": "Excuse me / Sorry"
            },
            {
                "native": "Вы говорите по-английски? (Vy govorite po-angliyski?)",
                "meaning": "Do you speak English?"
            }
        ]
    }
}

# Pydantic models
class NewsItem(BaseModel):
    id: str
    country_code: str
    timestamp: str
    title: str
    url: str
    source: str

class AnomalyAlert(BaseModel):
    country_code: str
    country_name: str
    flag: str
    current_count: int
    baseline: float
    spike_factor: float
    is_anomaly: bool
    top_headlines: List[Dict[str, str]]

class HealthResponse(BaseModel):
    status: str
    message: str
    data_points: int

class WelcomeItem(BaseModel):
    icon: str
    title: str
    message: str

class LanguagePhrase(BaseModel):
    native: str
    meaning: str

class CountryInfo(BaseModel):
    name: str
    welcome: List[WelcomeItem]
    transport: List[str]
    culture: List[str]
    language: List[LanguagePhrase]

def fetch_rss_feed(url: str) -> List[Dict]:
    """Fetch and parse RSS feed"""
    try:
        feed = feedparser.parse(url)
        items = []
        
        for entry in feed.entries:
            # Get published time, fallback to current time
            pub_time = getattr(entry, 'published_parsed', None)
            if pub_time:
                timestamp = datetime(*pub_time[:6])
            else:
                timestamp = datetime.now()
            
            # Create unique ID from title + url
            unique_id = hashlib.sha256(
                (entry.title + entry.link).encode('utf-8')
            ).hexdigest()[:16]
            
            items.append({
                'id': unique_id,
                'title': entry.title,
                'url': entry.link,
                'timestamp': timestamp.isoformat(),
                'source': feed.feed.get('title', 'Unknown')
            })
            
        return items
    except Exception as e:
        print(f"Error fetching RSS feed {url}: {e}")
        return []

def store_news_items(country_code: str, items: List[Dict]):
    """Store news items in database"""
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            for item in items:
                try:
                    conn.execute('''
                        INSERT OR IGNORE INTO news_items 
                        (id, country_code, timestamp, title, url, source)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        item['id'], country_code, item['timestamp'],
                        item['title'], item['url'], item['source']
                    ))
                except sqlite3.Error as e:
                    print(f"Database error: {e}")
            conn.commit()

def get_hourly_counts(country_code: str, hours_back: int = 168) -> Dict[str, int]:
    """Get hourly news counts for a country (default: last 7 days)"""
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours_back)
    
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute('''
                SELECT timestamp FROM news_items 
                WHERE country_code = ? AND timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp
            ''', (country_code, start_time.isoformat(), end_time.isoformat()))
            
            timestamps = [datetime.fromisoformat(row[0]) for row in cursor.fetchall()]
    
    # Count by hour
    hourly_counts = defaultdict(int)
    for ts in timestamps:
        hour_key = ts.replace(minute=0, second=0, microsecond=0)
        hourly_counts[hour_key.isoformat()] += 1
    
    return dict(hourly_counts)

def calculate_baseline_and_anomaly(country_code: str) -> Dict:
    """Calculate baseline and detect anomalies for a country"""
    hourly_counts = get_hourly_counts(country_code, hours_back=672)  # Look back 4 weeks for enough data

    if len(hourly_counts) < 24:  # Need at least 24 hours of data
        return {
            'current_count': 0,
            'baseline': 0.0,
            'spike_factor': 1.0,
            'is_anomaly': False
        }

    # Look for anomalies in the last 2 weeks instead of just current hour
    current_time = datetime.now()
    two_weeks_ago = current_time - timedelta(hours=336)

    # Separate recent data from baseline data
    baseline_counts = []
    recent_counts = []

    for hour_str, count in hourly_counts.items():
        hour_dt = datetime.fromisoformat(hour_str)
        if hour_dt >= two_weeks_ago:
            recent_counts.append((hour_str, count))
        else:
            baseline_counts.append(count)

    # Calculate baseline from older data
    if not baseline_counts:
        # If no baseline data, use all data except recent spikes for baseline
        all_counts = list(hourly_counts.values())
        all_counts.sort()
        # Use median of lower 75% as baseline to avoid including spikes
        baseline_size = max(1, int(len(all_counts) * 0.75))
        baseline_counts = all_counts[:baseline_size]

    baseline = statistics.mean(baseline_counts) if baseline_counts else 0.1

    # Find the maximum spike in recent data
    recent_max_count = 0
    recent_max_hour = None
    recent_max_spike = 1.0

    for hour_str, count in recent_counts:
        spike_factor = count / max(baseline, 0.1)
        if count > recent_max_count:
            recent_max_count = count
            recent_max_hour = hour_str
            recent_max_spike = spike_factor

    # Check if we found a recent anomaly
    is_anomaly = recent_max_spike >= 2.0 and recent_max_count >= 3

    return {
        'current_count': recent_max_count,
        'baseline': round(baseline, 2),
        'spike_factor': round(recent_max_spike, 2),
        'is_anomaly': is_anomaly
    }

def get_top_headlines(country_code: str, limit: int = 3) -> List[Dict[str, str]]:
    """Get top recent headlines for a country"""
    current_time = datetime.now()
    start_time = current_time - timedelta(hours=336)

    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute('''
                SELECT title, url, source FROM news_items
                WHERE country_code = ? AND timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (country_code, start_time.isoformat(), limit))

            return [
                {'title': row[0], 'url': row[1], 'source': row[2]}
                for row in cursor.fetchall()
            ]

async def collect_news_for_country(country_code: str):
    """Collect news for a single country"""
    country_config = COUNTRIES.get(country_code)
    if not country_config:
        return
    
    all_items = []
    for feed_url in country_config['feeds']:
        items = fetch_rss_feed(feed_url)
        all_items.extend(items)
    
    if all_items:
        store_news_items(country_code, all_items)
        print(f"Collected {len(all_items)} items for {country_code}")

# API Endpoints

@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint"""
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM news_items")
            count = cursor.fetchone()[0]
    
    return HealthResponse(
        status="healthy",
        message="Travel News Anomaly Detection API is running!",
        data_points=count
    )

@app.post("/api/collect-news")
async def collect_news():
    """Manually trigger news collection for all countries"""
    tasks = []
    for country_code in COUNTRIES.keys():
        tasks.append(collect_news_for_country(country_code))
    
    await asyncio.gather(*tasks)
    
    return {"message": f"News collection completed for {len(COUNTRIES)} countries"}

@app.get("/api/countries")
async def get_countries():
    """Get list of monitored countries"""
    # Get countries from database that have news data
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute('''
            SELECT DISTINCT country_code FROM news_items 
            ORDER BY country_code
        ''')
        db_countries = [row[0] for row in cursor.fetchall()]
    
    # Combine predefined countries with database countries
    all_countries = {}
    
    # Add predefined countries
    for code, config in COUNTRIES.items():
        all_countries[code] = {
            "code": code,
            "name": config["name"],
            "flag": config["flag"]
        }
    
    # Add countries from database that aren't predefined
    country_names = {
        'US': 'United States', 'GB': 'United Kingdom', 'FR': 'France', 'DE': 'Germany',
        'IT': 'Italy', 'ES': 'Spain', 'JP': 'Japan', 'CN': 'China', 'IN': 'India',
        'AE': 'United Arab Emirates', 'AU': 'Australia', 'CA': 'Canada', 'MX': 'Mexico',
        'BR': 'Brazil', 'KR': 'South Korea', 'SG': 'Singapore', 'NL': 'Netherlands',
        'SE': 'Sweden', 'CH': 'Switzerland', 'TH': 'Thailand', 'PH': 'Philippines',
        'ID': 'Indonesia', 'MY': 'Malaysia', 'NZ': 'New Zealand', 'AR': 'Argentina',
        'CL': 'Chile', 'CO': 'Colombia', 'PE': 'Peru', 'EG': 'Egypt', 'ZA': 'South Africa',
        'IR': 'Iran', 'PK': 'Pakistan', 'BD': 'Bangladesh', 'LK': 'Sri Lanka',
        'RU': 'Russia', 'UA': 'Ukraine', 'PL': 'Poland', 'CZ': 'Czech Republic',
        'HU': 'Hungary', 'GR': 'Greece', 'PT': 'Portugal', 'IE': 'Ireland',
        'FI': 'Finland', 'NO': 'Norway', 'DK': 'Denmark', 'BE': 'Belgium', 'AT': 'Austria'
    }
    
    for country_code in db_countries:
        if country_code not in all_countries:
            country_name = country_names.get(country_code, country_code)
            all_countries[country_code] = {
                "code": country_code,
                "name": country_name,
                "flag": "🌍"
            }
    
    return {
        "countries": list(all_countries.values())
    }

def generate_dynamic_country_info(country_code: str) -> dict:
    """Generate basic travel information for any country"""
    country_names = {
        'US': 'United States', 'GB': 'United Kingdom', 'FR': 'France', 'DE': 'Germany',
        'IT': 'Italy', 'ES': 'Spain', 'JP': 'Japan', 'CN': 'China', 'IN': 'India',
        'AE': 'United Arab Emirates', 'AU': 'Australia', 'CA': 'Canada', 'MX': 'Mexico',
        'BR': 'Brazil', 'KR': 'South Korea', 'SG': 'Singapore', 'NL': 'Netherlands',
        'SE': 'Sweden', 'CH': 'Switzerland', 'TH': 'Thailand', 'PH': 'Philippines',
        'ID': 'Indonesia', 'MY': 'Malaysia', 'NZ': 'New Zealand', 'AR': 'Argentina',
        'CL': 'Chile', 'CO': 'Colombia', 'PE': 'Peru', 'EG': 'Egypt', 'ZA': 'South Africa',
        'IR': 'Iran', 'PK': 'Pakistan', 'BD': 'Bangladesh', 'LK': 'Sri Lanka',
        'RU': 'Russia', 'UA': 'Ukraine', 'PL': 'Poland', 'CZ': 'Czech Republic',
        'HU': 'Hungary', 'GR': 'Greece', 'PT': 'Portugal', 'IE': 'Ireland',
        'FI': 'Finland', 'NO': 'Norway', 'DK': 'Denmark', 'BE': 'Belgium', 'AT': 'Austria'
    }
    
    country_name = country_names.get(country_code, country_code)
    
    return {
        "name": country_name,
        "welcome": [
            {
                "icon": "🌍",
                "title": f"Welcome to {country_name}",
                "message": f"Discover the beauty and culture of {country_name}. Check the latest travel advisories and news updates below."
            }
        ],
        "transport": [
            "Check local transportation options and schedules",
            "Verify visa requirements and entry procedures",
            "Review health and safety guidelines",
            "Confirm accommodation bookings"
        ],
        "culture": [
            "Respect local customs and traditions",
            "Learn basic phrases in the local language",
            "Understand cultural norms and etiquette",
            "Be aware of local laws and regulations"
        ],
        "language": [
            {"native": "Hello", "meaning": "Greeting"},
            {"native": "Thank you", "meaning": "Expression of gratitude"},
            {"native": "Excuse me", "meaning": "Polite way to get attention"},
            {"native": "Help", "meaning": "Request for assistance"}
        ]
    }

@app.get("/api/country-info", response_model=CountryInfo)
async def get_country_info(country_code: str = "NP"):
    """Get travel information for a specific country"""
    if country_code not in TRAVEL_DATA:
        # Generate dynamic travel data for new countries
        country_info = generate_dynamic_country_info(country_code)
        return CountryInfo(**country_info)
    
    return CountryInfo(**TRAVEL_DATA[country_code])

@app.get("/api/anomalies")
async def get_anomalies() -> List[AnomalyAlert]:
    """Get current anomaly alerts for all countries"""
    alerts = []
    
    for country_code, config in COUNTRIES.items():
        analysis = calculate_baseline_and_anomaly(country_code)
        headlines = get_top_headlines(country_code)
        
        alerts.append(AnomalyAlert(
            country_code=country_code,
            country_name=config["name"],
            flag=config["flag"],
            current_count=analysis["current_count"],
            baseline=analysis["baseline"],
            spike_factor=analysis["spike_factor"],
            is_anomaly=analysis["is_anomaly"],
            top_headlines=headlines
        ))
    
    # Sort by spike factor (highest first)
    alerts.sort(key=lambda x: x.spike_factor, reverse=True)
    return alerts

async def collect_news_for_dynamic_country(country_code: str):
    """Collect news for a dynamically detected country"""
    country_names = {
        'US': 'United States', 'GB': 'United Kingdom', 'FR': 'France', 'DE': 'Germany',
        'IT': 'Italy', 'ES': 'Spain', 'JP': 'Japan', 'CN': 'China', 'IN': 'India',
        'AE': 'United Arab Emirates', 'AU': 'Australia', 'CA': 'Canada', 'MX': 'Mexico',
        'BR': 'Brazil', 'KR': 'South Korea', 'SG': 'Singapore', 'NL': 'Netherlands',
        'SE': 'Sweden', 'CH': 'Switzerland', 'TH': 'Thailand', 'PH': 'Philippines',
        'ID': 'Indonesia', 'MY': 'Malaysia', 'NZ': 'New Zealand', 'AR': 'Argentina',
        'CL': 'Chile', 'CO': 'Colombia', 'PE': 'Peru', 'EG': 'Egypt', 'ZA': 'South Africa',
        'IR': 'Iran', 'PK': 'Pakistan', 'BD': 'Bangladesh', 'LK': 'Sri Lanka',
        'RU': 'Russia', 'UA': 'Ukraine', 'PL': 'Poland', 'CZ': 'Czech Republic',
        'HU': 'Hungary', 'GR': 'Greece', 'PT': 'Portugal', 'IE': 'Ireland',
        'FI': 'Finland', 'NO': 'Norway', 'DK': 'Denmark', 'BE': 'Belgium', 'AT': 'Austria'
    }
    
    country_name = country_names.get(country_code, country_code)
    
    # Create dynamic RSS feeds for the country
    search_queries = [
        f"{country_name}+(visa+OR+entry+OR+immigration+OR+border+OR+travel+advisory)",
        f"{country_name}+travel+restrictions",
        f"{country_name}+entry+requirements",
        f"{country_name}+visa+policy"
    ]
    
    all_items = []
    for query in search_queries:
        feed_url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:10]:  # Limit to 10 per query
                item_id = hashlib.md5(f"{entry.link}{entry.title}".encode()).hexdigest()
                all_items.append({
                    'id': item_id,
                    'country_code': country_code,
                    'timestamp': datetime.now().isoformat(),
                    'title': entry.title,
                    'url': entry.link,
                    'source': entry.get('source', {}).get('title', 'Google News')
                })
        except Exception as e:
            print(f"Error fetching news for {country_code}: {e}")
            continue
    
    # Store items in database
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            for item in all_items:
                try:
                    conn.execute('''
                        INSERT OR REPLACE INTO news_items 
                        (id, country_code, timestamp, title, url, source)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        item['id'], item['country_code'], item['timestamp'],
                        item['title'], item['url'], item['source']
                    ))
                except Exception as e:
                    print(f"Error storing news item: {e}")
            conn.commit()

@app.get("/api/anomalies/{country_code}")
async def get_country_anomaly(country_code: str) -> AnomalyAlert:
    """Get anomaly alert for specific country"""
    # Check if country exists in our predefined list
    if country_code in COUNTRIES:
        config = COUNTRIES[country_code]
        analysis = calculate_baseline_and_anomaly(country_code)
        headlines = get_top_headlines(country_code, limit=5)
        country_name = config["name"]
        flag = config["flag"]
    else:
        # For new countries, generate basic data and try to collect news
        country_names = {
            'US': 'United States', 'GB': 'United Kingdom', 'FR': 'France', 'DE': 'Germany',
            'IT': 'Italy', 'ES': 'Spain', 'JP': 'Japan', 'CN': 'China', 'IN': 'India',
            'AE': 'United Arab Emirates', 'AU': 'Australia', 'CA': 'Canada', 'MX': 'Mexico',
            'BR': 'Brazil', 'KR': 'South Korea', 'SG': 'Singapore', 'NL': 'Netherlands',
            'SE': 'Sweden', 'CH': 'Switzerland', 'TH': 'Thailand', 'PH': 'Philippines',
            'ID': 'Indonesia', 'MY': 'Malaysia', 'NZ': 'New Zealand', 'AR': 'Argentina',
            'CL': 'Chile', 'CO': 'Colombia', 'PE': 'Peru', 'EG': 'Egypt', 'ZA': 'South Africa',
            'IR': 'Iran', 'PK': 'Pakistan', 'BD': 'Bangladesh', 'LK': 'Sri Lanka',
            'RU': 'Russia', 'UA': 'Ukraine', 'PL': 'Poland', 'CZ': 'Czech Republic',
            'HU': 'Hungary', 'GR': 'Greece', 'PT': 'Portugal', 'IE': 'Ireland',
            'FI': 'Finland', 'NO': 'Norway', 'DK': 'Denmark', 'BE': 'Belgium', 'AT': 'Austria'
        }
        country_name = country_names.get(country_code, country_code)
        flag = "🌍"  # Default flag for unknown countries
        
        # Try to collect news for this country dynamically
        await collect_news_for_dynamic_country(country_code)
        
        # Calculate analysis for the new country
        analysis = calculate_baseline_and_anomaly(country_code)
        headlines = get_top_headlines(country_code, limit=5)
    
    return AnomalyAlert(
        country_code=country_code,
        country_name=country_name,
        flag=flag,
        current_count=analysis["current_count"],
        baseline=analysis["baseline"],
        spike_factor=analysis["spike_factor"],
        is_anomaly=analysis["is_anomaly"],
        top_headlines=headlines
    )

@app.get("/api/stats/{country_code}")
async def get_country_stats(country_code: str):
    """Get detailed statistics for a country"""
    if country_code not in COUNTRIES:
        raise HTTPException(status_code=404, detail="Country not found")
    
    hourly_counts = get_hourly_counts(country_code, hours_back=168)  # 7 days
    
    counts = list(hourly_counts.values())
    if not counts:
        return {
            "country_code": country_code,
            "total_articles": 0,
            "avg_per_hour": 0,
            "max_per_hour": 0,
            "hours_with_data": 0
        }
    
    return {
        "country_code": country_code,
        "total_articles": sum(counts),
        "avg_per_hour": round(statistics.mean(counts), 2),
        "max_per_hour": max(counts),
        "hours_with_data": len([c for c in counts if c > 0]),
        "recent_hourly_counts": dict(list(hourly_counts.items())[-24:])  # Last 24 hours
    }

# Background task to collect news every 30 minutes
@app.on_event("startup")
async def startup_event():
    """Collect initial news data on startup"""
    print("Starting up - collecting initial news data...")
    await collect_news()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
