#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합 트레이더 관리 시스템
- 코드3 (ETH 트레이더) + 코드4 (KIS 트레이더) 동시 관리
- Ollama 2개 독립 실행 (포트 충돌 방지)
- 지능적 리소스 관리 (메모리, CPU, 큐잉 감지)
- 타임아웃 자동 복구
- 주기적 재시작 (4시간)
"""
import subprocess
import time
import psutil
import os
import requests
from datetime import datetime
from pathlib import Path
from collections import deque
import threading
import re

# ===== 텔레그램 알림 =====
class TelegramNotifier:
    def __init__(self):
        self.bot_token = "7819173403:AAEwBNh6etqyWvh-GivLDrTJb8b_ho2ju-U"
        self.chat_id = "7805944420"
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def send_message(self, message: str):
        try:
            payload = {'chat_id': self.chat_id, 'text': message, 'parse_mode': 'HTML'}
            response = requests.post(self.base_url, data=payload, timeout=5)
            return response.status_code == 200
        except:
            return False

    def notify_system_start(self):
        message = "🚀 <b>통합 트레이더 시스템 시작</b>\n\n✅ ETH Trader\n✅ KIS Trader\n✅ Ollama 관리자"
        self.send_message(message)

    def notify_system_error(self, error_msg: str):
        message = f"⚠️ <b>시스템 오류</b>\n\n{error_msg}"
        self.send_message(message)

    def notify_position_change(self, trader: str, action: str, details: str):
        message = f"🔄 <b>{trader} 포지션 변경</b>\n\n{action}\n{details}"
        self.send_message(message)

    def notify_ollama_restart(self, trader: str, reason: str):
        message = f"🔧 <b>{trader} Ollama 재시작</b>\n\n사유: {reason}"
        self.send_message(message)

telegram = TelegramNotifier()

# ===== 설정 =====
RESTART_INTERVAL = 4 * 60 * 60  # 4시간 (초 단위)

# Ollama 설정
OLLAMA_EXE = r"C:\Users\user\AppData\Local\Programs\Ollama\ollama.exe"
OLLAMA_PORT_ETH = 11434  # 코드3 (ETH) 전용
OLLAMA_PORT_KIS = 11435  # 코드4 (KIS) 전용

# 트레이더 설정
ETH_TRADER_DIR = r"C:\Users\user\Documents\코드3"
ETH_TRADER_SCRIPT = r"C:\Users\user\Documents\코드3\llm_eth_trader_v3_ensemble.py"
ETH_PYTHON = r"C:\Users\user\PycharmProjects\PythonProject\.venv\Scripts\python.exe"

KIS_TRADER_DIR = r"C:\Users\user\Documents\코드4"
KIS_TRADER_SCRIPT = r"C:\Users\user\Documents\코드4\kis_llm_trader.py"
KIS_PYTHON = r"C:\Users\user\AppData\Local\Programs\Python\Python311\python.exe"

# ===== 리소스 모니터링 설정 =====
MAX_MEMORY_MB = 10 * 1024  # Ollama 메모리 상한: 10GB
MAX_CPU_PERCENT = 5.0  # 정상 상태 CPU: 5% 이하
RESPONSE_TIMEOUT = 10  # API 응답 타임아웃: 10초
QUEUE_DETECT_THRESHOLD = 60  # 큐잉 감지: 60초 이상 CPU 0%

# 응답 시간 추적 (최근 10개)
response_times_eth = deque(maxlen=10)
response_times_kis = deque(maxlen=10)

# ===== 색상 출력 =====
def colored_print(message, color="white"):
    """색상 출력"""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "reset": "\033[0m"
    }
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{colors.get(color, colors['white'])}[{timestamp}] {message}{colors['reset']}")

# ===== Ollama 헬스 체크 =====
def check_ollama_health(port):
    """Ollama 상태 체크 (메모리, CPU, 응답성)"""
    try:
        # 1. 프로세스 찾기
        ollama_proc = None
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info']):
            try:
                if proc.info['name'] == 'ollama.exe':
                    cmdline = proc.info.get('cmdline', [])
                    # 환경변수로 포트 구분은 어려우므로 PID 추적 필요
                    # 일단 메모리 기준으로 체크
                    ollama_proc = proc
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if not ollama_proc:
            return {"status": "not_running", "action": "restart"}

        # 2. 메모리 체크
        memory_mb = ollama_proc.info['memory_info'].rss / 1024 / 1024
        if memory_mb > MAX_MEMORY_MB:
            return {
                "status": "high_memory",
                "memory_mb": memory_mb,
                "action": "restart"
            }

        # 3. CPU 체크 (0%인데 요청 있으면 큐잉 의심)
        cpu_percent = ollama_proc.cpu_percent(interval=1)

        # 4. API 응답 체크
        start_time = time.time()
        try:
            response = requests.get(f"http://127.0.0.1:{port}/api/tags", timeout=RESPONSE_TIMEOUT)
            response_time = time.time() - start_time

            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "memory_mb": memory_mb,
                    "cpu_percent": cpu_percent,
                    "response_time": response_time
                }
            else:
                return {"status": "api_error", "action": "restart"}

        except requests.Timeout:
            return {
                "status": "timeout",
                "cpu_percent": cpu_percent,
                "action": "restart"
            }
        except requests.ConnectionError:
            return {"status": "connection_error", "action": "restart"}

    except Exception as e:
        return {"status": "error", "error": str(e), "action": "restart"}

def should_restart_ollama(health_status, response_times):
    """Ollama 재시작 필요 여부 판단 (지능적 판단)"""
    # 1. 명시적 재시작 필요
    if health_status.get("action") == "restart":
        reason = health_status.get("status")
        if reason == "high_memory":
            return True, f"메모리 과다 ({health_status['memory_mb']:.1f}MB > {MAX_MEMORY_MB}MB)"
        elif reason == "timeout":
            return True, f"API 타임아웃 (CPU: {health_status.get('cpu_percent', 0):.1f}%)"
        elif reason == "not_running":
            return True, "프로세스 종료됨"
        elif reason == "connection_error":
            return True, "연결 오류"
        else:
            return True, reason

    # 2. 응답 시간 패턴 분석 (최근 3개가 모두 5초 이상 → 큐잉)
    if len(response_times) >= 3:
        recent_3 = list(response_times)[-3:]
        if all(t > 5.0 for t in recent_3):
            avg_time = sum(recent_3) / 3
            return True, f"응답 지연 (평균 {avg_time:.1f}초)"

    # 3. CPU 0% + 응답 느림 (큐잉)
    cpu = health_status.get("cpu_percent", 0)
    response_time = health_status.get("response_time", 0)
    if cpu < 1.0 and response_time > 3.0:
        return True, f"큐잉 의심 (CPU: {cpu:.1f}%, 응답: {response_time:.1f}초)"

    return False, None

# ===== Ollama 관리 =====
def kill_all_ollama():
    """모든 Ollama 프로세스 종료"""
    try:
        subprocess.run(
            ["powershell", "-Command", "Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force"],
            timeout=10,
            capture_output=True
        )
        time.sleep(2)
        colored_print("Ollama 프로세스 모두 종료", "yellow")
    except Exception as e:
        colored_print(f"Ollama 종료 실패: {e}", "red")

def start_ollama(port):
    """Ollama 시작"""
    try:
        env = os.environ.copy()
        env["OLLAMA_HOST"] = f"127.0.0.1:{port}"

        # 백그라운드 실행
        process = subprocess.Popen(
            [OLLAMA_EXE, "serve"],
            env=env,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        time.sleep(5)  # 초기화 대기

        # 프로세스 확인
        if process.poll() is None:
            colored_print(f"Ollama 포트 {port} 시작 완료 (PID: {process.pid})", "green")
            return process
        else:
            colored_print(f"Ollama 포트 {port} 시작 실패", "red")
            return None

    except Exception as e:
        colored_print(f"Ollama 포트 {port} 시작 오류: {e}", "red")
        return None

def get_ollama_processes():
    """실행 중인 Ollama 프로세스 목록"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info']):
        try:
            if proc.info['name'] == 'ollama.exe':
                processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return processes

