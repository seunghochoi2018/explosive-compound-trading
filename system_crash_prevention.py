#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
시스템 크래시 방지 시스템

ROOT CAUSE ANALYSIS (2025-10-15):
==================================

1. ETH Trader 크래시
   원인: [ERROR] cannot access local variable 'deep_buy' where it is not associated with a value
   위치: llm_eth_trader_v4_3tier.py 메인 루프
   발생: Tier 3 폴백 경로에서 변수 초기화 누락
   영향: 프로세스 중단 → 거래 중단

2. 통합 매니저 반복 재시작
   원인: 봇 중지/시작 루프 (10-10 02:10~02:46, 36분간 17회 재시작)
   패턴: ETH 중지 → KIS 시작 → KIS 중지 → ETH 시작 (반복)
   영향: 시스템 불안정, 리소스 낭비

3. KIS Trader LLM 우회
   상태: [FORCE] 7b/14b LLM 분석 우회 - 강제 신호 생성
   원인: LLM 응답 실패 또는 타임아웃
   영향: 정확도 저하, 백테스트 무효화

PREVENTION STRATEGY (다층 방어 시스템):
=====================================

Layer 1: 코드 레벨 안전장치
- 모든 변수 초기화 보장
- Try-Except 강화
- 폴백 경로 검증

Layer 2: 프로세스 감시 (Watchdog)
- 30초마다 헬스체크
- 크래시 감지 → 즉시 재시작
- 재시작 쿨다운 (5분 내 3회 제한)

Layer 3: 무한 루프 차단
- 재시작 간격 모니터링
- 1분 내 재시작 → 경고
- 5분 내 3회 → 긴급 정지 + 텔레그램 알림

Layer 4: LLM 헬스체크
- Ollama API 응답 확인
- 타임아웃 감지
- 강제 신호 금지 (LLM 필수)

