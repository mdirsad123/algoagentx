#!/usr/bin/env python3
"""
Test script to verify frontend compilation
"""

import os
import subprocess
import sys

def test_frontend_compilation():
    """Test if the frontend compiles without errors"""
    print("🔧 Testing Frontend Compilation")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("AlgoAgentXApp"):
        print("❌ AlgoAgentXApp directory not found")
        return False
    
    # Check if package.json exists
    package_json_path = "AlgoAgentXApp/package.json"
    if not os.path.exists(package_json_path):
        print("❌ package.json not found in AlgoAgentXApp")
        return False
    
    print("✅ Found AlgoAgentXApp directory")
    print("✅ Found package.json")
    
    # Check if the dashboard file exists and has correct imports
    dashboard_path = "AlgoAgentXApp/app/[locale]/(root)/dashboard/page.tsx"
    if not os.path.exists(dashboard_path):
        print("❌ Dashboard file not found")
        return False
    
    print("✅ Found dashboard file")
    
    # Read the dashboard file and check imports
    try:
        with open(dashboard_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for correct import patterns
        correct_imports = [
            'from "@/components/ui/card"',
            'from "@/components/ui/badge"',
            'from "@/components/layout/AppShell"'
        ]
        
        all_imports_correct = True
        for import_pattern in correct_imports:
            if import_pattern in content:
                print(f"✅ Found correct import: {import_pattern}")
            else:
                print(f"❌ Missing correct import: {import_pattern}")
                all_imports_correct = False
        
        if all_imports_correct:
            print("✅ All imports are correct!")
        else:
            print("❌ Some imports are still incorrect")
            return False
            
    except Exception as e:
        print(f"❌ Error reading dashboard file: {e}")
        return False
    
    # Try to run npm install and build (if npm is available)
    try:
        print("\n🔍 Attempting to test compilation...")
        
        # Change to AlgoAgentXApp directory
        os.chdir("AlgoAgentXApp")
        
        # Try to run npm install
        try:
            result = subprocess.run(['npm', 'install'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=60)
            if result.returncode == 0:
                print("✅ npm install successful")
            else:
                print(f"⚠️  npm install had issues: {result.stderr}")
        except subprocess.TimeoutExpired:
            print("⚠️  npm install timed out")
        except FileNotFoundError:
            print("⚠️  npm not found, skipping install")
        
        # Try to run npm run build
        try:
            result = subprocess.run(['npm', 'run', 'build'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=120)
            if result.returncode == 0:
                print("✅ Frontend compilation successful!")
                return True
            else:
                print(f"❌ Frontend compilation failed:")
                print(f"   Error: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("⚠️  Build timed out")
            return False
        except FileNotFoundError:
            print("⚠️  npm not found, cannot test compilation")
            return False
            
    except Exception as e:
        print(f"❌ Error during compilation test: {e}")
        return False
    finally:
        # Change back to original directory
        os.chdir("..")

def main():
    """Main function"""
    success = test_frontend_compilation()
    
    print("\n" + "=" * 50)
    print("📊 COMPILATION TEST RESULT:")
    if success:
        print("✅ Frontend compilation test PASSED!")
        print("💡 Your dashboard should now compile without errors.")
    else:
        print("❌ Frontend compilation test FAILED!")
        print("💡 Check the import statements and try again.")
    
    print("\n🔧 MANUAL VERIFICATION:")
    print("   1. cd AlgoAgentXApp")
    print("   2. npm run dev")
    print("   3. Check if dashboard loads at http://localhost:3000")

if __name__ == "__main__":
    main()