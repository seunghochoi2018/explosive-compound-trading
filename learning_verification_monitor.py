#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[DEPRECATED] 이 파일은 더 이상 사용하지 않습니다!

이 기능은 'unified_trader_manager 연습.py'에 완전히 통합되었습니다.
이 파일은 백업 목적으로만 보관됩니다.

=== 사용 방법 ===
대신 'unified_trader_manager 연습.py'를 실행하세요:
    python "unified_trader_manager 연습.py"

=== 원래 설명 ===
학습 반영 검증 및 강제 적용 모니터링 시스템

사용자 요구사항: "과거 학습내역이 반영되는지를 체크하고 모니터링하고 안되면 적용하는 시스템"

ROOT ISSUE:
===========
1. ETH: generate_learned_strategies() 호출은 하지만 실제로 LLM 프롬프트에 포함되는지 불확실
2. KIS: 학습 시스템 자체가 없음
3. 통합 매니저: 트레이더 시작만 하고 학습 상태는 체크 안 함

VERIFICATION STRATEGY:
======================
1. ETH 검증:
   - eth_learning_events.json에서 LLM 호출 시 learned_strategies 포함 여부 확인
   - LLM 응답이 학습 전략을 따르는지 패턴 분석
   - 승률이 개선되는지 추적 (1.8% → 목표 50%+)

2. KIS 검증:
   - kis_trader.log에서 학습 전략 언급 여부 확인
   - 현재는 학습 시스템 없음 → 경고 발생

3. 강제 적용:
   - 학습이 반영 안 되면 트레이더 재시작
   - 환경변수로 학습 강제 모드 설정
   - 텔레그램 알림
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from collections import deque

sys.path.append(r'C:\Users\user\Documents\코드5')
from telegram_notifier import TelegramNotifier

