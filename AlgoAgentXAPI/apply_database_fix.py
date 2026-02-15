#!/usr/bin/env python3
"""
Direct database fix script to add missing columns to users table
"""
import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def apply_database_fix():
    """Apply the database fix directly"""
    try:
        # Import database configuration
        from app.core.config import settings
        from sqlalchemy import create_engine, text
        from sqlalchemy.ext.asyncio import create_async_engine
        
        print("🔧 Applying database schema fix...")
        print(f"📍 Database: {settings.masked_database_url}")
        
        # Create async engine
        engine = create_async_engine(settings.database_url)
        
        # SQL to add missing columns
        sql_statements = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS fullname VARCHAR;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS mobile VARCHAR;"
        ]
        
        async with engine.begin() as conn:
            for sql in sql_statements:
                print(f"📝 Executing: {sql}")
                await conn.execute(text(sql))
            
            # Verify the columns were added
            print("🔍 Verifying columns were added...")
            result = await conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name IN ('fullname', 'mobile')
                ORDER BY column_name;
            """))
            
            columns = result.fetchall()
            if columns:
                print("✅ Successfully added columns:")
                for col in columns:
                    print(f"   - {col[0]} ({col[1]})")
            else:
                print("❌ No columns found - verification failed")
                return False
            
        print("🎉 Database schema fix completed successfully!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you're running this from the AlgoAgentXAPI directory")
        return False
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

if __name__ == "__main__":
    # Run the async function
    success = asyncio.run(apply_database_fix())
    if not success:
        sys.exit(1)
    else:
        print("\n✨ Ready to test the login endpoint!")