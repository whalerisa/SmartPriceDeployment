#!/usr/bin/env python3
"""
Test the fixed file path logic
"""

import os
import json

def test_fixed_path_logic():
    """Test the fixed path logic"""
    
    print("🧪 Testing Fixed Path Logic")
    print("=" * 50)
    
    # Simulate the fixed logic
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    employees_file = os.path.join(backend_dir, "employees.json")
    
    print(f"📂 Backend dir: {backend_dir}")
    print(f"📂 First try: {employees_file}")
    print(f"📂 Exists: {os.path.exists(employees_file)}")
    
    # If file doesn't exist in backend dir, it might be running from root
    if not os.path.exists(employees_file):
        # Try relative path from current working directory
        employees_file = os.path.join("backend", "employees.json")
        print(f"📂 Second try: {employees_file}")
        print(f"📂 Exists: {os.path.exists(employees_file)}")
    
    print(f"📂 Final path: {employees_file}")
    print(f"📂 Absolute path: {os.path.abspath(employees_file)}")
    
    if os.path.exists(employees_file):
        try:
            with open(employees_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            count = len(data.get('employees', []))
            print(f"✅ Successfully loaded {count} employees")
            
            # Find BE region RM
            be_rm = next(
                (emp for emp in data.get("employees", []) 
                 if emp.get("region") == "BE" and emp.get("role") == "RM"),
                None
            )
            
            if be_rm:
                print(f"📋 Current BE RM: {be_rm.get('employee_id')}")
            else:
                print("❌ No RM found for BE region")
                
            return True
            
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            return False
    else:
        print("❌ File not found!")
        return False

if __name__ == "__main__":
    success = test_fixed_path_logic()
    print(f"\n🎯 Result: {'SUCCESS' if success else 'FAILED'}")