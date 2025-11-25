"""
Script to fix all remaining LSP imports to use source_atlas prefix.
"""
import re
from pathlib import Path

def fix_lsp_imports(directory):
    """Fix all lsp internal imports to use source_atlas prefix."""
    fixed_files = []
    errors = []
    
    for py_file in Path(directory).rglob("*.py"):
        try:
            content = py_file.read_text(encoding='utf-8')
            original_content = content
            
            # Fix lsp imports
            content = re.sub(r'\bfrom lsp\.', 'from source_atlas.lsp.', content)
            content = re.sub(r'\bimport lsp\.', 'import source_atlas.lsp.', content)
            
            if content != original_content:
                py_file.write_text(content, encoding='utf-8')
                fixed_files.append(str(py_file.relative_to(Path(__file__).parent)))
        except Exception as e:
            errors.append(f"{py_file}: {e}")
    
    return fixed_files, errors

if __name__ == "__main__":
    lsp_dir = Path(__file__).parent / "source_atlas" / "lsp"
    
    print("Fixing LSP imports...")
    fixed, errors = fix_lsp_imports(lsp_dir)
    
    print(f"\n✅ Fixed {len(fixed)} files")
    for f in fixed[:10]:  # Show first 10
        print(f"  - {f}")
    if len(fixed) > 10:
        print(f"  ... and {len(fixed) - 10} more")
    
    if errors:
        print(f"\n⚠️  {len(errors)} errors:")
        for e in errors:
            print(f"  - {e}")
    
    print("\n✅ Done!")
