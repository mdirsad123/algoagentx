#!/usr/bin/env python3
"""
Fix UUID import issues in all model files
"""

import os
import re

def fix_file(file_path):
    """Fix UUID imports and usage in a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Check if file uses PG_UUID without import
        if 'PG_UUID(' in content and 'from sqlalchemy.dialects.postgresql import UUID as PG_UUID' not in content:
            # Add the import
            if 'from sqlalchemy import' in content:
                # Find the first sqlalchemy import and add our import after
                content = re.sub(
                    r'(from sqlalchemy import[^\n]*\n)',
                    r'\1from sqlalchemy.dialects.postgresql import UUID as PG_UUID\n',
                    content,
                    count=1
                )
            else:
                # Add at the beginning
                content = 'from sqlalchemy.dialects.postgresql import UUID as PG_UUID\n' + content
        
        # Replace any existing problematic UUID imports
        if 'from sqlalchemy.dialects.postgresql import UUID' in content:
            # Replace the import
            content = re.sub(
                r'from sqlalchemy.dialects.postgresql import UUID',
                'from sqlalchemy.dialects.postgresql import UUID as PG_UUID',
                content
            )
            
        # Replace UUID(as_uuid=True) with PG_UUID(as_uuid=True)
        content = re.sub(r'UUID\(as_uuid=True\)', 'PG_UUID(as_uuid=True)', content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Fixed UUID imports: {file_path}")
        else:
            print(f"⚪ No UUID changes needed: {file_path}")
            
    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")

def main():
    print("🔧 Fixing UUID imports in all model files...")
    
    # Base path to models
    models_path = "AlgoAgentXAPI/app/db/models"
    
    # Get all Python files in models directory
    if os.path.exists(models_path):
        for filename in os.listdir(models_path):
            if filename.endswith('.py') and filename != '__init__.py':
                file_path = os.path.join(models_path, filename)
                fix_file(file_path)
    
    print("\n🎉 UUID import fixes completed!")

if __name__ == "__main__":
    main()