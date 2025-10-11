@echo off
REM 통합매니저 자동 시작 스크립트
cd /d "C:\Users\user\Documents\코드5"
set PYTHONIOENCODING=utf-8
start /min "" "C:\Users\user\PycharmProjects\PythonProject\.venv\Scripts\pythonw.exe" unified_trader_manager.py
