#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합매니저 감시견 (Watchdog) - 항상 실행 보장
컴퓨터가 켜져 있는 한 통합매니저를 계속 실행
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
