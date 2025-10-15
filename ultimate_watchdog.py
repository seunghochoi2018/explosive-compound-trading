#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
궁극의 감시견 (Ultimate Watchdog) - 모든 트레이더 24/7 모니터링

===================================================================================
[핵심 역할] 모든 트레이더가 항상 실행되도록 보장
===================================================================================

이 Watchdog의 목적:
1. unified_trader_manager.py (매니저 연습) - 항상 실행
2. llm_eth_trader_v4_3tier.py (ETH 트레이더) - 항상 실행
3. kis_llm_trader_v2_explosive.py (KIS 트레이더) - 항상 실행

왜 3개 모두 모니터링하는가?
- 매니저가 죽으면: 자동 개선 시스템 중단
- ETH 트레이더가 죽으면: 실시간 거래 기회 손실, 포지션 관리 불가
- KIS 트레이더가 죽으면: SOXL/SOXS 거래 중단, 정규장 수익 기회 손실

사용자 요구사항:
"시작시 뿐만 아니라 모니터링해서 항상 실행될 수 있게 문제없이"
"매니저 연습도" - unified_trader_manager 연습.py도 포함

===================================================================================
[작동 원리] 3중 안전장치
===================================================================================

1. 프로세스 생존 체크 (30초마다)
   - PID 파일 확인
   - 프로세스 목록 직접 검색
   - 크래시 자동 감지

2. 자동 재시작 시퀀스
   - 죽은 프로세스 감지 즉시 재시작
   - 10초 대기 후 시작 확인
   - 텔레그램 알림 (옵션)

3. 연속 크래시 보호
   - 5분 내 3회 이상 재시작 방지
   - 무한 루프 방지
   - 쿨다운 메커니즘

===================================================================================
[자동 시작 설정] Windows 부팅 시 자동 실행
===================================================================================

이 스크립트는 Windows 시작 프로그램에 자동으로 등록됩니다:
- 경로: shell:startup
- 파일: ultimate_watchdog.vbs (숨김 실행)
- 부팅 시 자동 시작

수동 등록 방법:
1. Win+R → shell:startup
2. 바로가기 생성: C:\\Users\\user\\PycharmProjects\\PythonProject\\.venv\\Scripts\\python.exe
3. 대상: "C:\\Users\\user\\Documents\\코드5\\ultimate_watchdog.py"

