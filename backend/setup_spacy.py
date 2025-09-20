#!/usr/bin/env python3
"""
Setup script for spaCy model installation
Run this after installing requirements.txt
"""

import subprocess
import sys
import os

def install_spacy_model():
    """Install the English spaCy model"""
    try:
        print("Installing spaCy English model...")
        subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
        print("✅ spaCy model installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing spaCy model: {e}")
        return False

def test_spacy_installation():
    """Test if spaCy is working correctly"""
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        
        # Test with a simple sentence
        doc = nlp("Thailand requires a visa for stays over 30 days.")
        
        print("✅ spaCy is working correctly!")
        print(f"Test sentence: {doc.text}")
        print(f"Entities found: {[(ent.text, ent.label_) for ent in doc.ents]}")
        return True
    except Exception as e:
        print(f"❌ spaCy test failed: {e}")
        return False

if __name__ == "__main__":
    print("Setting up spaCy for travel content processing...")
    
    # Install the model
    if install_spacy_model():
        # Test the installation
        if test_spacy_installation():
            print("\n🎉 spaCy setup completed successfully!")
            print("You can now use the travel content processing features.")
        else:
            print("\n⚠️ spaCy model installed but not working correctly.")
    else:
        print("\n❌ Failed to install spaCy model.")
        print("Please run: python -m spacy download en_core_web_sm")
