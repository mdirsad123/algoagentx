#!/usr/bin/env python3
"""
Script to analyze current database schema and generate migration plan
"""
import asyncio
import asyncpg
import os
from typing import Dict, List, Set

# Database connection from environment
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://algo_user:algo_password@localhost:5436/algo_db')

async def analyze_schema():
    """Analyze current database schema"""
    
    # Parse connection string for asyncpg
    conn_str = DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')
    
    conn = await asyncpg.connect(conn_str)
    
    try:
        # Get all tables in public schema
        tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """
        tables = await conn.fetch(tables_query)
        table_names = {row['table_name'] for row in tables}
        
        print("=== CURRENT DATABASE SCHEMA ANALYSIS ===")
        print(f"Found {len(table_names)} tables:")
        for table in sorted(table_names):
            print(f"  - {table}")
        
        # Analyze each table's structure
        print("\n=== TABLE STRUCTURE ANALYSIS ===")
        
        for table_name in sorted(table_names):
            print(f"\n--- Table: {table_name} ---")
            
            # Get columns
            columns_query = """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = $1
                ORDER BY ordinal_position;
            """
            columns = await conn.fetch(columns_query, table_name)
            
            print("Columns:")
            for col in columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                print(f"  - {col['column_name']}: {col['data_type']} {nullable}{default}")
            
            # Get constraints
            constraints_query = """
                SELECT constraint_name, constraint_type
                FROM information_schema.table_constraints 
                WHERE table_schema = 'public' 
                AND table_name = $1
                ORDER BY constraint_type, constraint_name;
            """
            constraints = await conn.fetch(constraints_query, table_name)
            
            if constraints:
                print("Constraints:")
                for const in constraints:
                    print(f"  - {const['constraint_name']}: {const['constraint_type']}")
            
            # Get indexes
            indexes_query = """
                SELECT indexname, indexdef
                FROM pg_indexes 
                WHERE schemaname = 'public' 
                AND tablename = $1
                ORDER BY indexname;
            """
            indexes = await conn.fetch(indexes_query, table_name)
            
            if indexes:
                print("Indexes:")
                for idx in indexes:
                    print(f"  - {idx['indexname']}: {idx['indexdef']}")
        
        # Check for required tables
        required_tables = {
            'plans', 'user_subscriptions', 'user_credits', 'credit_transactions',
            'payments', 'notifications', 'backtest_runs'
        }
        
        missing_tables = required_tables - table_names
        existing_required = required_tables & table_names
        
        print(f"\n=== REQUIRED TABLES ANALYSIS ===")
        print(f"Missing tables: {sorted(missing_tables)}")
        print(f"Existing required tables: {sorted(existing_required)}")
        
        # Check users table structure for FK compatibility
        print(f"\n=== USERS TABLE ANALYSIS (for FK compatibility) ===")
        if 'users' in table_names:
            users_query = """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'users'
                ORDER BY ordinal_position;
            """
            users_columns = await conn.fetch(users_query)
            
            print("Users table columns:")
            for col in users_columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                print(f"  - {col['column_name']}: {col['data_type']} {nullable}{default}")
        
        # Check job_status table for backtest_runs FK compatibility
        print(f"\n=== JOB_STATUS TABLE ANALYSIS (for backtest_runs FK compatibility) ===")
        if 'job_status' in table_names:
            job_status_query = """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'job_status'
                ORDER BY ordinal_position;
            """
            job_status_columns = await conn.fetch(job_status_query)
            
            print("Job_status table columns:")
            for col in job_status_columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                print(f"  - {col['column_name']}: {col['data_type']} {nullable}{default}")
        
        return table_names, missing_tables, existing_required
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(analyze_schema())