#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ollama 프로세스 확인"""
import psutil

print("Ollama processes:")
found = False
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if proc.info['name'] and 'ollama' in proc.info['name'].lower():
            print(f"  PID {proc.info['pid']}: {proc.info['name']}")
            if proc.info['cmdline']:
                print(f"    Command: {' '.join(proc.info['cmdline'])}")
            found = True
    except:
        pass

if not found:
    print("  No ollama processes found")
