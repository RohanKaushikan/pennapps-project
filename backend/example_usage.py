#!/usr/bin/env python3
"""
Example usage of spaCy with the JSON formats for travel content processing
"""

import json
from datetime import datetime
from spacy_processor import TravelContentProcessor

def example_scraped_content_processing():
    """Example: Process scraped content using spaCy"""
    print("=== Processing Scraped Content ===")
    
    # Example scraped content in your JSON format
    scraped_content = {
        "source_id": "us_state_dept",
        "country_code": "TH", 
        "url": "https://travel.state.gov/thailand",
        "content": """
        <h1>Thailand Travel Advisory Update</h1>
        <p>Effective January 15, 2025, all travelers to Thailand must obtain a tourist visa for stays over 30 days. 
        This is a critical requirement that cannot be waived. Travelers without proper documentation will be denied entry at the border.</p>
        
        <p>Additionally, proof of vaccination against COVID-19 is required for all international arrivals. 
        The vaccination certificate must be in English or Thai and issued by an approved health authority.</p>
        
        <p>Please note that the processing time for visa applications has been extended to 10-15 business days due to increased demand.</p>
        
        <p>For emergency situations, travelers can contact the nearest Thai embassy or consulate.</p>
        """,
        "content_hash": "sha256_abc123def456",
        "scraped_at": "2025-01-20T10:30:00Z",
        "content_type": "travel_advisory"
    }
    
    # Initialize processor
    processor = TravelContentProcessor()
    
    # Process the content
    alerts = processor.process_scraped_content(scraped_content)
    
    print(f"Generated {len(alerts)} alerts:")
    for i, alert in enumerate(alerts, 1):
        print(f"\nAlert {i}:")
        print(f"  Title: {alert.title}")
        print(f"  Risk Level: {alert.risk_level}")
        print(f"  Categories: {', '.join(alert.categories)}")
        print(f"  Confidence: {alert.confidence_score:.2f}")
        print(f"  Description: {alert.description}")
    
    return alerts

def example_alert_format():
    """Example: Generate alerts in your JSON format"""
    print("\n=== Alert Format Example ===")
    
    # Example alert in your JSON format
    alert_example = {
        "id": "uuid_12345",
        "country_code": "TH",
        "title": "New visa requirement",
        "description": "Tourist visa now required for stays over 30 days",
        "risk_level": "high",
        "categories": ["visa", "entry_requirements"],
        "source_url": "https://thailand.embassy.gov/visa-update",
        "created_at": "2025-01-20T10:30:00Z",
        "expires_at": "2025-04-20T10:30:00Z",
        "confidence_score": 0.95
    }
    
    print("Example Alert JSON:")
    print(json.dumps(alert_example, indent=2))
    
    return alert_example

def example_location_trigger():
    """Example: Process location trigger"""
    print("\n=== Location Trigger Processing ===")
    
    # Example location trigger in your JSON format
    location_trigger = {
        "user_id": "user_12345",
        "country_code": "TH", 
        "lat": 13.7563,
        "lng": 100.5018,
        "entry_detected_at": "2025-01-20T10:30:00Z"
    }
    
    processor = TravelContentProcessor()
    alerts = processor.process_location_trigger(location_trigger)
    
    print(f"Location trigger generated {len(alerts)} alerts:")
    for alert in alerts:
        print(f"  - {alert.title} (Risk: {alert.risk_level})")
    
    return alerts

def example_change_detection():
    """Example: Detect changes between content versions"""
    print("\n=== Change Detection Example ===")
    
    # Old content
    old_content = """
    Thailand travel requirements: Tourist visa required for stays over 60 days.
    COVID-19 vaccination recommended but not mandatory.
    Processing time: 5-7 business days.
    """
    
    # New content (with changes)
    new_content = """
    Thailand travel requirements: Tourist visa required for stays over 30 days.
    COVID-19 vaccination is now mandatory for all arrivals.
    Processing time: 10-15 business days due to increased demand.
    Emergency contact: +66-2-123-4567
    """
    
    processor = TravelContentProcessor()
    changes = processor.detect_changes(old_content, new_content)
    
    if changes:
        print("Changes detected:")
        print(f"  Change Type: {changes.change_type}")
        print(f"  Confidence: {changes.confidence:.2f}")
        print(f"  Key Changes: {changes.key_changes}")
    else:
        print("No changes detected")
    
    return changes

def example_api_usage():
    """Example: How to use the API endpoints"""
    print("\n=== API Usage Examples ===")
    
    print("1. Process scraped content:")
    print("POST /api/process-content")
    print("Body: {scraped_content_json}")
    
    print("\n2. Process location trigger:")
    print("POST /api/process-location")
    print("Body: {location_trigger_json}")
    
    print("\n3. Detect changes:")
    print("POST /api/detect-changes")
    print("Body: {\"old_content\": \"...\", \"new_content\": \"...\"}")
    
    print("\n4. Run example processing:")
    print("GET /api/example-processing")

def main():
    """Run all examples"""
    print("🚀 spaCy Travel Content Processing Examples")
    print("=" * 50)
    
    try:
        # Run examples
        example_scraped_content_processing()
        example_alert_format()
        example_location_trigger()
        example_change_detection()
        example_api_usage()
        
        print("\n✅ All examples completed successfully!")
        print("\nTo use in your application:")
        print("1. Install spaCy model: python setup_spacy.py")
        print("2. Start the backend: python main.py")
        print("3. Use the API endpoints for processing")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        print("Make sure spaCy is installed: python -m spacy download en_core_web_sm")

if __name__ == "__main__":
    main()
