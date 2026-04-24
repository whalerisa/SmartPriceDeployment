"""
Test script to verify JSON files can be loaded correctly
"""
import os
import sys

print("=" * 80)
print("Testing JSON File Loading")
print("=" * 80)

# Print current working directory
print(f"\n📂 Current working directory: {os.getcwd()}")
print(f"📂 Script location: {os.path.abspath(__file__)}")
print(f"📂 Script directory: {os.path.dirname(os.path.abspath(__file__))}")

# Test files to check
test_files = [
    "page_access_config.json",
    "role_approval_scope.json",
    "custom_roles.json",
    "employees.json"
]

print("\n" + "=" * 80)
print("Checking file locations...")
print("=" * 80)

for filename in test_files:
    print(f"\n🔍 Looking for: {filename}")
    
    possible_paths = [
        filename,
        os.path.join("backend", filename),
        os.path.join(os.path.dirname(__file__), filename),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), filename),
        os.path.join(os.getcwd(), filename),
        os.path.join(os.getcwd(), "backend", filename),
    ]
    
    found = False
    for path in possible_paths:
        if os.path.exists(path):
            print(f"  ✅ FOUND: {os.path.abspath(path)}")
            found = True
            
            # Try to load the file
            try:
                import json
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                print(f"     📄 Successfully loaded JSON")
                if isinstance(data, dict):
                    print(f"     📊 Keys: {list(data.keys())[:5]}")
                elif isinstance(data, list):
                    print(f"     📊 Items: {len(data)}")
            except Exception as e:
                print(f"     ❌ Error loading: {e}")
            break
    
    if not found:
        print(f"  ❌ NOT FOUND in any of these locations:")
        for path in possible_paths:
            print(f"     - {os.path.abspath(path)}")

print("\n" + "=" * 80)
print("Testing config_cache module...")
print("=" * 80)

try:
    # Add backend to path if needed
    backend_path = os.path.join(os.getcwd(), "backend")
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    
    from config_cache import get_page_access_config, get_role_approval_scope
    
    print("\n🔧 Testing get_page_access_config()...")
    page_config = get_page_access_config()
    print(f"  ✅ Loaded page access config with {len(page_config)} pages")
    for page_id, config in page_config.items():
        print(f"     - {page_id}: {config.get('page_label')} (roles: {len(config.get('allowed_roles', []))})")
    
    print("\n🔧 Testing get_role_approval_scope()...")
    role_scope = get_role_approval_scope()
    print(f"  ✅ Loaded role approval scope with {len(role_scope)} roles")
    for role, scope in role_scope.items():
        print(f"     - {role}: {scope}")
    
except Exception as e:
    print(f"  ❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("Test completed!")
print("=" * 80)
