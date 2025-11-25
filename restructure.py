"""
Restructure script to move source files into source_atlas package directory.
"""
import shutil
from pathlib import Path

# Root directory
root = Path(__file__).parent

# Create source_atlas directory if it doesn't exist
package_dir = root / "source_atlas"
package_dir.mkdir(exist_ok=True)

# Directories and files to move into source_atlas/
items_to_move = [
    "analyzers",
    "extractors",
    "lsp",
    "models",
    "neo4jdb",
    "config",
    "utils",
    "__init__.py",
    "__main__.py",
    "cli.py",
]

print("Starting restructuring...")

for item in items_to_move:
    source = root / item
    dest = package_dir / item
    
    if source.exists():
        if dest.exists():
            print(f"  ⚠️  {item} already exists in destination, skipping...")
            continue
        
        print(f"  Moving {item}...")
        shutil.move(str(source), str(dest))
        print(f"  ✅ Moved {item}")
    else:
        print(f"  ⚠️  {item} not found, skipping...")

print("\n✅ Restructuring complete!")
print(f"Package directory: {package_dir}")
