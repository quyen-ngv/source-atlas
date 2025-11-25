@echo off
REM Restructure source-atlas project for PyPI publication

echo Creating source_atlas package directory...
if not exist source_atlas mkdir source_atlas

echo.
echo Moving source files into source_atlas directory...
echo.

if exist analyzers (
    echo Moving analyzers...
    move analyzers source_atlas\analyzers
)

if exist extractors (
    echo Moving extractors...
    move extractors source_atlas\extractors
)

if exist lsp (
    echo Moving lsp...
    move lsp source_atlas\lsp
)

if exist models (
    echo Moving models...
    move models source_atlas\models
)

if exist neo4jdb (
    echo Moving neo4jdb...
    move neo4jdb source_atlas\neo4jdb
)

if exist config (
    echo Moving config...
    move config source_atlas\config
)

if exist utils (
    echo Moving utils...
    move utils source_atlas\utils
)

if exist __init__.py (
    echo Moving __init__.py...
    move __init__.py source_atlas\__init__.py
)

if exist __main__.py (
    echo Moving __main__.py...
    move __main__.py source_atlas\__main__.py
)

if exist cli.py (
    echo Moving cli.py...
    move cli.py source_atlas\cli.py
)

echo.
echo ======================================
echo Restructuring complete!
echo ======================================
echo.
echo Next steps:
echo 1. Update all import statements
echo 2. Update pyproject.toml
echo 3. Create MANIFEST.in
echo 4. Test the package
echo.
pause
