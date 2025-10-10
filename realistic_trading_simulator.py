#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실제 시장 주기별 거래 시뮬레이션
- 실제 보유 기간 (최소 30분 - 최대 6시간)
- 실제 시장 시간 기반 거래
- 정확한 매수/매도 타이밍
- FMP API 실시간 데이터

*** FMP API만 사용 - yfinance 절대 금지 ***
"""

import time
import requests
import numpy as np
from datetime import datetime, timedelta

class RealisticTradingSimulator:
    def __init__(self, api_key: str):
        """실제 시장 주기 거래 시뮬레이터"""
        print("=== 실제 시장 주기별 거래 시뮬레이션 ===")
        print("정확한 보유 기간과 매도 타이밍")
        print("실제 시장 시간 기반 거래")
        print("FMP API 실시간 데이터")
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

        # 실제 거래 파라미터 (데모용 단축)
        self.min_holding_minutes = 2     # 최소 2분 보유 (데모용)
        self.max_holding_minutes = 10    # 최대 10분 보유 (데모용)
        self.profit_target = 0.015       # 1.5% 수익 목표 (조금 낮춤)
        self.stop_loss = -0.02           # 2% 손절 (조금 낮춤)

        # 행동 확률 (순수 학습)
        self.action_probs = {
            "BUY_NVDL": 0.4,
            "BUY_NVDQ": 0.4,
            "HOLD": 0.2
        }

        # 학습 설정
        self.learning_rate = 0.1
        self.total_actions = 0
        self.total_reward = 0.0
        self.trade_count = 0
        self.api_calls = 0

        # 가격 캐시
        self.price_cache = {}
        self.last_api_call = 0

        print(f"초기화 완료 - 시작 자금: ${self.balance:,.0f}")
        print(f"실제 보유 기간: {self.min_holding_minutes}-{self.max_holding_minutes}분 (데모용 단축)")
        print(f"수익 목표: {self.profit_target*100:+.1f}%, 손절: {self.stop_loss*100:.1f}%")

    def get_real_price(self, symbol: str):
        """FMP API로 실제 가격 조회 (쿨다운 적용)"""
        current_time = time.time()

        # API 호출 제한 (10초마다 한 번)
        if current_time - self.last_api_call < 10:
            if symbol in self.price_cache:
                return self.price_cache[symbol]

        try:
            url = f"{self.base_url}/quote/{symbol}"
            response = requests.get(url,
                                  params={"apikey": self.api_key},
                                  timeout=10)

            self.api_calls += 1
            self.last_api_call = current_time

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    price = float(data[0].get('price', 0))
                    change_pct = float(data[0].get('changesPercentage', 0))

                    self.price_cache[symbol] = price

                    print(f"  {symbol}: ${price:.2f} ({change_pct:+.2f}%) [실시간]")
                    return price

        except Exception as e:
            print(f"  API 오류 ({symbol}): {str(e)[:50]}")

        # 실패시 시뮬레이션 가격
        if symbol in self.price_cache:
            base_price = self.price_cache[symbol]
        else:
            base_price = 85.0 if symbol == 'NVDL' else 1.0

        # 현실적인 가격 변동 시뮬레이션 (변동성 증가)
        change = np.random.normal(0, 0.02)  # 평균 0%, 표준편차 2% (더 큰 변동)
        new_price = base_price * (1 + change)
        self.price_cache[symbol] = new_price

        print(f"  {symbol}: ${new_price:.2f} ({change*100:+.2f}%) [시뮬레이션]")
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

    def can_sell_position(self):
        """매도 가능 여부 확인 (실제 보유 기간 기준)"""
        if self.position is None:
            return False

        current_time = datetime.now()
        holding_minutes = (current_time - self.entry_time).total_seconds() / 60

        # 현재 가격 조회
        nvdl_price = self.get_real_price('NVDL')
        nvdq_price = self.get_real_price('NVDQ')
        current_price = nvdl_price if self.position == 'NVDL' else nvdq_price

        # 수익률 계산
        price_change = (current_price / self.entry_price - 1)

        # 레버리지 적용
        if self.position == 'NVDL':
            leveraged_change = price_change * 3
        elif self.position == 'NVDQ':
            leveraged_change = price_change * 2
        else:
            leveraged_change = price_change

        print(f"    보유 중: {self.position} @ ${self.entry_price:.2f} → ${current_price:.2f}")
        print(f"    보유 시간: {holding_minutes:.1f}분, 레버리지 수익률: {leveraged_change*100:+.2f}%")

        # 매도 조건 확인
        should_sell = False
        sell_reason = ""

        # 1. 최소 보유 시간 후 수익 목표 달성
        if holding_minutes >= self.min_holding_minutes and leveraged_change >= self.profit_target:
            should_sell = True
            sell_reason = f"수익 목표 달성 ({leveraged_change*100:+.1f}%)"

        # 2. 손절 조건
        elif leveraged_change <= self.stop_loss:
            should_sell = True
            sell_reason = f"손절 ({leveraged_change*100:+.1f}%)"

        # 3. 최대 보유 시간 초과
        elif holding_minutes >= self.max_holding_minutes:
            should_sell = True
            sell_reason = f"최대 보유 시간 초과 ({holding_minutes:.1f}분)"

        if should_sell:
            print(f"    → 매도 결정: {sell_reason}")
            return True, current_price, leveraged_change
        else:
            print(f"    → 계속 보유 (조건 미달)")
            return False, current_price, leveraged_change

    def execute_action(self, action: str):
        """행동 실행"""
        current_time = datetime.now()

        # 현재 포지션이 있으면 매도 조건 확인
        if self.position is not None:
            should_sell, current_price, profit_rate = self.can_sell_position()

            if should_sell:
                return self.execute_sell(current_price, profit_rate)
            else:
                return 0  # 아직 보유

        # 새로운 매수
        elif action in ["BUY_NVDL", "BUY_NVDQ"]:
            symbol = "NVDL" if action == "BUY_NVDL" else "NVDQ"
            price = self.get_real_price(symbol)

            self.position = symbol
            self.entry_price = price
            self.entry_time = current_time
            self.position_size = self.balance * 0.8  # 80% 투자

            print(f"  매수 실행: {symbol} @ ${price:.2f} (투자금: ${self.position_size:,.0f})")
            return 0

        return 0

    def execute_sell(self, current_price: float, profit_rate: float):
        """매도 실행"""
        # 잔고 업데이트
        profit_amount = self.position_size * profit_rate
        self.balance += profit_amount

        print(f"  매도 실행: {self.position} @ ${current_price:.2f}")
        print(f"  최종 수익률: {profit_rate*100:+.2f}% (${profit_amount:+,.0f})")
        print(f"  새 잔고: ${self.balance:,.0f}")

        # 보상 계산
        reward = profit_rate * 100  # 수익률을 보상으로 직접 사용

        # 거래 완료
        self.position = None
        self.position_size = 0
        self.trade_count += 1

        return reward

    def learn(self, action: str, reward: float):
        """학습"""
        if reward == 0:
            return

        self.total_reward += reward
        print(f"  학습: {action} → 보상 {reward:+.2f}")

        # 확률 조정
        adjustment = self.learning_rate * abs(reward) / 100

        if reward > 0:
            self.action_probs[action] += adjustment
        else:
            self.action_probs[action] -= adjustment

        # 정규화
        total = sum(self.action_probs.values())
        for key in self.action_probs:
            self.action_probs[key] = max(0.05, self.action_probs[key] / total)

    def show_status(self):
        """상태 표시"""
        print(f"\n{'='*60}")
        print(f"실제 거래 시뮬레이션 상태 - 행동 {self.total_actions}회")
        print(f"{'='*60}")
        print(f"잔고: ${self.balance:,.0f} (수익률: {((self.balance/10000)-1)*100:+.1f}%)")

        if self.position:
            holding_time = (datetime.now() - self.entry_time).total_seconds() / 60
            print(f"현재 포지션: {self.position} @ ${self.entry_price:.2f} ({holding_time:.1f}분 보유)")
        else:
            print(f"현재 포지션: 없음")

        print(f"총 거래: {self.trade_count}회")
        print(f"총 보상: {self.total_reward:+.1f}")
        print(f"API 호출: {self.api_calls}회")

        print(f"\n학습된 행동 확률:")
        for action, prob in sorted(self.action_probs.items(), key=lambda x: x[1], reverse=True):
            print(f"  {action}: {prob:.3f}")
        print(f"{'='*60}\n")

    def run_realistic_simulation(self, cycles: int = 30):
        """실제 주기별 시뮬레이션 실행"""
        print(f"\n실제 주기별 거래 시뮬레이션 시작 ({cycles}사이클)")
        print("실제 보유 기간과 매도 조건을 적용한 현실적인 거래")
        print()

        try:
            for cycle in range(cycles):
                self.total_actions += 1

                print(f"\n--- 사이클 {cycle+1}/{cycles} ({datetime.now().strftime('%H:%M:%S')}) ---")

                # 행동 선택
                action = self.choose_action()
                print(f"선택된 행동: {action} (확률: {self.action_probs[action]:.3f})")

                # 실제 시장 가격으로 거래 실행
                reward = self.execute_action(action)

                # 학습
                self.learn(action, reward)

                # 주기적 상태 표시
                if cycle % 5 == 4:
                    self.show_status()

                # 실제 거래 주기 (5분마다)
                print("다음 사이클까지 대기...")
                time.sleep(5)  # 5초 (실제로는 5분)

        except KeyboardInterrupt:
            print("\n사용자 중단")

        self.show_final_results()

    def show_final_results(self):
        """최종 결과"""
        print(f"\n{'='*70}")
        print("실제 주기별 거래 시뮬레이션 완료")
        print(f"{'='*70}")
        print(f"시작 자금: $10,000")
        print(f"최종 자금: ${self.balance:,.0f}")
        print(f"총 수익률: {((self.balance/10000)-1)*100:+.2f}%")
        print(f"총 행동: {self.total_actions}회")
        print(f"실제 거래: {self.trade_count}회")
        print(f"총 보상: {self.total_reward:+.1f}")
        print(f"API 호출: {self.api_calls}회")

        print(f"\n최종 학습 결과:")
        for action, prob in sorted(self.action_probs.items(), key=lambda x: x[1], reverse=True):
            print(f"  {action}: {prob:.3f} ({prob*100:.1f}%)")

        if self.trade_count > 0:
            print(f"\n거래 분석:")
            print(f"  거래당 평균 보상: {self.total_reward/self.trade_count:+.2f}%")
            print(f"  거래당 평균 수익: ${(self.balance-10000)/self.trade_count:+.0f}")

        print(f"{'='*70}")

def main():
    """메인 실행"""
    print("*** 실제 주기별 거래 시뮬레이션 ***")
    print("현실적인 보유 기간과 매도 조건")
    print("FMP API 실시간 데이터")
    print("순수 학습 기반 거래\n")

    API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"

    simulator = RealisticTradingSimulator(API_KEY)
    simulator.run_realistic_simulation(20)  # 20사이클 실행

if __name__ == "__main__":
    main()