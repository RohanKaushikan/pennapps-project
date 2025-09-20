import spacy
import re
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json

# Load spaCy model (you'll need to download it: python -m spacy download en_core_web_sm)
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Warning: spaCy model not found. Run: python -m spacy download en_core_web_sm")
    nlp = None

@dataclass
class ScrapedContent:
    source_id: str
    country_code: str
    url: str
    content: str
    content_hash: str
    scraped_at: str
    content_type: str

@dataclass
class Alert:
    id: str
    country_code: str
    title: str
    description: str
    risk_level: str
    categories: List[str]
    source_url: str
    created_at: str
    expires_at: str
    confidence_score: float

@dataclass
class LocationTrigger:
    user_id: str
    country_code: str
    lat: float
    lng: float
    entry_detected_at: str

@dataclass
class ChangeDetection:
    old_content_hash: str
    new_content_hash: str
    change_type: str
    confidence: float
    key_changes: List[str]

class TravelContentProcessor:
    def __init__(self):
        self.nlp = nlp
        self.risk_keywords = {
            "high": ["urgent", "critical", "dangerous", "avoid", "prohibited", "banned", "emergency", "crisis"],
            "medium": ["caution", "warning", "restriction", "limited", "delayed", "changed", "updated"],
            "low": ["information", "notice", "reminder", "guidance", "recommendation", "suggestion"]
        }
        
        self.category_keywords = {
            "visa": ["visa", "passport", "entry", "immigration", "border", "customs"],
            "entry_requirements": ["requirement", "document", "certificate", "permit", "authorization"],
            "health": ["vaccination", "health", "medical", "quarantine", "covid", "disease"],
            "safety": ["safety", "security", "crime", "terrorism", "violence", "danger"],
            "transport": ["flight", "airport", "transportation", "travel", "border crossing"],
            "currency": ["money", "currency", "exchange", "payment", "cash", "card"]
        }

    def process_scraped_content(self, content_data: Dict[str, Any]) -> List[Alert]:
        """Process scraped content and generate alerts"""
        if not self.nlp:
            return []
            
        content = content_data.get("content", "")
        country_code = content_data.get("country_code", "")
        source_url = content_data.get("url", "")
        
        # Clean and preprocess content
        cleaned_content = self._clean_content(content)
        
        # Extract entities and key information
        doc = self.nlp(cleaned_content)
        
        # Generate alerts based on content analysis
        alerts = []
        
        # Extract sentences that might contain important information
        sentences = [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 20]
        
        for sentence in sentences:
            alert = self._analyze_sentence(sentence, country_code, source_url)
            if alert:
                alerts.append(alert)
        
        return alerts

    def _clean_content(self, content: str) -> str:
        """Clean HTML and extract text content"""
        # Remove HTML tags
        clean = re.compile('<.*?>')
        text = re.sub(clean, '', content)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s.,!?;:()\-]', '', text)
        
        return text.strip()

    def _analyze_sentence(self, sentence: str, country_code: str, source_url: str) -> Optional[Alert]:
        """Analyze a sentence and create an alert if it contains important information"""
        if not self.nlp:
            return None
            
        doc = self.nlp(sentence)
        
        # Determine risk level
        risk_level = self._determine_risk_level(sentence)
        
        # Extract categories
        categories = self._extract_categories(sentence)
        
        # Only create alert if it has relevant categories
        if not categories:
            return None
            
        # Generate title and description
        title = self._generate_title(sentence, categories)
        description = sentence[:200] + "..." if len(sentence) > 200 else sentence
        
        # Calculate confidence score
        confidence = self._calculate_confidence(sentence, categories, risk_level)
        
        # Generate alert
        alert = Alert(
            id=self._generate_alert_id(sentence, country_code),
            country_code=country_code,
            title=title,
            description=description,
            risk_level=risk_level,
            categories=categories,
            source_url=source_url,
            created_at=datetime.now().isoformat() + "Z",
            expires_at=(datetime.now() + timedelta(days=30)).isoformat() + "Z",
            confidence_score=confidence
        )
        
        return alert

    def _determine_risk_level(self, text: str) -> str:
        """Determine risk level based on keywords"""
        text_lower = text.lower()
        
        high_count = sum(1 for keyword in self.risk_keywords["high"] if keyword in text_lower)
        medium_count = sum(1 for keyword in self.risk_keywords["medium"] if keyword in text_lower)
        low_count = sum(1 for keyword in self.risk_keywords["low"] if keyword in text_lower)
        
        if high_count > 0:
            return "high"
        elif medium_count > 0:
            return "medium"
        else:
            return "low"

    def _extract_categories(self, text: str) -> List[str]:
        """Extract relevant categories from text"""
        text_lower = text.lower()
        categories = []
        
        for category, keywords in self.category_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                categories.append(category)
        
        return categories

    def _generate_title(self, sentence: str, categories: List[str]) -> str:
        """Generate a concise title for the alert"""
        # Extract key phrases using spaCy
        if not self.nlp:
            return sentence[:50] + "..."
            
        doc = self.nlp(sentence)
        
        # Get noun phrases
        noun_phrases = [chunk.text for chunk in doc.noun_chunks]
        
        # Get important entities
        entities = [ent.text for ent in doc.ents if ent.label_ in ["PERSON", "ORG", "GPE", "EVENT"]]
        
        # Combine and create title
        key_phrases = noun_phrases[:2] + entities[:1]
        title = " ".join(key_phrases)
        
        if len(title) > 60:
            title = title[:60] + "..."
            
        return title or sentence[:50] + "..."

    def _calculate_confidence(self, sentence: str, categories: List[str], risk_level: str) -> float:
        """Calculate confidence score for the alert"""
        confidence = 0.5  # Base confidence
        
        # Increase confidence based on categories
        confidence += len(categories) * 0.1
        
        # Increase confidence for high-risk content
        if risk_level == "high":
            confidence += 0.2
        elif risk_level == "medium":
            confidence += 0.1
        
        # Increase confidence for longer, more detailed sentences
        if len(sentence) > 100:
            confidence += 0.1
        
        return min(confidence, 1.0)

    def _generate_alert_id(self, sentence: str, country_code: str) -> str:
        """Generate unique alert ID"""
        content = f"{country_code}_{sentence}_{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()

    def detect_changes(self, old_content: str, new_content: str) -> ChangeDetection:
        """Detect changes between old and new content"""
        old_hash = hashlib.sha256(old_content.encode()).hexdigest()
        new_hash = hashlib.sha256(new_content.encode()).hexdigest()
        
        if old_hash == new_hash:
            return None
            
        # Simple change detection - in production, you'd use more sophisticated methods
        old_sentences = old_content.split('.')
        new_sentences = new_content.split('.')
        
        # Find new sentences
        new_sentences_only = [s for s in new_sentences if s.strip() not in [os.strip() for os in old_sentences]]
        
        # Determine change type
        change_type = "policy_update"
        if len(new_sentences_only) > 3:
            change_type = "new_requirement"
        elif any(keyword in new_content.lower() for keyword in ["clarify", "clarification", "note"]):
            change_type = "clarification"
        
        # Calculate confidence
        confidence = min(len(new_sentences_only) / 10, 1.0)
        
        return ChangeDetection(
            old_content_hash=old_hash,
            new_content_hash=new_hash,
            change_type=change_type,
            confidence=confidence,
            key_changes=new_sentences_only[:5]  # Top 5 changes
        )

    def process_location_trigger(self, location_data: Dict[str, Any]) -> List[Alert]:
        """Process location trigger and return relevant alerts"""
        country_code = location_data.get("country_code", "")
        
        # In a real implementation, you'd query your database for alerts
        # For now, return a sample alert
        return [Alert(
            id="location_trigger_alert",
            country_code=country_code,
            title=f"Welcome to {country_code}",
            description="You have entered a new country. Check for any travel advisories.",
            risk_level="low",
            categories=["information"],
            source_url="",
            created_at=datetime.now().isoformat() + "Z",
            expires_at=(datetime.now() + timedelta(hours=24)).isoformat() + "Z",
            confidence_score=0.8
        )]

