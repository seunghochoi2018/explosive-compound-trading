import requests
import json
import time
from datetime import datetime
import os

class NVDLNVDQSignalTrader:
    def __init__(self):
        """NVDL/NVDQ 멀티모델 신호 생성 시스템 (자동매매 없음)"""
        print("NVDL/NVDQ 멀티모델 신호 생성 시스템 초기화...")

        # FMP API 키
        self.api_key = "85rlFsFlAawfvGQ7xGw9vHvLvEimoRnr"

        # 거래 설정 (먼저 정의)
        self.symbols = ['NVDL', 'NVDQ']  # NVDA 레버리지 ETF
        self.initial_balance = 10000.0
        self.current_balance = self.initial_balance

        # 리스크 관리
        self.max_position_size = 0.1  # 기본 10%

        # 기존 학습된 모델 로드
        self.load_learned_models()

        print(f"거래 심볼: {', '.join(self.symbols)}")
        print(f"초기 자금: ${self.initial_balance:.2f}")

    def load_learned_models(self):
        """기존 학습된 모델 데이터 로드"""
        self.model_file = 'nvdl_nvdq_model_progress.json'

        try:
            with open(self.model_file, 'r', encoding='utf-8') as f:
                progress = json.load(f)

            self.learned_models = {}
            model_performance = progress.get('model_performance', {})

            # 성과 좋은 모델들만 선별 (승률 60% 이상)
            for model_key, perf in model_performance.items():
                trades = perf.get('trades', 0)
                wins = perf.get('wins', 0)

                if trades >= 3:  # 최소 3회 거래 경험
                    win_rate = wins / trades
                    if win_rate >= 0.6:  # 60% 이상 승률
                        # 모델명에서 타임프레임 추출
                        parts = model_key.split('_')
                        timeframe = parts[0] if parts else '15m'
                        interval_map = {
                            '15m': 900, '1h': 3600, '4h': 14400,
                            '12h': 43200, '1d': 86400
                        }

                        self.learned_models[model_key] = {
                            'weight': perf.get('weight', 1.0),
                            'win_rate': win_rate,
                            'avg_profit': perf.get('total_profit', 0) / trades,
                            'trades': trades,
                            'wins': wins,
                            'timeframe': timeframe,
                            'interval': interval_map.get(timeframe, 900),
                            'last_signal_time': 0,
                            'symbol': perf.get('symbol', 'NVDL')  # 기본 NVDL
                        }

            print(f"우수 모델 {len(self.learned_models)}개 로드 완료")

            # 상위 모델들 출력
            sorted_models = sorted(self.learned_models.items(),
                                 key=lambda x: x[1]['win_rate'], reverse=True)
            for i, (model, perf) in enumerate(sorted_models[:5]):
                symbol = perf.get('symbol', 'NVDL')
                print(f"  {i+1}. {model} ({symbol}): {perf['win_rate']*100:.1f}% 승률")

        except FileNotFoundError:
            print("학습 데이터 없음. 새로 시작")
            self.learned_models = self.create_initial_models()
            # 초기 모델 파일 생성
            self.save_models()

    def create_initial_models(self):
        """초기 모델 생성"""
        models = {}
        # 해외주식 특성 반영한 타임프레임
        timeframes = ['15m', '1h', '4h', '12h', '1d']
        strategies = ['momentum', 'counter_trend', 'breakout', 'mean_reversion']
        leverages = [1, 2, 3]  # NVDL은 2x, NVDQ는 -2x 이미 내장

        interval_map = {
            '15m': 900, '1h': 3600, '4h': 14400,
            '12h': 43200, '1d': 86400
        }

        for symbol in self.symbols:
            for tf in timeframes:
                for strategy in strategies:
                    for leverage in leverages:
                        model_key = f"{tf}_{leverage}x_{strategy}_{symbol}"

                        models[model_key] = {
                            'timeframe': tf,
                            'interval': interval_map[tf],
                            'strategy': strategy,
                            'leverage': leverage,
                            'symbol': symbol,
                            'trades': 0,
                            'wins': 0,
                            'win_rate': 0.5,
                            'avg_profit': 0.0,
                            'weight': 1.0,
                            'last_signal_time': 0
                        }

        print(f"초기 모델 {len(models)}개 생성 완료")
        return models

    def get_current_price(self, symbol='NVDL'):
        """현재 NVDL/NVDQ 가격 조회"""
        try:
            # FMP API로 실시간 가격 조회
            url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}?apikey={self.api_key}"
            response = requests.get(url, timeout=15)

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return float(data[0]['price'])

            # 백업: 다른 엔드포인트 시도
            url = f"https://financialmodelingprep.com/api/v3/quote-short/{symbol}?apikey={self.api_key}"
            response = requests.get(url, timeout=15)

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return float(data[0]['price'])

        except Exception as e:
            print(f"가격 조회 오류 ({symbol}): {e}")

        return None

    def get_best_model(self, symbol='NVDL'):
        """특정 심볼의 승률 가장 높은 모델 선택"""
        if not self.learned_models:
            return None

        # 해당 심볼의 모델만 필터링
        symbol_models = {k: v for k, v in self.learned_models.items()
                        if v.get('symbol') == symbol}

        if not symbol_models:
            return None

        # 승률 기준으로 최고 모델 선택
        best_model = max(symbol_models.items(),
                        key=lambda x: x[1]['win_rate'])
        return best_model

    def calculate_position_size(self, symbol='NVDL'):
        """동적 포지션 크기 계산"""
        # 모델 승률에 따라 포지션 크기 조절
        best_model = self.get_best_model(symbol)

        if best_model:
            model_key, model_data = best_model
            win_rate = model_data.get('win_rate', 0.5)

            # 승률에 따른 포지션 비율
            if win_rate >= 0.9:
                position_ratio = 0.25  # 25%
            elif win_rate >= 0.75:
                position_ratio = 0.20  # 20%
            elif win_rate >= 0.6:
                position_ratio = 0.15  # 15%
            else:
                position_ratio = 0.10  # 10%

            # NVDQ(인버스)는 조금 더 보수적으로
            if 'NVDQ' in symbol:
                position_ratio *= 0.8

        else:
            position_ratio = self.max_position_size

        return self.current_balance * position_ratio

    def generate_trading_signal(self, symbol='NVDL'):
        """최고 승률 모델로 거래 신호 생성"""
        best_model = self.get_best_model(symbol)
        if not best_model:
            return None

        model_key, model_data = best_model
        current_time = time.time()

        # 모델의 거래 주기 체크
        if current_time - model_data['last_signal_time'] < model_data['interval']:
            return None

        # 현재 가격 조회
        price = self.get_current_price(symbol)
        if price is None:
            return None

        # 최고 모델의 전략에 따른 신호 생성
        strategy = model_data.get('strategy', 'momentum')

        if strategy == 'momentum':
            # 모멘텀: 상승 추세면 BUY
            if hasattr(self, f'last_price_{symbol}'):
                signal = 1 if price > getattr(self, f'last_price_{symbol}') else -1
            else:
                signal = 0

        elif strategy == 'counter_trend':
            # 역추세: 상승하면 SELL, 하락하면 BUY
            if hasattr(self, f'last_price_{symbol}'):
                signal = -1 if price > getattr(self, f'last_price_{symbol}') else 1
            else:
                signal = 0

        elif strategy == 'mean_reversion':
            # 평균 회귀: 극단에서 반대 포지션
            if hasattr(self, f'avg_price_{symbol}'):
                avg = getattr(self, f'avg_price_{symbol}')
                deviation = (price - avg) / avg
                if deviation > 0.02:  # 2% 이상 상승
                    signal = -1
                elif deviation < -0.02:  # 2% 이상 하락
                    signal = 1
                else:
                    signal = 0
            else:
                signal = 0

        else:  # breakout
            # 돌파: 강한 움직임 따라가기
            if hasattr(self, f'last_price_{symbol}'):
                change = (price - getattr(self, f'last_price_{symbol}')) / getattr(self, f'last_price_{symbol}')
                if abs(change) > 0.01:  # 1% 이상 변화
                    signal = 1 if change > 0 else -1
                else:
                    signal = 0
            else:
                signal = 0

        # 마지막 가격 업데이트
        setattr(self, f'last_price_{symbol}', price)

        # 평균 가격 업데이트 (지수이동평균)
        if hasattr(self, f'avg_price_{symbol}'):
            avg = getattr(self, f'avg_price_{symbol}')
            new_avg = avg * 0.95 + price * 0.05
            setattr(self, f'avg_price_{symbol}', new_avg)
        else:
            setattr(self, f'avg_price_{symbol}', price)

        # 신호가 생성되면 마지막 신호 시간 업데이트
        if signal != 0:
            model_data['last_signal_time'] = current_time

        return 'BUY' if signal > 0 else 'SELL' if signal < 0 else None

    def update_model_performance(self, model_key, is_win, profit):
        """거래 결과로 모델 성과 업데이트"""
        if model_key not in self.learned_models:
            return

        model_data = self.learned_models[model_key]

        # 성과 업데이트
        model_data['trades'] += 1
        if is_win:
            model_data['wins'] += 1

        # 새로운 승률 계산
        model_data['win_rate'] = model_data['wins'] / model_data['trades']

        # 평균 수익 업데이트
        total_profit = model_data['avg_profit'] * (model_data['trades'] - 1) + profit
        model_data['avg_profit'] = total_profit / model_data['trades']

        print(f"\n학습 진행중...")
        print(f"  모델: {model_key}")
        print(f"  결과: {'승리' if is_win else '패배'} 기록")
        print(f"  거래: {model_data['trades']}, 승리: {model_data['wins']}")
        print(f"  새 승률: {model_data['win_rate']*100:.1f}%")
        print(f"  평균 수익: {model_data['avg_profit']:.2f}%")

    def save_models(self):
        """모델 성과를 파일에 저장"""
        try:
            # 기존 파일이 있으면 로드
            if os.path.exists(self.model_file):
                with open(self.model_file, 'r', encoding='utf-8') as f:
                    progress = json.load(f)
            else:
                progress = {}

            # 모델 성과 업데이트
            progress['model_performance'] = {}
            for model_key, model_data in self.learned_models.items():
                progress['model_performance'][model_key] = {
                    'trades': model_data['trades'],
                    'wins': model_data.get('wins', 0),
                    'win_rate': model_data['win_rate'],
                    'total_profit': model_data['avg_profit'] * model_data['trades'],
                    'avg_profit': model_data['avg_profit'],
                    'weight': model_data.get('weight', 1.0),
                    'symbol': model_data.get('symbol', 'NVDL')
                }

            progress['timestamp'] = datetime.now().isoformat()
            progress['balance'] = self.current_balance

            # 파일에 저장
            with open(self.model_file, 'w', encoding='utf-8') as f:
                json.dump(progress, f, ensure_ascii=False, indent=2)

            print("모델 성과 저장 완료")

        except Exception as e:
            print(f"모델 저장 오류: {e}")

    def run_signal_generation(self):
        """신호 생성 및 모니터링 (자동매매 없음)"""
        print("\nNVDL/NVDQ 신호 생성 시작!")
        print("=" * 50)
        print("* 자동매매 기능 없음 - 신호만 생성")
        print("* 실제 거래는 수동으로 진행하세요")
        print("=" * 50)

        last_save_time = time.time()
        save_interval = 300  # 5분마다 자동 저장

        positions = {}  # 가상 포지션 추적 (학습용)

        while True:
            try:
                for symbol in self.symbols:
                    # 현재 가격 조회
                    price = self.get_current_price(symbol)
                    if price is None:
                        continue

                    current_time = datetime.now().strftime('%H:%M:%S')

                    # 가상 포지션 상태 표시
                    if symbol in positions:
                        position = positions[symbol]
                        hold_minutes = (time.time() - position['entry_time']) / 60

                        if position['side'] == 'BUY':
                            pnl = (price - position['entry_price']) / position['entry_price'] * 100
                        else:
                            pnl = (position['entry_price'] - price) / position['entry_price'] * 100

                        print(f"\n[{current_time}] {symbol}: ${price:.2f} | [가상] {position['side']} 포지션 {hold_minutes:.1f}분 보유 | P&L: {pnl:+.2f}%")

                        # 청산 신호 체크
                        exit_signal = self.generate_trading_signal(symbol)
                        if exit_signal and exit_signal != position['side']:
                            print(f"  [청산 신호] {exit_signal} - 실제 거래 권장!")

                            # 모델 성과 업데이트 (가상 거래 결과)
                            is_win = pnl > 0
                            self.update_model_performance(position['model'], is_win, pnl)

                            # 가상 포지션 제거
                            del positions[symbol]

                        else:
                            # 다음 체크 시간 표시
                            best_model = self.get_best_model(symbol)
                            if best_model:
                                model_key, model_data = best_model
                                time_since_last = time.time() - model_data.get('last_signal_time', 0)
                                if time_since_last < model_data['interval']:
                                    print(f"  모델 {model_key} 대기중 | 다음 체크: {(model_data['interval']-time_since_last)/60:.1f}분 후")

                    else:
                        print(f"\n[{current_time}] {symbol}: ${price:.2f} | 대기중")

                        # 신규 진입 신호 체크
                        signal = self.generate_trading_signal(symbol)

                        if signal:
                            best_model = self.get_best_model(symbol)
                            if best_model:
                                model_key, model_data = best_model
                                position_size = self.calculate_position_size(symbol)

                                print(f"  [진입 신호] {signal} - 실제 거래 권장!")
                                print(f"  모델: {model_key}")
                                print(f"  승률: {model_data['win_rate']*100:.1f}%")
                                print(f"  권장 포지션: ${position_size:.2f}")

                                # 가상 포지션 생성 (학습용)
                                positions[symbol] = {
                                    'side': signal,
                                    'entry_price': price,
                                    'entry_time': time.time(),
                                    'model': model_key,
                                    'size': position_size
                                }
                        else:
                            # 다음 신호까지 시간 표시
                            best_model = self.get_best_model(symbol)
                            if best_model:
                                model_key, model_data = best_model
                                next_signal_sec = model_data['interval'] - (time.time() - model_data['last_signal_time'])
                                if next_signal_sec > 0:
                                    print(f"  모델: {model_key} | 다음 신호까지: {next_signal_sec/60:.1f}분")

                # 주기적 자동 저장
                if time.time() - last_save_time > save_interval:
                    print("\n  [자동 저장 중...]")
                    self.save_models()
                    last_save_time = time.time()

                time.sleep(10)  # 10초 간격

            except KeyboardInterrupt:
                print("\n신호 생성 중단")
                self.save_models()
                break
            except Exception as e:
                print(f"오류: {e}")
                time.sleep(30)

if __name__ == "__main__":
    trader = NVDLNVDQSignalTrader()
    trader.run_signal_generation()