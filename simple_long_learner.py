#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
심플 롱 학습 시스템
- NVDL 또는 NVDQ 중 하나만 선택해서 롱
- 임계값이나 제한 없이 자유롭게 학습
"""

import requests
import json
import time
from datetime import datetime
from collections import defaultdict
import random

class SimpleLongLearner:
    def __init__(self, api_key):
        print("="*50)
        print("Simple Long Learning System")
        print("Choose ONE: NVDL or NVDQ for LONG only")
        print("="*50)

        self.api_key = api_key
        self.balance = 10000.0
        self.initial_balance = self.balance

        # 가격 히스토리
        self.price_history = {
            'NVDL': [],
            'NVDQ': []
        }

        # 학습 메모리: symbol -> [results]
        self.symbol_performance = {
            'NVDL': [],
            'NVDQ': []
        }

        # 현재 포지션 (하나만)
        self.current_position = None

        # 통계
        self.stats = {
            'nvdl_trades': 0,
            'nvdq_trades': 0,
            'nvdl_wins': 0,
            'nvdq_wins': 0,
            'total_trades': 0
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
                    self.price_history[symbol].append({
                        'time': datetime.now(),
                        'price': price
                    })
                    # 최대 20개만 유지
                    if len(self.price_history[symbol]) > 20:
                        self.price_history[symbol].pop(0)
                    return price
        except:
            pass

        # 시뮬레이션 가격
        base = 84.0 if symbol == 'NVDL' else 1.0
        if self.price_history[symbol]:
            last_price = self.price_history[symbol][-1]['price']
            change = random.uniform(-0.02, 0.02)
            new_price = last_price * (1 + change)
        else:
            new_price = base + random.uniform(-2, 2)

        self.price_history[symbol].append({
            'time': datetime.now(),
            'price': new_price
        })
        return new_price

    def choose_symbol(self):
        """어떤 심볼을 선택할지 결정"""
        # 과거 성과 기반
        nvdl_perf = self.get_symbol_score('NVDL')
        nvdq_perf = self.get_symbol_score('NVDQ')

        print(f"  NVDL score: {nvdl_perf:.2f}")
        print(f"  NVDQ score: {nvdq_perf:.2f}")

        # 성과가 좋은 쪽 선택, 또는 랜덤
        if abs(nvdl_perf - nvdq_perf) < 0.5:  # 비슷하면 랜덤
            return random.choice(['NVDL', 'NVDQ'])
        elif nvdl_perf > nvdq_perf:
            return 'NVDL'
        else:
            return 'NVDQ'

    def get_symbol_score(self, symbol):
        """심볼 성과 점수"""
        results = self.symbol_performance[symbol]
        if len(results) < 3:
            return 0.0  # 경험 부족

        # 최근 10개 결과만 고려
        recent = results[-10:]
        avg_pnl = sum(recent) / len(recent)
        win_rate = len([r for r in recent if r > 0]) / len(recent)

        # 종합 점수
        score = avg_pnl * 0.7 + (win_rate - 0.5) * 10  # 승률 가중
        return score

    def open_position(self, symbol):
        """포지션 오픈"""
        price = self.get_current_price(symbol)
        size = self.balance * 0.3  # 30% 사용

        self.current_position = {
            'symbol': symbol,
            'entry_price': price,
            'entry_time': datetime.now(),
            'size': size
        }

        print(f"[{datetime.now().strftime('%H:%M:%S')}] LONG {symbol} @ ${price:.2f}")
        print(f"  Position Size: ${size:.0f} ({size/self.balance*100:.0f}%)")

    def check_exit(self):
        """포지션 청산 체크"""
        if not self.current_position:
            return

        symbol = self.current_position['symbol']
        current_price = self.get_current_price(symbol)
        entry_price = self.current_position['entry_price']

        # 수익률 계산
        raw_pnl = (current_price / entry_price - 1) * 100

        # 레버리지 적용
        if symbol == 'NVDL':
            pnl = raw_pnl * 3  # 3x 레버리지
        else:  # NVDQ
            pnl = raw_pnl * 2  # 2x 레버리지

        # 보유 시간
        hold_minutes = (datetime.now() - self.current_position['entry_time']).total_seconds() / 60

        # 자유로운 청산 조건 (제한 없음)
        should_close = False
        reason = ""

        # 기본적인 청산 조건들
        if pnl >= 5:  # 5% 이상 수익
            should_close = True
            reason = "Big Profit"
        elif pnl <= -3:  # 3% 이상 손실
            should_close = True
            reason = "Cut Loss"
        elif hold_minutes >= 60:  # 60분 경과
            should_close = True
            reason = "Time Exit"
        elif random.random() < 0.05:  # 5% 확률로 랜덤 청산
            should_close = True
            reason = "Random Exit"

        if should_close:
            # 청산 실행
            profit = self.current_position['size'] * (pnl / 100)
            self.balance += profit

            # 학습 데이터 저장
            self.symbol_performance[symbol].append(pnl)

            # 통계 업데이트
            self.stats['total_trades'] += 1
            if symbol == 'NVDL':
                self.stats['nvdl_trades'] += 1
                if pnl > 0:
                    self.stats['nvdl_wins'] += 1
            else:
                self.stats['nvdq_trades'] += 1
                if pnl > 0:
                    self.stats['nvdq_wins'] += 1

            print(f"[{datetime.now().strftime('%H:%M:%S')}] CLOSE {symbol} @ ${current_price:.2f}")
            print(f"  PnL: {pnl:+.2f}% ({reason}) | Balance: ${self.balance:.2f}")
            print(f"  Hold time: {hold_minutes:.0f} minutes")

            # 심볼별 누적 성과
            symbol_results = self.symbol_performance[symbol]
            if len(symbol_results) >= 3:
                avg = sum(symbol_results[-10:]) / min(len(symbol_results), 10)
                win_rate = len([r for r in symbol_results[-10:] if r > 0]) / min(len(symbol_results), 10)
                print(f"  {symbol} Performance: {win_rate*100:.0f}% win, {avg:+.1f}% avg")

            self.current_position = None

    def print_status(self):
        """상태 출력"""
        total_pnl = (self.balance / self.initial_balance - 1) * 100

        print(f"\n{'='*50}")
        print(f"SIMPLE LONG LEARNING")
        print(f"Balance: ${self.balance:.2f} ({total_pnl:+.2f}%)")
        print(f"Total Trades: {self.stats['total_trades']}")

        # 심볼별 성과
        if self.stats['nvdl_trades'] > 0:
            nvdl_wr = self.stats['nvdl_wins'] / self.stats['nvdl_trades'] * 100
            print(f"NVDL: {self.stats['nvdl_trades']} trades, {nvdl_wr:.0f}% win")

        if self.stats['nvdq_trades'] > 0:
            nvdq_wr = self.stats['nvdq_wins'] / self.stats['nvdq_trades'] * 100
            print(f"NVDQ: {self.stats['nvdq_trades']} trades, {nvdq_wr:.0f}% win")

        # 현재 포지션
        if self.current_position:
            pos = self.current_position
            current_price = self.price_history[pos['symbol']][-1]['price']
            unrealized_pnl = (current_price / pos['entry_price'] - 1) * 100
            if pos['symbol'] == 'NVDL':
                unrealized_pnl *= 3
            else:
                unrealized_pnl *= 2

            hold_time = (datetime.now() - pos['entry_time']).total_seconds() / 60
            print(f"Current Position: {pos['symbol']} ({unrealized_pnl:+.1f}%, {hold_time:.0f}min)")
        else:
            print("No Position")

        print("="*50 + "\n")

    def run(self):
        """메인 실행 루프"""
        print("Starting simple long learning...\n")

        cycle = 0
        last_status = time.time()
        last_trade = time.time()

        try:
            while True:
                cycle += 1

                # 현재 포지션 체크
                self.check_exit()

                # 새 포지션 (30초마다 체크)
                if not self.current_position and time.time() - last_trade >= 30:
                    print("\nChoosing symbol...")
                    chosen_symbol = self.choose_symbol()
                    print(f"Selected: {chosen_symbol}")
                    self.open_position(chosen_symbol)
                    last_trade = time.time()

                # 20초마다 상태 출력
                if time.time() - last_status >= 20:
                    self.print_status()
                    last_status = time.time()

                # 5초 대기
                time.sleep(5)

        except KeyboardInterrupt:
            print("\nStopping...")
            self.print_status()

            # 결과 저장
            with open('simple_long_results.json', 'w') as f:
                json.dump({
                    'balance': self.balance,
                    'stats': self.stats,
                    'nvdl_performance': self.symbol_performance['NVDL'],
                    'nvdq_performance': self.symbol_performance['NVDQ'],
                    'timestamp': datetime.now().isoformat()
                }, f, indent=2)

            print("Results saved!")

if __name__ == "__main__":
    API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"
    learner = SimpleLongLearner(API_KEY)
    learner.run()