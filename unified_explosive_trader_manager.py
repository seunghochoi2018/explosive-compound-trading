#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합 복리 폭발 트레이더 매니저

기능:
1. ETH + KIS 봇 통합 관리
2. Ollama 메모리 관리 (순차 실행)
3. 실시간 모니터링
4. 자동 재시작
5. 원클릭 실행

전략:
- ETH: qwen2.5:7b (메모리 4.5GB)
- KIS: qwen2.5:14b × 2 병렬 (메모리 8GB × 2)
- 동시 실행 불가 → 순차 실행 또는 시간대 분리
"""
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import time
import json
import subprocess
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import deque

import sys
sys.path.append('C:/Users/user/Documents/코드3')
sys.path.append('C:/Users/user/Documents/코드4')

from telegram_notifier import TelegramNotifier

class UnifiedExplosiveManager:
    """통합 폭발 매니저"""

    def __init__(self):
        print("="*80)
        print("통합 복리 폭발 트레이더 매니저 v1.0")
        print("="*80)
        print("기능:")
        print("  1. ETH + KIS 통합 실행")
        print("  2. Ollama 메모리 관리")
        print("  3. 실시간 모니터링")
        print("  4. 자동 재시작")
        print("="*80)

        self.telegram = TelegramNotifier()

        # 봇 프로세스
        self.eth_process = None
        self.kis_process = None
        self.monitor_process = None
        self.learner_process = None

        # 실행 전략
        self.strategy = "sequential"  # "sequential" or "time_split"

        # 메모리 체크
        self.check_ollama_memory()

        # 상태 추적
        self.stats = {
            'eth': {'running': False, 'last_check': None, 'trades': 0},
            'kis': {'running': False, 'last_check': None, 'trades': 0},
            'monitor': {'running': False, 'last_check': None}
        }

        # 로그 파일
        self.log_file = "unified_manager.log"

        print("\n[초기화 완료]")
        self.telegram.send_message(
            "🚀 통합 매니저 시작\n\n"
            "전략: Ollama 메모리 관리\n"
            "ETH: 복리 +4,654%\n"
            "KIS: 연 +2,634%"
        )

    def check_ollama_memory(self):
        """Ollama 메모리 체크 (비차단)"""
        print("\n[메모리 체크] Ollama 모델 확인...")

        try:
            # Ollama 모델 리스트 확인 (짧은 타임아웃)
            result = subprocess.run(
                ['C:/Users/user/AppData/Local/Programs/Ollama/ollama.exe', 'list'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=3  # 3초로 단축
            )

            if result.returncode == 0:
                print(f"[OK] Ollama 실행 중")

                # 메모리 추정
                if 'qwen2.5:7b' in result.stdout:
                    print("  - qwen2.5:7b: ~4.5GB (ETH용)")
                if 'qwen2.5:14b' in result.stdout:
                    print("  - qwen2.5:14b: ~8GB (KIS용)")

                print("\n[전략] 순차 실행")
                print("  방법: ETH 30분 → KIS 30분 → 교대 실행")

            else:
                print(f"[WARNING] Ollama 확인 실패 (계속 진행)")

        except subprocess.TimeoutExpired:
            print(f"[WARNING] Ollama 응답 없음 (3초 초과) - 건너뜀")
        except FileNotFoundError:
            print(f"[WARNING] Ollama 실행파일 없음 - 건너뜀")
        except Exception as e:
            print(f"[WARNING] 메모리 체크 건너뜀: {e}")

        # 항상 계속 진행
        print("[OK] 체크 완료, 시작합니다")

    def start_eth_bot(self):
        """ETH 봇 시작"""
        print("\n[ETH 봇 시작]")

        try:
            self.eth_process = subprocess.Popen(
                [
                    sys.executable,
                    'C:/Users/user/Documents/코드3/llm_eth_trader_v3_explosive.py'
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )

            self.stats['eth']['running'] = True
            self.stats['eth']['last_check'] = datetime.now()

            print(f"[OK] ETH 봇 PID: {self.eth_process.pid}")
            self.log(f"ETH 봇 시작 (PID: {self.eth_process.pid})")

            self.telegram.send_message("✅ ETH 봇 시작")

            return True

        except Exception as e:
            print(f"[ERROR] ETH 봇 시작 실패: {e}")
            self.log(f"ETH 봇 시작 실패: {e}")
            return False

    def start_kis_bot(self):
        """KIS 봇 시작"""
        print("\n[KIS 봇 시작]")

        try:
            self.kis_process = subprocess.Popen(
                [
                    sys.executable,
                    'C:/Users/user/Documents/코드4/kis_llm_trader_v2_explosive.py'
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )

            self.stats['kis']['running'] = True
            self.stats['kis']['last_check'] = datetime.now()

            print(f"[OK] KIS 봇 PID: {self.kis_process.pid}")
            self.log(f"KIS 봇 시작 (PID: {self.kis_process.pid})")

            self.telegram.send_message("✅ KIS 봇 시작")

            return True

        except Exception as e:
            print(f"[ERROR] KIS 봇 시작 실패: {e}")
            self.log(f"KIS 봇 시작 실패: {e}")
            return False

    def start_monitor(self):
        """모니터 시작"""
        print("\n[모니터 시작]")

        try:
            self.monitor_process = subprocess.Popen(
                [
                    sys.executable,
                    'C:/Users/user/Documents/코드4/continuous_learning_monitor.py'
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )

            self.stats['monitor']['running'] = True
            self.stats['monitor']['last_check'] = datetime.now()

            print(f"[OK] 모니터 PID: {self.monitor_process.pid}")
            self.log(f"모니터 시작 (PID: {self.monitor_process.pid})")

            return True

        except Exception as e:
            print(f"[ERROR] 모니터 시작 실패: {e}")
            return False

    def start_learner(self):
        """연속 학습기 시작"""
        print("\n[연속 학습기 시작]")

        try:
            self.learner_process = subprocess.Popen(
                [
                    sys.executable,
                    'C:/Users/user/Documents/코드5/continuous_strategy_learner.py'
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )

            print(f"[OK] 학습기 PID: {self.learner_process.pid}")
            self.log(f"연속 학습기 시작 (PID: {self.learner_process.pid})")

            self.telegram.send_message(
                "🧠 연속 학습 시작\n\n"
                "백그라운드에서 과거 데이터 분석\n"
                "획기적 전략 발견 시 자동 교체"
            )

            return True

        except Exception as e:
            print(f"[ERROR] 학습기 시작 실패: {e}")
            return False

    def stop_bot(self, bot_name: str):
        """봇 중지"""
        print(f"\n[{bot_name} 중지]")

        try:
            if bot_name == 'eth' and self.eth_process:
                self.eth_process.terminate()
                self.eth_process.wait(timeout=10)
                self.stats['eth']['running'] = False
                print(f"[OK] ETH 봇 중지")
                self.log(f"ETH 봇 중지")

            elif bot_name == 'kis' and self.kis_process:
                self.kis_process.terminate()
                self.kis_process.wait(timeout=10)
                self.stats['kis']['running'] = False
                print(f"[OK] KIS 봇 중지")
                self.log(f"KIS 봇 중지")

        except Exception as e:
            print(f"[ERROR] {bot_name} 중지 실패: {e}")

    def sequential_execution_loop(self):
        """
        순차 실행 루프 (최적화)

        전략:
        1. ETH 3분 실행
        2. ETH 중지 + Ollama 메모리 해제 (3초)
        3. KIS 3분 실행
        4. KIS 중지 + Ollama 메모리 해제 (3초)
        5. 반복

        이유:
        - 3분 교대 → 각 봇이 6분마다 기회 포착 ⚡
        - 신호 놓칠 확률 최소화
        - 메모리 안전하게 관리
        - 1시간에 각 봇이 10번 체크!
        """
        print("\n[전략] ⚡ 초고속 순차 실행 모드")
        print("  ETH 3분 → KIS 3분 → 빠른 교대")
        print("  각 봇이 6분마다 신호 체크")
        print("  1시간에 각 봇 10회 기회!")

        # 연속 학습기 시작 (백그라운드)
        print("\n[백그라운드] 연속 학습기 시작")
        self.start_learner()
        time.sleep(3)

        cycle = 0
        eth_runs = 0
        kis_runs = 0

        while True:
            try:
                cycle += 1
                print(f"\n{'='*80}")
                print(f"[사이클 {cycle}] {datetime.now().strftime('%H:%M:%S')}")
                print(f"{'='*80}")

                # 1. ETH 3분
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ⚡ ETH 봇 실행 (3분)")
                self.start_eth_bot()
                eth_runs += 1

                # 3분 대기 (1분마다 상태 체크)
                for i in range(3):
                    time.sleep(60)  # 1분

                    # 프로세스 살아있는지 체크
                    if self.eth_process and self.eth_process.poll() is not None:
                        print(f"[WARNING] ETH 봇 종료됨 (재시작)")
                        self.start_eth_bot()

                    print(f"  ETH 실행 중... {i+1}/3분")

                # 2. ETH 중지
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ETH 중지")
                self.stop_bot('eth')

                # Ollama 메모리 해제 대기 (짧게)
                time.sleep(3)

                # 3. KIS 3분
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ⚡ KIS 봇 실행 (3분)")
                self.start_kis_bot()
                kis_runs += 1

                # 3분 대기
                for i in range(3):
                    time.sleep(60)

                    if self.kis_process and self.kis_process.poll() is not None:
                        print(f"[WARNING] KIS 봇 종료됨 (재시작)")
                        self.start_kis_bot()

                    print(f"  KIS 실행 중... {i+1}/3분")

                # 4. KIS 중지
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] KIS 중지")
                self.stop_bot('kis')

                # 메모리 해제 대기
                time.sleep(3)

                # 사이클 통계
                print(f"\n[사이클 {cycle} 완료] ETH: {eth_runs}회, KIS: {kis_runs}회")

                # 30분마다 텔레그램 알림 (10사이클 = 60분)
                if cycle % 10 == 0:
                    self.telegram.send_message(
                        f"⚡ 1시간 완료\n"
                        f"사이클: {cycle}\n"
                        f"ETH: {eth_runs}회 (6분마다)\n"
                        f"KIS: {kis_runs}회 (6분마다)"
                    )

            except KeyboardInterrupt:
                print("\n[종료] 사용자 중단")
                self.cleanup()
                break

            except Exception as e:
                print(f"[ERROR] 사이클 실행 오류: {e}")
                self.log(f"사이클 오류: {e}")
                time.sleep(60)

    def parallel_execution_loop(self):
        """
        병렬 실행 루프 (메모리 충분할 때만)

        조건: RAM 32GB 이상
        """
        print("\n[전략] 병렬 실행 모드")
        print("  ETH + KIS 동시 실행")
        print("  [WARNING] 메모리 부족 시 순차 모드 권장")

        # 모든 봇 시작
        self.start_eth_bot()
        time.sleep(5)
        self.start_kis_bot()
        time.sleep(5)
        self.start_monitor()

        # 모니터링 루프
        while True:
            try:
                # 프로세스 상태 체크
                if self.eth_process and self.eth_process.poll() is not None:
                    print(f"[WARNING] ETH 봇 종료 (재시작)")
                    self.start_eth_bot()

                if self.kis_process and self.kis_process.poll() is not None:
                    print(f"[WARNING] KIS 봇 종료 (재시작)")
                    self.start_kis_bot()

                if self.monitor_process and self.monitor_process.poll() is not None:
                    print(f"[WARNING] 모니터 종료 (재시작)")
                    self.start_monitor()

                time.sleep(60)

            except KeyboardInterrupt:
                print("\n[종료] 사용자 중단")
                self.cleanup()
                break

    def cleanup(self):
        """정리"""
        print("\n[정리] 모든 프로세스 종료...")

        if self.eth_process:
            self.stop_bot('eth')

        if self.kis_process:
            self.stop_bot('kis')

        if self.monitor_process:
            try:
                self.monitor_process.terminate()
                self.monitor_process.wait(timeout=10)
            except:
                pass

        if self.learner_process:
            try:
                self.learner_process.terminate()
                self.learner_process.wait(timeout=10)
                print("[OK] 학습기 종료")
            except:
                pass

        print("[OK] 정리 완료")
        self.telegram.send_message("⚠️ 통합 매니저 종료")

    def log(self, message: str):
        """로그 저장"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"[{timestamp}] {message}\n")
        except:
            pass

    def run(self, auto_mode=False):
        """메인 실행"""
        print("\n[시작] 통합 매니저 실행")

        if auto_mode:
            # 자동 모드: 순차 실행
            print("\n[자동 모드] 순차 실행 시작")
            print("  ETH 30분 → KIS 30분 → 교대")
            self.strategy = "sequential"
            self.sequential_execution_loop()
        else:
            # 수동 모드: 사용자 선택
            print("\n[전략 선택]")
            print("1. 순차 실행 (권장) - ETH 30분 → KIS 30분 교대")
            print("2. 병렬 실행 (RAM 32GB+) - 동시 실행")

            choice = input("\n선택 (1/2, 기본=1): ").strip() or "1"

            if choice == "1":
                self.strategy = "sequential"
                self.sequential_execution_loop()
            else:
                self.strategy = "parallel"
                self.parallel_execution_loop()

if __name__ == "__main__":
    import sys

    # 커맨드 라인 인자 체크
    auto_mode = "--auto" in sys.argv or "-a" in sys.argv

    manager = UnifiedExplosiveManager()
    manager.run(auto_mode=auto_mode)
