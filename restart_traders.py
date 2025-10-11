#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""트레이더 재시작 스크립트"""
import os
import subprocess
import time
import psutil

print("=" * 80)
print("트레이더 재시작 스크립트")
print("=" * 80)

# 1. 모든 Python 프로세스 종료
print("\n[1] 기존 Python 프로세스 종료 중...")
killed_count = 0
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if proc.info['name'] and 'python' in proc.info['name'].lower():
            cmdline = proc.info['cmdline']
            if cmdline and any('trader' in str(cmd).lower() for cmd in cmdline):
                print(f"  종료: PID {proc.info['pid']} - {' '.join(cmdline[:2])}")
                proc.kill()
                killed_count += 1
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

print(f"  종료된 프로세스: {killed_count}개")
time.sleep(2)

# 2. PID 파일 정리
print("\n[2] PID 파일 정리 중...")
pid_files = [
    '.unified_trader_manager.pid',
    'eth_trader.pid',
    'kis_trader.pid'
]
for pid_file in pid_files:
    if os.path.exists(pid_file):
        os.remove(pid_file)
        print(f"  삭제: {pid_file}")

# 3. Ollama 프로세스 확인
print("\n[3] Ollama 프로세스 확인 중...")
ollama_count = 0
for proc in psutil.process_iter(['pid', 'name']):
    try:
        if proc.info['name'] and 'ollama' in proc.info['name'].lower():
            print(f"  실행 중: PID {proc.info['pid']} - {proc.info['name']}")
            ollama_count += 1
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

if ollama_count == 0:
    print("  ⚠️  Ollama 프로세스 없음 - 수동으로 시작 필요")
else:
    print(f"  ✅ Ollama 프로세스: {ollama_count}개")

# 4. 통합매니저 시작
print("\n[4] 통합 트레이더 매니저 시작 중...")
print("  (이 프로세스는 백그라운드에서 실행됩니다)")

# 백그라운드로 시작
venv_python = r"C:\Users\user\PycharmProjects\PythonProject\.venv\Scripts\pythonw.exe"
script_path = "unified_trader_manager.py"

# pythonw.exe로 백그라운드 실행
subprocess.Popen([venv_python, script_path],
                 cwd=r"C:\Users\user\Documents\코드5",
                 creationflags=subprocess.CREATE_NO_WINDOW)

print("  ✅ 통합매니저 시작 완료")
print("\n" + "=" * 80)
print("재시작 완료!")
print("=" * 80)
print("\n💡 통합매니저가 ETH 및 KIS 트레이더를 자동으로 시작합니다")
print("💡 로그는 각 트레이더의 콘솔 출력으로 확인할 수 있습니다")
