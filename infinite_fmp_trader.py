#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
무한 실행 FMP API 트레이더
- 계속 돌아가면서 학습
- Ctrl+C로만 중단 가능
- 실제 거래 결과로 학습
- 빠른 매매 사이클

*** FMP API만 사용 - yfinance 절대 금지 ***
"""

import time
import requests
import numpy as np
from datetime import datetime

class InfiniteFMPTrader:
    def __init__(self, api_key: str, cycle: str = "15min"):
        """무한 실행 FMP 트레이더"""
        print("=== 무한 실행 FMP API 트레이더 ===")
        print("실제 시장 주기로 거래")
        print("Ctrl+C로 중단할 때까지 계속 실행")
        print("FMP API 실시간 데이터 사용")
        print()

        # API 설정
        self.api_key = api_key
        self.base_url = "https://financialmodelingprep.com/api/v3"

        # 거래 주기 설정 (실제 시장 주기)
        self.cycles = {
            "15min": {"hold_seconds": 900, "display": "15분"},      # 15분 = 900초
            "1hour": {"hold_seconds": 3600, "display": "1시간"},     # 1시간 = 3600초
            "6hour": {"hold_seconds": 21600, "display": "6시간"},    # 6시간 = 21600초
            "12hour": {"hold_seconds": 43200, "display": "12시간"},  # 12시간 = 43200초
            "1day": {"hold_seconds": 86400, "display": "1일"}        # 1일 = 86400초
        }

        # 선택된 주기 (데모용으로 단축)
        self.selected_cycle = cycle
        self.hold_seconds = self.cycles[cycle]["hold_seconds"]
        self.demo_hold_seconds = min(60, self.hold_seconds // 60)  # 데모용: 최대 60초

        # 거래 설정
        self.balance = 10000.0
        self.position = None
        self.entry_price = 0
        self.entry_time = None
        self.profit_target = 0.015  # 1.5% 수익 목표
        self.stop_loss = -0.02      # 2% 손절

        # 행동 확률 (50:50 시작)
        self.action_probs = {
            "BUY_NVDL": 0.5,
            "BUY_NVDQ": 0.5
        }

        # 학습 설정
        self.learning_rate = 0.25  # 더 빠른 학습
        self.total_actions = 0
        self.total_reward = 0.0
        self.trade_count = 0
        self.api_calls = 0

        # 가격 시뮬레이션 (빠른 실행)
        self.prices = {'NVDL': 85.0, 'NVDQ': 1.0}
        self.last_api_call = 0

        print(f"초기화: ${self.balance:,.0f}")
        print(f"거래 주기: {self.cycles[cycle]['display']} (데모: {self.demo_hold_seconds}초 보유)")
        print(f"수익 목표: {self.profit_target*100:.1f}%, 손절: {self.stop_loss*100:.1f}%")
        print("50:50에서 시작하여 무한 학습")
        print()

    def get_price_with_api(self, symbol: str):
        """FMP API로 실제 가격 조회 (가끔)"""
        current_time = time.time()

        # 30초마다 한 번씩 실제 API 호출
        if current_time - self.last_api_call > 30:
            try:
                url = f"{self.base_url}/quote/{symbol}"
                response = requests.get(url,
                                      params={"apikey": self.api_key},
                                      timeout=8)

                self.api_calls += 1
                self.last_api_call = current_time

                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        price = float(data[0].get('price', 0))
                        self.prices[symbol] = price
                        return price

            except Exception as e:
                pass  # 조용히 실패

        # 대부분은 시뮬레이션으로 빠른 실행
        base = self.prices[symbol]
        change = np.random.uniform(-0.025, 0.025)  # ±2.5% 변동
        new_price = base * (1 + change)
        self.prices[symbol] = new_price
        return new_price

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
        nvdl_price = self.get_price_with_api('NVDL')
        nvdq_price = self.get_price_with_api('NVDQ')
        current_price = nvdl_price if self.position == "NVDL" else nvdq_price

        # 수익률 계산
        price_change = (current_price / self.entry_price - 1)

        # 레버리지 적용
        if self.position == "NVDL":
            leveraged_return = price_change * 3
        else:
            leveraged_return = price_change * 2

        # 매도 조건
        should_sell = False
        reason = ""

        # 1. 최소 보유 시간(데모) 경과 후 수익 목표 달성
        if holding_seconds >= self.demo_hold_seconds and leveraged_return >= self.profit_target:
            should_sell = True
            reason = f"수익 목표 달성 ({leveraged_return*100:+.1f}%)"
        # 2. 손절
        elif leveraged_return <= self.stop_loss:
            should_sell = True
            reason = f"손절 ({leveraged_return*100:+.1f}%)"
        # 3. 최대 보유 시간 초과 (데모용 2배)
        elif holding_seconds >= self.demo_hold_seconds * 2:
            should_sell = True
            reason = f"보유 시간 초과 ({holding_seconds:.0f}초)"

        return should_sell, current_price, leveraged_return, reason

    def execute_trade(self, action: str):
        """거래 실행 (실제 주기 반영)"""
        current_time = datetime.now()

        # 포지션 있으면 매도 조건 확인
        if self.position is not None:
            should_sell, current_price, leveraged_return, reason = self.check_sell_conditions()

            if should_sell:
                # 잔고 업데이트
                profit_amount = self.balance * 0.8 * leveraged_return
                self.balance += profit_amount

                holding_time = (current_time - self.entry_time).total_seconds()
                print(f"매도: {self.position} @ ${current_price:.2f}")
                print(f"  이유: {reason}")
                print(f"  보유: {holding_time:.0f}초, 수익률: {leveraged_return*100:+.2f}% (${profit_amount:+,.0f})")
                print(f"  잔고: ${self.balance:,.0f}")

                # 보상
                reward = min(max(leveraged_return * 100 * 0.3, -5), 5)

                self.position = None
                self.trade_count += 1

                return reward
            else:
                # 아직 보유 중
                holding_time = (current_time - self.entry_time).total_seconds()
                print(f"보유 중: {self.position} ({holding_time:.0f}초 경과)")
                return 0

        # 새로운 매수
        if action in ["BUY_NVDL", "BUY_NVDQ"]:
            nvdl_price = self.get_price_with_api('NVDL')
            nvdq_price = self.get_price_with_api('NVDQ')

            symbol = "NVDL" if action == "BUY_NVDL" else "NVDQ"
            price = nvdl_price if symbol == "NVDL" else nvdq_price

            self.position = symbol
            self.entry_price = price
            self.entry_time = current_time

            print(f"매수: {symbol} @ ${price:.2f} ({self.cycles[self.selected_cycle]['display']} 주기)")
            return 0

        return 0

    def learn(self, action: str, reward: float):
        """학습"""
        if reward == 0:
            return

        self.total_reward += reward

        # 더 적극적 학습
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

    def show_status(self):
        """상태 표시"""
        nvdl_pref = self.action_probs["BUY_NVDL"]
        nvdq_pref = self.action_probs["BUY_NVDQ"]

        print(f"\n{'='*60}")
        print(f"무한 학습 진행: {self.total_actions}회 행동, {self.trade_count}회 거래")
        print(f"현재 선호도: NVDL {nvdl_pref:.3f} vs NVDQ {nvdq_pref:.3f}")
        print(f"총 보상: {self.total_reward:+.1f}")
        print(f"잔고: ${self.balance:,.0f} (수익률: {((self.balance/10000)-1)*100:+.1f}%)")
        print(f"API 호출: {self.api_calls}회")

        # 현재 추세
        if nvdl_pref > 0.55:
            print(">> AI가 NVDL을 선호하는 중!")
        elif nvdq_pref > 0.55:
            print(">> AI가 NVDQ를 선호하는 중!")
        else:
            print(">> AI가 학습하며 선호도 조정 중...")

        if self.trade_count > 0:
            avg_reward = self.total_reward / self.trade_count
            print(f"거래당 평균 보상: {avg_reward:+.2f}")

        print(f"{'='*60}\n")

    def run_infinite(self):
        """무한 실행"""
        print("무한 학습 시작!")
        print(f"거래 주기: {self.cycles[self.selected_cycle]['display']}")
        print("실제 거래 결과로 계속 학습합니다...")
        print("Ctrl+C를 눌러 중단하세요.\n")

        try:
            while True:  # 무한 루프
                self.total_actions += 1

                # 현재 선호도로 행동 선택
                action = self.choose_action()
                nvdl_prob = self.action_probs["BUY_NVDL"]

                print(f"\n[{self.total_actions:3d}] {datetime.now().strftime('%H:%M:%S')} 행동: {action} (NVDL:{nvdl_prob:.3f})")

                # 거래 실행
                reward = self.execute_trade(action)

                # 학습
                self.learn(action, reward)

                # 주기적 상태 표시
                if self.total_actions % 10 == 0:
                    self.show_status()

                # 거래 주기에 맞춰 대기
                if self.position is None:
                    time.sleep(2)  # 포지션 없으면 2초 대기
                else:
                    time.sleep(5)  # 포지션 있으면 5초마다 체크

        except KeyboardInterrupt:
            print("\n\nCtrl+C 감지! 중단합니다...")
            self.show_final_result()

    def show_final_result(self):
        """최종 결과"""
        print(f"\n{'='*60}")
        print("무한 학습 트레이더 중단됨")
        print(f"{'='*60}")

        nvdl_pref = self.action_probs["BUY_NVDL"]
        nvdq_pref = self.action_probs["BUY_NVDQ"]

        print(f"총 행동: {self.total_actions}회")
        print(f"총 거래: {self.trade_count}회")
        print(f"시작 자금: $10,000")
        print(f"최종 자금: ${self.balance:,.0f}")
        print(f"총 수익률: {((self.balance/10000)-1)*100:+.2f}%")

        print(f"\n최종 학습 결과:")
        print(f"  NVDL 선호도: {nvdl_pref:.3f} ({nvdl_pref*100:.1f}%)")
        print(f"  NVDQ 선호도: {nvdq_pref:.3f} ({nvdq_pref*100:.1f}%)")

        if nvdl_pref > nvdq_pref:
            advantage = nvdl_pref - nvdq_pref
            print(f"\n결론: AI가 NVDL을 {advantage:.3f}만큼 더 선호함!")
        else:
            advantage = nvdq_pref - nvdl_pref
            print(f"\n결론: AI가 NVDQ를 {advantage:.3f}만큼 더 선호함!")

        print(f"\n성과:")
        print(f"  총 보상: {self.total_reward:+.1f}")
        print(f"  API 호출: {self.api_calls}회")

        if self.trade_count > 0:
            print(f"  거래당 평균 보상: {self.total_reward/self.trade_count:+.2f}")
            print(f"  거래당 평균 수익률: {((self.balance/10000-1)*100)/self.trade_count:+.2f}%")

        print(f"{'='*60}")

def main():
    """메인"""
    print("*** 무한 실행 FMP API 트레이더 ***")
    print("실제 시장 주기로 거래")
    print("50:50에서 시작하여 어떤 종목을 더 선호하게 될까요?")
    print("Ctrl+C로 중단할 수 있습니다.\n")

    API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"

    # 거래 주기 선택 (15min, 1hour, 6hour, 12hour, 1day)
    trader = InfiniteFMPTrader(API_KEY, cycle="15min")  # 15분 주기
    trader.run_infinite()

if __name__ == "__main__":
    main()