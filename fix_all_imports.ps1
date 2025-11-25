# PowerShell script to fix all imports for PyPI package
# Run this with: powershell -ExecutionPolicy Bypass -File fix_all_imports.ps1

$rootPath = $PSScriptRoot
$sourceAtlasPath = Join-Path $rootPath "source_atlas"

Write-Host "===================================" -ForegroundColor Cyan
Write-Host "Fixing Import Statements..." -ForegroundColor Cyan
Write-Host "===================================`n" -ForegroundColor Cyan

# Patterns to replace
$patterns = @(
    @{ Pattern = '\bfrom analyzers\.'; Replacement = 'from source_atlas.analyzers.' },
    @{ Pattern = '\bfrom extractors\.'; Replacement = 'from source_atlas.extractors.' },
    @{ Pattern = '\bfrom lsp\.'; Replacement = 'from source_atlas.lsp.' },
    @{ Pattern = '\bfrom models\.'; Replacement = 'from source_atlas.models.' },
    @{ Pattern = '\bfrom neo4jdb\.'; Replacement = 'from source_atlas.neo4jdb.' },
    @{ Pattern = '\bfrom config\.'; Replacement = 'from source_atlas.config.' },
    @{ Parameter = '\bfrom utils\.'; Replacement = 'from source_atlas.utils.' },
    @{ Pattern = '\bfrom cli import'; Replacement = 'from source_atlas.cli import' },
    @{ Pattern = '\bimport analyzers\.'; Replacement = 'import source_atlas.analyzers.' },
    @{ Pattern = '\bimport extractors\.'; Replacement = 'import source_atlas.extractors.' },
    @{ Pattern = '\bimport lsp\.'; Replacement = 'import source_atlas.lsp.' },
    @{ Pattern = '\bimport models\.'; Replacement = 'import source_atlas.models.' },
    @{ Pattern = '\bimport neo4jdb\.'; Replacement = 'import source_atlas.neo4jdb.' },
    @{ Pattern = '\bimport config\.'; Replacement = 'import source_atlas.config.' },
    @{ Pattern = '\bimport utils\.'; Replacement = 'import source_atlas.utils.' }
)

$totalFiles = 0
$totalReplacements = 0

# Process source_atlas directory
if (Test-Path $sourceAtlasPath) {
    Write-Host "Processing source_atlas directory..." -ForegroundColor Yellow
    Get-ChildItem -Path $sourceAtlasPath -Filter "*.py" -Recurse | ForEach-Object {
        $filePath = $_.FullName
        $content = Get-Content -Path $filePath -Raw -Encoding UTF8
        $originalContent = $content
        $fileReplacements = 0
        
        foreach ($pattern in $patterns) {
            $newContent = $content -replace $pattern.Pattern, $pattern.Replacement
            if ($newContent -ne $content) {
                $matches = [regex]::Matches($content, $pattern.Pattern)
                $fileReplacements += $matches.Count
                $content = $newContent
            }
        }
        
        if ($content -ne $originalContent) {
            Set-Content -Path $filePath -Value $content -Encoding UTF8 -NoNewline
            $totalFiles++
            $totalReplacements += $fileReplacements
            $relativePath = $filePath.Substring($rootPath.Length + 1)
            Write-Host "  ✓ $relativePath ($fileReplacements replacements)" -ForegroundColor Green
        }
    }
}

# Process tests directory
$testsPath = Join-Path $rootPath "tests"
if (Test-Path $testsPath) {
    Write-Host "`nProcessing tests directory..." -ForegroundColor Yellow
    Get-ChildItem -Path $testsPath -Filter "*.py" -Recurse | ForEach-Object {
        $filePath = $_.FullName
        $content = Get-Content -Path $filePath -Raw -Encoding UTF8
        $originalContent = $content
        $fileReplacements = 0
        
        foreach ($pattern in $patterns) {
            $newContent = $content -replace $pattern.Pattern, $pattern.Replacement
            if ($newContent -ne $content) {
                $matches = [regex]::Matches($content, $pattern.Pattern)
                $fileReplacements += $matches.Count
                $content = $newContent
            }
        }
        
        if ($content -ne $originalContent) {
            Set-Content -Path $filePath -Value $content -Encoding UTF8 -NoNewline
            $totalFiles++
            $totalReplacements += $fileReplacements
            $relativePath = $filePath.Substring($rootPath.Length + 1)
            Write-Host "  ✓ $relativePath ($fileReplacements replacements)" -ForegroundColor Green
        }
    }
}

# Process main.py
$mainPy = Join-Path $rootPath "main.py"
if (Test-Path $mainPy) {
    Write-Host "`nProcessing main.py..." -ForegroundColor Yellow
    $content = Get-Content -Path $mainPy -Raw -Encoding UTF8
    $originalContent = $content
    $fileReplacements = 0
    
    foreach ($pattern in $patterns) {
        $newContent = $content -replace $pattern.Pattern, $pattern.Replacement
        if ($newContent -ne $content) {
            $matches = [regex]::Matches($content, $pattern.Pattern)
            $fileReplacements += $matches.Count
            $content = $newContent
        }
    }
    
    if ($content -ne $originalContent) {
        Set-Content -Path $mainPy -Value $content -Encoding UTF8 -NoNewline
        $totalFiles++
        $totalReplacements += $fileReplacements
        Write-Host "  ✓ main.py ($fileReplacements replacements)" -ForegroundColor Green
    }
}

Write-Host "`n===================================" -ForegroundColor Cyan
Write-Host "✓ Complete!" -ForegroundColor Green
Write-Host "  Files modified: $totalFiles" -ForegroundColor White
Write-Host "  Total replacements: $totalReplacements" -ForegroundColor White
Write-Host "===================================" -ForegroundColor Cyan
