@echo off
chcp 65001 > nul
echo ========================================
echo 통합 트레이딩 시스템 시작
echo ========================================
echo.

REM 기존 프로세스 정리
echo [1단계] 기존 프로세스 정리 중...
"C:\Users\user\PycharmProjects\PythonProject\.venv\Scripts\python.exe" "C:\Users\user\Documents\코드5\force_kill.py"
timeout /t 2 /nobreak > nul

REM 캐시 정리
echo [2단계] 캐시 정리 중...
cd "C:\Users\user\Documents\코드3"
if exist __pycache__ rd /s /q __pycache__ 2>nul
del /s /q *.pyc 2>nul
cd "C:\Users\user\Documents\코드5"

echo [3단계] 워치독 시작 중...
start /min "Watchdog" "C:\Users\user\PycharmProjects\PythonProject\.venv\Scripts\python.exe" "C:\Users\user\Documents\코드5\watchdog.py"
timeout /t 3 /nobreak > nul

echo.
echo ========================================
echo ✅ 시스템 시작 완료!
echo ========================================
echo.
echo [실행 중인 시스템]
echo - 워치독: 통합매니저 자동 감시 및 재시작
echo - 통합매니저: ETH + KIS 트레이더 관리
echo.
echo [확인 방법]
echo - 프로세스: tasklist ^| findstr python
echo - PID 확인: type C:\Users\user\Documents\코드5\.unified_trader_manager.pid
echo.
pause
