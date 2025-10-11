@echo off
set PYTHONIOENCODING=utf-8
cd /d "C:\Users\user\Documents\코드5"
start /min "" "C:\Users\user\PycharmProjects\PythonProject\.venv\Scripts\pythonw.exe" "unified_trader_manager.py"
echo Manager started with UTF-8 encoding
timeout /t 3 >nul
python check_status.py
