#!/usr/bin/env python3
"""
Quick test to verify that search filters are now working correctly
"""
import requests
import json
from datetime import datetime

# API Configuration
BASE_URL = "http://localhost:8001/api/v1"

def test_search_with_filters():
    """Test search with subject and year filters"""
    print("🧪 TESTING PYQ SEARCH WITH FILTERS")
    print("=" * 50)
    
    # Test data
    test_cases = [
        {
            "name": "Search with Subject Filter Only",
            "query": "women issue",
            "subject": "General Studies Paper 1",
            "year": None
        },
        {
            "name": "Search with Year Filter Only", 
            "query": "women issue",
            "subject": None,
            "year": 2020
        },
        {
            "name": "Search with Both Filters",
            "query": "women issue", 
            "subject": "General Studies Paper 1",
            "year": 2020
        },
        {
            "name": "Search without Filters (baseline)",
            "query": "women issue",
            "subject": None,
            "year": None
        }
    ]
    
    # You'll need to replace this with a valid token
    headers = {
        "Content-Type": "application/json",
        # "Authorization": "Bearer YOUR_TOKEN_HERE"
    }
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print("-" * 40)
        
        # Prepare request payload
        payload = {
            "query": test_case["query"],
            "limit": 5,
            "page": 1
        }
        
        if test_case["subject"]:
            payload["subject"] = test_case["subject"]
        if test_case["year"]:
            payload["year"] = test_case["year"]
        
        print(f"📤 Request: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/pyqs/search",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                results = response.json()
                print(f"✅ Success: Found {len(results)} results")
                
                # Show first result details
                if results:
                    first = results[0]
                    print(f"   📋 First result:")
                    print(f"   - Subject: {first.get('subject', 'N/A')}")
                    print(f"   - Year: {first.get('year', 'N/A')}")
                    print(f"   - Score: {first.get('similarity_score', 0):.3f}")
                    print(f"   - Question: {first.get('question', '')[:80]}...")
                else:
                    print("   ⚠️ No results found")
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    print(f"🕒 Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    test_search_with_filters()
    print(f"\n🏁 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
