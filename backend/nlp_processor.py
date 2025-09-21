import re
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import sqlite3
from collections import Counter

@dataclass
class AlertIntelligence:
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

class NLPProcessor:
    def __init__(self):
        self.requirement_keywords = {
            'visa': ['visa', 'visa application', 'visa requirement', 'visa validity', 'entry visa'],
            'health': ['vaccination', 'health certificate', 'medical clearance', 'covid test', 'pcr test', 'health screening'],
            'customs': ['customs declaration', 'duty', 'customs form', 'import', 'export', 'prohibited items'],
            'entry': ['entry permit', 'entry requirement', 'border control', 'immigration', 'arrival'],
            'documentation': ['passport', 'id card', 'travel document', 'proof of', 'certificate', 'permit']
        }

        self.legal_language = {
            'mandatory': ['mandatory', 'required', 'must', 'shall', 'compulsory', 'obligatory'],
            'advisory': ['recommended', 'advised', 'suggested', 'should', 'encouraged', 'optional']
        }

        self.time_indicators = {
            'immediate': ['immediately', 'urgent', 'asap', 'right away', 'without delay'],
            'before_travel': ['before travel', 'prior to departure', 'before entry', 'in advance'],
            'upon_arrival': ['upon arrival', 'at the border', 'at entry point', 'on arrival'],
            'within_days': ['within \\d+ days?', 'within \\d+ weeks?', 'by [A-Za-z]+ \\d+']
        }

        self.penalty_keywords = [
            'fine', 'penalty', 'deportation', 'denial of entry', 'banned', 'refused entry',
            'prosecution', 'imprisonment', 'detention', 'confiscation', 'seized'
        ]

        self.document_keywords = [
            'passport', 'visa', 'permit', 'certificate', 'license', 'card', 'form',
            'declaration', 'proof', 'document', 'authorization', 'clearance'
        ]

    def extract_requirements_vs_recommendations(self, text: str) -> Tuple[List[str], List[str]]:
        """Extract legal requirements vs recommendations from text"""
        requirements = []
        recommendations = []

        sentences = re.split(r'[.!?]+', text)

        for sentence in sentences:
            sentence = sentence.strip().lower()
            if not sentence:
                continue

            # Check for mandatory language
            has_mandatory = any(keyword in sentence for keyword in self.legal_language['mandatory'])
            has_advisory = any(keyword in sentence for keyword in self.legal_language['advisory'])

            if has_mandatory and not has_advisory:
                requirements.append(sentence.capitalize())
            elif has_advisory and not has_mandatory:
                recommendations.append(sentence.capitalize())
            elif has_mandatory:  # If both, prioritize mandatory
                requirements.append(sentence.capitalize())

        return requirements, recommendations

    def extract_dates_and_deadlines(self, text: str) -> Tuple[List[str], List[str]]:
        """Extract effective dates and deadlines"""
        effective_dates = []
        deadlines = []

        # Date patterns
        date_patterns = [
            r'\b(?:from|effective|starting)\s+([A-Za-z]+ \d{1,2},? \d{4})\b',
            r'\b(?:from|effective|starting)\s+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\b',
            r'\b(?:as of|beginning)\s+([A-Za-z]+ \d{1,2},? \d{4})\b'
        ]

        deadline_patterns = [
            r'\b(?:by|before|until|deadline)\s+([A-Za-z]+ \d{1,2},? \d{4})\b',
            r'\b(?:by|before|until|deadline)\s+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\b',
            r'\bwithin (\d+ days?)\b',
            r'\bwithin (\d+ weeks?)\b'
        ]

        for pattern in date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            effective_dates.extend([match.group(1) for match in matches])

        for pattern in deadline_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            deadlines.extend([match.group(1) for match in matches])

        return effective_dates, deadlines

    def extract_penalties(self, text: str) -> List[str]:
        """Extract penalty and consequence information"""
        penalties = []
        sentences = re.split(r'[.!?]+', text)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Check if sentence contains penalty keywords
            if any(keyword in sentence.lower() for keyword in self.penalty_keywords):
                penalties.append(sentence)

        return penalties

    def extract_document_requirements(self, text: str) -> List[str]:
        """Extract document requirements"""
        documents = []

        # Look for document-related sentences
        sentences = re.split(r'[.!?]+', text)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Check if sentence mentions documents and requirements
            has_document = any(keyword in sentence.lower() for keyword in self.document_keywords)
            has_requirement = any(keyword in sentence.lower() for keyword in self.legal_language['mandatory'])

            if has_document and (has_requirement or 'need' in sentence.lower() or 'provide' in sentence.lower()):
                documents.append(sentence)

        return documents

    def determine_compliance_urgency(self, text: str, deadlines: List[str]) -> str:
        """Determine urgency level for compliance"""
        text_lower = text.lower()

        # Check for immediate urgency indicators
        if any(indicator in text_lower for indicator in self.time_indicators['immediate']):
            return 'immediate'

        # Check for deadline-based urgency
        if deadlines:
            for deadline in deadlines:
                if 'days' in deadline.lower():
                    # Extract number of days
                    days_match = re.search(r'(\d+)', deadline)
                    if days_match:
                        days = int(days_match.group(1))
                        if days <= 7:
                            return 'immediate'
                        elif days <= 30:
                            return 'upcoming'

        # Check for before travel indicators
        if any(indicator in text_lower for indicator in self.time_indicators['before_travel']):
            return 'upcoming'

        # Check for upon arrival indicators
        if any(indicator in text_lower for indicator in self.time_indicators['upon_arrival']):
            return 'immediate'

        return 'future'

    def extract_keywords(self, text: str) -> Dict[str, List[str]]:
        """Extract and categorize keywords"""
        text_lower = text.lower()

        requirement_found = {}
        legal_found = []
        time_found = []

        # Extract requirement type keywords
        for category, keywords in self.requirement_keywords.items():
            found = [kw for kw in keywords if kw in text_lower]
            if found:
                requirement_found[category] = found

        # Extract legal language keywords
        for category, keywords in self.legal_language.items():
            found = [kw for kw in keywords if kw in text_lower]
            legal_found.extend(found)

        # Extract time indicator keywords
        for category, keywords in self.time_indicators.items():
            for keyword in keywords:
                if re.search(keyword, text_lower):
                    time_found.append(keyword if '\\' not in keyword else category)

        return {
            'requirement_types': list(requirement_found.keys()),
            'legal_language': legal_found,
            'time_indicators': time_found
        }

    def classify_legal_obligation(self, requirements: List[str], recommendations: List[str]) -> str:
        """Classify as legal obligation vs advisory"""
        if len(requirements) > len(recommendations):
            return 'legal_obligation'
        elif len(recommendations) > len(requirements):
            return 'advisory'
        else:
            return 'mixed'

    def classify_risk_level(self, penalties: List[str], urgency: str, spike_factor: float = 1.0) -> str:
        """Classify risk level based on content and context"""
        penalty_score = len(penalties)
        urgency_score = {'immediate': 3, 'upcoming': 2, 'future': 1}.get(urgency, 1)
        spike_score = min(int(spike_factor), 3)  # Cap at 3

        total_score = penalty_score + urgency_score + spike_score

        if total_score >= 6:
            return 'critical'
        elif total_score >= 3:
            return 'important'
        else:
            return 'informational'

    def classify_traveler_impact(self, keywords: Dict[str, List[str]]) -> str:
        """Classify impact on different types of travelers"""
        requirement_types = keywords.get('requirement_types', [])

        # Specific visa types mentioned
        if 'visa' in requirement_types:
            return 'specific_visa_types'

        # Business/work related
        if any(term in ' '.join(keywords.get('legal_language', [])) for term in ['business', 'work', 'employment']):
            return 'specific_purposes'

        # General requirements
        if 'entry' in requirement_types or 'documentation' in requirement_types:
            return 'all_travelers'

        return 'all_travelers'

    def process_alert_content(self, alert_id: str, content: str, spike_factor: float = 1.0) -> AlertIntelligence:
        """Process alert content and extract intelligence"""

        # Extract main components
        requirements, recommendations = self.extract_requirements_vs_recommendations(content)
        effective_dates, deadlines = self.extract_dates_and_deadlines(content)
        penalties = self.extract_penalties(content)
        documents = self.extract_document_requirements(content)
        urgency = self.determine_compliance_urgency(content, deadlines)
        keywords = self.extract_keywords(content)

        # Perform classifications
        legal_classification = self.classify_legal_obligation(requirements, recommendations)
        risk_level = self.classify_risk_level(penalties, urgency, spike_factor)
        traveler_impact = self.classify_traveler_impact(keywords)

        return AlertIntelligence(
            alert_id=alert_id,
            legal_requirements=requirements,
            recommendations=recommendations,
            effective_dates=effective_dates,
            deadlines=deadlines,
            penalties=penalties,
            document_requirements=documents,
            compliance_urgency=urgency,
            requirement_keywords=keywords.get('requirement_types', []),
            legal_language_keywords=keywords.get('legal_language', []),
            time_indicators=keywords.get('time_indicators', []),
            legal_classification=legal_classification,
            risk_level=risk_level,
            traveler_impact=traveler_impact,
            created_at=datetime.now().isoformat()
        )