# ===== 로그 파서 =====
def parse_trader_log(line, trader_name):
    """트레이더 로그에서 중요 정보 추출 + 텔레그램 알림"""
    line = line.strip()
    if not line:
        return None

    # 중요 키워드 패턴
    important_patterns = [
        r'\[CLOSE\]',
        r'\[TREND_CHANGE\]',
        r'\[BUY\]',
        r'\[SELL\]',
        r'\[PYRAMID\]',
        r'\[LLM 분석 결과\]',
        r'신호:',
        r'신뢰도:',
        r'PNL[:\s]+[+-]?\d+\.?\d*%',
        r'손익[:\s]+[+-]?\d+\.?\d*%',
        r'수익[:\s]+[+-]?\d+\.?\d*%',
        r'포지션.*진입',
        r'청산.*완료',
        r'\[HOLD\].*보유',
    ]

    for pattern in important_patterns:
        if re.search(pattern, line):
            # 텔레그램 알림 (중요 이벤트만)
            if any(keyword in line for keyword in ['TREND_CHANGE', '청산 완료', 'PYRAMID', '진입 완료']):
                telegram.notify_position_change(trader_name, "포지션 변경", line)

            return line

    return None

def log_reader_thread(process, trader_name):
    """트레이더 로그 읽기 스레드"""
    try:
        for line in iter(process.stdout.readline, ''):
            if not line:
                break

            # UTF-8 디코딩
            try:
                decoded_line = line.decode('utf-8', errors='ignore')
            except:
                decoded_line = str(line)

            # 중요 정보 필터링
            important_info = parse_trader_log(decoded_line, trader_name)
            if important_info:
                colored_print(f"[{trader_name}] {important_info}", "magenta")
    except Exception as e:
        colored_print(f"[{trader_name}] 로그 읽기 오류: {e}", "red")

