#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KIS 트레이더 프로세스 정리 스크립트"""
import psutil
import time
import sys

print("KIS 트레이더 프로세스 검색 중...")

# 모든 Python 프로세스에서 KIS 트레이더 찾기
kis_processes = []
for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
    try:
        if proc.info['name'] and 'python' in proc.info['name'].lower():
            if proc.info['cmdline']:
                cmdline_str = ' '.join(str(c) for c in proc.info['cmdline'])
                if 'kis_llm_trader_v2_explosive.py' in cmdline_str:
                    kis_processes.append({
                        'pid': proc.info['pid'],
                        'cmdline': cmdline_str[:100],
                        'proc': proc
                    })
                    print(f"발견: PID {proc.info['pid']} - {cmdline_str[:80]}")
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        continue

print(f"\n총 {len(kis_processes)}개 KIS 트레이더 프로세스 발견")

if len(kis_processes) == 0:
    print("실행 중인 KIS 트레이더 없음")
    sys.exit(0)

# 모든 프로세스 강제 종료
print("\n프로세스 종료 시작...")
for info in kis_processes:
    try:
        proc = info['proc']
        proc.kill()
        print(f"강제 종료: PID {info['pid']}")
    except Exception as e:
        print(f"종료 실패: PID {info['pid']} - {e}")

# 종료 확인
time.sleep(3)
print("\n종료 확인 중...")

still_running = 0
for info in kis_processes:
    try:
        if psutil.pid_exists(info['pid']):
            proc = psutil.Process(info['pid'])
            if proc.is_running():
                still_running += 1
                print(f"아직 실행 중: PID {info['pid']}")
    except:
        pass

if still_running == 0:
    print("\n모든 KIS 트레이더 프로세스 종료 완료!")
else:
    print(f"\n경고: {still_running}개 프로세스가 아직 실행 중입니다")

print("\n3초 후 재시작 준비...")
time.sleep(3)
