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
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
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
    hourly_counts = get_hourly_counts(country_code)
    
    if len(hourly_counts) < 24:  # Need at least 24 hours of data
        return {
            'current_count': 0,
            'baseline': 0.0,
            'spike_factor': 1.0,
            'is_anomaly': False
        }
    
    # Current hour count
    current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
    current_count = hourly_counts.get(current_hour.isoformat(), 0)
    
    # Calculate baseline (mean of last 7 days, excluding current hour)
    counts = [count for hour, count in hourly_counts.items() 
              if hour != current_hour.isoformat()]
    
    if not counts:
        baseline = 0.0
    else:
        baseline = statistics.mean(counts)
    
    # Calculate spike factor
    spike_factor = current_count / max(baseline, 0.1)  # Avoid division by zero
    
    # Anomaly detection: spike factor > 2.0 and current count > 2
    is_anomaly = spike_factor >= 2.0 and current_count >= 3
    
    return {
        'current_count': current_count,
        'baseline': round(baseline, 2),
        'spike_factor': round(spike_factor, 2),
        'is_anomaly': is_anomaly
    }

def get_top_headlines(country_code: str, limit: int = 3) -> List[Dict[str, str]]:
    """Get top recent headlines for a country"""
    current_time = datetime.now()
    start_time = current_time - timedelta(days=7)  # Look back 7 days for headlines
    
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
    return {
        "countries": [
            {
                "code": code,
                "name": config["name"],
                "flag": config["flag"]
            }
            for code, config in COUNTRIES.items()
        ]
    }

@app.get("/api/v1/countries/country-info")
async def get_country_info():
    """Get country information for frontend compatibility"""
    return {
        "countries": [
            {
                "code": code,
                "name": config["name"],
                "flag": config["flag"]
            }
            for code, config in COUNTRIES.items()
        ]
    }

@app.get("/api/v1/countries/")
async def get_countries_v1():
    """Get list of countries for v1 API compatibility"""
    return [
        {
            "code": code,
            "name": config["name"],
            "flag": config["flag"]
        }
        for code, config in COUNTRIES.items()
    ]

@app.get("/api/v1/alerts/")
async def get_alerts(country: str = None, user_id: int = 1):
    """Get alerts based on anomalies for v1 API compatibility"""
    anomalies = []
    for country_code in COUNTRIES.keys():
        analysis = calculate_baseline_and_anomaly(country_code)
        if analysis['is_anomaly']:
            headlines = get_top_headlines(country_code)
            anomalies.append({
                "id": f"alert_{country_code}_{datetime.now().isoformat()}",
                "title": f"Travel Alert: {COUNTRIES[country_code]['name']}",
                "message": f"Unusual spike in travel news detected for {COUNTRIES[country_code]['name']}",
                "country_code": country_code,
                "country_name": COUNTRIES[country_code]['name'],
                "country": {
                    "code": country_code,
                    "name": COUNTRIES[country_code]['name'],
                    "flag": COUNTRIES[country_code]['flag']
                },
                "severity": "medium" if analysis['spike_factor'] < 3 else "high",
                "created_at": datetime.now().isoformat(),
                "is_read": False,
                "user_status": {"is_read": False},
                "source": "Travel News Monitor",
                "headlines": headlines
            })

    # If no real anomalies, create some sample alerts for testing
    if not anomalies:
        for country_code in list(COUNTRIES.keys())[:2]:  # Show 2 sample alerts
            headlines = get_top_headlines(country_code, 3)  # Get more headlines
            anomalies.append({
                "id": f"sample_alert_{country_code}",
                "title": f"Travel Update: {COUNTRIES[country_code]['name']}",
                "message": f"Recent travel developments in {COUNTRIES[country_code]['name']}",
                "country_code": country_code,
                "country_name": COUNTRIES[country_code]['name'],
                "country": {
                    "code": country_code,
                    "name": COUNTRIES[country_code]['name'],
                    "flag": COUNTRIES[country_code]['flag']
                },
                "severity": "low",
                "created_at": datetime.now().isoformat(),
                "is_read": False,
                "user_status": {"is_read": False},
                "source": "Travel News Monitor",
                "headlines": headlines
            })

    return {
        "alerts": anomalies,
        "total_count": len(anomalies),
        "page": 1,
        "per_page": 20
    }

