"""
Source Atlas - Entry point for CLI execution.

Allows running the package as a module: python -m source_atlas
"""

from source_atlas.cli import main
import sys

if __name__ == '__main__':
    sys.exit(main())
