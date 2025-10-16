#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
공격적 전략 탐색 시스템
- 1초마다 새로운 전략 조합을 병렬로 백테스팅
- 최고 성과 전략을 실시간으로 선택
- 실제 매매는 선택된 전략의 최적 주기로 실행
"""
import asyncio
import aiohttp
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import itertools
import json
from concurrent.futures import ThreadPoolExecutor
import random

class StrategyFinder:
    def __init__(self):
        self.best_strategy = None
        self.best_performance = -999
        self.strategy_history = []
        self.test_counter = 0

        # 전략 파라미터 범위
        self.param_space = {
            'timeframe': ['1h', '4h', '1d'],  # 매매 주기
            'rsi_period': [7, 14, 21],
            'rsi_oversold': [20, 25, 30],
            'rsi_overbought': [70, 75, 80],
            'macd_fast': [8, 12, 16],
            'macd_slow': [21, 26, 31],
            'bb_period': [15, 20, 25],
            'bb_std': [1.5, 2.0, 2.5],
            'volume_threshold': [1.2, 1.5, 2.0],  # 평균 대비
            'stop_loss': [0.02, 0.03, 0.05],  # 2%, 3%, 5%
            'take_profit': [0.03, 0.05, 0.08],  # 3%, 5%, 8%
            'position_size': [0.3, 0.5, 0.7],  # 잔고의 %
            'trend_ma_period': [50, 100, 200],
            'entry_signals_required': [2, 3, 4],  # 최소 신호 개수
        }

        self.executor = ThreadPoolExecutor(max_workers=10)

    def generate_random_strategy(self):
        """랜덤 전략 생성"""
        strategy = {}
        for param, values in self.param_space.items():
            strategy[param] = random.choice(values)
        return strategy

    async def backtest_strategy(self, symbol, strategy):
        """전략 백테스팅 (빠른 평가)"""
        try:
            # 과거 데이터 가져오기 (캐시 사용)
            df = await self.get_historical_data(symbol, strategy['timeframe'])

            if df is None or len(df) < 100:
                return None

            # 지표 계산
            df = self.calculate_indicators(df, strategy)

            # 시뮬레이션
            performance = self.simulate_trades(df, strategy)

            return performance

        except Exception as e:
            print(f"백테스팅 오류: {e}")
            return None

    async def get_historical_data(self, symbol, timeframe):
        """과거 데이터 가져오기 (FMP API)"""
        try:
            # 타임프레임별 기간 설정
            if timeframe == '1h':
                interval = '1hour'
                days = 30
            elif timeframe == '4h':
                interval = '4hour'
                days = 90
            else:  # 1d
                interval = 'daily'
                days = 365

            url = f"https://financialmodelingprep.com/api/v3/historical-chart/{interval}/{symbol}"
            params = {'apikey': '5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI'}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data:
                            df = pd.DataFrame(data)
                            df['date'] = pd.to_datetime(df['date'])
                            df = df.sort_values('date')
                            return df.tail(500)  # 최근 500개
            return None
        except Exception as e:
            return None

    def calculate_indicators(self, df, strategy):
        """기술적 지표 계산"""
        try:
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=strategy['rsi_period']).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=strategy['rsi_period']).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))

            # MACD
            ema_fast = df['close'].ewm(span=strategy['macd_fast']).mean()
            ema_slow = df['close'].ewm(span=strategy['macd_slow']).mean()
            df['macd'] = ema_fast - ema_slow
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['macd_hist'] = df['macd'] - df['macd_signal']

            # 볼린저 밴드
            df['bb_mid'] = df['close'].rolling(window=strategy['bb_period']).mean()
            bb_std = df['close'].rolling(window=strategy['bb_period']).std()
            df['bb_upper'] = df['bb_mid'] + (bb_std * strategy['bb_std'])
            df['bb_lower'] = df['bb_mid'] - (bb_std * strategy['bb_std'])

            # 추세 (이동평균)
            df['trend_ma'] = df['close'].rolling(window=strategy['trend_ma_period']).mean()

            # 거래량
            df['volume_ma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']

            return df
        except Exception as e:
            print(f"지표 계산 오류: {e}")
            return df

    def simulate_trades(self, df, strategy):
        """거래 시뮬레이션"""
        try:
            initial_balance = 10000
            balance = initial_balance
            position = 0
            entry_price = 0
            trades = []

            for i in range(len(df)):
                if i < strategy['trend_ma_period']:
                    continue

                row = df.iloc[i]

                # 진입 신호 카운트
                signals = 0

                # 신호 1: RSI 과매도
                if row['rsi'] < strategy['rsi_oversold']:
                    signals += 1

                # 신호 2: MACD 골든크로스
                if i > 0:
                    if df.iloc[i-1]['macd_hist'] < 0 and row['macd_hist'] > 0:
                        signals += 1

                # 신호 3: 볼린저 밴드 하단 터치
                if row['close'] < row['bb_lower']:
                    signals += 1

                # 신호 4: 상승 추세
                if row['close'] > row['trend_ma']:
                    signals += 1

                # 신호 5: 거래량 증가
                if row['volume_ratio'] > strategy['volume_threshold']:
                    signals += 1

                # 포지션 없을 때: 진입
                if position == 0:
                    if signals >= strategy['entry_signals_required']:
                        # 매수
                        position_value = balance * strategy['position_size']
                        position = position_value / row['close']
                        entry_price = row['close']
                        balance -= position_value

                # 포지션 있을 때: 청산 조건
                elif position > 0:
                    current_value = position * row['close']
                    pnl_pct = (row['close'] - entry_price) / entry_price

                    # 익절 또는 손절
                    if pnl_pct >= strategy['take_profit']:
                        # 익절
                        balance += current_value
                        trades.append({
                            'entry': entry_price,
                            'exit': row['close'],
                            'pnl_pct': pnl_pct,
                            'type': 'take_profit'
                        })
                        position = 0

                    elif pnl_pct <= -strategy['stop_loss']:
                        # 손절
                        balance += current_value
                        trades.append({
                            'entry': entry_price,
                            'exit': row['close'],
                            'pnl_pct': pnl_pct,
                            'type': 'stop_loss'
                        })
                        position = 0

                    # RSI 과매수 또는 MACD 하락 신호
                    elif row['rsi'] > strategy['rsi_overbought']:
                        balance += current_value
                        trades.append({
                            'entry': entry_price,
                            'exit': row['close'],
                            'pnl_pct': pnl_pct,
                            'type': 'signal_exit'
                        })
                        position = 0

            # 마지막 포지션 청산
            if position > 0:
                final_value = position * df.iloc[-1]['close']
                balance += final_value
                pnl_pct = (df.iloc[-1]['close'] - entry_price) / entry_price
                trades.append({
                    'entry': entry_price,
                    'exit': df.iloc[-1]['close'],
                    'pnl_pct': pnl_pct,
                    'type': 'final'
                })

            # 성과 계산
            total_return = (balance - initial_balance) / initial_balance

            if len(trades) == 0:
                return {
                    'total_return': 0,
                    'win_rate': 0,
                    'total_trades': 0,
                    'sharpe_ratio': 0
                }

            wins = sum(1 for t in trades if t['pnl_pct'] > 0)
            win_rate = wins / len(trades)

            # 샤프 비율 (간단 버전)
            returns = [t['pnl_pct'] for t in trades]
            if len(returns) > 1:
                sharpe_ratio = np.mean(returns) / (np.std(returns) + 0.0001)
            else:
                sharpe_ratio = 0

            return {
                'total_return': total_return,
                'win_rate': win_rate,
                'total_trades': len(trades),
                'sharpe_ratio': sharpe_ratio,
                'avg_win': np.mean([t['pnl_pct'] for t in trades if t['pnl_pct'] > 0]) if wins > 0 else 0,
                'avg_loss': np.mean([t['pnl_pct'] for t in trades if t['pnl_pct'] < 0]) if wins < len(trades) else 0,
            }

        except Exception as e:
            print(f"시뮬레이션 오류: {e}")
            return None

    def calculate_score(self, performance):
        """전략 점수 계산 (복합 지표)"""
        if performance is None:
            return -999

        # 가중 평균
        score = (
            performance['total_return'] * 0.4 +  # 총 수익률 40%
            performance['win_rate'] * 0.3 +      # 승률 30%
            performance['sharpe_ratio'] * 0.2 +  # 샤프비율 20%
            (performance['total_trades'] / 100) * 0.1  # 거래 빈도 10%
        )

        return score

    async def find_best_strategy_parallel(self, symbols):
        """병렬로 전략 탐색"""
        print(f"\n{'='*80}")
        print(f"[전략 탐색 #{self.test_counter}] {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*80}")

        # 10개 랜덤 전략 동시 테스트
        tasks = []
        strategies = []

        for _ in range(10):
            strategy = self.generate_random_strategy()
            strategies.append(strategy)

            # 각 심볼에 대해 테스트
            for symbol in symbols:
                task = self.backtest_strategy(symbol, strategy)
                tasks.append((symbol, strategy, task))

        # 병렬 실행
        results = []
        for symbol, strategy, task in tasks:
            performance = await task
            if performance:
                score = self.calculate_score(performance)
                results.append({
                    'symbol': symbol,
                    'strategy': strategy,
                    'performance': performance,
                    'score': score
                })

        # 최고 전략 선택
        if results:
            best = max(results, key=lambda x: x['score'])

            if best['score'] > self.best_performance:
                self.best_performance = best['score']
                self.best_strategy = best

                print(f"\n✅ 새로운 최고 전략 발견!")
                print(f"심볼: {best['symbol']}")
                print(f"점수: {best['score']:.4f}")
                print(f"수익률: {best['performance']['total_return']*100:.2f}%")
                print(f"승률: {best['performance']['win_rate']*100:.2f}%")
                print(f"샤프비율: {best['performance']['sharpe_ratio']:.2f}")
                print(f"거래횟수: {best['performance']['total_trades']}")
                print(f"\n전략 파라미터:")
                for k, v in best['strategy'].items():
                    print(f"  {k}: {v}")

                # 저장
                self.save_best_strategy()
            else:
                print(f"현재 최고 점수: {self.best_performance:.4f} (변화 없음)")

        self.test_counter += 1

    def save_best_strategy(self):
        """최고 전략 저장"""
        try:
            with open('best_strategy.json', 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'score': self.best_performance,
                    'symbol': self.best_strategy['symbol'],
                    'strategy': self.best_strategy['strategy'],
                    'performance': self.best_strategy['performance']
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"저장 오류: {e}")

    async def run_continuous_search(self, symbols):
        """지속적으로 전략 탐색 (1초마다)"""
        print("="*80)
        print("공격적 전략 탐색 시작")
        print("="*80)
        print(f"대상: {', '.join(symbols)}")
        print(f"탐색 속도: 1초마다 10개 전략 병렬 테스트")
        print(f"자동 저장: best_strategy.json")
        print("="*80)

        while True:
            try:
                await self.find_best_strategy_parallel(symbols)
                await asyncio.sleep(1)  # 1초 대기
            except KeyboardInterrupt:
                print("\n\n탐색 중단")
                break
            except Exception as e:
                print(f"오류: {e}")
                await asyncio.sleep(1)

async def main():
    finder = StrategyFinder()

    # ETH와 SOXL에 대해 전략 탐색
    symbols = ['ETHUSD', 'SOXL']

    await finder.run_continuous_search(symbols)

if __name__ == "__main__":
    print("\n공격적 전략 탐색 시스템 v1.0")
    print("- 1초마다 10개 전략을 병렬로 백테스팅")
    print("- 최고 성과 전략 자동 선택 및 저장")
    print("- 매매 주기, 지표, 손익비 등 모든 파라미터 최적화")
    print("")

    asyncio.run(main())