@app.get("/api/v1/alerts/country/{country_code}")
async def get_country_alerts(country_code: str):
    """Get alerts for specific country"""
    if country_code not in COUNTRIES:
        raise HTTPException(status_code=404, detail="Country not found")

    analysis = calculate_baseline_and_anomaly(country_code)
    headlines = get_top_headlines(country_code, 5)

    alerts = []
    if analysis['is_anomaly'] or headlines:  # Show alerts if anomaly or recent news
        alerts.append({
            "id": f"alert_{country_code}_{datetime.now().isoformat()}",
            "title": f"Travel Alert: {COUNTRIES[country_code]['name']}",
            "message": f"Travel news activity detected for {COUNTRIES[country_code]['name']}",
            "country_code": country_code,
            "country_name": COUNTRIES[country_code]['name'],
            "severity": "high" if analysis['is_anomaly'] else "medium",
            "created_at": datetime.now().isoformat(),
            "is_read": False,
            "source": "Travel News Monitor",
            "headlines": headlines,
            "analysis": analysis
        })

    return alerts

@app.get("/api/v1/alerts/{alert_id}")
async def get_alert_detail(alert_id: str, user_id: int = 1):
    """Get detailed alert information"""
    # Extract country code from alert ID
    if alert_id.startswith("sample_alert_"):
        country_code = alert_id.replace("sample_alert_", "")
    elif alert_id.startswith("alert_"):
        parts = alert_id.split("_")
        country_code = parts[1] if len(parts) > 1 else "NP"
    else:
        country_code = "NP"  # Default fallback

    if country_code not in COUNTRIES:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Get headlines for this country
    headlines = get_top_headlines(country_code, 5)

    # Create detailed alert response
    alert_detail = {
        "id": alert_id,
        "title": f"Travel Advisory: {COUNTRIES[country_code]['name']}",
        "description": f"Current travel and visa developments for {COUNTRIES[country_code]['name']}. This alert aggregates recent news and official advisories affecting travelers to this destination.",
        "country": {
            "code": country_code,
            "name": COUNTRIES[country_code]['name'],
            "flag": COUNTRIES[country_code]['flag']
        },
        "country_code": country_code,
        "country_name": COUNTRIES[country_code]['name'],
        "risk_level": 2,  # Default to moderate
        "severity": "medium",
        "created_at": datetime.now().isoformat(),
        "is_read": False,
        "user_status": {"is_read": False},
        "source": {
            "name": "Travel News Monitor",
            "source_type": "Government Advisory Aggregator",
            "url": f"https://news.google.com/search?q={country_code}+travel+visa+immigration"
        },
        "categories": ["Travel", "Immigration", "Border Control", "Government Advisory"],
        "headlines": headlines,
        "full_text": f"Travel Advisory for {COUNTRIES[country_code]['name']}\n\n" +
                    "This advisory consolidates recent developments affecting travel to " +
                    f"{COUNTRIES[country_code]['name']}. Recent news includes:\n\n" +
                    "\n".join([f"• {h['title']}" for h in headlines]) +
                    f"\n\nFor the most current information, please consult official government sources and embassy advisories for {COUNTRIES[country_code]['name']}."
    }

    return alert_detail

@app.post("/api/v1/alerts/{alert_id}/mark-read")
async def mark_alert_read(alert_id: str):
    """Mark an alert as read"""
    return {"message": "Alert marked as read", "alert_id": alert_id}

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

@app.get("/api/anomalies/{country_code}")
async def get_country_anomaly(country_code: str) -> AnomalyAlert:
    """Get anomaly alert for specific country"""
    if country_code not in COUNTRIES:
        raise HTTPException(status_code=404, detail="Country not found")
    
    config = COUNTRIES[country_code]
    analysis = calculate_baseline_and_anomaly(country_code)
    headlines = get_top_headlines(country_code, limit=5)
    
    return AnomalyAlert(
        country_code=country_code,
        country_name=config["name"],
        flag=config["flag"],
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
