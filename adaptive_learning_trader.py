#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
적응형 학습 트레이더
- 승리 패턴 강화 학습
- 패배 패턴 회피 학습
- 실시간 거래 결과 반영
"""

import json
import time
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from collections import deque
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# 수정된 모델 임포트
from nvdl_nvdq_trading_model_fixed import NVDLNVDQTradingModel
from nvdl_nvdq_data_collector import NVDLNVDQDataCollector

class AdaptiveLearningTrader(NVDLNVDQTradingModel):
    def __init__(self, fmp_api_key: str):
        """적응형 학습 트레이더 초기화"""
        super().__init__(fmp_api_key)

        print("=== 적응형 학습 트레이더 ===")
        print("✅ 승리 패턴 강화")
        print("❌ 패배 패턴 회피")
        print("🔄 실시간 학습")

        # 패턴 메모리 확장
        self.winning_patterns = deque(maxlen=50000)  # 승리 패턴만
        self.losing_patterns = deque(maxlen=10000)   # 패배 패턴 (적게 보관)

        # 학습 통계
        self.learning_stats = {
            'total_patterns': 0,
            'winning_patterns': 0,
            'losing_patterns': 0,
            'win_rate': 0.0,
            'avg_win_profit': 0.0,
            'avg_loss_amount': 0.0,
            'best_pattern_profit': 0.0,
            'worst_pattern_loss': 0.0
        }

        # 거래 추적
        self.active_trades = {}  # 현재 진행 중인 거래
        self.trade_history = deque(maxlen=1000)  # 거래 이력

        # 학습 파라미터
        self.learning_params = {
            'win_weight_multiplier': 1.5,    # 승리 패턴 가중치 증가율
            'loss_weight_divisor': 2.0,      # 패배 패턴 가중치 감소율
            'min_profit_threshold': 1.0,     # 최소 수익률 (%)
            'max_loss_threshold': -2.0,      # 최대 손실률 (%)
            'pattern_decay_rate': 0.95,      # 패턴 중요도 감소율
            'learning_rate': 0.1              # 학습률
        }

    def record_trade_result(self, trade_id: str, symbol: str,
                           entry_price: float, exit_price: float,
                           features: np.ndarray, entry_time: datetime):
        """거래 결과 기록 및 학습"""

        # 수익률 계산
        profit_pct = (exit_price / entry_price - 1) * 100

        # 레버리지 적용
        if symbol == 'NVDL':
            profit_pct *= 3  # 3x 레버리지
        elif symbol == 'NVDQ':
            profit_pct *= 2  # 2x 레버리지

        # 거래 시간 계산
        holding_time = (datetime.now() - entry_time).total_seconds() / 3600

        # 승리/패배 판단
        is_winning = profit_pct > self.learning_params['min_profit_threshold']
        is_losing = profit_pct < self.learning_params['max_loss_threshold']

        # 패턴 저장
        pattern = {
            'features': features.tolist() if isinstance(features, np.ndarray) else features,
            'label': 1 if symbol == 'NVDL' else 0,
            'profit': profit_pct,
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'holding_time': holding_time,
            'trade_id': trade_id
        }

        if is_winning:
            # 승리 패턴 강화
            self.winning_patterns.append(pattern)
            self.success_patterns.append(pattern)  # 기본 패턴에도 추가

            # 특별히 좋은 수익은 여러 번 저장 (강화)
            if profit_pct > 5.0:  # 5% 이상 수익
                for _ in range(3):  # 3번 반복 저장
                    self.success_patterns.append(pattern)

            # 모델 가중치 증가
            for name in self.model_weights:
                self.model_weights[name] *= self.learning_params['win_weight_multiplier']

            print(f"✅ 승리 패턴 학습: {symbol} +{profit_pct:.2f}% (보유: {holding_time:.1f}시간)")

        elif is_losing:
            # 패배 패턴 저장 (회피 학습용)
            self.losing_patterns.append(pattern)

            # 모델 가중치 감소
            for name in self.model_weights:
                self.model_weights[name] /= self.learning_params['loss_weight_divisor']

            print(f"❌ 패배 패턴 학습: {symbol} {profit_pct:.2f}% (보유: {holding_time:.1f}시간)")

        else:
            # 중립 패턴도 약하게 학습
            if profit_pct > 0:
                self.success_patterns.append(pattern)
                print(f"➖ 중립 패턴 학습: {symbol} +{profit_pct:.2f}%")

        # 통계 업데이트
        self._update_learning_stats(profit_pct, is_winning)

        # 거래 이력 저장
        self.trade_history.append({
            'trade_id': trade_id,
            'symbol': symbol,
            'profit_pct': profit_pct,
            'is_winning': is_winning,
            'holding_time': holding_time,
            'timestamp': datetime.now().isoformat()
        })

        # 즉시 점진적 학습
        if len(self.winning_patterns) > 10:
            self.adaptive_learning()

    def _update_learning_stats(self, profit_pct: float, is_winning: bool):
        """학습 통계 업데이트"""
        self.learning_stats['total_patterns'] += 1

        if is_winning:
            self.learning_stats['winning_patterns'] += 1

            # 평균 수익 업데이트
            current_avg = self.learning_stats['avg_win_profit']
            new_count = self.learning_stats['winning_patterns']
            self.learning_stats['avg_win_profit'] = ((current_avg * (new_count - 1)) + profit_pct) / new_count

            # 최고 수익 업데이트
            if profit_pct > self.learning_stats['best_pattern_profit']:
                self.learning_stats['best_pattern_profit'] = profit_pct
        else:
            self.learning_stats['losing_patterns'] += 1

            # 평균 손실 업데이트
            current_avg = self.learning_stats['avg_loss_amount']
            new_count = self.learning_stats['losing_patterns']
            self.learning_stats['avg_loss_amount'] = ((current_avg * (new_count - 1)) + profit_pct) / new_count

            # 최악 손실 업데이트
            if profit_pct < self.learning_stats['worst_pattern_loss']:
                self.learning_stats['worst_pattern_loss'] = profit_pct

        # 승률 계산
        if self.learning_stats['total_patterns'] > 0:
            self.learning_stats['win_rate'] = (
                self.learning_stats['winning_patterns'] /
                self.learning_stats['total_patterns']
            ) * 100

    def adaptive_learning(self):
        """적응형 점진적 학습"""
        print("🔄 적응형 학습 시작...")

        # 승리 패턴과 패배 패턴 준비
        X_win = []
        y_win = []
        X_lose = []
        y_lose = []

        # 최근 승리 패턴 (더 많이 학습)
        for pattern in list(self.winning_patterns)[-500:]:
            if 'features' in pattern:
                X_win.append(pattern['features'])
                y_win.append(pattern['label'])

        # 최근 패배 패턴 (회피 학습)
        for pattern in list(self.losing_patterns)[-100:]:
            if 'features' in pattern:
                X_lose.append(pattern['features'])
                # 패배 패턴은 반대 라벨로 학습
                y_lose.append(1 - pattern['label'])

        if len(X_win) < 10:
            print("학습할 승리 패턴이 부족합니다.")
            return

        # 데이터 결합 (승리 패턴 비중 높게)
        X_combined = X_win * 3 + X_lose  # 승리 패턴 3배 반복
        y_combined = y_win * 3 + y_lose

        if len(X_combined) < 20:
            return

        X = np.array(X_combined)
        y = np.array(y_combined)

        # 정규화
        try:
            X_scaled = self.scaler.transform(X)
        except:
            X_scaled = self.scaler.fit_transform(X)

        # 각 모델 업데이트
        for name, model in self.models.items():
            try:
                # partial_fit 지원 모델
                if hasattr(model, 'partial_fit'):
                    model.partial_fit(X_scaled, y, classes=[0, 1])
                    print(f"[{name}] 적응형 학습 완료")
                # 일반 모델은 재학습
                elif hasattr(model, 'fit'):
                    # 기존 데이터와 결합하여 재학습
                    if self.last_training_data:
                        X_train, y_train = self.last_training_data
                        X_new = np.vstack([X_train[:100], X_scaled])  # 기존 데이터 일부 + 새 데이터
                        y_new = np.concatenate([y_train[:100], y])
                        model.fit(X_new, y_new)
                        print(f"[{name}] 재학습 완료")
            except Exception as e:
                print(f"[{name}] 학습 오류: {e}")

        print(f"✅ 적응형 학습 완료 - 승률: {self.learning_stats['win_rate']:.1f}%")

    def get_enhanced_signal(self) -> Tuple[str, str, float]:
        """패턴 학습이 강화된 신호 생성"""

        # 기본 신호
        action, symbol, confidence = self.get_portfolio_signal()

        # 최근 패턴과 비교하여 신뢰도 조정
        if len(self.winning_patterns) > 0 and len(self.losing_patterns) > 0:
            # 승률 기반 신뢰도 보정
            win_rate_factor = self.learning_stats['win_rate'] / 100.0

            # 최근 성과 기반 보정
            recent_trades = list(self.trade_history)[-10:]
            if recent_trades:
                recent_wins = sum(1 for t in recent_trades if t['is_winning'])
                recent_win_rate = recent_wins / len(recent_trades)

                # 최근 성과가 좋으면 신뢰도 증가
                if recent_win_rate > 0.6:
                    confidence *= 1.2
                elif recent_win_rate < 0.4:
                    confidence *= 0.8

            # 평균 수익률 기반 보정
            if self.learning_stats['avg_win_profit'] > 3.0:  # 평균 3% 이상 수익
                confidence *= 1.1

            # 최종 신뢰도 조정
            confidence = min(1.0, confidence * (0.5 + win_rate_factor * 0.5))

        return action, symbol, confidence

    def display_learning_status(self):
        """학습 상태 표시"""
        print("\n" + "="*50)
        print("📊 적응형 학습 상태")
        print("="*50)
        print(f"총 패턴 수: {self.learning_stats['total_patterns']}")
        print(f"승리 패턴: {self.learning_stats['winning_patterns']}")
        print(f"패배 패턴: {self.learning_stats['losing_patterns']}")
        print(f"승률: {self.learning_stats['win_rate']:.1f}%")
        print(f"평균 수익: {self.learning_stats['avg_win_profit']:.2f}%")
        print(f"평균 손실: {self.learning_stats['avg_loss_amount']:.2f}%")
        print(f"최고 수익: {self.learning_stats['best_pattern_profit']:.2f}%")
        print(f"최악 손실: {self.learning_stats['worst_pattern_loss']:.2f}%")
        print("="*50)

def main():
    """메인 실행"""
    FMP_API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"

    # 적응형 학습 트레이더 생성
    trader = AdaptiveLearningTrader(FMP_API_KEY)

    # 초기 데이터 수집
    print("초기 데이터 수집 중...")
    if not trader.data_collector.load_data():
        trader.data_collector.collect_all_data()
        trader.data_collector.calculate_all_features()
        trader.data_collector.save_data()

    # 초기 학습
    trader.mass_learning()

    # 가상 거래 시뮬레이션
    print("\n=== 적응형 학습 시작 ===")

    for cycle in range(100):  # 100회 시뮬레이션
        print(f"\n사이클 #{cycle+1}")

        # 신호 생성
        action, symbol, confidence = trader.get_enhanced_signal()
        print(f"신호: {action} {symbol} (신뢰도: {confidence:.3f})")

        # 가상 거래 실행 (시뮬레이션)
        if action == "BUY" and confidence > 0.1:
            # 가상 진입
            entry_price = 100.0
            trade_id = f"trade_{cycle}"

            # 랜덤 결과 생성 (실제로는 시장 데이터 사용)
            # 승률을 학습에 따라 조정
            win_probability = 0.5 + (trader.learning_stats['win_rate'] / 100.0 - 0.5) * 0.3

            if np.random.random() < win_probability:
                # 승리 거래
                exit_price = entry_price * np.random.uniform(1.01, 1.05)
            else:
                # 패배 거래
                exit_price = entry_price * np.random.uniform(0.97, 0.99)

            # 거래 결과 학습
            features = np.random.random(18)  # 실제로는 실제 특성 사용
            trader.record_trade_result(
                trade_id, symbol, entry_price, exit_price,
                features, datetime.now()
            )

        # 주기적 상태 표시
        if cycle % 10 == 9:
            trader.display_learning_status()

        # 주기적 모델 저장
        if cycle % 20 == 19:
            trader.save_models()
            trader.save_patterns()
            print("모델 저장 완료")

        time.sleep(0.1)  # CPU 부하 방지

    # 최종 상태
    trader.display_learning_status()
    print("\n적응형 학습 완료!")

if __name__ == "__main__":
    main()