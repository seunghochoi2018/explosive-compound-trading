#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합 매니저 Watchdog
- unified_trader_manager.py가 다운되면 감지하고 텔레그램 알림
- 자동 재시작
"""
import psutil
import time
import subprocess
import requests
from datetime import datetime
from pathlib import Path

# 설정
MANAGER_SCRIPT = r"C:\Users\user\Documents\코드5\unified_trader_manager 연습.py"
MANAGER_PYTHON = r"C:\Users\user\AppData\Local\Programs\Python\Python311\python.exe"
PID_FILE = Path(r"C:\Users\user\Documents\코드5\.unified_trader_manager.pid")
HEARTBEAT_FILE = Path(r"C:\Users\user\Documents\코드5\.manager_heartbeat.txt")
CHECK_INTERVAL = 30  # 30초마다 체크 (빠른 감지)
HEARTBEAT_TIMEOUT = 60  # 1분간 헬스비트 없으면 크래시로 판단

# 텔레그램
TELEGRAM_BOT_TOKEN = "7819173403:AAEwBNh6eKSPX3K79Lj87p5-h4CdmshfIBw"
TELEGRAM_CHAT_ID = "7805944420"

def send_telegram(message: str):
    """텔레그램 알림 전송"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, data=payload, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"[ERROR] 텔레그램 전송 실패: {e}")
        return False

def is_manager_running() -> tuple[bool, str]:
    """통합 매니저가 실행 중인지 확인 (헬스비트 포함)"""
    # 1. PID 파일 체크
    if not PID_FILE.exists():
        return False, "PID 파일 없음"

    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())

        # 2. PID가 실제로 실행 중인지 확인
        if not psutil.pid_exists(pid):
            return False, f"프로세스 없음 (PID: {pid})"

        # 3. 프로세스 정보 확인
        proc = psutil.Process(pid)
        cmdline = ' '.join(proc.cmdline())

        # unified_trader_manager 프로세스인지 확인
        if 'unified_trader_manager' not in cmdline:
            return False, "프로세스 불일치"

        # 4. 헬스비트 체크
        if HEARTBEAT_FILE.exists():
            heartbeat_age = time.time() - HEARTBEAT_FILE.stat().st_mtime
            if heartbeat_age > HEARTBEAT_TIMEOUT:
                return False, f"헬스비트 타임아웃 ({int(heartbeat_age)}초)"
        else:
            return False, "헬스비트 파일 없음"

        return True, "정상"

    except (ValueError, FileNotFoundError, psutil.NoSuchProcess, psutil.AccessDenied) as e:
        return False, f"오류: {e}"

def start_manager():
    """통합 매니저 시작"""
    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 통합 매니저 시작 중...")

        # 백그라운드 프로세스로 실행
        process = subprocess.Popen(
            [MANAGER_PYTHON, MANAGER_SCRIPT],
            cwd=Path(MANAGER_SCRIPT).parent,
            creationflags=subprocess.CREATE_NEW_CONSOLE  # 새 콘솔 창에서 실행
        )

        # 시작 대기 (10초)
        time.sleep(10)

        # 시작 확인
        running, status = is_manager_running()
        if running:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✓ 통합 매니저 시작 완료")
            return True
        else:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✗ 통합 매니저 시작 실패: {status}")
            return False

    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] 시작 실패: {e}")
        return False

def main():
    """메인 루프"""
    print("="*70)
    print("통합 매니저 Watchdog 시작")
    print(f"체크 주기: {CHECK_INTERVAL}초")
    print("="*70)

    # 초기 알림
    send_telegram(
        f"[START] <b>Watchdog 시작</b>\n\n"
        f"통합 매니저 감시 시작\n"
        f"체크 주기: {CHECK_INTERVAL}초\n"
        f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    down_count = 0  # 연속 다운 카운트
    last_alert_time = 0  # 마지막 알림 시간 (중복 알림 방지)

    while True:
        try:
            current_time = time.time()

            running, status = is_manager_running()

            if running:
                # 정상 실행 중
                if down_count > 0:
                    # 복구됨
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✓ 통합 매니저 복구 확인")
                    send_telegram(
                        f"[OK] <b>통합 매니저 복구됨</b>\n\n"
                        f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    down_count = 0

                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✓ 통합 매니저 정상 ({status})")

            else:
                # 다운 감지
                down_count += 1
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✗ 통합 매니저 다운 감지 ({down_count}회) - {status}")

                # 1분 이상 경과 시 알림 (중복 방지)
                if current_time - last_alert_time > 60:
                    send_telegram(
                        f"[CRITICAL] <b>통합 매니저 다운!</b>\n\n"
                        f"<b>원인:</b> {status}\n"
                        f"<b>감지 횟수:</b> {down_count}회\n"
                        f"<b>시간:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        f"⚠️ 즉시 확인 필요! 자동 재시작 시도 중..."
                    )
                    last_alert_time = current_time

                # 2회 연속 다운 감지 시 재시작 시도 (빠른 복구)
                if down_count >= 2:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [RESTART] 자동 재시작 시도...")

                    if start_manager():
                        send_telegram(
                            f"[OK] <b>통합 매니저 자동 재시작 성공</b>\n\n"
                            f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        down_count = 0
                    else:
                        send_telegram(
                            f"[ERROR] <b>통합 매니저 재시작 실패</b>\n\n"
                            f"⚠️ 수동 재시작 필요!\n"
                            f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        # 재시도를 위해 카운트 유지

            # 대기
            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Watchdog 종료")
            send_telegram(
                f"[STOP] <b>Watchdog 종료</b>\n\n"
                f"통합 매니저 감시 중단\n"
                f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            break

        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] Watchdog 오류: {e}")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
