#!/usr/bin/env python3
"""
Fix syntax errors caused by duplicate imports
"""

import os
import re

def fix_file(file_path):
    """Fix syntax errors in a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Fix duplicate "as PG_UUID as PG_UUID" 
        content = re.sub(r' as PG_UUID as PG_UUID', ' as PG_UUID', content)
        
        # Fix "as PG_UUID as PGUUID"
        content = re.sub(r' as PG_UUID as PGUUID', ' as PG_UUID', content)
        
        # Fix "as PG_UUID as UUID"
        content = re.sub(r' as PG_UUID as UUID', ' as PG_UUID', content)
        
        # Fix any PG_PG_UUID references
        content = re.sub(r'PG_PG_UUID', 'PG_UUID', content)
        
        # Fix any PGPG_UUID references
        content = re.sub(r'PGPG_UUID', 'PG_UUID', content)
        
        # Fix any PGUUID references
        content = re.sub(r'PGUUID\(', 'PG_UUID(', content)
        
        # Fix any mangled UUID references
        content = re.sub(r'PG_UUID_UUID', 'PG_UUID', content)
        content = re.sub(r'UUID_PG_UUID', 'PG_UUID', content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Fixed syntax errors: {file_path}")
        else:
            print(f"⚪ No syntax fixes needed: {file_path}")
            
    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")

def main():
    print("🔧 Fixing syntax errors in all model files...")
    
    # Base path to models
    models_path = "AlgoAgentXAPI/app/db/models"
    
    # Get all Python files in models directory
    if os.path.exists(models_path):
        for filename in os.listdir(models_path):
            if filename.endswith('.py') and filename != '__init__.py':
                file_path = os.path.join(models_path, filename)
                fix_file(file_path)
    
    print("\n🎉 Syntax error fixes completed!")

if __name__ == "__main__":
    main()