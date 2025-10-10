#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVDL/NVDQ 개선된 데이터 수집 시스템
- 네트워크 안정성 강화
- 자동 재시도 로직
- 백업 엔드포인트 지원
- 상세한 에러 핸들링
"""

import json
import time
import pickle
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# 개선된 API 핸들러 임포트
from improved_api_handler import ImprovedAPIHandler

class NVDLNVDQDataCollectorImproved:
    def __init__(self, fmp_api_key: str):
        """
        개선된 NVDL/NVDQ 데이터 수집기 초기화

        Args:
            fmp_api_key: Financial Modeling Prep API 키
        """
        print("=== NVDL/NVDQ 개선된 데이터 수집 시스템 ===")
        print("네트워크 안정성 강화 + 자동 재시도")

        # API 설정
        self.fmp_api_key = fmp_api_key
        self.fmp_base_url = "https://financialmodelingprep.com/api/v3"

        # 개선된 API 핸들러
        self.api_handler = ImprovedAPIHandler(fmp_api_key)

        # 거래 대상 ETF
        self.symbols = {
            'NVDL': '3x 레버리지 NVIDIA ETF (Long)',
            'NVDQ': '2x 역 레버리지 NASDAQ ETF (Short)'
        }

        # 데이터 저장소
        self.historical_data = {}
        self.realtime_data = {}
        self.features_data = {}

        # API 호출 제한 관리
        self.api_call_times = []
        self.calls_per_minute = 250  # FMP 제한
        self.delay_between_calls = 0.3

        # 캐시 파일 경로
        self.cache_file = "nvdl_nvdq_data_cache_improved.pkl"
        self.features_file = "nvdl_nvdq_features_cache_improved.pkl"

        # 네트워크 품질 추적
        self.network_stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'retry_counts': 0,
            'last_success_time': None,
            'consecutive_failures': 0
        }

        print(f"수집 대상: {list(self.symbols.keys())}")
        print(f"API 제한: {self.calls_per_minute}회/분")

    def rate_limit_check(self):
        """API 호출 제한 확인 및 대기"""
        current_time = time.time()

        # 1분 전 호출 기록 정리
        self.api_call_times = [t for t in self.api_call_times if current_time - t < 60]

        # 제한 확인
        if len(self.api_call_times) >= self.calls_per_minute:
            sleep_time = 60 - (current_time - self.api_call_times[0])
            if sleep_time > 0:
                print(f"API 제한 대기: {sleep_time:.1f}초")
                time.sleep(sleep_time)

        # 호출 기록 및 딜레이
        self.api_call_times.append(current_time)
        time.sleep(self.delay_between_calls)

    def fetch_realtime_data(self, symbol: str) -> Optional[Dict]:
        """
        개선된 실시간 가격 데이터 수집
        """
        self.rate_limit_check()
        self.network_stats['total_calls'] += 1

        try:
            print(f"[{symbol}] 실시간 가격 조회 중...")

            # 개선된 API 핸들러 사용
            data = self.api_handler.robust_api_call(
                f"{self.fmp_base_url}/quote/{symbol}",
                endpoint_type='quote'
            )

            if data:
                self.network_stats['successful_calls'] += 1
                self.network_stats['last_success_time'] = datetime.now()
                self.network_stats['consecutive_failures'] = 0

                print(f"[{symbol}] 실시간 데이터 수집 성공")
                return data
            else:
                self._handle_api_failure(symbol)
                return None

        except Exception as e:
            print(f"[{symbol}] 실시간 데이터 수집 중 오류: {e}")
            self._handle_api_failure(symbol)
            return None

    def _handle_api_failure(self, symbol: str):
        """API 실패 처리"""
        self.network_stats['failed_calls'] += 1
        self.network_stats['consecutive_failures'] += 1

        # 연속 실패가 많으면 더 긴 대기 시간
        if self.network_stats['consecutive_failures'] >= 3:
            wait_time = min(self.network_stats['consecutive_failures'] * 5, 30)
            print(f"연속 실패 {self.network_stats['consecutive_failures']}회, {wait_time}초 대기...")
            time.sleep(wait_time)

    def get_latest_features(self, symbol: str) -> Optional[np.ndarray]:
        """
        최신 특성 데이터 가져오기 (캐시 우선)
        """
        try:
            # 캐시된 특성 데이터가 있으면 사용
            if symbol in self.features_data:
                features = self.features_data[symbol]
                if len(features) > 0:
                    return np.array(features[-1])  # 최신 특성

            # 캐시된 데이터가 없으면 실시간 데이터로 간단한 특성 생성
            realtime_data = self.fetch_realtime_data(symbol)
            if realtime_data:
                return self._generate_basic_features(symbol, realtime_data)

            return None

        except Exception as e:
            print(f"[{symbol}] 특성 데이터 조회 오류: {e}")
            return None

    def _generate_basic_features(self, symbol: str, realtime_data: Dict) -> np.ndarray:
        """실시간 데이터로부터 기본 특성 생성"""
        try:
            price = float(realtime_data.get('price', 50))
            change_pct = float(realtime_data.get('changesPercentage', 0)) / 100
            volume = float(realtime_data.get('volume', 1000000))

            # 기본 특성 15개 생성 (모델 호환성)
            features = [
                1.0 + change_pct * 0.1,        # SMA 5 ratio (추정)
                1.0 + change_pct * 0.08,       # SMA 10 ratio
                1.0 + change_pct * 0.05,       # SMA 20 ratio
                1.0 + change_pct * 0.02,       # SMA 50 ratio
                abs(change_pct) * 2,           # Volatility (추정)
                change_pct,                    # Momentum 5
                change_pct * 0.8,              # Momentum 10
                change_pct * 0.6,              # Momentum 20
                min(max(volume / 1000000, 0.5), 3.0),  # Volume ratio
                max(min((price % 10) / 10, 1.0), 0.0), # RSI 추정
                0.5,                           # Bollinger position
                change_pct * 0.5,              # MACD 추정
                0.5,                           # Price position 20
                abs(change_pct) * 1.5,         # Realized volatility
                1.0 if symbol == 'NVDL' else 0.0  # Symbol indicator
            ]

            return np.array(features)

        except Exception as e:
            print(f"기본 특성 생성 오류: {e}")
            # 기본값 반환
            basic_features = [1.0] * 14 + [1.0 if symbol == 'NVDL' else 0.0]
            return np.array(basic_features)

    def fetch_historical_data_robust(self, symbol: str, from_date: str = None,
                                   to_date: str = None, interval: str = '1hour') -> Optional[List[Dict]]:
        """
        강화된 역사적 데이터 수집
        """
        self.rate_limit_check()

        try:
            url = f"{self.fmp_base_url}/historical-chart/{interval}/{symbol}"
            params = {}

            if from_date:
                params['from'] = from_date
            if to_date:
                params['to'] = to_date

            print(f"[{symbol}] 역사적 데이터 수집 중... (간격: {interval})")

            data = self.api_handler.robust_api_call(url, params)

            if isinstance(data, list) and len(data) > 0:
                print(f"[{symbol}] {len(data)}개 역사적 데이터 수집 완료")
                return data
            else:
                print(f"[{symbol}] 역사적 데이터 없음")
                return None

        except Exception as e:
            print(f"[{symbol}] 역사적 데이터 수집 오류: {e}")
            return None

    def collect_all_data_improved(self):
        """개선된 전체 데이터 수집"""
        print("\n=== 개선된 전체 데이터 수집 시작 ===")

        for symbol in self.symbols:
            print(f"\n[{symbol}] 데이터 수집 시작...")

            # 1. 실시간 데이터
            realtime_data = self.fetch_realtime_data(symbol)
            if realtime_data:
                self.realtime_data[symbol] = realtime_data

            # 2. 간단한 역사적 데이터 (최근 30일)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)

            historical_data = self.fetch_historical_data_robust(
                symbol,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d'),
                '1hour'
            )

            if historical_data:
                self.historical_data[symbol] = historical_data

            print(f"[{symbol}] 데이터 수집 완료")

        # 수집 통계 출력
        self.print_network_stats()

    def print_network_stats(self):
        """네트워크 통계 출력"""
        stats = self.network_stats
        success_rate = (stats['successful_calls'] / max(stats['total_calls'], 1)) * 100

        print(f"\n=== 네트워크 통계 ===")
        print(f"총 API 호출: {stats['total_calls']}")
        print(f"성공: {stats['successful_calls']}")
        print(f"실패: {stats['failed_calls']}")
        print(f"성공률: {success_rate:.1f}%")
        print(f"연속 실패: {stats['consecutive_failures']}")

        if stats['last_success_time']:
            last_success = (datetime.now() - stats['last_success_time']).total_seconds()
            print(f"마지막 성공: {last_success:.0f}초 전")

    def load_data(self) -> bool:
        """캐시된 데이터 로드"""
        try:
            with open(self.cache_file, 'rb') as f:
                cached_data = pickle.load(f)
                self.historical_data = cached_data.get('historical_data', {})
                self.realtime_data = cached_data.get('realtime_data', {})

                print(f"캐시된 데이터 로드 완료")
                return True
        except FileNotFoundError:
            print("캐시 파일이 없습니다. 새로 수집합니다.")
            return False
        except Exception as e:
            print(f"캐시 로드 오류: {e}")
            return False

    def save_data(self):
        """데이터 저장"""
        try:
            cache_data = {
                'historical_data': self.historical_data,
                'realtime_data': self.realtime_data,
                'features_data': self.features_data,
                'network_stats': self.network_stats,
                'last_update': datetime.now().isoformat()
            }

            with open(self.cache_file, 'wb') as f:
                pickle.dump(cache_data, f)

            print("데이터 캐시 저장 완료")

        except Exception as e:
            print(f"데이터 저장 오류: {e}")

    def calculate_all_features(self):
        """모든 심볼에 대해 특성 계산"""
        print("\n=== 특성 계산 시작 ===")

        for symbol in self.symbols:
            if symbol in self.historical_data:
                features = self.calculate_basic_features(self.historical_data[symbol])
                if features is not None:
                    self.features_data[symbol] = features
                    print(f"[{symbol}] 특성 계산 완료: {len(features)}개")

    def calculate_basic_features(self, price_data: List[Dict]) -> Optional[List[List[float]]]:
        """기본 특성 계산"""
        try:
            if not price_data or len(price_data) < 20:
                return None

            df = pd.DataFrame(price_data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)

            features_list = []

            for i in range(20, len(df)):  # 최소 20개 데이터 필요
                current_data = df.iloc[:i+1]

                # 기본 특성들 계산
                close_prices = current_data['close'].values
                volumes = current_data['volume'].values

                # 이동평균 비율
                sma_5 = close_prices[-5:].mean()
                sma_10 = close_prices[-10:].mean() if len(close_prices) >= 10 else sma_5
                sma_20 = close_prices[-20:].mean()
                current_price = close_prices[-1]

                features = [
                    current_price / sma_5,
                    current_price / sma_10,
                    current_price / sma_20,
                    current_price / sma_20,  # SMA 50 대신 20 사용
                    np.std(close_prices[-5:]) / current_price,  # 변동성
                    (close_prices[-1] / close_prices[-2] - 1) if len(close_prices) >= 2 else 0,  # Momentum
                    (close_prices[-1] / close_prices[-5] - 1) if len(close_prices) >= 5 else 0,
                    (close_prices[-1] / close_prices[-10] - 1) if len(close_prices) >= 10 else 0,
                    volumes[-1] / volumes[-5:].mean() if len(volumes) >= 5 else 1.0,  # Volume ratio
                    0.5,  # RSI placeholder
                    0.5,  # Bollinger placeholder
                    0.0,  # MACD placeholder
                    0.5,  # Price position placeholder
                    np.std(close_prices[-5:]) / current_price,  # Realized volatility
                    1.0   # Symbol placeholder
                ]

                features_list.append(features)

            return features_list

        except Exception as e:
            print(f"특성 계산 오류: {e}")
            return None

def test_improved_collector():
    """개선된 데이터 수집기 테스트"""
    api_key = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"
    collector = NVDLNVDQDataCollectorImproved(api_key)

    print("=== 개선된 데이터 수집기 테스트 ===")

    # 실시간 데이터 테스트
    for symbol in ['NVDL', 'NVDQ']:
        realtime = collector.fetch_realtime_data(symbol)
        if realtime:
            print(f"{symbol} 실시간: ${realtime.get('price', 'N/A')}")

        features = collector.get_latest_features(symbol)
        if features is not None:
            print(f"{symbol} 특성: {len(features)}개")

    # 네트워크 통계
    collector.print_network_stats()

if __name__ == "__main__":
    test_improved_collector()