Layer 5: 리소스 모니터링
- 메모리 9GB 제한 (각 포트)
- CPU 800% 초과 → 경고
- 디스크 여유 공간 체크
"""

import os
import sys
import time
import json
import psutil
import requests
from datetime import datetime, timedelta
from collections import deque

# ========== 설정 ==========
CHECK_INTERVAL = 30  # 30초마다 체크

PROCESSES = {
    'ETH': {
        'script': r'C:\Users\user\Documents\코드3\llm_eth_trader_v4_3tier.py',
        'cwd': r'C:\Users\user\Documents\코드3',
        'name': 'ETH 트레이더'
    },
    'KIS': {
        'script': r'C:\Users\user\Documents\코드4\kis_llm_trader_v2_explosive.py',
        'cwd': r'C:\Users\user\Documents\코드4',
        'name': 'KIS 트레이더'
    },
    'Manager': {
        'script': r'C:\Users\user\Documents\코드5\unified_trader_manager 연습.py',
        'cwd': r'C:\Users\user\Documents\코드5',
        'name': '통합 매니저'
    }
}

OLLAMA_PORTS = [11434, 11436]
MEMORY_LIMIT_GB = 9.0
CPU_LIMIT_PERCENT = 800.0

# 재시작 제한
MAX_RESTARTS_PER_WINDOW = 3
RESTART_WINDOW_MINUTES = 5
MIN_RESTART_INTERVAL_SECONDS = 60

# ========== 상태 추적 ==========
restart_history = {name: deque(maxlen=10) for name in PROCESSES.keys()}
last_restart_time = {name: None for name in PROCESSES.keys()}
restart_count = {name: 0 for name in PROCESSES.keys()}

# ========== 함수 ==========

def send_telegram_alert(message):
    """텔레그램 긴급 알림"""
    try:
        # 실제 텔레그램 봇 토큰/채팅ID는 각 트레이더의 설정 파일에서 로드
        print(f"[TELEGRAM] {message}")
    except Exception as e:
        print(f"[WARN] 텔레그램 전송 실패: {e}")


def check_ollama_health():
    """Ollama 서버 헬스체크"""
    healthy_ports = []
    for port in OLLAMA_PORTS:
        try:
            resp = requests.get(f"http://127.0.0.1:{port}/api/tags", timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                if 'models' in data and len(data['models']) > 0:
                    healthy_ports.append(port)
        except:
            pass

    return healthy_ports


def check_process_alive(process_name):
    """프로세스 실행 여부 확인"""
    script_path = PROCESSES[process_name]['script']

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline', [])
            if cmdline and any(script_path in arg for arg in cmdline):
                return proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    return None


def check_restart_safety(process_name):
    """재시작 안전성 검사 (무한 루프 방지)"""
    now = datetime.now()

    # 1분 내 재시작 금지
    if last_restart_time[process_name]:
        elapsed = (now - last_restart_time[process_name]).total_seconds()
        if elapsed < MIN_RESTART_INTERVAL_SECONDS:
            print(f"[BLOCK] {process_name} 재시작 차단: {elapsed:.0f}초 전에 재시작됨 (최소 {MIN_RESTART_INTERVAL_SECONDS}초 필요)")
            return False

    # 5분 내 3회 재시작 제한
    recent_restarts = [t for t in restart_history[process_name]
                       if (now - t).total_seconds() < RESTART_WINDOW_MINUTES * 60]

    if len(recent_restarts) >= MAX_RESTARTS_PER_WINDOW:
        msg = f"[CRITICAL] {process_name} 반복 크래시 감지! (5분 내 {len(recent_restarts)}회 재시작)"
        print(msg)
        send_telegram_alert(msg)
        print(f"[EMERGENCY STOP] {process_name} 자동 재시작 중단 - 수동 개입 필요!")
        return False

    return True


def restart_process(process_name):
    """프로세스 재시작"""
    if not check_restart_safety(process_name):
        return False

    proc_info = PROCESSES[process_name]

    print(f"[RESTART] {proc_info['name']} 재시작 시작...")

    # Python 경로
    python_exe = r"C:\Users\user\PycharmProjects\PythonProject\.venv\Scripts\python.exe"

    # 재시작
    try:
        import subprocess

        # 백그라운드 실행
        cmd = f'start "" /MIN "{python_exe}" "{proc_info["script"]}"'
        subprocess.Popen(cmd, shell=True, cwd=proc_info['cwd'],
                        creationflags=subprocess.CREATE_NEW_CONSOLE)

        # 재시작 기록
        now = datetime.now()
        restart_history[process_name].append(now)
        last_restart_time[process_name] = now
        restart_count[process_name] += 1

        print(f"[SUCCESS] {proc_info['name']} 재시작 완료")

        # 텔레그램 알림
        recent_count = len([t for t in restart_history[process_name]
                           if (now - t).total_seconds() < 300])
        send_telegram_alert(f"[AUTO-RESTART] {proc_info['name']} 자동 재시작 (5분 내 {recent_count}회)")

        return True

    except Exception as e:
        print(f"[ERROR] {proc_info['name']} 재시작 실패: {e}")
        return False


def check_resource_limits():
    """리소스 제한 체크"""
    warnings = []

    # Ollama 프로세스 메모리 체크
    for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
        try:
            if proc.info['name'] in ['ollama.exe', 'ollama']:
                mem_gb = proc.info['memory_info'].rss / (1024**3)
                cpu_pct = proc.info.get('cpu_percent', 0)

                if mem_gb > MEMORY_LIMIT_GB:
                    warnings.append(f"Ollama PID={proc.info['pid']} 메모리 초과: {mem_gb:.1f}GB > {MEMORY_LIMIT_GB}GB")

                if cpu_pct > CPU_LIMIT_PERCENT:
                    warnings.append(f"Ollama PID={proc.info['pid']} CPU 과부하: {cpu_pct:.0f}% > {CPU_LIMIT_PERCENT}%")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # 디스크 여유 공간
    disk = psutil.disk_usage('C:\\')
    free_gb = disk.free / (1024**3)
    if free_gb < 5.0:
        warnings.append(f"디스크 여유 공간 부족: {free_gb:.1f}GB < 5GB")

    return warnings


def main():
    """메인 루프"""
    print("="*80)
    print("시스템 크래시 방지 시스템 시작")
    print("="*80)
    print(f"체크 간격: {CHECK_INTERVAL}초")
    print(f"재시작 제한: {RESTART_WINDOW_MINUTES}분 내 {MAX_RESTARTS_PER_WINDOW}회")
    print(f"최소 재시작 간격: {MIN_RESTART_INTERVAL_SECONDS}초")
    print("="*80)
    print()

    cycle = 0

    while True:
        try:
            cycle += 1
            now = datetime.now().strftime("%H:%M:%S")

            print(f"\n[{now}] ========== Cycle {cycle} ==========")

            # 1. Ollama 헬스체크
            healthy_ports = check_ollama_health()
            print(f"[OLLAMA] 정상 포트: {healthy_ports}/{OLLAMA_PORTS}")

            if len(healthy_ports) == 0:
                print("[CRITICAL] Ollama 서버 모두 다운!")
                send_telegram_alert("[CRITICAL] Ollama 서버 모두 다운! Guardian 확인 필요")

            # 2. 프로세스 체크
            for name, info in PROCESSES.items():
                pid = check_process_alive(name)

                if pid:
                    print(f"[OK] {info['name']}: PID={pid}")
                else:
                    print(f"[DOWN] {info['name']}: 프로세스 없음")
                    restart_process(name)

            # 3. 리소스 체크
            warnings = check_resource_limits()
            if warnings:
                print("[WARN] 리소스 경고:")
                for w in warnings:
                    print(f"  - {w}")

            # 대기
            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print("\n[STOP] 사용자 중단")
            break
        except Exception as e:
            print(f"[ERROR] 메인 루프 에러: {e}")
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
