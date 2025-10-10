#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실시간 데이터 학습 트레이더
- FMP API로 실제 가격 데이터 수집
- 15분마다 실시간 학습 및 거래
"""

import requests
import json
import time
from datetime import datetime, timedelta
from collections import deque
import pickle
import os

class RealtimeLearningTrader:
    def __init__(self, api_key):
        print("="*50)
        print("Realtime Learning Trader")
        print("Learning from actual market data")
        print("="*50)

        self.api_key = api_key
        self.balance = 10000.0
        self.initial_balance = self.balance

        # 실시간 가격 히스토리
        self.price_history = {
            'NVDL': deque(maxlen=100),
            'NVDQ': deque(maxlen=100)
        }

        # 학습된 패턴 데이터
        self.pattern_memory = self.load_memory()

        # 현재 포지션
        self.positions = {}

        # 마지막 거래 시간
        self.last_check_time = datetime.now()

        # 통계
        self.stats = {
            'trades': 0,
            'wins': 0,
            'total_pnl': 0.0,
            'consecutive_wins': 0,
            'consecutive_losses': 0
        }

        print(f"Loaded {sum(len(p) for p in self.pattern_memory.values())} patterns from memory")
        print(f"Starting balance: ${self.balance:.2f}\n")

    def load_memory(self):
        """이전 학습 데이터 로드"""
        if os.path.exists('realtime_patterns.pkl'):
            try:
                with open('realtime_patterns.pkl', 'rb') as f:
                    return pickle.load(f)
            except:
                pass

        return {
            'NVDL': {},
            'NVDQ': {}
        }

    def save_memory(self):
        """학습 데이터 저장"""
        with open('realtime_patterns.pkl', 'wb') as f:
            pickle.dump(self.pattern_memory, f)

    def get_realtime_price(self, symbol):
        """실시간 가격 조회"""
        try:
            url = f"https://financialmodelingprep.com/api/v3/quote-short/{symbol}"
            params = {'apikey': self.api_key}
            response = requests.get(url, params=params, timeout=5)

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    price = float(data[0]['price'])

                    # 가격 히스토리에 추가
                    self.price_history[symbol].append({
                        'time': datetime.now(),
                        'price': price
                    })

                    return price

        except Exception as e:
            print(f"Error fetching {symbol}: {e}")

        return None

    def get_historical_data(self, symbol):
        """최근 15분 데이터 조회"""
        try:
            url = f"https://financialmodelingprep.com/api/v3/historical-chart/15min/{symbol}"
            params = {'apikey': self.api_key}
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    # 최근 20개 캔들
                    recent = data[:20]
                    for candle in reversed(recent):
                        self.price_history[symbol].append({
                            'time': datetime.fromisoformat(candle['date'].replace(' ', 'T')),
                            'price': float(candle['close'])
                        })
                    return True

        except Exception as e:
            print(f"Error fetching history for {symbol}: {e}")

        return False

    def extract_pattern(self, symbol):
        """가격 패턴 추출"""
        if len(self.price_history[symbol]) < 10:
            return None

        prices = [p['price'] for p in list(self.price_history[symbol])[-10:]]

        # 패턴 생성: 최근 5개 가격 변화율
        pattern_parts = []
        for i in range(5, 10):
            change = (prices[i] - prices[i-1]) / prices[i-1] * 100

            if change > 0.5:
                pattern_parts.append('UU')  # 강한 상승
            elif change > 0.1:
                pattern_parts.append('U')   # 약한 상승
            elif change < -0.5:
                pattern_parts.append('DD')  # 강한 하락
            elif change < -0.1:
                pattern_parts.append('D')   # 약한 하락
            else:
                pattern_parts.append('N')   # 중립

        # 볼륨 가중치 (시간대별)
        hour = datetime.now().hour
        if 9 <= hour <= 16:  # 미국 장중
            pattern_parts.append('H')  # High volume
        else:
            pattern_parts.append('L')  # Low volume

        return ''.join(pattern_parts)

    def analyze_pattern(self, symbol, pattern):
        """패턴 분석 및 신호 생성"""
        if not pattern or pattern not in self.pattern_memory[symbol]:
            return None, 0

        memory = self.pattern_memory[symbol][pattern]

        # 충분한 데이터 필요
        if memory['count'] < 3:
            return None, 0

        win_rate = memory['wins'] / memory['count']
        avg_pnl = memory['total_pnl'] / memory['count']

        # 신호 생성
        if win_rate >= 0.65 and avg_pnl > 0.5:
            confidence = min(win_rate * 1.2, 0.95)
            return 'BUY', confidence
        elif win_rate <= 0.35 and avg_pnl < -0.5:
            confidence = min((1 - win_rate) * 1.2, 0.95)
            return 'SELL', confidence

        return None, 0

    def update_pattern_memory(self, symbol, pattern, pnl):
        """패턴 메모리 업데이트"""
        if pattern not in self.pattern_memory[symbol]:
            self.pattern_memory[symbol][pattern] = {
                'count': 0,
                'wins': 0,
                'total_pnl': 0.0,
                'last_updated': datetime.now()
            }

        memory = self.pattern_memory[symbol][pattern]
        memory['count'] += 1
        memory['total_pnl'] += pnl
        if pnl > 0:
            memory['wins'] += 1
        memory['last_updated'] = datetime.now()

    def check_positions(self):
        """포지션 체크 및 청산"""
        for symbol in list(self.positions.keys()):
            pos = self.positions[symbol]
            current_price = self.get_realtime_price(symbol)

            if not current_price:
                continue

            # 수익률 계산
            if pos['side'] == 'BUY':
                pnl = (current_price / pos['entry_price'] - 1) * 100
            else:
                pnl = (pos['entry_price'] / current_price - 1) * 100

            # 레버리지 적용
            if symbol == 'NVDL':
                pnl *= 3  # 3x 레버리지
            else:  # NVDQ
                pnl *= 2  # 2x 레버리지

            # 보유 시간
            hold_time = (datetime.now() - pos['entry_time']).seconds / 60  # 분

            # 청산 조건
            should_close = False
            reason = ""

            if pnl >= 2.5:  # 2.5% 익절
                should_close = True
                reason = "Take Profit"
            elif pnl <= -1.5:  # 1.5% 손절
                should_close = True
                reason = "Stop Loss"
            elif hold_time >= 60:  # 60분 경과
                should_close = True
                reason = "Time Exit"

            if should_close:
                # 청산 실행
                profit = pos['size'] * (pnl / 100)
                self.balance += profit

                # 패턴 학습
                self.update_pattern_memory(symbol, pos['pattern'], pnl)

                # 통계 업데이트
                self.stats['trades'] += 1
                self.stats['total_pnl'] += pnl

                if pnl > 0:
                    self.stats['wins'] += 1
                    self.stats['consecutive_wins'] += 1
                    self.stats['consecutive_losses'] = 0
                else:
                    self.stats['consecutive_losses'] += 1
                    self.stats['consecutive_wins'] = 0

                print(f"[{datetime.now().strftime('%H:%M:%S')}] CLOSE {symbol} @ ${current_price:.2f}")
                print(f"  PnL: {pnl:+.2f}% ({reason}) | Balance: ${self.balance:.2f}")

                del self.positions[symbol]

    def execute_trade(self, symbol):
        """거래 실행"""
        # 이미 포지션이 있으면 스킵
        if symbol in self.positions:
            return

        # 현재 가격
        current_price = self.get_realtime_price(symbol)
        if not current_price:
            return

        # 패턴 추출
        pattern = self.extract_pattern(symbol)
        if not pattern:
            return

        # 신호 분석
        signal, confidence = self.analyze_pattern(symbol, pattern)

        # 새 패턴 탐색 (20% 확률)
        if not signal and pattern not in self.pattern_memory[symbol]:
            if self.stats['consecutive_losses'] < 3:  # 연속 3패 미만일 때만
                import random
                if random.random() < 0.2:
                    signal = random.choice(['BUY', 'SELL'])
                    confidence = 0.5
                    print(f"  Exploring new pattern: {pattern}")

        if signal and confidence >= 0.5:
            # 포지션 크기 (신뢰도 기반)
            base_size = 0.2  # 기본 20%

            # 연속 승/패 조정
            if self.stats['consecutive_wins'] >= 3:
                base_size *= 1.5  # 연승 중이면 크기 증가
            elif self.stats['consecutive_losses'] >= 2:
                base_size *= 0.5  # 연패 중이면 크기 감소

            position_size = self.balance * base_size * confidence

            # 포지션 생성
            self.positions[symbol] = {
                'side': signal,
                'entry_price': current_price,
                'entry_time': datetime.now(),
                'pattern': pattern,
                'size': position_size,
                'confidence': confidence
            }

            print(f"[{datetime.now().strftime('%H:%M:%S')}] {signal} {symbol} @ ${current_price:.2f}")
            print(f"  Pattern: {pattern[:10]}... | Confidence: {confidence:.1%}")

    def print_status(self):
        """상태 출력"""
        total_pnl = (self.balance / self.initial_balance - 1) * 100
        win_rate = (self.stats['wins'] / max(self.stats['trades'], 1)) * 100

        print(f"\n{'='*50}")
        print(f"PERFORMANCE UPDATE")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Balance: ${self.balance:.2f} ({total_pnl:+.2f}%)")
        print(f"Trades: {self.stats['trades']} | Win Rate: {win_rate:.1f}%")
        print(f"Positions: {list(self.positions.keys())}")
        print(f"Learned Patterns: {sum(len(p) for p in self.pattern_memory.values())}")

        if self.stats['consecutive_wins'] > 0:
            print(f"Winning Streak: {self.stats['consecutive_wins']}")
        elif self.stats['consecutive_losses'] > 0:
            print(f"Losing Streak: {self.stats['consecutive_losses']}")

        print("="*50 + "\n")

    def run(self):
        """메인 실행 루프"""
        print("Initializing with historical data...")

        # 초기 히스토리 로드
        for symbol in ['NVDL', 'NVDQ']:
            if self.get_historical_data(symbol):
                print(f"  Loaded history for {symbol}")

        print("\nStarting realtime trading...\n")

        last_trade_time = datetime.now()
        last_status_time = datetime.now()
        cycle = 0

        try:
            while True:
                cycle += 1
                current_time = datetime.now()

                # 15분마다 거래 체크
                if (current_time - last_trade_time).seconds >= 900:  # 15분 = 900초
                    print(f"\n[Cycle {cycle}] Checking market...")

                    for symbol in ['NVDL', 'NVDQ']:
                        self.execute_trade(symbol)

                    self.check_positions()
                    last_trade_time = current_time

                    # 메모리 저장
                    if cycle % 5 == 0:
                        self.save_memory()

                # 5분마다 상태 출력
                if (current_time - last_status_time).seconds >= 300:  # 5분
                    self.print_status()
                    last_status_time = current_time

                # 30초 대기
                time.sleep(30)

        except KeyboardInterrupt:
            print("\n\nStopping trader...")
            self.print_status()
            self.save_memory()

            # 최종 결과 저장
            with open('realtime_results.json', 'w') as f:
                json.dump({
                    'balance': self.balance,
                    'stats': self.stats,
                    'patterns_learned': sum(len(p) for p in self.pattern_memory.values()),
                    'timestamp': datetime.now().isoformat()
                }, f, indent=2)

            print("Results saved to realtime_results.json")

if __name__ == "__main__":
    API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"
    trader = RealtimeLearningTrader(API_KEY)
    trader.run()