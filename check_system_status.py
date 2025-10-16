#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""시스템 상태 확인"""
import psutil
import time
from pathlib import Path
from datetime import datetime
import sys
import io

# UTF-8 인코딩 강제
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 파일 경로
PID_FILE = Path(r"C:\Users\user\Documents\코드5\.unified_trader_manager.pid")
HEARTBEAT_FILE = Path(r"C:\Users\user\Documents\코드5\.manager_heartbeat.txt")

print("="*70)
print("통합 트레이더 시스템 상태 확인")
print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*70)

# 1. PID 파일 확인
if PID_FILE.exists():
    with open(PID_FILE, 'r') as f:
        pid = int(f.read().strip())
    print(f"\n[통합 매니저]")
    print(f"  PID: {pid}")

    if psutil.pid_exists(pid):
        proc = psutil.Process(pid)
        print(f"  상태: 실행 중 [OK]")
        print(f"  메모리: {proc.memory_info().rss / 1024 / 1024:.1f} MB")
        print(f"  CPU: {proc.cpu_percent(interval=1):.1f}%")
        print(f"  실행 시간: {time.time() - proc.create_time():.0f}초")
    else:
        print(f"  상태: 종료됨 [X]")
else:
    print(f"\n[통합 매니저]")
    print(f"  상태: PID 파일 없음 [X]")

# 2. Heartbeat 확인
if HEARTBEAT_FILE.exists():
    heartbeat_age = time.time() - HEARTBEAT_FILE.stat().st_mtime
    with open(HEARTBEAT_FILE, 'r') as f:
        heartbeat_time = float(f.read().strip())

    print(f"\n[Heartbeat]")
    print(f"  마지막 업데이트: {heartbeat_age:.1f}초 전")

    if heartbeat_age < 60:
        print(f"  상태: 정상 [OK]")
    else:
        print(f"  상태: 타임아웃 [X]")
else:
    print(f"\n[Heartbeat]")
    print(f"  상태: 파일 없음 [X]")

# 3. Python 프로세스 전체 확인
print(f"\n[Python 프로세스]")
python_procs = []
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if 'python' in proc.info['name'].lower():
            cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
            if 'unified_trader_manager' in cmdline:
                python_procs.append((proc.info['pid'], cmdline))
    except:
        pass

if python_procs:
    print(f"  통합 매니저 관련 프로세스: {len(python_procs)}개")
    for pid, cmd in python_procs:
        print(f"    - PID {pid}: {cmd[:80]}...")
else:
    print(f"  통합 매니저 관련 프로세스 없음")

print("\n" + "="*70)
