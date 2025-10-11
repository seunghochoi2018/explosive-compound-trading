#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ollama 수호자 (Ollama Guardian)
- 실시간 Ollama 프로세스 모니터링 (10초마다)
- 불필요한 프로세스 자동 정리
- 허가된 포트만 유지 (11434, 11435, 11436)
- 메모리 폭주 감지 및 재시작
"""

import psutil
import time
import subprocess
import requests
from datetime import datetime

# 허가된 Ollama 포트
ALLOWED_PORTS = [11434, 11435, 11436]
MAX_MEMORY_MB = 8 * 1024  # 8GB 이상 사용 시 재시작

def get_port_by_pid(pid):
    """PID로 사용 중인 포트 찾기"""
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.pid == pid and conn.status == 'LISTEN':
                return conn.laddr.port
    except:
        pass
    return None

def get_ollama_processes():
    """모든 Ollama 프로세스 정보"""
    ollama_procs = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
        try:
            if proc.info['name'] and 'ollama.exe' in proc.info['name'].lower():
                pid = proc.info['pid']
                memory_mb = proc.info['memory_info'].rss / 1024 / 1024
                port = get_port_by_pid(pid)

                ollama_procs.append({
                    'pid': pid,
                    'port': port,
                    'memory_mb': memory_mb,
                    'proc': proc
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return ollama_procs

def kill_process(pid):
    """프로세스 강제 종료"""
    try:
        proc = psutil.Process(pid)
        proc.kill()
        print(f"[KILL] PID {pid} 종료")
        return True
    except:
        return False

def monitor_ollama():
    """Ollama 프로세스 모니터링"""
    print("=" * 70)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Ollama 수호자 가동 시작")
    print(f"허가된 포트: {ALLOWED_PORTS}")
    print(f"메모리 상한: {MAX_MEMORY_MB / 1024:.1f}GB")
    print("=" * 70)

    while True:
        try:
            procs = get_ollama_processes()

            if not procs:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Ollama 프로세스 없음")
                time.sleep(10)
                continue

            killed = []
            kept = []

            for p in procs:
                pid = p['pid']
                port = p['port']
                memory_mb = p['memory_mb']

                # 1. 포트 없는 프로세스 (관리 밖)
                if port is None:
                    # app.exe는 유지, 나머지는 확인 필요
                    if 'app.exe' in str(p['proc'].name()):
                        kept.append(f"PID {pid} (app.exe, {memory_mb:.0f}MB)")
                        continue

                    # 메모리가 1GB 이상이면 불필요한 프로세스
                    if memory_mb > 1024:
                        print(f"[KILL] PID {pid} - 포트 없음 + 메모리 {memory_mb:.0f}MB (불필요)")
                        kill_process(pid)
                        killed.append(f"PID {pid} (포트없음, {memory_mb:.0f}MB)")
                        continue
                    else:
                        kept.append(f"PID {pid} (포트없음, {memory_mb:.0f}MB)")
                        continue

                # 2. 허가되지 않은 포트
                if port not in ALLOWED_PORTS:
                    print(f"[KILL] PID {pid} - 포트 {port} 허가되지 않음 ({memory_mb:.0f}MB)")
                    kill_process(pid)
                    killed.append(f"PID {pid} (포트 {port}, {memory_mb:.0f}MB)")
                    continue

                # 3. 메모리 폭주 (8GB 초과)
                if memory_mb > MAX_MEMORY_MB:
                    print(f"[KILL] PID {pid} - 포트 {port} 메모리 폭주 ({memory_mb:.0f}MB > {MAX_MEMORY_MB}MB)")
                    kill_process(pid)
                    killed.append(f"PID {pid} (포트 {port}, 메모리폭주 {memory_mb:.0f}MB)")
                    continue

                # 4. 정상 프로세스
                kept.append(f"PID {pid} (포트 {port}, {memory_mb:.0f}MB)")

            # 상태 출력
            if killed:
                print(f"[{datetime.now().strftime('%H:%M:%S')}]   정리: {', '.join(killed)}")
            if kept:
                print(f"[{datetime.now().strftime('%H:%M:%S')}]  유지: {', '.join(kept)}")

            time.sleep(10)  # 10초마다 체크

        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(10)

if __name__ == "__main__":
    monitor_ollama()
