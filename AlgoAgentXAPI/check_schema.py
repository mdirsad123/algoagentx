#!/usr/bin/env python3
import asyncio
from sqlalchemy import text
from app.db.session import async_session

async def check_schema():
    try:
        async with async_session() as db:
            # Check if users table has is_active column
            result = await db.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                ORDER BY column_name
            """))
            columns = result.all()
            print('Users table columns:')
            for col in columns:
                print(f'  {col[0]}: {col[1]}')
            
            # Check if there are any users
            result = await db.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar()
            print(f'Total users: {count}')
            
            # Check user data
            result = await db.execute(text("SELECT id, email, role, fullname, mobile FROM users LIMIT 5"))
            users = result.all()
            print('Sample users:')
            for user in users:
                print(f'  {user}')
                
    except Exception as e:
        print(f'Error: {e}')

if __name__ == "__main__":
    asyncio.run(check_schema())