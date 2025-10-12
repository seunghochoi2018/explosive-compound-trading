#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합매니저 감시견 (Watchdog) - 항상 실행 보장

===================================================================================
[핵심 역할] 세 개의 프로세스가 무조건 돌아가야 함 (CRITICAL)
===================================================================================

이 Watchdog의 유일한 목적:
1. unified_trader_manager.py가 죽지 않고 항상 실행되도록 보장
2. 만약 죽으면 즉시 자동 재시작
3. 컴퓨터가 켜져 있는 한 절대 중단되지 않음

왜 중요한가?
- unified_trader_manager.py는 세 개의 트레이더를 관리:
  1. ETH Trader (이더) - Bybit ETH 25x 레버리지 선물
     * 3-Tier LLM 시스템 (Websocket → 7b → 14b)
     * 동적 임계값 조정 (no-trade 방지)
     * 실시간 거래 및 포지션 관리

  2. KIS Trader (케이아이에스) - SOXL/SOXS 3x 레버리지 ETF
     * 한국투자증권 API 기반
     * 반도체 섹터 14b LLM 분석
     * 정규장 시간 자동매매 (월~금 22:30-05:00)

  3. Self-Improvement (학습 프로세스) - 전략 자동 개선
     * 32b LLM 기반 거래 분석
     * 자동 전략 개선 및 적용
     * 백그라운드 학습 및 검증

이 프로세스들이 죽으면 발생하는 문제:
  * [거래 손실] 거래 기회를 놓쳐서 수익 기회 상실
  * [포지션 관리 불가] 진입한 포지션을 관리하지 못해 손실 확대 위험
  * [학습 중단] 전략 개선이 멈춰서 성능 저하
  * [데이터 손실] 거래 히스토리 및 학습 데이터 누락

사용자 요구사항 (User requirement):
"통합매니저 이더 케이아이에스 세개가 무조건 돌아가야한다고!!"
"강제진입이 아니라" (NOT about forced trading entry)
"프로세스가 항상 살아있어야 함" (Processes must ALWAYS stay alive)

===================================================================================
[작동 원리]
===================================================================================

1. 30초마다 unified_trader_manager.py 프로세스 확인
   - PID 파일 (.unified_trader_manager.pid) 체크
   - 프로세스 목록에서 실제 실행 확인

2. 프로세스가 죽은 경우 감지:
   - exit_code=15 (SIGTERM)
   - 메모리 부족으로 인한 종료
   - 예외로 인한 크래시
   - 기타 모든 종료 원인

3. 자동 재시작 시퀀스:
   - 기존 PID 파일 삭제
   - 새 프로세스 백그라운드 시작
   - 10초 대기 후 시작 확인
   - 성공 여부 로그 출력

4. 연속 재시작 보호:
   - 5분 내 3회 이상 재시작 방지
   - 쿨다운 후 카운터 리셋
   - 무한 재시작 루프 방지

===================================================================================
[사용법]
===================================================================================

# 백그라운드로 시작 (권장):
start /min python watchdog.py

# 터미널에서 직접 실행:
python watchdog.py

# 종료:
Ctrl+C (watchdog만 종료, unified_trader_manager는 계속 실행)

