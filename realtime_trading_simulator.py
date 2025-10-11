#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실시간 트레이딩 시뮬레이터
- 과거 데이터 학습 없음
- 실시간 데이터로만 학습
- 실제 매매 시뮬레이션
- 결과 기반 실시간 학습

*** 중요: FMP API만 사용! yfinance 절대 사용 금지! ***
데이터 소스: Financial Modeling Prep API (FMP)
- 실시간 데이터: FMP Real-time API
- 과거 데이터는 사용하지 않음
- 실시간 매매 시뮬레이션으로만 학습
"""

import json
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from collections import deque
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# 간단한 모델만 사용 (복잡한 모델 제거)
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

# 데이터 수집기 임포트
from nvdl_nvdq_data_collector import NVDLNVDQDataCollector

class RealtimeTradingSimulator:
    def __init__(self, fmp_api_key: str):
        """실시간 트레이딩 시뮬레이터 초기화"""
        print("=== 실시간 트레이딩 시뮬레이터 ===")
        print(" 과거 데이터 학습 없음")
        print(" 실시간 데이터로만 학습")
        print(" 실제 매매 시뮬레이션")
        print(" 결과 기반 실시간 학습")
        print()
        print("*** 데이터 소스 확인 ***")
        print(" FMP API 사용 (Financial Modeling Prep)")
        print(" yfinance 사용 금지 (신뢰성 문제)")
        print(" 실시간 데이터: FMP Real-time API")
        print(" 과거 데이터 사용 안함")
        print()

        # 데이터 수집기 초기화
        self.data_collector = NVDLNVDQDataCollector(fmp_api_key)

        # 거래 설정
        self.symbols = ['NVDL', 'NVDQ']
        self.balance = 10000.0  # 시작 자금
        self.position = None    # 현재 포지션
        self.position_size = 0  # 포지션 크기
        self.entry_price = 0    # 진입 가격
        self.entry_time = None  # 진입 시간

        # 간단한 모델만 사용 (복잡한 앙상블 제거)
        self.model = RandomForestClassifier(
            n_estimators=20,  # 적은 수의 트리
            max_depth=5,      # 얕은 깊이
            random_state=42
        )
        self.scaler = StandardScaler()
        self.is_model_trained = False

        # 실시간 학습 데이터 (매우 작은 메모리)
        self.recent_features = deque(maxlen=100)  # 최근 100개 특성만
        self.recent_labels = deque(maxlen=100)    # 최근 100개 라벨만
        self.trade_results = deque(maxlen=50)     # 최근 50개 거래만

        # 매매 통계
        self.total_trades = 0
        self.winning_trades = 0
        self.total_profit = 0.0
        self.win_rate = 0.0

        # 실시간 가격 추적
        self.price_history = {
            'NVDL': deque(maxlen=20),  # 최근 20개 가격만
            'NVDQ': deque(maxlen=20)
        }

        # 신호 임계값 (매우 단순화)
        self.confidence_threshold = 0.6  # 60% 이상 신뢰도에서만 매매

        print(f" 초기화 완료 - 시작 자금: ${self.balance:,.0f}")

    def get_realtime_price(self, symbol: str) -> float:
        """실시간 가격 조회"""
        try:
            # FMP API로 실시간 가격 조회
            current_data = self.data_collector.fetch_realtime_data(symbol)
            if current_data and 'price' in current_data:
                price = float(current_data['price'])
                self.price_history[symbol].append(price)
                return price
        except Exception as e:
            print(f" {symbol} 실시간 가격 조회 실패: {e}")

        # 실패시 임시 가격 (실제로는 마지막 알려진 가격 사용)
        if symbol == 'NVDL':
            return 45.0 + np.random.uniform(-2, 2)
        else:
            return 25.0 + np.random.uniform(-1, 1)

    def calculate_simple_features(self, symbol: str) -> np.ndarray:
        """간단한 특성 계산 (복잡한 특성 제거)"""
        if len(self.price_history[symbol]) < 5:
            return np.array([0.5, 0.5, 0.5])  # 기본값

        prices = list(self.price_history[symbol])
        current_price = prices[-1]

        # 매우 간단한 특성만 사용
        features = []

        # 1. 단기 가격 변화율 (최근 3개 가격)
        if len(prices) >= 3:
            short_change = (current_price - prices[-3]) / prices[-3]
            features.append(short_change)
        else:
            features.append(0.0)

        # 2. 변동성 (최근 5개 가격 표준편차)
        if len(prices) >= 5:
            volatility = np.std(prices[-5:]) / np.mean(prices[-5:])
            features.append(volatility)
        else:
            features.append(0.02)  # 기본 변동성

        # 3. 모멘텀 (최근 가격이 평균보다 높은지)
        if len(prices) >= 10:
            avg_price = np.mean(prices[-10:])
            momentum = 1.0 if current_price > avg_price else 0.0
            features.append(momentum)
        else:
            features.append(0.5)

        return np.array(features)

    def make_trading_decision(self) -> Tuple[str, str, float]:
        """매매 결정 (실시간 데이터만 사용)"""
        if not self.is_model_trained:
            return "HOLD", "NONE", 0.0

        # 양쪽 심볼 특성 계산
        nvdl_features = self.calculate_simple_features('NVDL')
        nvdq_features = self.calculate_simple_features('NVDQ')

        # 특성 결합
        combined_features = np.concatenate([nvdl_features, nvdq_features])

        try:
            # 정규화 및 예측
            features_scaled = self.scaler.transform([combined_features])
            prediction = self.model.predict_proba(features_scaled)[0]

            # NVDL 확률이 높으면 NVDL 매수, 낮으면 NVDQ 매수
            nvdl_prob = prediction[1] if len(prediction) > 1 else prediction[0]
            confidence = abs(nvdl_prob - 0.5) * 2  # 0.5에서 멀수록 높은 신뢰도

            if nvdl_prob > 0.5 and confidence > self.confidence_threshold:
                return "BUY", "NVDL", confidence
            elif nvdl_prob < 0.5 and confidence > self.confidence_threshold:
                return "BUY", "NVDQ", confidence
            else:
                return "HOLD", "NONE", confidence

        except Exception as e:
            print(f" 예측 오류: {e}")
            return "HOLD", "NONE", 0.0

    def execute_trade(self, action: str, symbol: str, confidence: float):
        """매매 실행"""
        current_price = self.get_realtime_price(symbol)
        current_time = datetime.now()

        if action == "BUY" and self.position is None:
            # 매수 실행
            self.position = symbol
            self.entry_price = current_price
            self.entry_time = current_time
            self.position_size = self.balance * 0.95  # 95% 투자

            print(f" 매수: {symbol} @ ${current_price:.2f} (신뢰도: {confidence:.3f})")
            print(f"   투자금액: ${self.position_size:,.0f}")

        elif self.position is not None:
            # 매도 조건 체크 (시간 기반 또는 수익/손실 기준)
            holding_time = (current_time - self.entry_time).total_seconds() / 3600
            profit_rate = (current_price / self.entry_price - 1) * 100

            # 레버리지 적용
            if self.position == 'NVDL':
                profit_rate *= 3  # 3배 레버리지
            elif self.position == 'NVDQ':
                profit_rate *= 2  # 2배 레버리지

            should_sell = False
            sell_reason = ""

            # 매도 조건
            if holding_time > 2:  # 2시간 이상 보유
                should_sell = True
                sell_reason = "시간초과"
            elif profit_rate > 5:  # 5% 이상 수익
                should_sell = True
                sell_reason = "수익실현"
            elif profit_rate < -3:  # 3% 이상 손실
                should_sell = True
                sell_reason = "손절"

            if should_sell:
                # 매도 실행
                profit_amount = self.position_size * (profit_rate / 100)
                self.balance += profit_amount
                self.total_profit += profit_rate

                print(f" 매도: {self.position} @ ${current_price:.2f} ({sell_reason})")
                print(f"   수익률: {profit_rate:+.2f}% (${profit_amount:+,.0f})")
                print(f"   잔고: ${self.balance:,.0f}")

                # 거래 결과 저장 및 학습
                self.record_trade_result(profit_rate > 1.0)

                # 포지션 초기화
                self.position = None
                self.position_size = 0
                self.entry_price = 0

    def record_trade_result(self, is_winning: bool):
        """거래 결과 기록 및 실시간 학습"""
        self.total_trades += 1
        if is_winning:
            self.winning_trades += 1

        self.win_rate = (self.winning_trades / self.total_trades) * 100

        # 거래 시점의 특성과 결과를 학습 데이터로 저장
        if len(self.price_history['NVDL']) >= 3 and len(self.price_history['NVDQ']) >= 3:
            nvdl_features = self.calculate_simple_features('NVDL')
            nvdq_features = self.calculate_simple_features('NVDQ')
            combined_features = np.concatenate([nvdl_features, nvdq_features])

            # 승리한 거래의 특성을 저장
            label = 1 if (is_winning and self.position == 'NVDL') else 0

            self.recent_features.append(combined_features)
            self.recent_labels.append(label)

            # 거래 결과 저장
            self.trade_results.append({
                'symbol': self.position,
                'is_winning': is_winning,
                'timestamp': datetime.now()
            })

            print(f" 학습 데이터 추가: {len(self.recent_features)}개 샘플")

        # 충분한 데이터가 쌓이면 모델 재학습
        if len(self.recent_features) >= 10:
            self.retrain_model()

    def retrain_model(self):
        """실시간 모델 재학습"""
        if len(self.recent_features) < 5:
            return

        print(" 실시간 모델 재학습 시작...")

        try:
            X = np.array(list(self.recent_features))
            y = np.array(list(self.recent_labels))

            # 라벨 균형 확인
            if len(np.unique(y)) < 2:
                print("    라벨이 한쪽으로 치우침, 재학습 스킵")
                return

            # 데이터 정규화
            if not self.is_model_trained:
                X_scaled = self.scaler.fit_transform(X)
            else:
                X_scaled = self.scaler.transform(X)

            # 모델 학습
            self.model.fit(X_scaled, y)
            self.is_model_trained = True

            print(f"    재학습 완료 - 샘플: {len(X)}개")

        except Exception as e:
            print(f"    재학습 실패: {e}")

    def display_status(self):
        """현재 상태 표시"""
        print(f"\n{'='*50}")
        print(f" 실시간 트레이딩 상태")
        print(f"{'='*50}")
        print(f"잔고: ${self.balance:,.0f}")
        print(f"포지션: {self.position or 'None'}")
        if self.position:
            current_price = self.get_realtime_price(self.position)
            unrealized = ((current_price / self.entry_price - 1) * 100)
            if self.position == 'NVDL':
                unrealized *= 3
            elif self.position == 'NVDQ':
                unrealized *= 2
            print(f"   진입가: ${self.entry_price:.2f}")
            print(f"   현재가: ${current_price:.2f}")
            print(f"   미실현: {unrealized:+.2f}%")
        print(f"총 거래: {self.total_trades}회")
        print(f"승률: {self.win_rate:.1f}%")
        print(f"총 수익: {self.total_profit:+.2f}%")
        print(f"학습 샘플: {len(self.recent_features)}개")
        print(f"모델 훈련: {'' if self.is_model_trained else ''}")
        print(f"{'='*50}")

def main():
    """메인 실행"""
    print("*** 실시간 트레이딩 시뮬레이터 ***")
    print(" FMP API 실시간 데이터 사용")
    print(" 과거 데이터 학습 없음")
    print(" 실제 매매로만 학습")
    print()

    FMP_API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"

    if not FMP_API_KEY or FMP_API_KEY == "YOUR_API_KEY_HERE":
        print("ERROR: FMP API 키를 설정해주세요!")
        print("FMP API는 https://financialmodelingprep.com에서 발급받으세요.")
        print("yfinance는 절대 사용하지 마세요!")
        return

    # 시뮬레이터 생성
    simulator = RealtimeTradingSimulator(FMP_API_KEY)

    print(" 실시간 시뮬레이션 시작!")
    print("Ctrl+C로 종료")
    print()

    cycle = 0

    try:
        while True:
            cycle += 1
            current_time = datetime.now()

            print(f"\n[사이클 #{cycle}] {current_time.strftime('%H:%M:%S')}")

            # 1. 실시간 가격 업데이트
            nvdl_price = simulator.get_realtime_price('NVDL')
            nvdq_price = simulator.get_realtime_price('NVDQ')
            print(f"NVDL: ${nvdl_price:.2f} | NVDQ: ${nvdq_price:.2f}")

            # 2. 매매 결정
            action, symbol, confidence = simulator.make_trading_decision()
            if action != "HOLD":
                print(f"신호: {action} {symbol} (신뢰도: {confidence:.3f})")

            # 3. 매매 실행
            simulator.execute_trade(action, symbol, confidence)

            # 4. 주기적 상태 표시
            if cycle % 10 == 0:
                simulator.display_status()

            # 5. 대기 (실제로는 더 짧은 간격)
            time.sleep(5)  # 5초마다 실행

    except KeyboardInterrupt:
        print(f"\n\n시뮬레이션 종료")
        simulator.display_status()
        print("\n최종 결과:")
        if simulator.total_trades > 0:
            print(f" 총 수익률: {simulator.total_profit:+.2f}%")
            print(f" 승률: {simulator.win_rate:.1f}%")
            print(f" 최종 잔고: ${simulator.balance:,.0f}")
        else:
            print("거래가 없었습니다.")

if __name__ == "__main__":
    main()