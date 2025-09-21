import re
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import sqlite3
from collections import Counter

@dataclass
class LegalRequirement:
    requirement_text: str
    requirement_type: str  # mandatory, recommended, prohibited
    penalty_severity: str  # none, minor, major, critical
    compliance_deadline: Optional[str]
    legal_authority: Optional[str]
    enforcement_likelihood: str  # low, medium, high
    fine_amount: Optional[str]
    document_validity_period: Optional[str]
    entry_exit_specific: str  # entry, exit, both, neither

@dataclass
class AlertLegalAnalysis:
    alert_id: str
    requirements: List[LegalRequirement]
    overall_severity: str
    critical_deadlines: List[str]
    mandatory_documents: List[str]
    penalty_summary: str
    created_at: str

class LegalTextAnalyzer:
    def __init__(self):
        # Legal language patterns for requirement classification
        self.mandatory_patterns = [
            r'\b(?:must|shall|required|mandatory|compulsory|obligatory)\b',
            r'\b(?:is required|are required|will be required)\b',
            r'\b(?:failure to .* will result)\b',
            r'\b(?:violation .* will result)\b'
        ]

        self.recommended_patterns = [
            r'\b(?:should|recommended|advised|suggested|encouraged)\b',
            r'\b(?:it is recommended|it is advised|it is suggested)\b',
            r'\b(?:travelers are advised|visitors are encouraged)\b'
        ]

        self.prohibited_patterns = [
            r'\b(?:prohibited|forbidden|illegal|banned|not allowed)\b',
            r'\b(?:shall not|must not|cannot|may not)\b',
            r'\b(?:is not permitted|are not permitted)\b',
            r'\b(?:strictly forbidden|strictly prohibited)\b'
        ]

        # Penalty severity patterns
        self.penalty_patterns = {
            'critical': [
                r'\b(?:deportation|imprisonment|detention|arrest|prosecution)\b',
                r'\b(?:permanent ban|lifetime ban|criminal charges)\b',
                r'\b(?:confiscation|seizure|forfeiture)\b'
            ],
            'major': [
                r'\b(?:fine|penalty|refused entry|denied entry)\b',
                r'\b(?:temporary ban|suspension|revocation)\b',
                r'\$\d+(?:,\d{3})*(?:\.\d{2})?',  # Dollar amounts
                r'€\d+(?:,\d{3})*(?:\.\d{2})?',   # Euro amounts
                r'£\d+(?:,\d{3})*(?:\.\d{2})?'    # Pound amounts
            ],
            'minor': [
                r'\b(?:warning|caution|administrative fee)\b',
                r'\b(?:delay|processing delay|additional screening)\b'
            ]
        }

        # Deadline and validity patterns
        self.deadline_patterns = [
            r'\b(?:by|before|until|deadline|expires?|valid until)\s+([A-Za-z]+ \d{1,2},? \d{4})\b',
            r'\b(?:within|in)\s+(\d+)\s+(days?|weeks?|months?|years?)\b',
            r'\b(?:at least|minimum)\s+(\d+)\s+(days?|weeks?|months?)\s+(?:before|prior to)\b',
            r'\b(?:valid for)\s+(\d+)\s+(days?|weeks?|months?|years?)\b'
        ]

        # Legal authority patterns
        self.authority_patterns = [
            r'\b(?:ministry of|department of|immigration|customs|border control)\b[^.]*',
            r'\b(?:embassy|consulate|visa office)\b[^.]*',
            r'\b(?:according to|as per|under)\s+([^.]*(?:law|act|regulation|directive))\b'
        ]

        # Entry/Exit specific patterns
        self.entry_patterns = [
            r'\b(?:upon arrival|at entry|entry point|border crossing|immigration checkpoint)\b',
            r'\b(?:before travel|prior to departure|pre-arrival)\b',
            r'\b(?:visa on arrival|entry visa|arrival requirements)\b'
        ]

        self.exit_patterns = [
            r'\b(?:upon departure|at exit|exit requirements|departure tax)\b',
            r'\b(?:before leaving|prior to exit)\b'
        ]

        # Document validity patterns
        self.validity_patterns = [
            r'\b(?:passport|visa|permit|certificate|license)\s+(?:must be )?valid for\s+(?:at least\s+)?(\d+)\s+(months?|years?)\b',
            r'\b(?:minimum validity|remaining validity)\s+(?:of\s+)?(\d+)\s+(months?|years?)\b'
        ]

    def extract_fine_amounts(self, text: str) -> List[str]:
        """Extract monetary fine amounts from text"""
        fine_patterns = [
            r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'€(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'£(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'\b(\d+(?:,\d{3})*)\s+(?:dollars?|euros?|pounds?)\b'
        ]

        fines = []
        for pattern in fine_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            fines.extend([match.group(0) for match in matches])

        return fines

    def classify_requirement_type(self, text: str) -> str:
        """Classify requirement as mandatory, recommended, or prohibited"""
        text_lower = text.lower()

        # Check for prohibited language first
        for pattern in self.prohibited_patterns:
            if re.search(pattern, text_lower):
                return 'prohibited'

        # Check for mandatory language
        mandatory_score = 0
        for pattern in self.mandatory_patterns:
            if re.search(pattern, text_lower):
                mandatory_score += 1

        # Check for recommended language
        recommended_score = 0
        for pattern in self.recommended_patterns:
            if re.search(pattern, text_lower):
                recommended_score += 1

        if mandatory_score > recommended_score:
            return 'mandatory'
        elif recommended_score > 0:
            return 'recommended'
        else:
            return 'mandatory'  # Default to mandatory if unclear

    def analyze_penalty_severity(self, text: str) -> Tuple[str, List[str]]:
        """Analyze penalty severity and extract fine amounts"""
        text_lower = text.lower()
        fine_amounts = self.extract_fine_amounts(text)

        # Check for critical penalties
        for pattern in self.penalty_patterns['critical']:
            if re.search(pattern, text_lower):
                return 'critical', fine_amounts

        # Check for major penalties
        for pattern in self.penalty_patterns['major']:
            if re.search(pattern, text_lower):
                return 'major', fine_amounts

        # Check for minor penalties
        for pattern in self.penalty_patterns['minor']:
            if re.search(pattern, text_lower):
                return 'minor', fine_amounts

        return 'none', fine_amounts

    def extract_compliance_deadlines(self, text: str) -> List[str]:
        """Extract compliance deadlines from text"""
        deadlines = []

        for pattern in self.deadline_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if match.groups():
                    deadlines.append(match.group(0))

        return deadlines

    def extract_legal_authority(self, text: str) -> Optional[str]:
        """Extract legal authority or source"""
        for pattern in self.authority_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        return None

    def determine_enforcement_likelihood(self, requirement_type: str, penalty_severity: str,
                                       fine_amounts: List[str]) -> str:
        """Determine likelihood of enforcement based on requirement characteristics"""
        if requirement_type == 'prohibited' and penalty_severity == 'critical':
            return 'high'
        elif requirement_type == 'mandatory' and penalty_severity in ['major', 'critical']:
            return 'high'
        elif requirement_type == 'mandatory' and fine_amounts:
            return 'medium'
        elif requirement_type == 'mandatory':
            return 'medium'
        elif requirement_type == 'recommended':
            return 'low'
        else:
            return 'low'

    def extract_document_validity(self, text: str) -> Optional[str]:
        """Extract document validity requirements"""
        for pattern in self.validity_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None

    def classify_entry_exit_specific(self, text: str) -> str:
        """Classify if requirement is entry, exit, or both specific"""
        text_lower = text.lower()

        has_entry = any(re.search(pattern, text_lower) for pattern in self.entry_patterns)
        has_exit = any(re.search(pattern, text_lower) for pattern in self.exit_patterns)

        if has_entry and has_exit:
            return 'both'
        elif has_entry:
            return 'entry'
        elif has_exit:
            return 'exit'
        else:
            return 'neither'

    def process_legal_requirement(self, requirement_text: str) -> LegalRequirement:
        """Process a single legal requirement and extract all relevant information"""

        # Classify requirement type
        requirement_type = self.classify_requirement_type(requirement_text)

        # Analyze penalty severity
        penalty_severity, fine_amounts = self.analyze_penalty_severity(requirement_text)

        # Extract compliance deadlines
        deadlines = self.extract_compliance_deadlines(requirement_text)
        compliance_deadline = deadlines[0] if deadlines else None

        # Extract legal authority
        legal_authority = self.extract_legal_authority(requirement_text)

        # Determine enforcement likelihood
        enforcement_likelihood = self.determine_enforcement_likelihood(
            requirement_type, penalty_severity, fine_amounts
        )

        # Extract document validity
        document_validity = self.extract_document_validity(requirement_text)

        # Classify entry/exit specific
        entry_exit_specific = self.classify_entry_exit_specific(requirement_text)

        # Extract fine amount
        fine_amount = fine_amounts[0] if fine_amounts else None

        return LegalRequirement(
            requirement_text=requirement_text,
            requirement_type=requirement_type,
            penalty_severity=penalty_severity,
            compliance_deadline=compliance_deadline,
            legal_authority=legal_authority,
            enforcement_likelihood=enforcement_likelihood,
            fine_amount=fine_amount,
            document_validity_period=document_validity,
            entry_exit_specific=entry_exit_specific
        )

    def analyze_alert_content(self, alert_id: str, content: str) -> AlertLegalAnalysis:
        """Analyze entire alert content for legal requirements"""

        # Split content into sentences for individual analysis
        sentences = re.split(r'[.!?]+', content)
        requirements = []

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 20:  # Skip very short sentences
                continue

            # Process each sentence as a potential legal requirement
            requirement = self.process_legal_requirement(sentence)
            requirements.append(requirement)

        # Analyze overall characteristics
        critical_deadlines = [req.compliance_deadline for req in requirements
                            if req.compliance_deadline and req.penalty_severity in ['major', 'critical']]

        mandatory_documents = [req.requirement_text for req in requirements
                             if req.requirement_type == 'mandatory' and
                             any(doc in req.requirement_text.lower() for doc in
                                 ['passport', 'visa', 'permit', 'certificate', 'license'])]

        # Determine overall severity
        severity_scores = {'critical': 4, 'major': 3, 'minor': 2, 'none': 1}
        max_severity = max([severity_scores[req.penalty_severity] for req in requirements], default=1)
        overall_severity = [k for k, v in severity_scores.items() if v == max_severity][0]

        # Create penalty summary
        penalties = [req for req in requirements if req.penalty_severity != 'none']
        if penalties:
            penalty_summary = f"{len(penalties)} penalties identified: {', '.join(set([p.penalty_severity for p in penalties]))}"
        else:
            penalty_summary = "No specific penalties identified"

        return AlertLegalAnalysis(
            alert_id=alert_id,
            requirements=requirements,
            overall_severity=overall_severity,
            critical_deadlines=critical_deadlines,
            mandatory_documents=mandatory_documents,
            penalty_summary=penalty_summary,
            created_at=datetime.now().isoformat()
        )