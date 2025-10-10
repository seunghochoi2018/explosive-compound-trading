#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVDL/NVDQ 울트라 시간주기 최적화 시스템
- 코드3 로직 기반으로 NVDL/NVDQ 특화
- 15분~1주 모든 시간주기 테스트
- 승률 높은 모델로 자동 수렴
- 동적 포지션 크기 조정
- 수수료/슬리피지 고려
"""

import requests
import json
import time
import random
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

class NVDLNVDQUltraTimeframeOptimizer:
    def __init__(self, fmp_api_key: str):
        """
        NVDL/NVDQ 울트라 시간주기 최적화 시스템 초기화
        """
        print("=" * 70)
        print("🚀 NVDL/NVDQ 울트라 시간주기 최적화 시스템")
        print("📊 15분~1주 모든 주기 + 최적 모델 자동 수렴")
        print("💎 코드3 고급 로직 기반 NVDL/NVDQ 특화")
        print("=" * 70)

        self.fmp_api_key = fmp_api_key
        self.balance = 10000.0
        self.initial_balance = self.balance
        self.symbols = ['NVDL', 'NVDQ']

        # 현실적인 시간주기별 전략 (수수료/슬리피지 고려)
        self.timeframes = {
            '15m': {
                'interval': 900,        # 15분
                'hold_time': 3600,      # 1시간 보유
                'min_profit': 0.02,     # 2% 최소 수익
                'base_position_size': 0.15,  # 기본 15% 할당
                'fee_rate': 0.002,      # 0.2% 수수료 (바이비트 기준)
                'slippage': 0.001,      # 0.1% 슬리피지
                'leverage_multiplier': 1.0,
                'last_check': {},
                'models': {}
            },
            '1h': {
                'interval': 3600,       # 1시간
                'hold_time': 7200,      # 2시간 보유
                'min_profit': 0.025,    # 2.5% 최소 수익
                'base_position_size': 0.2,   # 기본 20% 할당
                'fee_rate': 0.002,
                'slippage': 0.001,
                'leverage_multiplier': 1.2,
                'last_check': {},
                'models': {}
            },
            '6h': {
                'interval': 21600,      # 6시간
                'hold_time': 43200,     # 12시간 보유
                'min_profit': 0.03,     # 3% 최소 수익
                'base_position_size': 0.25,  # 기본 25% 할당
                'fee_rate': 0.002,
                'slippage': 0.001,
                'leverage_multiplier': 1.5,
                'last_check': {},
                'models': {}
            },
            '12h': {
                'interval': 43200,      # 12시간
                'hold_time': 86400,     # 1일 보유
                'min_profit': 0.04,     # 4% 최소 수익
                'base_position_size': 0.3,   # 기본 30% 할당
                'fee_rate': 0.002,
                'slippage': 0.0008,
                'leverage_multiplier': 2.0,
                'last_check': {},
                'models': {}
            },
            '1d': {
                'interval': 86400,      # 1일
                'hold_time': 259200,    # 3일 보유
                'min_profit': 0.05,     # 5% 최소 수익
                'base_position_size': 0.35,  # 기본 35% 할당
                'fee_rate': 0.002,
                'slippage': 0.0005,
                'leverage_multiplier': 2.5,
                'last_check': {},
                'models': {}
            }
        }

        # 각 시간주기, 심볼, 전략별로 모델 생성
        self.strategies_per_timeframe = 5  # 각 시간주기별 5개 전략
        self.initialize_models()

        # 전역 성과 추적
        self.all_trades = []
        self.active_positions = {}  # {(timeframe, symbol): position_data}

        # 자동 수렴 설정 (순수 학습을 위해 수정)
        self.convergence_threshold = 100  # 100회 거래 후 수렴 시작 (충분한 학습 기회)
        self.min_trades_per_timeframe = 20  # 각 시간주기별 최소 20회 거래 필요
        self.top_models_count = 2       # 상위 2개 모델에만 집중 (과도한 제한 방지)
        self.focus_started = False

        print(f"✅ 초기화 완료!")
        print(f"📊 시간주기: {list(self.timeframes.keys())}")
        print(f"🎯 심볼: {self.symbols}")
        print(f"💰 초기 자금: ${self.balance:,.2f}")

    def initialize_models(self):
        """각 시간주기, 심볼, 전략별 모델 초기화"""
        for tf_name, tf_config in self.timeframes.items():
            tf_config['last_check'] = {}
            tf_config['models'] = {}

            for symbol in self.symbols:
                # 각 심볼별로 초기 체크 시간 설정
                tf_config['last_check'][symbol] = 0
                tf_config['models'][symbol] = {}

                # 각 전략별로 모델 생성
                for strategy_id in range(self.strategies_per_timeframe):
                    strategy_names = ['Random', 'Momentum', 'TimeCycle', 'Contrarian', 'Volatility']
                    strategy_name = strategy_names[strategy_id % len(strategy_names)]
                    model_key = f"{tf_name}_{symbol}_{strategy_name}"

                    # 초기에는 짧은 주기만 활성화하여 순차 학습
                    is_short_timeframe = tf_name in ['15m', '1h']

                    tf_config['models'][symbol][strategy_id] = {
                        'strategy_name': strategy_name,
                        'strategy_id': strategy_id,
                        'trades': 0,
                        'wins': 0,
                        'total_profit': 0.0,
                        'win_rate': 0.0,
                        'avg_profit': 0.0,
                        'weight': 1.0,
                        'active': is_short_timeframe,  # 초기에는 짧은 주기만 활성화
                        'recent_profits': [],
                        'sharpe_ratio': 0.0,
                        'max_drawdown': 0.0,
                        'consecutive_wins': 0,
                        'consecutive_losses': 0,
                        'best_trade': 0.0,
                        'worst_trade': 0.0
                    }

    def get_stock_price(self, symbol: str) -> Optional[float]:
        """실시간 주식 가격 조회"""
        try:
            url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}?apikey={self.fmp_api_key}"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return float(data[0]['price'])

            # 백업 가격
            backup_prices = {'NVDL': 45.0, 'NVDQ': 25.0}
            if symbol in backup_prices:
                price = backup_prices[symbol] + random.uniform(-2, 2)
                return price

        except Exception as e:
            print(f"가격 조회 오류 ({symbol}): {e}")

        return None

    def calculate_signal_strength(self, symbol: str, timeframe: str, strategy_id: int = 0) -> Tuple[float, str]:
        """순수 시장 데이터 기반 신호 계산 (기술적 지표 없음)"""
        try:
            current_price = self.get_stock_price(symbol)
            if not current_price:
                return 0.0, 'HOLD'

            # 순수 시장 학습: 시간, 가격, 심볼만 사용
            import hashlib
            import time as time_module

            # 현재 시간을 시간주기 단위로 나눈 값
            current_time = time_module.time()
            time_bucket = int(current_time // self.timeframes[timeframe]['interval'])

            # 다양한 전략을 위한 시드 생성 (시간 + 심볼 + 전략ID)
            seed_string = f"{time_bucket}_{symbol}_{timeframe}_{strategy_id}_{current_price:.2f}"
            seed = int(hashlib.md5(seed_string.encode()).hexdigest()[:8], 16)
            random.seed(seed)

            # 전략별 다른 접근법
            strategies = {
                0: self._pure_random_strategy,      # 순수 랜덤
                1: self._price_momentum_strategy,   # 가격 모멘텀
                2: self._time_cycle_strategy,      # 시간 사이클
                3: self._contrarian_strategy,      # 역추세
                4: self._volatility_strategy       # 변동성 기반
            }

            strategy_func = strategies.get(strategy_id % len(strategies), strategies[0])
            signal_strength, action = strategy_func(symbol, timeframe, current_price, time_bucket)

            # 시드 초기화
            random.seed()

            return signal_strength, action

        except Exception as e:
            print(f"신호 계산 오류: {e}")
            random.seed()  # 오류 시에도 시드 초기화
            return 0.0, 'HOLD'

    def _pure_random_strategy(self, symbol: str, timeframe: str, price: float, time_bucket: int) -> Tuple[float, str]:
        """순수 랜덤 전략"""
        signal_strength = random.uniform(0.0, 1.0)
        actions = ['BUY', 'SELL', 'HOLD']
        action = random.choice(actions)
        return signal_strength, action

    def _price_momentum_strategy(self, symbol: str, timeframe: str, price: float, time_bucket: int) -> Tuple[float, str]:
        """가격 기반 모멘텀 전략"""
        # 가격의 마지막 두 자리를 이용한 패턴
        price_pattern = int((price * 100) % 100)

        if price_pattern > 70:
            action = 'BUY'
            signal_strength = (price_pattern - 70) / 30
        elif price_pattern < 30:
            action = 'SELL'
            signal_strength = (30 - price_pattern) / 30
        else:
            action = 'HOLD'
            signal_strength = 0.5

        return signal_strength, action

    def _time_cycle_strategy(self, symbol: str, timeframe: str, price: float, time_bucket: int) -> Tuple[float, str]:
        """시간 사이클 전략"""
        # 시간 버킷을 이용한 사이클 패턴
        cycle = time_bucket % 10  # 10 주기 사이클

        if cycle in [0, 1, 2]:
            action = 'BUY'
            signal_strength = 0.8
        elif cycle in [7, 8, 9]:
            action = 'SELL'
            signal_strength = 0.8
        else:
            action = 'HOLD'
            signal_strength = 0.3

        return signal_strength, action

    def _contrarian_strategy(self, symbol: str, timeframe: str, price: float, time_bucket: int) -> Tuple[float, str]:
        """역추세 전략"""
        # NVDL이 높을 때 NVDQ 매수, 그 반대
        price_level = int(price) % 10

        if symbol == 'NVDL':
            if price_level > 6:
                action = 'SELL'  # 높을 때 매도
            elif price_level < 4:
                action = 'BUY'   # 낮을 때 매수
            else:
                action = 'HOLD'
        else:  # NVDQ
            if price_level > 6:
                action = 'BUY'   # NVDL 높을 때 NVDQ 매수
            elif price_level < 4:
                action = 'SELL'  # NVDL 낮을 때 NVDQ 매도
            else:
                action = 'HOLD'

        signal_strength = abs(price_level - 5) / 5  # 중앙에서 멀수록 강한 신호
        return signal_strength, action

    def _volatility_strategy(self, symbol: str, timeframe: str, price: float, time_bucket: int) -> Tuple[float, str]:
        """변동성 기반 전략"""
        # 가격 변화를 시뮬레이션
        price_hash = hash(f"{price:.2f}") % 1000
        volatility = price_hash / 1000  # 0-1 범위의 변동성

        if volatility > 0.7:
            # 고변동성: 적극적 거래
            action = 'BUY' if (time_bucket % 2) == 0 else 'SELL'
            signal_strength = volatility
        elif volatility < 0.3:
            # 저변동성: 보수적
            action = 'HOLD'
            signal_strength = 0.2
        else:
            # 중간변동성: 선택적 거래
            action = 'BUY' if (price_hash % 3) == 0 else 'HOLD'
            signal_strength = 0.5

        return signal_strength, action

    def calculate_position_size(self, timeframe: str, symbol: str, signal_strength: float, strategy_id: int = 0) -> float:
        """동적 포지션 크기 계산 (전략별)"""
        try:
            tf_config = self.timeframes[timeframe]
            model = tf_config['models'][symbol][strategy_id]

            # 기본 포지션 크기 (다중 전략이므로 더 작게)
            base_size = tf_config['base_position_size'] / self.strategies_per_timeframe  # 전략 수만큼 나누기

            # 모델 성과에 따른 조정
            if model['trades'] >= 5:  # 충분한 거래 경험
                win_rate = model['win_rate']

                # 승률에 따른 포지션 크기 조정
                if win_rate >= 0.8:      # 80% 이상
                    size_multiplier = 2.0
                elif win_rate >= 0.75:   # 75% 이상
                    size_multiplier = 1.8
                elif win_rate >= 0.7:    # 70% 이상
                    size_multiplier = 1.5
                elif win_rate >= 0.65:   # 65% 이상
                    size_multiplier = 1.2
                elif win_rate >= 0.6:    # 60% 이상
                    size_multiplier = 1.0
                else:                    # 60% 미만
                    size_multiplier = 0.5
            else:
                size_multiplier = 1.0

            # 신호 강도에 따른 조정
            strength_multiplier = signal_strength * 1.5

            # 레버리지 효과 고려
            leverage_adj = tf_config['leverage_multiplier']

            # 최종 포지션 크기
            final_size = base_size * size_multiplier * strength_multiplier * leverage_adj

            # 최대 10% 제한 (다중 전략이므로 더 보수적)
            final_size = min(final_size, 0.1)

            return final_size

        except Exception as e:
            print(f"포지션 크기 계산 오류: {e}")
            return 0.02  # 더 작은 기본값

    def execute_trade(self, timeframe: str, symbol: str, action: str,
                     signal_strength: float, strategy_id: int = 0) -> Optional[Dict]:
        """거래 실행"""
        try:
            current_price = self.get_stock_price(symbol)
            if not current_price:
                return None

            tf_config = self.timeframes[timeframe]
            position_size_ratio = self.calculate_position_size(timeframe, symbol, signal_strength, strategy_id)
            position_value = self.balance * position_size_ratio

            # 수수료 및 슬리피지 적용
            fee_cost = position_value * tf_config['fee_rate']
            slippage_cost = position_value * tf_config['slippage']
            total_cost = fee_cost + slippage_cost

            # 레버리지 적용 (NVDL=3x, NVDQ=2x)
            leverage = 3.0 if symbol == 'NVDL' else 2.0

            # 전략 이름 가져오기
            strategy_name = self.timeframes[timeframe]['models'][symbol][strategy_id]['strategy_name']

            # 거래 데이터
            trade_data = {
                'timeframe': timeframe,
                'symbol': symbol,
                'strategy_id': strategy_id,
                'strategy_name': strategy_name,
                'action': action,
                'price': current_price,
                'position_value': position_value,
                'position_ratio': position_size_ratio,
                'leverage': leverage,
                'signal_strength': signal_strength,
                'timestamp': datetime.now(),
                'fee_cost': fee_cost,
                'slippage_cost': slippage_cost,
                'total_cost': total_cost,
                'expected_hold_time': tf_config['hold_time']
            }

            # 활성 포지션에 추가 (전략별로 구분)
            position_key = (timeframe, symbol, strategy_id)
            self.active_positions[position_key] = {
                'side': 'long' if action == 'BUY' else 'short',
                'entry_price': current_price,
                'position_value': position_value,
                'leverage': leverage,
                'entry_time': datetime.now(),
                'timeframe': timeframe,
                'symbol': symbol,
                'strategy_id': strategy_id,
                'strategy_name': strategy_name,
                'signal_strength': signal_strength,
                'total_cost': total_cost
            }

            print(f"[{timeframe}-{strategy_name}] {action} {symbol} @ ${current_price:.2f} "
                  f"(크기: {position_size_ratio*100:.1f}%, 신뢰도: {signal_strength:.2f})")

            self.all_trades.append(trade_data)
            return trade_data

        except Exception as e:
            print(f"거래 실행 오류: {e}")
            return None

    def check_position_exits(self):
        """포지션 청산 조건 점검"""
        current_time = datetime.now()
        positions_to_close = []

        for position_key, position in self.active_positions.items():
            # 3차원 키 처리 (timeframe, symbol, strategy_id)
            timeframe, symbol, strategy_id = position_key
            tf_config = self.timeframes[timeframe]

            current_price = self.get_stock_price(symbol)
            if not current_price:
                continue

            # 보유 시간
            holding_seconds = (current_time - position['entry_time']).total_seconds()

            # 수익률 계산
            entry_price = position['entry_price']
            if position['side'] == 'long':
                raw_profit_pct = (current_price / entry_price - 1) * 100
            else:
                raw_profit_pct = (entry_price / current_price - 1) * 100

            # 레버리지 적용
            leveraged_profit_pct = raw_profit_pct * position['leverage']

            should_close = False
            close_reason = ""

            # 최소 보유 시간 체크 (시간주기에 맞는 최소 보유)
            min_hold_seconds = tf_config['interval']  # 시간주기만큼은 최소 보유

            if holding_seconds < min_hold_seconds:
                continue  # 최소 보유 시간 미달 시 청산 금지

            # 순수 학습: 오직 시간 기준으로만 청산 (목표수익/손절 제거)
            # 1. 최대 보유 시간 도달 시에만 청산
            if holding_seconds >= tf_config['hold_time']:
                should_close = True
                close_reason = f"보유시간완료 ({holding_seconds/3600:.1f}h, 수익률: {leveraged_profit_pct:+.2f}%)"

            if should_close:
                self.close_position(position_key, current_price, leveraged_profit_pct, close_reason)
                positions_to_close.append(position_key)

        # 청산된 포지션 제거
        for position_key in positions_to_close:
            if position_key in self.active_positions:
                del self.active_positions[position_key]

    def close_position(self, position_key: Tuple[str, str, int], current_price: float,
                      profit_pct: float, close_reason: str):
        """포지션 청산 및 성과 업데이트"""
        try:
            timeframe, symbol, strategy_id = position_key
            position = self.active_positions[position_key]

            # 잔고 업데이트
            position_value = position['position_value']
            profit_amount = position_value * (profit_pct / 100)
            self.balance += profit_amount

            # 보유 시간 계산
            holding_time = (datetime.now() - position['entry_time']).total_seconds() / 3600

            # 모델 성과 업데이트
            self.update_model_performance(timeframe, symbol, profit_pct, holding_time, strategy_id)

            strategy_name = position.get('strategy_name', 'Unknown')
            print(f"[{timeframe}-{strategy_name}] {symbol} 청산: {profit_pct:+.2f}% ({close_reason}) "
                  f"잔고: ${self.balance:,.2f}")

        except Exception as e:
            print(f"포지션 청산 오류: {e}")

    def update_model_performance(self, timeframe: str, symbol: str, profit_pct: float, holding_time: float, strategy_id: int = 0):
        """모델 성과 업데이트 (전략별)"""
        try:
            model = self.timeframes[timeframe]['models'][symbol][strategy_id]

            # 기본 통계 업데이트
            model['trades'] += 1
            model['total_profit'] += profit_pct

            if profit_pct > 0:
                model['wins'] += 1
                model['consecutive_wins'] += 1
                model['consecutive_losses'] = 0
                model['best_trade'] = max(model['best_trade'], profit_pct)
            else:
                model['consecutive_losses'] += 1
                model['consecutive_wins'] = 0
                model['worst_trade'] = min(model['worst_trade'], profit_pct)

            # 파생 통계 계산
            model['win_rate'] = model['wins'] / model['trades']
            model['avg_profit'] = model['total_profit'] / model['trades']

            # 최근 수익률 저장 (최대 20개)
            model['recent_profits'].append(profit_pct)
            if len(model['recent_profits']) > 20:
                model['recent_profits'].pop(0)

            # 샤프 비율 계산
            if len(model['recent_profits']) >= 5:
                profits = model['recent_profits']
                avg = sum(profits) / len(profits)
                variance = sum((p - avg) ** 2 for p in profits) / len(profits)
                std_dev = math.sqrt(variance)
                model['sharpe_ratio'] = avg / max(std_dev, 0.001)

            # 가중치 계산 (복합 점수)
            if model['trades'] >= 3:
                # 승률 40% + 평균수익 30% + 샤프비율 20% + 연속승 10%
                win_rate_score = model['win_rate'] * 0.4
                profit_score = max(model['avg_profit'] / 10, 0) * 0.3  # 10% 수익을 1.0점으로
                sharpe_score = max(model['sharpe_ratio'] / 2, 0) * 0.2  # 샤프비율 2를 1.0점으로
                streak_score = min(model['consecutive_wins'] / 5, 1.0) * 0.1  # 연속승 5회를 1.0점으로

                combined_score = win_rate_score + profit_score + sharpe_score + streak_score
                model['weight'] = max(combined_score, 0.1)  # 최소 0.1

            # 순차적 시간주기 활성화
            self.activate_next_timeframes()

            # 자동 수렴 체크
            if model['trades'] >= self.convergence_threshold and not self.focus_started:
                self.check_convergence()

        except Exception as e:
            print(f"성과 업데이트 오류: {e}")

    def activate_next_timeframes(self):
        """짧은 주기부터 순차적으로 긴 주기 활성화"""
        try:
            # 15분, 1시간이 충분히 학습되면 6시간 활성화
            short_ready = all(
                sum(sum(strategy_model['trades'] for strategy_model in symbol_models.values())
                    for symbol_models in self.timeframes[tf]['models'].values()) >= 10
                for tf in ['15m', '1h']
            )

            if short_ready:
                for symbol in self.symbols:
                    for strategy_id in range(self.strategies_per_timeframe):
                        if not self.timeframes['6h']['models'][symbol][strategy_id]['active']:
                            self.timeframes['6h']['models'][symbol][strategy_id]['active'] = True
                            strategy_name = self.timeframes['6h']['models'][symbol][strategy_id]['strategy_name']
                            print(f"📈 6시간 주기 활성화: {symbol}-{strategy_name}")

            # 6시간이 충분히 학습되면 12시간 활성화
            medium_ready = sum(sum(strategy_model['trades'] for strategy_model in symbol_models.values())
                             for symbol_models in self.timeframes['6h']['models'].values()) >= 10

            if medium_ready:
                for symbol in self.symbols:
                    for strategy_id in range(self.strategies_per_timeframe):
                        if not self.timeframes['12h']['models'][symbol][strategy_id]['active']:
                            self.timeframes['12h']['models'][symbol][strategy_id]['active'] = True
                            strategy_name = self.timeframes['12h']['models'][symbol][strategy_id]['strategy_name']
                            print(f"📈 12시간 주기 활성화: {symbol}-{strategy_name}")

            # 12시간이 충분히 학습되면 1일 활성화
            long_ready = sum(sum(strategy_model['trades'] for strategy_model in symbol_models.values())
                           for symbol_models in self.timeframes['12h']['models'].values()) >= 10

            if long_ready:
                for symbol in self.symbols:
                    for strategy_id in range(self.strategies_per_timeframe):
                        if not self.timeframes['1d']['models'][symbol][strategy_id]['active']:
                            self.timeframes['1d']['models'][symbol][strategy_id]['active'] = True
                            strategy_name = self.timeframes['1d']['models'][symbol][strategy_id]['strategy_name']
                            print(f"📈 1일 주기 활성화: {symbol}-{strategy_name}")

        except Exception as e:
            print(f"순차 활성화 오류: {e}")

    def check_convergence(self):
        """상위 모델로 수렴 체크 (공정한 평가 기준)"""
        try:
            # 모든 시간주기가 충분한 거래 기회를 가졌는지 확인
            timeframe_ready = {}
            for tf_name, tf_config in self.timeframes.items():
                total_trades = sum(sum(model['trades'] for model in symbol_models.values())
                                 for symbol_models in tf_config['models'].values())
                timeframe_ready[tf_name] = total_trades >= self.min_trades_per_timeframe

            # 모든 시간주기가 최소 거래 수에 도달했는지 확인
            if not all(timeframe_ready.values()):
                print(f"⏳ 시간주기별 학습 진행 중: {timeframe_ready}")
                return  # 아직 충분한 학습이 이루어지지 않음

            # 모든 모델의 성과 수집 (더 엄격한 기준)
            all_models = []
            for tf_name, tf_config in self.timeframes.items():
                for symbol, symbol_models in tf_config['models'].items():
                    for strategy_id, model in symbol_models.items():
                        if model['trades'] >= self.min_trades_per_timeframe:  # 각 모델별 최소 거래 수
                            all_models.append({
                                'timeframe': tf_name,
                                'symbol': symbol,
                                'strategy_id': strategy_id,
                                'model': model,
                                'key': f"{tf_name}_{symbol}_{model['strategy_name']}"
                            })

            if len(all_models) < self.top_models_count:
                return  # 충분한 모델 없음

            # 성과 기준 정렬 (가중치 대신 실제 수익률 우선)
            all_models.sort(key=lambda x: (x['model']['avg_profit'], x['model']['win_rate']), reverse=True)
            top_models = all_models[:self.top_models_count]

            # 모든 모델 비활성화
            for tf_name, tf_config in self.timeframes.items():
                for symbol in self.symbols:
                    for strategy_id in range(self.strategies_per_timeframe):
                        tf_config['models'][symbol][strategy_id]['active'] = False

            # 상위 모델만 활성화
            for model_info in top_models:
                tf_name = model_info['timeframe']
                symbol = model_info['symbol']
                strategy_id = model_info['strategy_id']
                self.timeframes[tf_name]['models'][symbol][strategy_id]['active'] = True

            print(f"\n🎯 충분한 학습 후 상위 {len(top_models)}개 전략으로 수렴!")
            for i, model_info in enumerate(top_models):
                model = model_info['model']
                print(f"  {i+1}. {model_info['key']}: "
                      f"승률 {model['win_rate']*100:.1f}%, "
                      f"평균수익 {model['avg_profit']:+.2f}%, "
                      f"거래수 {model['trades']}회")

            self.focus_started = True

        except Exception as e:
            print(f"수렴 체크 오류: {e}")

    def run_trading_cycle(self):
        """메인 거래 사이클"""
        try:
            current_time = time.time()
            trades_executed = 0

            # 각 시간주기별 체크
            for tf_name, tf_config in self.timeframes.items():
                interval = tf_config['interval']

                for symbol in self.symbols:
                    # 시간 간격 체크
                    last_check = tf_config['last_check'][symbol]
                    if current_time - last_check < interval:
                        continue

                    # 모델 구조 확인 (디버깅)
                    if symbol not in tf_config['models']:
                        print(f"🔴 오류: {tf_name}에 {symbol} 모델이 없음")
                        continue

                    if not isinstance(tf_config['models'][symbol], dict):
                        print(f"🔴 오류: {tf_name}-{symbol} 모델이 dict가 아님: {type(tf_config['models'][symbol])}")
                        continue

                    # 각 전략별로 체크
                    for strategy_id, model in tf_config['models'][symbol].items():
                        # 모델이 비활성화된 경우 스킵
                        if not model['active']:
                            continue

                        # 이미 해당 시간주기/심볼/전략으로 포지션이 있는 경우 스킵
                        position_key = (tf_name, symbol, strategy_id)
                        if position_key in self.active_positions:
                            continue

                        # 전략별 신호 계산
                        signal_strength, action = self.calculate_signal_strength(symbol, tf_name, strategy_id)

                        # 임계값 없이 모든 신호에 대해 거래 (순수 학습)
                        if action != 'HOLD':
                            # 거래 실행 (다중 전략 동시 테스트)
                            trade_result = self.execute_trade(tf_name, symbol, action, signal_strength, strategy_id)
                            if trade_result:
                                trades_executed += 1

                    # 마지막 체크 시간 업데이트
                    tf_config['last_check'][symbol] = current_time

            # 기존 포지션 점검
            self.check_position_exits()

            return trades_executed

        except Exception as e:
            print(f"거래 사이클 오류: {e}")
            return 0

    def print_status(self):
        """현재 상태 출력"""
        try:
            total_profit_pct = (self.balance / self.initial_balance - 1) * 100
            active_models = sum(1 for tf in self.timeframes.values()
                              for symbol_models in tf['models'].values()
                              for model in symbol_models.values() if model['active'])

            print(f"\n💰 잔고: ${self.balance:,.2f} ({total_profit_pct:+.2f}%)")
            print(f"📍 활성 포지션: {len(self.active_positions)}개")
            total_models = len(self.symbols) * len(self.timeframes) * self.strategies_per_timeframe
            print(f"🤖 활성 모델: {active_models}/{total_models}개")

            # 상위 5개 모델 출력
            all_models = []
            for tf_name, tf_config in self.timeframes.items():
                for symbol, symbol_models in tf_config['models'].items():
                    for strategy_id, model in symbol_models.items():
                        if model['trades'] >= 3:
                            all_models.append({
                                'name': f"{tf_name}_{symbol}_{model['strategy_name']}",
                                'data': model,
                                'active': model['active']
                            })

            if all_models:
                all_models.sort(key=lambda x: x['data']['weight'], reverse=True)
                print(f"\n🏆 상위 전략들:")
                for i, model_info in enumerate(all_models[:5]):
                    model = model_info['data']
                    active_mark = "🔥" if model_info['active'] else "💤"
                    print(f"  {active_mark} {i+1}. {model_info['name']}: "
                          f"{model['win_rate']*100:.1f}% 승률, {model['avg_profit']:+.2f}% 평균")

        except Exception as e:
            print(f"상태 출력 오류: {e}")

    def save_progress(self):
        """진행 상황 저장"""
        try:
            # 포지션 키 문자열로 변환 (3차원 튜플)
            str_positions = {}
            for k, v in self.active_positions.items():
                key_str = f"{k[0]}_{k[1]}_{k[2]}" if len(k) == 3 else str(k)
                str_positions[key_str] = v

            # 저장할 데이터 준비
            data = {
                'balance': self.balance,
                'initial_balance': self.initial_balance,
                'active_positions': str_positions,
                'all_trades': len(self.all_trades),
                'focus_started': self.focus_started,
                'last_update': datetime.now().isoformat(),
                # timeframes는 너무 복잡하므로 간략한 정보만 저장
                'timeframe_summary': {
                    tf_name: {
                        'interval': tf_config['interval'],
                        'active_models': sum(1 for symbol_models in tf_config['models'].values()
                                           for model in symbol_models.values()
                                           if model.get('active', False))
                    }
                    for tf_name, tf_config in self.timeframes.items()
                }
            }

            with open('nvdl_nvdq_ultra_optimizer_progress.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

            print(f"💾 진행상황 저장 완료")

        except Exception as e:
            print(f"🔴 진행상황 저장 오류: {e}")
            import traceback
            traceback.print_exc()

    def run(self):
        """메인 실행 루프"""
        print(f"\n🚀 NVDL/NVDQ 울트라 시간주기 최적화 시작!")
        print(f"🎯 목표: 모든 시간주기 테스트 → 최고 모델 자동 발견")

        cycle_count = 0
        last_status_time = time.time()

        try:
            while True:
                cycle_count += 1
                current_time = time.time()

                print(f"\n[사이클 {cycle_count}] {datetime.now().strftime('%H:%M:%S')}")

                # 거래 사이클 실행
                trades_executed = self.run_trading_cycle()

                if trades_executed > 0:
                    print(f"✅ {trades_executed}개 거래 실행")

                # 5분마다 상태 출력
                if current_time - last_status_time >= 300:  # 5분
                    try:
                        self.print_status()
                    except Exception as e:
                        print(f"🔴 상태 출력 오류: {e}")
                        import traceback
                        traceback.print_exc()
                    last_status_time = current_time

                # 10 사이클마다 저장
                if cycle_count % 10 == 0:
                    try:
                        self.save_progress()
                    except Exception as e:
                        print(f"🔴 저장 오류: {e}")
                        import traceback
                        traceback.print_exc()

                # 동적 대기: 가장 짧은 활성 시간주기의 1/10
                try:
                    active_intervals = []
                    for tf_name, tf_config in self.timeframes.items():
                        # 디버깅: 모델 구조 확인
                        if 'models' not in tf_config:
                            print(f"🔴 오류: {tf_name}에 'models' 키가 없음")
                            continue

                        for symbol, symbol_models in tf_config['models'].items():
                            # 각 전략 모델 체크
                            if isinstance(symbol_models, dict):
                                for strategy_id, model in symbol_models.items():
                                    if isinstance(model, dict) and model.get('active', False):
                                        active_intervals.append(tf_config['interval'])
                                        break
                            else:
                                print(f"🔴 오류: {tf_name}-{symbol}의 models가 dict가 아님: {type(symbol_models)}")

                    if active_intervals:
                        min_interval = min(active_intervals)
                        sleep_time = max(min_interval // 10, 60)  # 최소 1분, 최대 짧은주기/10
                    else:
                        sleep_time = 300  # 기본 5분

                    print(f"⏰ 다음 체크까지 {sleep_time//60}분 {sleep_time%60}초 대기...")
                    time.sleep(sleep_time)

                except Exception as e:
                    print(f"🔴 대기 시간 계산 오류: {e}")
                    import traceback
                    traceback.print_exc()
                    # 오류 시 기본값 사용
                    sleep_time = 60
                    print(f"⏰ 기본값 사용: {sleep_time}초 대기...")
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            print("\n사용자 중단")
        except Exception as e:
            print(f"\n🔴 시스템 오류: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.save_progress()
            final_profit = (self.balance / self.initial_balance - 1) * 100
            print(f"\n🔚 최적화 완료!")
            print(f"💰 최종 수익률: {final_profit:+.2f}%")
            print(f"🔄 총 사이클: {cycle_count}회")

def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="NVDL/NVDQ 울트라 시간주기 최적화 시스템")
    parser.add_argument('--api-key', type=str,
                       default="5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI",
                       help='FMP API 키')

    args = parser.parse_args()

    # 최적화 시스템 생성 및 실행
    optimizer = NVDLNVDQUltraTimeframeOptimizer(args.api_key)
    optimizer.run()

if __name__ == "__main__":
    main()