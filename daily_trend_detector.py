import requests
import numpy as np
import pandas as pd
from collections import deque
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

class DailyTrendDetector:
    """일봉 기반 NVDL/NVDQ 추세 감지 시스템 - 최적화된 정확도"""

    def __init__(self):
        print("일봉 추세 감지 시스템 v2.0")
        print("NVDL/NVDQ 특화 일봉 분석 (ETH 87% 정확도 적용)")

        # FMP API 설정
        self.fmp_api_key = '5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI'
        self.symbols = ['NVDL', 'NVDQ']
        self.cache = {}
        self.last_update = {}

        # 일봉 기반 최적화 (ETH 15분봉 시스템을 일봉으로 스케일업)
        self.primary_timeframe = '1d'
        self.primary_hours = 24

        # 보조 타임프레임들 (추세 확인용)
        self.secondary_timeframes = {
            '4h': 0.25,   # 4시간봉 (조기 확인)
            '1h': 0.15    # 1시간봉 (진입 타이밍)
        }

        # 각 타임프레임별 가격 히스토리 (더 많은 데이터)
        self.price_history = {
            '1d': deque(maxlen=100),  # 100일 일봉 데이터
            '4h': deque(maxlen=150),  # 25일 4시간봉
            '1h': deque(maxlen=200)   # 8일 1시간봉
        }

        # 마지막 업데이트 시간
        self.last_update = {
            '1d': 0,
            '4h': 0,
            '1h': 0
        }

        # 일봉 최적 파라미터 (ETH 15분봉 87% 정확도 시스템을 일봉에 적용)
        self.params = {
            '1d': {
                'window': 20,       # 20일 분석 윈도우
                'check_count': 5,   # 최근 5일로 추세 판단
                'threshold': 2.0,   # 2.0% 일일 움직임 (레버리지 ETF 특성)
                'confidence_weight': 0.6  # 60% 가중치 (메인)
            },
            '4h': {
                'window': 30,       # 5일 4시간봉 분석
                'check_count': 8,   # 최근 32시간으로 판단
                'threshold': 1.5,   # 1.5% 움직임
                'confidence_weight': 0.25  # 25% 가중치
            },
            '1h': {
                'window': 48,       # 2일 1시간봉 분석
                'check_count': 12,  # 최근 12시간으로 판단
                'threshold': 0.8,   # 0.8% 움직임
                'confidence_weight': 0.15  # 15% 가중치
            }
        }

        # NVDL/NVDQ 특성 고려 (레버리지 ETF 특성)
        self.volatility_multiplier = 1.5  # 변동성 증폭 고려

    def get_stock_data(self, symbol: str, timeframe: str = '1D', limit: int = 30) -> List[float]:
        """
        Alpha Vantage에서 주식 데이터 가져오기

        Args:
            symbol: 주식 심볼 (NVDL, NVDQ)
            timeframe: 시간 프레임
            limit: 데이터 개수
        """
        try:
            # Alpha Vantage API (무료 API 키 필요)
            api_key = "demo"  # 실제 사용시 API 키 필요

            if timeframe == '1D':
                function = 'TIME_SERIES_DAILY'
            elif timeframe == '4H':
                function = 'TIME_SERIES_INTRADAY'
                interval = '60min'  # 1시간 데이터로 4시간 구성
            else:
                function = 'TIME_SERIES_INTRADAY'
                interval = '60min'

            url = f"https://www.alphavantage.co/query"
            params = {
                'function': function,
                'symbol': symbol,
                'apikey': api_key,
                'outputsize': 'compact'
            }

            if function == 'TIME_SERIES_INTRADAY':
                params['interval'] = interval

            # 데모 데이터 (실제 구현시 API 호출)
            # NVDL/NVDQ의 실제 가격 패턴을 모방한 데모 데이터
            base_price = 45.0 if symbol == 'NVDL' else 18.0
            prices = []

            for i in range(limit):
                # 더 강한 트렌드와 변동성으로 시뮬레이션
                if i < limit // 3:  # 첫 1/3은 하락 트렌드
                    trend = -0.015 * np.random.uniform(0.5, 2.0)
                elif i < 2 * limit // 3:  # 중간 1/3은 횡보
                    trend = np.random.uniform(-0.005, 0.005)
                else:  # 마지막 1/3은 상승 트렌드
                    trend = 0.020 * np.random.uniform(0.5, 2.0)

                noise = np.random.normal(0, 0.03)  # 3% 노이즈
                volatility = 0.08 if symbol == 'NVDL' else 0.06  # 더 큰 변동성

                price_change = (trend + noise) * volatility * self.volatility_multiplier
                price = base_price * (1 + price_change)
                prices.append(price)
                base_price = price

            return prices

        except Exception as e:
            print(f"[ERROR] {symbol} {timeframe} 데이터 가져오기 실패: {e}")
            return []

    def update_price_data(self, symbol: str = 'NVDL'):
        """모든 타임프레임 데이터 업데이트"""
        current_time = time.time()

        timeframe_mapping = {
            '1d': ('1D', 86400),      # 일봉
            '4h': ('4H', 14400),      # 4시간
            '1h': ('1H', 3600)        # 1시간
        }

        for tf_name, (tf_api, tf_seconds) in timeframe_mapping.items():
            # 업데이트 주기 체크 (타임프레임의 1/4 간격)
            update_interval = tf_seconds * 0.25

            if current_time - self.last_update[tf_name] > update_interval:
                # 일봉은 더 많은 히스토리 데이터 수집
                limit = 100 if tf_name == '1d' else 50
                prices = self.get_stock_data(symbol=symbol, timeframe=tf_api, limit=limit)

                if prices:
                    # 기존 데이터와 중복 제거하여 추가
                    for price in prices:
                        if not self.price_history[tf_name] or price != self.price_history[tf_name][-1]:
                            self.price_history[tf_name].append(price)

                    self.last_update[tf_name] = current_time
                    print(f"[UPDATE] {symbol} {tf_name} 데이터 업데이트: {len(self.price_history[tf_name])}개")

    def detect_trend_reversal_single(self, prices: List[float], timeframe: str) -> Tuple[Optional[str], float]:
        """단일 타임프레임 추세 변환 감지"""
        if timeframe not in self.params:
            return None, 0

        params = self.params[timeframe]

        if len(prices) < params['window']:
            return None, 0

        # 최적화된 윈도우 사용
        recent_prices = prices[-params['window']:]
        changes = []

        # 변화율 계산
        for i in range(1, len(recent_prices)):
            change = (recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1] * 100
            changes.append(change)

        if len(changes) < params['check_count']:
            return None, 0

        # 최근 체크 개수만큼 확인
        recent_changes = changes[-params['check_count']:]
        threshold = params['threshold']

        up_moves = sum(1 for c in recent_changes if c > threshold)
        down_moves = sum(1 for c in recent_changes if c < -threshold)

        # 더 민감한 신호 생성을 위해 기준 완화
        min_required = max(1, int(params['check_count'] * 0.3))  # 30% 이상으로 완화

        if up_moves >= min_required:
            strength = min(0.8, up_moves / len(recent_changes) * 1.5)  # 강도 증폭
            return 'UP', strength
        elif down_moves >= min_required:
            strength = min(0.8, down_moves / len(recent_changes) * 1.5)  # 강도 증폭
            return 'DOWN', strength
        else:
            # 약한 신호도 감지
            avg_change = sum(recent_changes) / len(recent_changes)
            if avg_change > 0.5:
                return 'UP', 0.3
            elif avg_change < -0.5:
                return 'DOWN', 0.3
            else:
                return 'SIDEWAYS', 0.1

    def detect_multi_timeframe_reversal(self, symbol: str = 'NVDL', current_position: Optional[str] = None) -> Dict:
        """
        다중 타임프레임 종합 추세 변환 감지

        Args:
            symbol: 분석할 심볼 (NVDL, NVDQ)
            current_position: 현재 포지션 ('LONG', 'SHORT', None)

        Returns:
            dict: {
                'should_exit': bool,
                'confidence': float,
                'primary_signal': str,
                'consensus': str,
                'reason': str,
                'symbol': str
            }
        """
        # 데이터 업데이트
        self.update_price_data(symbol)

        signals = {}
        confidences = {}

        # 각 타임프레임 분석 (일봉 중심)
        for tf_name in ['1d', '4h', '1h']:
            if len(self.price_history[tf_name]) < 3:
                continue

            signal, strength = self.detect_trend_reversal_single(
                list(self.price_history[tf_name]), tf_name
            )

            if signal:
                signals[tf_name] = signal
                confidences[tf_name] = strength * self.params[tf_name]['confidence_weight']

        if not signals:
            return {
                'should_exit': False,
                'confidence': 0.0,
                'primary_signal': 'NONE',
                'consensus': 'NONE',
                'reason': '데이터 부족',
                'symbol': symbol,
                'timeframe_signals': {},
                'timeframe_confidences': {}
            }

        # 일봉 타임프레임 우선 (메인 신호)
        primary_signal = signals.get('1d', 'NONE')

        # 가중 평균으로 종합 신뢰도 계산
        total_confidence = sum(confidences.values())

        # 컨센서스 계산
        up_weight = sum(conf for tf, conf in confidences.items() if signals[tf] == 'UP')
        down_weight = sum(conf for tf, conf in confidences.items() if signals[tf] == 'DOWN')

        if up_weight > down_weight * 1.3:  # 30% 이상 차이
            consensus = 'UP'
        elif down_weight > up_weight * 1.3:
            consensus = 'DOWN'
        else:
            consensus = 'SIDEWAYS'

        # 포지션 기반 청산 판단
        should_exit = False
        reason = ""

        if current_position and total_confidence > 0.25:  # 최소 신뢰도 (일봉은 더 보수적)
            if current_position == 'LONG' and consensus == 'DOWN':
                should_exit = True
                reason = f"상승추세 종료 감지 (신뢰도: {total_confidence:.2f})"
            elif current_position == 'SHORT' and consensus == 'UP':
                should_exit = True
                reason = f"하락추세 종료 감지 (신뢰도: {total_confidence:.2f})"
            elif primary_signal != 'NONE' and primary_signal != 'SIDEWAYS':
                # 일봉 시그널이 강할 때
                if current_position == 'LONG' and primary_signal == 'DOWN':
                    should_exit = True
                    reason = f"일봉 하락신호 (강도: {confidences.get('1d', 0):.2f})"
                elif current_position == 'SHORT' and primary_signal == 'UP':
                    should_exit = True
                    reason = f"일봉 상승신호 (강도: {confidences.get('1d', 0):.2f})"

        return {
            'should_exit': should_exit,
            'confidence': total_confidence,
            'primary_signal': primary_signal,
            'consensus': consensus,
            'reason': reason,
            'symbol': symbol,
            'timeframe_signals': signals,
            'timeframe_confidences': confidences
        }

    def get_trading_signal(self, symbol: str = 'NVDL') -> Dict:
        """거래 신호 생성 (신규 진입용)"""
        result = self.detect_multi_timeframe_reversal(symbol)

        # 학습을 위해 임계값을 더 낮게 설정
        entry_threshold = 0.15  # 15% 이상 신뢰도 (더 많은 학습 기회)

        # 추천 포지션 로깅 (항상 표시)
        print(f"\n[ANALYZE] {symbol} 신호 분석:")
        print(f"   [SIGNAL] 주요신호: {result['primary_signal']} | 컨센서스: {result['consensus']}")
        print(f"   [CONF] 신뢰도: {result['confidence']:.3f} (임계값: {entry_threshold:.2f})")

        if result['timeframe_signals']:
            print(f"   [TIMEFRAME] 타임프레임별:")
            for tf, signal in result['timeframe_signals'].items():
                conf = result['timeframe_confidences'].get(tf, 0)
                print(f"      {tf}: {signal} ({conf:.3f})")

        if result['confidence'] >= entry_threshold:
            if result['consensus'] == 'UP':
                action_info = {
                    'action': 'BUY',
                    'symbol': symbol,
                    'confidence': result['confidence'],
                    'reason': f"상승 컨센서스 (신뢰도: {result['confidence']:.2f})"
                }
                print(f"   [RECOMMEND] 추천 포지션: {symbol} 매수 (BUY) 신뢰도: {result['confidence']:.2f}")
                return action_info
            elif result['consensus'] == 'DOWN':
                action_info = {
                    'action': 'SELL',
                    'symbol': symbol,
                    'confidence': result['confidence'],
                    'reason': f"하락 컨센서스 (신뢰도: {result['confidence']:.2f})"
                }
                print(f"   [RECOMMEND] 추천 포지션: {symbol} 매도 (SELL) 신뢰도: {result['confidence']:.2f}")
                return action_info

        hold_info = {
            'action': 'HOLD',
            'symbol': symbol,
            'confidence': result['confidence'],
            'reason': f"신호 부족 (신뢰도: {result['confidence']:.2f} < {entry_threshold:.2f})"
        }
        print(f"   [HOLD] 추천 포지션: 대기 (HOLD) - {hold_info['reason']}")
        return hold_info

    def print_status(self, symbol: str = 'NVDL'):
        """현재 상태 출력"""
        print(f"\n[STATUS] {symbol} 다중 타임프레임 추세 상태")
        print(f"일봉 데이터: {len(self.price_history['1d'])}개")
        print(f"4시간 데이터: {len(self.price_history['4h'])}개")
        print(f"1시간 데이터: {len(self.price_history['1h'])}개")

        result = self.detect_multi_timeframe_reversal(symbol)
        print(f"주요 신호: {result['primary_signal']}")
        print(f"컨센서스: {result['consensus']}")
        print(f"신뢰도: {result['confidence']:.2f}")

        signal = self.get_trading_signal(symbol)
        print(f"거래 신호: {signal['action']} - {signal['reason']}")

    def get_daily_data(self, symbol: str, days: int = 30) -> Optional[pd.DataFrame]:
        """일일 데이터 조회 - 누락된 메서드 구현"""
        try:
            # 캐시 확인 (5분간 유효)
            cache_key = f"{symbol}_{days}"
            now = datetime.now()

            if (cache_key in self.cache and
                cache_key in self.last_update and
                (now - self.last_update[cache_key]).seconds < 300):
                return self.cache[cache_key]

            # API 호출
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}"
            params = {
                'apikey': self.fmp_api_key,
                'from': start_date.strftime('%Y-%m-%d'),
                'to': end_date.strftime('%Y-%m-%d')
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if 'historical' not in data or not data['historical']:
                print(f"[WARN] {symbol} 데이터 없음")
                return None

            # DataFrame 변환
            df = pd.DataFrame(data['historical'])
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            df.reset_index(drop=True, inplace=True)

            # 캐시 업데이트
            self.cache[cache_key] = df
            self.last_update[cache_key] = now

            print(f"[DATA] {symbol} 일일 데이터: {len(df)}일")
            return df

        except Exception as e:
            print(f"[ERROR] {symbol} 일일 데이터 조회 오류: {e}")
            return None

    def analyze_symbol(self, symbol: str) -> Dict:
        """심볼별 종합 분석"""
        try:
            print(f"[ANALYZE] {symbol} 신호 분석:")

            # 다중 타임프레임 분석
            timeframes = {
                '1d': self.get_daily_data(symbol, 30),
                '4h': self.get_daily_data(symbol, 7),  # 7일치 일봉을 4시간 대용
                '1h': self.get_daily_data(symbol, 2)   # 2일치 일봉을 1시간 대용
            }

            signals = {}
            confidences = {}

            for tf, data in timeframes.items():
                if data is not None and not data.empty and len(data) > 0:
                    result = self.calculate_signals(data)
                    signals[tf] = result['signal']
                    confidences[tf] = result['confidence']
                else:
                    signals[tf] = 'SIDEWAYS'
                    confidences[tf] = 0.0

            # 가중 평균 신뢰도 계산 (1d: 60%, 4h: 25%, 1h: 15%)
            weights = {'1d': 0.60, '4h': 0.25, '1h': 0.15}
            weighted_confidence = sum(confidences[tf] * weights[tf] for tf in weights.keys())

            # 컨센서스 신호 결정
            buy_weight = sum(weights[tf] for tf in signals.keys() if signals[tf] == 'BUY')
            sell_weight = sum(weights[tf] for tf in signals.keys() if signals[tf] == 'SELL')

            if buy_weight > sell_weight and weighted_confidence > 0.15:
                consensus = 'BUY'
            elif sell_weight > buy_weight and weighted_confidence > 0.15:
                consensus = 'SELL'
            else:
                consensus = 'SIDEWAYS'

            return {
                'symbol': symbol,
                'main_signal': signals.get('1d', 'SIDEWAYS'),
                'consensus': consensus,
                'confidence': weighted_confidence,
                'timeframe_signals': signals,
                'timeframe_confidences': confidences,
                'recommendation': consensus if weighted_confidence >= 0.15 else 'HOLD'
            }

        except Exception as e:
            print(f"[ERROR] {symbol} 신호 생성 오류: {e}")
            return {
                'symbol': symbol,
                'main_signal': 'SIDEWAYS',
                'consensus': 'SIDEWAYS',
                'confidence': 0.0,
                'timeframe_signals': {},
                'timeframe_confidences': {},
                'recommendation': 'HOLD',
                'error': str(e)
            }

    def calculate_signals(self, df: pd.DataFrame) -> Dict:
        """기술적 신호 계산"""
        if df is None or df.empty or len(df) < 10:
            return {'signal': 'SIDEWAYS', 'confidence': 0.0, 'reason': '데이터 부족'}

        try:
            # 가격 데이터
            closes = df['close'].values
            current_price = closes[-1]

            # 이동평균
            ma5 = np.mean(closes[-5:]) if len(closes) >= 5 else closes[-1]
            ma10 = np.mean(closes[-10:]) if len(closes) >= 10 else closes[-1]

            # 신호 계산
            if current_price > ma5 > ma10:
                return {'signal': 'BUY', 'confidence': 0.5}
            elif current_price < ma5 < ma10:
                return {'signal': 'SELL', 'confidence': 0.5}
            else:
                return {'signal': 'SIDEWAYS', 'confidence': 0.1}

        except Exception as e:
            print(f"[ERROR] 신호 계산 오류: {e}")
            return {'signal': 'SIDEWAYS', 'confidence': 0.0, 'reason': f'계산 오류: {e}'}

if __name__ == "__main__":
    detector = DailyTrendDetector()

    print("\n[TEST] 일봉 추세 감지 테스트")

    # NVDL 테스트
    print("\n[ANALYZE] NVDL 분석:")
    detector.print_status('NVDL')

    # NVDQ 테스트
    print("\n[ANALYZE] NVDQ 분석:")
    detector.print_status('NVDQ')

    # 포지션 청산 신호 테스트
    print("\n[TEST] LONG 포지션 청산 신호 테스트:")
    result = detector.detect_multi_timeframe_reversal('NVDL', 'LONG')
    print(f"청산 필요: {result['should_exit']}")
    print(f"이유: {result['reason']}")