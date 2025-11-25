@echo off
REM Script to create clean git history without static files

echo ========================================
echo Tao branch moi khong co static files
echo ========================================

REM 1. Tao orphan branch (khong co history)
echo [1/5] Tao orphan branch...
git checkout --orphan clean-main

REM 2. Add tat ca files (tru .gitignore)
echo [2/5] Add files...
git add -A

REM 3. Commit
echo [3/5] Commit...
git commit -m "chore: Clean history - prepare for PyPI publication"

REM 4. Xoa branch main cu
echo [4/5] Xoa branch main cu...
git branch -D main

REM 5. Doi ten branch
echo [5/5] Doi ten branch...
git branch -m main

echo.
echo ========================================
echo DONE! Bay gio chay:
echo   git push origin main --force
echo ========================================
pause
