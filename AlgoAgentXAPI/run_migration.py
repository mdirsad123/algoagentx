#!/usr/bin/env python3
"""
Simple script to run Alembic migrations
"""
import os
import sys
from alembic.config import main

# Change to the AlgoAgentXAPI directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Run the migration
try:
    main(['upgrade', 'head'])
    print("Migration completed successfully!")
except Exception as e:
    print(f"Migration failed: {e}")
    sys.exit(1)