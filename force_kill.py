#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""강제 종료"""
import psutil
import sys

print("Killing trader processes...")
killed = []

for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if proc.info['name'] in ['python.exe', 'pythonw.exe']:
            cmdline = ' '.join(proc.info.get('cmdline', []))
            if any(x in cmdline for x in ['unified_trader', 'llm_eth', 'kis_llm']):
                print(f"  Killing PID {proc.info['pid']}: {proc.info['name']}")
                proc.kill()
                killed.append(proc.info['pid'])
    except:
        pass

if killed:
    print(f"Killed {len(killed)} processes: {killed}")
else:
    print("No trader processes found")
