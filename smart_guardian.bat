@echo off
REM 똑똑한 감시견 - 프로세스 직접 체크
setlocal enabledelayedexpansion

title Smart Guardian

set PYTHON=C:\Users\user\PycharmProjects\PythonProject\.venv\Scripts\python.exe
set ETH_SCRIPT=C:\Users\user\Documents\코드3\llm_eth_trader_v4_3tier.py
set KIS_SCRIPT=C:\Users\user\Documents\코드4\kis_llm_trader_v2_explosive.py
set MGR_SCRIPT=C:\Users\user\Documents\코드5\unified_trader_manager 연습.py

echo ========== Smart Guardian 시작 ==========
echo.

:LOOP
    echo [%TIME%] 체크 시작...

    REM Ollama 체크
    netstat -ano | findstr ":11434.*LISTENING" >nul
    if errorlevel 1 (
        echo [%TIME%] [CRITICAL] Ollama 죽음! 재시작...
        taskkill /F /IM ollama.exe 2>nul
        start "" /MIN ollama serve
        timeout /t 3 /nobreak >nul
    ) else (
        echo [%TIME%] [OK] Ollama 정상
    )

    REM ETH Trader 체크 (실제 스크립트 경로로 확인)
    tasklist /V 2>nul | findstr "python.exe" | findstr "llm_eth_trader" >nul
    if errorlevel 1 (
        echo [%TIME%] [ERROR] ETH 죽음! 시작 시도...
        start "ETH-Trader" /MIN "%PYTHON%" "%ETH_SCRIPT%"
        echo [%TIME%] ETH 시작 명령 실행됨
        timeout /t 2 /nobreak >nul
    ) else (
        echo [%TIME%] [OK] ETH 정상
    )

    REM KIS Trader 체크
    tasklist /V 2>nul | findstr "python.exe" | findstr "kis_llm" >nul
    if errorlevel 1 (
        echo [%TIME%] [ERROR] KIS 죽음! 시작 시도...
        start "KIS-Trader" /MIN "%PYTHON%" "%KIS_SCRIPT%"
        echo [%TIME%] KIS 시작 명령 실행됨
        timeout /t 2 /nobreak >nul
    ) else (
        echo [%TIME%] [OK] KIS 정상
    )

    REM Manager 체크
    tasklist /V 2>nul | findstr "python.exe" | findstr "unified_trader" >nul
    if errorlevel 1 (
        echo [%TIME%] [ERROR] Manager 죽음! 시작 시도...
        start "Manager" /MIN "%PYTHON%" "%MGR_SCRIPT%"
        echo [%TIME%] Manager 시작 명령 실행됨
        timeout /t 2 /nobreak >nul
    ) else (
        echo [%TIME%] [OK] Manager 정상
    )

    echo [%TIME%] 다음 체크: 15초 후
    echo.
    timeout /t 15 /nobreak >nul
    goto LOOP
