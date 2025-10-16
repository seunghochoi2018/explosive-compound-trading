#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합 러너 - 매니저 + 워치독 통합 실행
- unified_trader_manager.py 시작 및 관리
- 내장 워치독으로 실시간 감시
- 헬스체크 및 자동 복구
"""
import subprocess
import time
import psutil
import requests
from datetime import datetime
from pathlib import Path
import threading
import sys

# ===== 설정 =====
MANAGER_SCRIPT = r"C:\Users\user\Documents\코드5\unified_trader_manager.py"
MANAGER_PYTHON = r"C:\Users\user\AppData\Local\Programs\Python\Python311\python.exe"
PID_FILE = Path(r"C:\Users\user\Documents\코드5\.unified_trader_manager.pid")
HEARTBEAT_FILE = Path(r"C:\Users\user\Documents\코드5\.manager_heartbeat.txt")
RUNNER_PID_FILE = Path(r"C:\Users\user\Documents\코드5\.integrated_runner.pid")

# 워치독 설정
CHECK_INTERVAL = 30  # 30초마다 체크
HEARTBEAT_TIMEOUT = 60  # 1분간 헬스비트 없으면 크래시로 판단

# 텔레그램
TELEGRAM_BOT_TOKEN = "7819173403:AAEwBNh6eKSPX3K79Lj87p5-h4CdmshfIBw"
TELEGRAM_CHAT_ID = "7805944420"

# ===== 전역 변수 =====
manager_process = None
shutdown_flag = False
last_alert_message = None  # 마지막 알림 메시지 (중복 방지)

def send_telegram(message: str, skip_duplicate=True):
    """텔레그램 알림 전송 (중복 방지)"""
    global last_alert_message

    # 중복 메시지 확인
    if skip_duplicate and message == last_alert_message:
        return False  # 같은 메시지는 보내지 않음

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, data=payload, timeout=5)
        if response.status_code == 200:
            last_alert_message = message  # 성공 시 저장
            return True
        return False
    except Exception as e:
        print(f"[ERROR] 텔레그램 전송 실패: {e}")
        return False

def log(message: str):
    """타임스탬프 포함 로그"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    full_msg = f"[{timestamp}] {message}"
    print(full_msg)
    return full_msg

def is_manager_healthy() -> tuple[bool, str]:
    """통합 매니저 헬스체크"""
    global manager_process

    # 1. 프로세스 객체 확인
    if manager_process is None:
        return False, "프로세스 미시작"

    # 2. 프로세스 상태 확인
    try:
        poll = manager_process.poll()
        if poll is not None:
            return False, f"프로세스 종료됨 (exit code: {poll})"
    except Exception as e:
        return False, f"프로세스 체크 오류: {e}"

    # 3. PID 파일 확인
    if not PID_FILE.exists():
        return False, "PID 파일 없음"

    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())

        if not psutil.pid_exists(pid):
            return False, f"프로세스 없음 (PID: {pid})"
    except Exception as e:
        return False, f"PID 파일 오류: {e}"

    # 4. 헬스비트 체크
    if HEARTBEAT_FILE.exists():
        heartbeat_age = time.time() - HEARTBEAT_FILE.stat().st_mtime
        if heartbeat_age > HEARTBEAT_TIMEOUT:
            return False, f"헬스비트 타임아웃 ({int(heartbeat_age)}초)"
    else:
        return False, "헬스비트 파일 없음"

    return True, "정상"

