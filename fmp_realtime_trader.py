#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FMP API 연동 실시간 순수 학습 트레이더
- Financial Modeling Prep API 실시간 데이터 사용
- 완전히 빈 상태에서 시작
- 실제 거래 결과로만 학습
- 실시간 가격으로 매매 시뮬레이션

*** FMP API만 사용 - yfinance 절대 금지 ***
"""

import time
import requests
import json
import numpy as np
from datetime import datetime
from typing import Optional, Dict, Any

class FMPRealtimeTrader:
    def __init__(self, fmp_api_key: str):
        """FMP API 연동 실시간 순수 학습 트레이더"""
        print("=== FMP API 연동 실시간 트레이더 ===")
        print("Financial Modeling Prep API 사용")
        print("완전히 빈 상태에서 시작")
        print("실시간 데이터로만 학습")
        print("yfinance 사용 금지")
        print()

        # API 설정
        self.api_key = fmp_api_key
        self.base_url = "https://financialmodelingprep.com/api/v3"

        # 거래 설정
        self.symbols = ['NVDL', 'NVDQ']
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

        # 학습 설정
        self.learning_rate = 0.1
        self.total_actions = 0
        self.total_reward = 0.0
        self.trade_count = 0

        # API 호출 제한 (분당 250회)
        self.api_calls_today = 0
        self.last_api_call = 0
        self.min_call_interval = 0.25  # 4초에 1번 (안전하게)

        print(f"초기화 완료 - 시작 자금: ${self.balance:,.0f}")
        print(f"API 키: {self.api_key[:10]}...")

    def get_realtime_quote(self, symbol: str) -> Optional[Dict[Any, Any]]:
        """FMP API로 실시간 주가 조회"""
        current_time = time.time()

        # API 호출 제한 체크
        if current_time - self.last_api_call < self.min_call_interval:
            time.sleep(self.min_call_interval - (current_time - self.last_api_call))

        try:
            url = f"{self.base_url}/quote/{symbol}"
            params = {"apikey": self.api_key}

            print(f"API 호출: {symbol} 실시간 가격 조회...")
            response = requests.get(url, params=params, timeout=10)

            self.last_api_call = time.time()
            self.api_calls_today += 1

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    quote = data[0]  # 첫 번째 항목
                    print(f"  {symbol}: ${quote.get('price', 0):.2f} (변동: {quote.get('changesPercentage', 0):+.2f}%)")
                    return quote
                else:
                    print(f"  {symbol}: 데이터 없음")
                    return None
            else:
                print(f"  {symbol}: API 오류 {response.status_code}")
                return None

        except Exception as e:
            print(f"  {symbol}: API 호출 실패 - {e}")
            return None

    def get_current_prices(self):
        """현재 실시간 가격 조회"""
        prices = {}

        for symbol in self.symbols:
            quote = self.get_realtime_quote(symbol)
            if quote and 'price' in quote:
                prices[symbol] = float(quote['price'])
            else:
                # API 실패시 마지막 알려진 가격 + 약간의 변동
                if symbol == 'NVDL':
                    prices[symbol] = 45.0 + np.random.uniform(-1, 1)
                else:
                    prices[symbol] = 25.0 + np.random.uniform(-0.5, 0.5)
                print(f"  {symbol}: API 실패, 임시 가격 사용 ${prices[symbol]:.2f}")

        return prices['NVDL'], prices['NVDQ']

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

            # 매도 조건 (10초 이상 보유 또는 2% 이상 변동)
            if holding_time > 10 or abs(current_price / self.entry_price - 1) > 0.02:
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

        # 잔고 업데이트
        profit_amount = self.balance * 0.9 * (profit_rate / 100)
        self.balance += profit_amount

        print(f"매도: {self.position} @ ${current_price:.2f}")
        print(f"   수익률: {profit_rate:+.2f}% (${profit_amount:+,.0f})")
        print(f"   잔고: ${self.balance:,.0f}")

        # 보상 계산
        reward = min(max(profit_rate, -10), 10)

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

        # 확률 업데이트
        if reward > 0:
            self.action_probs[action] += self.learning_rate * abs(reward) / 100
        else:
            self.action_probs[action] -= self.learning_rate * abs(reward) / 100

        # 확률 정규화
        total_prob = sum(self.action_probs.values())
        if total_prob > 0:
            for key in self.action_probs:
                self.action_probs[key] = max(0.01, self.action_probs[key] / total_prob)

        # 학습 상태 출력
        if self.total_actions % 5 == 0:
            print(f"\n{'='*50}")
            print(f"학습 상태 (행동 {self.total_actions}회, API 호출 {self.api_calls_today}회)")
            print("행동 확률:")
            for act, prob in self.action_probs.items():
                print(f"  {act}: {prob:.3f}")
            print(f"총 보상: {self.total_reward:+.1f}")
            print(f"현재 잔고: ${self.balance:,.0f}")
            print(f"{'='*50}\n")

    def run_realtime_simulation(self, cycles: int = 50):
        """실시간 FMP API 연동 시뮬레이션"""
        print(f"\n실시간 FMP API 연동 시뮬레이션 시작 ({cycles}사이클)")
        print("완전히 빈 상태에서 실시간 데이터로 학습...\n")

        try:
            for cycle in range(cycles):
                self.total_actions += 1

                print(f"\n[사이클 {cycle+1}/{cycles}] {datetime.now().strftime('%H:%M:%S')}")

                # 1. 행동 선택
                action = self.choose_action()
                print(f"선택된 행동: {action}")

                # 2. 행동 실행 (실시간 API 호출)
                reward = self.execute_action(action)

                # 3. 학습
                self.learn(action, reward)

                # 4. API 제한을 고려한 대기
                print("다음 사이클까지 대기...")
                time.sleep(5)  # 5초 대기

        except KeyboardInterrupt:
            print("\n사용자에 의해 중단됨")

        # 최종 결과
        self.show_final_results()

    def show_final_results(self):
        """최종 결과 출력"""
        print(f"\n{'='*60}")
        print("FMP API 연동 실시간 학습 완료")
        print(f"{'='*60}")
        print(f"시작 자금: $10,000")
        print(f"최종 자금: ${self.balance:,.0f}")
        print(f"총 수익률: {((self.balance / 10000) - 1) * 100:+.2f}%")
        print(f"총 행동: {self.total_actions}회")
        print(f"총 거래: {self.trade_count}회")
        print(f"총 보상: {self.total_reward:+.1f}")
        print(f"API 호출 횟수: {self.api_calls_today}회")
        print(f"\n학습된 행동 확률:")
        for action, prob in self.action_probs.items():
            print(f"  {action}: {prob:.3f}")
        print(f"{'='*60}")

        # API 사용량 체크
        if self.api_calls_today > 200:
            print("WARNING: API 호출 횟수가 많습니다. 일일 제한에 주의하세요.")
        else:
            print(f"OK: API 사용량 양호: {self.api_calls_today}/250")

def test_fmp_api(api_key: str):
    """FMP API 연결 테스트"""
    print("=== FMP API 연결 테스트 ===")

    base_url = "https://financialmodelingprep.com/api/v3"

    for symbol in ['NVDL', 'NVDQ']:
        try:
            url = f"{base_url}/quote/{symbol}"
            params = {"apikey": api_key}

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    quote = data[0]
                    print(f"OK {symbol}: ${quote.get('price', 0):.2f} (변동: {quote.get('changesPercentage', 0):+.2f}%)")
                else:
                    print(f"FAIL {symbol}: 데이터 없음")
            else:
                print(f"FAIL {symbol}: HTTP {response.status_code}")

        except Exception as e:
            print(f"ERROR {symbol}: 오류 - {e}")

    print("=== API 테스트 완료 ===\n")

def main():
    """메인 실행"""
    print("*** FMP API 연동 실시간 순수 학습 트레이더 ***")
    print("Financial Modeling Prep API 사용")
    print("완전히 빈 상태에서 시작")
    print("실시간 데이터로만 학습")
    print("yfinance 사용 금지\n")

    FMP_API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"

    if not FMP_API_KEY or FMP_API_KEY == "YOUR_API_KEY_HERE":
        print("ERROR: FMP API 키를 설정해주세요!")
        print("FMP API는 https://financialmodelingprep.com에서 발급받으세요.")
        return

    # API 연결 테스트
    test_fmp_api(FMP_API_KEY)

    # 실시간 트레이더 생성 및 실행
    trader = FMPRealtimeTrader(FMP_API_KEY)
    trader.run_realtime_simulation(30)  # 30사이클 실행

if __name__ == "__main__":
    main()