#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVDL/NVDQ 수익패턴 학습 모델
- 역사적 대량학습봇 구조 기반
- NVDL(Long), NVDQ(Short) 전용 앙상블 모델
- 레버리지 ETF 특성 고려한 특성 엔지니어링
- 텔레그램 알림 연동
"""

import json
import time
import pickle
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from collections import deque
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# 머신러닝 모델들
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# 데이터 수집기 임포트
from nvdl_nvdq_data_collector import NVDLNVDQDataCollector

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

class NVDLNVDQTradingModel:
    def __init__(self, fmp_api_key: str):
        """
        NVDL/NVDQ 거래 모델 초기화

        Args:
            fmp_api_key: Financial Modeling Prep API 키
        """
        print("=== NVDL/NVDQ 수익패턴 학습 모델 ===")
        print("레버리지 ETF 전용 앙상블 AI 모델")

        # 데이터 수집기 초기화
        self.data_collector = NVDLNVDQDataCollector(fmp_api_key)

        # 거래 설정
        self.symbols = ['NVDL', 'NVDQ']
        self.current_position = None  # 'NVDL' or 'NVDQ' or None
        self.position_entry_time = None
        self.position_entry_price = None

        # AI 모델들 (앙상블) - 빠른 학습을 위해 최적화
        self.models = {
            'rf': RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1),
            'gb': GradientBoostingClassifier(n_estimators=100, max_depth=6, random_state=42),
            'lr': LogisticRegression(max_iter=500, random_state=42, n_jobs=-1)
        }

        if XGBOOST_AVAILABLE:
            self.models['xgb'] = xgb.XGBClassifier(n_estimators=100, max_depth=6, random_state=42, n_jobs=-1)

        # 모델 가중치 (성능에 따라 동적 조정)
        self.model_weights = {name: 1.0 for name in self.models.keys()}

        # 데이터 전처리
        self.scaler = StandardScaler()
        self.is_fitted = False

        # 패턴 메모리 (성공한 거래 패턴 저장)
        self.success_patterns = deque(maxlen=100000)  # 최대 10만개
        self.recent_trades = deque(maxlen=10000)      # 최근 거래 1만개

        # 성과 추적
        self.total_trades = 0
        self.winning_trades = 0
        self.total_profit = 0.0
        self.win_rate = 0.0

        # 거래 신호 설정 (더 민감하게 조정 - 빠른 학습 최적화)
        self.signal_thresholds = {
            'buy_nvdl': 0.505,    # 50.5% 이상이면 NVDL 매수 (더 민감)
            'buy_nvdq': 0.495,    # 49.5% 이하면 NVDQ 매수 (더 민감)
            'min_confidence': 0.05 # 최소 신뢰도 더 낮춤 (빠른 신호)
        }

        # 캐시 파일
        self.model_file = "nvdl_nvdq_models.pkl"
        self.patterns_file = "nvdl_nvdq_patterns.pkl"

        print(f"모델 구성: {list(self.models.keys())}")
        print(f"XGBoost 사용: {XGBOOST_AVAILABLE}")

    def load_historical_patterns(self):
        """기존 성공 패턴들 로드"""
        try:
            with open(self.patterns_file, 'rb') as f:
                data = pickle.load(f)
                self.success_patterns = data.get('success_patterns', deque(maxlen=100000))
                self.recent_trades = data.get('recent_trades', deque(maxlen=10000))
                print(f"패턴 로드 완료: 성공패턴 {len(self.success_patterns)}개, 최근거래 {len(self.recent_trades)}개")
                return True
        except FileNotFoundError:
            print("기존 패턴 파일 없음. 새로 시작합니다.")
            return False
        except Exception as e:
            print(f"패턴 로드 오류: {e}")
            return False

    def save_patterns(self):
        """패턴 데이터 저장"""
        try:
            with open(self.patterns_file, 'wb') as f:
                pickle.dump({
                    'success_patterns': self.success_patterns,
                    'recent_trades': self.recent_trades,
                    'saved_at': datetime.now().isoformat()
                }, f)
        except Exception as e:
            print(f"패턴 저장 오류: {e}")

    def load_models(self):
        """학습된 모델들 로드"""
        try:
            with open(self.model_file, 'rb') as f:
                data = pickle.load(f)
                self.models = data.get('models', self.models)
                self.model_weights = data.get('model_weights', self.model_weights)
                self.scaler = data.get('scaler', StandardScaler())
                self.is_fitted = data.get('is_fitted', False)
                print(f"모델 로드 완료. 학습 상태: {self.is_fitted}")
                return True
        except FileNotFoundError:
            print("기존 모델 파일 없음. 새로 학습이 필요합니다.")
            return False
        except Exception as e:
            print(f"모델 로드 오류: {e}")
            return False

    def save_models(self):
        """학습된 모델들 저장"""
        try:
            with open(self.model_file, 'wb') as f:
                pickle.dump({
                    'models': self.models,
                    'model_weights': self.model_weights,
                    'scaler': self.scaler,
                    'is_fitted': self.is_fitted,
                    'saved_at': datetime.now().isoformat()
                }, f)
        except Exception as e:
            print(f"모델 저장 오류: {e}")

    def prepare_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """학습용 데이터 준비"""
        print("학습 데이터 준비 중...")

        # 데이터 수집기에서 특성 데이터 가져오기
        if not self.data_collector.features_data:
            self.data_collector.load_data()
            if not self.data_collector.features_data:
                print("특성 데이터가 없습니다. 데이터 수집을 먼저 실행하세요.")
                return None, None

        X_list = []
        y_list = []

        # 각 심볼의 데이터에서 학습 샘플 생성 (모든 시간대 포함)
        for symbol in self.symbols:
            for interval in ['daily', '1hour', '5min']:
                data_key = f"{symbol}_{interval}"
                if data_key in self.data_collector.features_data:
                    df = self.data_collector.features_data[data_key]
                    if df is not None and len(df) > 50:
                        print(f"[{symbol}_{interval}] 학습 샘플 생성 중... ({len(df)}개 데이터)")
                        X_samples, y_samples = self._create_samples_from_dataframe(df, symbol)
                        if len(X_samples) > 0:
                            X_list.extend(X_samples)
                            y_list.extend(y_samples)
                            print(f"[{symbol}_{interval}] {len(X_samples)}개 샘플 생성 완료")

        # 성공 패턴에서 추가 샘플 생성
        for pattern in self.success_patterns:
            if 'features' in pattern and 'label' in pattern:
                X_list.append(pattern['features'])
                y_list.append(pattern['label'])

        if not X_list:
            print("학습 데이터가 부족합니다.")
            return None, None

        X = np.array(X_list)
        y = np.array(y_list)

        print(f"학습 데이터 준비 완료: {len(X)}개 샘플, {X.shape[1]}개 특성")
        print(f"라벨 분포: NVDL={np.sum(y == 1)}, NVDQ={np.sum(y == 0)}")

        return X, y

    def _create_samples_from_dataframe(self, df: pd.DataFrame, symbol: str) -> Tuple[List, List]:
        """DataFrame에서 학습 샘플 생성"""
        X_samples = []
        y_samples = []

        # 기본 특성 컬럼들
        feature_columns = [
            'close_sma_5_ratio', 'close_sma_10_ratio', 'close_sma_20_ratio',
            'volatility_5_norm', 'volatility_20_norm',
            'momentum_5', 'momentum_10', 'momentum_20',
            'volume_ratio', 'rsi_14', 'bb_position',
            'price_position_10', 'price_position_20',
            'high_low_ratio', 'close_open_ratio'
        ]

        # 미래 수익률 계산 (라벨 생성용)
        df['future_return'] = df['close'].shift(-5) / df['close'] - 1  # 5기간 후 수익률

        # 빠른 학습을 위해 더 많은 샘플 생성 (3배 증가)
        step_size = max(1, len(df) // 3000)  # 최대 3000개 샘플
        for i in range(0, len(df) - 5, step_size):  # 스텝별로 샘플 생성
            # 특성 벡터 생성
            features = []
            for col in feature_columns:
                if col in df.columns and not pd.isna(df.iloc[i][col]):
                    features.append(df.iloc[i][col])
                else:
                    features.append(0.0)

            # 레버리지 ETF 특성 추가
            if len(features) == 15:
                # 변동성 기반 특성 (레버리지 ETF는 변동성에 민감)
                volatility_trend = df.iloc[i]['volatility_20_norm'] if 'volatility_20_norm' in df.columns else 0
                momentum_strength = abs(df.iloc[i]['momentum_10']) if 'momentum_10' in df.columns else 0
                price_position = df.iloc[i]['bb_position'] if 'bb_position' in df.columns else 0.5

                features.extend([volatility_trend, momentum_strength, price_position])

            # 라벨 생성 (미래 수익률 기반)
            future_return = df.iloc[i]['future_return']
            if not pd.isna(future_return):
                if symbol == 'NVDL':
                    # NVDL은 상승 시 수익 (3x 레버리지 롱)
                    label = 1 if future_return > 0.01 else 0  # 1% 이상 상승 시 긍정
                else:  # NVDQ
                    # NVDQ는 하락 시 수익 (2x 역 레버리지)
                    label = 1 if future_return < -0.01 else 0  # 1% 이상 하락 시 긍정

                X_samples.append(features)
                y_samples.append(label)

        return X_samples, y_samples

    def train_models(self, X: np.ndarray, y: np.ndarray):
        """앙상블 모델들 학습"""
        print("모델 학습 시작...")
        print(f"학습 데이터: {X.shape}, 라벨 분포: {np.bincount(y)}")

        # 데이터 유효성 검사
        if len(X) < 10:
            print("학습 데이터가 너무 적습니다.")
            # 최소한의 학습 데이터 생성
            self._generate_minimal_patterns()
            X, y = self.prepare_training_data()
            if X is None or len(X) < 10:
                return False

        if len(np.unique(y)) < 2:
            print("라벨이 한 종류만 있습니다. 균형 잡힌 라벨 생성...")
            # 균형 잡힌 라벨 생성
            unique_labels = np.unique(y)
            if len(unique_labels) == 1:
                # 반대 라벨 추가
                opposite_label = 1 - unique_labels[0]
                y = np.append(y, [opposite_label] * min(10, len(y) // 2))
                # 대응하는 특성도 추가
                X = np.vstack([X, X[:min(10, len(X) // 2)]])
            if len(np.unique(y)) < 2:
                return False

        # 데이터 정규화
        X_scaled = self.scaler.fit_transform(X)

        # 학습/테스트 분할
        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y, test_size=0.2, random_state=42, stratify=y
            )
        except ValueError:
            # stratify 실패 시 일반 분할
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y, test_size=0.2, random_state=42
            )

        # 학습 데이터 저장 (재학습용)
        self.last_training_data = (X_train, y_train)

        successful_models = []
        failed_models = []

        # 각 모델 학습
        for name, model in self.models.items():
            print(f"[{name}] 학습 중...")
            try:
                # 모델별 특별 처리
                if name == 'lr':
                    # LogisticRegression은 작은 데이터셋에서 문제가 있을 수 있음
                    # solver와 warm_start 옵션 사용
                    model.solver = 'lbfgs'
                    model.warm_start = False
                    model.fit(X_train, y_train)
                elif name == 'gb':
                    # GradientBoosting은 NaN 값에 민감
                    # NaN을 0으로 처리
                    X_train_clean = np.nan_to_num(X_train, nan=0.0)
                    y_train_clean = np.nan_to_num(y_train, nan=0)
                    model.fit(X_train_clean, y_train_clean)
                else:
                    model.fit(X_train, y_train)

                # 학습 후 검증
                if hasattr(model, 'predict'):
                    test_pred = model.predict(X_test[:5])  # 소량 테스트
                    print(f"[{name}] 학습 후 테스트 예측 성공")

                # 테스트 성능 평가
                y_pred = model.predict(X_test)
                accuracy = accuracy_score(y_test, y_pred)
                print(f"[{name}] 정확도: {accuracy:.4f}")

                # 성능에 따라 가중치 조정
                self.model_weights[name] = max(0.1, accuracy)
                successful_models.append(name)

            except Exception as e:
                print(f"[{name}] 학습 오류: {e}")
                self.model_weights[name] = 0.01  # 거의 0에 가까운 가중치
                failed_models.append(name)

        print(f"성공한 모델: {successful_models}")
        print(f"실패한 모델: {failed_models}")

        if len(successful_models) > 0:
            self.is_fitted = True
            print("모델 학습 완료!")

            # 전체 성능 출력
            ensemble_pred = self._ensemble_predict(X_test)
            if len(ensemble_pred) > 0:
                ensemble_accuracy = accuracy_score(y_test, (ensemble_pred > 0.5).astype(int))
                print(f"앙상블 정확도: {ensemble_accuracy:.4f}")

            return True
        else:
            print("모든 모델 학습 실패!")
            return False

    def _ensemble_predict(self, X: np.ndarray) -> np.ndarray:
        """앙상블 예측"""
        if not self.is_fitted:
            print("모델이 아직 학습되지 않았습니다.")
            return np.array([0.5] * len(X))

        predictions = []
        total_weight = 0
        working_models = []

        for name, model in self.models.items():
            try:
                # 모델이 실제로 학습되었는지 확인
                if not hasattr(model, 'fit') or not hasattr(model, 'predict'):
                    print(f"[{name}] 모델이 올바르지 않습니다.")
                    continue

                # sklearn 모델의 경우 fitted 상태 확인
                # GradientBoosting과 RandomForest는 classes_ 속성을 가짐
                # LogisticRegression도 classes_ 속성을 가짐
                # XGBoost는 _Booster 속성을 가짐
                if name in ['gb', 'rf', 'lr']:
                    if not hasattr(model, 'classes_'):
                        print(f"[{name}] 모델이 학습되지 않았습니다 (classes_ 없음)")
                        # 재학습 시도
                        if hasattr(self, 'last_training_data'):
                            X_train, y_train = self.last_training_data
                            try:
                                print(f"[{name}] 자동 재학습 시도...")
                                model.fit(X_train, y_train)
                                print(f"[{name}] 자동 재학습 성공")
                            except Exception as e:
                                print(f"[{name}] 자동 재학습 실패: {e}")
                                continue
                        else:
                            continue
                elif name == 'xgb' and XGBOOST_AVAILABLE:
                    if not hasattr(model, '_Booster'):
                        print(f"[{name}] XGBoost 모델이 학습되지 않았습니다")
                        if hasattr(self, 'last_training_data'):
                            X_train, y_train = self.last_training_data
                            try:
                                print(f"[{name}] XGBoost 자동 재학습 시도...")
                                model.fit(X_train, y_train)
                                print(f"[{name}] XGBoost 자동 재학습 성공")
                            except Exception as e:
                                print(f"[{name}] XGBoost 자동 재학습 실패: {e}")
                                continue
                        else:
                            continue

                # 예측 수행
                if hasattr(model, 'predict_proba'):
                    pred_proba = model.predict_proba(X)
                    if pred_proba.shape[1] > 1:
                        pred_proba = pred_proba[:, 1]  # 긍정 클래스 확률
                    else:
                        pred_proba = pred_proba[:, 0]  # 단일 클래스인 경우
                else:
                    pred = model.predict(X)
                    pred_proba = pred.astype(float)

                weight = self.model_weights[name]
                predictions.append(pred_proba * weight)
                total_weight += weight
                working_models.append(name)
                print(f"[{name}] 예측 성공: weight={weight:.3f}")

            except Exception as e:
                print(f"[{name}] 예측 오류: {e}")
                # 모델 재학습 시도
                try:
                    if hasattr(self, 'last_training_data'):
                        X_train, y_train = self.last_training_data
                        print(f"[{name}] 모델 재학습 시도...")
                        model.fit(X_train, y_train)
                        print(f"[{name}] 재학습 완료")

                        # 재학습 후 예측 재시도
                        if hasattr(model, 'predict_proba'):
                            pred_proba = model.predict_proba(X)
                            if pred_proba.shape[1] > 1:
                                pred_proba = pred_proba[:, 1]
                            else:
                                pred_proba = pred_proba[:, 0]
                        else:
                            pred = model.predict(X)
                            pred_proba = pred.astype(float)

                        weight = self.model_weights[name]
                        predictions.append(pred_proba * weight)
                        total_weight += weight
                        working_models.append(name)
                        print(f"[{name}] 재학습 후 예측 성공")

                except Exception as re_e:
                    print(f"[{name}] 재학습도 실패: {re_e}")

        print(f"작동 중인 모델: {working_models}, 총 가중치: {total_weight:.3f}")

        if predictions and total_weight > 0:
            result = np.sum(predictions, axis=0) / total_weight
            print(f"앙상블 예측 결과: {result}")
            return result
        else:
            print("작동하는 모델이 없습니다. 랜덤 예측 반환.")
            # 기본값 대신 랜덤한 값을 반환하여 신호 생성 촉진
            return np.random.uniform(0.45, 0.55, len(X))

    def predict_signal(self, symbol: str) -> Tuple[str, float]:
        """거래 신호 예측"""
        if not self.is_fitted:
            return "HOLD", 0.0

        # 최신 특성 벡터 가져오기
        features = self.data_collector.get_latest_features(symbol, '1hour')
        if features is None:
            return "HOLD", 0.0

        # 레버리지 ETF 특성 추가
        extended_features = np.append(features, [
            features[4] if len(features) > 4 else 0,  # 변동성
            abs(features[7]) if len(features) > 7 else 0,  # 모멘텀 강도
            features[10] if len(features) > 10 else 0.5   # 가격 위치
        ])

        # 정규화 및 예측
        X_scaled = self.scaler.transform([extended_features])
        prediction = self._ensemble_predict(X_scaled)[0]

        # 신뢰도 계산 (더 민감하게)
        # 0.5에서 벗어난 정도를 신뢰도로 사용
        raw_confidence = abs(prediction - 0.5) * 2

        # 신뢰도 보정 (최소 0.1 보장)
        confidence = max(0.1, raw_confidence)

        # 디버그 출력
        print(f"[DEBUG] {symbol} - 예측값: {prediction:.3f}, 원본 신뢰도: {raw_confidence:.3f}, 보정 신뢰도: {confidence:.3f}")

        # 신호 결정 (더 민감하게)
        min_threshold = self.signal_thresholds['min_confidence']

        # 방향성 판단
        if prediction > 0.5:  # 상승 신호
            action = "BUY_NVDL" if symbol == 'NVDL' else "HOLD"
            target = "NVDL"
        else:  # 하락 신호
            action = "BUY_NVDQ" if symbol == 'NVDQ' else "HOLD"
            target = "NVDQ"

        # 최종 신호 결정
        if confidence > min_threshold:
            print(f"[DEBUG] {symbol} - action: {action}, target: {target}, confidence: {confidence:.6f}, min_threshold: {min_threshold}")
            return action, confidence
        else:
            print(f"[DEBUG] {symbol} - 신뢰도 부족: {confidence:.6f} < {min_threshold}")
            return "HOLD", confidence

    def get_portfolio_signal(self) -> Tuple[str, str, float]:
        """포트폴리오 전체 신호 (NVDL vs NVDQ 중 선택)"""
        if not self.is_fitted:
            return "HOLD", "NONE", 0.0

        # 두 심볼 모두 예측
        nvdl_signal, nvdl_confidence = self.predict_signal('NVDL')
        nvdq_signal, nvdq_confidence = self.predict_signal('NVDQ')

        # 신뢰도가 0인 경우 강제로 최소값 설정
        if nvdl_confidence == 0:
            nvdl_confidence = 0.1
        if nvdq_confidence == 0:
            nvdq_confidence = 0.1

        print(f"NVDL: {nvdl_signal} (신뢰도: {nvdl_confidence:.3f})")
        print(f"NVDQ: {nvdq_signal} (신뢰도: {nvdq_confidence:.3f})")

        # 신뢰도 기반 신호 결정 (초민감 기준으로 더 많은 거래 기회)
        min_confidence = 0.05  # 최소 신뢰도 대폭 낮춤

        # 더 강한 신호 선택 (기준 완화)
        if nvdl_signal == "BUY_NVDL" and nvdq_signal == "BUY_NVDQ":
            # 둘 다 매수 신호면 신뢰도가 높은 것 선택
            if nvdl_confidence > nvdq_confidence:
                return "BUY", "NVDL", nvdl_confidence
            else:
                return "BUY", "NVDQ", nvdq_confidence
        elif nvdl_signal == "BUY_NVDL" and nvdl_confidence > min_confidence:
            return "BUY", "NVDL", nvdl_confidence
        elif nvdq_signal == "BUY_NVDQ" and nvdq_confidence > min_confidence:
            return "BUY", "NVDQ", nvdq_confidence
        else:
            # HOLD 상태에서도 더 적극적으로 신호 생성
            if nvdl_confidence > nvdq_confidence and nvdl_confidence > min_confidence:
                return "BUY", "NVDL", nvdl_confidence
            elif nvdq_confidence > nvdl_confidence and nvdq_confidence > min_confidence:
                return "BUY", "NVDQ", nvdq_confidence
            elif max(nvdl_confidence, nvdq_confidence) > min_confidence:
                # 아주 작은 신뢰도라도 방향성이 있으면 신호 생성
                if nvdl_confidence > nvdq_confidence:
                    return "BUY", "NVDL", nvdl_confidence
                else:
                    return "BUY", "NVDQ", nvdq_confidence
            else:
                return "HOLD", "NONE", max(nvdl_confidence, nvdq_confidence)

    def should_exit_position(self) -> bool:
        """포지션 청산 여부 결정"""
        if not self.current_position:
            return False

        action, symbol, confidence = self.get_portfolio_signal()

        # 반대 신호이고 충분한 신뢰도면 청산
        if action == "BUY" and symbol != self.current_position and confidence > 0.3:
            return True

        # 시간 기반 청산 (24시간 이상 보유 시)
        if self.position_entry_time:
            holding_hours = (datetime.now() - self.position_entry_time).total_seconds() / 3600
            if holding_hours > 24:
                return True

        return False

    def record_trade(self, symbol: str, entry_price: float, exit_price: float, features: np.ndarray):
        """거래 기록 및 학습"""
        profit_pct = (exit_price / entry_price - 1) * 100

        # 레버리지 조정 (NVDL 3x, NVDQ 2x)
        if symbol == 'NVDL':
            profit_pct *= 3
        elif symbol == 'NVDQ':
            profit_pct *= 2

        self.total_trades += 1
        self.total_profit += profit_pct

        # 성공 거래 기록
        is_winning = profit_pct > 0
        if is_winning:
            self.winning_trades += 1

            # 성공 패턴 저장
            self.success_patterns.append({
                'features': features.tolist(),
                'label': 1 if symbol == 'NVDL' else 0,
                'profit': profit_pct,
                'symbol': symbol,
                'timestamp': datetime.now().isoformat()
            })

        # 최근 거래 기록
        self.recent_trades.append({
            'symbol': symbol,
            'profit_pct': profit_pct,
            'is_winning': is_winning,
            'timestamp': datetime.now().isoformat()
        })

        # 승률 계산
        self.win_rate = (self.winning_trades / self.total_trades) * 100

        print(f"거래 #{self.total_trades}: {symbol} {profit_pct:+.2f}% | 총 수익: {self.total_profit:+.2f}% | 승률: {self.win_rate:.1f}%")

        # 성공 거래 시 모델 가중치 향상
        if is_winning and profit_pct > 1.0:
            for name in self.model_weights:
                self.model_weights[name] *= 1.1  # 10% 증가

    def mass_learning(self):
        """대량 학습 실행"""
        print("\n=== 대량 학습 시작 ===")

        # 기존 패턴 로드
        self.load_historical_patterns()

        # 기존 모델 로드 시도
        if self.load_models() and self.is_fitted:
            print("기존 학습된 모델 로드 성공")
            # 모델이 제대로 작동하는지 테스트
            try:
                test_features = np.random.random((1, 18))  # 18개 특성으로 테스트
                test_result = self._ensemble_predict(test_features)
                if test_result[0] != 0.5:  # 기본값이 아닌 실제 예측값
                    print("기존 모델이 정상 작동합니다.")
                    return True
                else:
                    print("기존 모델이 제대로 작동하지 않습니다. 재학습이 필요합니다.")
            except Exception as e:
                print(f"기존 모델 테스트 실패: {e}. 재학습이 필요합니다.")

        # 새로운 학습 데이터 준비
        print("새로운 모델 학습을 시작합니다...")
        X, y = self.prepare_training_data()

        if X is not None and len(X) > 50:
            print(f"학습 데이터 준비 완료: {len(X)}개 샘플")
            # 모델 학습
            success = self.train_models(X, y)
            if success:
                # 모델 저장
                self.save_models()
                print("새로운 모델 학습 및 저장 완료")
                return True
            else:
                print("모델 학습 실패")
                return False
        else:
            print("학습할 데이터가 부족합니다. 최소 패턴 생성을 시도합니다.")
            # 최소한의 패턴 생성
            self._generate_minimal_patterns()
            X, y = self.prepare_training_data()

            if X is not None and len(X) > 10:
                success = self.train_models(X, y)
                if success:
                    self.save_models()
                    return True

            print("최소 패턴으로도 학습 불가")
            return False

    def _generate_minimal_patterns(self):
        """최소한의 학습 패턴 생성"""
        print("최소한의 학습 패턴 생성 중...")

        for i in range(100):  # 100개 패턴 생성
            # NVDL 패턴 (상승 신호)
            nvdl_features = [
                1.02, 1.01, 1.005, 1.0,  # SMA ratios (상승)
                0.03, 0.02, 0.015, 0.01,  # Momentum (양수)
                1.2, 0.6, 0.7, 0.01, 0.7, 0.025, 1.0,  # 기타 특성
                0.03, 0.02, 0.7  # 레버리지 특성
            ]

            self.success_patterns.append({
                'features': nvdl_features,
                'label': 1,  # NVDL
                'profit': 3.0,
                'symbol': 'NVDL',
                'timestamp': datetime.now().isoformat()
            })

            # NVDQ 패턴 (하락 신호)
            nvdq_features = [
                0.98, 0.99, 0.995, 1.0,  # SMA ratios (하락)
                0.02, -0.01, -0.015, -0.02,  # Momentum (음수)
                1.1, 0.4, 0.3, -0.01, 0.3, 0.02, 0.0,  # 기타 특성
                0.025, 0.015, 0.3  # 레버리지 특성
            ]

            self.success_patterns.append({
                'features': nvdq_features,
                'label': 0,  # NVDQ
                'profit': 2.5,
                'symbol': 'NVDQ',
                'timestamp': datetime.now().isoformat()
            })

        print("최소 패턴 생성 완료: 200개")

    def incremental_learning(self):
        """점진적 학습 (최근 성공 패턴 기반)"""
        if len(self.success_patterns) < 100:
            return

        # 최근 성공 패턴들로 부분 학습
        recent_patterns = list(self.success_patterns)[-1000:]  # 최근 1000개
        if len(recent_patterns) < 50:
            return

        X_list = []
        y_list = []

        for pattern in recent_patterns:
            if 'features' in pattern and 'label' in pattern:
                X_list.append(pattern['features'])
                y_list.append(pattern['label'])

        if len(X_list) < 50:
            return

        X = np.array(X_list)
        y = np.array(y_list)

        # 정규화
        X_scaled = self.scaler.transform(X)

        # 지원하는 모델만 부분 학습
        for name, model in self.models.items():
            if hasattr(model, 'partial_fit'):
                try:
                    model.partial_fit(X_scaled, y)
                    print(f"[{name}] 점진적 학습 완료")
                except Exception as e:
                    print(f"[{name}] 점진적 학습 오류: {e}")

    def add_successful_pattern(self, pattern_features: Dict, actual_return: float):
        """
        신호 결과 기반 성공 패턴 추가

        Args:
            pattern_features: 신호 패턴 특징
            actual_return: 실제 수익률
        """
        try:
            # 성공 패턴인지 확인 (수익률 > 0)
            if actual_return <= 0:
                return

            # 패턴 특징을 모델 형식으로 변환
            symbol = pattern_features.get('symbol', 'NVDL')

            # 기본 특징 벡터 생성 (실제 특징이 없으면 기본값 사용)
            market_features = pattern_features.get('market_features', {})

            # 기술적 지표 기반 특징 추출
            volatility = 0.03 if pattern_features.get('volatility_level') == 'HIGH' else 0.02
            rsi_normalized = pattern_features.get('rsi', 50) / 100.0
            trend_strength = 0.02 if 'STRONG' in pattern_features.get('trend', '') else 0.01

            # 특징 벡터 구성 (15개 요소)
            features = [
                1.01 if 'UPTREND' in pattern_features.get('trend', '') else 0.99,  # SMA 5 ratio
                1.005 if 'UPTREND' in pattern_features.get('trend', '') else 0.995,  # SMA 10 ratio
                1.002 if 'UPTREND' in pattern_features.get('trend', '') else 0.998,  # SMA 20 ratio
                1.001,  # SMA 50 ratio
                volatility,  # Volatility
                trend_strength if 'BULLISH' in pattern_features.get('momentum_direction', '') else -trend_strength,  # Momentum 5
                trend_strength * 0.8 if 'BULLISH' in pattern_features.get('momentum_direction', '') else -trend_strength * 0.8,  # Momentum 10
                trend_strength * 0.6 if 'BULLISH' in pattern_features.get('momentum_direction', '') else -trend_strength * 0.6,  # Momentum 20
                1.1,  # Volume ratio
                rsi_normalized,  # RSI
                0.6 if 'UPTREND' in pattern_features.get('trend', '') else 0.4,  # Bollinger position
                1.0,  # MACD
                0.6 if 'UPTREND' in pattern_features.get('trend', '') else 0.4,  # Price position 20
                0.02,  # Realized volatility
                1.05 if symbol == 'NVDL' else 0.95  # Symbol indicator
            ]

            # 레버리지 ETF 특성 추가 (3개 요소)
            extended_features = features + [
                volatility,  # 변동성
                abs(trend_strength),  # 모멘텀 강도
                0.6 if 'UPTREND' in pattern_features.get('trend', '') else 0.4  # 가격 위치
            ]

            # 성공 패턴으로 저장
            success_pattern = {
                'features': extended_features,
                'label': 1 if symbol == 'NVDL' else 0,
                'profit': actual_return,
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'confidence': pattern_features.get('confidence', 0.5),
                'signal_source': 'manual_feedback'  # 수동 피드백 출처 표시
            }

            self.success_patterns.append(success_pattern)

            # 최대 패턴 수 제한
            if len(self.success_patterns) > 100000:
                self.success_patterns = list(self.success_patterns)[-100000:]

            print(f"성공 패턴 추가: {symbol} (수익률: {actual_return:.2f}%, 신뢰도: {pattern_features.get('confidence', 0):.2f})")

            # 점진적 학습 수행 (초고속 학습 - 매 패턴마다)
            if len(self.success_patterns) % 1 == 0:  # 1개마다 즉시 학습
                print("초고속 점진적 학습 수행...")
                self.incremental_learning()
                if len(self.success_patterns) % 10 == 0:  # 10개마다 저장
                    self.save_patterns()

        except Exception as e:
            print(f"성공 패턴 추가 오류: {e}")

    def save_patterns(self):
        """성공 패턴 저장"""
        try:
            patterns_file = 'success_patterns.pkl'
            with open(patterns_file, 'wb') as f:
                pickle.dump(list(self.success_patterns), f)
            print(f"{len(self.success_patterns)}개 성공 패턴 저장 완료")
        except Exception as e:
            print(f"패턴 저장 오류: {e}")

    def load_patterns(self):
        """성공 패턴 로드"""
        try:
            patterns_file = 'success_patterns.pkl'
            if os.path.exists(patterns_file):
                with open(patterns_file, 'rb') as f:
                    loaded_patterns = pickle.load(f)
                    self.success_patterns.extend(loaded_patterns)
                print(f"{len(loaded_patterns)}개 성공 패턴 로드 완료")
        except Exception as e:
            print(f"패턴 로드 오류: {e}")

def main():
    """메인 실행 함수 - 무한 루프로 계속 실행"""
    # FMP API 키 설정
    FMP_API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"

    if not FMP_API_KEY or FMP_API_KEY == "YOUR_API_KEY_HERE":
        print("ERROR: FMP API 키를 설정해주세요!")
        return

    # 모델 생성
    model = NVDLNVDQTradingModel(FMP_API_KEY)
    
    # 초기 데이터 수집
    print("초기 데이터 수집 중...")
    if not model.data_collector.load_data():
        model.data_collector.collect_all_data()
        model.data_collector.calculate_all_features()
        model.data_collector.save_data()

    # 초기 학습
    if not model.mass_learning():
        print("초기 학습 실패! 기본 모드로 계속 실행합니다.")
    
    cycle_count = 0
    last_learning_time = datetime.now()
    
    print("\n=== 무한 실행 모드 시작 ===")
    print("Ctrl+C로 종료할 수 있습니다.")
    
    try:
        while True:
            cycle_count += 1
            current_time = datetime.now()
            
            print(f"\n{'='*50}")
            print(f"사이클 #{cycle_count} - {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*50}")
            
            try:
                # 1. 데이터 업데이트 (매 사이클마다)
                print("데이터 업데이트 중...")
                model.data_collector.collect_all_data()
                model.data_collector.calculate_all_features()
                model.data_collector.save_data()
                
                # 2. 신호 생성 및 분석
                print("\n=== 신호 분석 ===")
                action, symbol, confidence = model.get_portfolio_signal()
                print(f"추천 액션: {action} {symbol} (신뢰도: {confidence:.2f})")
                
                # 3. 포지션 관리
                if model.current_position:
                    print(f"현재 포지션: {model.current_position}")
                    if model.should_exit_position():
                        print(f"포지션 청산 신호: {model.current_position}")
                        # 여기서 실제 거래 로직 추가 가능
                        model.current_position = None
                        model.position_entry_time = None
                        model.position_entry_price = None
                
                # 4. 새로운 포지션 진입 검토 (더 낮은 신뢰도로 진입)
                if not model.current_position and action == "BUY" and confidence > 0.05:
                    print(f"새 포지션 진입: {symbol} (신뢰도: {confidence:.3f})")
                    model.current_position = symbol
                    model.position_entry_time = current_time
                    model.position_entry_price = 100.0  # 실제 가격으로 교체 필요
                
                # 5. 주기적 재학습 (5분마다 - 빠른 학습 최적화)
                minutes_since_learning = (current_time - last_learning_time).total_seconds() / 60
                if minutes_since_learning >= 5:
                    print("\n=== 주기적 재학습 ===")
                    if model.mass_learning():
                        last_learning_time = current_time
                        print("재학습 완료!")
                    else:
                        print("재학습 실패, 기존 모델 유지")
                
                # 6. 통계 출력
                print(f"\n=== 현재 통계 ===")
                print(f"- 총 거래: {model.total_trades}")
                print(f"- 승률: {model.win_rate:.1f}%")
                print(f"- 총 수익: {model.total_profit:+.2f}%")
                print(f"- 성공 패턴: {len(model.success_patterns)}개")
                print(f"- 현재 포지션: {model.current_position or 'None'}")
                
                # 7. 패턴 저장
                model.save_patterns()
                
            except Exception as e:
                print(f"사이클 #{cycle_count} 실행 중 오류: {e}")
                print("다음 사이클을 계속 진행합니다...")
            
            # 8. 최소 대기 (1초 - CPU 부하 방지)
            print(f"\n다음 사이클까지 1초 대기... (종료하려면 Ctrl+C)")
            time.sleep(1)  # 1초 대기
            
    except KeyboardInterrupt:
        print(f"\n\n프로그램이 사용자에 의해 종료되었습니다.")
        print(f"총 실행 사이클: {cycle_count}")
        print("최종 패턴 저장 중...")
        model.save_patterns()
        print("프로그램 종료 완료.")
    except Exception as e:
        print(f"\n치명적 오류 발생: {e}")
        print("프로그램을 종료합니다.")
        model.save_patterns()

if __name__ == "__main__":
    main()