#!/usr/bin/env python3
"""
Seed script for subscription system data
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings


async def seed_data():
    """Seed plans and ensure user_credits exist for all users"""
    
            # Create sync engine for seeding
    engine = create_engine(settings.database_url.replace("+asyncpg", ""))
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    try:
        with SessionLocal() as db:
            print("Seeding plans...")
            
            # Insert plans
            plans_data = [
                {
                    'code': 'FREE',
                    'billing_period': 'NONE',
                    'price_inr': 0,
                    'included_credits': 50,
                    'features': {
                        'backtests_per_day': 5,
                        'ai_runs_per_day': 3,
                        'max_parallel_jobs': 1,
                        'max_strategies': 3,
                        'support_priority': 'LOW'
                    }
                },
                {
                    'code': 'PRO',
                    'billing_period': 'MONTHLY',
                    'price_inr': 999,
                    'included_credits': 500,
                    'features': {
                        'backtests_per_day': 50,
                        'ai_runs_per_day': 20,
                        'max_parallel_jobs': 3,
                        'max_strategies': 10,
                        'support_priority': 'MEDIUM'
                    }
                },
                {
                    'code': 'PRO',
                    'billing_period': 'YEARLY',
                    'price_inr': 9999,
                    'included_credits': 6000,
                    'features': {
                        'backtests_per_day': 50,
                        'ai_runs_per_day': 20,
                        'max_parallel_jobs': 3,
                        'max_strategies': 10,
                        'support_priority': 'MEDIUM'
                    }
                },
                {
                    'code': 'PREMIUM',
                    'billing_period': 'MONTHLY',
                    'price_inr': 1999,
                    'included_credits': 1500,
                    'features': {
                        'backtests_per_day': 200,
                        'ai_runs_per_day': 100,
                        'max_parallel_jobs': 5,
                        'max_strategies': 25,
                        'support_priority': 'HIGH'
                    }
                },
                {
                    'code': 'PREMIUM',
                    'billing_period': 'YEARLY',
                    'price_inr': 19999,
                    'included_credits': 18000,
                    'features': {
                        'backtests_per_day': 200,
                        'ai_runs_per_day': 100,
                        'max_parallel_jobs': 5,
                        'max_strategies': 25,
                        'support_priority': 'HIGH'
                    }
                },
                {
                    'code': 'ULTIMATE',
                    'billing_period': 'MONTHLY',
                    'price_inr': 3999,
                    'included_credits': 5000,
                    'features': {
                        'backtests_per_day': 500,
                        'ai_runs_per_day': 300,
                        'max_parallel_jobs': 10,
                        'max_strategies': 50,
                        'support_priority': 'PRIORITY'
                    }
                },
                {
                    'code': 'ULTIMATE',
                    'billing_period': 'YEARLY',
                    'price_inr': 39999,
                    'included_credits': 60000,
                    'features': {
                        'backtests_per_day': 500,
                        'ai_runs_per_day': 300,
                        'max_parallel_jobs': 10,
                        'max_strategies': 50,
                        'support_priority': 'PRIORITY'
                    }
                }
            ]
            
            # Check if plans already exist
            existing_plans = db.execute(text("SELECT COUNT(*) FROM plans")).scalar()
            if existing_plans > 0:
                print(f"Plans already exist ({existing_plans}), skipping...")
            else:
                for plan_data in plans_data:
                    db.execute(text("""
                        INSERT INTO plans (code, billing_period, price_inr, included_credits, features, is_active)
                        VALUES (:code, :billing_period, :price_inr, :included_credits, :features, :is_active)
                    """), {
                        'code': plan_data['code'],
                        'billing_period': plan_data['billing_period'],
                        'price_inr': plan_data['price_inr'],
                        'included_credits': plan_data['included_credits'],
                        'features': plan_data['features'],
                        'is_active': True
                    })
                db.commit()
                print(f"Inserted {len(plans_data)} plans")
            
            # Ensure user_credits exist for all users
            print("Ensuring user_credits exist for all users...")
            
            # Get all users without credits
            users_without_credits = db.execute(text("""
                SELECT id FROM users 
                WHERE id NOT IN (SELECT user_id FROM user_credits)
            """)).fetchall()
            
            if users_without_credits:
                for user_row in users_without_credits:
                    user_id = str(user_row[0])
                    db.execute(text("""
                        INSERT INTO user_credits (user_id, balance, updated_at)
                        VALUES (:user_id, :balance, :updated_at)
                    """), {
                        'user_id': user_id,
                        'balance': 0,
                        'updated_at': datetime.utcnow()
                    })
                db.commit()
                print(f"Created user_credits for {len(users_without_credits)} users")
            else:
                print("All users already have user_credits entries")
            
            print("Seeding completed successfully!")
            
    except Exception as e:
        print(f"Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(seed_data())