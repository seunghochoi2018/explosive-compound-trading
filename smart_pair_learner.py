#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
스마트 페어 학습 시스템
- NVDL(3x 상승)과 NVDQ(2x 하락)의 특성 고려
- 서로 반대 방향 거래로 헷징 효과
- 실시간 학습
"""

import requests
import json
import time
from datetime import datetime
from collections import defaultdict
import random

class SmartPairLearner:
    def __init__(self, api_key):
        print("="*50)
        print("Smart Pair Learning System")
        print("NVDL (3x up) vs NVDQ (2x down) hedging")
        print("="*50)

        self.api_key = api_key
        self.balance = 10000.0
        self.initial_balance = self.balance

        # 가격 데이터
        self.price_data = {
            'NVDL': [],
            'NVDQ': []
        }

        # 시장 전망별 학습
        self.market_patterns = defaultdict(list)  # market_outlook -> [results]

        # 현재 포지션
        self.positions = {}

        # 통계
        self.stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'pair_trades': 0,  # 페어 거래 수
            'single_trades': 0  # 단일 거래 수
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
                    # 최대 30개만 유지
                    if len(self.price_data[symbol]) > 30:
                        self.price_data[symbol].pop(0)
                    return price
        except:
            pass

        # 시뮬레이션 가격
        base = 84.0 if symbol == 'NVDL' else 1.0
        if self.price_data[symbol]:
            last_price = self.price_data[symbol][-1]['price']
            # NVDL과 NVDQ는 보통 반대로 움직임
            if len(self.price_data['NVDL']) > 0 and len(self.price_data['NVDQ']) > 0:
                # 상관관계 고려
                change = random.uniform(-0.015, 0.015)
                if symbol == 'NVDQ':
                    change *= -0.7  # NVDQ는 반대 방향으로 더 약하게
                new_price = last_price * (1 + change)
            else:
                new_price = last_price * (1 + random.uniform(-0.01, 0.01))
        else:
            new_price = base + random.uniform(-1, 1)

        self.price_data[symbol].append({
            'time': datetime.now(),
            'price': new_price
        })
        return new_price

    def analyze_market_sentiment(self):
        """시장 전망 분석"""
        if len(self.price_data['NVDL']) < 5 or len(self.price_data['NVDQ']) < 5:
            return 'NEUTRAL'

        # 최근 5개 가격으로 트렌드 분석
        nvdl_prices = [d['price'] for d in self.price_data['NVDL'][-5:]]
        nvdq_prices = [d['price'] for d in self.price_data['NVDQ'][-5:]]

        nvdl_trend = (nvdl_prices[-1] - nvdl_prices[0]) / nvdl_prices[0] * 100
        nvdq_trend = (nvdq_prices[-1] - nvdq_prices[0]) / nvdq_prices[0] * 100

        # NVDQ는 역방향이므로 반전
        nvdq_trend = -nvdq_trend

        # 두 트렌드의 합으로 시장 방향 판단
        combined_trend = (nvdl_trend + nvdq_trend) / 2

        if combined_trend > 0.5:
            return 'BULLISH'
        elif combined_trend < -0.5:
            return 'BEARISH'
        else:
            return 'NEUTRAL'

    def decide_strategy(self, market_outlook):
        """시장 전망에 따른 전략 결정"""
        # 과거 경험 확인
        if market_outlook in self.market_patterns:
            results = self.market_patterns[market_outlook]
            if len(results) >= 3:
                avg_pnl = sum(results) / len(results)
                win_rate = len([r for r in results if r > 0]) / len(results)

                # 경험 기반 결정
                if win_rate >= 0.65 and avg_pnl > 0.5:
                    if market_outlook == 'BULLISH':
                        return {'NVDL': 'BUY'}  # 상승장에서 NVDL 매수
                    elif market_outlook == 'BEARISH':
                        return {'NVDQ': 'BUY'}  # 하락장에서 NVDQ 매수
                    else:
                        return {'NVDL': 'BUY', 'NVDQ': 'BUY'}  # 헷징

        # 탐색적 거래 (새로운 패턴 시도)
        if random.random() < 0.5:  # 50% 확률
            strategies = [
                {'NVDL': 'BUY'},           # 상승 베팅
                {'NVDQ': 'BUY'},           # 하락 베팅
                {'NVDL': 'BUY', 'NVDQ': 'BUY'},  # 페어 거래 (헷징)
                {}  # 관망
            ]
            return random.choice(strategies)

        return {}

    def execute_strategy(self, strategy, market_outlook):
        """전략 실행"""
        if not strategy:
            return

        for symbol, action in strategy.items():
            if symbol in self.positions:
                continue

            price = self.get_current_price(symbol)
            size = self.balance * 0.15  # 15% 사용

            self.positions[symbol] = {
                'action': action,
                'entry_price': price,
                'entry_time': datetime.now(),
                'market_outlook': market_outlook,
                'size': size
            }

            print(f"[{datetime.now().strftime('%H:%M:%S')}] {action} {symbol} @ ${price:.2f}")
            print(f"  Market View: {market_outlook}")

            self.stats['total_trades'] += 1
            if len(strategy) > 1:
                self.stats['pair_trades'] += 1
            else:
                self.stats['single_trades'] += 1

    def check_exits(self):
        """포지션 청산 체크"""
        for symbol in list(self.positions.keys()):
            pos = self.positions[symbol]
            current_price = self.get_current_price(symbol)

            # 수익률 계산
            if pos['action'] == 'BUY':
                if symbol == 'NVDL':
                    # NVDL: 가격 상승하면 수익
                    pnl = (current_price / pos['entry_price'] - 1) * 100 * 3  # 3x 레버리지
                else:  # NVDQ
                    # NVDQ: 기초자산 하락하면 수익 (하지만 ETF 가격은 상승)
                    pnl = (current_price / pos['entry_price'] - 1) * 100 * 2  # 2x 레버리지
            else:  # SELL
                pnl = (pos['entry_price'] / current_price - 1) * 100
                if symbol == 'NVDL':
                    pnl *= 3
                else:
                    pnl *= 2

            # 보유 시간 (초)
            hold_time = (datetime.now() - pos['entry_time']).total_seconds()

            # 청산 조건
            should_close = False
            reason = ""

            if pnl >= 2.0:  # 2% 익절
                should_close = True
                reason = "Take Profit"
            elif pnl <= -1.5:  # 1.5% 손절
                should_close = True
                reason = "Stop Loss"
            elif hold_time >= 1800:  # 30분 경과
                should_close = True
                reason = "Time Exit"

            if should_close:
                # 청산 실행
                profit = pos['size'] * (pnl / 100)
                self.balance += profit

                # 시장 전망별 결과 학습
                self.market_patterns[pos['market_outlook']].append(pnl)

                if pnl > 0:
                    self.stats['winning_trades'] += 1

                print(f"[{datetime.now().strftime('%H:%M:%S')}] CLOSE {symbol} @ ${current_price:.2f}")
                print(f"  PnL: {pnl:+.2f}% ({reason}) | Balance: ${self.balance:.2f}")

                # 패턴 성과 출력
                outlook_results = self.market_patterns[pos['market_outlook']]
                if len(outlook_results) >= 3:
                    avg_pnl = sum(outlook_results) / len(outlook_results)
                    win_rate = len([r for r in outlook_results if r > 0]) / len(outlook_results)
                    print(f"  {pos['market_outlook']} pattern: {win_rate*100:.0f}% win, {avg_pnl:+.1f}% avg")

                del self.positions[symbol]

    def print_status(self):
        """상태 출력"""
        total_pnl = (self.balance / self.initial_balance - 1) * 100
        win_rate = (self.stats['winning_trades'] / max(self.stats['total_trades'], 1)) * 100

        print(f"\n{'='*50}")
        print(f"PAIR TRADING STATUS")
        print(f"Balance: ${self.balance:.2f} ({total_pnl:+.2f}%)")
        print(f"Trades: {self.stats['total_trades']} | Win Rate: {win_rate:.1f}%")
        print(f"Pair Trades: {self.stats['pair_trades']} | Single: {self.stats['single_trades']}")
        print(f"Active Positions: {list(self.positions.keys())}")

        # 시장 전망별 성과
        if self.market_patterns:
            print("\nMarket Outlook Performance:")
            for outlook, results in self.market_patterns.items():
                if len(results) >= 2:
                    avg = sum(results) / len(results)
                    wins = len([r for r in results if r > 0])
                    print(f"  {outlook}: {wins}/{len(results)} ({wins/len(results)*100:.0f}%) {avg:+.1f}%")

        # 현재 가격
        if self.price_data['NVDL'] and self.price_data['NVDQ']:
            nvdl_price = self.price_data['NVDL'][-1]['price']
            nvdq_price = self.price_data['NVDQ'][-1]['price']
            market = self.analyze_market_sentiment()
            print(f"\nCurrent: NVDL=${nvdl_price:.2f}, NVDQ=${nvdq_price:.2f}")
            print(f"Market Sentiment: {market}")

        print("="*50 + "\n")

    def run(self):
        """메인 실행 루프"""
        print("Starting smart pair learning...\n")

        cycle = 0
        last_status = time.time()
        last_trade = time.time()

        try:
            while True:
                cycle += 1

                # 가격 업데이트
                for symbol in ['NVDL', 'NVDQ']:
                    self.get_current_price(symbol)

                # 기존 포지션 체크
                self.check_exits()

                # 새 거래 (1분마다)
                if time.time() - last_trade >= 60:
                    market_outlook = self.analyze_market_sentiment()
                    strategy = self.decide_strategy(market_outlook)
                    if strategy:
                        self.execute_strategy(strategy, market_outlook)
                    last_trade = time.time()

                # 30초마다 상태 출력
                if time.time() - last_status >= 30:
                    self.print_status()
                    last_status = time.time()

                # 10초 대기
                time.sleep(10)

        except KeyboardInterrupt:
            print("\nStopping pair trading...")
            self.print_status()

            # 결과 저장
            with open('pair_trading_results.json', 'w') as f:
                json.dump({
                    'balance': self.balance,
                    'stats': self.stats,
                    'market_patterns': {k: v for k, v in self.market_patterns.items()},
                    'timestamp': datetime.now().isoformat()
                }, f, indent=2)

            print("Results saved!")

if __name__ == "__main__":
    API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"
    learner = SmartPairLearner(API_KEY)
    learner.run()