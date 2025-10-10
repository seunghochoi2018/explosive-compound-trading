#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVDL/NVDQ 데이터 수집 시스템
- Financial Modeling Prep API 사용
- 전체 역사적 데이터부터 최신 데이터까지 수집
- 실시간 데이터 업데이트
- 패턴 분석을 위한 특성 계산
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

class NVDLNVDQDataCollector:
    def __init__(self, fmp_api_key: str):
        """
        NVDL/NVDQ 데이터 수집기 초기화

        Args:
            fmp_api_key: Financial Modeling Prep API 키
        """
        print("=== NVDL/NVDQ 데이터 수집 시스템 ===")
        print("FMP API를 활용한 전체 역사적 데이터 수집")

        # API 설정
        self.fmp_api_key = fmp_api_key
        self.fmp_base_url = "https://financialmodelingprep.com/api/v3"

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
        self.cache_file = "nvdl_nvdq_data_cache.pkl"
        self.features_file = "nvdl_nvdq_features_cache.pkl"

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

    def fetch_historical_data(self, symbol: str, from_date: str = None, to_date: str = None,
                             interval: str = '1hour') -> Optional[List[Dict]]:
        """
        특정 심볼의 역사적 데이터 수집

        Args:
            symbol: 주식 심볼 (NVDL, NVDQ)
            from_date: 시작 날짜 (YYYY-MM-DD)
            to_date: 종료 날짜 (YYYY-MM-DD)
            interval: 데이터 간격 (1min, 5min, 15min, 30min, 1hour, 4hour)

        Returns:
            가격 데이터 리스트
        """
        self.rate_limit_check()

        try:
            # URL 구성
            url = f"{self.fmp_base_url}/historical-chart/{interval}/{symbol}"
            params = {'apikey': self.fmp_api_key}

            if from_date:
                params['from'] = from_date
            if to_date:
                params['to'] = to_date

            print(f"[{symbol}] 데이터 수집 중... (간격: {interval})")

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            if isinstance(data, list) and len(data) > 0:
                print(f"[{symbol}] {len(data)}개 데이터 수집 완료")
                return data
            else:
                print(f"[{symbol}] 데이터 없음 또는 오류: {data}")
                return None

        except Exception as e:
            print(f"[{symbol}] 데이터 수집 오류: {e}")
            return None

    def fetch_daily_data(self, symbol: str, years_back: int = 5) -> Optional[List[Dict]]:
        """
        일일 데이터 수집 (더 긴 기간)

        Args:
            symbol: 주식 심볼
            years_back: 몇 년 전까지 데이터를 가져올지

        Returns:
            일일 가격 데이터 리스트
        """
        self.rate_limit_check()

        try:
            # 날짜 계산
            end_date = datetime.now()
            start_date = end_date - timedelta(days=years_back * 365)

            url = f"{self.fmp_base_url}/historical-price-full/{symbol}"
            params = {
                'apikey': self.fmp_api_key,
                'from': start_date.strftime('%Y-%m-%d'),
                'to': end_date.strftime('%Y-%m-%d')
            }

            print(f"[{symbol}] 일일 데이터 수집 중... ({years_back}년)")

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            if 'historical' in data and len(data['historical']) > 0:
                historical = data['historical']
                print(f"[{symbol}] {len(historical)}개 일일 데이터 수집 완료")
                return historical
            else:
                print(f"[{symbol}] 일일 데이터 없음: {data}")
                return None

        except Exception as e:
            print(f"[{symbol}] 일일 데이터 수집 오류: {e}")
            return None

    def fetch_realtime_data(self, symbol: str) -> Optional[Dict]:
        """
        실시간 가격 데이터 수집

        Args:
            symbol: 주식 심볼

        Returns:
            실시간 가격 정보
        """
        self.rate_limit_check()

        try:
            url = f"{self.fmp_base_url}/quote/{symbol}"
            params = {'apikey': self.fmp_api_key}

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if isinstance(data, list) and len(data) > 0:
                return data[0]
            else:
                print(f"[{symbol}] 실시간 데이터 오류: {data}")
                return None

        except Exception as e:
            print(f"[{symbol}] 실시간 데이터 오류: {e}")
            return None

    def calculate_features(self, price_data: List[Dict], window_sizes: List[int] = [5, 10, 20]) -> pd.DataFrame:
        """
        가격 데이터로부터 기술적 특성 계산

        Args:
            price_data: 가격 데이터 리스트
            window_sizes: 이동평균 윈도우 크기들

        Returns:
            특성이 계산된 DataFrame
        """
        # DataFrame 변환
        df = pd.DataFrame(price_data)

        # 날짜 정렬 (오래된 것부터)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)

        # 기본 특성
        df['high_low_ratio'] = df['high'] / df['low']
        df['close_open_ratio'] = df['close'] / df['open']
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']

        # 이동평균들
        for window in window_sizes:
            df[f'sma_{window}'] = df['close'].rolling(window=window).mean()
            df[f'close_sma_{window}_ratio'] = df['close'] / df[f'sma_{window}']

        # 변동성 (표준편차)
        for window in window_sizes:
            df[f'volatility_{window}'] = df['close'].rolling(window=window).std()
            df[f'volatility_{window}_norm'] = df[f'volatility_{window}'] / df['close']

        # 모멘텀
        for window in window_sizes:
            df[f'momentum_{window}'] = df['close'] / df['close'].shift(window) - 1

        # RSI 계산
        def calculate_rsi(prices, window=14):
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi

        df['rsi_14'] = calculate_rsi(df['close'])

        # 볼린저 밴드
        bb_window = 20
        bb_std = 2
        df['bb_middle'] = df['close'].rolling(window=bb_window).mean()
        bb_std_val = df['close'].rolling(window=bb_window).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std_val * bb_std)
        df['bb_lower'] = df['bb_middle'] - (bb_std_val * bb_std)
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

        # 가격 위치 (최근 N일 범위에서)
        for window in [10, 20, 50]:
            rolling_max = df['high'].rolling(window=window).max()
            rolling_min = df['low'].rolling(window=window).min()
            df[f'price_position_{window}'] = (df['close'] - rolling_min) / (rolling_max - rolling_min)

        return df

    def collect_all_data(self):
        """모든 심볼의 전체 데이터 수집 - 5년치 이상 대량 수집"""
        print("\n=== 전체 데이터 수집 시작 (5년치 이상) ===")

        for symbol in self.symbols.keys():
            print(f"\n[{symbol}] 대량 데이터 수집 시작")

            # 1. 일일 데이터 (7년 - 최대한 많이)
            daily_data = self.fetch_daily_data(symbol, years_back=7)
            if daily_data:
                self.historical_data[f"{symbol}_daily"] = daily_data
                print(f"[{symbol}] 일일 데이터: {len(daily_data)}개 (7년치)")

            # 2. 시간별 데이터 (최근 1년)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)

            hourly_data = self.fetch_historical_data(
                symbol,
                from_date=start_date.strftime('%Y-%m-%d'),
                to_date=end_date.strftime('%Y-%m-%d'),
                interval='1hour'
            )
            if hourly_data:
                self.historical_data[f"{symbol}_1hour"] = hourly_data
                print(f"[{symbol}] 시간별 데이터: {len(hourly_data)}개 (1년치)")

            # 3. 5분 데이터 (최근 3개월)
            start_date = end_date - timedelta(days=90)

            minute_data = self.fetch_historical_data(
                symbol,
                from_date=start_date.strftime('%Y-%m-%d'),
                to_date=end_date.strftime('%Y-%m-%d'),
                interval='5min'
            )
            if minute_data:
                self.historical_data[f"{symbol}_5min"] = minute_data
                print(f"[{symbol}] 5분 데이터: {len(minute_data)}개 (3개월치)")

            # 4. 추가 시간별 데이터 (2년치 - 더 많은 학습 데이터)
            start_date = end_date - timedelta(days=730)
            end_date_2y = end_date - timedelta(days=365)

            hourly_data_2y = self.fetch_historical_data(
                symbol,
                from_date=start_date.strftime('%Y-%m-%d'),
                to_date=end_date_2y.strftime('%Y-%m-%d'),
                interval='1hour'
            )
            if hourly_data_2y:
                # 기존 데이터와 합치기
                if f"{symbol}_1hour" in self.historical_data:
                    self.historical_data[f"{symbol}_1hour"].extend(hourly_data_2y)
                else:
                    self.historical_data[f"{symbol}_1hour"] = hourly_data_2y
                print(f"[{symbol}] 추가 시간별 데이터: {len(hourly_data_2y)}개 (2년치)")

            # 5. 실시간 데이터
            realtime = self.fetch_realtime_data(symbol)
            if realtime:
                self.realtime_data[symbol] = realtime
                print(f"[{symbol}] 실시간 가격: ${realtime.get('price', 'N/A')}")

            time.sleep(0.5)  # 심볼 간 딜레이 단축

    def calculate_all_features(self):
        """모든 데이터에 대해 특성 계산"""
        print("\n=== 특성 계산 시작 ===")

        for data_key, data in self.historical_data.items():
            if data and len(data) > 50:  # 최소 50개 데이터 포인트 필요
                print(f"[{data_key}] 특성 계산 중...")
                features_df = self.calculate_features(data)
                self.features_data[data_key] = features_df
                print(f"[{data_key}] 특성 계산 완료: {len(features_df)} rows, {len(features_df.columns)} features")

    def save_data(self):
        """수집된 데이터를 파일로 저장"""
        try:
            # 원본 데이터 저장
            with open(self.cache_file, 'wb') as f:
                pickle.dump({
                    'historical_data': self.historical_data,
                    'realtime_data': self.realtime_data,
                    'collected_at': datetime.now().isoformat(),
                    'symbols': self.symbols
                }, f)
            print(f"데이터 저장 완료: {self.cache_file}")

            # 특성 데이터 저장
            with open(self.features_file, 'wb') as f:
                pickle.dump({
                    'features_data': self.features_data,
                    'calculated_at': datetime.now().isoformat()
                }, f)
            print(f"특성 데이터 저장 완료: {self.features_file}")

        except Exception as e:
            print(f"데이터 저장 오류: {e}")

    def load_data(self) -> bool:
        """저장된 데이터 로드"""
        try:
            # 원본 데이터 로드
            with open(self.cache_file, 'rb') as f:
                cache_data = pickle.load(f)
                self.historical_data = cache_data.get('historical_data', {})
                self.realtime_data = cache_data.get('realtime_data', {})
                collected_at = cache_data.get('collected_at', 'Unknown')
                print(f"데이터 로드 완료: {self.cache_file} (수집 시간: {collected_at})")

            # 특성 데이터 로드
            with open(self.features_file, 'rb') as f:
                features_cache = pickle.load(f)
                self.features_data = features_cache.get('features_data', {})
                calculated_at = features_cache.get('calculated_at', 'Unknown')
                print(f"특성 데이터 로드 완료: {self.features_file} (계산 시간: {calculated_at})")

            return True

        except FileNotFoundError:
            print("저장된 데이터 파일이 없습니다. 새로 수집합니다.")
            return False
        except Exception as e:
            print(f"데이터 로드 오류: {e}")
            return False

    def print_summary(self):
        """수집된 데이터 요약 출력"""
        print("\n=== 데이터 수집 요약 ===")

        print(f"수집 대상: {list(self.symbols.keys())}")
        print(f"수집 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        print("\n[역사적 데이터]")
        for key, data in self.historical_data.items():
            if data:
                print(f"  {key}: {len(data):,}개 데이터 포인트")

        print("\n[실시간 데이터]")
        for symbol, data in self.realtime_data.items():
            if data:
                price = data.get('price', 'N/A')
                change = data.get('changesPercentage', 'N/A')
                print(f"  {symbol}: ${price} ({change}%)")

        print("\n[특성 데이터]")
        for key, df in self.features_data.items():
            if df is not None and not df.empty:
                valid_rows = df.dropna().shape[0]
                print(f"  {key}: {df.shape[0]} rows, {df.shape[1]} features (유효: {valid_rows})")

    def get_latest_features(self, symbol: str, interval: str = '1hour') -> Optional[np.ndarray]:
        """최신 특성 벡터 반환 (거래 신호 생성용)"""
        data_key = f"{symbol}_{interval}"

        if data_key in self.features_data:
            df = self.features_data[data_key]
            if df is not None and not df.empty:
                # 최신 데이터의 특성 벡터 (NaN 제외)
                latest_row = df.iloc[-1]

                # 기본 특성들만 선택 (15개)
                feature_columns = [
                    'close_sma_5_ratio', 'close_sma_10_ratio', 'close_sma_20_ratio',
                    'volatility_5_norm', 'volatility_20_norm',
                    'momentum_5', 'momentum_10', 'momentum_20',
                    'volume_ratio', 'rsi_14', 'bb_position',
                    'price_position_10', 'price_position_20',
                    'high_low_ratio', 'close_open_ratio'
                ]

                features = []
                for col in feature_columns:
                    if col in latest_row and not pd.isna(latest_row[col]):
                        features.append(latest_row[col])
                    else:
                        features.append(0.0)  # 기본값

                return np.array(features)

        return None

def main():
    """메인 실행 함수"""
    # FMP API 키 설정 (실제 키로 교체 필요)
    FMP_API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"  # 여기에 실제 API 키 입력

    if not FMP_API_KEY or FMP_API_KEY == "YOUR_API_KEY_HERE":
        print("ERROR: FMP API 키를 설정해주세요!")
        print("https://financialmodelingprep.com/developer/docs 에서 API 키를 발급받으세요.")
        return

    # 데이터 수집기 생성
    collector = NVDLNVDQDataCollector(FMP_API_KEY)

    # 기존 데이터 로드 시도
    if not collector.load_data():
        # 새로운 데이터 수집
        collector.collect_all_data()
        collector.calculate_all_features()
        collector.save_data()

    # 요약 출력
    collector.print_summary()

    # 최신 특성 테스트
    print("\n=== 최신 특성 테스트 ===")
    for symbol in ['NVDL', 'NVDQ']:
        features = collector.get_latest_features(symbol)
        if features is not None:
            print(f"{symbol} 최신 특성: {len(features)}개, 평균: {features.mean():.4f}")
        else:
            print(f"{symbol} 특성 데이터 없음")

if __name__ == "__main__":
    main()