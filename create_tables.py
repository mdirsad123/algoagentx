#!/usr/bin/env python3
"""
Simple script to create database tables for AlgoAgentX
"""
import asyncio
import sys
from pathlib import Path
import os

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Set environment to development
os.environ.setdefault('ENVIRONMENT', 'development')

try:
    from app.db.base import Base
    from app.db.session import engine
    from app.core.config import settings
    
    async def create_tables():
        """Create all database tables"""
        print(f"Creating tables with database URL: {settings.masked_database_url}")
        
        try:
            # Create all tables
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            print("✅ Database tables created successfully!")
            print(f"Database file: {settings.database_url.split('///')[-1] if 'sqlite' in settings.database_url else 'PostgreSQL'}")
            
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        return True

    if __name__ == "__main__":
        asyncio.run(create_tables())
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)
