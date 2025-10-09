@echo off
chcp 65001 >nul
echo ================================================================================
echo GitHub Auto Push Script
echo ================================================================================
echo.

cd /d "C:\Users\user\Documents\코드5"

REM GitHub CLI 설치 확인
where gh >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] GitHub CLI가 설치되지 않았습니다.
    echo.
    echo GitHub CLI 자동 설치 중...
    echo.

    REM winget으로 설치 시도
    winget install --id GitHub.cli -e --silent

    if %errorlevel% neq 0 (
        echo [ERROR] 자동 설치 실패
        echo.
        echo 수동 설치 방법:
        echo 1. https://cli.github.com/ 접속
        echo 2. Download for Windows 클릭
        echo 3. 설치 후 이 스크립트 다시 실행
        pause
        exit /b 1
    )

    echo [OK] GitHub CLI 설치 완료
    echo.
)

REM GitHub 인증 확인
gh auth status >nul 2>&1
if %errorlevel% neq 0 (
    echo [인증] GitHub 로그인 필요
    echo.
    echo 브라우저가 열립니다. GitHub 계정으로 로그인하세요.
    echo.
    pause

    gh auth login

    if %errorlevel% neq 0 (
        echo [ERROR] 인증 실패
        pause
        exit /b 1
    )
)

echo [OK] GitHub 인증 완료
echo.

REM 저장소 생성 (이미 있으면 무시)
echo [저장소] 생성 중...
gh repo create explosive-compound-trading --public --description "백테스트 기반 복리 폭발 자동매매 - ETH +4654%%, KIS +2634%%" --source=. --push 2>nul

if %errorlevel% equ 0 (
    echo [OK] 저장소 생성 및 푸시 완료!
    echo.
    echo GitHub 저장소: https://github.com/YOUR_USERNAME/explosive-compound-trading
    echo.
) else (
    REM 이미 저장소가 있는 경우 푸시만
    echo [푸시] 기존 저장소에 푸시 중...

    REM remote 확인
    git remote get-url origin >nul 2>&1
    if %errorlevel% neq 0 (
        echo [설정] remote 추가 중...
        for /f "tokens=*" %%i in ('gh repo view --json url -q .url') do set REPO_URL=%%i
        git remote add origin !REPO_URL!
    )

    REM 푸시
    git push -u origin master

    if %errorlevel% equ 0 (
        echo [OK] 푸시 완료!
    ) else (
        echo [ERROR] 푸시 실패
        pause
        exit /b 1
    )
)

echo.
echo ================================================================================
echo [완료] GitHub에 성공적으로 저장되었습니다!
echo ================================================================================
echo.

REM 저장소 URL 출력
for /f "tokens=*" %%i in ('gh repo view --json url -q .url') do (
    echo 저장소 주소: %%i
)

echo.
pause
