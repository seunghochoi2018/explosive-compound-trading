#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합 트레이더 관리 시스템 (간소화)
- Ollama 1개 공유 사용 (11434)
- ETH + KIS 트레이더 동시 실행
"""
import subprocess
import time
import os
from datetime import datetime

# ===== 설정 =====
OLLAMA_EXE = r"C:\Users\user\AppData\Local\Programs\Ollama\ollama.exe"
OLLAMA_PORT = 11434  # 공유 포트

ETH_TRADER_DIR = r"C:\Users\user\Documents\코드3"
ETH_TRADER_SCRIPT = r"C:\Users\user\Documents\코드3\llm_eth_trader_v3_explosive.py"
ETH_PYTHON = r"C:\Users\user\PycharmProjects\PythonProject\.venv\Scripts\python.exe"

KIS_TRADER_DIR = r"C:\Users\user\Documents\코드4"
KIS_TRADER_SCRIPT = r"C:\Users\user\Documents\코드4\kis_llm_trader_v2_explosive.py"
KIS_PYTHON = r"C:\Users\user\AppData\Local\Programs\Python\Python311\python.exe"

def print_log(message, color="white"):
    """색상 로그 출력"""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "cyan": "\033[96m",
        "reset": "\033[0m"
    }
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{colors.get(color, colors['white'])}[{timestamp}] {message}{colors['reset']}")

def start_trader(script_path, python_exe, working_dir, trader_name, ollama_port):
    """트레이더 시작"""
    try:
        env = os.environ.copy()
        env["OLLAMA_HOST"] = f"http://127.0.0.1:{ollama_port}"
        env["PYTHONIOENCODING"] = "utf-8"

        process = subprocess.Popen(
            [python_exe, script_path],
            cwd=working_dir,
            env=env,
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
        )

        time.sleep(2)

        if process.poll() is None:
            print_log(f"{trader_name} 시작 완료 (PID: {process.pid})", "green")
            return process
        else:
            print_log(f"{trader_name} 시작 실패", "red")
            return None

    except Exception as e:
        print_log(f"{trader_name} 시작 오류: {e}", "red")
        return None

def main():
    print_log("=" * 60, "cyan")
    print_log("통합 트레이더 관리 시스템 (간소화)", "cyan")
    print_log("=" * 60, "cyan")

    # Ollama는 이미 실행 중이라고 가정 (수동 시작 필요)
    print_log(f"\n[INFO] Ollama가 포트 {OLLAMA_PORT}에서 실행 중이어야 합니다", "yellow")
    print_log("[INFO] Ollama가 없다면: ollama serve 실행", "yellow")

    time.sleep(2)

    # 트레이더 시작
    print_log("\n[TRADER] 시작 중...", "blue")

    trader_eth = start_trader(
        ETH_TRADER_SCRIPT,
        ETH_PYTHON,
        ETH_TRADER_DIR,
        "ETH Trader (코드3)",
        OLLAMA_PORT
    )

    time.sleep(3)

    trader_kis = start_trader(
        KIS_TRADER_SCRIPT,
        KIS_PYTHON,
        KIS_TRADER_DIR,
        "KIS Trader (코드4)",
        OLLAMA_PORT
    )

    if trader_eth or trader_kis:
        print_log("\n[SUCCESS] 트레이더 시작 완료!", "green")
        print_log("[INFO] 각 트레이더는 독립 콘솔에서 실행 중입니다", "cyan")
        print_log("[INFO] 종료하려면 각 콘솔을 닫거나 Ctrl+C 누르세요", "cyan")
    else:
        print_log("\n[ERROR] 모든 트레이더 시작 실패", "red")

    # 프로세스 모니터링 (간단)
    try:
        while True:
            time.sleep(60)
            eth_alive = trader_eth and trader_eth.poll() is None
            kis_alive = trader_kis and trader_kis.poll() is None
            print_log(f"[STATUS] ETH: {'OK' if eth_alive else 'DEAD'} | KIS: {'OK' if kis_alive else 'DEAD'}", "cyan")

            if not eth_alive and not kis_alive:
                print_log("[INFO] 모든 트레이더 종료됨", "yellow")
                break

    except KeyboardInterrupt:
        print_log("\n[SHUTDOWN] 사용자 종료 요청", "yellow")

if __name__ == "__main__":
    main()
