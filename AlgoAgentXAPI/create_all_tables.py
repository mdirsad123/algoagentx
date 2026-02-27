#!/usr/bin/env python3
"""
Create all database tables directly using SQLAlchemy
"""

import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings
from app.db.base import Base

def create_tables():
    """Create all tables using sync SQLAlchemy"""
    # Convert async URL to sync
    sync_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    print(f"Creating tables with URL: {sync_url.replace(':algo_password', ':****')}")
    
    # Create sync engine
    engine = create_engine(sync_url, echo=True)
    
    try:
        # Test connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print(f"✅ Database connection successful!")
        
        # Create all tables
        print("Creating all tables...")
        Base.metadata.create_all(engine)
        print("✅ All tables created successfully!")
        
        # Show created tables
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            tables = result.fetchall()
            print(f"\nCreated {len(tables)} tables:")
            for table in tables:
                print(f"  - {table[0]}")
                
        return True
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False
    finally:
        engine.dispose()

if __name__ == "__main__":
    success = create_tables()
    sys.exit(0 if success else 1)