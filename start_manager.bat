@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "C:\Users\user\Documents\코드5"
start /min "" "C:\Users\user\PycharmProjects\PythonProject\.venv\Scripts\pythonw.exe" "C:\Users\user\Documents\코드5\unified_trader_manager.py"
echo 통합 매니저 시작됨
timeout /t 5 /nobreak >nul
python check_status.py