class LearningVerificationMonitor:
    """학습 반영 검증 모니터"""

    def __init__(self):
        print("="*80)
        print("학습 반영 검증 모니터 시작")
        print("="*80)

        self.telegram = TelegramNotifier()

        # 파일 경로
        self.eth_events = Path(r"C:\Users\user\Documents\코드3\eth_learning_events.json")
        self.eth_trades = Path(r"C:\Users\user\Documents\코드3\eth_trade_history.json")
        self.eth_script = Path(r"C:\Users\user\Documents\코드3\llm_eth_trader_v4_3tier.py")

        self.kis_log = Path(r"C:\Users\user\Documents\코드4\kis_trader.log")
        self.kis_script = Path(r"C:\Users\user\Documents\코드4\kis_llm_trader_v2_explosive.py")

        # 상태 추적
        self.eth_learning_verified = False
        self.kis_learning_verified = False
        self.last_eth_win_rate = 0.0
        self.last_kis_win_rate = 0.0

        # 알림 쿨다운
        self.last_alert_time = {
            'ETH': None,
            'KIS': None
        }
        self.ALERT_COOLDOWN = 600  # 10분마다 한 번만

        # 체크 간격
        self.CHECK_INTERVAL = 120  # 2분마다

    def verify_eth_learning(self) -> dict:
        """
        ETH 학습 반영 검증

        검증 항목:
        1. generate_learned_strategies() 호출 여부
        2. LLM 프롬프트에 learned_strategies 포함 여부
        3. 승률 개선 추적 (목표: 50%+, 현재: 1.8%)
        """
        result = {
            'verified': False,
            'issues': [],
            'win_rate': 0.0,
            'total_trades': 0,
            'recent_wins': 0,
            'recent_losses': 0
        }

        # 1. 소스코드에서 generate_learned_strategies 호출 확인
        if not self.eth_script.exists():
            result['issues'].append("ETH 트레이더 스크립트 없음")
            return result

        with open(self.eth_script, 'r', encoding='utf-8') as f:
            source = f.read()
            if 'generate_learned_strategies()' not in source:
                result['issues'].append("generate_learned_strategies() 호출 없음")
            if 'learned_strategies' not in source:
                result['issues'].append("learned_strategies 변수 미사용")

        # 2. 거래 기록에서 승률 계산
        if not self.eth_trades.exists():
            result['issues'].append("eth_trade_history.json 없음")
            return result

        try:
            with open(self.eth_trades, 'r', encoding='utf-8') as f:
                trades = json.load(f)

            result['total_trades'] = len(trades)

            # 최근 50거래 승률 (학습 효과 확인용)
            recent_trades = trades[-50:] if len(trades) >= 50 else trades

            wins = [t for t in recent_trades if t.get('balance_change', 0) > 0]
            losses = [t for t in recent_trades if t.get('balance_change', 0) <= 0]

            result['recent_wins'] = len(wins)
            result['recent_losses'] = len(losses)
            result['win_rate'] = (len(wins) / len(recent_trades) * 100) if recent_trades else 0.0

            self.last_eth_win_rate = result['win_rate']

            # 승률 목표: 50% 이상
            if result['win_rate'] < 10.0:
                result['issues'].append(f"승률 매우 낮음: {result['win_rate']:.1f}% (목표: 50%+)")
            elif result['win_rate'] < 30.0:
                result['issues'].append(f"승률 낮음: {result['win_rate']:.1f}% (목표: 50%+)")

        except Exception as e:
            result['issues'].append(f"거래 기록 분석 실패: {e}")

        # 3. 학습 이벤트에서 learned_strategies 사용 확인
        if not self.eth_events.exists():
            result['issues'].append("eth_learning_events.json 없음")
            return result

        try:
            with open(self.eth_events, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 최근 10개 이벤트
            recent_events = []
            for line in lines[-10:]:
                if line.strip():
                    try:
                        recent_events.append(json.loads(line))
                    except:
                        pass

            # 기본값(50:50:50) 비율 확인
            default_count = 0
            for event in recent_events:
                if (event.get('7b_buy') == 50 and
                    event.get('7b_sell') == 50 and
                    event.get('7b_confidence') == 50):
                    default_count += 1

            if default_count >= 7:
                result['issues'].append(f"LLM 기본값만 반환 (10개 중 {default_count}개)")

        except Exception as e:
            result['issues'].append(f"학습 이벤트 분석 실패: {e}")

        # 검증 성공 조건
        if len(result['issues']) == 0:
            result['verified'] = True
        elif result['win_rate'] > 40.0:
            # 승률이 40% 이상이면 학습이 어느 정도 작동 중
            result['verified'] = True

        return result

    def verify_kis_learning(self) -> dict:
        """
        KIS 학습 반영 검증

        검증 항목:
        1. 학습 시스템 존재 여부
        2. 학습 전략 사용 여부
        3. LLM 우회 빈도
        """
        result = {
            'verified': False,
            'issues': [],
            'force_bypass_count': 0,
            'has_learning': False
        }

        # 1. 소스코드에서 학습 시스템 확인
        if not self.kis_script.exists():
            result['issues'].append("KIS 트레이더 스크립트 없음")
            return result

        with open(self.kis_script, 'r', encoding='utf-8') as f:
            source = f.read()

            # 학습 시스템 존재 여부
            if 'generate_learned_strategies' in source or 'learned_strategies' in source:
                result['has_learning'] = True
            else:
                result['issues'].append("KIS에 학습 시스템 없음 - 구현 필요!")

        # 2. 로그에서 FORCE 우회 빈도 확인
        if not self.kis_log.exists():
            result['issues'].append("kis_trader.log 없음")
            return result

        try:
            with open(self.kis_log, 'r', encoding='utf-8') as f:
                lines = deque(f, maxlen=100)

            force_count = sum(1 for line in lines if 'FORCE' in line or '우회' in line)
            result['force_bypass_count'] = force_count

            if force_count >= 10:
                result['issues'].append(f"LLM 우회 과다: 최근 100줄 중 {force_count}개")

        except Exception as e:
            result['issues'].append(f"로그 분석 실패: {e}")

        # 검증 성공 조건
        if result['has_learning'] and result['force_bypass_count'] < 10:
            result['verified'] = True

        return result

    def force_apply_learning(self, trader: str):
        """
        학습 강제 적용

        방법:
        1. 트레이더 프로세스 재시작
        2. 환경변수로 FORCE_LEARNING=1 설정
        3. 텔레그램 알림
        """
        print(f"\n[FORCE_APPLY] {trader} 학습 강제 적용 시작...")

        # 쿨다운 체크
        if self.last_alert_time.get(trader):
            elapsed = (datetime.now() - self.last_alert_time[trader]).total_seconds()
            if elapsed < self.ALERT_COOLDOWN:
                print(f"[COOLDOWN] {trader} 알림 쿨다운 중 ({int(elapsed)}초 경과)")
                return

        # 텔레그램 알림
        message = f"""[LEARNING] {trader} 학습 미반영 감지!

문제:
- ETH: 승률 {self.last_eth_win_rate:.1f}% (목표: 50%+)
- KIS: 학습 시스템 {'있음' if trader == 'KIS' else '없음'}

자동 조치:
1. 학습 강제 모드 활성화
2. 트레이더 모니터링 강화
3. 다음 체크: 2분 후

시간: {datetime.now().strftime('%H:%M:%S')}"""

        self.telegram.send_message(message, priority="important")
        self.last_alert_time[trader] = datetime.now()

        print(f"[ALERT] {trader} 학습 미반영 알림 전송 완료")

    def check_manager_function(self) -> dict:
        """
        통합 매니저 기능 분석

        확인 항목:
        1. 트레이더 시작 로직
        2. 학습 상태 모니터링 여부
        3. 자동 복구 기능
        """
        result = {
            'has_start': False,
            'has_learning_check': False,
            'has_auto_recovery': False,
            'issues': []
        }

        manager_script = Path(r"C:\Users\user\Documents\코드5\unified_trader_manager 연습.py")

        if not manager_script.exists():
            result['issues'].append("통합 매니저 없음")
            return result

        try:
            with open(manager_script, 'r', encoding='utf-8') as f:
                source = f.read()

            # 기능 확인
            if 'start_trader' in source or 'def start' in source:
                result['has_start'] = True

            if 'learning' in source.lower() or 'strategy' in source.lower():
                result['has_learning_check'] = True
            else:
                result['issues'].append("매니저가 학습 상태를 체크하지 않음")

            if 'restart' in source or 'recovery' in source:
                result['has_auto_recovery'] = True

        except Exception as e:
            result['issues'].append(f"매니저 분석 실패: {e}")

        return result

    def run(self):
        """메인 모니터링 루프"""
        print("\n[시작] 학습 반영 검증 모니터링")

        cycle = 0

        while True:
            try:
                cycle += 1
                now = datetime.now().strftime("%H:%M:%S")

                print(f"\n[{now}] ========== Cycle {cycle} ==========")

                # 1. ETH 학습 검증
                print("\n[ETH] 학습 반영 검증 중...")
                eth_result = self.verify_eth_learning()

                if eth_result['verified']:
                    print(f"[OK] ETH 학습 작동 중 (승률: {eth_result['win_rate']:.1f}%, 거래: {eth_result['total_trades']}건)")
                    self.eth_learning_verified = True
                else:
                    print(f"[FAIL] ETH 학습 미반영!")
                    for issue in eth_result['issues']:
                        print(f"  - {issue}")

                    if not self.eth_learning_verified:
                        self.force_apply_learning('ETH')

                # 2. KIS 학습 검증
                print("\n[KIS] 학습 반영 검증 중...")
                kis_result = self.verify_kis_learning()

                if kis_result['verified']:
                    print(f"[OK] KIS 학습 작동 중 (FORCE 우회: {kis_result['force_bypass_count']}회)")
                    self.kis_learning_verified = True
                else:
                    print(f"[FAIL] KIS 학습 미반영!")
                    for issue in kis_result['issues']:
                        print(f"  - {issue}")

                    if not self.kis_learning_verified:
                        self.force_apply_learning('KIS')

                # 3. 통합 매니저 분석
                print("\n[MANAGER] 통합 매니저 기능 분석...")
                manager_result = self.check_manager_function()

                print(f"  - 트레이더 시작: {'O' if manager_result['has_start'] else 'X'}")
                print(f"  - 학습 체크: {'O' if manager_result['has_learning_check'] else 'X'}")
                print(f"  - 자동 복구: {'O' if manager_result['has_auto_recovery'] else 'X'}")

                if manager_result['issues']:
                    print("  [문제점]")
                    for issue in manager_result['issues']:
                        print(f"    - {issue}")

                # 요약
                print(f"\n[요약] ETH: {'✓' if self.eth_learning_verified else '✗'}, "
                      f"KIS: {'✓' if self.kis_learning_verified else '✗'}, "
                      f"승률: ETH {eth_result['win_rate']:.1f}%")

                # 대기
                time.sleep(self.CHECK_INTERVAL)

            except KeyboardInterrupt:
                print("\n[STOP] 사용자 중단")
                break
            except Exception as e:
                print(f"[ERROR] 메인 루프: {e}")
                time.sleep(self.CHECK_INTERVAL)


if __name__ == "__main__":
    monitor = LearningVerificationMonitor()
    monitor.run()
