#!/usr/bin/env python3
"""
Test AI Summary API to ensure it's working correctly.
"""

import asyncio
import sys
import os
import json

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from fastapi.testclient import TestClient
from main import app

def test_ai_summary():
    """Test the AI summary endpoint."""
    
    client = TestClient(app)
    
    print("🧠 Testing AI Summary API")
    print("=" * 40)
    
    # Test data
    test_text = """
    Today we discussed the new project requirements. 
    Arnav will fix the login bug by tomorrow. 
    Kunal needs to deploy the new features to production tonight.
    Sarah will review the pull request when she gets a chance.
    We also need to update the API documentation by Friday.
    The database connection issue is critical and needs immediate attention.
    """
    
    print(f"📝 Input text: {test_text[:100]}...")
    
    try:
        # Make API request
        response = client.post("/api/summarize", json={"text": test_text})
        
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Summary generated successfully!")
            print(f"📋 Summary: {result.get('summary', 'No summary found')}")
        else:
            print(f"❌ API Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    print("\n" + "=" * 40)
    print("🎯 AI Summary Test Complete!")

if __name__ == "__main__":
    test_ai_summary()