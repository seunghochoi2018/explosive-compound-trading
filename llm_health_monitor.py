#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 헬스 모니터링 및 자동 복구 시스템

ROOT CAUSE (2025-10-15):
=======================
1. KIS: analyze_market_simple() 메서드 존재하지 않음
   - get_llm_signal_7b/14b에서 호출하나 LLMMarketAnalyzer에 없음
   - Exception 발생 → 기본값만 반환 (NEUTRAL/50:50)
   - 로그: "[FORCE] LLM 분석 우회" (실제로는 메서드 없음)

2. ETH: 학습 시스템 통합했으나 실제 작동 확인 필요
   - generate_learned_strategies() 호출 성공 여부 불확실
   - LLM 응답 타임아웃 가능성

SOLUTION (자동 모니터링 및 복구):
==================================
1. LLM 응답 패턴 감지
   - 기본값만 반환: buy=50, sell=50, confidence=50 → 우회 모드
   - 타임아웃: 60초 이상 응답 없음 → Ollama 재시작
   - 실제 분석: 값이 50이 아님 → 정상 작동

2. 자동 복구
   - Ollama 프로세스 재시작
   - 트레이더 재시작 (필요 시)
   - 텔레그램 긴급 알림

3. 로그 패턴 분석
   - kis_trader.log, eth_learning_events.json 실시간 감시
   - FORCE, 우회, 기본값 패턴 감지
"""

import os
import sys
import time
import json
import psutil
import requests
import subprocess
from datetime import datetime, timedelta
from collections import deque
from pathlib import Path

# 텔레그램 알림
sys.path.append(r'C:\Users\user\Documents\코드5')
from telegram_notifier import TelegramNotifier

class LLMHealthMonitor:
    """LLM 헬스 모니터링 및 자동 복구"""

    def __init__(self):
        print("="*80)
        print("LLM 헬스 모니터 시작")
        print("="*80)

        self.telegram = TelegramNotifier()

        # 모니터링 대상
        self.ollama_ports = [11434, 11435, 11436]
        self.eth_log = Path(r"C:\Users\user\Documents\코드3\eth_learning_events.json")
        self.kis_log = Path(r"C:\Users\user\Documents\코드4\kis_trader.log")

        # 상태 추적
        self.llm_bypass_count = {
            'ETH': 0,
            'KIS': 0
        }
        self.last_alert_time = {
            'ETH': None,
            'KIS': None
        }
        self.ollama_restart_count = 0
        self.last_ollama_restart = None

        # 임계값
        self.MAX_BYPASS_COUNT = 5  # 5회 연속 우회면 알림
        self.ALERT_COOLDOWN = 300  # 5분마다 한 번만 알림
        self.CHECK_INTERVAL = 60  # 1분마다 체크

    def check_ollama_health(self) -> dict:
        """Ollama 서버 헬스체크"""
        status = {}

        for port in self.ollama_ports:
            try:
                resp = requests.get(f"http://127.0.0.1:{port}/api/tags", timeout=3)
                if resp.status_code == 200:
                    data = resp.json()
                    models = data.get('models', [])
                    status[port] = {
                        'alive': True,
                        'models': len(models),
                        'model_names': [m.get('name', '') for m in models]
                    }
                else:
                    status[port] = {'alive': False, 'error': f'HTTP {resp.status_code}'}
            except Exception as e:
                status[port] = {'alive': False, 'error': str(e)}

        return status

    def detect_llm_bypass(self, trader: str) -> bool:
        """LLM 우회 모드 감지"""

        if trader == 'ETH':
            # ETH: eth_learning_events.json 최근 10개 이벤트 확인
            if not self.eth_log.exists():
                return False

            try:
                with open(self.eth_log, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                # 최근 10개 이벤트
                recent_events = [json.loads(line) for line in lines[-10:] if line.strip()]

                # 기본값 패턴 감지: buy=50, sell=50, confidence=50
                bypass_count = 0
                for event in recent_events:
                    buy = event.get('7b_buy', 0)
                    sell = event.get('7b_sell', 0)
                    conf = event.get('7b_confidence', 0)

                    # 모두 50이면 기본값 (우회 모드)
                    if buy == 50 and sell == 50 and conf == 50:
                        bypass_count += 1

                # 10개 중 7개 이상이 기본값이면 우회 모드
                return bypass_count >= 7

            except Exception as e:
                print(f"[WARN] ETH 로그 분석 실패: {e}")
                return False

        elif trader == 'KIS':
            # KIS: kis_trader.log에서 FORCE 패턴 검색
            if not self.kis_log.exists():
                return False

            try:
                # 최근 100줄 읽기
                with open(self.kis_log, 'r', encoding='utf-8') as f:
                    lines = deque(f, maxlen=100)

                # FORCE 패턴 개수 세기
                force_count = sum(1 for line in lines if 'FORCE' in line or '우회' in line)

                # 최근 100줄 중 5개 이상 FORCE면 우회 모드
                return force_count >= 5

            except Exception as e:
                print(f"[WARN] KIS 로그 분석 실패: {e}")
                return False

        return False

    def restart_ollama(self) -> bool:
        """Ollama 재시작"""
        try:
            print("[AUTO-RESTART] Ollama 재시작 시작...")

            # 1. 모든 Ollama 프로세스 종료
            for proc in psutil.process_iter(['name']):
                try:
                    if 'ollama' in proc.info['name'].lower():
                        print(f"  [KILL] Ollama PID {proc.pid} 종료")
                        proc.kill()
                except:
                    pass

            time.sleep(3)

            # 2. Ollama 서버 시작
            ollama_path = r"C:\Users\user\AppData\Local\Programs\Ollama\ollama.exe"

            if not os.path.exists(ollama_path):
                print(f"[ERROR] Ollama 실행 파일 없음: {ollama_path}")
                return False

            subprocess.Popen(
                [ollama_path, "serve"],
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            print("[AUTO-RESTART] Ollama 재시작 완료, 10초 대기...")
            time.sleep(10)

            # 3. 헬스체크
            status = self.check_ollama_health()
            alive_count = sum(1 for s in status.values() if s.get('alive', False))

            print(f"[HEALTH] Ollama 포트: {alive_count}/{len(self.ollama_ports)} 정상")

            self.ollama_restart_count += 1
            self.last_ollama_restart = datetime.now()

            return alive_count > 0

        except Exception as e:
            print(f"[ERROR] Ollama 재시작 실패: {e}")
            return False

    def send_alert(self, trader: str, issue: str):
        """텔레그램 알림"""

        # 쿨다운 체크
        if self.last_alert_time.get(trader):
            elapsed = (datetime.now() - self.last_alert_time[trader]).total_seconds()
            if elapsed < self.ALERT_COOLDOWN:
                print(f"[COOLDOWN] {trader} 알림 쿨다운 중 ({int(elapsed)}초 경과)")
                return

        message = f"""[CRITICAL] {trader} LLM 우회 감지!

