"""
Test script to verify page access API is working correctly
"""
import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"
TEST_EMPLOYEE_CODE = "10001"  # Change this to a valid employee code

print("=" * 80)
print("Testing Page Access API")
print("=" * 80)

# Test 1: Login
print("\n1. Testing login...")
try:
    response = requests.post(
        f"{BASE_URL}/api/login",
        json={"employeeCode": TEST_EMPLOYEE_CODE}
    )
    
    if response.status_code == 200:
        print(f"  ✅ Login successful")
        data = response.json()
        employee = data.get("employee", {})
        print(f"     Employee: {employee.get('employee_id')}")
        print(f"     Role: {employee.get('role')}")
        print(f"     Region: {employee.get('region')}")
        
        # Get cookies for subsequent requests
        cookies = response.cookies
    else:
        print(f"  ❌ Login failed: {response.status_code}")
        print(f"     {response.text}")
        exit(1)
except Exception as e:
    print(f"  ❌ Error: {e}")
    exit(1)

# Test 2: Check page access for different pages
pages_to_test = [
    "create_quote",
    "project_price",
    "special_price_approval",
    "update_price"
]

print("\n2. Testing page access...")
for page_id in pages_to_test:
    try:
        response = requests.get(
            f"{BASE_URL}/api/config/page-access/check/{page_id}",
            cookies=cookies
        )
        
        if response.status_code == 200:
            data = response.json()
            has_access = data.get("has_access")
            user_role = data.get("user_role")
            
            status = "✅ ALLOWED" if has_access else "❌ DENIED"
            print(f"  {status} - {page_id} (role: {user_role})")
        else:
            print(f"  ❌ Error checking {page_id}: {response.status_code}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

# Test 3: Get user accessible pages
print("\n3. Getting all accessible pages...")
try:
    response = requests.get(
        f"{BASE_URL}/api/config/page-access/user-pages",
        cookies=cookies
    )
    
    if response.status_code == 200:
        data = response.json()
        accessible_pages = data.get("accessible_pages", [])
        user_role = data.get("user_role")
        
        print(f"  ✅ User role: {user_role}")
        print(f"  ✅ Accessible pages ({len(accessible_pages)}):")
        for page in accessible_pages:
            print(f"     - {page}")
    else:
        print(f"  ❌ Error: {response.status_code}")
except Exception as e:
    print(f"  ❌ Error: {e}")

print("\n" + "=" * 80)
print("Test completed!")
print("=" * 80)
