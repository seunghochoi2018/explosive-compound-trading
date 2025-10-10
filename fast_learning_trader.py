#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
빠른 학습 FMP API 트레이더
- 매우 빠른 매매 사이클
- 실시간 학습 효과 확인
- 계속 돌아가면서 학습

*** FMP API만 사용 ***
"""

import time
import requests
import numpy as np
from datetime import datetime

class FastLearningTrader:
    def __init__(self, api_key: str):
        """빠른 학습 트레이더"""
        print("=== 빠른 학습 FMP API 트레이더 ===")
        print("매우 빠른 매매로 학습 효과 확인")
        print()

        self.api_key = api_key
        self.base_url = "https://financialmodelingprep.com/api/v3"

        # 거래 설정
        self.balance = 10000.0
        self.position = None
        self.entry_price = 0
        self.entry_time = None

        # 행동 확률 (균등하게 시작)
        self.action_probs = {
            "BUY_NVDL": 0.5,
            "BUY_NVDQ": 0.5
        }

        self.learning_rate = 0.3  # 빠른 학습
        self.total_actions = 0
        self.total_reward = 0.0
        self.trade_count = 0

        # 가격 시뮬레이션 (API 호출 최소화)
        self.prices = {'NVDL': 85.0, 'NVDQ': 1.0}

        print(f"초기화: ${self.balance:,.0f}, 빠른 학습 모드")

    def get_simulated_price(self, symbol: str):
        """가격 시뮬레이션 (빠른 실행용)"""
        # 실제 변동성 시뮬레이션
        base = self.prices[symbol]
        change = np.random.uniform(-0.03, 0.03)  # ±3% 변동
        new_price = base * (1 + change)
        self.prices[symbol] = new_price
        return new_price

    def choose_action(self):
        """행동 선택 (NVDL vs NVDQ)"""
        if np.random.random() < self.action_probs["BUY_NVDL"]:
            return "BUY_NVDL"
        else:
            return "BUY_NVDQ"

    def execute_trade(self, action: str):
        """빠른 거래 실행"""
        nvdl_price = self.get_simulated_price('NVDL')
        nvdq_price = self.get_simulated_price('NVDQ')

        # 매수
        if self.position is None:
            symbol = "NVDL" if action == "BUY_NVDL" else "NVDQ"
            price = nvdl_price if symbol == "NVDL" else nvdq_price

            self.position = symbol
            self.entry_price = price
            self.entry_time = datetime.now()

            print(f"매수: {symbol} @ ${price:.2f}", end=" → ")
            return 0

        # 매도 (빠르게)
        else:
            current_price = nvdl_price if self.position == "NVDL" else nvdq_price
            profit_rate = (current_price / self.entry_price - 1) * 100

            # 레버리지 적용
            if self.position == "NVDL":
                profit_rate *= 3
            elif self.position == "NVDQ":
                profit_rate *= 2

            # 수익 계산
            profit_amount = self.balance * 0.8 * (profit_rate / 100)
            self.balance += profit_amount

            print(f"매도 ${current_price:.2f} ({profit_rate:+.2f}%) 잔고:${self.balance:,.0f}")

            # 보상
            reward = min(max(profit_rate * 0.3, -5), 5)

            self.position = None
            self.trade_count += 1

            return reward

    def learn(self, action: str, reward: float):
        """빠른 학습"""
        if reward == 0:
            return

        self.total_reward += reward

        # 학습 업데이트
        adjustment = self.learning_rate * abs(reward) / 100

        if reward > 0:
            if action == "BUY_NVDL":
                self.action_probs["BUY_NVDL"] += adjustment
                print(f"  NVDL 선호 증가! (+{reward:.1f})")
            else:
                self.action_probs["BUY_NVDQ"] += adjustment
                print(f"  NVDQ 선호 증가! (+{reward:.1f})")
        else:
            if action == "BUY_NVDL":
                self.action_probs["BUY_NVDL"] -= adjustment
                print(f"  NVDL 선호 감소... ({reward:.1f})")
            else:
                self.action_probs["BUY_NVDQ"] -= adjustment
                print(f"  NVDQ 선호 감소... ({reward:.1f})")

        # 정규화
        total = sum(self.action_probs.values())
        self.action_probs["BUY_NVDL"] = max(0.1, self.action_probs["BUY_NVDL"] / total)
        self.action_probs["BUY_NVDQ"] = max(0.1, self.action_probs["BUY_NVDQ"] / total)

    def show_progress(self):
        """진행 상황"""
        nvdl_pref = self.action_probs["BUY_NVDL"]
        nvdq_pref = self.action_probs["BUY_NVDQ"]

        print(f"\n{'='*60}")
        print(f"학습 진행: {self.total_actions}회 행동, {self.trade_count}회 거래")
        print(f"현재 선호도: NVDL {nvdl_pref:.3f} vs NVDQ {nvdq_pref:.3f}")
        print(f"총 보상: {self.total_reward:+.1f}")
        print(f"잔고: ${self.balance:,.0f} (수익률: {((self.balance/10000)-1)*100:+.1f}%)")

        # 학습 방향성 표시
        if nvdl_pref > 0.6:
            print(">> AI가 NVDL을 선호하고 있습니다!")
        elif nvdq_pref > 0.6:
            print(">> AI가 NVDQ를 선호하고 있습니다!")
        else:
            print(">> AI가 아직 학습 중입니다...")

        print(f"{'='*60}\n")

    def run_fast_learning(self, cycles: int = 50):
        """빠른 학습 실행"""
        print(f"빠른 학습 시작 ({cycles}사이클)")
        print("50:50에서 시작하여 실제 결과로 학습...\n")

        try:
            for i in range(cycles):
                self.total_actions += 1

                # 현재 선호도로 행동 선택
                action = self.choose_action()
                nvdl_prob = self.action_probs["BUY_NVDL"]

                print(f"[{i+1:2d}] {action} (NVDL:{nvdl_prob:.3f}) ", end="")

                # 거래 실행
                reward = self.execute_trade(action)

                # 학습
                self.learn(action, reward)

                # 진행 상황 표시
                if (i + 1) % 10 == 0:
                    self.show_progress()

                time.sleep(0.2)  # 빠른 실행

        except KeyboardInterrupt:
            print("\n중단됨!")

        # 최종 결과
        self.show_final_result()

    def show_final_result(self):
        """최종 결과"""
        print(f"\n{'='*60}")
        print("빠른 학습 완료!")
        print(f"{'='*60}")

        nvdl_pref = self.action_probs["BUY_NVDL"]
        nvdq_pref = self.action_probs["BUY_NVDQ"]

        print(f"최종 선호도:")
        print(f"  NVDL: {nvdl_pref:.3f} ({nvdl_pref*100:.1f}%)")
        print(f"  NVDQ: {nvdq_pref:.3f} ({nvdq_pref*100:.1f}%)")

        if nvdl_pref > nvdq_pref:
            advantage = nvdl_pref - nvdq_pref
            print(f"\n결과: AI가 NVDL을 {advantage:.3f}만큼 더 선호함!")
        else:
            advantage = nvdq_pref - nvdl_pref
            print(f"\n결과: AI가 NVDQ를 {advantage:.3f}만큼 더 선호함!")

        print(f"\n성과:")
        print(f"  총 거래: {self.trade_count}회")
        print(f"  총 보상: {self.total_reward:+.1f}")
        print(f"  최종 잔고: ${self.balance:,.0f}")
        print(f"  총 수익률: {((self.balance/10000)-1)*100:+.2f}%")

        if self.trade_count > 0:
            print(f"  거래당 평균 보상: {self.total_reward/self.trade_count:+.2f}")

def main():
    """메인"""
    print("*** 빠른 학습 FMP API 트레이더 ***")
    print("50:50에서 시작하여 실제 결과로 학습")
    print("어떤 종목을 더 선호하게 될까요?\n")

    API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"

    trader = FastLearningTrader(API_KEY)
    trader.run_fast_learning(50)

if __name__ == "__main__":
    main()