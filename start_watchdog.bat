@echo off
REM 감시견 자동 시작 스크립트
cd /d "C:\Users\user\Documents\코드5"
set PYTHONIOENCODING=utf-8
start /min "" "C:\Users\user\PycharmProjects\PythonProject\.venv\Scripts\pythonw.exe" watchdog.py
