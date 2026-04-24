#!/usr/bin/env python3
"""
Debug file path issues
"""

import os
import json

def debug_file_paths():
    """Debug where files are being read/written"""
    
    print("🔍 File Path Debug")
    print("=" * 50)
    
    # Current working directory
    cwd = os.getcwd()
    print(f"📂 Current working directory: {cwd}")
    
    # This file location
    this_file = __file__
    this_dir = os.path.dirname(__file__)
    print(f"📂 This file: {this_file}")
    print(f"📂 This directory: {this_dir}")
    
    # Simulate backend path calculation
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    employees_file = os.path.join(backend_dir, "employees.json")
    print(f"📂 Backend directory: {backend_dir}")
    print(f"📂 Employees file path: {employees_file}")
    print(f"📂 Absolute employees path: {os.path.abspath(employees_file)}")
    
    # Check if files exist
    possible_paths = [
        "employees.json",
        "backend/employees.json", 
        employees_file,
        os.path.join(cwd, "employees.json"),
        os.path.join(cwd, "backend", "employees.json")
    ]
    
    print(f"\n📋 Checking possible file locations:")
    for path in possible_paths:
        exists = os.path.exists(path)
        abs_path = os.path.abspath(path)
        print(f"   {'✅' if exists else '❌'} {path}")
        print(f"      → {abs_path}")
        
        if exists:
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                count = len(data.get('employees', []))
                print(f"      → Contains {count} employees")
            except Exception as e:
                print(f"      → Error reading: {e}")
    
    # Test write to different locations
    print(f"\n🧪 Testing write permissions:")
    test_data = {"test": "data"}
    
    for path in possible_paths:
        if path.endswith('employees.json'):
            test_path = path.replace('employees.json', 'test_write.json')
            try:
                with open(test_path, 'w') as f:
                    json.dump(test_data, f)
                print(f"   ✅ Can write to: {os.path.dirname(test_path) or '.'}")
                os.remove(test_path)  # Clean up
            except Exception as e:
                print(f"   ❌ Cannot write to: {os.path.dirname(test_path) or '.'} - {e}")

if __name__ == "__main__":
    debug_file_paths()