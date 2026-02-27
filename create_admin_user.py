#!/usr/bin/env python3
"""
Script to create admin user with specified credentials.
"""

import os
import sys
import subprocess

# Set environment variables
os.environ['ADMIN_EMAIL'] = 'algoagentx@gmail.com'
os.environ['ADMIN_PASSWORD'] = 'admin@123'

# Run the admin creation script
result = subprocess.run([sys.executable, 'AlgoAgentXAPI/scripts/create_admin.py'], 
                       capture_output=True, text=True)

print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)
print(f"\nReturn code: {result.returncode}")