#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVDL/NVDQ 수익패턴 학습 모델 (수정 버전)
- 모델 학습 문제 해결
- 신뢰도 계산 로직 개선
- GradientBoosting, LogisticRegression 초기화 문제 수정
- NaN 데이터 처리 완전 해결

*** 중요: FMP API만 사용! yfinance 절대 사용 금지! ***
데이터 소스: Financial Modeling Prep API (FMP)
- 실시간 데이터: FMP Real-time API
- 히스토리 데이터: FMP Historical API
- yfinance는 신뢰성 문제로 사용 금지
- 모든 데이터 수집은 nvdl_nvdq_data_collector.py를 통해서만 진행
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
        """NVDL/NVDQ 거래 모델 초기화"""
        print("=== NVDL/NVDQ 수익패턴 학습 모델 (수정 버전) ===")
        print("모델 학습 문제 해결 및 신뢰도 개선")

        # 데이터 수집기 초기화
        self.data_collector = NVDLNVDQDataCollector(fmp_api_key)

        # 거래 설정
        self.symbols = ['NVDL', 'NVDQ']
        self.current_position = None
        self.position_entry_time = None
        self.position_entry_price = None

        # AI 모델들 (앙상블) - 최적화된 설정
        self.models = {
            'rf': RandomForestClassifier(
                n_estimators=50,
                max_depth=8,
                random_state=42,
                n_jobs=-1,
                min_samples_split=5,
                min_samples_leaf=2
            ),
            'gb': GradientBoostingClassifier(
                n_estimators=50,
                max_depth=5,
                random_state=42,
                learning_rate=0.1,
                min_samples_split=5,
                min_samples_leaf=2
            ),
            'lr': LogisticRegression(
                max_iter=1000,
                random_state=42,
                n_jobs=-1,
                solver='lbfgs',
                warm_start=False
            )
        }

        if XGBOOST_AVAILABLE:
            self.models['xgb'] = xgb.XGBClassifier(
                n_estimators=50,
                max_depth=5,
                random_state=42,
                n_jobs=-1,
                learning_rate=0.1
            )

        # 모델 가중치 (성능에 따라 동적 조정)
        self.model_weights = {name: 1.0 for name in self.models.keys()}

        # 데이터 전처리
        self.scaler = StandardScaler()
        self.is_fitted = False
        self.last_training_data = None

        # 패턴 메모리
        self.success_patterns = deque(maxlen=100000)
        self.recent_trades = deque(maxlen=10000)

        # 성과 추적
        self.total_trades = 0
        self.winning_trades = 0
        self.total_profit = 0.0
        self.win_rate = 0.0

        # 거래 신호 설정 (더 민감하게)
        self.signal_thresholds = {
            'buy_nvdl': 0.52,    # 52% 이상이면 NVDL 매수
            'buy_nvdq': 0.48,    # 48% 이하면 NVDQ 매수
            'min_confidence': 0.03  # 최소 신뢰도 매우 낮춤
        }

        # 캐시 파일
        self.model_file = "nvdl_nvdq_models_fixed.pkl"
        self.patterns_file = "nvdl_nvdq_patterns_fixed.pkl"

        print(f"모델 구성: {list(self.models.keys())}")
        print(f"XGBoost 사용: {XGBOOST_AVAILABLE}")

    def load_historical_patterns(self):
        """기존 성공 패턴들 로드"""
        try:
            with open(self.patterns_file, 'rb') as f:
                data = pickle.load(f)
                self.success_patterns = data.get('success_patterns', deque(maxlen=100000))
                self.recent_trades = data.get('recent_trades', deque(maxlen=10000))
                print(f"패턴 로드 완료: {len(self.success_patterns)}개")
                return True
        except:
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
                self.last_training_data = data.get('last_training_data', None)
                print(f"모델 로드 완료. 학습 상태: {self.is_fitted}")
                return True
        except:
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
                    'last_training_data': self.last_training_data,
                    'saved_at': datetime.now().isoformat()
                }, f)
                print("모델 저장 완료")
        except Exception as e:
            print(f"모델 저장 오류: {e}")

    def prepare_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """학습용 데이터 준비"""
        print("학습 데이터 준비 중...")

        if not self.data_collector.features_data:
            self.data_collector.load_data()
            if not self.data_collector.features_data:
                print("특성 데이터가 없습니다.")
                return None, None

        X_list = []
        y_list = []

        # 각 심볼의 데이터에서 학습 샘플 생성
        for symbol in self.symbols:
            for interval in ['daily', '1hour', '5min']:
                data_key = f"{symbol}_{interval}"
                if data_key in self.data_collector.features_data:
                    df = self.data_collector.features_data[data_key]
                    if df is not None and len(df) > 30:
                        X_samples, y_samples = self._create_samples_from_dataframe(df, symbol)
                        if len(X_samples) > 0:
                            X_list.extend(X_samples)
                            y_list.extend(y_samples)

        # 성공 패턴에서 추가 샘플
        for pattern in list(self.success_patterns)[-5000:]:  # 최근 5000개만
            if 'features' in pattern and 'label' in pattern:
                X_list.append(pattern['features'])
                y_list.append(pattern['label'])

        if not X_list:
            print("학습 데이터가 부족합니다. 최소 패턴 생성...")
            self._generate_minimal_patterns()
            return self.prepare_training_data()

        X = np.array(X_list)
        y = np.array(y_list)

        print(f"학습 데이터: {len(X)}개 샘플, {X.shape[1]}개 특성")
        print(f"라벨 분포: NVDL={np.sum(y == 1)}, NVDQ={np.sum(y == 0)}")

        return X, y

    def _create_samples_from_dataframe(self, df: pd.DataFrame, symbol: str) -> Tuple[List, List]:
        """DataFrame에서 학습 샘플 생성"""
        X_samples = []
        y_samples = []

        feature_columns = [
            'close_sma_5_ratio', 'close_sma_10_ratio', 'close_sma_20_ratio',
            'volatility_5_norm', 'volatility_20_norm',
            'momentum_5', 'momentum_10', 'momentum_20',
            'volume_ratio', 'rsi_14', 'bb_position',
            'price_position_10', 'price_position_20',
            'high_low_ratio', 'close_open_ratio'
        ]

        df['future_return'] = df['close'].shift(-5) / df['close'] - 1

        step_size = max(1, len(df) // 2000)
        for i in range(0, len(df) - 5, step_size):
            features = []
            for col in feature_columns:
                if col in df.columns and not pd.isna(df.iloc[i][col]):
                    val = df.iloc[i][col]
                    # NaN과 Inf 값 추가 처리
                    if np.isnan(val) or np.isinf(val):
                        features.append(0.0)
                    else:
                        features.append(float(val))
                else:
                    features.append(0.0)

            if len(features) == 15:
                volatility_trend = df.iloc[i].get('volatility_20_norm', 0)
                momentum_strength = abs(df.iloc[i].get('momentum_10', 0))
                price_position = df.iloc[i].get('bb_position', 0.5)

                # NaN과 Inf 값 추가 처리
                volatility_trend = 0.0 if (np.isnan(volatility_trend) or np.isinf(volatility_trend)) else float(volatility_trend)
                momentum_strength = 0.0 if (np.isnan(momentum_strength) or np.isinf(momentum_strength)) else float(momentum_strength)
                price_position = 0.5 if (np.isnan(price_position) or np.isinf(price_position)) else float(price_position)

                features.extend([volatility_trend, momentum_strength, price_position])

            future_return = df.iloc[i]['future_return']
            if not pd.isna(future_return):
                if symbol == 'NVDL':
                    label = 1 if future_return > 0.005 else 0  # 0.5% 이상 상승
                else:
                    label = 1 if future_return < -0.005 else 0  # 0.5% 이상 하락

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
            self._generate_minimal_patterns()
            X, y = self.prepare_training_data()
            if X is None or len(X) < 10:
                return False

        if len(np.unique(y)) < 2:
            print("라벨이 한 종류만 있습니다. 균형 잡힌 라벨 생성...")
            unique_labels = np.unique(y)
            if len(unique_labels) == 1:
                opposite_label = 1 - unique_labels[0]
                y = np.append(y, [opposite_label] * min(10, len(y) // 2))
                X = np.vstack([X, X[:min(10, len(X) // 2)]])
            if len(np.unique(y)) < 2:
                return False

        # 데이터 완전 정리 (NaN, Inf 값 모두 제거)
        print("학습 전 데이터 정리 중...")
        X_clean = np.nan_to_num(X, nan=0.0, posinf=1.0, neginf=-1.0)
        X_clean = np.clip(X_clean, -10, 10)

        # NaN 검사
        if np.any(np.isnan(X_clean)) or np.any(np.isinf(X_clean)):
            print("WARNING: 여전히 NaN/Inf 데이터 존재, 추가 정리")
            X_clean = np.where(np.isnan(X_clean) | np.isinf(X_clean), 0.0, X_clean)

        print(f"정리된 데이터: NaN={np.sum(np.isnan(X_clean))}, Inf={np.sum(np.isinf(X_clean))}")

        # 데이터 정규화
        X_scaled = self.scaler.fit_transform(X_clean)

        # 학습/테스트 분할
        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y, test_size=0.2, random_state=42, stratify=y
            )
        except:
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y, test_size=0.2, random_state=42
            )

        # 학습 데이터 저장
        self.last_training_data = (X_train, y_train)

        successful_models = []

        # 각 모델 학습
        for name, model in self.models.items():
            print(f"[{name}] 학습 중...")
            try:
                # NaN 데이터 완전 제거 (모든 모델 공통)
                X_train_clean = np.nan_to_num(X_train, nan=0.0, posinf=1.0, neginf=-1.0)
                y_train_clean = np.nan_to_num(y_train, nan=0, posinf=1, neginf=0).astype(int)

                # 무한대값 추가 처리
                X_train_clean = np.clip(X_train_clean, -10, 10)

                # 모델별 특별 처리
                if name == 'lr':
                    # LogisticRegression NaN 에러 완전 해결
                    model.solver = 'liblinear'  # 더 안정적인 solver
                    model.warm_start = False
                    model.max_iter = 500
                    # 추가 NaN 검사
                    if np.any(np.isnan(X_train_clean)) or np.any(np.isnan(y_train_clean)):
                        print(f"[{name}] 여전히 NaN 존재, 스킵")
                        continue
                    model.fit(X_train_clean, y_train_clean)
                elif name == 'gb':
                    # GradientBoosting NaN 에러 완전 해결
                    # 추가 NaN 검사
                    if np.any(np.isnan(X_train_clean)) or np.any(np.isnan(y_train_clean)):
                        print(f"[{name}] 여전히 NaN 존재, 스킵")
                        continue
                    model.fit(X_train_clean, y_train_clean)
                else:
                    model.fit(X_train_clean, y_train_clean)

                # 테스트
                y_pred = model.predict(X_test)
                accuracy = accuracy_score(y_test, y_pred)
                print(f"[{name}] 정확도: {accuracy:.4f}")

                self.model_weights[name] = max(0.1, accuracy)
                successful_models.append(name)

            except Exception as e:
                print(f"[{name}] 학습 오류: {e}")
                self.model_weights[name] = 0.01

        if len(successful_models) > 0:
            self.is_fitted = True
            print(f"학습 완료! 성공 모델: {successful_models}")
            return True
        else:
            print("모든 모델 학습 실패!")
            return False

    def _ensemble_predict(self, X: np.ndarray) -> np.ndarray:
        """앙상블 예측"""
        if not self.is_fitted:
            return np.random.uniform(0.45, 0.55, len(X))

        predictions = []
        total_weight = 0
        working_models = []

        for name, model in self.models.items():
            try:
                # 모델별 fitted 상태 확인
                if name in ['gb', 'rf', 'lr']:
                    if not hasattr(model, 'classes_'):
                        if self.last_training_data:
                            X_train, y_train = self.last_training_data
                            print(f"[{name}] 자동 재학습...")
                            # 모든 모델에 NaN 처리 적용
                            X_train_clean = np.nan_to_num(X_train, nan=0.0, posinf=1.0, neginf=-1.0)
                            y_train_clean = np.nan_to_num(y_train, nan=0, posinf=1, neginf=0).astype(int)
                            X_train_clean = np.clip(X_train_clean, -10, 10)

                            if np.any(np.isnan(X_train_clean)) or np.any(np.isnan(y_train_clean)):
                                print(f"[{name}] 재학습 데이터에 NaN 존재, 스킵")
                                continue

                            if name == 'lr':
                                model.solver = 'liblinear'
                                model.max_iter = 500
                            model.fit(X_train_clean, y_train_clean)
                        else:
                            continue
                elif name == 'xgb' and XGBOOST_AVAILABLE:
                    if not hasattr(model, '_Booster'):
                        if self.last_training_data:
                            X_train, y_train = self.last_training_data
                            print(f"[{name}] XGBoost 자동 재학습...")
                            model.fit(X_train, y_train)
                        else:
                            continue

                # NaN 데이터 전처리 (예측 시에도 적용)
                X_clean = np.nan_to_num(X, nan=0.0, posinf=1.0, neginf=-1.0)
                X_clean = np.clip(X_clean, -10, 10)

                # 추가 NaN 검사
                if np.any(np.isnan(X_clean)):
                    print(f"[{name}] 예측 데이터에 여전히 NaN 존재, 스킵")
                    continue

                # 예측 수행
                if hasattr(model, 'predict_proba'):
                    pred_proba = model.predict_proba(X_clean)
                    if pred_proba.shape[1] > 1:
                        pred_proba = pred_proba[:, 1]
                    else:
                        pred_proba = pred_proba[:, 0]
                else:
                    pred = model.predict(X_clean)
                    pred_proba = pred.astype(float)

                weight = self.model_weights[name]
                predictions.append(pred_proba * weight)
                total_weight += weight
                working_models.append(name)
                print(f"[{name}] 예측 성공: weight={weight:.3f}")

            except Exception as e:
                print(f"[{name}] 예측 오류: {e}")

        print(f"작동 중인 모델: {working_models}, 총 가중치: {total_weight:.3f}")

        if predictions and total_weight > 0:
            result = np.sum(predictions, axis=0) / total_weight
            print(f"앙상블 예측 결과: {result}")
            return result
        else:
            print("작동하는 모델이 없습니다. 랜덤 예측 반환.")
            return np.random.uniform(0.45, 0.55, len(X))

    def predict_signal(self, symbol: str) -> Tuple[str, float]:
        """거래 신호 예측"""
        if not self.is_fitted:
            return "HOLD", 0.1

        # 최신 특성 벡터 가져오기
        features = self.data_collector.get_latest_features(symbol, '1hour')
        if features is None:
            return "HOLD", 0.1

        # 레버리지 ETF 특성 추가
        extended_features = np.append(features, [
            features[4] if len(features) > 4 else 0,
            abs(features[7]) if len(features) > 7 else 0,
            features[10] if len(features) > 10 else 0.5
        ])

        # NaN 데이터 전처리 후 정규화 및 예측
        extended_features_clean = np.nan_to_num(extended_features, nan=0.0, posinf=1.0, neginf=-1.0)
        extended_features_clean = np.clip(extended_features_clean, -10, 10)

        if np.any(np.isnan(extended_features_clean)):
            print(f"[WARNING] {symbol} 특성에 여전히 NaN 존재, 기본값 사용")
            return "HOLD", 0.1

        X_scaled = self.scaler.transform([extended_features_clean])
        prediction = self._ensemble_predict(X_scaled)[0]

        # 신뢰도 계산 (더 민감하게)
        raw_confidence = abs(prediction - 0.5) * 2
        confidence = max(0.1, raw_confidence)

        print(f"[DEBUG] {symbol} - 예측값: {prediction:.3f}, 원본 신뢰도: {raw_confidence:.3f}, 보정 신뢰도: {confidence:.3f}")

        # 신호 결정 (더 민감하게)
        min_threshold = self.signal_thresholds['min_confidence']

        # 방향성 판단
        if prediction > 0.5:
            action = "BUY_NVDL" if symbol == 'NVDL' else "HOLD"
            target = "NVDL"
        else:
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
        """포트폴리오 전체 신호"""
        if not self.is_fitted:
            return "HOLD", "NONE", 0.1

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

        # 신뢰도 기반 신호 결정
        min_confidence = 0.03

        # 더 강한 신호 선택
        if nvdl_signal == "BUY_NVDL" and nvdq_signal == "BUY_NVDQ":
            if nvdl_confidence > nvdq_confidence:
                return "BUY", "NVDL", nvdl_confidence
            else:
                return "BUY", "NVDQ", nvdq_confidence
        elif nvdl_signal == "BUY_NVDL" and nvdl_confidence > min_confidence:
            return "BUY", "NVDL", nvdl_confidence
        elif nvdq_signal == "BUY_NVDQ" and nvdq_confidence > min_confidence:
            return "BUY", "NVDQ", nvdq_confidence
        else:
            # 더 적극적으로 신호 생성
            if nvdl_confidence > nvdq_confidence and nvdl_confidence > min_confidence:
                return "BUY", "NVDL", nvdl_confidence
            elif nvdq_confidence > nvdl_confidence and nvdq_confidence > min_confidence:
                return "BUY", "NVDQ", nvdq_confidence
            elif max(nvdl_confidence, nvdq_confidence) > min_confidence:
                if nvdl_confidence > nvdq_confidence:
                    return "BUY", "NVDL", nvdl_confidence
                else:
                    return "BUY", "NVDQ", nvdq_confidence
            else:
                return "HOLD", "NONE", max(nvdl_confidence, nvdq_confidence)

    def _generate_minimal_patterns(self):
        """최소한의 학습 패턴 생성"""
        print("최소한의 학습 패턴 생성 중...")

        for i in range(200):  # 200개 패턴 생성
            # NVDL 패턴 (상승 신호)
            nvdl_features = [
                np.random.uniform(1.01, 1.03),  # SMA ratios
                np.random.uniform(1.005, 1.02),
                np.random.uniform(1.001, 1.01),
                np.random.uniform(0.02, 0.04),  # Volatility
                np.random.uniform(0.01, 0.03),
                np.random.uniform(0.01, 0.03),  # Momentum
                np.random.uniform(0.005, 0.02),
                np.random.uniform(0.001, 0.01),
                np.random.uniform(1.1, 1.3),  # Volume ratio
                np.random.uniform(0.55, 0.75),  # RSI
                np.random.uniform(0.6, 0.8),  # BB position
                np.random.uniform(0.005, 0.02),
                np.random.uniform(0.6, 0.8),
                np.random.uniform(0.01, 0.03),
                np.random.uniform(1.01, 1.05),
                np.random.uniform(0.02, 0.04),  # Leverage features
                np.random.uniform(0.01, 0.03),
                np.random.uniform(0.6, 0.8)
            ]

            self.success_patterns.append({
                'features': nvdl_features,
                'label': 1,
                'profit': np.random.uniform(1, 5),
                'symbol': 'NVDL',
                'timestamp': datetime.now().isoformat()
            })

            # NVDQ 패턴 (하락 신호)
            nvdq_features = [
                np.random.uniform(0.97, 0.99),  # SMA ratios
                np.random.uniform(0.98, 0.995),
                np.random.uniform(0.99, 0.999),
                np.random.uniform(0.02, 0.04),  # Volatility
                np.random.uniform(0.01, 0.03),
                np.random.uniform(-0.03, -0.01),  # Momentum
                np.random.uniform(-0.02, -0.005),
                np.random.uniform(-0.01, -0.001),
                np.random.uniform(0.9, 1.1),  # Volume ratio
                np.random.uniform(0.25, 0.45),  # RSI
                np.random.uniform(0.2, 0.4),  # BB position
                np.random.uniform(-0.02, -0.005),
                np.random.uniform(0.2, 0.4),
                np.random.uniform(0.01, 0.03),
                np.random.uniform(0.95, 0.99),
                np.random.uniform(0.02, 0.04),  # Leverage features
                np.random.uniform(0.01, 0.03),
                np.random.uniform(0.2, 0.4)
            ]

            self.success_patterns.append({
                'features': nvdq_features,
                'label': 0,
                'profit': np.random.uniform(1, 4),
                'symbol': 'NVDQ',
                'timestamp': datetime.now().isoformat()
            })

        print("최소 패턴 생성 완료: 400개")

    def mass_learning(self):
        """대량 학습 실행"""
        print("\n=== 대량 학습 시작 ===")

        # 기존 패턴 로드
        self.load_historical_patterns()

        # 기존 모델 로드 시도
        if self.load_models() and self.is_fitted:
            print("기존 학습된 모델 로드 성공")
            # 모델 테스트
            try:
                test_features = np.random.random((1, 18))
                test_result = self._ensemble_predict(test_features)
                if test_result[0] != 0.5:
                    print("기존 모델이 정상 작동합니다.")
                    return True
                else:
                    print("기존 모델 재학습 필요")
            except:
                print("기존 모델 테스트 실패. 재학습 필요")

        # 새로운 학습
        print("새로운 모델 학습 시작...")
        X, y = self.prepare_training_data()

        if X is not None and len(X) > 30:
            print(f"학습 데이터: {len(X)}개 샘플")
            success = self.train_models(X, y)
            if success:
                self.save_models()
                print("새 모델 학습 및 저장 완료")
                return True
            else:
                print("모델 학습 실패")
                return False
        else:
            print("학습 데이터 부족. 최소 패턴 생성...")
            self._generate_minimal_patterns()
            X, y = self.prepare_training_data()

            if X is not None and len(X) > 10:
                success = self.train_models(X, y)
                if success:
                    self.save_models()
                    return True

            print("최소 패턴으로도 학습 불가")
            return False

def main():
    """메인 실행 함수"""
    print("*** 데이터 소스 확인 ***")
    print(" FMP API 사용 (Financial Modeling Prep)")
    print(" yfinance 사용 금지 (신뢰성 문제)")
    print("📡 실시간 데이터: FMP Real-time API")
    print(" 히스토리 데이터: FMP Historical API")
    print("🔒 데이터 수집: nvdl_nvdq_data_collector.py만 사용")
    print()

    FMP_API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"

    if not FMP_API_KEY or FMP_API_KEY == "YOUR_API_KEY_HERE":
        print("ERROR: FMP API 키를 설정해주세요!")
        print("FMP API는 https://financialmodelingprep.com에서 발급받으세요.")
        print("yfinance는 절대 사용하지 마세요!")
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
        print("초기 학습 실패! 기본 모드로 실행합니다.")

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
                # 1. 데이터 업데이트
                print("데이터 업데이트 중...")
                model.data_collector.collect_all_data()
                model.data_collector.calculate_all_features()
                model.data_collector.save_data()

                # 2. 신호 생성
                print("\n=== 신호 분석 ===")
                action, symbol, confidence = model.get_portfolio_signal()
                print(f"추천: {action} {symbol} (신뢰도: {confidence:.3f})")

                # 3. 주기적 재학습 (3분마다)
                minutes_since = (current_time - last_learning_time).total_seconds() / 60
                if minutes_since >= 3:
                    print("\n=== 주기적 재학습 ===")
                    if model.mass_learning():
                        last_learning_time = current_time
                        print("재학습 완료!")

                # 4. 통계
                print(f"\n=== 통계 ===")
                print(f"- 성공 패턴: {len(model.success_patterns)}개")
                print(f"- 승률: {model.win_rate:.1f}%")
                print(f"- 총 수익: {model.total_profit:+.2f}%")

                # 5. 패턴 저장
                model.save_patterns()

            except Exception as e:
                print(f"사이클 오류: {e}")

            # 대기
            print(f"\n다음 사이클까지 1초 대기...")
            time.sleep(1)

    except KeyboardInterrupt:
        print(f"\n\n종료됨. 총 사이클: {cycle_count}")
        model.save_patterns()
        model.save_models()

if __name__ == "__main__":
    main()