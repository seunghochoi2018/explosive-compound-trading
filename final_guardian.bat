@echo off
setlocal enabledelayedexpansion

title Final Guardian - 무조건 살려놓기

set PYTHON=C:\Users\user\PycharmProjects\PythonProject\.venv\Scripts\python.exe
set ETH=C:\Users\user\Documents\코드3\llm_eth_trader_v4_3tier.py
set KIS=C:\Users\user\Documents\코드4\kis_llm_trader_v2_explosive.py
set MGR=C:\Users\user\Documents\코드5\unified_trader_manager 연습.py

echo ========================================
echo   Final Guardian - 무조건 살림
echo ========================================
echo.

:LOOP
    echo [%TIME%] 체크...

    REM Ollama - curl로 직접 체크
    curl -s --max-time 1 http://127.0.0.1:11434/api/tags >nul 2>&1
    if errorlevel 1 (
        echo [%TIME%] [X] Ollama 죽음! 재시작
        taskkill /F /IM ollama.exe 2>nul
        start "" /MIN ollama serve
        timeout /t 3 /nobreak >nul
    ) else (
        echo [%TIME%] [O] Ollama OK
    )

    REM ETH - wmic로 cmdline 체크
    wmic process where "name='python.exe'" get commandline 2>nul | findstr "llm_eth_trader_v4_3tier" >nul
    if errorlevel 1 (
        echo [%TIME%] [X] ETH 죽음! 재시작
        "%PYTHON%" "%ETH%" >nul 2>&1 &
    ) else (
        echo [%TIME%] [O] ETH OK
    )

    REM KIS
    wmic process where "name='python.exe'" get commandline 2>nul | findstr "kis_llm_trader_v2_explosive" >nul
    if errorlevel 1 (
        echo [%TIME%] [X] KIS 죽음! 재시작
        "%PYTHON%" "%KIS%" >nul 2>&1 &
    ) else (
        echo [%TIME%] [O] KIS OK
    )

    REM Manager
    wmic process where "name='python.exe'" get commandline 2>nul | findstr "unified_trader_manager" >nul
    if errorlevel 1 (
        echo [%TIME%] [X] MGR 죽음! 재시작
        "%PYTHON%" "%MGR%" >nul 2>&1 &
    ) else (
        echo [%TIME%] [O] MGR OK
    )

    echo [%TIME%] 15초 대기...
    echo.
    timeout /t 15 /nobreak >nul
    goto LOOP
