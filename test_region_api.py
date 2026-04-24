#!/usr/bin/env python3
"""
Test script for Region Manager API
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"  # Adjust if needed
ADMIN_TOKEN = "your-admin-token"  # You'll need to get this from browser

def test_get_regions():
    """Test GET /api/config/regions"""
    print("🔍 Testing GET /api/config/regions...")
    
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    response = requests.get(f"{BASE_URL}/api/config/regions", headers=headers)
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("✅ Success!")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"❌ Error: {response.text}")

def test_update_region(region_code, new_rm_id):
    """Test PUT /api/config/regions/{region_code}"""
    print(f"🔄 Testing PUT /api/config/regions/{region_code}...")
    
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    data = {"rm_employee_id": new_rm_id}
    
    response = requests.put(
        f"{BASE_URL}/api/config/regions/{region_code}", 
        headers=headers,
        json=data
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print("✅ Success!")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"❌ Error: {response.text}")

if __name__ == "__main__":
    print("🧪 Region Manager API Test")
    print("=" * 50)
    
    # Test 1: Get regions
    test_get_regions()
    
    print("\n" + "=" * 50)
    
    # Test 2: Update region (example)
    # test_update_region("N", "20037")
    
    print("\n💡 To test update:")
    print("1. Get admin token from browser (F12 > Application > Cookies > auth_token)")
    print("2. Update ADMIN_TOKEN variable above")
    print("3. Uncomment test_update_region line")
    print("4. Run: python test_region_api.py")