@echo off
chcp 65001 >nul
echo ================================================================================
echo Manual GitHub Push (Most Reliable Method)
echo ================================================================================
echo.
echo Step 1: Create repository on GitHub website
echo.
echo 1. Open browser: https://github.com/new
echo 2. Repository name: explosive-compound-trading
echo 3. Description: Explosive Compound Trading Bot - ETH +4654%%, KIS +2634%%
echo 4. Select: Public
echo 5. DO NOT check "Initialize this repository with a README"
echo 6. Click "Create repository"
echo.
echo Press any key after creating the repository...
pause
echo.

cd /d "C:\Users\user\Documents\코드5"

echo Step 2: Add remote and push
echo.

REM Add remote
echo Adding remote...
git remote add origin https://github.com/seunghochoi2018/explosive-compound-trading.git

if %errorlevel% neq 0 (
    echo Remote already exists, updating...
    git remote set-url origin https://github.com/seunghochoi2018/explosive-compound-trading.git
)

echo.
echo Pushing to GitHub...
git push -u origin master

if %errorlevel% equ 0 (
    echo.
    echo ================================================================================
    echo [SUCCESS] Code pushed to GitHub!
    echo ================================================================================
    echo.
    echo Repository URL:
    echo https://github.com/seunghochoi2018/explosive-compound-trading
    echo.
    echo Open in browser?
    start https://github.com/seunghochoi2018/explosive-compound-trading
) else (
    echo.
    echo [ERROR] Push failed
    echo.
    echo Possible reasons:
    echo 1. Repository not created on GitHub
    echo 2. Wrong repository name
    echo 3. Authentication issue
    echo.
    echo Please check:
    echo 1. Repository exists: https://github.com/seunghochoi2018/explosive-compound-trading
    echo 2. You are logged in to GitHub
    echo.
    echo To try again: git push -u origin master
)

echo.
pause