# Example usage functions
def process_example_scraped_content():
    """Example of processing scraped content"""
    processor = TravelContentProcessor()
    
    # Example scraped content
    scraped_data = {
        "source_id": "us_state_dept",
        "country_code": "TH",
        "url": "https://travel.state.gov/thailand",
        "content": """
        <h1>Thailand Travel Advisory</h1>
        <p>Effective immediately, all travelers to Thailand must obtain a tourist visa for stays over 30 days. 
        This is a critical requirement that cannot be waived. Travelers without proper documentation will be denied entry.</p>
        <p>Additionally, proof of vaccination against COVID-19 is required for all international arrivals.</p>
        """,
        "content_hash": "sha256_hash_example",
        "scraped_at": "2025-01-20T10:30:00Z",
        "content_type": "travel_advisory"
    }
    
    alerts = processor.process_scraped_content(scraped_data)
    
    print("Generated Alerts:")
    for alert in alerts:
        print(f"- {alert.title} (Risk: {alert.risk_level}, Categories: {alert.categories})")
    
    return alerts

def process_example_location_trigger():
    """Example of processing location trigger"""
    processor = TravelContentProcessor()
    
    location_data = {
        "user_id": "user123",
        "country_code": "TH",
        "lat": 13.7563,
        "lng": 100.5018,
        "entry_detected_at": "2025-01-20T10:30:00Z"
    }
    
    alerts = processor.process_location_trigger(location_data)
    
    print("Location Trigger Alerts:")
    for alert in alerts:
        print(f"- {alert.title}")
    
    return alerts

if __name__ == "__main__":
    # Run examples
    print("Processing scraped content...")
    process_example_scraped_content()
    
    print("\nProcessing location trigger...")
    process_example_location_trigger()
