#!/usr/bin/env python3
"""
Redis connectivity checker and setup helper for AlgoAgentX.
This script helps diagnose Redis connection issues and provides setup guidance.
"""

import os
import sys
import subprocess
import socket
from pathlib import Path

def check_redis_server(host='localhost', port=6379, timeout=5):
    """Check if Redis server is running and accessible."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False

def check_redis_cli():
    """Check if redis-cli is available."""
    try:
        result = subprocess.run(['redis-cli', 'ping'], 
                              capture_output=True, text=True, timeout=5)
        return result.returncode == 0 and 'PONG' in result.stdout
    except Exception:
        return False

def check_docker_redis():
    """Check if Redis is running in Docker."""
    try:
        result = subprocess.run(['docker', 'ps'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return 'redis' in result.stdout.lower()
        return False
    except Exception:
        return False

def get_redis_status():
    """Get comprehensive Redis status information."""
    print("=== Redis Status Check ===\n")
    
    # Check if Redis server is running locally
    print("1. Checking local Redis server...")
    if check_redis_server():
        print("✅ Redis server is running on localhost:6379")
        if check_redis_cli():
            print("✅ redis-cli is working correctly")
        else:
            print("⚠️  redis-cli not available or not working")
    else:
        print("❌ Redis server is not running on localhost:6379")
    
    # Check Docker Redis
    print("\n2. Checking Docker Redis...")
    if check_docker_redis():
        print("✅ Redis is running in Docker")
    else:
        print("❌ No Redis container found in Docker")
    
    # Check environment configuration
    print("\n3. Checking environment configuration...")
    env_file = Path("AlgoAgentXAPI/.env")
    if env_file.exists():
        with open(env_file, 'r') as f:
            content = f.read()
            if 'REDIS_URL' in content:
                print("✅ Redis environment variables found in .env")
                if 'redis://localhost:6379/0' in content:
                    print("   Using default localhost:6379 configuration")
            else:
                print("⚠️  No Redis configuration found in .env")
    else:
        print("❌ .env file not found")
    
    # Check requirements
    print("\n4. Checking Python dependencies...")
    try:
        import redis
        print("✅ redis package is installed")
    except ImportError:
        print("❌ redis package not installed - run: pip install redis[hiredis]")
    
    try:
        import celery
        print("✅ celery package is installed")
    except ImportError:
        print("❌ celery package not installed - run: pip install celery")

def provide_setup_instructions():
    """Provide setup instructions based on current status."""
    print("\n=== Setup Instructions ===\n")
    
    if check_redis_server():
        print("🎉 Redis is already running! Your application should work with Redis.")
        print("   No further action needed.")
        return
    
    print("Redis server is not running. Here are your options:\n")
    
    print("Option 1: Install Redis using Docker (Recommended)")
    print("   docker run -d -p 6379:6379 --name algoagentx-redis redis:alpine")
    print("   docker exec algoagentx-redis redis-cli ping  # Should return PONG\n")
    
    print("Option 2: Install Redis on Windows")
    print("   1. Download from: https://github.com/microsoftarchive/redis/releases")
    print("   2. Run the installer")
    print("   3. Start Redis: redis-server.exe\n")
    
    print("Option 3: Use external Redis service")
    print("   - Sign up at: https://redis.com/try-free/")
    print("   - Update .env with your connection details\n")
    
    print("Option 4: Continue without Redis (Fallback mode)")
    print("   - Your application will use FastAPI BackgroundTasks")
    print("   - No installation needed, but less robust for production\n")

def main():
    """Main function to run Redis status check."""
    print("AlgoAgentX Redis Connectivity Checker\n")
    print("This script helps diagnose Redis connection issues and provides setup guidance.\n")
    
    # Change to the correct directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    get_redis_status()
    provide_setup_instructions()
    
    print("=== Summary ===")
    if check_redis_server():
        print("✅ Redis is ready to use!")
    else:
        print("⚠️  Redis needs to be set up. Follow the instructions above.")
        print("💡 Note: Your application will still work using fallback mode.")

if __name__ == "__main__":
    main()