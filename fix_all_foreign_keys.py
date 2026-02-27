#!/usr/bin/env python3
"""
Fix all foreign key data type mismatches to use UUID instead of String(36)
"""

import os
import re

def fix_file(file_path, replacements):
    """Fix foreign key types in a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply replacements
        for pattern, replacement in replacements.items():
            content = re.sub(pattern, replacement, content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Fixed: {file_path}")
        else:
            print(f"⚪ No changes needed: {file_path}")
            
    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")

def main():
    print("🔧 Fixing all foreign key data type mismatches...")
    
    # Base path to models
    models_path = "AlgoAgentXAPI/app/db/models"
    
    # Files and their fixes
    files_to_fix = {
        "strategy_requests.py": {
            r'user_id = Column\(String\(36\), ForeignKey\("users\.id"\)': 'user_id = Column(UUID(as_uuid=True), ForeignKey("users.id")',
            r'from sqlalchemy import Column, String, Text, DateTime, Enum, JSON, Integer, ForeignKey': 'from sqlalchemy import Column, String, Text, DateTime, Enum, JSON, Integer, ForeignKey\nfrom sqlalchemy.dialects.postgresql import UUID'
        },
        
        "notifications.py": {
            r'user_id = Column\(String\(36\), ForeignKey\("users\.id"\)': 'user_id = Column(UUID(as_uuid=True), ForeignKey("users.id")',
            r'from sqlalchemy import Column, String, Text, DateTime, Boolean, JSON, ForeignKey': 'from sqlalchemy import Column, String, Text, DateTime, Boolean, JSON, ForeignKey\nfrom sqlalchemy.dialects.postgresql import UUID'
        },
        
        "job_status.py": {
            r'user_id = Column\(String\(36\), ForeignKey\("users\.id"\)': 'user_id = Column(UUID(as_uuid=True), ForeignKey("users.id")',
            r'from sqlalchemy import Column, String, DateTime, ForeignKey, Enum': 'from sqlalchemy import Column, String, DateTime, ForeignKey, Enum\nfrom sqlalchemy.dialects.postgresql import UUID'
        },
        
        "credit_transactions.py": {
            r'user_id = Column\(String\(36\), ForeignKey\("users\.id"\)': 'user_id = Column(UUID(as_uuid=True), ForeignKey("users.id")',
            r'from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Enum': 'from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Enum\nfrom sqlalchemy.dialects.postgresql import UUID'
        },
        
        "backtests.py": {
            r'user_id = Column\(String\(36\), ForeignKey\("users\.id"\)': 'user_id = Column(UUID(as_uuid=True), ForeignKey("users.id")',
            r'from sqlalchemy import Column, String, Date, Numeric, UUID, Integer, ForeignKey, DateTime, Index': 'from sqlalchemy import Column, String, Date, Numeric, Integer, ForeignKey, DateTime, Index\nfrom sqlalchemy.dialects.postgresql import UUID'
        }
    }
    
    # Fix each file
    for filename, replacements in files_to_fix.items():
        file_path = os.path.join(models_path, filename)
        if os.path.exists(file_path):
            fix_file(file_path, replacements)
        else:
            print(f"⚠️  File not found: {file_path}")
    
    print("\n🎉 Foreign key fixes completed!")

if __name__ == "__main__":
    main()