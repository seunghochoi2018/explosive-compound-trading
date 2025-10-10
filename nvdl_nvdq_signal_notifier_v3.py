#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVDL/NVDQ 텔레그램 신호 알림 시스템 V3
- 실제 역사적 데이터 기반 백테스팅
- 더 공격적인 신호 생성
- 강화된 학습 시스템
"""

import json
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import pickle
import os
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# 자체 모듈 임포트
from nvdl_nvdq_data_collector import NVDLNVDQDataCollector
from nvdl_nvdq_trading_model import NVDLNVDQTradingModel
from telegram_notifier import TelegramNotifier

@dataclass
class TradingSignal:
    """거래 신호 데이터 클래스"""
    timestamp: datetime
    symbol: str
    action: str
    confidence: float
    current_price: float
    target_price: float
    stop_loss: float
    expected_return: float
    holding_period: str
    risk_level: str
    analysis: Dict
    signal_id: str = None

@dataclass
class SignalResult:
    """신호 결과 추적 클래스"""
    signal_id: str
    symbol: str
    action: str
    confidence: float
    entry_price: float
    target_price: float
    stop_loss: float
    timestamp: datetime
    actual_exit_price: float = None
    exit_timestamp: datetime = None
    actual_return: float = None
    success: bool = None
    holding_duration: float = None
    market_features: Dict = None
    outcome: str = None

class NVDLNVDQSignalNotifierV3:
    def __init__(self, fmp_api_key: str):
        """NVDL/NVDQ 신호 알림 시스템 V3 초기화"""
        print("=" * 70)
        print("NVDL/NVDQ 텔레그램 신호 알림 시스템 V3")
        print("실제 역사적 데이터 백테스팅 + 공격적 신호 생성")
        print("=" * 70)

        # 컴포넌트 초기화
        self.data_collector = NVDLNVDQDataCollector(fmp_api_key)
        self.trading_model = NVDLNVDQTradingModel(fmp_api_key)
        self.telegram = TelegramNotifier()

        # 신호 관리
        self.last_signals = {}
        self.signal_history = []
        self.active_signals = {}
        self.signal_results = []
        self.running = False

        # 학습 관리
        self.learning_data_path = Path('signal_learning_data')
        self.learning_data_path.mkdir(exist_ok=True)
        self.load_signal_results()

        # 초고속 학습 설정
        self.learning_config = {
            'min_results_for_learning': 1,     # 1개만 있어도 학습
            'learning_frequency': 0.25,        # 15분마다 재학습
            'success_threshold': 0.5,          # 성공 임계값 낮춤
            'confidence_adjustment_factor': 0.01,
            'incremental_learning_interval': 2,  # 2개마다 즉시 학습
        }

        self.last_learning_time = datetime.now() - timedelta(hours=25)

        # 공격적 신호 설정
        self.config = {
            'check_interval': 60,
            'min_confidence': 0.1,          # 매우 낮은 신뢰도
            'signal_change_threshold': 0.05,
            'max_signals_per_day': 500,
            'detailed_analysis': True,
            'status_update_interval': 43200,
            'aggressive_mode': True,         # 공격적 모드
        }

        # 포지션 추적
        self.current_position = None
        self.last_status_update = datetime.now()
        self.position_entry_time = None
        self.daily_signal_count = 0
        self.last_reset_date = datetime.now().date()

        print(f"시스템 초기화 완료")
        print(f"저장된 신호 결과: {len(self.signal_results)}개")

    def calculate_enhanced_indicators(self, symbol: str) -> Dict:
        """강화된 기술적 지표 계산"""
        try:
            features = self.data_collector.get_latest_features(symbol)
            realtime_data = self.data_collector.realtime_data.get(symbol, {})

            if features is None or not realtime_data:
                return {}

            current_price = realtime_data.get('price', 0)
            price_change_24h = realtime_data.get('changesPercentage', 0)

            indicators = {
                'current_price': current_price,
                'price_change_24h': price_change_24h,
                'rsi': features[9] * 100 if len(features) > 9 else 50,
                'sma_5_ratio': features[0] if len(features) > 0 else 1.0,
                'sma_10_ratio': features[1] if len(features) > 1 else 1.0,
                'sma_20_ratio': features[2] if len(features) > 2 else 1.0,
                'volatility': features[4] if len(features) > 4 else 0.02,
                'momentum_5': features[5] if len(features) > 5 else 0,
                'momentum_10': features[6] if len(features) > 6 else 0,
                'momentum_20': features[7] if len(features) > 7 else 0,
                'volume_ratio': features[8] if len(features) > 8 else 1.0,
                'bollinger_position': features[10] if len(features) > 10 else 0.5,
                'price_position_20': features[12] if len(features) > 12 else 0.5,
            }

            # 추가 강화된 지표들
            indicators['trend_strength'] = abs(indicators['momentum_10'])
            indicators['momentum_divergence'] = abs(indicators['momentum_5'] - indicators['momentum_10'])
            indicators['volatility_level'] = 'HIGH' if indicators['volatility'] > 0.05 else 'MEDIUM' if indicators['volatility'] > 0.02 else 'LOW'
            indicators['rsi_level'] = 'OVERBOUGHT' if indicators['rsi'] > 70 else 'OVERSOLD' if indicators['rsi'] < 30 else 'NORMAL'

            # 가격 모멘텀 계산
            indicators['price_momentum'] = (indicators['sma_5_ratio'] - 1) * 100
            indicators['volume_surge'] = indicators['volume_ratio'] > 1.5

            # 복합 신호 점수
            bull_score = 0
            bear_score = 0

            # RSI 신호
            if indicators['rsi'] < 35:
                bull_score += 2
            elif indicators['rsi'] > 65:
                bear_score += 2

            # 모멘텀 신호
            if indicators['momentum_10'] > 0.01:
                bull_score += 3
            elif indicators['momentum_10'] < -0.01:
                bear_score += 3

            # 가격 위치 신호
            if indicators['price_position_20'] < 0.3:
                bull_score += 2
            elif indicators['price_position_20'] > 0.7:
                bear_score += 2

            # 볼륨 확인
            if indicators['volume_surge']:
                bull_score += 1
                bear_score += 1

            indicators['bull_score'] = bull_score
            indicators['bear_score'] = bear_score
            indicators['signal_strength'] = max(bull_score, bear_score)

            return indicators

        except Exception as e:
            print(f"기술적 지표 계산 오류 ({symbol}): {e}")
            return {}

    def generate_aggressive_signal(self, symbol: str) -> Optional[TradingSignal]:
        """공격적 신호 생성"""
        try:
            # 기존 AI 모델 신호
            action, target_symbol, confidence = self.trading_model.get_portfolio_signal()

            # 강화된 지표 계산
            indicators = self.calculate_enhanced_indicators(symbol)
            if not indicators:
                return None

            current_price = indicators.get('current_price', 0)
            if current_price == 0:
                return None

            # 공격적 신호 로직
            bull_score = indicators.get('bull_score', 0)
            bear_score = indicators.get('bear_score', 0)
            signal_strength = indicators.get('signal_strength', 0)

            # 신호 결정 (더 관대한 기준)
            signal_action = "HOLD"
            signal_confidence = 0.0

            if symbol == "NVDL":
                if bull_score >= 3:  # 강세 신호
                    signal_action = "BUY"
                    signal_confidence = min(0.8, 0.2 + bull_score * 0.1)
                elif bear_score >= 6:  # 매우 강한 약세에서 역매수 고려
                    if indicators.get('rsi', 50) < 25:  # 극도 과매도
                        signal_action = "BUY"
                        signal_confidence = 0.3

            elif symbol == "NVDQ":
                if bear_score >= 3:  # 약세 신호
                    signal_action = "BUY"
                    signal_confidence = min(0.8, 0.2 + bear_score * 0.1)
                elif bull_score >= 6:  # 매우 강한 강세에서 역매수 고려
                    if indicators.get('rsi', 50) > 75:  # 극도 과매수
                        signal_action = "BUY"
                        signal_confidence = 0.3

            # AI 모델 신호와 조합
            if action == "BUY" and target_symbol == symbol:
                signal_confidence = max(signal_confidence, confidence)
                if signal_action == "HOLD":
                    signal_action = "BUY"

            # 최소 신뢰도 체크
            if signal_confidence < self.config['min_confidence']:
                return None

            # 목표가 및 손절가 계산
            target_price, stop_loss = self._calculate_targets(current_price, symbol, indicators)

            # 예상 수익률 계산
            if signal_action == "BUY":
                expected_return = ((target_price / current_price) - 1) * 100
                if symbol == 'NVDL':
                    expected_return *= 3
                elif symbol == 'NVDQ':
                    expected_return *= 2
            else:
                expected_return = 0

            # 보유 기간 예상
            volatility = indicators.get('volatility', 0.02)
            if volatility > 0.05:
                holding_period = "2-8시간"
            elif volatility > 0.03:
                holding_period = "4-16시간"
            else:
                holding_period = "8시간-2일"

            # 위험도 평가
            risk_level = "HIGH" if signal_strength >= 6 else "MEDIUM" if signal_strength >= 3 else "LOW"

            # 고유 신호 ID 생성
            signal_id = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{signal_confidence:.3f}"

            return TradingSignal(
                timestamp=datetime.now(),
                symbol=symbol,
                action=signal_action,
                confidence=signal_confidence,
                current_price=current_price,
                target_price=target_price,
                stop_loss=stop_loss,
                expected_return=expected_return,
                holding_period=holding_period,
                risk_level=risk_level,
                analysis={
                    'bull_score': bull_score,
                    'bear_score': bear_score,
                    'signal_strength': signal_strength,
                    'indicators': indicators
                },
                signal_id=signal_id
            )

        except Exception as e:
            print(f"신호 생성 오류 ({symbol}): {e}")
            return None

    def _calculate_targets(self, current_price: float, symbol: str, indicators: Dict) -> Tuple[float, float]:
        """목표가 및 손절가 계산"""
        volatility = indicators.get('volatility', 0.02)
        signal_strength = indicators.get('signal_strength', 0)

        # 신호 강도에 따른 목표 수익률
        if signal_strength >= 6:
            target_pct = 0.06  # 6%
            stop_pct = 0.025   # 2.5%
        elif signal_strength >= 4:
            target_pct = 0.04  # 4%
            stop_pct = 0.02    # 2%
        else:
            target_pct = 0.025 # 2.5%
            stop_pct = 0.015   # 1.5%

        # 변동성에 따른 조정
        if volatility > 0.05:
            target_pct *= 1.3
            stop_pct *= 1.2
        elif volatility < 0.02:
            target_pct *= 0.8
            stop_pct *= 0.8

        target_price = current_price * (1 + target_pct)
        stop_loss = current_price * (1 - stop_pct)

        return target_price, stop_loss

    def should_send_signal(self, signal: TradingSignal) -> bool:
        """신호 전송 여부 결정"""
        if self.daily_signal_count >= self.config['max_signals_per_day']:
            return False

        if signal.confidence < self.config['min_confidence']:
            return False

        # 포지션 변경 여부 체크
        new_position = signal.symbol if signal.action == "BUY" else None

        # 포지션이 실제로 변경되는 경우만 알림
        if new_position != self.current_position:
            return True

        return False

    def format_signal_message(self, signal: TradingSignal) -> str:
        """신호 메시지 포맷팅"""
        # 이전 포지션 정보
        prev_position = f"이전: {self.current_position}" if self.current_position else "이전: CASH"
        new_position = f"신규: {signal.symbol}" if signal.action == "BUY" else "신규: CASH"
        leverage_text = "3배 레버리지" if signal.symbol == "NVDL" else "2배 역 레버리지"

        # 분석 정보
        analysis = signal.analysis
        bull_score = analysis.get('bull_score', 0)
        bear_score = analysis.get('bear_score', 0)
        signal_strength = analysis.get('signal_strength', 0)

        message_parts = [
            f"**[포지션 변경 알림 V3]**",
            "",
            f"{prev_position} → {new_position}",
            ""
        ]

        if signal.action == "BUY":
            message_parts.extend([
                f"종목: {signal.symbol} ({leverage_text})",
                f"신뢰도: {signal.confidence:.1%}",
                f"현재가: ${signal.current_price:.2f}",
                f"목표가: ${signal.target_price:.2f}",
                f"손절가: ${signal.stop_loss:.2f}",
                f"예상수익: {signal.expected_return:+.1f}%",
                f"예상보유: {signal.holding_period}",
                f"위험도: {signal.risk_level}",
                "",
                f"**신호 분석:**",
                f"강세점수: {bull_score}/10",
                f"약세점수: {bear_score}/10",
                f"신호강도: {signal_strength}/10",
                ""
            ])

        # 시장 상태
        indicators = analysis.get('indicators', {})
        if indicators:
            rsi = indicators.get('rsi', 50)
            momentum = indicators.get('momentum_10', 0)
            vol_level = indicators.get('volatility_level', 'NORMAL')

            message_parts.extend([
                f"**시장 상태:**",
                f"RSI: {rsi:.0f}",
                f"모멘텀: {momentum:+.3f}",
                f"변동성: {vol_level}",
                ""
            ])

        if signal.action == "BUY":
            message_parts.extend([
                "**거래 가이드:**",
                f"1. {signal.symbol} 매수",
                f"2. 목표가 도달 시 익절",
                f"3. 손절가 도달 시 손절",
                ""
            ])

        message_parts.append(f"시간: {signal.timestamp.strftime('%H:%M:%S')}")
        return "\n".join(message_parts)

    def send_signal_notification(self, signal: TradingSignal):
        """신호 알림 전송"""
        try:
            message = self.format_signal_message(signal)
            success = self.telegram.send_message(message)

            if success:
                # 매수 신호인 경우 활성 신호로 추가
                if signal.action == 'BUY':
                    self.add_active_signal(signal)
                    self.position_entry_time = datetime.now()

                self.daily_signal_count += 1
                self.current_position = signal.symbol if signal.action == "BUY" else None

                print(f"V3 신호 전송: {self.current_position if self.current_position else 'CASH'} (신뢰도: {signal.confidence:.1%})")
            else:
                print(f"신호 전송 실패")

        except Exception as e:
            print(f"신호 알림 전송 오류: {e}")

    def add_active_signal(self, signal: TradingSignal):
        """활성 신호 추가"""
        signal_result = SignalResult(
            signal_id=signal.signal_id,
            symbol=signal.symbol,
            action=signal.action,
            confidence=signal.confidence,
            entry_price=signal.current_price,
            target_price=signal.target_price,
            stop_loss=signal.stop_loss,
            timestamp=signal.timestamp,
            market_features=signal.analysis
        )
        self.active_signals[signal.signal_id] = signal_result

    def track_active_signals(self):
        """활성 신호 결과 추적"""
        if not self.active_signals:
            return

        current_time = datetime.now()
        completed_signals = []

        for signal_id, signal_result in self.active_signals.items():
            try:
                current_data = self.data_collector.realtime_data.get(signal_result.symbol, {})
                current_price = current_data.get('price', 0)

                if current_price == 0:
                    continue

                hours_elapsed = (current_time - signal_result.timestamp).total_seconds() / 3600

                # 24시간 후 자동 종료 (더 빠른 학습을 위해)
                if hours_elapsed > 24:
                    signal_result.actual_exit_price = current_price
                    signal_result.exit_timestamp = current_time
                    signal_result.holding_duration = hours_elapsed
                    signal_result.actual_return = ((current_price / signal_result.entry_price) - 1) * 100
                    signal_result.outcome = 'TIME_EXIT'
                    signal_result.success = signal_result.actual_return > 0
                    completed_signals.append(signal_id)
                    continue

                # 목표가 도달 체크
                if current_price >= signal_result.target_price:
                    signal_result.actual_exit_price = signal_result.target_price
                    signal_result.exit_timestamp = current_time
                    signal_result.holding_duration = hours_elapsed
                    signal_result.actual_return = ((signal_result.target_price / signal_result.entry_price) - 1) * 100
                    signal_result.outcome = 'TARGET_HIT'
                    signal_result.success = True
                    completed_signals.append(signal_id)
                    continue

                # 손절가 도달 체크
                if current_price <= signal_result.stop_loss:
                    signal_result.actual_exit_price = signal_result.stop_loss
                    signal_result.exit_timestamp = current_time
                    signal_result.holding_duration = hours_elapsed
                    signal_result.actual_return = ((signal_result.stop_loss / signal_result.entry_price) - 1) * 100
                    signal_result.outcome = 'STOP_LOSS'
                    signal_result.success = False
                    completed_signals.append(signal_id)
                    continue

            except Exception as e:
                print(f"신호 추적 오류 ({signal_id}): {e}")

        # 완료된 신호 처리
        for signal_id in completed_signals:
            completed_signal = self.active_signals.pop(signal_id)
            self.signal_results.append(completed_signal)
            print(f"신호 완료: {completed_signal.symbol} ({completed_signal.outcome}) 수익률: {completed_signal.actual_return:+.2f}%")

            # 즉시 저장 및 학습
            self.save_signal_results()

            # 2개마다 즉시 학습
            if len(self.signal_results) % self.learning_config['incremental_learning_interval'] == 0:
                print("즉시 학습 수행...")
                self.perform_signal_based_learning()

    def perform_signal_based_learning(self):
        """신호 결과 기반 학습 수행"""
        try:
            if len(self.signal_results) < self.learning_config['min_results_for_learning']:
                return

            successful_signals = [r for r in self.signal_results if r.success]

            if len(self.signal_results) > 0:
                success_rate = len(successful_signals) / len(self.signal_results)
                print(f"현재 성공률: {success_rate:.1%} ({len(successful_signals)}/{len(self.signal_results)})")

            # 성공 패턴을 모델에 추가
            for signal in successful_signals[-5:]:  # 최근 5개
                if signal.market_features:
                    pattern_features = self.extract_pattern_features(signal)
                    self.trading_model.add_successful_pattern(pattern_features, signal.actual_return)

            print("학습 완료!")

        except Exception as e:
            print(f"학습 수행 오류: {e}")

    def extract_pattern_features(self, signal: SignalResult) -> Dict:
        """신호에서 패턴 특징 추출"""
        try:
            market_features = signal.market_features or {}
            indicators = market_features.get('indicators', {})

            pattern = {
                'symbol': signal.symbol,
                'confidence': signal.confidence,
                'bull_score': market_features.get('bull_score', 0),
                'bear_score': market_features.get('bear_score', 0),
                'signal_strength': market_features.get('signal_strength', 0),
                'rsi': indicators.get('rsi', 50),
                'momentum_10': indicators.get('momentum_10', 0),
                'volatility': indicators.get('volatility', 0.02),
                'outcome': signal.outcome,
                'actual_return': signal.actual_return,
                'holding_duration': signal.holding_duration
            }

            return pattern

        except Exception as e:
            print(f"패턴 특징 추출 오류: {e}")
            return {}

    def check_and_perform_learning(self):
        """학습 필요성 체크 및 실행"""
        current_time = datetime.now()
        hours_since_last_learning = (current_time - self.last_learning_time).total_seconds() / 3600

        # 15분마다 학습
        if (hours_since_last_learning >= self.learning_config['learning_frequency'] and
            len(self.signal_results) >= self.learning_config['min_results_for_learning']):

            print("정기 학습 수행...")
            self.perform_signal_based_learning()
            self.last_learning_time = current_time

    def load_signal_results(self):
        """저장된 신호 결과 로드"""
        try:
            results_file = self.learning_data_path / 'signal_results_v3.pkl'
            if results_file.exists():
                with open(results_file, 'rb') as f:
                    self.signal_results = pickle.load(f)
                print(f"{len(self.signal_results)}개 신호 결과 로드 완료")
            else:
                self.signal_results = []
        except Exception as e:
            print(f"신호 결과 로드 실패: {e}")
            self.signal_results = []

    def save_signal_results(self):
        """신호 결과 저장"""
        try:
            results_file = self.learning_data_path / 'signal_results_v3.pkl'
            with open(results_file, 'wb') as f:
                pickle.dump(self.signal_results, f)
        except Exception as e:
            print(f"신호 결과 저장 실패: {e}")

    def send_status_update(self):
        """12시간마다 정기 상태 업데이트"""
        try:
            # 현재 포지션 정보
            if self.current_position:
                position_msg = f"현재 포지션: {self.current_position}"
                if self.position_entry_time:
                    holding_hours = (datetime.now() - self.position_entry_time).total_seconds() / 3600
                    position_msg += f" ({holding_hours:.1f}시간 보유중)"
            else:
                position_msg = "현재 포지션: CASH"

            # 성과 요약
            if len(self.signal_results) > 0:
                success_rate = sum(1 for r in self.signal_results if r.success) / len(self.signal_results)
                avg_return = np.mean([r.actual_return for r in self.signal_results if r.actual_return is not None])
                recent_results = self.signal_results[-10:]
                recent_success = sum(1 for r in recent_results if r.success) / len(recent_results) if recent_results else 0
                perf_msg = f"전체: {success_rate:.1%} (평균 {avg_return:+.2f}%)\n최근 10개: {recent_success:.1%}"
            else:
                perf_msg = "아직 거래 결과 없음"

            # 시장 상태
            nvdl_indicators = self.calculate_enhanced_indicators('NVDL')
            nvdq_indicators = self.calculate_enhanced_indicators('NVDQ')

            market_msg = ""
            if nvdl_indicators:
                market_msg += f"\nNVDL: ${nvdl_indicators.get('current_price', 0):.2f}"
                market_msg += f" 강세점수:{nvdl_indicators.get('bull_score', 0)}"

            if nvdq_indicators:
                market_msg += f"\nNVDQ: ${nvdq_indicators.get('current_price', 0):.2f}"
                market_msg += f" 약세점수:{nvdq_indicators.get('bear_score', 0)}"

            message = f"""**[V3 12시간 업데이트]**