# ===== 트레이더 관리 =====
def start_trader(script_path, python_exe, working_dir, trader_name, ollama_port):
    """트레이더 시작 (로그 캡처)"""
    try:
        env = os.environ.copy()
        env["OLLAMA_HOST"] = f"http://127.0.0.1:{ollama_port}"
        env["PYTHONIOENCODING"] = "utf-8"

        process = subprocess.Popen(
            [python_exe, script_path],
            cwd=working_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW  # 백그라운드 실행
        )

        # 로그 읽기 스레드 시작
        log_thread = threading.Thread(
            target=log_reader_thread,
            args=(process, trader_name),
            daemon=True
        )
        log_thread.start()

        time.sleep(2)

        if process.poll() is None:
            colored_print(f"{trader_name} 시작 완료 (PID: {process.pid}, Ollama: {ollama_port})", "green")
            return process
        else:
            colored_print(f"{trader_name} 시작 실패", "red")
            return None

    except Exception as e:
        colored_print(f"{trader_name} 시작 오류: {e}", "red")
        return None

def stop_process(process, name, timeout=30):
    """프로세스 정상 종료"""
    try:
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=timeout)
                colored_print(f"{name} 정상 종료", "yellow")
            except subprocess.TimeoutExpired:
                process.kill()
                colored_print(f"{name} 강제 종료", "yellow")
        return True
    except Exception as e:
        colored_print(f"{name} 종료 실패: {e}", "red")
        return False

