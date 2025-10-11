#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""통합 매니저 상태 확인"""
import os
import psutil
from datetime import datetime

pid_file = r"C:\Users\user\Documents\코드5\.unified_trader_manager.pid"

print(f"[{datetime.now().strftime('%H:%M:%S')}] 통합 매니저 상태 확인\n")

# PID 파일 확인
if os.path.exists(pid_file):
    with open(pid_file, 'r') as f:
        pid = int(f.read().strip())

    print(f"[PID File] {pid}")

    # 프로세스 확인
    if psutil.pid_exists(pid):
        try:
            proc = psutil.Process(pid)
            cmdline = ' '.join(proc.cmdline())

            print(f"[Status] RUNNING")
            print(f"[Command] {cmdline}")
            print(f"[Memory] {proc.memory_info().rss / 1024 / 1024:.1f} MB")

            # 자식 프로세스 확인
            children = proc.children(recursive=True)
            print(f"\n[Children] {len(children)} processes")
            for child in children:
                try:
                    child_cmd = ' '.join(child.cmdline())
                    if 'llm_eth' in child_cmd or 'kis_llm' in child_cmd:
                        print(f"  - PID {child.pid}: {os.path.basename(child_cmd)}")
                except:
                    pass

        except psutil.NoSuchProcess:
            print(f"[Status] NOT RUNNING (PID {pid} not found)")
    else:
        print(f"[Status] NOT RUNNING (PID {pid} not found)")
else:
    print("[PID File] Not found")
    print("[Status] NOT RUNNING")

    # 수동으로 프로세스 찾기
    print("\n[Search] Looking for trader processes...")
    found = False
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['cmdline']:
                cmdline = ' '.join(proc.info['cmdline'])
                if 'unified_trader_manager' in cmdline or 'llm_eth' in cmdline or 'kis_llm' in cmdline:
                    print(f"  Found: PID {proc.info['pid']} - {os.path.basename(cmdline)}")
                    found = True
        except:
            pass

    if not found:
        print("  No trader processes found")
