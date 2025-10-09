@echo off
chcp 65001 >nul
echo ================================================================================
echo GitHub CLI 자동 설치
echo ================================================================================
echo.

REM 이미 설치되어 있는지 확인
where gh >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] GitHub CLI가 이미 설치되어 있습니다.
    gh --version
    echo.
    pause
    exit /b 0
)

echo [설치] GitHub CLI 설치 중...
echo.

REM winget 사용 (Windows 10/11)
winget install --id GitHub.cli -e --accept-source-agreements --accept-package-agreements

if %errorlevel% equ 0 (
    echo.
    echo ================================================================================
    echo [완료] GitHub CLI 설치 완료!
    echo ================================================================================
    echo.
    echo 설치된 버전:
    gh --version
    echo.
    echo 다음 단계:
    echo 1. AUTO_GITHUB_PUSH.bat 실행
    echo 2. GitHub 계정으로 로그인
    echo 3. 자동으로 푸시됩니다!
    echo.
) else (
    echo.
    echo [ERROR] 자동 설치 실패
    echo.
    echo 수동 설치 방법:
    echo.
    echo 1. 브라우저에서 https://cli.github.com/ 접속
    echo 2. "Download for Windows" 클릭
    echo 3. 설치 프로그램 실행
    echo 4. 설치 후 AUTO_GITHUB_PUSH.bat 실행
    echo.
)

pause