===================================================================================
"""
import os
import sys
import time
import subprocess
import psutil
from datetime import datetime
from pathlib import Path

class UltimateWatchdog:
    def __init__(self):
        # Python 경로
        self.python_path = r"C:\Users\user\PycharmProjects\PythonProject\.venv\Scripts\python.exe"

        # 감시 대상 (매니저 연습 추가!)
        self.traders = {
            'manager': {
                'name': '통합매니저 (연습)',
                'script': r"C:\Users\user\Documents\코드5\unified_trader_manager 연습.py",
                'pid_file': r"C:\Users\user\Documents\코드5\.unified_trader_manager_practice.pid",
                'process_name': 'unified_trader_manager 연습',
                'enabled': True
            },
            'eth': {
                'name': 'ETH 트레이더',
                'script': r"C:\Users\user\Documents\코드3\llm_eth_trader_v4_3tier.py",
                'pid_file': r"C:\Users\user\Documents\코드3\.eth_trader.pid",
                'process_name': 'llm_eth_trader_v4_3tier',
                'enabled': True
            },
            'kis': {
                'name': 'KIS 트레이더',
                'script': r"C:\Users\user\Documents\코드4\kis_llm_trader_v2_explosive.py",
                'pid_file': r"C:\Users\user\Documents\코드4\.kis_trader.pid",
                'process_name': 'kis_llm_trader_v2_explosive',
                'enabled': True
            }
        }

        # 감시 설정
        self.check_interval = 30  # 30초마다 확인
        self.restart_delay = 10  # 재시작 후 10초 대기
        self.max_restart_attempts = 3  # 5분 내 최대 3회
        self.restart_cooldown = 300  # 5분 쿨다운

        # 재시작 카운터 (각 트레이더별)
        self.restart_counts = {k: 0 for k in self.traders.keys()}
        self.last_restart_times = {k: 0 for k in self.traders.keys()}

        print("=" * 80)
        print("궁극의 감시견 (Ultimate Watchdog) 시작")
        print("=" * 80)
        print("감시 대상:")
        for key, trader in self.traders.items():
            if trader['enabled']:
                print(f"  - {trader['name']}: {os.path.basename(trader['script'])}")
        print(f"\n확인 주기: {self.check_interval}초")
        print(f"재시작 지연: {self.restart_delay}초")
        print("=" * 80)

        # Windows 시작 프로그램 자동 등록
        self.setup_startup()

    def is_trader_running(self, trader_key):
        """트레이더가 실행 중인지 확인"""
        trader = self.traders[trader_key]

        # 1. PID 파일 확인
        if os.path.exists(trader['pid_file']):
            try:
                with open(trader['pid_file'], 'r') as f:
                    pid = int(f.read().strip())

                if psutil.pid_exists(pid):
                    try:
                        proc = psutil.Process(pid)
                        cmdline = ' '.join(proc.cmdline())
                        if trader['process_name'] in cmdline:
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
                    if 'python' in cmdline.lower() and trader['process_name'] in cmdline:
                        return True, proc.info['pid']
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return False, None

    def start_trader(self, trader_key):
        """트레이더 시작"""
        trader = self.traders[trader_key]
        current_time = time.time()

        # 쿨다운 체크
        if current_time - self.last_restart_times[trader_key] > self.restart_cooldown:
            self.restart_counts[trader_key] = 0

        # 연속 재시작 제한
        if self.restart_counts[trader_key] >= self.max_restart_attempts:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [WARN] {trader['name']} 연속 재시작 {self.restart_counts[trader_key]}회 초과")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [WAIT] {self.restart_cooldown}초 대기 후 재시도...")
            time.sleep(self.restart_cooldown)
            self.restart_counts[trader_key] = 0

        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] [START] {trader['name']} 시작 중...")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [SCRIPT] {trader['script']}")

            # 기존 PID 파일 정리
            if os.path.exists(trader['pid_file']):
                os.remove(trader['pid_file'])
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [CLEAN] 기존 PID 파일 삭제")

            # 백그라운드로 시작
            proc = subprocess.Popen(
                [self.python_path, trader['script']],
                cwd=os.path.dirname(trader['script']),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )

            # PID 파일 생성
            with open(trader['pid_file'], 'w') as f:
                f.write(str(proc.pid))

            self.restart_counts[trader_key] += 1
            self.last_restart_times[trader_key] = current_time

            # 시작 확인 대기
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [WAIT] {self.restart_delay}초 대기 (초기화 확인)...")
            time.sleep(self.restart_delay)

            # 시작 확인
            is_running, pid = self.is_trader_running(trader_key)
            if is_running:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [OK] {trader['name']} 시작 완료 (PID: {pid})")
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [STAT] 재시작 카운터: {self.restart_counts[trader_key]}/{self.max_restart_attempts}")
                return True
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR] {trader['name']} 시작 실패")
                return False

        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR] {trader['name']} 시작 오류: {e}")
            return False

    def setup_startup(self):
        """Windows 시작 프로그램에 자동 등록"""
        try:
            startup_folder = Path(os.path.expandvars(r'%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup'))
            vbs_path = startup_folder / 'ultimate_watchdog.vbs'

            # VBS 스크립트로 숨김 실행 (콘솔 창 없음)
            vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """{self.python_path}"" ""{os.path.abspath(__file__)}""", 0, False
Set WshShell = Nothing
'''

            if not vbs_path.exists():
                with open(vbs_path, 'w', encoding='utf-8') as f:
                    f.write(vbs_content)
                print(f"\n[STARTUP] Windows 시작 프로그램에 등록 완료")
                print(f"[STARTUP] 경로: {vbs_path}")
            else:
                print(f"\n[STARTUP] 이미 Windows 시작 프로그램에 등록됨")

        except Exception as e:
            print(f"\n[WARN] Windows 시작 프로그램 등록 실패: {e}")
            print(f"[WARN] 수동 등록 필요: shell:startup")

    def run(self):
        """감시견 메인 루프 - 무한 실행"""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] [WATCH] 감시 시작...\n")

        # 초기 상태 확인 및 시작
        for key, trader in self.traders.items():
            if not trader['enabled']:
                continue

            is_running, pid = self.is_trader_running(key)
            if not is_running:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [WARN] {trader['name']} 실행되지 않음")
                self.start_trader(key)
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [OK] {trader['name']} 실행 중 (PID: {pid})")

        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] [WATCH] 정기 감시 시작 ({self.check_interval}초 간격)\n")

        # 무한 감시 루프
        while True:
            try:
                time.sleep(self.check_interval)

                # 각 트레이더 상태 확인
                for key, trader in self.traders.items():
                    if not trader['enabled']:
                        continue

                    is_running, pid = self.is_trader_running(key)

                    if is_running:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] [OK] {trader['name']} 정상 (PID: {pid})")
                    else:
                        # 크래시 감지 - 즉시 재시작
                        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] [ERROR] {trader['name']} 크래시 감지!")
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] [RESTART] 자동 재시작 시도...")

                        success = self.start_trader(key)
                        if success:
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] [OK] {trader['name']} 재시작 성공\n")
                        else:
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] [WARN] {trader['name']} 재시작 실패, 다음 주기에 재시도\n")

            except KeyboardInterrupt:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] [STOP] 감시견 종료 요청")
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [WARN] 모든 트레이더는 계속 실행됩니다")
                break
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR] 감시 오류: {e}")
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [WAIT] 30초 후 재시도...")
                time.sleep(30)

if __name__ == "__main__":
    watchdog = UltimateWatchdog()
    watchdog.run()
