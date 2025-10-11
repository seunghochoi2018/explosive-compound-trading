#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""통합 매니저 재시작"""
import os
import sys
import psutil
import time

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("=" * 60)
print("통합 매니저 재시작")
print("=" * 60)
print()

# 1. 기존 프로세스 종료
pid_file = r"C:\Users\user\Documents\코드5\.unified_trader_manager.pid"

if os.path.exists(pid_file):
    with open(pid_file, 'r') as f:
        pid = int(f.read().strip())

    print(f"[1/3] 기존 프로세스 종료 중 (PID: {pid})...")

    if psutil.pid_exists(pid):
        try:
            proc = psutil.Process(pid)
            # 자식 프로세스도 모두 종료
            children = proc.children(recursive=True)
            for child in children:
                try:
                    print(f"  자식 프로세스 종료: PID {child.pid}")
                    child.terminate()
                except:
                    pass

            # 메인 프로세스 종료
            proc.terminate()
            proc.wait(timeout=10)
            print(f"  [OK] 프로세스 종료 완료")
        except Exception as e:
            print(f"  [WARN] 종료 실패: {e}")
    else:
        print(f"  [INFO] PID {pid}는 이미 종료됨")
else:
    print("[1/3] PID 파일 없음, 새로 시작")

print()

# 2. 잠시 대기 (포트 정리)
print("[2/3] 포트 정리 대기 중...")
time.sleep(3)
print("  [OK] 준비 완료")
print()

# 3. 새 프로세스 시작
print("[3/3] 통합 매니저 시작 중...")
os.chdir(r"C:\Users\user\Documents\코드5")

import subprocess
subprocess.Popen(
    ["python", "unified_trader_manager.py"],
    creationflags=subprocess.CREATE_NEW_CONSOLE
)

time.sleep(2)

# 확인
if os.path.exists(pid_file):
    with open(pid_file, 'r') as f:
        new_pid = int(f.read().strip())
    print(f"  [OK] 새 PID: {new_pid}")
else:
    print("  [WARN] PID 파일 생성 대기 중...")

print()
print("=" * 60)
print("재시작 완료!")
print("=" * 60)
