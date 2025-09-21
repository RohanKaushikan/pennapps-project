"""
Pattern Recognition and Intelligence Module
Adds cross-country analysis, relationship mapping, and historical intelligence
"""
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, Counter
import re

@dataclass
class CrossCountryPattern:
    pattern_type: str
    countries: List[str]
    requirement_text: str
    confidence: float
    frequency: int
    last_seen: str

@dataclass
class AlertRelationship:
    alert_id: str
    related_alerts: List[str]
    relationship_type: str  # 'dependency', 'conflict', 'similar'
    confidence: float
    description: str

@dataclass
class HistoricalTrend:
    requirement_type: str
    country_code: str
    trend_direction: str  # 'increasing', 'decreasing', 'stable'
    change_frequency: int
    seasonal_pattern: Optional[str]
    predicted_next_change: Optional[str]

@dataclass
class SmartRecommendation:
    recommendation_type: str
    title: str
    description: str
    confidence: float
    based_on: List[str]
    action_items: List[str]

class PatternAnalyzer:
    def __init__(self, db_path: str):
        self.db_path = db_path
        
        # Pattern recognition keywords
        self.requirement_categories = {
            'visa': ['visa', 'permit', 'authorization', 'entry clearance'],
            'health': ['vaccination', 'health certificate', 'medical', 'covid', 'pcr'],
            'documentation': ['passport', 'id', 'certificate', 'proof', 'document'],
            'customs': ['customs', 'duty', 'declaration', 'import', 'export'],
            'financial': ['insurance', 'funds', 'bank statement', 'financial proof']
        }
        
        self.seasonal_keywords = {
            'summer': ['summer', 'june', 'july', 'august', 'vacation'],
            'winter': ['winter', 'december', 'january', 'february', 'holiday'],
            'spring': ['spring', 'march', 'april', 'may'],
            'fall': ['fall', 'autumn', 'september', 'october', 'november']
        }

    def analyze_cross_country_patterns(self) -> List[CrossCountryPattern]:
        """Analyze similar requirements across different countries"""
        patterns = []
        
        with sqlite3.connect(self.db_path) as conn:
            # Get all legal requirements grouped by type, joining with news_items for country_code
            cursor = conn.execute('''
                SELECT ala.requirement_type, ala.requirement_text, ni.country_code, ala.created_at
                FROM alert_legal_analysis ala
                JOIN news_items ni ON ala.alert_id = ni.id
                WHERE ala.requirement_text != 'SUMMARY'
                ORDER BY ala.requirement_type, ala.created_at DESC
            ''')
            
            requirements_by_type = defaultdict(list)
            for row in cursor.fetchall():
                req_type, req_text, country, created_at = row
                requirements_by_type[req_type].append({
                    'text': req_text,
                    'country': country,
                    'created_at': created_at
                })
            
            # Find patterns within each requirement type
            for req_type, requirements in requirements_by_type.items():
                if len(requirements) < 2:
                    continue
                    
                # Group by similar text patterns
                text_groups = defaultdict(list)
                for req in requirements:
                    # Normalize text for comparison
                    normalized = self._normalize_requirement_text(req['text'])
                    text_groups[normalized].append(req)
                
                # Find patterns with multiple countries
                for normalized_text, group in text_groups.items():
                    if len(group) >= 2:
                        countries = list(set([req['country'] for req in group]))
                        if len(countries) >= 2:
                            patterns.append(CrossCountryPattern(
                                pattern_type=req_type,
                                countries=countries,
                                requirement_text=group[0]['text'],
                                confidence=min(len(countries) / 3.0, 1.0),
                                frequency=len(group),
                                last_seen=max([req['created_at'] for req in group])
                            ))
        
        return sorted(patterns, key=lambda x: x.confidence, reverse=True)

    def analyze_alert_relationships(self, alert_id: str) -> List[AlertRelationship]:
        """Analyze relationships between alerts"""
        relationships = []
        
        with sqlite3.connect(self.db_path) as conn:
            # Get the target alert
            cursor = conn.execute('''
                SELECT title, country_code, timestamp FROM news_items WHERE id = ?
            ''', (alert_id,))
            target_alert = cursor.fetchone()
            
            if not target_alert:
                return relationships
            
            target_title, target_country, target_timestamp = target_alert
            
            # Get other alerts from the same country
            cursor = conn.execute('''
                SELECT id, title, timestamp FROM news_items 
                WHERE country_code = ? AND id != ?
                ORDER BY timestamp DESC LIMIT 20
            ''', (target_country, alert_id))
            
            other_alerts = cursor.fetchall()
            
            for other_id, other_title, other_timestamp in other_alerts:
                relationship_type, confidence, description = self._analyze_relationship(
                    target_title, other_title, target_timestamp, other_timestamp
                )
                
                if confidence > 0.3:  # Only include meaningful relationships
                    relationships.append(AlertRelationship(
                        alert_id=alert_id,
                        related_alerts=[other_id],
                        relationship_type=relationship_type,
                        confidence=confidence,
                        description=description
                    ))
        
        return relationships

    def analyze_historical_trends(self, country_code: str = None) -> List[HistoricalTrend]:
        """Analyze historical trends in requirements"""
        trends = []
        
        with sqlite3.connect(self.db_path) as conn:
            # Get requirements over time
            query = '''
                SELECT requirement_type, created_at, requirement_text
                FROM alert_legal_analysis 
                WHERE requirement_text != 'SUMMARY'
            '''
            params = []
            
            if country_code:
                query += ' AND alert_id IN (SELECT id FROM news_items WHERE country_code = ?)'
                params.append(country_code)
            
            query += ' ORDER BY created_at DESC'
            
            cursor = conn.execute(query, params)
            requirements = cursor.fetchall()
            
            # Group by requirement type and analyze trends
            by_type = defaultdict(list)
            for req_type, created_at, req_text in requirements:
                by_type[req_type].append({
                    'created_at': created_at,
                    'text': req_text
                })
            
            for req_type, reqs in by_type.items():
                if len(reqs) < 3:
                    continue
                
                # Analyze frequency over time
                monthly_counts = defaultdict(int)
                for req in reqs:
                    month_key = req['created_at'][:7]  # YYYY-MM
                    monthly_counts[month_key] += 1
                
                # Determine trend direction
                months = sorted(monthly_counts.keys())
                if len(months) >= 2:
                    recent_avg = sum(monthly_counts[m] for m in months[-2:]) / 2
                    older_avg = sum(monthly_counts[m] for m in months[:-2]) / max(len(months) - 2, 1)
                    
                    if recent_avg > older_avg * 1.2:
                        trend_direction = 'increasing'
                    elif recent_avg < older_avg * 0.8:
                        trend_direction = 'decreasing'
                    else:
                        trend_direction = 'stable'
                    
                    # Check for seasonal patterns
                    seasonal_pattern = self._detect_seasonal_pattern(reqs)
                    
                    trends.append(HistoricalTrend(
                        requirement_type=req_type,
                        country_code=country_code or 'all',
                        trend_direction=trend_direction,
                        change_frequency=len(reqs),
                        seasonal_pattern=seasonal_pattern,
                        predicted_next_change=self._predict_next_change(monthly_counts)
                    ))
        
        return trends

    def generate_smart_recommendations(self, country_code: str, user_requirements: List[str] = None) -> List[SmartRecommendation]:
        """Generate smart recommendations based on patterns"""
        recommendations = []
        
        # Get cross-country patterns
        patterns = self.analyze_cross_country_patterns()
        
        # Get historical trends for the country
        trends = self.analyze_historical_trends(country_code)
        
        # Generate recommendations based on patterns
        for pattern in patterns:
            if country_code in pattern.countries and pattern.confidence > 0.6:
                recommendations.append(SmartRecommendation(
                    recommendation_type='cross_country_pattern',
                    title=f"Similar requirement in {len(pattern.countries)} countries",
                    description=f"'{pattern.requirement_text}' is also required in {', '.join(pattern.countries)}",
                    confidence=pattern.confidence,
                    based_on=[f"Pattern in {len(pattern.countries)} countries"],
                    action_items=[f"Check if this applies to {country_code}"]
                ))
        
        # Generate recommendations based on trends
        for trend in trends:
            if trend.trend_direction == 'increasing':
                recommendations.append(SmartRecommendation(
                    recommendation_type='trend_analysis',
                    title=f"Increasing {trend.requirement_type} requirements",
                    description=f"Requirements for {trend.requirement_type} are increasing in frequency",
                    confidence=0.7,
                    based_on=[f"Historical analysis of {trend.change_frequency} requirements"],
                    action_items=["Monitor for new requirements", "Prepare documentation early"]
                ))
        
        # Generate seasonal recommendations
        current_month = datetime.now().month
        for trend in trends:
            if trend.seasonal_pattern and self._is_seasonal_relevant(trend.seasonal_pattern, current_month):
                recommendations.append(SmartRecommendation(
                    recommendation_type='seasonal',
                    title=f"Seasonal {trend.requirement_type} pattern detected",
                    description=f"Requirements typically change during {trend.seasonal_pattern}",
                    confidence=0.6,
                    based_on=[f"Historical seasonal analysis"],
                    action_items=[f"Watch for updates during {trend.seasonal_pattern}"]
                ))
        
        return sorted(recommendations, key=lambda x: x.confidence, reverse=True)

    def _normalize_requirement_text(self, text: str) -> str:
        """Normalize text for pattern matching"""
        # Remove common variations and normalize
        normalized = text.lower()
        normalized = re.sub(r'\b(?:must|shall|required|mandatory)\b', 'required', normalized)
        normalized = re.sub(r'\b(?:visa|permit|authorization)\b', 'visa', normalized)
        normalized = re.sub(r'\b(?:passport|travel document)\b', 'passport', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized.strip()

    def _analyze_relationship(self, title1: str, title2: str, time1: str, time2: str) -> Tuple[str, float, str]:
        """Analyze relationship between two alerts"""
        # Check for similar keywords
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())
        common_words = words1.intersection(words2)
        
        if len(common_words) >= 2:
            # Check for dependency keywords
            dependency_keywords = ['before', 'after', 'then', 'next', 'followed by']
            if any(kw in title1.lower() or kw in title2.lower() for kw in dependency_keywords):
                return 'dependency', 0.8, f"Sequential requirements: {title1} → {title2}"
            
            # Check for conflict keywords
            conflict_keywords = ['instead', 'alternative', 'either', 'or', 'not both']
            if any(kw in title1.lower() or kw in title2.lower() for kw in conflict_keywords):
                return 'conflict', 0.7, f"Conflicting requirements: {title1} vs {title2}"
            
            # Similar requirements
            similarity = len(common_words) / max(len(words1), len(words2))
            if similarity > 0.3:
                return 'similar', similarity, f"Similar requirements: {title1} and {title2}"
        
        return 'unrelated', 0.0, "No clear relationship"

    def _detect_seasonal_pattern(self, requirements: List[Dict]) -> Optional[str]:
        """Detect seasonal patterns in requirements"""
        month_counts = defaultdict(int)
        for req in requirements:
            try:
                month = datetime.fromisoformat(req['created_at']).month
                month_counts[month] += 1
            except:
                continue
        
        if len(month_counts) < 3:
            return None
        
        # Check for seasonal patterns
        summer_months = [6, 7, 8]
        winter_months = [12, 1, 2]
        
        summer_count = sum(month_counts[m] for m in summer_months if m in month_counts)
        winter_count = sum(month_counts[m] for m in winter_months if m in month_counts)
        
        if summer_count > winter_count * 1.5:
            return 'summer'
        elif winter_count > summer_count * 1.5:
            return 'winter'
        
        return None

    def _predict_next_change(self, monthly_counts: Dict[str, int]) -> Optional[str]:
        """Predict when the next change might occur"""
        if len(monthly_counts) < 3:
            return None
        
        # Simple prediction based on recent frequency
        recent_months = sorted(monthly_counts.keys())[-3:]
        avg_frequency = sum(monthly_counts[m] for m in recent_months) / len(recent_months)
        
        if avg_frequency > 2:
            next_month = datetime.now() + timedelta(days=30)
            return next_month.strftime('%Y-%m')
        
        return None

    def _is_seasonal_relevant(self, seasonal_pattern: str, current_month: int) -> bool:
        """Check if seasonal pattern is currently relevant"""
        if seasonal_pattern == 'summer':
            return current_month in [5, 6, 7, 8, 9]
        elif seasonal_pattern == 'winter':
            return current_month in [11, 12, 1, 2, 3]
        return False