===================================================================================
"""
import os
import sys
import time
import subprocess
import psutil
from datetime import datetime

class UnifiedManagerWatchdog:
    def __init__(self):
        self.manager_script = r"C:\Users\user\Documents\코드5\unified_trader_manager.py"
        self.python_path = r"C:\Users\user\PycharmProjects\PythonProject\.venv\Scripts\python.exe"
        self.pid_file = r"C:\Users\user\Documents\코드5\.unified_trader_manager.pid"
        self.check_interval = 30  # 30초마다 확인
        self.restart_delay = 10  # 재시작 전 10초 대기
        self.max_restart_attempts = 3  # 최대 재시작 시도 (연속)
        self.restart_cooldown = 300  # 5분 쿨다운 후 카운터 리셋

        self.restart_count = 0
        self.last_restart_time = 0

        print("=" * 80)
        print("통합매니저 감시견 (Watchdog) 시작")
        print("=" * 80)
        print(f"감시 대상: unified_trader_manager.py")
        print(f"확인 주기: {self.check_interval}초")
        print(f"재시작 지연: {self.restart_delay}초")
        print("=" * 80)

    def is_manager_running(self):
        """통합매니저가 실행 중인지 확인"""
        # 1. PID 파일 확인
        if os.path.exists(self.pid_file):
            try:
                with open(self.pid_file, 'r') as f:
                    pid = int(f.read().strip())

                # 프로세스 존재 확인
                if psutil.pid_exists(pid):
                    try:
                        proc = psutil.Process(pid)
                        cmdline = ' '.join(proc.cmdline())
                        if 'unified_trader_manager' in cmdline:
                            return True, pid
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            except Exception:
                pass

        # 2. 프로세스 목록에서 직접 검색
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['cmdline']:
                    cmdline = ' '.join(proc.info['cmdline'])
                    if 'python' in cmdline.lower() and 'unified_trader_manager' in cmdline:
                        return True, proc.info['pid']
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return False, None

    def start_manager(self):
        """통합매니저 시작"""
        current_time = time.time()

        # 쿨다운 체크 - 5분 지났으면 카운터 리셋
        if current_time - self.last_restart_time > self.restart_cooldown:
            self.restart_count = 0

        # 연속 재시작 제한
        if self.restart_count >= self.max_restart_attempts:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [WARN] 연속 재시작 {self.restart_count}회 초과")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [WAIT] {self.restart_cooldown}초 대기 후 재시도...")
            time.sleep(self.restart_cooldown)
            self.restart_count = 0

        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] [START] 통합매니저 시작 중...")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [DIR] 작업 디렉토리: {os.path.dirname(self.manager_script)}")

            # 기존 PID 파일 정리
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [CLEAN] 기존 PID 파일 삭제")

            # 백그라운드로 시작
            subprocess.Popen(
                [self.python_path, self.manager_script],
                cwd=os.path.dirname(self.manager_script),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )

            self.restart_count += 1
            self.last_restart_time = current_time

            # 시작 확인 대기
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [WAIT] {self.restart_delay}초 대기 (초기화 확인)...")
            time.sleep(self.restart_delay)

            # 시작 확인
            is_running, pid = self.is_manager_running()
            if is_running:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [OK] 통합매니저 시작 완료 (PID: {pid})")
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [STAT] 재시작 카운터: {self.restart_count}/{self.max_restart_attempts}")
                return True
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR] 통합매니저 시작 실패")
                return False

        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR] 시작 오류: {e}")
            return False

    def run(self):
        """감시견 메인 루프 - 무한 실행"""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] [WATCH] 감시 시작...\n")

        # 초기 상태 확인
        is_running, pid = self.is_manager_running()
        if not is_running:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [WARN] 통합매니저가 실행되지 않음")
            self.start_manager()
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [OK] 통합매니저 실행 중 (PID: {pid})")

        # 무한 감시 루프
        while True:
            try:
                time.sleep(self.check_interval)

                is_running, pid = self.is_manager_running()

                if is_running:
                    # 정상 실행 중
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] [OK] 정상 실행 중 (PID: {pid})")
                else:
                    # 중단됨 - 재시작
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] [ERROR] 통합매니저 중단 감지!")
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] [RESTART] 자동 재시작 시도...")

                    success = self.start_manager()
                    if success:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] [OK] 재시작 성공\n")
                    else:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] [WARN] 재시작 실패, 다음 주기에 재시도\n")

            except KeyboardInterrupt:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] [STOP] 감시견 종료 요청")
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [WARN] 통합매니저는 계속 실행됩니다")
                break
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR] 감시 오류: {e}")
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [WAIT] 30초 후 재시도...")
                time.sleep(30)

if __name__ == "__main__":
    watchdog = UnifiedManagerWatchdog()
    watchdog.run()
