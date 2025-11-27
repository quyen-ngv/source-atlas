@echo off
REM ============================================================================
REM Build and Publish Source Atlas to PyPI
REM ============================================================================

echo.
echo ========================================
echo Source Atlas - PyPI Publishing Script
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Show menu
echo Select an option:
echo.
echo 1. Clean build artifacts
echo 2. Build package
echo 3. Test build locally
echo 4. Upload to TestPyPI
echo 5. Upload to PyPI (Production)
echo 6. Full workflow (Clean + Build + TestPyPI)
echo 7. Exit
echo.

set /p choice="Enter your choice (1-7): "

if "%choice%"=="1" goto clean
if "%choice%"=="2" goto build
if "%choice%"=="3" goto test_local
if "%choice%"=="4" goto upload_test
if "%choice%"=="5" goto upload_prod
if "%choice%"=="6" goto full_workflow
if "%choice%"=="7" goto end
goto invalid_choice

:clean
echo.
echo [STEP 1/1] Cleaning build artifacts...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
for /d %%i in (*.egg-info) do rmdir /s /q "%%i"
echo Done!
goto end

:build
echo.
echo [STEP 1/2] Installing build tools...
py -m pip install --upgrade build twine
if %errorlevel% neq 0 (
    echo ERROR: Failed to install build tools
    pause
    exit /b 1
)

echo.
echo [STEP 2/2] Building package...
py -m build
if %errorlevel% neq 0 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo Files created in dist/:
dir dist
goto end

:test_local
echo.
echo [STEP 1/1] Installing package locally for testing...
echo.
echo Available wheel files:
dir dist\*.whl
echo.
set /p wheel_file="Enter wheel filename (or press Enter to use latest): "

if "%wheel_file%"=="" (
    for /f "delims=" %%i in ('dir /b /od dist\*.whl') do set wheel_file=%%i
)

echo Installing: dist\%wheel_file%
pip install dist\%wheel_file% --force-reinstall
if %errorlevel% neq 0 (
    echo ERROR: Installation failed
    pause
    exit /b 1
)

echo.
echo Testing import...
py -c "from source_atlas.analyzers.analyzer_factory import AnalyzerFactory; print('✓ Import successful')"
if %errorlevel% neq 0 (
    echo ERROR: Import test failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo Local installation test passed!
echo ========================================
goto end

:upload_test
echo.
echo [STEP 1/1] Uploading to TestPyPI...
echo.
echo You will need your TestPyPI API token.
echo Username: __token__
echo Password: (your TestPyPI token)
echo.
py -m twine upload --repository testpypi dist/*
if %errorlevel% neq 0 (
    echo ERROR: Upload to TestPyPI failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo Upload to TestPyPI completed!
echo ========================================
echo.
echo Test installation with:
echo pip install --index-url https://test.pypi.org/simple/ source-atlas
goto end

:upload_prod
echo.
echo ========================================
echo WARNING: You are about to upload to PyPI (PRODUCTION)
echo ========================================
echo.
set /p confirm="Are you sure? (yes/no): "
if /i not "%confirm%"=="yes" (
    echo Upload cancelled.
    goto end
)

echo.
echo [STEP 1/1] Uploading to PyPI...
echo.
echo You will need your PyPI API token.
echo Username: __token__
echo Password: (your PyPI token)
echo.
py -m twine upload dist/*
if %errorlevel% neq 0 (
    echo ERROR: Upload to PyPI failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo Upload to PyPI completed!
echo ========================================
echo.
echo Install with:
echo pip install source-atlas
goto end

:full_workflow
echo.
echo ========================================
echo Full Workflow: Clean + Build + TestPyPI
echo ========================================
echo.

echo [STEP 1/4] Cleaning build artifacts...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
for /d %%i in (*.egg-info) do rmdir /s /q "%%i"
echo Done!

echo.
echo [STEP 2/4] Installing build tools...
py -m pip install --upgrade build twine
if %errorlevel% neq 0 (
    echo ERROR: Failed to install build tools
    pause
    exit /b 1
)

echo.
echo [STEP 3/4] Building package...
py -m build
if %errorlevel% neq 0 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

echo.
echo [STEP 4/4] Uploading to TestPyPI...
echo.
echo You will need your TestPyPI API token.
echo Username: __token__
echo Password: (your TestPyPI token)
echo.
py -m twine upload --repository testpypi dist/*
if %errorlevel% neq 0 (
    echo ERROR: Upload to TestPyPI failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo Full workflow completed successfully!
echo ========================================
echo.
echo Test installation with:
echo pip install --index-url https://test.pypi.org/simple/ source-atlas
goto end

:invalid_choice
echo.
echo ERROR: Invalid choice. Please select 1-7.
pause
exit /b 1

:end
echo.
pause
