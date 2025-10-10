import requests
import json
import time
import random
import math
from datetime import datetime

class NVDAMultiTimeframeTrader:
    def __init__(self):
        self.balance = 10000.0
        self.current_prices = {}
        self.price_history = {'NVDL': [], 'NVDQ': []}
        self.all_trades = []

        # 기본 주기 설정 (레버리지 없음)
        self.base_timeframes = {
            '15m': {'interval': 900, 'hold_time': 3600, 'min_profit': 0.01},
            '1h': {'interval': 3600, 'hold_time': 7200, 'min_profit': 0.015},
            '4h': {'interval': 14400, 'hold_time': 28800, 'min_profit': 0.02},
            '1d': {'interval': 86400, 'hold_time': 259200, 'min_profit': 0.03}
        }

        # 종목별 설정
        self.symbols = ['NVDL', 'NVDQ']

        # 거래 방향 옵션
        self.directions = ['both', 'long_only', 'short_only']

        # 전략 옵션
        self.strategies = ['momentum', 'counter_trend', 'breakout']

        # 모든 모델 생성
        self.models = {}
        self.create_all_models()

        print(f"=== NVDA 멀티 타임프레임 트레이더 시작 ===")
        print(f"총 {len(self.models)}개 모델 생성")
        print("종목: NVDL, NVDQ")
        print("주기: 15분, 1시간, 4시간, 1일")
        print("방향: 롱+숏, 롱만, 숏만")
        print("전략: 모멘텀, 역추세, 돌파")

    def create_all_models(self):
        """모든 모델 조합 생성"""
        model_id = 0
        total_models = len(self.symbols) * len(self.base_timeframes) * len(self.directions) * len(self.strategies)

        for symbol in self.symbols:
            for tf_name, tf_config in self.base_timeframes.items():
                for direction in self.directions:
                    for strategy in self.strategies:
                        model_key = f"{symbol}_{tf_name}_{direction}_{strategy}"

                        self.models[model_key] = {
                            'id': model_id,
                            'symbol': symbol,
                            'timeframe': tf_name,
                            'direction': direction,
                            'strategy': strategy,
                            'interval': tf_config['interval'],  # 원래 분석 주기 유지
                            # 'hold_time': 제거 - 시간 제한 없음
                            # 'min_profit': 제거 - 목표 수익률 제한 없음
                            'position_size': 0.05 / total_models,  # 총 자본의 5%를 모든 모델에 분배
                            'fee_rate': 0.001,
                            'last_trade': 0,
                            'trades': 0,
                            'wins': 0,
                            'total_profit': 0.0,
                            'weight': 1.0,
                            'position': None,
                            'entry_price': 0,
                            'entry_time': 0,
                            'current_pnl': 0.0,
                            'max_drawdown': 0.0,  # 최대 손실 추적
                            'max_profit': 0.0,    # 최대 수익 추적
                            'trend_strength': 0.0  # 추세 강도 추적
                        }
                        model_id += 1

    def get_stock_price(self, symbol):
        """Yahoo Finance에서 가격 가져오기 (시뮬레이션)"""
        try:
            # 실제로는 Yahoo Finance API 또는 다른 주식 API 사용
            # 여기서는 시뮬레이션용 가격 생성
            if symbol not in self.current_prices:
                self.current_prices[symbol] = 100.0 + random.uniform(-50, 50)

            # 약간의 변동 추가
            change_percent = random.uniform(-0.02, 0.02)  # ±2%
            self.current_prices[symbol] *= (1 + change_percent)

            return self.current_prices[symbol]
        except:
            return None

    def calculate_indicators(self, symbol, model):
        """기술적 지표 계산"""
        if len(self.price_history[symbol]) < 50:
            return {}

        prices = self.price_history[symbol][-200:]

        # 이동평균
        sma_short = sum(prices[-10:]) / 10 if len(prices) >= 10 else prices[-1]
        sma_long = sum(prices[-30:]) / 30 if len(prices) >= 30 else prices[-1]

        # 모멘텀
        momentum = (prices[-1] - prices[-20]) / prices[-20] if len(prices) >= 20 else 0

        # 변동성
        volatility = sum(abs(prices[i] - prices[i-1]) for i in range(1, min(len(prices), 50))) / min(len(prices)-1, 49)

        # RSI
        gains = [max(0, prices[i] - prices[i-1]) for i in range(1, len(prices))]
        losses = [max(0, prices[i-1] - prices[i]) for i in range(1, len(prices))]
        avg_gain = sum(gains[-14:]) / 14 if len(gains) >= 14 else 0
        avg_loss = sum(losses[-14:]) / 14 if len(losses) >= 14 else 0
        rsi = 100 - (100 / (1 + (avg_gain / avg_loss))) if avg_loss != 0 else 50

        # 볼린저 밴드
        bb_period = 20
        if len(prices) >= bb_period:
            bb_sma = sum(prices[-bb_period:]) / bb_period
            bb_std = math.sqrt(sum((p - bb_sma)**2 for p in prices[-bb_period:]) / bb_period)
            bb_upper = bb_sma + (bb_std * 2)
            bb_lower = bb_sma - (bb_std * 2)
        else:
            bb_upper = bb_lower = prices[-1]

        return {
            'sma_short': sma_short,
            'sma_long': sma_long,
            'momentum': momentum,
            'volatility': volatility,
            'rsi': rsi,
            'bb_upper': bb_upper,
            'bb_lower': bb_lower,
            'current_price': prices[-1]
        }

    def generate_signal(self, model, indicators):
        """신호 생성"""
        strategy = model['strategy']
        direction = model['direction']

        signal = None

        if strategy == 'momentum':
            # 모멘텀 전략
            momentum = indicators.get('momentum', 0)
            rsi = indicators.get('rsi', 50)

            if momentum > 0.01 and rsi < 70:  # 주식은 더 큰 움직임 필요
                signal = 'BUY'
            elif momentum < -0.01 and rsi > 30:
                signal = 'SELL'

        elif strategy == 'counter_trend':
            # 역추세 전략
            rsi = indicators.get('rsi', 50)
            current_price = indicators.get('current_price', 0)
            bb_upper = indicators.get('bb_upper', current_price)
            bb_lower = indicators.get('bb_lower', current_price)

            if rsi > 75 or current_price > bb_upper:
                signal = 'SELL'
            elif rsi < 25 or current_price < bb_lower:
                signal = 'BUY'

        elif strategy == 'breakout':
            # 돌파 전략
            sma_short = indicators.get('sma_short', 0)
            sma_long = indicators.get('sma_long', 0)
            volatility = indicators.get('volatility', 0)

            if sma_short > sma_long * 1.015 and volatility > 1.0:  # 주식용 조정
                signal = 'BUY'
            elif sma_short < sma_long * 0.985 and volatility > 1.0:
                signal = 'SELL'

        # 방향 제한 적용
        if direction == 'long_only' and signal == 'SELL':
            signal = None
        elif direction == 'short_only' and signal == 'BUY':
            signal = None

        return signal

    def generate_exit_signal(self, model, indicators):
        """AI 기반 청산 신호 생성 - 모든 인위적 제한 제거"""
        if not model['position']:
            return False

        strategy = model['strategy']
        position = model['position']
        symbol = model['symbol']
        current_price = self.current_prices[symbol]

        # 현재 손익 계산
        if position == 'BUY':
            pnl_ratio = (current_price - model['entry_price']) / model['entry_price']
        else:
            pnl_ratio = (model['entry_price'] - current_price) / model['entry_price']

        net_pnl_ratio = pnl_ratio - model['fee_rate'] * 2

        # AI 기반 청산 신호 생성
        exit_signal = False

        if strategy == 'momentum':
            # 모멘텀 전략 청산 신호
            momentum = indicators.get('momentum', 0)
            rsi = indicators.get('rsi', 50)

            if position == 'BUY':
                # 매수 포지션: 모멘텀 약화 또는 과매수 시 청산
                if momentum < -0.005 or rsi > 75:
                    exit_signal = True
            else:
                # 매도 포지션: 모멘텀 반전 또는 과매도 시 청산
                if momentum > 0.005 or rsi < 25:
                    exit_signal = True

        elif strategy == 'counter_trend':
            # 역추세 전략 청산 신호
            rsi = indicators.get('rsi', 50)
            current_price = indicators.get('current_price', 0)
            bb_upper = indicators.get('bb_upper', current_price)
            bb_lower = indicators.get('bb_lower', current_price)

            if position == 'BUY':
                # 매수 포지션: 과매수 구간 도달 또는 밴드 상단 접근 시 청산
                if rsi > 65 or current_price > bb_upper * 0.995:
                    exit_signal = True
            else:
                # 매도 포지션: 과매도 구간 도달 또는 밴드 하단 접근 시 청산
                if rsi < 35 or current_price < bb_lower * 1.005:
                    exit_signal = True

        elif strategy == 'breakout':
            # 돌파 전략 청산 신호
            sma_short = indicators.get('sma_short', 0)
            sma_long = indicators.get('sma_long', 0)
            volatility = indicators.get('volatility', 0)

            if position == 'BUY':
                # 매수 포지션: 단기 평균이 장기 평균 아래로 또는 변동성 급감
                if sma_short < sma_long * 0.998 or volatility < 0.01:
                    exit_signal = True
            else:
                # 매도 포지션: 단기 평균이 장기 평균 위로 또는 변동성 급감
                if sma_short > sma_long * 1.002 or volatility < 0.01:
                    exit_signal = True

        # 극단적 손실 방지 (유일한 하드 제한)
        if net_pnl_ratio <= -0.12:  # -12% 이상 손실 시에만 강제 청산
            exit_signal = True

        return exit_signal

    def should_exit_position(self, model):
        """기존 호환성을 위한 래퍼 함수"""
        if not model['position']:
            return False

        indicators = self.calculate_indicators(model)
        if not indicators:
            return False

        return self.generate_exit_signal(model, indicators)

    def execute_trade(self, model_key, signal):
        """거래 실행"""
        model = self.models[model_key]
        current_time = time.time()

        # 거래 간격 체크
        if current_time - model['last_trade'] < model['interval']:
            return

        current_price = self.current_prices[model['symbol']]

        if not model['position']:
            # 신규 진입
            model['position'] = signal
            model['entry_price'] = current_price
            model['entry_time'] = current_time
            model['last_trade'] = current_time
            model['trades'] += 1

            print(f"[{model_key}] {signal} 진입: ${current_price:.2f}")

        elif self.should_exit_position(model):
            # 포지션 청산
            exit_price = current_price
            hold_duration = current_time - model['entry_time']

            if model['position'] == 'BUY':
                pnl_ratio = (exit_price - model['entry_price']) / model['entry_price']
            else:
                pnl_ratio = (model['entry_price'] - exit_price) / model['entry_price']

            # 수수료 차감
            net_pnl_ratio = pnl_ratio - model['fee_rate'] * 2
            pnl = self.balance * model['position_size'] * net_pnl_ratio

            # 현재 PnL 업데이트
            model['current_pnl'] = pnl

            # 거래 기록
            trade_data = {
                'model': model_key,
                'symbol': model['symbol'],
                'timeframe': model['timeframe'],
                'strategy': model['strategy'],
                'direction_type': model['direction'],
                'position_direction': model['position'],
                'entry_price': model['entry_price'],
                'exit_price': exit_price,
                'pnl': pnl,
                'pnl_ratio': net_pnl_ratio,
                'hold_duration': hold_duration,
                'timestamp': datetime.now().isoformat(),
                'profit': pnl > 0
            }

            self.all_trades.append(trade_data)
            model['total_profit'] += pnl

            if pnl > 0:
                model['wins'] += 1

            print(f"[{model_key}] 청산: ${exit_price:.2f}, "
                  f"보유: {hold_duration/3600:.1f}h, 손익: {net_pnl_ratio*100:.2f}% (${pnl:.2f})")

            # 포지션 클리어
            model['position'] = None
            model['entry_price'] = 0
            model['entry_time'] = 0
            model['last_trade'] = current_time

    def update_weights(self):
        """성과에 따른 가중치 조정"""
        for model_key, model in self.models.items():
            if model['trades'] > 5:
                win_rate = model['wins'] / model['trades']
                avg_profit = model['total_profit'] / model['trades'] if model['trades'] > 0 else 0

                # 승률과 평균 수익을 결합한 점수
                score = win_rate * 0.7 + max(0, avg_profit + 10) * 0.3 / 10
                model['weight'] = max(0.1, min(3.0, score))

    def save_progress(self):
        """진행상황 저장"""
        progress = {
            'timestamp': datetime.now().isoformat(),
            'balance': self.balance,
            'current_prices': self.current_prices,
            'total_models': len(self.models),
            'model_performance': {},
            'recent_trades': self.all_trades[-50:],
            'summary': {}
        }

        total_trades = 0
        total_wins = 0
        total_profit = 0
        active_positions = 0

        for model_key, model in self.models.items():
            if model['trades'] > 0:
                win_rate = (model['wins'] / model['trades']) * 100
                avg_profit = model['total_profit'] / model['trades']

                progress['model_performance'][model_key] = {
                    'trades': model['trades'],
                    'wins': model['wins'],
                    'win_rate': win_rate,
                    'total_profit': model['total_profit'],
                    'avg_profit': avg_profit,
                    'weight': model['weight'],
                    'current_position': model['position'],
                    'current_pnl': model.get('current_pnl', 0)
                }

                total_trades += model['trades']
                total_wins += model['wins']
                total_profit += model['total_profit']

                if model['position']:
                    active_positions += 1

        if total_trades > 0:
            progress['summary'] = {
                'total_trades': total_trades,
                'total_wins': total_wins,
                'overall_win_rate': (total_wins / total_trades) * 100,
                'total_profit': total_profit,
                'active_positions': active_positions,
                'models_with_trades': len([m for m in self.models.values() if m['trades'] > 0])
            }

        with open('nvda_multi_timeframe_progress.json', 'w', encoding='utf-8') as f:
            json.dump(progress, f, indent=2, ensure_ascii=False)

    def print_status(self):
        """현황 출력"""
        print(f"\n=== NVDA 멀티 타임프레임 트레이딩 현황 ===")
        print(f"NVDL: ${self.current_prices.get('NVDL', 0):.2f}")
        print(f"NVDQ: ${self.current_prices.get('NVDQ', 0):.2f}")

        # 상위 성과 모델들
        performing_models = [(k, v) for k, v in self.models.items() if v['trades'] > 0]
        performing_models.sort(key=lambda x: x[1]['total_profit'], reverse=True)

        print(f"\n상위 성과 모델 (총 {len(performing_models)}개 활성):")
        for i, (model_key, model) in enumerate(performing_models[:10]):
            win_rate = (model['wins'] / model['trades']) * 100
            avg_profit = model['total_profit'] / model['trades']
            position_info = f"[{model['position']}]" if model['position'] else ""

            print(f"{i+1:2d}. {model_key:30s} {model['wins']:2d}/{model['trades']:2d} "
                  f"({win_rate:4.1f}%) ${model['total_profit']:6.2f} {position_info}")

        # 전체 통계
        total_trades = sum(m['trades'] for m in self.models.values())
        total_wins = sum(m['wins'] for m in self.models.values())
        total_profit = sum(m['total_profit'] for m in self.models.values())
        active_positions = len([m for m in self.models.values() if m['position']])

        print(f"\n전체 통계:")
        print(f"총 거래: {total_trades}, 승리: {total_wins}, 승률: {total_wins/total_trades*100 if total_trades > 0 else 0:.1f}%")
        print(f"총 수익: ${total_profit:.2f}, 활성 포지션: {active_positions}개")

    def run(self):
        """메인 실행 루프"""
        last_save = time.time()
        last_status = time.time()
        last_weight_update = time.time()

        print("NVDA 멀티 타임프레임 거래 시작...")

        while True:
            try:
                # 각 종목의 가격 업데이트
                for symbol in self.symbols:
                    price = self.get_stock_price(symbol)
                    if price is not None:
                        self.price_history[symbol].append(price)

                        # 최근 1000개 가격 유지
                        if len(self.price_history[symbol]) > 1000:
                            self.price_history[symbol] = self.price_history[symbol][-1000:]

                current_time = time.time()

                # 모든 모델 처리
                if all(len(self.price_history[symbol]) > 50 for symbol in self.symbols):
                    for model_key in self.models.keys():
                        model = self.models[model_key]
                        symbol = model['symbol']

                        indicators = self.calculate_indicators(symbol, model)
                        if indicators:
                            signal = self.generate_signal(model, indicators)
                            if signal:
                                self.execute_trade(model_key, signal)

                # 가중치 업데이트 (10분마다)
                if current_time - last_weight_update > 600:
                    self.update_weights()
                    last_weight_update = current_time

                # 저장 (3분마다)
                if current_time - last_save > 180:
                    self.save_progress()
                    last_save = current_time

                # 상태 출력 (5분마다)
                if current_time - last_status > 300:
                    self.print_status()
                    last_status = current_time

                time.sleep(10)  # 10초 간격

            except KeyboardInterrupt:
                print("\n거래 중단")
                self.save_progress()
                break
            except Exception as e:
                print(f"오류: {e}")
                time.sleep(30)

if __name__ == "__main__":
    trader = NVDAMultiTimeframeTrader()
    trader.run()