# ===== 메인 관리 루프 =====
def main():
    colored_print("=" * 70, "cyan")
    colored_print("통합 트레이더 관리 시스템 시작", "cyan")
    colored_print(f"재시작 주기: {RESTART_INTERVAL // 3600}시간", "cyan")
    colored_print("=" * 70, "cyan")

    # 텔레그램 시작 알림
    telegram.notify_system_start()

    # 초기 정리
    colored_print("\n[초기화] 기존 프로세스 정리 중...", "yellow")
    kill_all_ollama()

    # Ollama 시작
    colored_print("\n[OLLAMA] 시작 중...", "blue")
    ollama_eth = start_ollama(OLLAMA_PORT_ETH)
    time.sleep(3)
    ollama_kis = start_ollama(OLLAMA_PORT_KIS)

    if not ollama_eth or not ollama_kis:
        colored_print("\n[ERROR] Ollama 시작 실패! 종료합니다.", "red")
        return

    # 트레이더 시작
    colored_print("\n[TRADER] 시작 중...", "blue")
    trader_eth = start_trader(
        ETH_TRADER_SCRIPT,
        ETH_PYTHON,
        ETH_TRADER_DIR,
        "ETH Trader (코드3)",
        OLLAMA_PORT_ETH
    )
    time.sleep(3)

    trader_kis = start_trader(
        KIS_TRADER_SCRIPT,
        KIS_PYTHON,
        KIS_TRADER_DIR,
        "KIS Trader (코드4)",
        OLLAMA_PORT_KIS
    )

    if not trader_eth or not trader_kis:
        colored_print("\n[WARNING] 일부 트레이더 시작 실패", "yellow")

    # 재시작 타이머
    last_restart_time = time.time()
    check_interval = 60  # 1분마다 상태 체크

    colored_print("\n[MONITOR] 모니터링 시작 (Ctrl+C로 종료)\n", "green")

    try:
        while True:
            time.sleep(check_interval)
            current_time = time.time()
            elapsed = current_time - last_restart_time

            # 상태 체크
            eth_alive = trader_eth and trader_eth.poll() is None
            kis_alive = trader_kis and trader_kis.poll() is None

            # Ollama 헬스 체크 (지능적 관리)
            health_eth = check_ollama_health(OLLAMA_PORT_ETH)
            health_kis = check_ollama_health(OLLAMA_PORT_KIS)

            # 응답 시간 기록
            if health_eth.get("response_time"):
                response_times_eth.append(health_eth["response_time"])
            if health_kis.get("response_time"):
                response_times_kis.append(health_kis["response_time"])

            # Ollama 재시작 판단 (ETH)
            need_restart_eth, reason_eth = should_restart_ollama(health_eth, response_times_eth)
            if need_restart_eth:
                colored_print(f"\n[SMART_RESTART] ETH Ollama 재시작 필요: {reason_eth}", "red")
                # telegram.notify_ollama_restart("ETH", reason_eth)  # 메모리 과다 알림 끔
                colored_print("[SMART_RESTART] ETH Trader 종료 중...", "yellow")
                stop_process(trader_eth, "ETH Trader", timeout=10)

                colored_print("[SMART_RESTART] ETH Ollama 재시작 중...", "yellow")
                if ollama_eth and ollama_eth.poll() is None:
                    ollama_eth.terminate()
                    time.sleep(3)
                ollama_eth = start_ollama(OLLAMA_PORT_ETH)
                time.sleep(5)

                colored_print("[SMART_RESTART] ETH Trader 재시작 중...", "green")
                trader_eth = start_trader(
                    ETH_TRADER_SCRIPT,
                    ETH_PYTHON,
                    ETH_TRADER_DIR,
                    "ETH Trader (코드3)",
                    OLLAMA_PORT_ETH
                )
                response_times_eth.clear()

            # Ollama 재시작 판단 (KIS)
            need_restart_kis, reason_kis = should_restart_ollama(health_kis, response_times_kis)
            if need_restart_kis:
                colored_print(f"\n[SMART_RESTART] KIS Ollama 재시작 필요: {reason_kis}", "red")
                # telegram.notify_ollama_restart("KIS", reason_kis)  # 메모리 과다 알림 끔
                colored_print("[SMART_RESTART] KIS Trader 종료 중...", "yellow")
                stop_process(trader_kis, "KIS Trader", timeout=10)

                colored_print("[SMART_RESTART] KIS Ollama 재시작 중...", "yellow")
                if ollama_kis and ollama_kis.poll() is None:
                    ollama_kis.terminate()
                    time.sleep(3)
                ollama_kis = start_ollama(OLLAMA_PORT_KIS)
                time.sleep(5)

                colored_print("[SMART_RESTART] KIS Trader 재시작 중...", "green")
                trader_kis = start_trader(
                    KIS_TRADER_SCRIPT,
                    KIS_PYTHON,
                    KIS_TRADER_DIR,
                    "KIS Trader (코드4)",
                    OLLAMA_PORT_KIS
                )
                response_times_kis.clear()

            # 프로세스 복구 (크래시 시)
            if not eth_alive and not need_restart_eth:
                colored_print("\n[AUTO_RECOVERY] ETH Trader 크래시 → 재시작...", "yellow")
                trader_eth = start_trader(
                    ETH_TRADER_SCRIPT,
                    ETH_PYTHON,
                    ETH_TRADER_DIR,
                    "ETH Trader (코드3)",
                    OLLAMA_PORT_ETH
                )

            if not kis_alive and not need_restart_kis:
                colored_print("\n[AUTO_RECOVERY] KIS Trader 크래시 → 재시작...", "yellow")
                trader_kis = start_trader(
                    KIS_TRADER_SCRIPT,
                    KIS_PYTHON,
                    KIS_TRADER_DIR,
                    "KIS Trader (코드4)",
                    OLLAMA_PORT_KIS
                )

            # 주기적 재시작 (4시간)
            if elapsed >= RESTART_INTERVAL:
                colored_print("\n" + "=" * 70, "magenta")
                colored_print(f"{RESTART_INTERVAL // 3600}시간 경과 → 전체 재시작", "magenta")
                colored_print("=" * 70, "magenta")

                # 1. ETH 트레이더 재시작
                colored_print("\n[RESTART 1/4] ETH Trader 종료 중...", "yellow")
                stop_process(trader_eth, "ETH Trader")
                time.sleep(5)

                # 2. ETH Ollama 재시작
                colored_print("[RESTART 2/4] ETH Ollama 재시작 중...", "yellow")
                if ollama_eth and ollama_eth.poll() is None:
                    ollama_eth.terminate()
                    time.sleep(3)
                ollama_eth = start_ollama(OLLAMA_PORT_ETH)
                time.sleep(5)

                # 3. KIS 트레이더 재시작
                colored_print("[RESTART 3/4] KIS Trader 종료 중...", "yellow")
                stop_process(trader_kis, "KIS Trader")
                time.sleep(5)

                # 4. KIS Ollama 재시작
                colored_print("[RESTART 4/4] KIS Ollama 재시작 중...", "yellow")
                if ollama_kis and ollama_kis.poll() is None:
                    ollama_kis.terminate()
                    time.sleep(3)
                ollama_kis = start_ollama(OLLAMA_PORT_KIS)
                time.sleep(5)

                # 트레이더 재시작
                colored_print("\n[RESTART] 트레이더 재시작 중...", "green")
                trader_eth = start_trader(
                    ETH_TRADER_SCRIPT,
                    ETH_PYTHON,
                    ETH_TRADER_DIR,
                    "ETH Trader (코드3)",
                    OLLAMA_PORT_ETH
                )
                time.sleep(3)

                trader_kis = start_trader(
                    KIS_TRADER_SCRIPT,
                    KIS_PYTHON,
                    KIS_TRADER_DIR,
                    "KIS Trader (코드4)",
                    OLLAMA_PORT_KIS
                )

                last_restart_time = current_time
                colored_print(f"\n[RESTART] 완료! 다음 재시작: {RESTART_INTERVAL // 3600}시간 후", "green")
                colored_print("=" * 70 + "\n", "magenta")

            # 상태 출력 (1분마다)
            colored_print(
                f"[STATUS] ETH: {'OK' if eth_alive else 'DEAD'} "
                f"(Ollama: {health_eth.get('status', 'unknown')}, "
                f"응답: {health_eth.get('response_time', 0):.1f}s, "
                f"메모리: {health_eth.get('memory_mb', 0):.0f}MB) | "
                f"KIS: {'OK' if kis_alive else 'DEAD'} "
                f"(Ollama: {health_kis.get('status', 'unknown')}, "
                f"응답: {health_kis.get('response_time', 0):.1f}s, "
                f"메모리: {health_kis.get('memory_mb', 0):.0f}MB) | "
                f"다음 재시작: {(RESTART_INTERVAL - elapsed) / 3600:.1f}시간 후",
                "cyan"
            )

    except KeyboardInterrupt:
        colored_print("\n\n[SHUTDOWN] 사용자 종료 요청", "yellow")
        colored_print("[SHUTDOWN] 모든 프로세스 종료 중...", "yellow")

        stop_process(trader_eth, "ETH Trader")
        stop_process(trader_kis, "KIS Trader")

        if ollama_eth and ollama_eth.poll() is None:
            ollama_eth.terminate()
        if ollama_kis and ollama_kis.poll() is None:
            ollama_kis.terminate()

        time.sleep(2)
        kill_all_ollama()

        colored_print("[SHUTDOWN] 완료", "green")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        colored_print(f"\n[CRITICAL ERROR] {e}", "red")
        colored_print("[CRITICAL ERROR] 프로세스 정리 중...", "red")
        kill_all_ollama()
