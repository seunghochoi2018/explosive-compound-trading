import requests
import json
import time
import random
import math
from datetime import datetime, timedelta
import pytz

class NVDLNVDQMultiTrader:
    def __init__(self):
        print("NVDL/NVDQ 멀티 모델 트레이더 초기화 시작...")
        self.balance = 10000.0
        self.current_prices = {'NVDL': 0, 'NVDQ': 0}
        self.price_history = {'NVDL': [], 'NVDQ': []}
        self.all_trades = []

        # Financial Modeling Prep API 키 import
        try:
            from config import FMP_API_KEY
            self.api_key = FMP_API_KEY
        except ImportError:
            self.api_key = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"  # 백업 키

        print("기본 설정 로드 중...")
        # 기본 주기 설정 (실제 봉 시간에 맞춤)
        self.base_timeframes = {
            '15m': {'interval': 900, 'candle_period': 900},      # 15분봉 = 15분마다 거래
            '1h': {'interval': 3600, 'candle_period': 3600},     # 1시간봉 = 1시간마다 거래
            '4h': {'interval': 14400, 'candle_period': 14400},   # 4시간봉 = 4시간마다 거래
            '12h': {'interval': 43200, 'candle_period': 43200},  # 12시간봉 = 12시간마다 거래
            '1d': {'interval': 86400, 'candle_period': 86400}    # 1일봉 = 1일마다 거래
        }

        # 레버리지 옵션 (NVDL/NVDQ는 이미 레버리지 ETN이므로 1x만)
        self.leverages = [1]  # 레버리지 없음 - 현물 거래만

        # 거래 방향 옵션
        self.directions = ['both', 'long_only', 'short_only']

        # 전략 옵션
        self.strategies = ['momentum', 'counter_trend', 'breakout']

        # 거래할 종목
        self.symbols = ['NVDL', 'NVDQ']

        print("모델 생성 중...")
        # 모든 모델 생성
        self.models = {}
        self.create_all_models()

        print(f"=== NVDL/NVDQ 멀티 모델 트레이더 시작 ===")
        print(f"총 {len(self.models)}개 모델 생성")
        print("종목: NVDL (3x Long), NVDQ (3x Inverse)")
        print("주기: 15분, 1시간, 4시간, 12시간, 1일")
        print("레버리지: 현물 거래만 (ETN 자체가 레버리지)")
        print("방향: 롱+숏, 롱만, 숏만")
        print("전략: 모멘텀, 역추세, 돌파")
        print("순수 시장 데이터 학습 - 기술적 분석 없음")
        print("성과 좋은 모델로 자동 수렴")

    def create_all_models(self):
        """모든 모델 조합 생성"""
        model_id = 0
        total_models = len(self.symbols) * len(self.base_timeframes) * len(self.leverages) * len(self.directions) * len(self.strategies)

        for symbol in self.symbols:
            for tf_name, tf_config in self.base_timeframes.items():
                for leverage in self.leverages:
                    for direction in self.directions:
                        for strategy in self.strategies:
                            model_key = f"{symbol}_{tf_name}_{leverage}x_{direction}_{strategy}"

                            self.models[model_key] = {
                                'id': model_id,
                                'symbol': symbol,
                                'timeframe': tf_name,
                                'leverage': leverage,
                                'direction': direction,
                                'strategy': strategy,
                                'interval': tf_config['interval'],
                                'base_position_size': 0.05 / total_models,  # 기본 포지션 크기
                                'position_size': 0.05 / total_models,  # 동적으로 조절되는 포지션 크기
                                'fee_rate': 0.001,  # 주식 수수료 (0.1%)
                                'last_trade': 0,
                                'trades': 0,
                                'wins': 0,
                                'total_profit': 0.0,
                                'weight': 1.0,
                                'position': None,
                                'entry_price': 0,
                                'entry_time': 0,
                                'current_pnl': 0.0,
                                'max_drawdown': 0.0,
                                'max_profit': 0.0,
                                'trend_strength': 0.0,
                                'recent_profits': [],
                                'leverage_performance': 0.0,
                                'timeframe_performance': 0.0
                            }
                            model_id += 1

    def is_market_open(self):
        """미국 주식 시장 개장 시간 확인"""
        est = pytz.timezone('US/Eastern')
        now_est = datetime.now(est)

        # 주말은 휴장
        if now_est.weekday() >= 5:  # 5=토요일, 6=일요일
            return False

        # 평일 9:30 ~ 16:00 EST
        market_open = now_est.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now_est.replace(hour=16, minute=0, second=0, microsecond=0)

        return market_open <= now_est <= market_close

    def get_stock_price(self, symbol):
        """FMP API를 통해 실시간 주식 가격 가져오기"""
        try:
            # Financial Modeling Prep 실시간 가격 API
            url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}?apikey={self.api_key}"
            response = requests.get(url, timeout=15)

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return float(data[0]['price'])

            # 백업: Yahoo Finance 스타일 (데모용)
            if symbol == 'NVDL':
                return 50.0 + random.uniform(-2, 2)  # 데모 가격
            elif symbol == 'NVDQ':
                return 75.0 + random.uniform(-3, 3)  # 데모 가격

        except Exception as e:
            print(f"가격 수집 오류 ({symbol}): {e}")

        return None

    def calculate_market_data(self, model):
        """순수 시장 데이터만 제공 - 봇이 직접 학습"""
        symbol = model['symbol']
        timeframe = model['timeframe']

        required_data = {
            '15m': 20,   # 15분봉 20개 = 5시간 데이터
            '1h': 24,    # 1시간봉 24개 = 1일 데이터
            '4h': 24,    # 4시간봉 24개 = 4일 데이터
            '12h': 14,   # 12시간봉 14개 = 1주 데이터
            '1d': 30     # 1일봉 30개 = 1달 데이터
        }

        min_data = required_data.get(timeframe, 10)
        price_history = self.price_history[symbol]

        if len(price_history) < min_data:
            return None

        recent_prices = price_history[-min_data:]

        return {
            'current_price': self.current_prices[symbol],
            'price_history': recent_prices,
            'price_changes': [
                recent_prices[i] - recent_prices[i-1]
                for i in range(1, len(recent_prices))
            ],
            'price_ratios': [
                recent_prices[i] / recent_prices[i-1]
                for i in range(1, len(recent_prices))
            ]
        }

    def generate_signal(self, model, market_data):
        """순수 시장 데이터로 봇이 스스로 학습하여 신호 생성"""
        if not market_data:
            return None

        strategy = model['strategy']
        direction = model['direction']
        leverage = model['leverage']

        # 시장 데이터 분석
        current_price = market_data['current_price']
        price_history = market_data['price_history']
        price_changes = market_data['price_changes']
        price_ratios = market_data['price_ratios']

        # 봇이 스스로 학습할 시장 패턴들
        signal_strength = 0.0

        # 1. 최근 가격 움직임 패턴 학습
        if len(price_changes) >= 3:
            recent_momentum = sum(price_changes[-3:]) / 3
            total_momentum = sum(price_changes) / len(price_changes)

            # 모멘텀 패턴에 따른 신호 강도
            if strategy == 'momentum':
                if recent_momentum > 0 and total_momentum > 0:
                    signal_strength += 0.3  # 상승 모멘텀
                elif recent_momentum < 0 and total_momentum < 0:
                    signal_strength -= 0.3  # 하락 모멘텀

            elif strategy == 'counter_trend':
                if recent_momentum > 0 and total_momentum < 0:
                    signal_strength -= 0.2  # 반전 예상 (매도)
                elif recent_momentum < 0 and total_momentum > 0:
                    signal_strength += 0.2  # 반전 예상 (매수)

            elif strategy == 'breakout':
                volatility = sum(abs(c) for c in price_changes) / len(price_changes)
                if abs(recent_momentum) > volatility * 1.5:
                    signal_strength += 0.4 if recent_momentum > 0 else -0.4

        # 2. 가격 비율 패턴 학습
        if len(price_ratios) >= 5:
            avg_ratio = sum(price_ratios) / len(price_ratios)
            recent_ratio = price_ratios[-1]

            # 비정상적 움직임 감지
            if recent_ratio > avg_ratio * 1.02:  # 2% 이상 상승
                signal_strength += 0.2
            elif recent_ratio < avg_ratio * 0.98:  # 2% 이상 하락
                signal_strength -= 0.2

        # 3. 개별 모델의 과거 성과 반영
        if model['trades'] > 0:
            win_rate = model['wins'] / model['trades']
            avg_profit = model['total_profit'] / model['trades']

            # 성과 좋은 모델일수록 더 적극적으로
            performance_multiplier = (win_rate * 0.7 + max(0, avg_profit + 0.01) * 30)
            signal_strength *= performance_multiplier

        # 4. 신호 결정 임계값 (현물 거래)
        threshold = 0.15  # 15% 신호 강도 이상에서 거래

        # 신호 결정
        signal = None
        if signal_strength > threshold:
            signal = 'BUY'
        elif signal_strength < -threshold:
            signal = 'SELL'

        # 방향 제한 적용
        if direction == 'long_only' and signal == 'SELL':
            signal = None
        elif direction == 'short_only' and signal == 'BUY':
            signal = None

        return signal

    def generate_exit_signal(self, model, market_data):
        """순수 시장 데이터 기반 청산 신호 생성"""
        if not model['position'] or not market_data:
            return False

        strategy = model['strategy']
        position = model['position']
        leverage = model['leverage']

        # 현재 손익 계산 (현물 거래 - 레버리지 없음)
        current_price = self.current_prices[model['symbol']]
        if position == 'BUY':
            pnl_ratio = (current_price - model['entry_price']) / model['entry_price']
        else:
            pnl_ratio = (model['entry_price'] - current_price) / model['entry_price']

        # 레버리지 없음 (현물)
        net_pnl_ratio = pnl_ratio - model['fee_rate'] * 2

        # 시장 데이터 분석
        price_changes = market_data['price_changes']
        price_ratios = market_data['price_ratios']

        exit_strength = 0.0

        # 1. 손익 기반 청산 판단
        if net_pnl_ratio > 0.03:  # 3% 이상 수익 시 청산 고려 (주식은 더 보수적)
            exit_strength += 0.3
        elif net_pnl_ratio < -0.05:  # 5% 이상 손실 시 청산 고려
            exit_strength += 0.5

        # 2. 시장 모멘텀 변화 감지
        if len(price_changes) >= 3:
            recent_momentum = sum(price_changes[-3:]) / 3

            if strategy == 'momentum':
                # 모멘텀 전략: 모멘텀 약화 시 청산
                if position == 'BUY' and recent_momentum < 0:
                    exit_strength += 0.4
                elif position == 'SELL' and recent_momentum > 0:
                    exit_strength += 0.4

            elif strategy == 'counter_trend':
                # 역추세 전략: 예상 반전 완료 시 청산
                if position == 'BUY' and recent_momentum > 0:
                    exit_strength += 0.3
                elif position == 'SELL' and recent_momentum < 0:
                    exit_strength += 0.3

            elif strategy == 'breakout':
                # 돌파 전략: 모멘텀 소실 시 청산
                if abs(recent_momentum) < 0.01:
                    exit_strength += 0.3

        # 3. 개별 모델 성과 반영
        if model['trades'] > 2:
            win_rate = model['wins'] / model['trades']
            if win_rate < 0.3:  # 승률 30% 미만이면 빠른 청산
                exit_strength += 0.2

        # 4. 강제 청산 조건 (NVDL/NVDQ는 변동성이 크므로 더 보수적)
        if net_pnl_ratio <= -0.05:  # -5% 이상 손실 시 강제 청산
            return True

        # 청산 결정
        return exit_strength > 0.5

    def should_exit_position(self, model):
        """순수 시장 데이터 기반 청산 결정"""
        if not model['position']:
            return False

        market_data = self.calculate_market_data(model)
        if not market_data:
            return False

        return self.generate_exit_signal(model, market_data)

    def execute_trade(self, model_key, signal):
        model = self.models[model_key]
        current_time = time.time()

        # 시장 개장 시간 확인
        if not self.is_market_open():
            return  # 시장 휴장시 거래 중단

        # 각 시간대별 실제 봉 주기에 맞춰 거래
        timeframe_intervals = {
            '15m': 900,    # 15분 = 900초
            '1h': 3600,    # 1시간 = 3600초
            '4h': 14400,   # 4시간 = 14400초
            '12h': 43200,  # 12시간 = 43200초
            '1d': 86400    # 1일 = 86400초
        }

        required_interval = timeframe_intervals.get(model['timeframe'], model['interval'])

        if current_time - model['last_trade'] < required_interval:
            return

        symbol = model['symbol']
        current_price = self.current_prices[symbol]

        if not model['position']:
            # 신규 진입
            model['position'] = signal
            model['entry_price'] = current_price
            model['entry_time'] = current_time
            model['last_trade'] = current_time
            model['trades'] += 1

            print(f"[{symbol}_{model['timeframe']}_{model['leverage']}x_{model['strategy']}] {signal} 진입: ${current_price:.2f}")

        elif self.should_exit_position(model):
            # 포지션 청산
            exit_price = current_price
            hold_duration = current_time - model['entry_time']

            if model['position'] == 'BUY':
                pnl_ratio = (exit_price - model['entry_price']) / model['entry_price']
            else:
                pnl_ratio = (model['entry_price'] - exit_price) / model['entry_price']

            # 레버리지 없음 (현물 거래)
            # 수수료 차감
            net_pnl_ratio = pnl_ratio - model['fee_rate'] * 2
            pnl = self.balance * model['position_size'] * net_pnl_ratio

            # 현재 PnL 업데이트
            model['current_pnl'] = pnl

            # 거래 기록
            trade_data = {
                'model': model_key,
                'symbol': symbol,
                'timeframe': model['timeframe'],
                'leverage': model['leverage'],
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

            profit_status = "✅수익" if pnl > 0 else "❌손실"
            print(f"🔥 [{symbol}_{model['timeframe']}_{model['leverage']}x_{model['strategy']}] {profit_status}")
            print(f"   진입: ${model['entry_price']:.2f} → 청산: ${exit_price:.2f}")
            print(f"   보유: {hold_duration/3600:.1f}시간, 실현손익: {net_pnl_ratio*100:.2f}% (${pnl:.2f})")
            print(f"   누적거래: {model['trades']}회, 누적수익: ${model['total_profit']:.2f}")
            print("-" * 60)

            # 포지션 클리어
            model['position'] = None
            model['entry_price'] = 0
            model['entry_time'] = 0
            model['last_trade'] = current_time

    def convergence_system(self):
        """성과 기반 모델 수렴 시스템"""
        # 충분한 거래 데이터가 있는 모델들만 평가
        active_models = [(k, v) for k, v in self.models.items() if v['trades'] >= 3]

        if len(active_models) < 10:
            return  # 충분한 데이터 없음

        # 성과 점수 계산 (승률 + 평균수익 + 총수익 조합)
        for model_key, model in active_models:
            win_rate = model['wins'] / model['trades']
            avg_profit = model['total_profit'] / model['trades']
            total_profit = model['total_profit']

            # 통합 성과 점수
            performance_score = (
                win_rate * 0.4 +                    # 승률 40%
                max(0, avg_profit + 0.005) * 50 +   # 평균수익 40%
                max(0, total_profit + 0.01) * 10    # 총수익 20%
            )

            model['performance_score'] = performance_score

        # 상위 성과 모델들 식별
        active_models.sort(key=lambda x: x[1]['performance_score'], reverse=True)
        top_20_percent = len(active_models) // 5
        top_models = active_models[:max(5, top_20_percent)]

        # 상위 모델들에게 자본 집중
        for i, (model_key, model) in enumerate(top_models):
            bonus_multiplier = 3.0 - (i * 0.3)  # 1위: 3배, 2위: 2.7배...
            model['position_size'] = model['base_position_size'] * bonus_multiplier

        # 하위 모델 자본 감소
        poor_models = active_models[len(top_models):]
        for model_key, model in poor_models:
            if model['performance_score'] < 0.3:  # 낮은 성과
                model['position_size'] = model['base_position_size'] * 0.2  # 80% 감소

        print(f"🔥 수렴 시스템: 상위 {len(top_models)}개 모델에 자본 집중")
        for i, (model_key, model) in enumerate(top_models[:3]):
            print(f"   {i+1}위: {model_key} (점수: {model['performance_score']:.3f})")

        return top_models

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
        progress = {
            'timestamp': datetime.now().isoformat(),
            'balance': self.balance,
            'current_prices': self.current_prices,
            'total_models': len(self.models),
            'model_performance': {},
            'recent_trades': self.all_trades[-50:],
            'summary': {},
            'market_status': self.is_market_open()
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
                    'symbol': model['symbol'],
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

        with open('C:\\Users\\user\\Documents\\코드4\\nvdl_nvdq_progress.json', 'w', encoding='utf-8') as f:
            json.dump(progress, f, indent=2, ensure_ascii=False)

    def print_status(self):
        print(f"\n=== NVDL/NVDQ 멀티 모델 트레이딩 현황 ===")
        print(f"NVDL: ${self.current_prices['NVDL']:.2f}, NVDQ: ${self.current_prices['NVDQ']:.2f}")
        print(f"시장 상태: {'🟢 개장' if self.is_market_open() else '🔴 휴장'}")
        print(f"총 모델: {len(self.models)}개")

        # 상위 성과 모델들
        performing_models = [(k, v) for k, v in self.models.items() if v['trades'] > 0]
        performing_models.sort(key=lambda x: x[1]['total_profit'], reverse=True)

        print(f"\n💰 실현손익 TOP 10 (총 {len(performing_models)}개 활성):")
        for i, (model_key, model) in enumerate(performing_models[:10]):
            win_rate = (model['wins'] / model['trades']) * 100
            avg_profit = model['total_profit'] / model['trades']
            position_info = f"[{model['position']}]" if model['position'] else ""
            profit_emoji = "✅" if model['total_profit'] > 0 else "❌" if model['total_profit'] < 0 else "⚪"

            print(f"{profit_emoji} {i+1:2d}. [{model['symbol']}_{model['timeframe']}_{model['leverage']}x_{model['strategy']}]")
            print(f"      거래: {model['wins']:2d}승/{model['trades']:2d}전 ({win_rate:4.1f}%) | "
                  f"실현손익: ${model['total_profit']:7.2f} | 평균: ${avg_profit:6.2f} {position_info}")
            print()

        # 전체 통계
        total_trades = sum(m['trades'] for m in self.models.values())
        total_wins = sum(m['wins'] for m in self.models.values())
        total_profit = sum(m['total_profit'] for m in self.models.values())
        active_positions = len([m for m in self.models.values() if m['position']])

        print(f"\n전체 통계:")
        print(f"총 거래: {total_trades}, 승리: {total_wins}, 승률: {total_wins/total_trades*100 if total_trades > 0 else 0:.1f}%")
        print(f"총 수익: ${total_profit:.2f}, 활성 포지션: {active_positions}개")

    def run(self):
        last_save = time.time()
        last_status = time.time()
        last_weight_update = time.time()

        print("NVDL/NVDQ 멀티 모델 거래 시작...")

        cycle_count = 0
        while True:
            try:
                cycle_count += 1
                print(f"\n[사이클 {cycle_count}] 가격 수집 중...")

                # 두 종목 가격 수집
                nvdl_price = self.get_stock_price('NVDL')
                nvdq_price = self.get_stock_price('NVDQ')

                if nvdl_price is None or nvdq_price is None:
                    print("가격 수집 실패, 30초 대기...")
                    time.sleep(30)
                    continue

                self.current_prices['NVDL'] = nvdl_price
                self.current_prices['NVDQ'] = nvdq_price
                self.price_history['NVDL'].append(nvdl_price)
                self.price_history['NVDQ'].append(nvdq_price)

                print(f"NVDL: ${nvdl_price:.2f}, NVDQ: ${nvdq_price:.2f}")
                print(f"시장: {'🟢 개장' if self.is_market_open() else '🔴 휴장'}")

                # 최근 1000개 가격 유지
                for symbol in ['NVDL', 'NVDQ']:
                    if len(self.price_history[symbol]) > 1000:
                        self.price_history[symbol] = self.price_history[symbol][-1000:]

                current_time = time.time()

                # 모든 모델 처리
                min_data_needed = min([20, 24, 24, 14, 30])  # 각 시간대별 최소 필요 데이터
                if all(len(self.price_history[symbol]) > min_data_needed for symbol in ['NVDL', 'NVDQ']):
                    print(f"모델 분석 시작... (총 {len(self.models)}개 모델)")
                    signals_generated = 0
                    trades_executed = 0

                    for model_key in self.models.keys():
                        market_data = self.calculate_market_data(self.models[model_key])
                        if market_data:
                            signal = self.generate_signal(self.models[model_key], market_data)
                            if signal:
                                signals_generated += 1
                                self.execute_trade(model_key, signal)
                                trades_executed += 1

                    print(f"신호 생성: {signals_generated}개, 거래 실행: {trades_executed}개")
                else:
                    min_collected = min(len(self.price_history[s]) for s in ['NVDL', 'NVDQ'])
                    print(f"데이터 수집 중... ({min_collected}/{min_data_needed})")

                # 가중치 업데이트 및 수렴 시스템 (5분마다)
                if current_time - last_weight_update > 300:
                    print("가중치 업데이트 중...")
                    self.update_weights()

                    # 수렴 시스템 실행 (충분한 데이터 축적 후)
                    total_trades = sum(m['trades'] for m in self.models.values())
                    if total_trades > 30:  # 총 30회 이상 거래 후 수렴 시작
                        self.convergence_system()

                    last_weight_update = current_time

                # 저장 (10분마다)
                if current_time - last_save > 600:
                    print("진행 상황 저장 중...")
                    self.save_progress()
                    last_save = current_time

                # 상태 출력 (2분마다)
                if current_time - last_status > 120:
                    self.print_status()
                    last_status = current_time

                # 시장 시간에 따른 대기 시간 조절
                if self.is_market_open():
                    print(f"30초 대기... (다음 사이클: {cycle_count + 1})")
                    time.sleep(30)  # 시장 개장시 30초 간격
                else:
                    print(f"시장 휴장 - 5분 대기... (다음 사이클: {cycle_count + 1})")
                    time.sleep(300)  # 시장 휴장시 5분 간격

            except KeyboardInterrupt:
                print("\n거래 중단")
                self.save_progress()
                break
            except Exception as e:
                print(f"오류: {e}")
                time.sleep(60)

if __name__ == "__main__":
    trader = NVDLNVDQMultiTrader()
    trader.run()