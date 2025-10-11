#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import psutil
import os

print("=" * 80)
print("통합 매니저 상태 확인")
print("=" * 80)

# 1. Python 프로세스 확인
python_procs = []
for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
    try:
        if proc.info['name'] and 'python' in proc.info['name'].lower():
            if proc.info['cmdline']:
                cmdline = ' '.join(proc.info['cmdline'])
                if any(keyword in cmdline for keyword in ['unified_trader_manager', 'watchdog', 'llm_eth_trader', 'kis_llm_trader']):
                    python_procs.append(proc.info)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        continue

print(f"\n[Python 프로세스] {len(python_procs)}개 실행 중\n")
for p in python_procs:
    cmdline = ' '.join(p['cmdline'])
    if 'unified_trader_manager' in cmdline:
        print(f"  [MANAGER] PID {p['pid']}: unified_trader_manager.py")
    elif 'watchdog' in cmdline:
        print(f"  [WATCHDOG] PID {p['pid']}: watchdog.py")
    elif 'llm_eth_trader' in cmdline:
        print(f"  [ETH] PID {p['pid']}: llm_eth_trader_v3_explosive.py")
    elif 'kis_llm_trader' in cmdline:
        print(f"  [KIS] PID {p['pid']}: kis_llm_trader_v2_explosive.py")

# 2. PID 파일 확인
pid_file = r"C:\Users\user\Documents\코드5\.unified_trader_manager.pid"
if os.path.exists(pid_file):
    with open(pid_file, 'r') as f:
        pid = int(f.read().strip())
    if psutil.pid_exists(pid):
        print(f"\n[PID 파일] PID {pid} - 프로세스 실행 중")
    else:
        print(f"\n[PID 파일] PID {pid} - 프로세스 없음 (정리 필요)")
else:
    print(f"\n[PID 파일] 없음")

# 3. Ollama 프로세스 확인
ollama_procs = []
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if proc.info['name'] and 'ollama' in proc.info['name'].lower():
            ollama_procs.append(proc.info)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        continue

print(f"\n[Ollama 프로세스] {len(ollama_procs)}개 실행 중")

print("=" * 80)
