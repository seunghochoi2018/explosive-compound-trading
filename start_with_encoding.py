#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import subprocess

# UTF-8 encoding for all output
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

python_path = r"C:\Users\user\PycharmProjects\PythonProject\.venv\Scripts\python.exe"
script_path = r"C:\Users\user\Documents\코드5\unified_trader_manager.py"

# Start with proper encoding
env = os.environ.copy()
env['PYTHONIOENCODING'] = 'utf-8'

print("[START] Starting unified manager with UTF-8 encoding...")

proc = subprocess.Popen(
    [python_path, script_path],
    cwd=os.path.dirname(script_path),
    env=env,
    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
)

print(f"[OK] Process started with PID: {proc.pid}")
print("[INFO] Waiting 10 seconds to verify startup...")

import time
time.sleep(10)

# Check if still running
import psutil
if psutil.pid_exists(proc.pid):
    try:
        p = psutil.Process(proc.pid)
        print(f"[SUCCESS] Manager is running (PID: {proc.pid}, Status: {p.status()})")
    except:
        print(f"[WARNING] PID exists but cannot access")
else:
    print(f"[ERROR] Process died (PID: {proc.pid} no longer exists)")

# Check log
log_path = r"C:\Users\user\Documents\코드5\unified_output.log"
if os.path.exists(log_path) and os.path.getsize(log_path) > 0:
    print("\n[LOG] Last 20 lines of log:")
    with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
        for line in lines[-20:]:
            print(line.rstrip())
else:
    print("\n[WARNING] No log output generated")
