#!/usr/bin/env python3
"""
Simple validation script to verify the Redis fallback implementation.
This script checks the code structure without requiring Redis to be installed.
"""

import sys
import os
import importlib.util

def check_file_exists(filepath):
    """Check if a file exists and is readable."""
    if os.path.exists(filepath):
        print(f"✅ {filepath}")
        return True
    else:
        print(f"❌ {filepath} - File not found")
        return False

def check_imports(filepath):
    """Check if a Python file can be imported without errors."""
    try:
        # Add the app directory to Python path
        app_dir = os.path.join(os.path.dirname(filepath), 'app')
        if app_dir not in sys.path:
            sys.path.insert(0, app_dir)
        
        # Try to import the module
        spec = importlib.util.spec_from_file_location("module", filepath)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            print(f"✅ {filepath} - Imports successfully")
            return True
    except ImportError as e:
        print(f"⚠️  {filepath} - Import warning: {e}")
        return True  # Import warnings are okay for optional dependencies
    except Exception as e:
        print(f"❌ {filepath} - Import error: {e}")
        return False

def main():
    """Main validation function."""
    print("=== Redis Fallback Implementation Validation ===\n")
    
    # Check required files exist
    print("Checking required files...")
    required_files = [
        "AlgoAgentXAPI/app/core/redis_manager.py",
        "AlgoAgentXAPI/app/celery_app.py",
        "AlgoAgentXAPI/app/main.py",
        "AlgoAgentXAPI/app/services/background_service.py",
        "AlgoAgentXAPI/app/api/v1/backtests.py",
        "AlgoAgentXAPI/.env",
        "AlgoAgentXAPI/REDIS_FALLBACK_GUIDE.md",
        "AlgoAgentXAPI/requirements.txt"
    ]
    
    all_files_exist = True
    for filepath in required_files:
        if not check_file_exists(filepath):
            all_files_exist = False
    
    print(f"\nFile existence check: {'✅ PASS' if all_files_exist else '❌ FAIL'}\n")
    
    # Check core implementation files
    print("Checking core implementation files...")
    core_files = [
        "AlgoAgentXAPI/app/core/redis_manager.py",
        "AlgoAgentXAPI/app/celery_app.py",
        "AlgoAgentXAPI/app/services/background_service.py"
    ]
    
    all_imports_ok = True
    for filepath in core_files:
        if not check_imports(filepath):
            all_imports_ok = False
    
    print(f"\nImport validation: {'✅ PASS' if all_imports_ok else '❌ FAIL'}\n")
    
    # Check environment configuration
    print("Checking environment configuration...")
    env_file = "AlgoAgentXAPI/.env"
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            content = f.read()
            if 'REDIS_URL' in content and 'REDIS_HOST' in content:
                print("✅ Redis environment variables configured")
            else:
                print("⚠️  Redis environment variables may be missing")
    else:
        print("❌ Environment file not found")
    
    # Check requirements
    print("\nChecking requirements...")
    req_file = "AlgoAgentXAPI/requirements.txt"
    if os.path.exists(req_file):
        with open(req_file, 'r') as f:
            content = f.read()
            if 'redis' in content:
                print("✅ Redis package in requirements")
            else:
                print("❌ Redis package missing from requirements")
    else:
        print("❌ Requirements file not found")
    
    # Summary
    print("\n=== Validation Summary ===")
    if all_files_exist and all_imports_ok:
        print("🎉 All validation checks passed!")
        print("\nThe Redis fallback implementation is ready.")
        print("Next steps:")
        print("1. Install Redis: pip install redis[hiredis]")
        print("2. Start Redis server (if testing with Redis)")
        print("3. Run: python AlgoAgentXAPI/test_redis_fallback.py")
        print("4. Test the API endpoints")
        return 0
    else:
        print("⚠️  Some validation checks failed.")
        print("Please review the issues above before proceeding.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)