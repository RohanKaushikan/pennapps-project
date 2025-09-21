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
from nlp_processor import NLPProcessor, AlertIntelligence
from legal_analyzer import LegalTextAnalyzer, AlertLegalAnalysis, LegalRequirement
from alert_enhancer import AlertEnhancer, EnhancedAlert, AlertIntelligenceOverlay, DetailedAlertAnalysis
from background_processor import BackgroundProcessor
from pattern_analyzer import PatternAnalyzer, CrossCountryPattern, AlertRelationship, HistoricalTrend, SmartRecommendation

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

        conn.execute('''
            CREATE TABLE IF NOT EXISTS alert_intelligence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT NOT NULL,
                legal_requirements TEXT,
                recommendations TEXT,
                effective_dates TEXT,
                deadlines TEXT,
                penalties TEXT,
                document_requirements TEXT,
                compliance_urgency TEXT,
                requirement_keywords TEXT,
                legal_language_keywords TEXT,
                time_indicators TEXT,
                legal_classification TEXT,
                risk_level TEXT,
                traveler_impact TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(alert_id)
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS alert_legal_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT NOT NULL,
                requirement_text TEXT,
                requirement_type TEXT NOT NULL,
                penalty_severity TEXT NOT NULL,
                compliance_deadline TEXT,
                legal_authority TEXT,
                enforcement_likelihood TEXT NOT NULL,
                fine_amount TEXT,
                document_validity_period TEXT,
                entry_exit_specific TEXT NOT NULL,
                overall_severity TEXT,
                critical_deadlines TEXT,
                mandatory_documents TEXT,
                penalty_summary TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (alert_id) REFERENCES news_items (id)
            )
        ''')

        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_legal_analysis_alert_id ON alert_legal_analysis(alert_id)
        ''')

        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_legal_analysis_requirement_type ON alert_legal_analysis(requirement_type)
        ''')

        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_legal_analysis_penalty_severity ON alert_legal_analysis(penalty_severity)
        ''')

        # Predictive insights for individual alerts (stored separately)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS predictive_insights (
                alert_id TEXT PRIMARY KEY,
                related_requirements TEXT,
                predicted_documents TEXT,
                processing_time_days INTEGER,
                forecast_change_window TEXT,
                violation_probability REAL,
                consequence_severity TEXT,
                appeal_success_probability REAL,
                upcoming_deadlines TEXT,
                preparation_timeline TEXT,
                potential_compliance_issues TEXT,
                created_at TEXT NOT NULL
            )
        ''')

        # Country risk previews for quick risk summaries
        conn.execute('''
            CREATE TABLE IF NOT EXISTS country_risk_preview (
                country_code TEXT PRIMARY KEY,
                risk_level TEXT,
                violation_probability_avg REAL,
                top_concerns TEXT,
                suggested_preparation_days INTEGER,
                upcoming_deadlines TEXT,
                generated_at TEXT NOT NULL
            )
        ''')
        conn.commit()

# Initialize database on startup
init_db()

# Initialize NLP processor, legal analyzer, and alert enhancer
nlp_processor = NLPProcessor()
legal_analyzer = LegalTextAnalyzer()
alert_enhancer = AlertEnhancer(nlp_processor, legal_analyzer)

# Initialize background processor
background_processor = BackgroundProcessor(DB_PATH)

# Initialize pattern analyzer
pattern_analyzer = PatternAnalyzer(DB_PATH)

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

class ProcessAlertRequest(BaseModel):
    alert_id: str
    content: str
    spike_factor: Optional[float] = 1.0

class AlertIntelligenceResponse(BaseModel):
    alert_id: str
    legal_requirements: List[str]
    recommendations: List[str]
    effective_dates: List[str]
    deadlines: List[str]
    penalties: List[str]
    document_requirements: List[str]
    compliance_urgency: str
    requirement_keywords: List[str]
    legal_language_keywords: List[str]
    time_indicators: List[str]
    legal_classification: str
    risk_level: str
    traveler_impact: str
    created_at: str

class LegalRequirementResponse(BaseModel):
    requirement_text: str
    requirement_type: str
    penalty_severity: str
    compliance_deadline: Optional[str]
    legal_authority: Optional[str]
    enforcement_likelihood: str
    fine_amount: Optional[str]
    document_validity_period: Optional[str]
    entry_exit_specific: str

class AlertLegalAnalysisResponse(BaseModel):
    alert_id: str
    requirements: List[LegalRequirementResponse]
    overall_severity: str
    critical_deadlines: List[str]
    mandatory_documents: List[str]
    penalty_summary: str
    created_at: str

class ProcessLegalAnalysisRequest(BaseModel):
    alert_id: str
    content: str

class AlertIntelligenceOverlayResponse(BaseModel):
    risk_score: int
    requirement_type: str
    penalties: List[str]
    urgency_level: str
    legal_category: str
    compliance_deadline: Optional[str]
    fine_amounts: List[str]
    document_requirements: List[str]
    confidence_score: float

class EnhancedAlertResponse(BaseModel):
    # Original alert data
    id: str
    country_code: str
    timestamp: str
    title: str
    url: str
    source: str
    # ML insights overlay
    intelligence: Optional[AlertIntelligenceOverlayResponse]

class DetailedAlertAnalysisResponse(BaseModel):
    alert_id: str
    legal_requirements: List[Dict]
    compliance_timeline: List[Dict]
    penalty_information: Dict
    related_requirements: List[str]
    risk_assessment: Dict
    action_items: List[str]

class BatchProcessingRequest(BaseModel):
    country_code: str
    limit: Optional[int] = 50

class BatchProcessingResponse(BaseModel):
    country_code: str
    processed_count: int
    success_count: int
    error_count: int
    processing_time: float
    status: str

# Pattern Analysis Models
class CrossCountryPatternResponse(BaseModel):
    pattern_type: str
    countries: List[str]
    requirement_text: str
    confidence: float
    frequency: int
    last_seen: str

class AlertRelationshipResponse(BaseModel):
    alert_id: str
    related_alerts: List[str]
    relationship_type: str
    confidence: float
    description: str

class HistoricalTrendResponse(BaseModel):
    requirement_type: str
    country_code: str
    trend_direction: str
    change_frequency: int
    seasonal_pattern: Optional[str]
    predicted_next_change: Optional[str]

class SmartRecommendationResponse(BaseModel):
    recommendation_type: str
    title: str
    description: str
    confidence: float
    based_on: List[str]
    action_items: List[str]

class PatternAnalysisResponse(BaseModel):
    cross_country_patterns: List[CrossCountryPatternResponse]
    alert_relationships: List[AlertRelationshipResponse]
    historical_trends: List[HistoricalTrendResponse]
    smart_recommendations: List[SmartRecommendationResponse]
    analysis_timestamp: str

