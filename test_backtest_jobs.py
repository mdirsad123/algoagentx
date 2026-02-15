#!/usr/bin/env python3
"""
Test script for backtest job functionality.
This script demonstrates how to use the new background job system.
"""

import requests
import time
import json

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer your-jwt-token-here"  # Replace with actual token
}

def test_backtest_job():
    """Test the complete backtest job workflow."""
    
    print("=== Backtest Job Test ===")
    
    # 1. Submit a backtest job
    print("\n1. Submitting backtest job...")
    
    backtest_request = {
        "strategy_id": "your-strategy-id",  # Replace with actual strategy ID
        "instrument_id": 1,  # Replace with actual instrument ID
        "timeframe": "1d",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "capital": 100000
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/backtests/run",
            headers=HEADERS,
            json=backtest_request
        )
        
        if response.status_code == 202:
            job_data = response.json()
            job_id = job_data["job_id"]
            print(f"✓ Job submitted successfully! Job ID: {job_id}")
            print(f"  Status: {job_data['status']}")
            print(f"  Message: {job_data['message']}")
        else:
            print(f"✗ Failed to submit job: {response.status_code}")
            print(response.text)
            return
            
    except Exception as e:
        print(f"✗ Error submitting job: {e}")
        return
    
    # 2. Poll job status
    print(f"\n2. Polling job status for {job_id}...")
    
    max_polls = 30  # Poll for up to 5 minutes (30 * 10 seconds)
    poll_count = 0
    
    while poll_count < max_polls:
        try:
            response = requests.get(f"{BASE_URL}/jobs/{job_id}", headers=HEADERS)
            
            if response.status_code == 200:
                status_data = response.json()
                status = status_data["status"]
                progress = status_data["progress"]
                message = status_data["message"]
                
                print(f"  Status: {status} | Progress: {progress}% | Message: {message}")
                
                if status == "completed":
                    print("✓ Job completed successfully!")
                    if "result_data" in status_data and status_data["result_data"]:
                        result = status_data["result_data"]
                        print(f"  Backtest ID: {result.get('backtest_id', 'N/A')}")
                        print(f"  Net Profit: ${result.get('net_profit', 0):,.2f}")
                        print(f"  Win Rate: {result.get('win_rate', 0) * 100:.1f}%")
                        print(f"  Total Trades: {result.get('total_trades', 0)}")
                    break
                elif status == "failed":
                    print(f"✗ Job failed: {message}")
                    break
                elif status == "retry":
                    print(f"⚠ Job retrying: {message}")
                else:
                    # Continue polling
                    pass
                    
            else:
                print(f"✗ Failed to get job status: {response.status_code}")
                print(response.text)
                
        except Exception as e:
            print(f"✗ Error polling job status: {e}")
        
        poll_count += 1
        time.sleep(10)  # Wait 10 seconds between polls
    
    if poll_count >= max_polls:
        print("⚠ Max polling attempts reached, job may still be running")
    
    # 3. Get user jobs list
    print(f"\n3. Getting user jobs list...")
    
    try:
        response = requests.get(f"{BASE_URL}/jobs/", headers=HEADERS)
        
        if response.status_code == 200:
            jobs_data = response.json()
            jobs = jobs_data.get("jobs", [])
            print(f"✓ Found {len(jobs)} jobs")
            
            for job in jobs[:5]:  # Show first 5 jobs
                print(f"  Job {job['id']}: {job['status']} | {job['progress']}% | {job['message']}")
        else:
            print(f"✗ Failed to get jobs list: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"✗ Error getting jobs list: {e}")

def test_example_curl_requests():
    """Print example curl requests for manual testing."""
    
    print("\n=== Example Curl Requests ===")
    
    print("\n1. Submit backtest job:")
    print("""curl -X POST "http://localhost:8000/api/v1/backtests/run" \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer your-jwt-token" \\
  -d '{
    "strategy_id": "your-strategy-id",
    "instrument_id": 1,
    "timeframe": "1d",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "capital": 100000
  }'""")
    
    print("\n2. Check job status:")
    print("""curl -X GET "http://localhost:8000/api/v1/jobs/your-job-id" \\
  -H "Authorization: Bearer your-jwt-token" """)
    
    print("\n3. List user jobs:")
    print("""curl -X GET "http://localhost:8000/api/v1/jobs/" \\
  -H "Authorization: Bearer your-jwt-token" """)
    
    print("\n4. Retry failed job:")
    print("""curl -X POST "http://localhost:8000/api/v1/jobs/your-job-id/retry" \\
  -H "Authorization: Bearer your-jwt-token" """)

if __name__ == "__main__":
    test_example_curl_requests()
    print("\n" + "="*50)
    print("To test the actual functionality:")
    print("1. Start the FastAPI server")
    print("2. Replace placeholder values in test_backtest_job()")
    print("3. Run: python test_backtest_jobs.py")
    print("="*50)