#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
완전한 거래 데모 - 실제 매수/매도 사이클 확인
- 시뮬레이션된 실시간 가격 변동
- 실제 보유 기간 및 매도 조건
- 완전한 학습 사이클

*** FMP API 구조 사용 + 변동성 시뮬레이션 ***
"""

import time
import requests
import numpy as np
from datetime import datetime, timedelta

class CompleteTradingDemo:
    def __init__(self, api_key: str):
        """완전한 거래 데모"""
        print("=== 완전한 거래 데모 ===")
        print("실제 매수/매도 사이클 확인")
        print("실시간 가격 변동 + 학습")
        print()

        # API 설정
        self.api_key = api_key
        self.base_url = "https://financialmodelingprep.com/api/v3"

        # 거래 설정
        self.balance = 10000.0
        self.position = None
        self.entry_price = 0
        self.entry_time = None
        self.position_size = 0

        # 거래 조건 (데모용)
        self.min_holding_seconds = 30    # 30초 보유
        self.max_holding_seconds = 120   # 2분 최대
        self.profit_target = 0.01        # 1% 수익
        self.stop_loss = -0.015          # 1.5% 손절

        # 학습 설정
        self.action_probs = {
            "BUY_NVDL": 0.5,
            "BUY_NVDQ": 0.5
        }

        self.learning_rate = 0.2
        self.total_actions = 0
        self.total_reward = 0.0
        self.trade_count = 0
        self.api_calls = 0

        # 가격 기반 (실제 FMP API로 시작)
        self.base_prices = {}
        self.current_prices = {}

        print(f"초기화 완료 - 시작 자금: ${self.balance:,.0f}")
        print(f"보유 기간: {self.min_holding_seconds}-{self.max_holding_seconds}초")
        print(f"수익 목표: {self.profit_target*100:+.1f}%, 손절: {self.stop_loss*100:.1f}%")

    def initialize_prices(self):
        """실제 FMP API로 기준 가격 설정"""
        print("\n실제 FMP API로 기준 가격 설정 중...")

        for symbol in ['NVDL', 'NVDQ']:
            try:
                url = f"{self.base_url}/quote/{symbol}"
                response = requests.get(url, params={"apikey": self.api_key}, timeout=10)
                self.api_calls += 1

                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        price = float(data[0].get('price', 0))
                        self.base_prices[symbol] = price
                        self.current_prices[symbol] = price
                        print(f"  {symbol}: ${price:.2f} (실제 FMP API)")
                        continue

            except Exception as e:
                print(f"  {symbol}: API 오류 - {e}")

            # 실패시 기본값
            default_price = 85.0 if symbol == 'NVDL' else 1.0
            self.base_prices[symbol] = default_price
            self.current_prices[symbol] = default_price
            print(f"  {symbol}: ${default_price:.2f} (기본값)")

    def simulate_price_movement(self, symbol: str):
        """실시간 가격 변동 시뮬레이션"""
        base_price = self.base_prices.get(symbol, 85.0 if symbol == 'NVDL' else 1.0)

        # 현실적인 가격 변동
        # 1. 장기 트렌드 (±0.1% 드리프트)
        trend = np.random.uniform(-0.001, 0.001)

        # 2. 단기 변동성 (±2% 랜덤 워크)
        volatility = np.random.normal(0, 0.02)

        # 3. 가격 업데이트
        change = trend + volatility
        new_price = self.current_prices[symbol] * (1 + change)

        # 합리적 범위 유지 (기준 가격의 ±10%)
        min_price = base_price * 0.9
        max_price = base_price * 1.1
        new_price = max(min_price, min(max_price, new_price))

        self.current_prices[symbol] = new_price
        return new_price, change

    def choose_action(self):
        """행동 선택"""
        if np.random.random() < self.action_probs["BUY_NVDL"]:
            return "BUY_NVDL"
        else:
            return "BUY_NVDQ"

    def check_sell_conditions(self):
        """매도 조건 확인"""
        if self.position is None:
            return False, 0, 0

        current_time = datetime.now()
        holding_seconds = (current_time - self.entry_time).total_seconds()

        # 현재 가격
        current_price, change = self.simulate_price_movement(self.position)
        price_change_rate = (current_price / self.entry_price - 1)

        # 레버리지 적용
        if self.position == 'NVDL':
            leveraged_return = price_change_rate * 3
        else:
            leveraged_return = price_change_rate * 2

        print(f"    체크: {self.position} ${self.entry_price:.2f} → ${current_price:.2f} ({change*100:+.2f}%)")
        print(f"    보유: {holding_seconds:.1f}초, 레버리지 수익률: {leveraged_return*100:+.2f}%")

        # 매도 조건
        should_sell = False
        reason = ""

        if holding_seconds >= self.min_holding_seconds and leveraged_return >= self.profit_target:
            should_sell = True
            reason = f"수익 달성 ({leveraged_return*100:+.1f}%)"
        elif leveraged_return <= self.stop_loss:
            should_sell = True
            reason = f"손절 ({leveraged_return*100:+.1f}%)"
        elif holding_seconds >= self.max_holding_seconds:
            should_sell = True
            reason = f"시간 초과 ({holding_seconds:.1f}초)"

        if should_sell:
            print(f"    → 매도 결정: {reason}")

        return should_sell, current_price, leveraged_return

    def execute_action(self, action: str):
        """행동 실행"""
        # 매도 조건 확인
        if self.position is not None:
            should_sell, current_price, profit_rate = self.check_sell_conditions()

            if should_sell:
                # 매도 실행
                profit_amount = self.position_size * profit_rate
                self.balance += profit_amount

                print(f"  매도: {self.position} @ ${current_price:.2f}")
                print(f"    최종 수익률: {profit_rate*100:+.2f}% (${profit_amount:+,.0f})")
                print(f"    새 잔고: ${self.balance:,.0f}")

                reward = profit_rate * 100  # 수익률을 보상으로
                self.position = None
                self.position_size = 0
                self.trade_count += 1

                return reward

            return 0

        # 새로운 매수
        symbol = "NVDL" if action == "BUY_NVDL" else "NVDQ"
        price, change = self.simulate_price_movement(symbol)

        self.position = symbol
        self.entry_price = price
        self.entry_time = datetime.now()
        self.position_size = self.balance * 0.8

        print(f"  매수: {symbol} @ ${price:.2f} (변동: {change*100:+.2f}%)")
        print(f"    투자금: ${self.position_size:,.0f}")

        return 0

    def learn(self, action: str, reward: float):
        """학습"""
        if reward == 0:
            return

        self.total_reward += reward
        print(f"  학습: {action} → 보상 {reward:+.2f}")

        # 확률 업데이트
        adjustment = self.learning_rate * abs(reward) / 100

        if reward > 0:
            if action == "BUY_NVDL":
                self.action_probs["BUY_NVDL"] += adjustment
            else:
                self.action_probs["BUY_NVDQ"] += adjustment
        else:
            if action == "BUY_NVDL":
                self.action_probs["BUY_NVDL"] -= adjustment
            else:
                self.action_probs["BUY_NVDQ"] -= adjustment

        # 정규화
        total = sum(self.action_probs.values())
        self.action_probs["BUY_NVDL"] = max(0.1, self.action_probs["BUY_NVDL"] / total)
        self.action_probs["BUY_NVDQ"] = max(0.1, self.action_probs["BUY_NVDQ"] / total)

    def show_status(self):
        """상태 표시"""
        print(f"\n{'='*60}")
        print(f"완전한 거래 데모 상태 - 행동 {self.total_actions}회")
        print(f"{'='*60}")
        print(f"잔고: ${self.balance:,.0f} (수익률: {((self.balance/10000)-1)*100:+.1f}%)")

        if self.position:
            holding_time = (datetime.now() - self.entry_time).total_seconds()
            current_price = self.current_prices.get(self.position, 0)
            unrealized = ((current_price / self.entry_price - 1) *
                         (3 if self.position == 'NVDL' else 2) * 100)
            print(f"포지션: {self.position} @ ${self.entry_price:.2f} ({holding_time:.1f}초)")
            print(f"현재가: ${current_price:.2f} (미실현: {unrealized:+.2f}%)")
        else:
            print(f"포지션: 없음")

        print(f"완료 거래: {self.trade_count}회")
        print(f"총 보상: {self.total_reward:+.1f}")

        nvdl_pref = self.action_probs["BUY_NVDL"]
        nvdq_pref = self.action_probs["BUY_NVDQ"]
        print(f"학습 상태: NVDL {nvdl_pref:.3f} vs NVDQ {nvdq_pref:.3f}")

        if nvdl_pref > nvdq_pref + 0.1:
            print("  → AI가 NVDL을 선호하고 있습니다!")
        elif nvdq_pref > nvdl_pref + 0.1:
            print("  → AI가 NVDQ를 선호하고 있습니다!")
        else:
            print("  → AI가 아직 학습 중입니다...")

        print(f"{'='*60}\n")

    def run_complete_demo(self, cycles: int = 30):
        """완전한 거래 데모 실행"""
        print(f"\n완전한 거래 데모 시작 ({cycles}사이클)")

        # 실제 가격으로 초기화
        self.initialize_prices()

        print(f"\n실제 매수/매도 사이클을 확인합니다...")
        print("변동성 있는 가격 + 실제 보유 기간 + 학습")
        print()

        try:
            for cycle in range(cycles):
                self.total_actions += 1

                print(f"\n--- 사이클 {cycle+1}/{cycles} ({datetime.now().strftime('%H:%M:%S')}) ---")

                # 행동 선택
                action = self.choose_action()
                nvdl_prob = self.action_probs["BUY_NVDL"]
                print(f"선택: {action} (NVDL: {nvdl_prob:.3f})")

                # 거래 실행
                reward = self.execute_action(action)

                # 학습
                self.learn(action, reward)

                # 상태 표시
                if cycle % 5 == 4:
                    self.show_status()

                # 대기
                time.sleep(3)  # 3초 대기

        except KeyboardInterrupt:
            print("\n중단됨")

        self.show_final_results()

    def show_final_results(self):
        """최종 결과"""
        print(f"\n{'='*70}")
        print("완전한 거래 데모 완료")
        print(f"{'='*70}")
        print(f"시작 자금: $10,000")
        print(f"최종 자금: ${self.balance:,.0f}")
        print(f"총 수익률: {((self.balance/10000)-1)*100:+.2f}%")
        print(f"총 사이클: {self.total_actions}회")
        print(f"완료 거래: {self.trade_count}회")
        print(f"총 보상: {self.total_reward:+.1f}")

        nvdl_pref = self.action_probs["BUY_NVDL"]
        nvdq_pref = self.action_probs["BUY_NVDQ"]

        print(f"\n최종 학습 결과:")
        print(f"  NVDL 선호도: {nvdl_pref:.3f} ({nvdl_pref*100:.1f}%)")
        print(f"  NVDQ 선호도: {nvdq_pref:.3f} ({nvdq_pref*100:.1f}%)")

        if nvdl_pref > nvdq_pref:
            print(f"\n결과: AI가 NVDL을 {(nvdl_pref-nvdq_pref):.3f}만큼 더 선호합니다!")
        else:
            print(f"\n결과: AI가 NVDQ를 {(nvdq_pref-nvdl_pref):.3f}만큼 더 선호합니다!")

        if self.trade_count > 0:
            print(f"\n거래 성과:")
            print(f"  거래당 평균 보상: {self.total_reward/self.trade_count:+.2f}%")
            print(f"  거래 성공률: {(1 if self.total_reward > 0 else 0)*100:.0f}%")

        print(f"{'='*70}")

def main():
    """메인 실행"""
    print("*** 완전한 거래 데모 ***")
    print("실제 매수/매도 사이클 + 학습 확인")
    print("FMP API 기준 + 변동성 시뮬레이션")
    print()

    API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"

    demo = CompleteTradingDemo(API_KEY)
    demo.run_complete_demo(25)  # 25사이클

if __name__ == "__main__":
    main()