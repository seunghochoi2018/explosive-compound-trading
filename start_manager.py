#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""통합 매니저 간단 시작 스크립트"""
import subprocess
import sys
import os

manager_script = r"C:\Users\user\Documents\코드5\unified_trader_manager.py"
python_path = r"C:\Users\user\PycharmProjects\PythonProject\.venv\Scripts\pythonw.exe"
log_file = r"C:\Users\user\Documents\코드5\manager_startup.log"

print(f"Starting unified trader manager...")
print(f"Manager: {manager_script}")
print(f"Python: {python_path}")
print(f"Log: {log_file}")

# Start manager in background
proc = subprocess.Popen(
    [python_path, manager_script],
    cwd=os.path.dirname(manager_script),
    stdout=open(log_file, 'w', encoding='utf-8'),
    stderr=subprocess.STDOUT
)

print(f"\nManager started with PID: {proc.pid}")
print(f"Check log file: {log_file}")
print(f"Or use check_manager_status.py to verify")
