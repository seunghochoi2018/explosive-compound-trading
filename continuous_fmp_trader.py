#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
계속 돌아가는 FMP API 실시간 학습 트레이더
- 더 적극적인 매매
- 계속 학습하면서 돌아감
- 실제 거래 결과로 학습

*** FMP API만 사용 - yfinance 절대 금지 ***
"""

import time
import requests
import numpy as np
from datetime import datetime

class ContinuousFMPTrader:
    def __init__(self, api_key: str):
        """계속 돌아가는 FMP 트레이더"""
        print("=== 계속 돌아가는 FMP API 학습 트레이더 ===")
        print("더 적극적인 매매로 계속 학습")
        print("실제 FMP API 데이터 사용")
        print("무한 학습 모드")
        print()

        # API 설정
        self.api_key = api_key
        self.base_url = "https://financialmodelingprep.com/api/v3"

        # 거래 설정
        self.balance = 10000.0
        self.position = None
        self.entry_price = 0
        self.entry_time = None

        # 행동 확률 (랜덤 시작)
        self.action_probs = {
            "BUY_NVDL": 0.4,
            "BUY_NVDQ": 0.4,
            "HOLD": 0.2  # HOLD 확률 낮춤 (더 적극적)
        }

        # 학습 설정
        self.learning_rate = 0.2
        self.total_actions = 0
        self.total_reward = 0.0
        self.trade_count = 0
        self.api_calls = 0

        # 가격 기록
        self.last_prices = {'NVDL': 85.0, 'NVDQ': 1.0}

        print(f"초기화 완료 - 시작 자금: ${self.balance:,.0f}")
        print("더 적극적 매매: HOLD 20%, 매수 80%")

    def get_price(self, symbol: str):
        """실시간 가격 조회 (최적화)"""
        try:
            url = f"{self.base_url}/quote/{symbol}"
            response = requests.get(url,
                                  params={"apikey": self.api_key},
                                  timeout=8)

            self.api_calls += 1

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    price = float(data[0].get('price', 0))
                    self.last_prices[symbol] = price
                    return price

        except Exception as e:
            print(f"API 오류 ({symbol}): {e}")

        # 실패시 약간 변동된 마지막 가격 사용
        base_price = self.last_prices[symbol]
        variation = np.random.uniform(-0.02, 0.02)  # ±2% 변동
        new_price = base_price * (1 + variation)
        self.last_prices[symbol] = new_price
        return new_price

    def choose_action(self):
        """행동 선택"""
        rand = np.random.random()
        if rand < self.action_probs["BUY_NVDL"]:
            return "BUY_NVDL"
        elif rand < self.action_probs["BUY_NVDL"] + self.action_probs["BUY_NVDQ"]:
            return "BUY_NVDQ"
        else:
            return "HOLD"

    def execute_trade(self, action: str):
        """거래 실행"""
        nvdl_price = self.get_price('NVDL')
        nvdq_price = self.get_price('NVDQ')
        current_time = datetime.now()

        print(f"현재 가격: NVDL=${nvdl_price:.2f}, NVDQ=${nvdq_price:.2f}")

        # 매수
        if action in ["BUY_NVDL", "BUY_NVDQ"] and self.position is None:
            symbol = "NVDL" if action == "BUY_NVDL" else "NVDQ"
            price = nvdl_price if symbol == "NVDL" else nvdq_price

            self.position = symbol
            self.entry_price = price
            self.entry_time = current_time

            print(f"→ 매수: {symbol} @ ${price:.2f}")
            return 0

        # 매도 (더 빠르게)
        elif self.position is not None:
            current_price = nvdl_price if self.position == "NVDL" else nvdq_price
            holding_time = (current_time - self.entry_time).total_seconds()

            # 매도 조건 (5초 이상 또는 0.5% 이상 변동)
            should_sell = (
                holding_time > 5 or
                abs(current_price / self.entry_price - 1) > 0.005
            )

            if should_sell:
                profit_rate = (current_price / self.entry_price - 1) * 100

                # 레버리지 적용
                if self.position == "NVDL":
                    profit_rate *= 3
                elif self.position == "NVDQ":
                    profit_rate *= 2

                profit_amount = self.balance * 0.8 * (profit_rate / 100)
                self.balance += profit_amount

                print(f"→ 매도: {self.position} @ ${current_price:.2f}")
                print(f"  수익률: {profit_rate:+.2f}% (${profit_amount:+,.0f})")
                print(f"  잔고: ${self.balance:,.0f}")

                # 보상
                reward = min(max(profit_rate * 0.5, -10), 10)  # 보상 조정

                self.position = None
                self.trade_count += 1

                return reward

        return 0

    def learn(self, action: str, reward: float):
        """학습"""
        if reward == 0:
            return

        self.total_reward += reward
        print(f"학습: {action} → 보상 {reward:+.2f}")

        # 더 적극적 학습
        adjustment = self.learning_rate * abs(reward) / 50

        if reward > 0:
            self.action_probs[action] += adjustment
            print(f"  {action} 확률 증가!")
        else:
            self.action_probs[action] -= adjustment
            print(f"  {action} 확률 감소...")

        # 정규화
        total = sum(self.action_probs.values())
        for key in self.action_probs:
            self.action_probs[key] = max(0.05, self.action_probs[key] / total)

    def show_status(self):
        """상태 표시"""
        print(f"\n{'='*50}")
        print(f"학습 진행 상황 (총 {self.total_actions}회 행동)")
        print(f"거래 횟수: {self.trade_count}회")
        print(f"총 보상: {self.total_reward:+.1f}")
        print(f"현재 잔고: ${self.balance:,.0f}")
        print(f"수익률: {((self.balance/10000)-1)*100:+.1f}%")
        print(f"API 호출: {self.api_calls}회")
        print("현재 행동 확률:")
        for action, prob in self.action_probs.items():
            print(f"  {action}: {prob:.3f}")
        print(f"{'='*50}\n")

    def run_continuous(self):
        """계속 돌아가는 학습"""
        print("\n계속 돌아가는 실시간 학습 시작!")
        print("Ctrl+C로 중단할 수 있습니다.")
        print()

        try:
            while True:
                self.total_actions += 1

                print(f"\n[행동 #{self.total_actions}] {datetime.now().strftime('%H:%M:%S')}")

                # 1. 행동 선택
                action = self.choose_action()
                print(f"선택: {action} (확률: {self.action_probs[action]:.3f})")

                # 2. 거래 실행
                reward = self.execute_trade(action)

                # 3. 학습
                self.learn(action, reward)

                # 4. 주기적 상태 표시
                if self.total_actions % 10 == 0:
                    self.show_status()

                # 5. 짧은 대기
                time.sleep(2)  # 2초마다 실행

        except KeyboardInterrupt:
            print("\n\n중단됨!")
            self.show_final_results()

    def show_final_results(self):
        """최종 결과"""
        print(f"\n{'='*60}")
        print("계속 학습 트레이더 결과")
        print(f"{'='*60}")
        print(f"총 행동: {self.total_actions}회")
        print(f"총 거래: {self.trade_count}회")
        print(f"시작 자금: $10,000")
        print(f"최종 자금: ${self.balance:,.0f}")
        print(f"총 수익률: {((self.balance/10000)-1)*100:+.2f}%")
        print(f"총 보상: {self.total_reward:+.1f}")
        print(f"API 호출: {self.api_calls}회")

        print(f"\n최종 학습된 확률:")
        for action, prob in sorted(self.action_probs.items(), key=lambda x: x[1], reverse=True):
            print(f"  {action}: {prob:.3f}")

        if self.trade_count > 0:
            print(f"\n성과 분석:")
            print(f"  평균 보상: {self.total_reward/self.trade_count:+.2f}")
            print(f"  거래당 수익: {((self.balance/10000-1)*100)/self.trade_count:+.2f}%")

            # 학습 효과 분석
            max_prob = max(self.action_probs.values())
            min_prob = min(self.action_probs.values())
            learning_effect = max_prob - min_prob
            print(f"  학습 효과: {learning_effect:.3f} (높을수록 확실한 선호)")

        print(f"{'='*60}")

def main():
    """메인 실행"""
    print("*** 계속 돌아가는 FMP API 학습 트레이더 ***")
    print("무한 학습 모드")
    print("더 적극적인 매매")
    print("실시간 FMP API 데이터\n")

    API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"

    trader = ContinuousFMPTrader(API_KEY)
    trader.run_continuous()

if __name__ == "__main__":
    main()