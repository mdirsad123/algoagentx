#!/usr/bin/env python3
"""
Quick script to check and create database tables
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings

def main():
    # Convert async URL to sync
    sync_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    print(f"Connecting to: {sync_url.replace(':algo_password', ':****')}")
    
    # Create sync engine
    engine = create_engine(sync_url, echo=False)
    
    try:
        # Check existing tables
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            tables = result.fetchall()
            print(f"Existing tables ({len(tables)}):")
            for table in tables:
                print(f"  - {table[0]}")
                
        if len(tables) == 0:
            print("\nNo tables found. Creating tables...")
            # Import all models to register them
            from app.db.base import Base
            
            # Create all tables
            Base.metadata.create_all(engine)
            print("Tables created successfully!")
            
            # Check tables again
            with engine.connect() as connection:
                result = connection.execute(text("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    ORDER BY table_name
                """))
                tables = result.fetchall()
                print(f"New tables ({len(tables)}):")
                for table in tables:
                    print(f"  - {table[0]}")
                    
        # Check for users table specifically
        users_exists = any('users' in str(table[0]).lower() for table in tables)
        print(f"\n✅ Users table exists: {users_exists}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        engine.dispose()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)