#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
적극적 학습 시스템
- 모든 패턴을 시도하면서 학습
- 실시간 가격으로 실전 학습
"""

import requests
import json
import time
from datetime import datetime
from collections import defaultdict
import random

class AggressiveLearner:
    def __init__(self, api_key):
        print("="*50)
        print("Aggressive Learning System")
        print("Learning by trying everything")
        print("="*50)

        self.api_key = api_key
        self.balance = 10000.0
        self.initial_balance = self.balance

        # 가격 데이터
        self.price_data = {
            'NVDL': [],
            'NVDQ': []
        }

        # 학습 메모리 - 모든 시도 기록
        self.experience = defaultdict(list)  # pattern -> [pnl_results]

        # 현재 포지션
        self.positions = {}

        # 통계
        self.stats = {
            'total_attempts': 0,
            'successful_trades': 0,
            'exploration_trades': 0,
            'learned_patterns': 0
        }

    def get_current_price(self, symbol):
        """현재 가격 조회"""
        try:
            url = f"https://financialmodelingprep.com/api/v3/quote-short/{symbol}"
            response = requests.get(url, params={'apikey': self.api_key}, timeout=5)

            if response.status_code == 200:
                data = response.json()
                if data:
                    price = float(data[0]['price'])
                    self.price_data[symbol].append({
                        'time': datetime.now(),
                        'price': price
                    })
                    # 최대 50개만 유지
                    if len(self.price_data[symbol]) > 50:
                        self.price_data[symbol].pop(0)

                    return price
        except:
            pass

        # 폴백 가격 (시뮬레이션)
        base = 50.0 if symbol == 'NVDL' else 25.0
        if self.price_data[symbol]:
            last_price = self.price_data[symbol][-1]['price']
            new_price = last_price * (1 + random.uniform(-0.02, 0.02))
        else:
            new_price = base + random.uniform(-2, 2)

        self.price_data[symbol].append({
            'time': datetime.now(),
            'price': new_price
        })

        return new_price

    def create_pattern(self, symbol):
        """현재 상황의 패턴 생성"""
        if len(self.price_data[symbol]) < 5:
            return None

        prices = [d['price'] for d in self.price_data[symbol][-5:]]

        pattern_elements = []

        # 1. 최근 변화율
        for i in range(1, 5):
            change = (prices[i] - prices[i-1]) / prices[i-1] * 100
            if change > 0.5:
                pattern_elements.append('Up')
            elif change < -0.5:
                pattern_elements.append('Down')
            else:
                pattern_elements.append('Flat')

        # 2. 전체 트렌드
        total_change = (prices[-1] - prices[0]) / prices[0] * 100
        if total_change > 1:
            pattern_elements.append('Rising')
        elif total_change < -1:
            pattern_elements.append('Falling')
        else:
            pattern_elements.append('Sideways')

        # 3. 현재 시간 (시간대별 특성)
        hour = datetime.now().hour
        if 9 <= hour <= 12:
            pattern_elements.append('Morning')
        elif 13 <= hour <= 16:
            pattern_elements.append('Afternoon')
        else:
            pattern_elements.append('After')

        return '_'.join(pattern_elements)

    def should_trade(self, symbol, pattern):
        """거래 여부 결정"""
        # 이미 포지션 있으면 거래 안함
        if symbol in self.positions:
            return None, 0

        # 학습된 패턴이면 경험 기반 결정
        if pattern in self.experience:
            results = self.experience[pattern]

            if len(results) >= 3:
                avg_pnl = sum(results) / len(results)
                win_rate = len([r for r in results if r > 0]) / len(results)

                if win_rate >= 0.6 and avg_pnl > 0.5:
                    return 'BUY', 0.8
                elif win_rate <= 0.4 and avg_pnl < -0.5:
                    return 'SELL', 0.8

        # 새로운 패턴 또는 불확실한 패턴 - 탐색
        if random.random() < 0.4:  # 40% 확률로 탐색
            action = random.choice(['BUY', 'SELL'])
            self.stats['exploration_trades'] += 1
            return action, 0.5

        return None, 0

    def open_position(self, symbol, action, price, pattern):
        """포지션 오픈"""
        size = self.balance * 0.15  # 15% 사용

        self.positions[symbol] = {
            'action': action,
            'entry_price': price,
            'entry_time': datetime.now(),
            'pattern': pattern,
            'size': size
        }

        print(f"[{datetime.now().strftime('%H:%M:%S')}] {action} {symbol} @ ${price:.2f}")
        print(f"  Pattern: {pattern[:30]}...")
        self.stats['total_attempts'] += 1

    def check_exit(self, symbol):
        """청산 조건 체크"""
        if symbol not in self.positions:
            return

        pos = self.positions[symbol]
        current_price = self.get_current_price(symbol)

        # 수익률 계산
        if pos['action'] == 'BUY':
            pnl = (current_price / pos['entry_price'] - 1) * 100
        else:
            pnl = (pos['entry_price'] / current_price - 1) * 100

        # 레버리지 적용
        if symbol == 'NVDL':
            pnl *= 3
        else:  # NVDQ
            pnl *= 2

        # 보유 시간 (초)
        hold_time = (datetime.now() - pos['entry_time']).total_seconds()

        # 청산 조건
        should_close = False
        reason = ""

        if pnl >= 1.5:  # 1.5% 익절
            should_close = True
            reason = "Profit"
        elif pnl <= -1.0:  # 1% 손절
            should_close = True
            reason = "Loss"
        elif hold_time >= 1800:  # 30분 경과
            should_close = True
            reason = "Time"

        if should_close:
            # 청산 실행
            profit = pos['size'] * (pnl / 100)
            self.balance += profit

            # 경험 학습
            self.experience[pos['pattern']].append(pnl)

            # 패턴별 최대 20개 결과만 유지
            if len(self.experience[pos['pattern']]) > 20:
                self.experience[pos['pattern']].pop(0)

            if pnl > 0:
                self.stats['successful_trades'] += 1

            print(f"[{datetime.now().strftime('%H:%M:%S')}] CLOSE {symbol} @ ${current_price:.2f}")
            print(f"  PnL: {pnl:+.2f}% ({reason}) | Balance: ${self.balance:.2f}")

            # 패턴 성과 출력
            pattern_results = self.experience[pos['pattern']]
            avg_pnl = sum(pattern_results) / len(pattern_results)
            win_rate = len([r for r in pattern_results if r > 0]) / len(pattern_results)
            print(f"  Pattern learned: {win_rate*100:.0f}% win, {avg_pnl:+.1f}% avg (n={len(pattern_results)})")

            del self.positions[symbol]

    def print_status(self):
        """상태 출력"""
        total_pnl = (self.balance / self.initial_balance - 1) * 100
        success_rate = self.stats['successful_trades'] / max(self.stats['total_attempts'], 1) * 100

        print(f"\n{'='*50}")
        print(f"LEARNING STATUS")
        print(f"Balance: ${self.balance:.2f} ({total_pnl:+.2f}%)")
        print(f"Attempts: {self.stats['total_attempts']} | Success: {success_rate:.1f}%")
        print(f"Active Positions: {list(self.positions.keys())}")
        print(f"Patterns Learned: {len(self.experience)}")
        print(f"Exploration Trades: {self.stats['exploration_trades']}")

        # 상위 패턴
        if self.experience:
            patterns = []
            for pattern, results in self.experience.items():
                if len(results) >= 3:
                    avg = sum(results) / len(results)
                    win_rate = len([r for r in results if r > 0]) / len(results)
                    patterns.append((pattern, win_rate, avg, len(results)))

            if patterns:
                patterns.sort(key=lambda x: x[2], reverse=True)
                print("\nTop Patterns:")
                for pattern, wr, avg, count in patterns[:3]:
                    print(f"  {pattern[:25]}...: {wr*100:.0f}% win, {avg:+.1f}% (n={count})")

        print("="*50 + "\n")

    def run(self):
        """메인 학습 루프"""
        print("Starting aggressive learning...\n")

        cycle = 0
        last_status = time.time()

        try:
            while True:
                cycle += 1

                for symbol in ['NVDL', 'NVDQ']:
                    # 현재 가격 가져오기
                    price = self.get_current_price(symbol)

                    # 기존 포지션 체크
                    self.check_exit(symbol)

                    # 새 거래 기회 탐색
                    if symbol not in self.positions:
                        pattern = self.create_pattern(symbol)
                        if pattern:
                            action, confidence = self.should_trade(symbol, pattern)
                            if action and confidence >= 0.5:
                                self.open_position(symbol, action, price, pattern)

                # 30초마다 상태 출력
                if time.time() - last_status >= 30:
                    self.print_status()
                    last_status = time.time()

                # 10초 대기
                time.sleep(10)

        except KeyboardInterrupt:
            print("\nStopping learning...")
            self.print_status()

            # 학습 데이터 저장
            learned_patterns = {}
            for pattern, results in self.experience.items():
                if len(results) >= 3:
                    learned_patterns[pattern] = {
                        'avg_pnl': sum(results) / len(results),
                        'win_rate': len([r for r in results if r > 0]) / len(results),
                        'count': len(results)
                    }

            with open('aggressive_learning_results.json', 'w') as f:
                json.dump({
                    'balance': self.balance,
                    'stats': self.stats,
                    'learned_patterns': learned_patterns,
                    'timestamp': datetime.now().isoformat()
                }, f, indent=2)

            print("Learning data saved!")

if __name__ == "__main__":
    API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"
    learner = AggressiveLearner(API_KEY)
    learner.run()