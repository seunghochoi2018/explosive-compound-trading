@echo off
REM ==================================================
REM 영구 감시 스크립트 - 30초마다 확인
REM ==================================================
REM 사용자 요구: "시작시 뿐만 아니라 모니터링해서 항상 실행될 수 있게 문제없이"
REM ==================================================

title 트레이더 감시견 - 30초마다 확인

echo.
echo ======================================================================
echo   트레이더 감시견 시작
echo ======================================================================
echo   - ETH Trader (llm_eth_trader_v4_3tier.py)
echo   - KIS Trader (kis_llm_trader_v2_explosive.py)
echo   - Manager Practice (unified_trader_manager 연습.py)
echo ======================================================================
echo   30초마다 프로세스 확인 후 죽으면 자동 재시작
echo ======================================================================
echo.

set PYTHON=C:\Users\user\PycharmProjects\PythonProject\.venv\Scripts\python.exe
set ETH_SCRIPT=C:\Users\user\Documents\코드3\llm_eth_trader_v4_3tier.py
set KIS_SCRIPT=C:\Users\user\Documents\코드4\kis_llm_trader_v2_explosive.py
set MGR_SCRIPT=C:\Users\user\Documents\코드5\unified_trader_manager 연습.py

:LOOP
    echo [%TIME%] 프로세스 확인 중...

    REM ETH Trader 확인
    tasklist /FI "WINDOWTITLE eq ETH Trader*" 2>NUL | find "python.exe" >NUL
    if errorlevel 1 (
        echo [%TIME%] [ERROR] ETH Trader 죽음! 재시작 중...
        start "ETH Trader" /MIN "%PYTHON%" "%ETH_SCRIPT%"
    ) else (
        echo [%TIME%] [OK] ETH Trader 정상
    )

    REM KIS Trader 확인
    tasklist /FI "WINDOWTITLE eq KIS Trader*" 2>NUL | find "python.exe" >NUL
    if errorlevel 1 (
        echo [%TIME%] [ERROR] KIS Trader 죽음! 재시작 중...
        start "KIS Trader" /MIN "%PYTHON%" "%KIS_SCRIPT%"
    ) else (
        echo [%TIME%] [OK] KIS Trader 정상
    )

    REM Manager Practice 확인
    tasklist /FI "WINDOWTITLE eq Manager Practice*" 2>NUL | find "python.exe" >NUL
    if errorlevel 1 (
        echo [%TIME%] [ERROR] Manager Practice 죽음! 재시작 중...
        start "Manager Practice" /MIN "%PYTHON%" "%MGR_SCRIPT%"
    ) else (
        echo [%TIME%] [OK] Manager Practice 정상
    )

    echo [%TIME%] 다음 확인까지 30초 대기...
    echo.
    timeout /t 30 /nobreak >nul

goto LOOP