{position_msg}

**성과 현황:**
{perf_msg}

**시장 신호:**{market_msg}

**학습 상태:**
총 학습 데이터: {len(self.signal_results)}개
마지막 학습: {(datetime.now() - self.last_learning_time).total_seconds() / 3600:.1f}시간 전

다음 업데이트: 12시간 후
            """.strip()

            self.telegram.send_message(message)
            self.last_status_update = datetime.now()

        except Exception as e:
            print(f"상태 업데이트 전송 오류: {e}")

    def reset_daily_counter(self):
        """일일 카운터 리셋"""
        today = datetime.now().date()
        if today > self.last_reset_date:
            self.daily_signal_count = 0
            self.last_reset_date = today

    def run_signal_monitor(self):
        """신호 모니터링 실행"""
        print("\nV3 신호 모니터링 시작")

        # 시작 알림
        start_message = f"""**[NVDL/NVDQ V3 시작]**

공격적 신호 생성 모드
최소 신뢰도: {self.config['min_confidence']:.0%}
학습 주기: 15분마다
즉시 학습: 2개 결과마다

강화된 신호 분석:
- 강세/약세 점수 기반
- 복합 지표 활용
- 빠른 학습 및 개선

시작: {datetime.now().strftime('%H:%M:%S')}
        """.strip()

        self.telegram.send_message(start_message)
        self.running = True

        try:
            while self.running:
                # 일일 카운터 리셋
                self.reset_daily_counter()

                # 활성 신호 추적
                self.track_active_signals()

                # 학습 체크
                self.check_and_perform_learning()

                # 최신 데이터 업데이트
                for symbol in ['NVDL', 'NVDQ']:
                    realtime_data = self.data_collector.fetch_realtime_data(symbol)
                    if realtime_data:
                        self.data_collector.realtime_data[symbol] = realtime_data

                # 최고 신뢰도 신호 찾기
                best_signal = None
                best_confidence = 0

                for symbol in ['NVDL', 'NVDQ']:
                    signal = self.generate_aggressive_signal(symbol)

                    if signal and signal.action == "BUY" and signal.confidence > best_confidence:
                        best_signal = signal
                        best_confidence = signal.confidence

                # 포지션 변경이 필요한 경우만 알림
                if best_signal and self.should_send_signal(best_signal):
                    self.send_signal_notification(best_signal)
                elif best_signal:
                    print(f"신호 감지: {best_signal.symbol} (신뢰도: {best_signal.confidence:.1%}) - 포지션 변경 없음")

                # 12시간마다 상태 업데이트
                if (datetime.now() - self.last_status_update).total_seconds() > self.config['status_update_interval']:
                    self.send_status_update()

                # 대기
                time.sleep(self.config['check_interval'])

        except KeyboardInterrupt:
            print("\n사용자에 의한 중단")
        except Exception as e:
            print(f"\n시스템 오류: {e}")
        finally:
            self.running = False
            self.save_signal_results()
            self.telegram.send_message("**[V3 시스템 종료]**")
            print("V3 신호 모니터링 종료")

    def run(self):
        """메인 실행 함수"""
        print("V3 시스템 준비 중...")

        # 데이터 수집 및 로드
        if not self.data_collector.load_data():
            print("새로운 데이터 수집 중...")
            self.data_collector.collect_all_data()
            self.data_collector.calculate_all_features()
            self.data_collector.save_data()

        # 모델 학습
        if not self.trading_model.mass_learning():
            print("모델 학습 실패")
            return

        print("V3 시스템 준비 완료!")
        self.run_signal_monitor()

def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="NVDL/NVDQ V3 신호 알림 시스템")
    parser.add_argument('--api-key', type=str,
                       default="5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI",
                       help='FMP API 키')
    parser.add_argument('--interval', type=int, default=1,
                       help='체크 간격 (분)')

    args = parser.parse_args()

    # V3 시스템 생성
    notifier = NVDLNVDQSignalNotifierV3(args.api_key)
    notifier.config['check_interval'] = args.interval * 60

    # 실행
    notifier.run()

if __name__ == "__main__":
    main()