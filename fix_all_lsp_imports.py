"""
Bulk fix all LSP imports to use source_atlas prefix.
This script will recursively find and replace imports in the lsp directory.
"""
import re
from pathlib import Path

def fix_imports_in_file(file_path):
    """Fix imports in a single file."""
    try:
        content = file_path.read_text(encoding='utf-8')
        original = content
        
        # Fix: from lsp.multilspy -> from source_atlas.lsp.multilspy
        content = re.sub(
            r'\bfrom lsp\.multilspy',
            'from source_atlas.lsp.multilspy',
            content
        )
        
        # Fix: import lsp.multilspy -> import source_atlas.lsp.multilspy  
        content = re.sub(
            r'\bimport lsp\.multilspy',
            'import source_atlas.lsp.multilspy',
            content
        )
        
        if content != original:
            file_path.write_text(content, encoding='utf-8')
            return True, None
        return False, None
    except Exception as e:
        return False, str(e)

def main():
    lsp_dir = Path(__file__).parent / "source_atlas" / "lsp"
    
    if not lsp_dir.exists():
        print(f"❌ Directory not found: {lsp_dir}")
        return 1
    
    fixed_count = 0
    error_count = 0
    total_files = 0
    
    print(f"🔍 Scanning {lsp_dir}...")
    
    for py_file in lsp_dir.rglob("*.py"):
        total_files += 1
        was_fixed, error = fix_imports_in_file(py_file)
        
        if error:
            print(f"❌ Error in {py_file.relative_to(lsp_dir)}: {error}")
            error_count += 1
        elif was_fixed:
            print(f"✅ Fixed: {py_file.relative_to(lsp_dir)}")
            fixed_count += 1
    
    print(f"\n📊 Results:")
    print(f"   Total files scanned: {total_files}")
    print(f"   Files fixed: {fixed_count}")
    print(f"   Errors: {error_count}")
    
    return 0 if error_count == 0 else 1

if __name__ == "__main__":
    exit(main())
