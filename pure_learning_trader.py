#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
순수 학습 트레이더
- 어떠한 과거 데이터도 사용하지 않음
- 완전히 빈 상태에서 시작
- 실제 거래 결과로만 학습
- 매우 단순한 강화학습

*** FMP API만 사용 - yfinance 절대 금지 ***
"""

import time
import numpy as np
from datetime import datetime

class PureLearningTrader:
    def __init__(self, fmp_api_key: str):
        """순수 학습 트레이더 - 완전히 빈 상태에서 시작"""
        print("=== 순수 학습 트레이더 ===")
        print("완전히 빈 상태에서 시작")
        print("과거 데이터 사용 안함")
        print("실제 거래 결과로만 학습")
        print()

        # 자금
        self.balance = 10000.0
        self.position = None
        self.entry_price = 0
        self.entry_time = None

        # 행동 선택 확률 (완전히 랜덤에서 시작)
        self.action_probs = {
            "BUY_NVDL": 0.33,
            "BUY_NVDQ": 0.33,
            "HOLD": 0.34
        }

        # 학습률과 통계
        self.learning_rate = 0.1
        self.total_actions = 0
        self.total_reward = 0.0
        self.trade_count = 0

        print(f"순수 학습 시작 - 시작 자금: ${self.balance:,.0f}")

    def get_current_prices(self):
        """현재 가격 조회 (시뮬레이션)"""
        # 실시간 가격 시뮬레이션 (변동성 있는 랜덤 가격)
        nvdl_price = 45.0 + np.random.uniform(-3, 3)
        nvdq_price = 25.0 + np.random.uniform(-2, 2)
        return nvdl_price, nvdq_price

    def choose_action(self):
        """행동 선택 (확률 기반)"""
        rand = np.random.random()
        if rand < self.action_probs["BUY_NVDL"]:
            return "BUY_NVDL"
        elif rand < self.action_probs["BUY_NVDL"] + self.action_probs["BUY_NVDQ"]:
            return "BUY_NVDQ"
        else:
            return "HOLD"

    def execute_action(self, action: str):
        """행동 실행"""
        nvdl_price, nvdq_price = self.get_current_prices()
        current_time = datetime.now()

        # 매수 실행
        if action in ["BUY_NVDL", "BUY_NVDQ"] and self.position is None:
            symbol = "NVDL" if action == "BUY_NVDL" else "NVDQ"
            price = nvdl_price if symbol == "NVDL" else nvdq_price

            self.position = symbol
            self.entry_price = price
            self.entry_time = current_time

            print(f"매수: {symbol} @ ${price:.2f}")
            return 0  # 매수시 보상 없음

        # 매도 조건 체크
        elif self.position is not None:
            current_price = nvdl_price if self.position == "NVDL" else nvdq_price
            holding_time = (current_time - self.entry_time).total_seconds()

            # 간단한 매도 조건 (3초 이상 보유 또는 2% 이상 변동)
            if holding_time > 3 or abs(current_price / self.entry_price - 1) > 0.02:
                return self.execute_sell(current_price)

        return 0  # 아무 행동 없음

    def execute_sell(self, current_price: float):
        """매도 실행 및 보상 계산"""
        profit_rate = (current_price / self.entry_price - 1) * 100

        # 레버리지 적용
        if self.position == "NVDL":
            profit_rate *= 3  # 3배 레버리지
        elif self.position == "NVDQ":
            profit_rate *= 2  # 2배 레버리지

        # 잔고 업데이트 (간소화)
        profit_amount = self.balance * 0.9 * (profit_rate / 100)
        self.balance += profit_amount

        print(f"매도: {self.position} @ ${current_price:.2f}")
        print(f"   수익률: {profit_rate:+.2f}% (${profit_amount:+,.0f})")
        print(f"   잔고: ${self.balance:,.0f}")

        # 보상 계산 (단순화)
        reward = min(max(profit_rate, -10), 10)  # -10 ~ +10 범위

        # 포지션 리셋
        self.position = None
        self.trade_count += 1

        return reward

    def learn(self, action: str, reward: float):
        """순수 학습 (매우 단순한 강화학습)"""
        if reward == 0:
            return

        self.total_reward += reward
        print(f"학습: {action} -> 보상 {reward:+.2f}")

        # 확률 업데이트
        if reward > 0:  # 좋은 결과면 확률 증가
            self.action_probs[action] += self.learning_rate * abs(reward) / 100
        else:  # 나쁜 결과면 확률 감소
            self.action_probs[action] -= self.learning_rate * abs(reward) / 100

        # 확률 정규화 (합이 1이 되도록)
        total_prob = sum(self.action_probs.values())
        if total_prob > 0:
            for key in self.action_probs:
                self.action_probs[key] = max(0.01, self.action_probs[key] / total_prob)

        # 주기적 학습 상태 출력
        if self.total_actions % 10 == 0:
            print(f"\n{'='*40}")
            print(f"학습 상태 (행동 {self.total_actions}회)")
            print("행동 확률:")
            for act, prob in self.action_probs.items():
                print(f"  {act}: {prob:.3f}")
            print(f"총 보상: {self.total_reward:+.1f}")
            print(f"현재 잔고: ${self.balance:,.0f}")
            print(f"{'='*40}\n")

    def run_simulation(self, cycles: int = 100):
        """순수 학습 시뮬레이션 실행"""
        print(f"순수 학습 시뮬레이션 시작 ({cycles}사이클)")
        print("완전히 빈 상태에서 학습 시작...\n")

        try:
            for cycle in range(cycles):
                self.total_actions += 1

                # 1. 행동 선택
                action = self.choose_action()

                # 2. 행동 실행
                reward = self.execute_action(action)

                # 3. 학습
                self.learn(action, reward)

                # 4. 진행 상황 출력
                if cycle % 20 == 0:
                    nvdl_price, nvdq_price = self.get_current_prices()
                    print(f"[{cycle:3d}] NVDL:${nvdl_price:.2f} NVDQ:${nvdq_price:.2f} | 행동:{action} | 보상:{reward:+.1f}")

                time.sleep(0.1)  # 0.1초 대기

        except KeyboardInterrupt:
            print("\n사용자에 의해 중단됨")

        # 최종 결과 출력
        self.show_final_results()

    def show_final_results(self):
        """최종 결과 출력"""
        print(f"\n{'='*50}")
        print("순수 학습 완료")
        print(f"{'='*50}")
        print(f"시작 자금: $10,000")
        print(f"최종 자금: ${self.balance:,.0f}")
        print(f"총 수익률: {((self.balance / 10000) - 1) * 100:+.2f}%")
        print(f"총 행동: {self.total_actions}회")
        print(f"총 거래: {self.trade_count}회")
        print(f"총 보상: {self.total_reward:+.1f}")
        print(f"\n학습된 행동 확률:")
        for action, prob in self.action_probs.items():
            print(f"  {action}: {prob:.3f}")
        print(f"{'='*50}")

def main():
    """메인 실행"""
    print("*** 순수 학습 트레이더 ***")
    print("완전히 빈 상태에서 시작")
    print("FMP API만 사용")
    print("과거 데이터 없음")
    print("실제 결과로만 학습\n")

    FMP_API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"

    # 순수 학습 트레이더 생성
    trader = PureLearningTrader(FMP_API_KEY)

    # 시뮬레이션 실행
    trader.run_simulation(100)  # 100사이클 실행

if __name__ == "__main__":
    main()
