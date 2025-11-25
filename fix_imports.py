"""
Script to fix all import statements for PyPI package structure.
Converts absolute imports to package-relative imports.
"""
import re
from pathlib import Path

# Root directory
root = Path(__file__).parent
source_atlas_dir = root / "source_atlas"

# Import patterns to replace
replacements = [
    # Main modules
    (r'\bfrom analyzers\.', 'from source_atlas.analyzers.'),
    (r'\bfrom extractors\.', 'from source_atlas.extractors.'),
    (r'\bfrom lsp\.', 'from source_atlas.lsp.'),
    (r'\bfrom models\.', 'from source_atlas.models.'),
    (r'\bfrom neo4jdb\.', 'from source_atlas.neo4jdb.'),
    (r'\bfrom config\.', 'from source_atlas.config.'),
    (r'\bfrom utils\.', 'from source_atlas.utils.'),
    
    # Standalone imports
    (r'\bfrom cli import', 'from source_atlas.cli import'),
    (r'\bimport analyzers\.', 'import source_atlas.analyzers.'),
    (r'\bimport extractors\.', 'import source_atlas.extractors.'),
    (r'\bimport lsp\.', 'import source_atlas.lsp.'),
    (r'\bimport models\.', 'import source_atlas.models.'),
    (r'\bimport neo4jdb\.', 'import source_atlas.neo4jdb.'),
    (r'\bimport config\.', 'import source_atlas.config.'),
    (r'\bimport utils\.', 'import source_atlas.utils.'),
]

def fix_imports_in_file(file_path: Path) -> tuple[bool, int]:
    """
    Fix imports in a single file.
    
    Returns:
        (changed, num_replacements)
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        num_replacements = 0
        
        for pattern, replacement in replacements:
            new_content, count = re.subn(pattern, replacement, content)
            if count > 0:
                content = new_content
                num_replacements += count
        
        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            return True, num_replacements
        
        return False, 0
    except Exception as e:
        print(f"  ⚠️  Error processing {file_path}: {e}")
        return False, 0

def process_directory(directory: Path):
    """Process all Python files in a directory recursively."""
    print(f"\n📂 Processing directory: {directory.relative_to(root)}")
    
    files_changed = 0
    total_replacements = 0
    
    for py_file in directory.rglob("*.py"):
        changed, count = fix_imports_in_file(py_file)
        if changed:
            files_changed += 1
            total_replacements += count
            rel_path = py_file.relative_to(root)
            print(f"  ✅ {rel_path} ({count} replacements)")
    
    return files_changed, total_replacements

# Main execution
print("=" * 70)
print("FIXING IMPORT STATEMENTS FOR PYPI PACKAGE")
print("=" * 70)

total_files = 0
total_replacements = 0

# Process source_atlas directory
if source_atlas_dir.exists():
    files, replacements = process_directory(source_atlas_dir)
    total_files += files
    total_replacements += replacements

# Process tests directory
tests_dir = root / "tests"
if tests_dir.exists():
    files, replacements = process_directory(tests_dir)
    total_files += files
    total_replacements += replacements

# Process main.py if it exists at root
main_py = root / "main.py"
if main_py.exists():
    changed, count = fix_imports_in_file(main_py)
    if changed:
        total_files += 1
        total_replacements += count
        print(f"\n  ✅ main.py ({count} replacements)")

print("\n" + "=" * 70)
print(f"✅ COMPLETE!")
print(f"   Files modified: {total_files}")
print(f"   Total replacements: {total_replacements}")
print("=" * 70)