class SeasonalPredictionResponse(BaseModel):
    requirement_type: str
    country_code: str
    seasonal_pattern: Optional[str]
    predicted_next_change: Optional[str]
    confidence: float
    rationale: List[str]

class CountryRelationshipsResponse(BaseModel):
    country_code: str
    relationships: List[AlertRelationshipResponse]

class PredictiveInsightResponse(BaseModel):
    alert_id: str
    related_requirements: List[str]
    predicted_documents: List[str]
    processing_time_days: int
    forecast_change_window: Optional[str]
    violation_probability: float
    consequence_severity: str
    appeal_success_probability: float
    upcoming_deadlines: List[str]
    preparation_timeline: List[str]
    potential_compliance_issues: List[str]
    created_at: str

class CountryRiskPreviewResponse(BaseModel):
    country_code: str
    risk_level: str
    violation_probability_avg: float
    top_concerns: List[str]
    suggested_preparation_days: int
    upcoming_deadlines: List[str]
    generated_at: str

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

def store_alert_intelligence(intelligence: AlertIntelligence):
    """Store alert intelligence in database"""
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO alert_intelligence (
                    alert_id, legal_requirements, recommendations, effective_dates,
                    deadlines, penalties, document_requirements, compliance_urgency,
                    requirement_keywords, legal_language_keywords, time_indicators,
                    legal_classification, risk_level, traveler_impact, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                intelligence.alert_id,
                json.dumps(intelligence.legal_requirements),
                json.dumps(intelligence.recommendations),
                json.dumps(intelligence.effective_dates),
                json.dumps(intelligence.deadlines),
                json.dumps(intelligence.penalties),
                json.dumps(intelligence.document_requirements),
                intelligence.compliance_urgency,
                json.dumps(intelligence.requirement_keywords),
                json.dumps(intelligence.legal_language_keywords),
                json.dumps(intelligence.time_indicators),
                intelligence.legal_classification,
                intelligence.risk_level,
                intelligence.traveler_impact,
                intelligence.created_at
            ))
            conn.commit()