문제: {issue}

우회 횟수: {self.llm_bypass_count[trader]}회
Ollama 재시작: {self.ollama_restart_count}회

자동 복구:
1. Ollama 서버 재시작 시도 중...
2. LLM 응답 모니터링 중...

시간: {datetime.now().strftime('%H:%M:%S')}"""

        self.telegram.send_message(message, priority="important")
        self.last_alert_time[trader] = datetime.now()

    def run(self):
        """메인 모니터링 루프"""
        print("\n[시작] LLM 헬스 모니터링")

        cycle = 0

        while True:
            try:
                cycle += 1
                now = datetime.now().strftime("%H:%M:%S")

                print(f"\n[{now}] ========== Cycle {cycle} ==========")

                # 1. Ollama 헬스체크
                ollama_status = self.check_ollama_health()
                alive_ports = [p for p, s in ollama_status.items() if s.get('alive', False)]

                print(f"[OLLAMA] 정상 포트: {alive_ports}/{self.ollama_ports}")

                if len(alive_ports) == 0:
                    print("[CRITICAL] Ollama 전체 다운!")
                    self.restart_ollama()

                # 2. ETH LLM 우회 감지
                eth_bypass = self.detect_llm_bypass('ETH')
                if eth_bypass:
                    self.llm_bypass_count['ETH'] += 1
                    print(f"[BYPASS] ETH LLM 우회 모드 감지! (누적: {self.llm_bypass_count['ETH']}회)")

                    if self.llm_bypass_count['ETH'] >= self.MAX_BYPASS_COUNT:
                        self.send_alert('ETH', 'LLM이 기본값만 반환 (50:50:50)')
                        self.restart_ollama()
                        self.llm_bypass_count['ETH'] = 0
                else:
                    self.llm_bypass_count['ETH'] = max(0, self.llm_bypass_count['ETH'] - 1)
                    print(f"[OK] ETH LLM 정상 작동 중")

                # 3. KIS LLM 우회 감지
                kis_bypass = self.detect_llm_bypass('KIS')
                if kis_bypass:
                    self.llm_bypass_count['KIS'] += 1
                    print(f"[BYPASS] KIS LLM 우회 모드 감지! (누적: {self.llm_bypass_count['KIS']}회)")

                    if self.llm_bypass_count['KIS'] >= self.MAX_BYPASS_COUNT:
                        self.send_alert('KIS', 'analyze_market_simple() 메서드 없음')
                        self.restart_ollama()
                        self.llm_bypass_count['KIS'] = 0
                else:
                    self.llm_bypass_count['KIS'] = max(0, self.llm_bypass_count['KIS'] - 1)
                    print(f"[OK] KIS LLM 정상 작동 중")

                # 대기
                time.sleep(self.CHECK_INTERVAL)

            except KeyboardInterrupt:
                print("\n[STOP] 사용자 중단")
                break
            except Exception as e:
                print(f"[ERROR] 메인 루프: {e}")
                time.sleep(self.CHECK_INTERVAL)


if __name__ == "__main__":
    monitor = LLMHealthMonitor()
    monitor.run()
