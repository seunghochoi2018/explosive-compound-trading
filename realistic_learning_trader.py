#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
현실적인 학습 트레이더
- 15분 주기로 실제 거래
- 패턴 학습 기반
"""

import random
import time
import json
from datetime import datetime, timedelta
from collections import deque

class RealisticLearningTrader:
    def __init__(self):
        print("="*50)
        print("Realistic Learning Trader")
        print("15-minute intervals, pattern-based learning")
        print("="*50)

        self.balance = 10000.0
        self.initial_balance = self.balance

        # 가격 히스토리 (15분 봉)
        self.candles = {
            'NVDL': deque(maxlen=100),
            'NVDQ': deque(maxlen=100)
        }

        # 학습 데이터
        self.patterns = {
            'NVDL': {},  # pattern -> [results]
            'NVDQ': {}
        }

        # 현재 포지션
        self.positions = {}

        # 통계
        self.stats = {
            'trades': 0,
            'wins': 0,
            'total_profit': 0.0
        }

        # 시간 설정
        self.interval = 15  # 15분 주기
        self.last_trade_time = {}

    def simulate_15min_candle(self, symbol):
        """15분 캔들 시뮬레이션"""
        base = 50.0 if symbol == 'NVDL' else 25.0

        # 이전 종가 기반
        if len(self.candles[symbol]) > 0:
            prev_close = self.candles[symbol][-1]['close']
            volatility = 0.02 if symbol == 'NVDL' else 0.015  # NVDL이 더 변동성 큼

            # 15분 동안의 가격 변화 시뮬레이션
            change = random.gauss(0, volatility)
            open_price = prev_close * (1 + random.gauss(0, 0.005))
            high = open_price * (1 + abs(random.gauss(0, volatility)))
            low = open_price * (1 - abs(random.gauss(0, volatility)))
            close = prev_close * (1 + change)

        else:
            open_price = base + random.uniform(-1, 1)
            high = open_price * 1.01
            low = open_price * 0.99
            close = open_price * (1 + random.uniform(-0.01, 0.01))

        volume = random.randint(100000, 1000000)

        candle = {
            'time': datetime.now(),
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        }

        self.candles[symbol].append(candle)
        return candle

    def get_pattern(self, symbol):
        """최근 5개 캔들로 패턴 생성"""
        if len(self.candles[symbol]) < 5:
            return None

        recent = list(self.candles[symbol])[-5:]
        pattern = []

        for i in range(len(recent)):
            candle = recent[i]

            # 캔들 특성
            body_size = abs(candle['close'] - candle['open']) / candle['open']
            is_bullish = candle['close'] > candle['open']

            # 이전 캔들 대비 변화
            if i > 0:
                prev = recent[i-1]
                change = (candle['close'] - prev['close']) / prev['close']

                if change > 0.005:  # 0.5% 이상 상승
                    pattern.append('U')
                elif change < -0.005:  # 0.5% 이상 하락
                    pattern.append('D')
                else:
                    pattern.append('N')  # 중립

        return ''.join(pattern)

    def learn_from_trade(self, symbol, pattern, profit):
        """거래 결과 학습"""
        if pattern not in self.patterns[symbol]:
            self.patterns[symbol][pattern] = []

        self.patterns[symbol][pattern].append(profit)

        # 최대 10개 결과만 유지
        if len(self.patterns[symbol][pattern]) > 10:
            self.patterns[symbol][pattern].pop(0)

    def predict_action(self, symbol):
        """패턴 기반 예측"""
        pattern = self.get_pattern(symbol)
        if not pattern:
            return None

        # 해당 패턴의 과거 성과 확인
        if pattern in self.patterns[symbol]:
            results = self.patterns[symbol][pattern]
            if len(results) >= 2:  # 최소 2번 경험
                avg_profit = sum(results) / len(results)
                win_rate = len([r for r in results if r > 0]) / len(results)

                # 승률 60% 이상이고 평균 수익 양수면 매수
                if win_rate >= 0.6 and avg_profit > 0:
                    confidence = min(win_rate, 0.9)
                    return ('BUY', confidence)
                # 승률 40% 이하고 평균 손실이면 매도
                elif win_rate <= 0.4 and avg_profit < 0:
                    confidence = min(1 - win_rate, 0.9)
                    return ('SELL', confidence)

        # 경험 없으면 랜덤 (탐색)
        if random.random() < 0.3:  # 30% 확률로 탐색
            return (random.choice(['BUY', 'SELL']), 0.5)

        return None

    def execute_trade(self, symbol):
        """거래 실행 (15분 주기)"""
        # 시간 체크
        now = datetime.now()
        last_time = self.last_trade_time.get(symbol, datetime.min)

        if (now - last_time).seconds < self.interval * 60:
            return False

        # 새 캔들 생성
        candle = self.simulate_15min_candle(symbol)

        # 기존 포지션 체크
        if symbol in self.positions:
            pos = self.positions[symbol]
            current_price = candle['close']

            # 수익률 계산
            if pos['side'] == 'LONG':
                pnl = (current_price / pos['entry_price'] - 1) * 100
                # NVDL은 3배 레버리지
                if symbol == 'NVDL':
                    pnl *= 3
            else:  # SHORT
                pnl = (pos['entry_price'] / current_price - 1) * 100
                # NVDQ는 2배 역레버리지
                if symbol == 'NVDQ':
                    pnl *= 2

            # 청산 조건
            should_close = False

            if pnl >= 3:  # 3% 익절
                should_close = True
                reason = "Take Profit"
            elif pnl <= -2:  # 2% 손절
                should_close = True
                reason = "Stop Loss"
            elif (now - pos['entry_time']).seconds >= 3600:  # 1시간 경과
                should_close = True
                reason = "Time Exit"

            if should_close:
                # 포지션 청산
                profit = pos['size'] * (pnl / 100)
                self.balance += profit

                # 학습
                self.learn_from_trade(symbol, pos['pattern'], pnl)

                # 통계 업데이트
                self.stats['trades'] += 1
                if pnl > 0:
                    self.stats['wins'] += 1
                self.stats['total_profit'] += pnl

                print(f"[{now.strftime('%H:%M')}] CLOSE {symbol} @ {current_price:.2f} "
                      f"PnL: {pnl:+.2f}% ({reason}) Balance: ${self.balance:.2f}")

                del self.positions[symbol]

        else:
            # 새 포지션 열기
            action = self.predict_action(symbol)

            if action:
                signal, confidence = action
                pattern = self.get_pattern(symbol)

                if confidence >= 0.5:  # 50% 이상 신뢰도
                    size = self.balance * 0.2 * confidence  # 신뢰도에 따른 크기

                    self.positions[symbol] = {
                        'side': 'LONG' if signal == 'BUY' else 'SHORT',
                        'entry_price': candle['close'],
                        'entry_time': now,
                        'pattern': pattern,
                        'size': size
                    }

                    print(f"[{now.strftime('%H:%M')}] {signal} {symbol} @ {candle['close']:.2f} "
                          f"Pattern: {pattern} Confidence: {confidence:.1%}")

        self.last_trade_time[symbol] = now
        return True

    def print_status(self):
        """상태 출력"""
        total_pnl = (self.balance / self.initial_balance - 1) * 100
        win_rate = (self.stats['wins'] / max(self.stats['trades'], 1)) * 100

        print(f"\n{'='*50}")
        print(f"Balance: ${self.balance:.2f} ({total_pnl:+.2f}%)")
        print(f"Trades: {self.stats['trades']} | Win Rate: {win_rate:.1f}%")
        print(f"Avg Profit: {self.stats['total_profit']/max(self.stats['trades'],1):.2f}%")
        print(f"Positions: {list(self.positions.keys())}")
        print(f"Learned Patterns: NVDL={len(self.patterns['NVDL'])} NVDQ={len(self.patterns['NVDQ'])}")

    def save_learning(self):
        """학습 데이터 저장"""
        data = {
            'patterns': self.patterns,
            'stats': self.stats,
            'balance': self.balance,
            'timestamp': datetime.now().isoformat()
        }

        with open('realistic_learning_data.json', 'w') as f:
            json.dump(data, f, indent=2)

        print("Learning data saved!")

    def run(self):
        """메인 실행"""
        print("\nStarting realistic learning trader...")
        print("Trading every 15 minutes based on learned patterns\n")

        cycle = 0
        last_status = time.time()

        try:
            while True:
                cycle += 1

                # 각 심볼 거래 체크
                for symbol in ['NVDL', 'NVDQ']:
                    self.execute_trade(symbol)

                # 상태 출력 (5분마다)
                if time.time() - last_status >= 300:
                    self.print_status()
                    last_status = time.time()

                # 저장 (10사이클마다)
                if cycle % 10 == 0:
                    self.save_learning()

                # 1분 대기 (15분 주기 체크용)
                time.sleep(60)

        except KeyboardInterrupt:
            print("\n\nStopping trader...")
            self.print_status()
            self.save_learning()

if __name__ == "__main__":
    trader = RealisticLearningTrader()
    trader.run()