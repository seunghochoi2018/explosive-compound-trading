#!/usr/bin/env python3
# Kill all Python processes except current one
import os
import psutil

my_pid = os.getpid()
killed_count = 0

for proc in psutil.process_iter(['pid', 'name']):
    try:
        if proc.info['pid'] != my_pid and 'python' in proc.info['name'].lower():
            proc.kill()
            killed_count += 1
            print(f"Killed PID {proc.info['pid']}: {proc.info['name']}")
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

print(f"\nTotal killed: {killed_count} Python processes")
