#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
백테스트 학습 시스템
- 실제 과거 데이터로 학습
- 빠른 백테스팅
"""

import requests
import json
from datetime import datetime, timedelta
from collections import defaultdict

class BacktestLearner:
    def __init__(self, api_key):
        self.api_key = api_key
        self.balance = 10000.0
        self.initial_balance = self.balance

        # 패턴 메모리
        self.patterns = defaultdict(lambda: {'count': 0, 'wins': 0, 'total_pnl': 0})

        # 통계
        self.total_trades = 0
        self.winning_trades = 0

    def fetch_historical_data(self, symbol, timeframe='15min'):
        """과거 데이터 가져오기"""
        print(f"Fetching {timeframe} data for {symbol}...")

        url = f"https://financialmodelingprep.com/api/v3/historical-chart/{timeframe}/{symbol}"
        params = {'apikey': self.api_key}

        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data:
                    # 최근 500개 캔들 (약 5일)
                    return data[:500]
        except Exception as e:
            print(f"Error: {e}")

        return None

    def extract_pattern(self, candles, index):
        """패턴 추출"""
        if index < 5:
            return None

        pattern = []
        for i in range(index-4, index):
            prev = candles[i+1]
            curr = candles[i]

            change = (float(curr['close']) - float(prev['close'])) / float(prev['close']) * 100

            if change > 0.3:
                pattern.append('U')
            elif change < -0.3:
                pattern.append('D')
            else:
                pattern.append('N')

        return ''.join(pattern)

    def backtest(self, symbol):
        """백테스트 실행"""
        data = self.fetch_historical_data(symbol)
        if not data:
            print(f"No data for {symbol}")
            return

        print(f"Running backtest on {len(data)} candles...")

        position = None
        trades = []

        for i in range(len(data)-5, 5, -1):  # 역순으로 (과거부터)
            pattern = self.extract_pattern(data, i)
            if not pattern:
                continue

            current = data[i]
            current_price = float(current['close'])

            if position:
                # 포지션 청산 체크
                entry_price = position['entry_price']
                holding_bars = position['entry_index'] - i

                if symbol == 'NVDL':
                    pnl = (current_price / entry_price - 1) * 100 * 3  # 3x 레버리지
                else:  # NVDQ
                    pnl = (entry_price / current_price - 1) * 100 * 2  # 2x 역레버리지

                # 청산 조건
                if pnl >= 2 or pnl <= -1.5 or holding_bars >= 4:
                    # 청산
                    profit = self.balance * 0.2 * (pnl / 100)
                    self.balance += profit

                    # 패턴 학습
                    pattern_key = f"{symbol}_{position['pattern']}"
                    self.patterns[pattern_key]['count'] += 1
                    self.patterns[pattern_key]['total_pnl'] += pnl
                    if pnl > 0:
                        self.patterns[pattern_key]['wins'] += 1
                        self.winning_trades += 1

                    self.total_trades += 1

                    trades.append({
                        'symbol': symbol,
                        'pnl': pnl,
                        'pattern': position['pattern']
                    })

                    position = None

            else:
                # 진입 신호 체크
                pattern_key = f"{symbol}_{pattern}"

                if pattern_key in self.patterns:
                    p = self.patterns[pattern_key]
                    if p['count'] >= 3:
                        win_rate = p['wins'] / p['count']
                        avg_pnl = p['total_pnl'] / p['count']

                        if win_rate > 0.6 and avg_pnl > 0.5:
                            # 매수 신호
                            position = {
                                'entry_price': current_price,
                                'entry_index': i,
                                'pattern': pattern
                            }

        # 결과 출력
        print(f"\n{symbol} Backtest Results:")
        print(f"  Trades: {len(trades)}")
        if trades:
            wins = len([t for t in trades if t['pnl'] > 0])
            avg_pnl = sum(t['pnl'] for t in trades) / len(trades)
            print(f"  Win Rate: {wins/len(trades)*100:.1f}%")
            print(f"  Avg PnL: {avg_pnl:.2f}%")

    def run_full_backtest(self):
        """전체 백테스트"""
        print("="*50)
        print("Starting Backtest")
        print("="*50 + "\n")

        # 각 심볼 백테스트
        for symbol in ['NVDL', 'NVDQ']:
            self.backtest(symbol)

        # 최종 결과
        print("\n" + "="*50)
        print("BACKTEST COMPLETE")
        print("="*50)

        final_pnl = (self.balance / self.initial_balance - 1) * 100
        win_rate = (self.winning_trades / max(self.total_trades, 1)) * 100

        print(f"Final Balance: ${self.balance:.2f} ({final_pnl:+.2f}%)")
        print(f"Total Trades: {self.total_trades}")
        print(f"Win Rate: {win_rate:.1f}%")

        # 상위 패턴
        print("\nTop Patterns:")
        patterns_list = []
        for pattern_key, data in self.patterns.items():
            if data['count'] >= 3:
                win_rate = data['wins'] / data['count']
                avg_pnl = data['total_pnl'] / data['count']
                patterns_list.append((pattern_key, win_rate, avg_pnl, data['count']))

        patterns_list.sort(key=lambda x: x[2], reverse=True)

        for pattern, wr, avg, count in patterns_list[:10]:
            print(f"  {pattern}: {wr*100:.0f}% win, {avg:+.1f}% avg (n={count})")

        # 결과 저장
        with open('backtest_results.json', 'w') as f:
            json.dump({
                'final_balance': self.balance,
                'total_trades': self.total_trades,
                'win_rate': win_rate,
                'top_patterns': [
                    {'pattern': p[0], 'win_rate': p[1], 'avg_pnl': p[2], 'count': p[3]}
                    for p in patterns_list[:20]
                ],
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)

        print("\nResults saved to backtest_results.json")

if __name__ == "__main__":
    API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"
    backtester = BacktestLearner(API_KEY)
    backtester.run_full_backtest()