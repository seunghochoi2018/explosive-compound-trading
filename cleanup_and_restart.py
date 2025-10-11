#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합매니저 정리 및 재시작
"""
import os
import sys
import time
import psutil
import subprocess

def kill_all_related_processes():
    """통합매니저 및 관련 프로세스 모두 종료"""
    killed_count = 0

    # unified_trader_manager 프로세스 찾기
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['cmdline']:
                cmdline = ' '.join(proc.info['cmdline'])
                if 'unified_trader_manager' in cmdline or 'llm_eth_trader' in cmdline or 'kis_llm_trader' in cmdline:
                    print(f"[KILL] PID {proc.info['pid']}: {cmdline[:80]}")
                    proc.kill()
                    killed_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    print(f"\n총 {killed_count}개 프로세스 종료")
    return killed_count

def cleanup_pid_file():
    """PID 파일 정리"""
    pid_file = r"C:\Users\user\Documents\코드5\.unified_trader_manager.pid"
    if os.path.exists(pid_file):
        os.remove(pid_file)
        print(f"[CLEAN] PID 파일 삭제: {pid_file}")

def start_unified_manager():
    """통합매니저 시작 (PYTHONIOENCODING 설정)"""
    python_path = r"C:\Users\user\PycharmProjects\PythonProject\.venv\Scripts\python.exe"
    script_path = r"C:\Users\user\Documents\코드5\unified_trader_manager.py"

    # 환경변수 설정
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'

    print(f"\n[START] 통합매니저 시작...")
    proc = subprocess.Popen(
        [python_path, script_path],
        cwd=os.path.dirname(script_path),
        env=env,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
    )

    print(f"[OK] 통합매니저 시작 완료 (PID: {proc.pid})")
    return proc.pid

if __name__ == "__main__":
    print("=" * 80)
    print("통합매니저 정리 및 재시작")
    print("=" * 80)

    # 1. 모든 관련 프로세스 종료
    killed = kill_all_related_processes()

    if killed > 0:
        print("\n[WAIT] 3초 대기 (프로세스 종료 확인)...")
        time.sleep(3)

    # 2. PID 파일 정리
    cleanup_pid_file()

    # 3. 통합매니저 재시작
    new_pid = start_unified_manager()

    print("\n[WAIT] 5초 대기 (초기화 확인)...")
    time.sleep(5)

    # 4. 시작 확인
    if psutil.pid_exists(new_pid):
        print(f"\n[SUCCESS] 통합매니저 정상 실행 중 (PID: {new_pid})")
    else:
        print(f"\n[ERROR] 통합매니저 시작 실패")

    print("=" * 80)
