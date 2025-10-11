#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import psutil
import sys

killed = []
for p in psutil.process_iter(['name', 'cmdline', 'pid']):
    try:
        if p.info['name'] in ['python.exe', 'pythonw.exe']:
            cmdline = ' '.join(p.info.get('cmdline', []))
            if any(x in cmdline for x in ['unified_trader', 'llm_eth', 'kis_llm']):
                print(f"Killing PID {p.info['pid']}: {p.info['name']}")
                p.kill()
                killed.append(p.info['pid'])
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

print(f"\nKilled {len(killed)} processes: {killed}")
