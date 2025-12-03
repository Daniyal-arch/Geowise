"""
Debug GEE Initialization
"""
import os
import json

# Check 1: JSON key file
print("=" * 70)
print("CHECK 1: JSON Key File")
print("=" * 70)

key_file = 'gee-service-account-key.json'

if os.path.exists(key_file):
    print(f"✅ File exists: {os.path.abspath(key_file)}")
    
    # Check if valid JSON
    try:
        with open(key_file, 'r') as f:
            key_data = json.load(f)
        print(f"✅ Valid JSON")
        print(f"   Service Account: {key_data.get('client_email', 'N/A')}")
        print(f"   Project ID: {key_data.get('project_id', 'N/A')}")
    except Exception as e:
        print(f"❌ Invalid JSON: {e}")
else:
    print(f"❌ File not found: {os.path.abspath(key_file)}")
    print("\n💡 Try these locations:")
    print(f"   - {os.path.abspath('.')}/gee-service-account-key.json")
    print(f"   - {os.path.abspath('app')}/gee-service-account-key.json")

# Check 2: Service module
print("\n" + "=" * 70)
print("CHECK 2: GEE Service Module")
print("=" * 70)

try:
    from app.services.gee_service import gee_service, initialize_gee_service
    print("✅ gee_service module imported successfully")
    print(f"   Initialized: {gee_service.initialized}")
    
    # Try to initialize
    print("\n⏳ Attempting to initialize GEE...")
    result = initialize_gee_service(
        key_file=key_file,
        project_id='active-apogee-444711-k5'
    )
    
    if result:
        print("✅ GEE initialized successfully!")
    else:
        print("❌ GEE initialization failed!")
        print("   Check the error message above")
    
except ImportError as e:
    print(f"❌ Cannot import gee_service: {e}")
    print("\n💡 Make sure:")
    print("   - app/services/gee_service.py exists")
    print("   - app/services/__init__.py exists")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 70)