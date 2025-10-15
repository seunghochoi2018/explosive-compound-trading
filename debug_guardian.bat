@echo off
setlocal enabledelayedexpansion

title Debug Guardian - 원인 분석 포함

set PYTHON=C:\Users\user\PycharmProjects\PythonProject\.venv\Scripts\python.exe
set ETH=C:\Users\user\Documents\코드3\llm_eth_trader_v4_3tier.py
set KIS=C:\Users\user\Documents\코드4\kis_llm_trader_v2_explosive.py
set MGR=C:\Users\user\Documents\코드5\unified_trader_manager 연습.py

echo ========================================
echo   Debug Guardian with Full Logging
echo ========================================
echo   로그파일: guardian_debug.log
echo ========================================
echo.

:LOOP
    echo ==================== [%TIME%] ==================== >> guardian_debug.log
    echo [%TIME%] 체크 시작

    REM === 1. Ollama 체크 (3단계) ===
    echo [OLLAMA] 체크 시작... >> guardian_debug.log

    REM 1-1. 프로세스 존재
    tasklist | findstr "ollama.exe" >nul
    if errorlevel 1 (
        echo [OLLAMA] FAIL: 프로세스 없음 >> guardian_debug.log
        goto RESTART_OLLAMA
    ) else (
        echo [OLLAMA] OK: 프로세스 존재 >> guardian_debug.log
    )

    REM 1-2. API 응답
    curl -s --max-time 2 http://127.0.0.1:11434/api/tags >nul 2>&1
    if errorlevel 1 (
        echo [OLLAMA] FAIL: API 응답 없음 (포트 11434 죽음) >> guardian_debug.log
        goto RESTART_OLLAMA
    ) else (
        echo [OLLAMA] OK: API 정상 응답 >> guardian_debug.log
        echo [%TIME%] [O] Ollama OK
    )
    goto OLLAMA_OK

:RESTART_OLLAMA
    echo [%TIME%] [X] Ollama 죽음! (로그 확인: guardian_debug.log)
    echo [OLLAMA] 재시작 시작... >> guardian_debug.log
    taskkill /F /IM ollama.exe 2>nul
    timeout /t 1 /nobreak >nul
    start "" /MIN ollama serve
    echo [OLLAMA] start 명령 실행됨 >> guardian_debug.log
    timeout /t 3 /nobreak >nul
    echo [OLLAMA] 재시작 완료 >> guardian_debug.log

:OLLAMA_OK

    REM === 2. ETH Trader 체크 ===
    echo [ETH] 체크 시작... >> guardian_debug.log
    wmic process where "name='python.exe'" get commandline 2>nul | findstr "llm_eth_trader_v4_3tier" >nul
    if errorlevel 1 (
        echo [ETH] FAIL: 프로세스 없음 >> guardian_debug.log
        echo [%TIME%] [X] ETH 죽음! 재시작
        echo [ETH] 재시작 시작... >> guardian_debug.log
        "%PYTHON%" "%ETH%" >nul 2>&1 &
        echo [ETH] 백그라운드 실행됨 >> guardian_debug.log
    ) else (
        echo [ETH] OK: 실행 중 >> guardian_debug.log
        echo [%TIME%] [O] ETH OK
    )

    REM === 3. KIS Trader 체크 ===
    echo [KIS] 체크 시작... >> guardian_debug.log
    wmic process where "name='python.exe'" get commandline 2>nul | findstr "kis_llm_trader_v2_explosive" >nul
    if errorlevel 1 (
        echo [KIS] FAIL: 프로세스 없음 >> guardian_debug.log
        echo [%TIME%] [X] KIS 죽음! 재시작
        echo [KIS] 재시작 시작... >> guardian_debug.log
        "%PYTHON%" "%KIS%" >nul 2>&1 &
        echo [KIS] 백그라운드 실행됨 >> guardian_debug.log
    ) else (
        echo [KIS] OK: 실행 중 >> guardian_debug.log
        echo [%TIME%] [O] KIS OK
    )

    REM === 4. Manager 체크 ===
    echo [MGR] 체크 시작... >> guardian_debug.log
    wmic process where "name='python.exe'" get commandline 2>nul | findstr "unified_trader_manager" >nul
    if errorlevel 1 (
        echo [MGR] FAIL: 프로세스 없음 >> guardian_debug.log
        echo [%TIME%] [X] MGR 죽음! 재시작
        echo [MGR] 재시작 시작... >> guardian_debug.log
        "%PYTHON%" "%MGR%" >nul 2>&1 &
        echo [MGR] 백그라운드 실행됨 >> guardian_debug.log
    ) else (
        echo [MGR] OK: 실행 중 >> guardian_debug.log
        echo [%TIME%] [O] MGR OK
    )

    echo [%TIME%] 다음 체크: 15초 후 (로그: guardian_debug.log)
    echo. >> guardian_debug.log
    timeout /t 15 /nobreak >nul
    goto LOOP