def get_alert_intelligence(alert_id: str) -> Optional[AlertIntelligence]:
    """Retrieve alert intelligence from database"""
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute('''
                SELECT * FROM alert_intelligence WHERE alert_id = ?
            ''', (alert_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return AlertIntelligence(
                alert_id=row[1],
                legal_requirements=json.loads(row[2]),
                recommendations=json.loads(row[3]),
                effective_dates=json.loads(row[4]),
                deadlines=json.loads(row[5]),
                penalties=json.loads(row[6]),
                document_requirements=json.loads(row[7]),
                compliance_urgency=row[8],
                requirement_keywords=json.loads(row[9]),
                legal_language_keywords=json.loads(row[10]),
                time_indicators=json.loads(row[11]),
                legal_classification=row[12],
                risk_level=row[13],
                traveler_impact=row[14],
                created_at=row[15]
            )

def store_legal_analysis(analysis: AlertLegalAnalysis):
    """Store legal analysis in database"""
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            # First, store the main analysis record
            conn.execute('''
                INSERT OR REPLACE INTO alert_legal_analysis (
                    alert_id, requirement_text, requirement_type, penalty_severity,
                    compliance_deadline, legal_authority, enforcement_likelihood,
                    fine_amount, document_validity_period, entry_exit_specific,
                    overall_severity, critical_deadlines, mandatory_documents,
                    penalty_summary, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                analysis.alert_id,
                'SUMMARY',  # Main summary record
                'summary',
                analysis.overall_severity,
                None,
                None,
                'high',
                None,
                None,
                'both',
                analysis.overall_severity,
                json.dumps(analysis.critical_deadlines),
                json.dumps(analysis.mandatory_documents),
                analysis.penalty_summary,
                analysis.created_at
            ))

            # Store individual requirements
            for req in analysis.requirements:
                conn.execute('''
                    INSERT INTO alert_legal_analysis (
                        alert_id, requirement_text, requirement_type, penalty_severity,
                        compliance_deadline, legal_authority, enforcement_likelihood,
                        fine_amount, document_validity_period, entry_exit_specific,
                        overall_severity, critical_deadlines, mandatory_documents,
                        penalty_summary, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    analysis.alert_id,
                    req.requirement_text,
                    req.requirement_type,
                    req.penalty_severity,
                    req.compliance_deadline,
                    req.legal_authority,
                    req.enforcement_likelihood,
                    req.fine_amount,
                    req.document_validity_period,
                    req.entry_exit_specific,
                    analysis.overall_severity,
                    json.dumps(analysis.critical_deadlines),
                    json.dumps(analysis.mandatory_documents),
                    analysis.penalty_summary,
                    analysis.created_at
                ))
            conn.commit()

def get_legal_analysis(alert_id: str) -> Optional[AlertLegalAnalysis]:
    """Retrieve legal analysis from database"""
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            # Get summary record
            summary_cursor = conn.execute('''
                SELECT overall_severity, critical_deadlines, mandatory_documents,
                       penalty_summary, created_at
                FROM alert_legal_analysis
                WHERE alert_id = ? AND requirement_text = 'SUMMARY'
                LIMIT 1
            ''', (alert_id,))
            summary_row = summary_cursor.fetchone()

            if not summary_row:
                return None

            # Get individual requirements
            req_cursor = conn.execute('''
                SELECT requirement_text, requirement_type, penalty_severity,
                       compliance_deadline, legal_authority, enforcement_likelihood,
                       fine_amount, document_validity_period, entry_exit_specific
                FROM alert_legal_analysis
                WHERE alert_id = ? AND requirement_text != 'SUMMARY'
            ''', (alert_id,))

            requirements = []
            for row in req_cursor.fetchall():
                requirements.append(LegalRequirement(
                    requirement_text=row[0],
                    requirement_type=row[1],
                    penalty_severity=row[2],
                    compliance_deadline=row[3],
                    legal_authority=row[4],
                    enforcement_likelihood=row[5],
                    fine_amount=row[6],
                    document_validity_period=row[7],
                    entry_exit_specific=row[8]
                ))

            return AlertLegalAnalysis(
                alert_id=alert_id,
                requirements=requirements,
                overall_severity=summary_row[0],
                critical_deadlines=json.loads(summary_row[1]),
                mandatory_documents=json.loads(summary_row[2]),
                penalty_summary=summary_row[3],
                created_at=summary_row[4]
            )

# -----------------------------
# Predictive Insights Utilities
# -----------------------------

def store_predictive_insight(data: Dict[str, Any]):
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO predictive_insights (
                    alert_id, related_requirements, predicted_documents, processing_time_days,
                    forecast_change_window, violation_probability, consequence_severity,
                    appeal_success_probability, upcoming_deadlines, preparation_timeline,
                    potential_compliance_issues, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['alert_id'],
                json.dumps(data.get('related_requirements', [])),
                json.dumps(data.get('predicted_documents', [])),
                data.get('processing_time_days', 7),
                data.get('forecast_change_window'),
                data.get('violation_probability', 0.2),
                data.get('consequence_severity', 'low'),
                data.get('appeal_success_probability', 0.3),
                json.dumps(data.get('upcoming_deadlines', [])),
                json.dumps(data.get('preparation_timeline', [])),
                json.dumps(data.get('potential_compliance_issues', [])),
                data.get('created_at', datetime.now().isoformat())
            ))
            conn.commit()

def get_predictive_insight(alert_id: str) -> Optional[Dict[str, Any]]:
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute('SELECT * FROM predictive_insights WHERE alert_id = ?', (alert_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                'alert_id': row[0],
                'related_requirements': json.loads(row[1] or '[]'),
                'predicted_documents': json.loads(row[2] or '[]'),
                'processing_time_days': row[3],
                'forecast_change_window': row[4],
                'violation_probability': row[5],
                'consequence_severity': row[6],
                'appeal_success_probability': row[7],
                'upcoming_deadlines': json.loads(row[8] or '[]'),
                'preparation_timeline': json.loads(row[9] or '[]'),
                'potential_compliance_issues': json.loads(row[10] or '[]'),
                'created_at': row[11]
            }

def generate_predictive_insight(alert_id: str) -> Dict[str, Any]:
    """Heuristic prediction using existing intelligence, legal analysis, and trends."""
    # Fetch alert
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute('SELECT title, country_code FROM news_items WHERE id = ?', (alert_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Alert not found")
            title, country_code = row

    # Use existing intelligence/analysis if present
    intelligence = get_alert_intelligence(alert_id)
    legal = get_legal_analysis(alert_id)
    trends = pattern_analyzer.analyze_historical_trends(country_code)

    related_reqs = []
    predicted_docs = []
    processing_days = 7
    forecast_window = None
    violation_prob = 0.2
    consequence_severity = 'low'
    appeal_prob = 0.3
    upcoming_deadlines: List[str] = []
    prep_timeline: List[str] = []
    compliance_issues: List[str] = []

    # From intelligence
    if intelligence:
        # Related requirements based on requirement_keywords and legal_classification
        related_reqs.extend(intelligence.requirement_keywords[:5])
        if intelligence.legal_classification in ['mandatory', 'prohibited']:
            consequence_severity = 'high' if intelligence.legal_classification == 'prohibited' else 'medium'
        # Document predictions
        predicted_docs.extend(intelligence.document_requirements[:5])
        # Processing time heuristic
        if any(k in title.lower() for k in ['visa', 'permit']):
            processing_days = 21
        elif any(k in title.lower() for k in ['vaccination', 'health']):
            processing_days = 3
        elif any(k in title.lower() for k in ['passport', 'document']):
            processing_days = 10
        # Violation probability influenced by risk_level
        risk_map = {'low': 0.2, 'medium': 0.4, 'high': 0.6, 'critical': 0.8}
        violation_prob = max(violation_prob, risk_map.get(intelligence.risk_level.lower(), 0.3))

    # From legal analysis
    if legal:
        for req in legal.requirements[:5]:
            related_reqs.append(req.requirement_type)
            # Check for document validity period (placeholder for future enhancement)
            if req.document_validity_period:
                pass  # placeholder; primary docs come from intelligence above
            if req.compliance_deadline:
                upcoming_deadlines.append(req.compliance_deadline)
            if req.penalty_severity in ['high', 'severe']:
                consequence_severity = 'high'
                violation_prob = max(violation_prob, 0.6)
        # Appeal probability simple heuristic
        appeal_prob = 0.25 if consequence_severity == 'high' else 0.35

    # From trends
    if trends:
        # Use any predicted next change window
        next_changes = [t.predicted_next_change for t in trends if t.predicted_next_change]
        forecast_window = next_changes[0] if next_changes else None
        # Preparation suggestions
        if any(t.trend_direction == 'increasing' for t in trends):
            prep_timeline.append('Begin documentation as soon as possible (increasing requirements)')
        if any(t.seasonal_pattern for t in trends):
            prep_timeline.append('Expect seasonal changes; verify requirements during travel month')

    # Compliance issues suggestions
    if 'insurance' in title.lower():
        compliance_issues.append('Verify insurance coverage amount and validity period')
    if 'transit' in title.lower():
        compliance_issues.append('Check transit visa requirements and layover rules')

    # Deduplicate and finalize
    related_reqs = list(dict.fromkeys([r for r in related_reqs if r]))
    predicted_docs = list(dict.fromkeys([d for d in predicted_docs if d]))
    upcoming_deadlines = list(dict.fromkeys(upcoming_deadlines))
    created_at = datetime.now().isoformat()

    return {
        'alert_id': alert_id,
        'related_requirements': related_reqs,
        'predicted_documents': predicted_docs,
        'processing_time_days': processing_days,
        'forecast_change_window': forecast_window,
        'violation_probability': round(min(max(violation_prob, 0.0), 1.0), 2),
        'consequence_severity': consequence_severity,
        'appeal_success_probability': round(appeal_prob, 2),
        'upcoming_deadlines': upcoming_deadlines,
        'preparation_timeline': prep_timeline,
        'potential_compliance_issues': compliance_issues,
        'created_at': created_at
    }

def store_country_risk_preview(data: Dict[str, Any]):
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO country_risk_preview (
                    country_code, risk_level, violation_probability_avg, top_concerns,
                    suggested_preparation_days, upcoming_deadlines, generated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['country_code'],
                data.get('risk_level', 'low'),
                data.get('violation_probability_avg', 0.2),
                json.dumps(data.get('top_concerns', [])),
                data.get('suggested_preparation_days', 7),
                json.dumps(data.get('upcoming_deadlines', [])),
                data.get('generated_at', datetime.now().isoformat())
            ))
            conn.commit()

def get_country_risk_preview(country_code: str) -> Optional[Dict[str, Any]]:
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute('SELECT * FROM country_risk_preview WHERE country_code = ?', (country_code,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                'country_code': row[0],
                'risk_level': row[1],
                'violation_probability_avg': row[2],
                'top_concerns': json.loads(row[3] or '[]'),
                'suggested_preparation_days': row[4],
                'upcoming_deadlines': json.loads(row[5] or '[]'),
                'generated_at': row[6]
            }

def generate_country_risk_preview(country_code: str) -> Dict[str, Any]:
    """Heuristic country risk preview based on recent alerts and trends."""
    if country_code not in COUNTRIES:
        raise HTTPException(status_code=404, detail="Country not found")

    alerts = get_alerts_for_country(country_code, limit=20)
    trends = pattern_analyzer.analyze_historical_trends(country_code)

    violation_probs = []
    concerns_counter = Counter()
    deadlines: List[str] = []
    suggested_prep = 7

    for alert in alerts[:10]:
        # Use existing predictive insight if available; otherwise generate lightweight estimate
        pi = get_predictive_insight(alert['id'])
        if not pi:
            try:
                pi = generate_predictive_insight(alert['id'])
            except Exception:
                pi = None
        if pi:
            violation_probs.append(pi['violation_probability'])
            for r in pi['related_requirements']:
                concerns_counter[r] += 1
            deadlines.extend(pi['upcoming_deadlines'])
            suggested_prep = max(suggested_prep, pi['processing_time_days'])

    avg_violation = round(sum(violation_probs) / len(violation_probs), 2) if violation_probs else 0.2
    top_concerns = [t[0] for t in concerns_counter.most_common(5)]
    deadlines = list(dict.fromkeys(deadlines))

    # Risk level heuristic using anomalies and trends
    anomaly = calculate_baseline_and_anomaly(country_code)
    risk_level = 'low'
    if anomaly.get('is_anomaly') and anomaly.get('spike_factor', 1) >= 2:
        risk_level = 'high'
    if any(t.trend_direction == 'increasing' for t in trends):
        risk_level = 'medium' if risk_level == 'low' else risk_level

    return {
        'country_code': country_code,
        'risk_level': risk_level,
        'violation_probability_avg': avg_violation,
        'top_concerns': top_concerns,
        'suggested_preparation_days': suggested_prep,
        'upcoming_deadlines': deadlines,
        'generated_at': datetime.now().isoformat()
    }

def get_alerts_for_country(country_code: str, limit: int = 50) -> List[Dict]:
    """Get recent alerts for a specific country"""
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute('''
                SELECT id, country_code, timestamp, title, url, source
                FROM news_items
                WHERE country_code = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (country_code, limit))

            alerts = []
            for row in cursor.fetchall():
                alerts.append({
                    'id': row[0],
                    'country_code': row[1],
                    'timestamp': row[2],
                    'title': row[3],
                    'url': row[4],
                    'source': row[5]
                })

            return alerts

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

@app.post("/api/ml/process-alert", response_model=AlertIntelligenceResponse)
async def process_alert(request: ProcessAlertRequest):
    """Process alert content with NLP and return enhanced metadata"""
    try:
        # Check if alert intelligence already exists
        existing_intelligence = get_alert_intelligence(request.alert_id)
        if existing_intelligence:
            # Return existing intelligence without reprocessing
            return AlertIntelligenceResponse(
                alert_id=existing_intelligence.alert_id,
                legal_requirements=existing_intelligence.legal_requirements,
                recommendations=existing_intelligence.recommendations,
                effective_dates=existing_intelligence.effective_dates,
                deadlines=existing_intelligence.deadlines,
                penalties=existing_intelligence.penalties,
                document_requirements=existing_intelligence.document_requirements,
                compliance_urgency=existing_intelligence.compliance_urgency,
                requirement_keywords=existing_intelligence.requirement_keywords,
                legal_language_keywords=existing_intelligence.legal_language_keywords,
                time_indicators=existing_intelligence.time_indicators,
                legal_classification=existing_intelligence.legal_classification,
                risk_level=existing_intelligence.risk_level,
                traveler_impact=existing_intelligence.traveler_impact,
                created_at=existing_intelligence.created_at
            )

        # Process the alert content with NLP
        intelligence = nlp_processor.process_alert_content(
            alert_id=request.alert_id,
            content=request.content,
            spike_factor=request.spike_factor
        )

        # Store the intelligence in database
        store_alert_intelligence(intelligence)

        # Return the enhanced metadata
        return AlertIntelligenceResponse(
            alert_id=intelligence.alert_id,
            legal_requirements=intelligence.legal_requirements,
            recommendations=intelligence.recommendations,
            effective_dates=intelligence.effective_dates,
            deadlines=intelligence.deadlines,
            penalties=intelligence.penalties,
            document_requirements=intelligence.document_requirements,
            compliance_urgency=intelligence.compliance_urgency,
            requirement_keywords=intelligence.requirement_keywords,
            legal_language_keywords=intelligence.legal_language_keywords,
            time_indicators=intelligence.time_indicators,
            legal_classification=intelligence.legal_classification,
            risk_level=intelligence.risk_level,
            traveler_impact=intelligence.traveler_impact,
            created_at=intelligence.created_at
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing alert: {str(e)}")

@app.get("/api/ml/alert-intelligence/{alert_id}", response_model=AlertIntelligenceResponse)
async def get_alert_intelligence_endpoint(alert_id: str):
    """Get existing alert intelligence by alert ID"""
    intelligence = get_alert_intelligence(alert_id)
    if not intelligence:
        raise HTTPException(status_code=404, detail="Alert intelligence not found")

    return AlertIntelligenceResponse(
        alert_id=intelligence.alert_id,
        legal_requirements=intelligence.legal_requirements,
        recommendations=intelligence.recommendations,
        effective_dates=intelligence.effective_dates,
        deadlines=intelligence.deadlines,
        penalties=intelligence.penalties,
        document_requirements=intelligence.document_requirements,
        compliance_urgency=intelligence.compliance_urgency,
        requirement_keywords=intelligence.requirement_keywords,
        legal_language_keywords=intelligence.legal_language_keywords,
        time_indicators=intelligence.time_indicators,
        legal_classification=intelligence.legal_classification,
        risk_level=intelligence.risk_level,
        traveler_impact=intelligence.traveler_impact,
        created_at=intelligence.created_at
    )

@app.post("/api/legal/analyze-alert", response_model=AlertLegalAnalysisResponse)
async def analyze_alert_legal(request: ProcessLegalAnalysisRequest):
    """Analyze alert content for legal requirements and compliance obligations"""
    try:
        # Check if legal analysis already exists
        existing_analysis = get_legal_analysis(request.alert_id)
        if existing_analysis:
            # Return existing analysis without reprocessing
            requirements_response = [
                LegalRequirementResponse(
                    requirement_text=req.requirement_text,
                    requirement_type=req.requirement_type,
                    penalty_severity=req.penalty_severity,
                    compliance_deadline=req.compliance_deadline,
                    legal_authority=req.legal_authority,
                    enforcement_likelihood=req.enforcement_likelihood,
                    fine_amount=req.fine_amount,
                    document_validity_period=req.document_validity_period,
                    entry_exit_specific=req.entry_exit_specific
                ) for req in existing_analysis.requirements
            ]

            return AlertLegalAnalysisResponse(
                alert_id=existing_analysis.alert_id,
                requirements=requirements_response,
                overall_severity=existing_analysis.overall_severity,
                critical_deadlines=existing_analysis.critical_deadlines,
                mandatory_documents=existing_analysis.mandatory_documents,
                penalty_summary=existing_analysis.penalty_summary,
                created_at=existing_analysis.created_at
            )

        # Process the alert content with legal analyzer
        analysis = legal_analyzer.analyze_alert_content(
            alert_id=request.alert_id,
            content=request.content
        )

        # Store the legal analysis in database
        store_legal_analysis(analysis)

        # Convert to response format
        requirements_response = [
            LegalRequirementResponse(
                requirement_text=req.requirement_text,
                requirement_type=req.requirement_type,
                penalty_severity=req.penalty_severity,
                compliance_deadline=req.compliance_deadline,
                legal_authority=req.legal_authority,
                enforcement_likelihood=req.enforcement_likelihood,
                fine_amount=req.fine_amount,
                document_validity_period=req.document_validity_period,
                entry_exit_specific=req.entry_exit_specific
            ) for req in analysis.requirements
        ]

        return AlertLegalAnalysisResponse(
            alert_id=analysis.alert_id,
            requirements=requirements_response,
            overall_severity=analysis.overall_severity,
            critical_deadlines=analysis.critical_deadlines,
            mandatory_documents=analysis.mandatory_documents,
            penalty_summary=analysis.penalty_summary,
            created_at=analysis.created_at
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing legal content: {str(e)}")

@app.get("/api/legal/alert-analysis/{alert_id}", response_model=AlertLegalAnalysisResponse)
async def get_alert_legal_analysis(alert_id: str):
    """Get existing legal analysis by alert ID"""
    analysis = get_legal_analysis(alert_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Legal analysis not found")

    requirements_response = [
        LegalRequirementResponse(
            requirement_text=req.requirement_text,
            requirement_type=req.requirement_type,
            penalty_severity=req.penalty_severity,
            compliance_deadline=req.compliance_deadline,
            legal_authority=req.legal_authority,
            enforcement_likelihood=req.enforcement_likelihood,
            fine_amount=req.fine_amount,
            document_validity_period=req.document_validity_period,
            entry_exit_specific=req.entry_exit_specific
        ) for req in analysis.requirements
    ]

    return AlertLegalAnalysisResponse(
        alert_id=analysis.alert_id,
        requirements=requirements_response,
        overall_severity=analysis.overall_severity,
        critical_deadlines=analysis.critical_deadlines,
        mandatory_documents=analysis.mandatory_documents,
        penalty_summary=analysis.penalty_summary,
        created_at=analysis.created_at
    )

@app.get("/api/legal/requirements-by-type")
async def get_requirements_by_type(requirement_type: str = "mandatory"):
    """Get all legal requirements filtered by type (mandatory/recommended/prohibited)"""
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute('''
                SELECT alert_id, requirement_text, penalty_severity, enforcement_likelihood,
                       fine_amount, compliance_deadline
                FROM alert_legal_analysis
                WHERE requirement_type = ? AND requirement_text != 'SUMMARY'
                ORDER BY penalty_severity DESC, enforcement_likelihood DESC
            ''', (requirement_type,))

            requirements = []
            for row in cursor.fetchall():
                requirements.append({
                    "alert_id": row[0],
                    "requirement_text": row[1],
                    "penalty_severity": row[2],
                    "enforcement_likelihood": row[3],
                    "fine_amount": row[4],
                    "compliance_deadline": row[5]
                })

            return {
                "requirement_type": requirement_type,
                "count": len(requirements),
                "requirements": requirements
            }

@app.get("/api/legal/penalties-summary")
async def get_penalties_summary():
    """Get summary of penalties across all legal analyses"""
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            # Get penalty severity distribution
            severity_cursor = conn.execute('''
                SELECT penalty_severity, COUNT(*) as count
                FROM alert_legal_analysis
                WHERE requirement_text != 'SUMMARY'
                GROUP BY penalty_severity
                ORDER BY count DESC
            ''')

            severity_distribution = dict(severity_cursor.fetchall())

            # Get enforcement likelihood distribution
            enforcement_cursor = conn.execute('''
                SELECT enforcement_likelihood, COUNT(*) as count
                FROM alert_legal_analysis
                WHERE requirement_text != 'SUMMARY'
                GROUP BY enforcement_likelihood
                ORDER BY count DESC
            ''')

            enforcement_distribution = dict(enforcement_cursor.fetchall())

            # Get alerts with fines
            fines_cursor = conn.execute('''
                SELECT alert_id, fine_amount, penalty_severity
                FROM alert_legal_analysis
                WHERE fine_amount IS NOT NULL AND requirement_text != 'SUMMARY'
                ORDER BY penalty_severity DESC
            ''')

            fines = [{"alert_id": row[0], "fine_amount": row[1], "penalty_severity": row[2]}
                    for row in fines_cursor.fetchall()]

            return {
                "penalty_severity_distribution": severity_distribution,
                "enforcement_likelihood_distribution": enforcement_distribution,
                "alerts_with_fines": fines,
                "total_requirements_analyzed": sum(severity_distribution.values())
            }

@app.get("/api/alerts/{country_code}/enhanced", response_model=List[EnhancedAlertResponse])
async def get_enhanced_alerts_for_country(country_code: str, limit: int = 20):
    """Get enhanced alerts with ML insights for a specific country"""
    if country_code not in COUNTRIES:
        raise HTTPException(status_code=404, detail="Country not found")

    try:
        # Get basic alerts
        alerts = get_alerts_for_country(country_code, limit)
        enhanced_alerts = []

        for alert in alerts:
            try:
                # Enhance each alert with ML insights
                enhanced_alert = alert_enhancer.enhance_alert(alert, alert['title'])

                # Convert to response format
                intelligence_response = None
                if enhanced_alert.intelligence:
                    intelligence_response = AlertIntelligenceOverlayResponse(
                        risk_score=enhanced_alert.intelligence.risk_score,
                        requirement_type=enhanced_alert.intelligence.requirement_type,
                        penalties=enhanced_alert.intelligence.penalties,
                        urgency_level=enhanced_alert.intelligence.urgency_level,
                        legal_category=enhanced_alert.intelligence.legal_category,
                        compliance_deadline=enhanced_alert.intelligence.compliance_deadline,
                        fine_amounts=enhanced_alert.intelligence.fine_amounts,
                        document_requirements=enhanced_alert.intelligence.document_requirements,
                        confidence_score=enhanced_alert.intelligence.confidence_score
                    )

                enhanced_response = EnhancedAlertResponse(
                    id=enhanced_alert.id,
                    country_code=enhanced_alert.country_code,
                    timestamp=enhanced_alert.timestamp,
                    title=enhanced_alert.title,
                    url=enhanced_alert.url,
                    source=enhanced_alert.source,
                    intelligence=intelligence_response
                )

                enhanced_alerts.append(enhanced_response)

            except Exception as e:
                # If enhancement fails, include original alert without intelligence
                print(f"Enhancement failed for alert {alert['id']}: {e}")
                enhanced_response = EnhancedAlertResponse(
                    id=alert['id'],
                    country_code=alert['country_code'],
                    timestamp=alert['timestamp'],
                    title=alert['title'],
                    url=alert['url'],
                    source=alert['source'],
                    intelligence=None
                )
                enhanced_alerts.append(enhanced_response)

        # Sort by risk score (highest first), then by timestamp
        enhanced_alerts.sort(key=lambda x: (
            x.intelligence.risk_score if x.intelligence else 0,
            x.timestamp
        ), reverse=True)

        return enhanced_alerts

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error enhancing alerts: {str(e)}")

@app.get("/api/alerts/{alert_id}/analysis", response_model=DetailedAlertAnalysisResponse)
async def get_detailed_alert_analysis(alert_id: str):
    """Get detailed analysis for a single alert"""
    try:
        # Get the original alert
        with db_lock:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.execute('''
                    SELECT title, url FROM news_items WHERE id = ?
                ''', (alert_id,))
                result = cursor.fetchone()

                if not result:
                    raise HTTPException(status_code=404, detail="Alert not found")

                title, url = result

        # Create detailed analysis
        detailed_analysis = alert_enhancer.create_detailed_analysis(alert_id, title)

        return DetailedAlertAnalysisResponse(
            alert_id=detailed_analysis.alert_id,
            legal_requirements=detailed_analysis.legal_requirements,
            compliance_timeline=detailed_analysis.compliance_timeline,
            penalty_information=detailed_analysis.penalty_information,
            related_requirements=detailed_analysis.related_requirements,
            risk_assessment=detailed_analysis.risk_assessment,
            action_items=detailed_analysis.action_items
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating detailed analysis: {str(e)}")

@app.post("/api/ml/enhance-country-alerts/{country_code}", response_model=BatchProcessingResponse)
async def batch_enhance_country_alerts(country_code: str, request: BatchProcessingRequest):
    """Batch process all alerts for a country to generate ML insights"""
    if country_code not in COUNTRIES:
        raise HTTPException(status_code=404, detail="Country not found")

    start_time = datetime.now()

    try:
        # Get alerts for the country
        alerts = get_alerts_for_country(country_code, request.limit)

        processed_count = 0
        success_count = 0
        error_count = 0

        for alert in alerts:
            processed_count += 1
            try:
                # Process NLP intelligence
                nlp_intelligence = nlp_processor.process_alert_content(
                    alert_id=alert['id'],
                    content=alert['title']
                )
                store_alert_intelligence(nlp_intelligence)

                # Process legal analysis
                legal_analysis = legal_analyzer.analyze_alert_content(
                    alert_id=alert['id'],
                    content=alert['title']
                )
                store_legal_analysis(legal_analysis)

                success_count += 1

            except Exception as e:
                print(f"Error processing alert {alert['id']}: {e}")
                error_count += 1

        processing_time = (datetime.now() - start_time).total_seconds()

        return BatchProcessingResponse(
            country_code=country_code,
            processed_count=processed_count,
            success_count=success_count,
            error_count=error_count,
            processing_time=processing_time,
            status="completed" if error_count == 0 else "completed_with_errors"
        )

    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")

@app.get("/api/alerts/prioritized")
async def get_prioritized_alerts(limit: int = 50):
    """Get alerts prioritized by risk score and urgency across all countries"""
    try:
        enhanced_alerts = []

        # Get alerts from all countries
        for country_code in COUNTRIES.keys():
            alerts = get_alerts_for_country(country_code, limit // len(COUNTRIES))

            for alert in alerts:
                try:
                    enhanced_alert = alert_enhancer.enhance_alert(alert, alert['title'])

                    # Create prioritized alert info
                    priority_info = {
                        'alert_id': enhanced_alert.id,
                        'country_code': enhanced_alert.country_code,
                        'title': enhanced_alert.title,
                        'timestamp': enhanced_alert.timestamp,
                        'url': enhanced_alert.url,
                        'risk_score': enhanced_alert.intelligence.risk_score if enhanced_alert.intelligence else 0,
                        'requirement_type': enhanced_alert.intelligence.requirement_type if enhanced_alert.intelligence else 'informational',
                        'urgency_level': enhanced_alert.intelligence.urgency_level if enhanced_alert.intelligence else 'low',
                        'legal_category': enhanced_alert.intelligence.legal_category if enhanced_alert.intelligence else 'mixed',
                        'has_penalties': len(enhanced_alert.intelligence.penalties) > 0 if enhanced_alert.intelligence else False,
                        'compliance_deadline': enhanced_alert.intelligence.compliance_deadline if enhanced_alert.intelligence else None
                    }

                    enhanced_alerts.append(priority_info)

                except Exception as e:
                    print(f"Error enhancing alert {alert['id']}: {e}")

        # Sort by priority: Critical > Important > Informational, then by risk score
        priority_order = {'critical': 3, 'important': 2, 'informational': 1}
        enhanced_alerts.sort(key=lambda x: (
            priority_order.get(x['requirement_type'], 0),
            x['risk_score'],
            x['timestamp']
        ), reverse=True)

        # Group by priority level
        critical_alerts = [a for a in enhanced_alerts if a['requirement_type'] == 'critical']
        important_alerts = [a for a in enhanced_alerts if a['requirement_type'] == 'important']
        informational_alerts = [a for a in enhanced_alerts if a['requirement_type'] == 'informational']

        return {
            'total_alerts': len(enhanced_alerts),
            'critical_count': len(critical_alerts),
            'important_count': len(important_alerts),
            'informational_count': len(informational_alerts),
            'alerts': {
                'critical': critical_alerts[:10],  # Top 10 of each
                'important': important_alerts[:10],
                'informational': informational_alerts[:10]
            },
            'highest_risk_score': max([a['risk_score'] for a in enhanced_alerts], default=0),
            'countries_with_critical_alerts': list(set([a['country_code'] for a in critical_alerts]))
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting prioritized alerts: {str(e)}")

@app.post("/api/background/start")
async def start_background_processing():
    """Start the background alert processing service"""
    try:
        background_processor.start_background_processing()
        return {
            "status": "started",
            "message": "Background alert processing has been started",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start background processing: {str(e)}")

@app.post("/api/background/stop")
async def stop_background_processing():
    """Stop the background alert processing service"""
    try:
        background_processor.stop_background_processing()
        return {
            "status": "stopped",
            "message": "Background alert processing has been stopped",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop background processing: {str(e)}")

@app.get("/api/background/status")
async def get_background_processing_status():
    """Get the status of background alert processing"""
    try:
        status = background_processor.get_status()
        return {
            "background_processing": status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get background processing status: {str(e)}")

@app.get("/api/system/health")
async def get_system_health():
    """Get comprehensive system health including background processing"""
    try:
        # Get basic health
        with db_lock:
            with sqlite3.connect(DB_PATH) as conn:
                # Count total news items
                cursor = conn.execute("SELECT COUNT(*) FROM news_items")
                total_alerts = cursor.fetchone()[0]

                # Count processed alerts
                cursor = conn.execute("SELECT COUNT(DISTINCT alert_id) FROM alert_intelligence")
                nlp_processed = cursor.fetchone()[0]

                cursor = conn.execute("SELECT COUNT(DISTINCT alert_id) FROM alert_legal_analysis WHERE requirement_text = 'SUMMARY'")
                legal_processed = cursor.fetchone()[0]

                # Get recent activity
                recent_time = (datetime.now() - timedelta(hours=24)).isoformat()
                cursor = conn.execute("SELECT COUNT(*) FROM news_items WHERE timestamp > ?", (recent_time,))
                recent_alerts = cursor.fetchone()[0]

        # Get background processing status
        bg_status = background_processor.get_status()

        return {
            "status": "healthy",
            "database": {
                "total_alerts": total_alerts,
                "nlp_processed": nlp_processed,
                "legal_processed": legal_processed,
                "processing_coverage": f"{min(nlp_processed, legal_processed) / max(total_alerts, 1) * 100:.1f}%",
                "recent_24h": recent_alerts
            },
            "background_processing": bg_status,
            "api_endpoints": {
                "basic_alerts": "/api/anomalies",
                "enhanced_alerts": "/api/alerts/{country_code}/enhanced",
                "detailed_analysis": "/api/alerts/{alert_id}/analysis",
                "prioritized_alerts": "/api/alerts/prioritized",
                "cross_country_patterns": "/api/intelligence/cross-country-patterns",
                "alert_relationships": "/api/intelligence/alert-relationships/{alert_id}",
                "historical_trends": "/api/intelligence/historical-trends",
                "smart_recommendations": "/api/intelligence/smart-recommendations/{country_code}",
                "pattern_analysis": "/api/intelligence/pattern-analysis/{country_code}",
                "relationships_by_country": "/api/intelligence/relationships-by-country/{country_code}",
                "seasonal_predictions": "/api/intelligence/seasonal-predictions/{country_code}",
                "predictive_alert": "/api/predictions/alert/{alert_id}",
                "predictive_alert_bulk": "/api/predictions/alerts/{country_code}",
                "predictive_country": "/api/predictions/country/{country_code}"
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"System health check failed: {str(e)}")

# Pattern Analysis API Endpoints

@app.get("/api/intelligence/cross-country-patterns", response_model=List[CrossCountryPatternResponse])
async def get_cross_country_patterns():
    """Get cross-country requirement patterns"""
    try:
        patterns = pattern_analyzer.analyze_cross_country_patterns()
        return [
            CrossCountryPatternResponse(
                pattern_type=p.pattern_type,
                countries=p.countries,
                requirement_text=p.requirement_text,
                confidence=p.confidence,
                frequency=p.frequency,
                last_seen=p.last_seen
            ) for p in patterns
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing cross-country patterns: {str(e)}")

@app.get("/api/intelligence/alert-relationships/{alert_id}", response_model=List[AlertRelationshipResponse])
async def get_alert_relationships(alert_id: str):
    """Get relationships for a specific alert"""
    try:
        relationships = pattern_analyzer.analyze_alert_relationships(alert_id)
        return [
            AlertRelationshipResponse(
                alert_id=r.alert_id,
                related_alerts=r.related_alerts,
                relationship_type=r.relationship_type,
                confidence=r.confidence,
                description=r.description
            ) for r in relationships
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing alert relationships: {str(e)}")

@app.get("/api/intelligence/historical-trends", response_model=List[HistoricalTrendResponse])
async def get_historical_trends(country_code: Optional[str] = None):
    """Get historical trends in requirements"""
    try:
        trends = pattern_analyzer.analyze_historical_trends(country_code)
        return [
            HistoricalTrendResponse(
                requirement_type=t.requirement_type,
                country_code=t.country_code,
                trend_direction=t.trend_direction,
                change_frequency=t.change_frequency,
                seasonal_pattern=t.seasonal_pattern,
                predicted_next_change=t.predicted_next_change
            ) for t in trends
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing historical trends: {str(e)}")

@app.get("/api/intelligence/smart-recommendations/{country_code}", response_model=List[SmartRecommendationResponse])
async def get_smart_recommendations(country_code: str, user_requirements: Optional[str] = None):
    """Get smart recommendations for a country"""
    try:
        if country_code not in COUNTRIES:
            raise HTTPException(status_code=404, detail="Country not found")
        
        requirements = json.loads(user_requirements) if user_requirements else None
        recommendations = pattern_analyzer.generate_smart_recommendations(country_code, requirements)
        
        return [
            SmartRecommendationResponse(
                recommendation_type=r.recommendation_type,
                title=r.title,
                description=r.description,
                confidence=r.confidence,
                based_on=r.based_on,
                action_items=r.action_items
            ) for r in recommendations
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")

@app.get("/api/intelligence/pattern-analysis/{country_code}", response_model=PatternAnalysisResponse)
async def get_comprehensive_pattern_analysis(country_code: str):
    """Get comprehensive pattern analysis for a country"""
    try:
        if country_code not in COUNTRIES:
            raise HTTPException(status_code=404, detail="Country not found")
        
        # Get all pattern analyses
        cross_country_patterns = pattern_analyzer.analyze_cross_country_patterns()
        historical_trends = pattern_analyzer.analyze_historical_trends(country_code)
        smart_recommendations = pattern_analyzer.generate_smart_recommendations(country_code)
        
        # Get recent alerts for relationship analysis
        recent_alerts = get_alerts_for_country(country_code, limit=5)
        alert_relationships = []
        for alert in recent_alerts:
            relationships = pattern_analyzer.analyze_alert_relationships(alert['id'])
            alert_relationships.extend(relationships)
        
        return PatternAnalysisResponse(
            cross_country_patterns=[
                CrossCountryPatternResponse(
                    pattern_type=p.pattern_type,
                    countries=p.countries,
                    requirement_text=p.requirement_text,
                    confidence=p.confidence,
                    frequency=p.frequency,
                    last_seen=p.last_seen
                ) for p in cross_country_patterns
            ],
            alert_relationships=[
                AlertRelationshipResponse(
                    alert_id=r.alert_id,
                    related_alerts=r.related_alerts,
                    relationship_type=r.relationship_type,
                    confidence=r.confidence,
                    description=r.description
                ) for r in alert_relationships
            ],
            historical_trends=[
                HistoricalTrendResponse(
                    requirement_type=t.requirement_type,
                    country_code=t.country_code,
                    trend_direction=t.trend_direction,
                    change_frequency=t.change_frequency,
                    seasonal_pattern=t.seasonal_pattern,
                    predicted_next_change=t.predicted_next_change
                ) for t in historical_trends
            ],
            smart_recommendations=[
                SmartRecommendationResponse(
                    recommendation_type=r.recommendation_type,
                    title=r.title,
                    description=r.description,
                    confidence=r.confidence,
                    based_on=r.based_on,
                    action_items=r.action_items
                ) for r in smart_recommendations
            ],
            analysis_timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error performing pattern analysis: {str(e)}")

# -----------------------------
# Predictive Insights Endpoints
# -----------------------------

@app.get("/api/predictions/alert/{alert_id}", response_model=PredictiveInsightResponse)
async def get_or_generate_alert_prediction(alert_id: str):
    """Return stored predictive insight for an alert, or generate and store it if missing."""
    try:
        data = get_predictive_insight(alert_id)
        if not data:
            data = generate_predictive_insight(alert_id)
            store_predictive_insight(data)
        return PredictiveInsightResponse(**data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting alert prediction: {str(e)}")

@app.post("/api/predictions/alert/{alert_id}", response_model=PredictiveInsightResponse)
async def regenerate_alert_prediction(alert_id: str):
    """Force regenerate and upsert predictive insight for an alert."""
    try:
        data = generate_predictive_insight(alert_id)
        store_predictive_insight(data)
        return PredictiveInsightResponse(**data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error regenerating alert prediction: {str(e)}")

@app.get("/api/predictions/alerts/{country_code}", response_model=List[PredictiveInsightResponse])
async def list_alert_predictions_for_country(country_code: str, limit: int = 10):
    """Return predictions for recent alerts in a country (generate on-demand if absent)."""
    try:
        if country_code not in COUNTRIES:
            raise HTTPException(status_code=404, detail="Country not found")

        alerts = get_alerts_for_country(country_code, limit=limit)
        results: List[PredictiveInsightResponse] = []
        for alert in alerts:
            data = get_predictive_insight(alert['id'])
            if not data:
                try:
                    data = generate_predictive_insight(alert['id'])
                    store_predictive_insight(data)
                except Exception:
                    continue
            results.append(PredictiveInsightResponse(**data))
        return results
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing alert predictions: {str(e)}")

@app.get("/api/predictions/country/{country_code}", response_model=CountryRiskPreviewResponse)
async def get_or_generate_country_prediction(country_code: str):
    """Return stored country risk preview, or generate and store it if missing."""
    try:
        if country_code not in COUNTRIES:
            raise HTTPException(status_code=404, detail="Country not found")
        data = get_country_risk_preview(country_code)
        if not data:
            data = generate_country_risk_preview(country_code)
            store_country_risk_preview(data)
        return CountryRiskPreviewResponse(**data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting country prediction: {str(e)}")

@app.post("/api/predictions/country/{country_code}", response_model=CountryRiskPreviewResponse)
async def regenerate_country_prediction(country_code: str):
    """Force regenerate and upsert country risk preview."""
    try:
        if country_code not in COUNTRIES:
            raise HTTPException(status_code=404, detail="Country not found")
        data = generate_country_risk_preview(country_code)
        store_country_risk_preview(data)
        return CountryRiskPreviewResponse(**data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error regenerating country prediction: {str(e)}")

@app.get("/api/intelligence/relationships-by-country/{country_code}", response_model=CountryRelationshipsResponse)
async def get_relationships_by_country(country_code: str, limit: int = 10):
    """Get alert relationships across recent alerts for a given country.
    This aggregates relationships discovered between recent alerts within the same country.
    """
    try:
        if country_code not in COUNTRIES:
            raise HTTPException(status_code=404, detail="Country not found")

        recent_alerts = get_alerts_for_country(country_code, limit=limit)
        aggregated: List[AlertRelationshipResponse] = []

        for alert in recent_alerts:
            rels = pattern_analyzer.analyze_alert_relationships(alert['id'])
            for r in rels:
                aggregated.append(AlertRelationshipResponse(
                    alert_id=r.alert_id,
                    related_alerts=r.related_alerts,
                    relationship_type=r.relationship_type,
                    confidence=r.confidence,
                    description=r.description
                ))

        return CountryRelationshipsResponse(country_code=country_code, relationships=aggregated)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error aggregating relationships: {str(e)}")

@app.get("/api/intelligence/seasonal-predictions/{country_code}", response_model=List[SeasonalPredictionResponse])
async def get_seasonal_predictions(country_code: str):
    """Provide seasonal predictions and upcoming change hints per requirement type for a country.
    Builds on historical trend analysis to surface user-friendly insights and confidences.
    """
    try:
        if country_code not in COUNTRIES:
            raise HTTPException(status_code=404, detail="Country not found")

        trends = pattern_analyzer.analyze_historical_trends(country_code)
        predictions: List[SeasonalPredictionResponse] = []

        for t in trends:
            # Derive a simple confidence score
            base_conf = 0.5
            if t.trend_direction == 'increasing':
                base_conf += 0.2
            elif t.trend_direction == 'decreasing':
                base_conf += 0.1
            # Boost if we have seasonal signal or explicit next-change estimate
            if t.seasonal_pattern:
                base_conf += 0.15
            if t.predicted_next_change:
                base_conf += 0.05
            confidence = min(base_conf, 0.95)

            rationale = [
                f"Observed {t.trend_direction} trend across {t.change_frequency} historical items"
            ]
            if t.seasonal_pattern:
                rationale.append(f"Seasonal pattern detected: {t.seasonal_pattern}")
            if t.predicted_next_change:
                rationale.append(f"Likely change window: {t.predicted_next_change}")

            predictions.append(SeasonalPredictionResponse(
                requirement_type=t.requirement_type,
                country_code=country_code,
                seasonal_pattern=t.seasonal_pattern,
                predicted_next_change=t.predicted_next_change,
                confidence=round(confidence, 2),
                rationale=rationale
            ))

        # Order by confidence descending
        predictions.sort(key=lambda p: p.confidence, reverse=True)
        return predictions
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating seasonal predictions: {str(e)}")

# Background task to collect news every 30 minutes
@app.on_event("startup")
async def startup_event():
    """Collect initial news data and start background processing on startup"""
    print("Starting up - collecting initial news data...")
    try:
        await collect_news()
        print("Initial news collection completed")
    except Exception as e:
        print(f"Warning: Failed to collect initial news: {e}")

    # Start background ML processing
    print("Starting background ML processing...")
    try:
        background_processor.start_background_processing()
        print("Background processing started successfully")
    except Exception as e:
        print(f"Warning: Failed to start background processing: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown of background processing"""
    print("Shutting down - stopping background processing...")
    try:
        background_processor.stop_background_processing()
        print("Background processing stopped successfully")
    except Exception as e:
        print(f"Warning: Failed to stop background processing: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
