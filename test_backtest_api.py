#!/usr/bin/env python3
"""
Test script for the backtest job API implementation.

This script demonstrates how to use the new backtest job system
with progress tracking and PostgreSQL-based job status management.
"""

import requests
import time
import json
import sys

# Configuration
BASE_URL = "http://localhost:8000"
API_KEY = "your-api-key-here"  # Replace with actual API key

def make_request(method, endpoint, data=None, headers=None):
    """Make HTTP request with error handling"""
    url = f"{BASE_URL}{endpoint}"
    default_headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    if headers:
        default_headers.update(headers)
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=default_headers)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, headers=default_headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        return None

def test_backtest_job():
    """Test the backtest job submission and polling workflow"""
    print("🧪 Testing Backtest Job API")
    print("=" * 50)
    
    # 1. Submit backtest job
    print("1. Submitting backtest job...")
    backtest_request = {
        "strategy_id": "your-strategy-id",  # Replace with actual strategy ID
        "instrument_id": 1,  # Replace with actual instrument ID
        "timeframe": "1d",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "capital": 100000
    }
    
    job_response = make_request("POST", "/api/v1/backtests/run", backtest_request)
    
    if not job_response:
        print("❌ Failed to submit backtest job")
        return
    
    job_id = job_response.get("job_id")
    print(f"✅ Job submitted successfully! Job ID: {job_id}")
    print(f"   Execution method: {job_response.get('execution_method', 'Unknown')}")
    
    # 2. Poll job status
    print("\n2. Polling job status...")
    max_polls = 30  # Maximum 30 polls (5 minutes)
    poll_interval = 10  # Poll every 10 seconds
    
    for i in range(max_polls):
        print(f"\n   Poll {i+1}/{max_polls}...")
        
        status_response = make_request("GET", f"/api/v1/jobs/{job_id}")
        
        if not status_response:
            print("❌ Failed to get job status")
            return
        
        status = status_response.get("status")
        progress = status_response.get("progress", 0)
        message = status_response.get("message", "Unknown")
        
        print(f"   Status: {status} | Progress: {progress}% | Message: {message}")
        
        if status == "completed":
            print("✅ Job completed successfully!")
            
            # Display results
            result_data = status_response.get("result_data")
            if result_data:
                print("\n📊 Backtest Results:")
                print(f"   Strategy: {result_data.get('strategy_name', 'Unknown')}")
                print(f"   Instrument: {result_data.get('instrument_symbol', 'Unknown')}")
                print(f"   Timeframe: {result_data.get('timeframe', 'Unknown')}")
                print(f"   Net Profit: ${result_data.get('net_profit', 0):,.2f}")
                print(f"   Win Rate: {result_data.get('win_rate', 0)*100:.1f}%")
                print(f"   Total Trades: {result_data.get('total_trades', 0)}")
            
            return
        elif status == "failed":
            print("❌ Job failed!")
            print(f"   Error: {message}")
            return
        elif status == "retry":
            print("🔄 Job is retrying...")
        
        # Wait before next poll
        if i < max_polls - 1:  # Don't wait after the last poll
            print(f"   Waiting {poll_interval} seconds before next poll...")
            time.sleep(poll_interval)
    
    print("⏰ Maximum polling attempts reached. Job may still be running.")
    print("   You can continue polling manually or check later.")

def test_job_list():
    """Test getting user jobs"""
    print("\n📋 Testing Job List API")
    print("=" * 50)
    
    jobs_response = make_request("GET", "/api/v1/jobs")
    
    if not jobs_response:
        print("❌ Failed to get job list")
        return
    
    jobs = jobs_response.get("jobs", [])
    print(f"✅ Found {len(jobs)} jobs")
    
    for job in jobs:
        print(f"   Job ID: {job.get('id')}")
        print(f"   Type: {job.get('job_type')}")
        print(f"   Status: {job.get('status')}")
        print(f"   Progress: {job.get('progress', 0)}%")
        print(f"   Created: {job.get('created_at')}")
        print()

def test_health_check():
    """Test health check endpoints"""
    print("\n🏥 Testing Health Check")
    print("=" * 50)
    
    # API health
    health_response = make_request("GET", "/health")
    if health_response:
        print(f"✅ API Health: {health_response.get('status')}")
    
    # Redis health
    redis_response = make_request("GET", "/health/redis")
    if redis_response:
        redis_available = redis_response.get("redis_available", False)
        print(f"{'✅' if redis_available else '⚠️ '} Redis: {'Available' if redis_available else 'Unavailable (using fallback)'}")

def main():
    """Main test function"""
    print("🚀 AlgoAgentX Backtest Job API Test Suite")
    print("=" * 60)
    
    # Test health checks first
    test_health_check()
    
    # Test job listing
    test_job_list()
    
    # Test backtest job workflow
    test_backtest_job()
    
    print("\n🏁 Test suite completed!")
    print("\n📝 Notes:")
    print("   - Replace placeholder values (API_KEY, strategy_id, instrument_id) with actual values")
    print("   - The system will work with or without Redis (fallback to FastAPI BackgroundTasks)")
    print("   - Progress tracking shows: FETCH_DATA(20%) → GENERATE_SIGNALS(50%) → BUILD_TRADES(70%) → METRICS(90%) → SAVE(100%)")
    print("   - All results are stored in PostgreSQL and linked to the job_id")

if __name__ == "__main__":
    main()