#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FMP API 실시간 순수 학습 트레이더 (최적화 버전)
- 실제 FMP API 데이터로 매매
- 완전히 빈 상태에서 시작
- 실제 거래 결과로만 학습
- API 호출 최적화

*** FMP API만 사용 - yfinance 절대 금지 ***
"""

import time
import requests
import numpy as np
from datetime import datetime

class FMPRealTimePureTrader:
    def __init__(self, api_key: str):
        """FMP API 실시간 순수 학습 트레이더"""
        print("=== FMP API 실시간 순수 학습 트레이더 ===")
        print("Financial Modeling Prep API 실제 데이터 사용")
        print("완전히 빈 상태에서 시작")
        print("실제 거래 결과로만 학습")
        print()

        # API 설정
        self.api_key = api_key
        self.base_url = "https://financialmodelingprep.com/api/v3"

        # 거래 설정
        self.symbols = ['NVDL', 'NVDQ']
        self.balance = 10000.0
        self.position = None
        self.entry_price = 0
        self.entry_time = None

        # 행동 선택 확률 (완전 랜덤 시작)
        self.action_probs = {
            "BUY_NVDL": 0.33,
            "BUY_NVDQ": 0.33,
            "HOLD": 0.34
        }

        # 학습 설정
        self.learning_rate = 0.15
        self.total_actions = 0
        self.total_reward = 0.0
        self.trade_count = 0
        self.api_calls = 0

        # 가격 캐시 (API 호출 최적화)
        self.price_cache = {}
        self.last_update = 0

        print(f"초기화 완료 - 시작 자금: ${self.balance:,.0f}")

    def get_real_price(self, symbol: str):
        """FMP API로 실제 가격 조회 (캐시 사용)"""
        current_time = time.time()

        # 캐시 확인 (30초 이내는 캐시 사용)
        if (symbol in self.price_cache and
            current_time - self.last_update < 30):
            return self.price_cache[symbol]

        try:
            url = f"{self.base_url}/quote/{symbol}"
            response = requests.get(url,
                                  params={"apikey": self.api_key},
                                  timeout=10)

            self.api_calls += 1

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    price = float(data[0].get('price', 0))
                    self.price_cache[symbol] = price
                    self.last_update = current_time
                    print(f"  {symbol}: ${price:.2f} (API)")
                    return price

        except Exception as e:
            print(f"  {symbol}: API 오류 - {e}")

        # API 실패시 캐시나 기본값 사용
        if symbol in self.price_cache:
            print(f"  {symbol}: ${self.price_cache[symbol]:.2f} (캐시)")
            return self.price_cache[symbol]

        # 최후의 수단: 기본 가격
        default_price = 85.0 if symbol == 'NVDL' else 25.0
        print(f"  {symbol}: ${default_price:.2f} (기본값)")
        return default_price

    def get_current_prices(self):
        """현재 실시간 가격 조회"""
        print("실시간 가격 조회...")
        nvdl_price = self.get_real_price('NVDL')
        nvdq_price = self.get_real_price('NVDQ')
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

            print(f"매수 실행: {symbol} @ ${price:.2f}")
            return 0

        # 매도 조건 체크
        elif self.position is not None:
            current_price = nvdl_price if self.position == "NVDL" else nvdq_price
            holding_time = (current_time - self.entry_time).total_seconds()

            # 매도 조건 (20초 이상 또는 1.5% 이상 변동)
            if holding_time > 20 or abs(current_price / self.entry_price - 1) > 0.015:
                return self.execute_sell(current_price)

        return 0

    def execute_sell(self, current_price: float):
        """매도 실행 및 보상 계산"""
        profit_rate = (current_price / self.entry_price - 1) * 100

        # 레버리지 적용
        if self.position == "NVDL":
            profit_rate *= 3  # 3배 레버리지
        elif self.position == "NVDQ":
            profit_rate *= 2  # 2배 레버리지

        # 잔고 업데이트
        profit_amount = self.balance * 0.9 * (profit_rate / 100)
        self.balance += profit_amount

        print(f"매도 실행: {self.position} @ ${current_price:.2f}")
        print(f"  수익률: {profit_rate:+.2f}% (${profit_amount:+,.0f})")
        print(f"  잔고: ${self.balance:,.0f}")

        # 보상 계산
        reward = min(max(profit_rate, -15), 15)  # -15 ~ +15 범위

        # 포지션 리셋
        self.position = None
        self.trade_count += 1

        return reward

    def learn(self, action: str, reward: float):
        """순수 학습"""
        if reward == 0:
            return

        self.total_reward += reward
        print(f"학습: {action} -> 보상 {reward:+.2f}")

        # 확률 업데이트 (더 적극적)
        adjustment = self.learning_rate * abs(reward) / 100

        if reward > 0:
            self.action_probs[action] += adjustment
        else:
            self.action_probs[action] -= adjustment

        # 확률 정규화
        total_prob = sum(self.action_probs.values())
        if total_prob > 0:
            for key in self.action_probs:
                self.action_probs[key] = max(0.05, self.action_probs[key] / total_prob)

        # 학습 상태 표시
        if self.total_actions % 3 == 0:  # 더 자주 표시
            self.show_learning_status()

    def show_learning_status(self):
        """학습 상태 표시"""
        print(f"\n{'='*50}")
        print(f"학습 상태 (행동 {self.total_actions}회, API 호출 {self.api_calls}회)")
        print("행동 확률:")
        for action, prob in self.action_probs.items():
            print(f"  {action}: {prob:.3f}")
        print(f"총 보상: {self.total_reward:+.1f}")
        print(f"거래 횟수: {self.trade_count}회")
        print(f"현재 잔고: ${self.balance:,.0f}")
        print(f"수익률: {((self.balance/10000)-1)*100:+.1f}%")
        print(f"{'='*50}\n")

    def run_realtime_learning(self, cycles: int = 20):
        """실시간 FMP API 학습 실행"""
        print(f"\n실시간 FMP API 학습 시작 ({cycles}사이클)")
        print("완전히 빈 상태에서 실제 데이터로 학습...\n")

        try:
            for cycle in range(cycles):
                self.total_actions += 1

                print(f"\n--- 사이클 {cycle+1}/{cycles} ({datetime.now().strftime('%H:%M:%S')}) ---")

                # 1. 행동 선택
                action = self.choose_action()
                print(f"선택: {action} (확률: {self.action_probs[action]:.3f})")

                # 2. 실제 FMP 데이터로 행동 실행
                reward = self.execute_action(action)

                # 3. 결과로 학습
                self.learn(action, reward)

                # 4. 대기 (API 제한 고려)
                time.sleep(3)  # 3초 대기 (빠른 테스트)

        except KeyboardInterrupt:
            print("\n사용자 중단")

        # 최종 결과
        self.show_final_results()

    def show_final_results(self):
        """최종 결과"""
        print(f"\n{'='*60}")
        print("FMP API 실시간 순수 학습 완료")
        print(f"{'='*60}")
        print(f"시작 자금: $10,000")
        print(f"최종 자금: ${self.balance:,.0f}")
        print(f"총 수익률: {((self.balance / 10000) - 1) * 100:+.2f}%")
        print(f"총 행동: {self.total_actions}회")
        print(f"총 거래: {self.trade_count}회")
        print(f"총 보상: {self.total_reward:+.1f}")
        print(f"API 호출: {self.api_calls}회")

        print(f"\n학습 결과 (최종 행동 확률):")
        for action, prob in self.action_probs.items():
            print(f"  {action}: {prob:.3f}")

        print(f"\n학습 성과:")
        if self.trade_count > 0:
            avg_reward = self.total_reward / self.trade_count
            print(f"  평균 보상: {avg_reward:+.2f}")
            print(f"  거래당 수익률: {((self.balance/10000-1)*100)/max(1,self.trade_count):+.2f}%")

        print(f"{'='*60}")

def main():
    """메인 실행"""
    print("*** FMP API 실시간 순수 학습 트레이더 ***")
    print("Financial Modeling Prep API 실제 데이터")
    print("완전히 빈 상태에서 시작")
    print("실제 거래 결과로만 학습\n")

    API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"

    # 실시간 트레이더 생성 및 실행
    trader = FMPRealTimePureTrader(API_KEY)
    trader.run_realtime_learning(5)  # 5사이클 실행

if __name__ == "__main__":
    main()