def start_manager():
    """통합 매니저 시작"""
    global manager_process

    try:
        log("통합 매니저 시작 중...")

        # 기존 프로세스 정리
        if manager_process:
            try:
                manager_process.terminate()
                manager_process.wait(timeout=5)
            except:
                pass

        # 새 프로세스 시작
        manager_process = subprocess.Popen(
            [MANAGER_PYTHON, MANAGER_SCRIPT],
            cwd=Path(MANAGER_SCRIPT).parent,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )

        log(f"통합 매니저 시작됨 (PID: {manager_process.pid})")

        # 시작 대기 (10초)
        time.sleep(10)

        # 시작 확인
        healthy, status = is_manager_healthy()
        if healthy:
            log("✓ 통합 매니저 시작 완료")
            send_telegram(
                f"[OK] <b>통합 매니저 시작 완료</b>\n\n"
                f"PID: {manager_process.pid}\n"
                f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            return True
        else:
            log(f"✗ 통합 매니저 시작 실패: {status}")
            return False

    except Exception as e:
        log(f"[ERROR] 시작 실패: {e}")
        send_telegram(
            f"[ERROR] <b>통합 매니저 시작 실패</b>\n\n"
            f"오류: {e}\n"
            f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        return False

def restart_manager():
    """통합 매니저 재시작"""
    global manager_process

    log("[RESTART] 통합 매니저 재시작 시도...")
    send_telegram(
        f"[WARNING] <b>통합 매니저 재시작 중...</b>\n\n"
        f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    # 기존 프로세스 종료
    if manager_process:
        try:
            log("기존 프로세스 종료 중...")
            manager_process.terminate()
            manager_process.wait(timeout=10)
            log("기존 프로세스 종료 완료")
        except Exception as e:
            log(f"기존 프로세스 강제 종료: {e}")
            try:
                manager_process.kill()
            except:
                pass

    # 재시작
    time.sleep(3)
    return start_manager()

def watchdog_thread():
    """워치독 쓰레드 - 매니저 감시"""
    global shutdown_flag

    log("[WATCHDOG] 워치독 시작")
    down_count = 0
    last_alert_time = 0
    last_healthy_status = True  # 마지막 헬스 상태

    while not shutdown_flag:
        try:
            time.sleep(CHECK_INTERVAL)

            if shutdown_flag:
                break

            current_time = time.time()
            healthy, status = is_manager_healthy()

            if healthy:
                # 정상 실행 중
                if not last_healthy_status or down_count > 0:
                    # 복구된 경우에만 알림
                    log("✓ 통합 매니저 복구 확인")
                    send_telegram(
                        f"[OK] <b>통합 매니저 복구됨</b>\n\n"
                        f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        skip_duplicate=False
                    )
                    down_count = 0
                    last_healthy_status = True

                # 정상 상태는 로그만 (알림 X)
                log(f"✓ 매니저 정상 ({status})")

            else:
                # 다운 감지
                down_count += 1
                log(f"✗ 매니저 이상 감지 ({down_count}회) - {status}")
                last_healthy_status = False

                # 1분 이상 경과 시 알림 (한 번만)
                if current_time - last_alert_time > 60:
                    send_telegram(
                        f"[CRITICAL] <b>통합 매니저 이상!</b>\n\n"
                        f"원인: {status}\n"
                        f"감지 횟수: {down_count}회\n"
                        f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        f"⚠️ 자동 재시작 시도 중...",
                        skip_duplicate=False
                    )
                    last_alert_time = current_time

                # 2회 연속 다운 감지 시 재시작
                if down_count >= 2:
                    if restart_manager():
                        down_count = 0
                        last_healthy_status = True
                    else:
                        send_telegram(
                            f"[ERROR] <b>통합 매니저 재시작 실패</b>\n\n"
                            f"⚠️ 수동 재시작 필요!\n"
                            f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                            skip_duplicate=False
                        )

        except Exception as e:
            log(f"[ERROR] 워치독 오류: {e}")

    log("[WATCHDOG] 워치독 종료")

def main():
    """메인 함수"""
    global shutdown_flag, manager_process

    print("="*70)
    print("통합 러너 시작 - 매니저 + 워치독")
    print("="*70)

    # Runner PID 저장
    with open(RUNNER_PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

    # 텔레그램 알림
    send_telegram(
        f"[START] <b>통합 러너 시작</b>\n\n"
        f"통합 매니저 + 워치독 실행\n"
        f"체크 주기: {CHECK_INTERVAL}초\n"
        f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        skip_duplicate=False
    )

    # 기존 매니저 확인
    healthy, status = is_manager_healthy()
    if healthy:
        log(f"✓ 기존 통합 매니저 감지됨 ({status})")
        log("기존 매니저를 감시합니다...")

        # 기존 프로세스 정보 가져오기
        try:
            with open(PID_FILE, 'r') as f:
                existing_pid = int(f.read().strip())
            log(f"기존 매니저 PID: {existing_pid}")
        except:
            pass
    else:
        # 통합 매니저 시작
        log("기존 매니저가 없습니다. 새로 시작합니다...")
        if not start_manager():
            log("[ERROR] 통합 매니저 시작 실패, 종료합니다")
            return

    # 워치독 쓰레드 시작
    watchdog = threading.Thread(target=watchdog_thread, daemon=True)
    watchdog.start()

    # 메인 루프
    try:
        log("통합 러너 실행 중... (Ctrl+C로 종료)")
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        log("\n[SHUTDOWN] 종료 신호 수신")
        shutdown_flag = True

        # 매니저 종료
        if manager_process:
            try:
                log("통합 매니저 종료 중...")
                manager_process.terminate()
                manager_process.wait(timeout=10)
                log("통합 매니저 종료 완료")
            except Exception as e:
                log(f"통합 매니저 강제 종료: {e}")
                try:
                    manager_process.kill()
                except:
                    pass

        # 워치독 대기
        watchdog.join(timeout=5)

        # PID 파일 정리
        try:
            RUNNER_PID_FILE.unlink()
        except:
            pass

        # 종료 알림
        send_telegram(
            f"[STOP] <b>통합 러너 종료</b>\n\n"
            f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        log("통합 러너 종료 완료")

import os
if __name__ == "__main__":
    main()
