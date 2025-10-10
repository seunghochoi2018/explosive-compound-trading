#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
빠른 학습 시뮬레이터
- 15분 주기를 시뮬레이션으로 빠르게 실행
- 패턴 학습 및 개선
"""

import random
import json
from datetime import datetime, timedelta
from collections import defaultdict

class FastLearningSimulator:
    def __init__(self):
        print("="*50)
        print("Fast Learning Simulator")
        print("Simulating 15-minute trading intervals")
        print("="*50)

        self.balance = 10000.0
        self.initial_balance = self.balance

        # 패턴별 성과 기록
        self.pattern_performance = {
            'NVDL': defaultdict(list),
            'NVDQ': defaultdict(list)
        }

        # 가격 히스토리
        self.price_history = {
            'NVDL': [],
            'NVDQ': []
        }

        # 통계
        self.total_trades = 0
        self.winning_trades = 0
        self.current_time = datetime.now()

    def generate_price_sequence(self, symbol, length=1000):
        """가격 시퀀스 생성 (15분봉 1000개 = 약 10일)"""
        base = 50.0 if symbol == 'NVDL' else 25.0
        prices = [base]

        for _ in range(length):
            # 트렌드 + 노이즈
            trend = random.choice([0.001, -0.001, 0])  # 약한 트렌드
            noise = random.gauss(0, 0.005)  # 0.5% 변동성
            next_price = prices[-1] * (1 + trend + noise)
            prices.append(max(next_price, base * 0.5))  # 최소가격 제한

        return prices

    def get_pattern(self, prices):
        """최근 5개 가격으로 패턴 생성"""
        if len(prices) < 5:
            return None

        pattern = ""
        for i in range(1, 5):
            change = (prices[-i] - prices[-i-1]) / prices[-i-1]
            if change > 0.003:
                pattern += "U"  # Up
            elif change < -0.003:
                pattern += "D"  # Down
            else:
                pattern += "N"  # Neutral

        return pattern

    def decide_action(self, symbol, pattern):
        """패턴 기반 행동 결정"""
        if not pattern:
            return None

        # 해당 패턴의 과거 성과
        if pattern in self.pattern_performance[symbol]:
            results = self.pattern_performance[symbol][pattern]

            if len(results) >= 3:  # 최소 3번 경험
                avg_return = sum(results) / len(results)
                win_rate = len([r for r in results if r > 0]) / len(results)

                # 승률과 평균 수익 기반 결정
                if win_rate > 0.6 and avg_return > 0.5:
                    return 'BUY'
                elif win_rate < 0.4 and avg_return < -0.5:
                    return 'SELL'

        # 탐색 (새로운 패턴 시도)
        if random.random() < 0.2:  # 20% 탐색
            return random.choice(['BUY', 'SELL', None])

        return None

    def simulate_trade(self, symbol, action, entry_price, exit_price):
        """거래 시뮬레이션"""
        # 레버리지 적용
        if symbol == 'NVDL':
            leverage = 3.0
        else:  # NVDQ
            leverage = -2.0  # 역방향

        # 수익률 계산
        base_return = (exit_price / entry_price - 1) * 100

        if action == 'BUY':
            pnl = base_return * abs(leverage)
        else:  # SELL
            pnl = -base_return * abs(leverage)

        # NVDQ는 역방향
        if symbol == 'NVDQ':
            pnl = -pnl

        return pnl

    def run_simulation(self):
        """시뮬레이션 실행"""
        print("\nGenerating price data...")

        # 가격 데이터 생성
        self.price_history['NVDL'] = self.generate_price_sequence('NVDL')
        self.price_history['NVDQ'] = self.generate_price_sequence('NVDQ')

        print("Running simulation...\n")

        # 각 심볼별로 시뮬레이션
        for symbol in ['NVDL', 'NVDQ']:
            prices = self.price_history[symbol]
            position = None

            for i in range(5, len(prices) - 10):  # 5개 이후부터, 마지막 10개 전까지
                # 패턴 추출
                current_prices = prices[:i+1]
                pattern = self.get_pattern(current_prices)

                if position:
                    # 포지션 있음 - 청산 체크
                    current_price = prices[i]
                    holding_periods = i - position['entry_index']

                    # 수익률 계산
                    pnl = self.simulate_trade(
                        symbol, position['action'],
                        position['entry_price'], current_price
                    )

                    # 청산 조건
                    if pnl >= 3 or pnl <= -2 or holding_periods >= 4:  # 3% 익절, 2% 손절, 4봉 경과
                        # 청산
                        profit = self.balance * 0.2 * (pnl / 100)
                        self.balance += profit

                        # 패턴 성과 기록
                        self.pattern_performance[symbol][position['pattern']].append(pnl)

                        # 통계 업데이트
                        self.total_trades += 1
                        if pnl > 0:
                            self.winning_trades += 1

                        # 15분 * holding_periods 시간 경과
                        self.current_time += timedelta(minutes=15 * holding_periods)

                        if self.total_trades % 20 == 0:  # 20거래마다 출력
                            self.print_trade(symbol, position['action'], pnl)

                        position = None

                else:
                    # 포지션 없음 - 진입 체크
                    action = self.decide_action(symbol, pattern)

                    if action:
                        position = {
                            'action': action,
                            'entry_price': prices[i],
                            'entry_index': i,
                            'pattern': pattern
                        }

        # 최종 결과
        self.print_final_results()

    def print_trade(self, symbol, action, pnl):
        """거래 출력"""
        time_str = self.current_time.strftime('%m/%d %H:%M')
        balance_pct = (self.balance / self.initial_balance - 1) * 100

        print(f"[{time_str}] {symbol} {action} closed: {pnl:+.2f}% | "
              f"Balance: ${self.balance:.0f} ({balance_pct:+.1f}%)")

    def print_final_results(self):
        """최종 결과 출력"""
        print("\n" + "="*50)
        print("SIMULATION COMPLETE")
        print("="*50)

        final_pnl = (self.balance / self.initial_balance - 1) * 100
        win_rate = (self.winning_trades / max(self.total_trades, 1)) * 100

        print(f"Final Balance: ${self.balance:.2f} ({final_pnl:+.2f}%)")
        print(f"Total Trades: {self.total_trades}")
        print(f"Win Rate: {win_rate:.1f}%")

        # 상위 패턴
        print("\nTop Performing Patterns:")

        for symbol in ['NVDL', 'NVDQ']:
            patterns = []
            for pattern, results in self.pattern_performance[symbol].items():
                if len(results) >= 3:
                    avg = sum(results) / len(results)
                    patterns.append((pattern, avg, len(results)))

            patterns.sort(key=lambda x: x[1], reverse=True)

            print(f"\n{symbol}:")
            for pattern, avg, count in patterns[:5]:
                print(f"  {pattern}: {avg:+.2f}% avg (n={count})")

        # 학습 데이터 저장
        self.save_results()

    def save_results(self):
        """결과 저장"""
        data = {
            'final_balance': self.balance,
            'total_trades': self.total_trades,
            'win_rate': self.winning_trades / max(self.total_trades, 1),
            'pattern_performance': {
                symbol: dict(patterns)
                for symbol, patterns in self.pattern_performance.items()
            },
            'timestamp': datetime.now().isoformat()
        }

        with open('simulation_results.json', 'w') as f:
            json.dump(data, f, indent=2)

        print("\nResults saved to simulation_results.json")

if __name__ == "__main__":
    simulator = FastLearningSimulator()
    simulator.run_simulation()