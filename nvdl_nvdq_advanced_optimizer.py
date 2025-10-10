#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVDL/NVDQ 고급 최적화 트레이딩 시스템 v2.0
- 개선된 신호 생성 로직
- 동적 포지션 관리
- 리스크 관리 강화
"""

import requests
import json
import time
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import random

class NVDLNVDQAdvancedOptimizer:
    def __init__(self, fmp_api_key: str):
        """고급 최적화 시스템 초기화"""
        print("=" * 70)
        print("NVDL/NVDQ Advanced Optimization Trading System v2.0")
        print("Improved Signal Generation and Risk Management")
        print("=" * 70)

        self.fmp_api_key = fmp_api_key
        self.balance = 10000.0
        self.initial_balance = self.balance
        self.symbols = ['NVDL', 'NVDQ']

        # 간소화된 시간주기 (성능 좋은 것만)
        self.timeframes = {
            '5m': {'interval': 300, 'hold_time': 900, 'min_profit': 0.015},
            '15m': {'interval': 900, 'hold_time': 1800, 'min_profit': 0.02},
            '1h': {'interval': 3600, 'hold_time': 7200, 'min_profit': 0.025}
        }

        # 전략별 성과 추적
        self.strategies = {}
        self.initialize_strategies()

        # 포지션 관리
        self.positions = {}
        self.max_positions = 3
        self.position_size = 0.2  # 20% per position

        # 시장 데이터 캐시
        self.price_cache = {}
        self.last_price_update = {}

        # 거래 기록
        self.trade_history = []
        self.winning_trades = 0
        self.total_trades = 0

        print(f"System initialization complete!")
        print(f"Initial balance: ${self.balance:,.2f}")

    def initialize_strategies(self):
        """전략 초기화"""
        strategy_types = ['momentum', 'reversal', 'breakout']

        for tf_name in self.timeframes.keys():
            for symbol in self.symbols:
                for strategy in strategy_types:
                    key = f"{tf_name}_{symbol}_{strategy}"
                    self.strategies[key] = {
                        'trades': 0,
                        'wins': 0,
                        'profit': 0.0,
                        'win_rate': 0.0,
                        'score': 1.0,
                        'active': True,
                        'last_signal': 0,
                        'consecutive_losses': 0
                    }

    def get_market_data(self, symbol: str) -> Dict:
        """시장 데이터 조회"""
        try:
            # 캐시 확인 (5초)
            now = time.time()
            if symbol in self.price_cache:
                if now - self.last_price_update.get(symbol, 0) < 5:
                    return self.price_cache[symbol]

            url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}"
            params = {'apikey': self.fmp_api_key}
            response = requests.get(url, params=params, timeout=5)

            if response.status_code == 200:
                data = response.json()
                if data:
                    market_data = {
                        'price': float(data[0]['price']),
                        'change': float(data[0]['changesPercentage']),
                        'volume': float(data[0].get('volume', 1000000)),
                        'high': float(data[0].get('dayHigh', data[0]['price'])),
                        'low': float(data[0].get('dayLow', data[0]['price']))
                    }
                    self.price_cache[symbol] = market_data
                    self.last_price_update[symbol] = now
                    return market_data

            # 폴백 데이터
            return {
                'price': 50.0 if symbol == 'NVDL' else 25.0,
                'change': random.uniform(-5, 5),
                'volume': 1000000,
                'high': 52.0 if symbol == 'NVDL' else 26.0,
                'low': 48.0 if symbol == 'NVDL' else 24.0
            }

        except Exception as e:
            print(f"WARNING: Data fetch failed ({symbol}): {e}")
            return None

    def calculate_indicators(self, symbol: str, timeframe: str) -> Dict:
        """기술적 지표 계산"""
        market_data = self.get_market_data(symbol)
        if not market_data:
            return {}

        price = market_data['price']
        high = market_data['high']
        low = market_data['low']
        change = market_data['change']

        # RSI 근사치
        rsi = 50 + (change * 5)  # -10% ~ +10% -> 0 ~ 100
        rsi = max(0, min(100, rsi))

        # 볼린저 밴드 위치
        range_pct = (price - low) / max(high - low, 0.01)

        # MACD 신호 (간단한 모멘텀)
        macd_signal = 1 if change > 0 else -1

        # 볼륨 강도
        volume_strength = min(market_data['volume'] / 1000000, 2.0)

        return {
            'rsi': rsi,
            'bb_position': range_pct,
            'macd': macd_signal,
            'volume': volume_strength,
            'change': change
        }

    def generate_signal(self, symbol: str, timeframe: str, strategy: str) -> Tuple[str, float]:
        """거래 신호 생성"""
        indicators = self.calculate_indicators(symbol, timeframe)
        if not indicators:
            return 'HOLD', 0.0

        signal_score = 0.0

        # 전략별 신호 로직
        if strategy == 'momentum':
            # 모멘텀 전략: 추세 추종
            if indicators['rsi'] > 60 and indicators['macd'] > 0:
                signal_score = 0.7 + (indicators['rsi'] - 60) / 100
            elif indicators['rsi'] < 40 and indicators['macd'] < 0:
                signal_score = -0.7 - (40 - indicators['rsi']) / 100

        elif strategy == 'reversal':
            # 반전 전략: 과매수/과매도
            if indicators['rsi'] > 70 and indicators['bb_position'] > 0.9:
                signal_score = -0.8  # 매도
            elif indicators['rsi'] < 30 and indicators['bb_position'] < 0.1:
                signal_score = 0.8   # 매수

        elif strategy == 'breakout':
            # 돌파 전략: 볼륨과 가격 움직임
            if abs(indicators['change']) > 2 and indicators['volume'] > 1.5:
                signal_score = 0.9 * (1 if indicators['change'] > 0 else -1)

        # NVDQ는 역방향이므로 신호 반전
        if symbol == 'NVDQ':
            signal_score *= -0.8  # 약간 보수적으로

        # 신호 결정
        if signal_score >= 0.6:
            return 'BUY', abs(signal_score)
        elif signal_score <= -0.6:
            return 'SELL', abs(signal_score)
        else:
            return 'HOLD', 0.0

    def execute_trade(self, symbol: str, timeframe: str, strategy: str,
                     signal: str, confidence: float) -> bool:
        """거래 실행"""
        if len(self.positions) >= self.max_positions:
            return False

        market_data = self.get_market_data(symbol)
        if not market_data:
            return False

        price = market_data['price']
        position_key = f"{timeframe}_{symbol}_{strategy}"

        # 이미 포지션이 있으면 스킵
        if position_key in self.positions:
            return False

        # 포지션 크기 계산
        strategy_data = self.strategies[position_key]
        size_multiplier = min(strategy_data['score'], 2.0)
        position_value = self.balance * self.position_size * size_multiplier * confidence

        # 레버리지
        leverage = 3.0 if symbol == 'NVDL' else 2.0

        # 포지션 생성
        self.positions[position_key] = {
            'symbol': symbol,
            'side': signal,
            'entry_price': price,
            'size': position_value,
            'leverage': leverage,
            'entry_time': datetime.now(),
            'timeframe': timeframe,
            'strategy': strategy,
            'stop_loss': price * (0.97 if signal == 'BUY' else 1.03),
            'take_profit': price * (1.03 if signal == 'BUY' else 0.97)
        }

        print(f"[{datetime.now().strftime('%H:%M:%S')}] "
              f"{signal} {symbol} @ ${price:.2f} "
              f"({strategy}/{timeframe}, Confidence: {confidence:.2%})")

        return True

    def check_exits(self):
        """포지션 종료 확인"""
        positions_to_close = []

        for key, pos in self.positions.items():
            market_data = self.get_market_data(pos['symbol'])
            if not market_data:
                continue

            current_price = market_data['price']
            entry_price = pos['entry_price']

            # 수익률 계산
            if pos['side'] == 'BUY':
                pnl = (current_price / entry_price - 1) * pos['leverage']
            else:
                pnl = (entry_price / current_price - 1) * pos['leverage']

            # 보유 시간
            hold_time = (datetime.now() - pos['entry_time']).seconds
            tf_config = self.timeframes[pos['timeframe']]

            # 종료 조건
            close_reason = None

            if pnl >= tf_config['min_profit']:
                close_reason = f"Target reached ({pnl:.2%})"
            elif pnl <= -0.03:  # 3% 손절
                close_reason = f"Stop loss ({pnl:.2%})"
            elif hold_time >= tf_config['hold_time']:
                close_reason = f"Time expired"
            elif pos['side'] == 'BUY' and current_price <= pos['stop_loss']:
                close_reason = "Stop loss"
            elif pos['side'] == 'SELL' and current_price >= pos['stop_loss']:
                close_reason = "Stop loss"

            if close_reason:
                self.close_position(key, current_price, pnl, close_reason)
                positions_to_close.append(key)

        # 포지션 제거
        for key in positions_to_close:
            del self.positions[key]

    def close_position(self, key: str, price: float, pnl: float, reason: str):
        """포지션 종료"""
        pos = self.positions[key]
        profit = pos['size'] * pnl
        self.balance += profit

        # 전략 성과 업데이트
        strategy_data = self.strategies[key]
        strategy_data['trades'] += 1
        strategy_data['profit'] += pnl

        if pnl > 0:
            strategy_data['wins'] += 1
            strategy_data['consecutive_losses'] = 0
            self.winning_trades += 1
        else:
            strategy_data['consecutive_losses'] += 1

        # 승률 및 점수 업데이트
        if strategy_data['trades'] > 0:
            strategy_data['win_rate'] = strategy_data['wins'] / strategy_data['trades']
            strategy_data['score'] = max(0.1,
                strategy_data['win_rate'] * 2 + strategy_data['profit'] / 10)

        # 연속 손실이 많으면 비활성화
        if strategy_data['consecutive_losses'] >= 5:
            strategy_data['active'] = False
            print(f"WARNING: Strategy disabled: {key}")

        self.total_trades += 1

        # 거래 기록
        self.trade_history.append({
            'time': datetime.now(),
            'symbol': pos['symbol'],
            'strategy': pos['strategy'],
            'pnl': pnl,
            'reason': reason
        })

        print(f"[{datetime.now().strftime('%H:%M:%S')}] "
              f"{pos['symbol']} Closed: {pnl:+.2%} ({reason}) "
              f"Balance: ${self.balance:,.2f}")

    def run_cycle(self):
        """거래 사이클 실행"""
        # 포지션 종료 확인
        self.check_exits()

        # 새 신호 확인
        for tf_name, tf_config in self.timeframes.items():
            for symbol in self.symbols:
                for strategy_type in ['momentum', 'reversal', 'breakout']:
                    key = f"{tf_name}_{symbol}_{strategy_type}"
                    strategy_data = self.strategies[key]

                    # 비활성 전략 스킵
                    if not strategy_data['active']:
                        continue

                    # 시간 간격 체크
                    now = time.time()
                    if now - strategy_data['last_signal'] < tf_config['interval']:
                        continue

                    # 신호 생성
                    signal, confidence = self.generate_signal(symbol, tf_name, strategy_type)

                    if signal != 'HOLD' and confidence >= 0.7:
                        if self.execute_trade(symbol, tf_name, strategy_type, signal, confidence):
                            strategy_data['last_signal'] = now

    def print_status(self):
        """상태 출력"""
        total_pnl = (self.balance / self.initial_balance - 1) * 100
        win_rate = self.winning_trades / max(self.total_trades, 1) * 100

        print(f"\n" + "="*50)
        print(f"Balance: ${self.balance:,.2f} ({total_pnl:+.2f}%)")
        print(f"Trades: {self.total_trades} (Win rate: {win_rate:.1f}%)")
        print(f"Positions: {len(self.positions)}/{self.max_positions}")

        # 상위 전략
        active_strategies = [(k, v) for k, v in self.strategies.items()
                            if v['active'] and v['trades'] >= 3]
        if active_strategies:
            active_strategies.sort(key=lambda x: x[1]['score'], reverse=True)
            print(f"\nTop Strategies:")
            for i, (key, data) in enumerate(active_strategies[:3]):
                print(f"  {i+1}. {key}: "
                      f"Win rate {data['win_rate']*100:.1f}%, "
                      f"Score {data['score']:.2f}")

    def save_state(self):
        """상태 저장"""
        state = {
            'balance': self.balance,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'strategies': self.strategies,
            'timestamp': datetime.now().isoformat()
        }

        with open('nvdl_nvdq_state.json', 'w') as f:
            json.dump(state, f, indent=2, default=str)

    def run(self):
        """메인 실행 루프"""
        print(f"\nTrading started!")

        cycle = 0
        last_status = time.time()
        last_save = time.time()

        try:
            while True:
                cycle += 1

                # 거래 사이클
                self.run_cycle()

                # 상태 출력 (1분마다)
                if time.time() - last_status >= 60:
                    print(f"\n[Cycle {cycle}] {datetime.now().strftime('%H:%M:%S')}")
                    self.print_status()
                    last_status = time.time()

                # 저장 (5분마다)
                if time.time() - last_save >= 300:
                    self.save_state()
                    last_save = time.time()

                # 대기
                time.sleep(10)

        except KeyboardInterrupt:
            print("\n\nSystem stopped")
            self.print_status()
            self.save_state()

def main():
    """메인 함수"""
    api_key = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"

    optimizer = NVDLNVDQAdvancedOptimizer(api_key)
    optimizer.run()

if __name__ == "__main__":
    main()