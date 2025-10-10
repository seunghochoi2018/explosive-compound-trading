@echo off
chcp 65001 >nul
echo ================================================================================
echo Quick GitHub Push
echo ================================================================================
echo.

cd /d "C:\Users\user\Documents\코드5"

echo [1] Remove old remote...
git remote remove origin 2>nul

echo [2] Create new repository...
gh repo create explosive-compound-trading --public --description "Explosive Compound Trading Bot - ETH +4654%%, KIS +2634%%" --source=. --remote=origin

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Repository creation failed
    echo.
    echo Trying manual setup...
    echo.

    REM Get username
    for /f "tokens=*" %%i in ('gh api user -q .login') do set GH_USER=%%i

    echo Your GitHub username: %GH_USER%
    echo.
    echo Please create repository manually:
    echo 1. Go to: https://github.com/new
    echo 2. Repository name: explosive-compound-trading
    echo 3. Description: Explosive Compound Trading Bot - ETH +4654%%, KIS +2634%%
    echo 4. Public
    echo 5. Do NOT initialize with README
    echo 6. Create repository
    echo.
    echo Then run this command:
    echo git remote add origin https://github.com/%GH_USER%/explosive-compound-trading.git
    echo git push -u origin master
    echo.
    pause
    exit /b 1
)

echo [3] Push to GitHub...
git push -u origin master

if %errorlevel% equ 0 (
    echo.
    echo ================================================================================
    echo [SUCCESS] Pushed to GitHub!
    echo ================================================================================
    echo.

    REM Get repository URL
    for /f "tokens=*" %%i in ('gh repo view --json url -q .url') do (
        echo Repository: %%i
    )
    echo.
) else (
    echo.
    echo [ERROR] Push failed
    echo.
    echo Manual push:
    echo   git push -u origin master
    echo.
)

pause
