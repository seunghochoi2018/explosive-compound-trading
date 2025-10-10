#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVDL/NVDQ 텔레그램 신호 알림 전용 프로그램
- 자동매매 없이 신호만 알림
- 상세한 분석 정보 제공
- 수동 거래를 위한 완벽한 가이드
"""

import json
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
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
    symbol: str                    # 'NVDL' or 'NVDQ'
    action: str                    # 'BUY', 'SELL', 'HOLD'
    confidence: float              # 0.0 ~ 1.0
    current_price: float
    target_price: float            # 목표가
    stop_loss: float              # 손절가
    expected_return: float         # 예상 수익률 (%)
    holding_period: str           # 예상 보유 기간
    risk_level: str               # 'LOW', 'MEDIUM', 'HIGH'
    analysis: Dict                # 상세 분석 정보
    signal_id: str = None         # 고유 신호 ID

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

    # 결과 데이터
    actual_exit_price: float = None
    exit_timestamp: datetime = None
    actual_return: float = None
    success: bool = None
    holding_duration: float = None  # 시간 (hours)

    # 학습용 피처
    market_features: Dict = None
    outcome: str = None  # 'TARGET_HIT', 'STOP_LOSS', 'TIME_EXIT', 'USER_EXIT'

class NVDLNVDQSignalNotifier:
    def __init__(self, fmp_api_key: str):
        """
        NVDL/NVDQ 신호 알림 시스템 초기화

        Args:
            fmp_api_key: Financial Modeling Prep API 키
        """
        print("=" * 70)
        print("NVDL/NVDQ 텔레그램 신호 알림 시스템")
        print("수동 거래용 상세 신호 제공")
        print("자동매매 없이 신호만 알림")
        print("=" * 70)

        # 컴포넌트 초기화
        self.data_collector = NVDLNVDQDataCollector(fmp_api_key)
        self.trading_model = NVDLNVDQTradingModel(fmp_api_key)
        self.telegram = TelegramNotifier()

        # 신호 관리
        self.last_signals = {}  # 마지막 신호 기록
        self.signal_history = []  # 신호 히스토리
        self.active_signals = {}  # 활성 신호 추적
        self.signal_results = []  # 신호 결과 기록
        self.running = False

        # 학습 관리
        self.learning_data_path = Path('signal_learning_data')
        self.learning_data_path.mkdir(exist_ok=True)
        self.load_signal_results()

        # 학습 설정 - 최대 속도로 학습
        self.learning_config = {
            'min_results_for_learning': 2,     # 최소 학습 데이터 수 (매우 낮춤)
            'learning_frequency': 0.5,          # 30분마다 재학습 (매우 빈번)
            'success_threshold': 0.6,          # 성공 임계값
            'confidence_adjustment_factor': 0.02, # 신뢰도 조정 비율 (미세조정)
            'incremental_learning_interval': 3,  # 3개 신호마다 즉시 학습
        }

        self.last_learning_time = datetime.now() - timedelta(hours=25)

        # 설정
        self.config = {
            'check_interval': 300,          # 5분마다 체크
            'min_confidence': 0.3,          # 최소 신뢰도
            'signal_change_threshold': 0.1,  # 신호 변경 임계값
            'max_signals_per_day': 20,      # 일일 최대 신호 수
            'detailed_analysis': True,       # 상세 분석 포함
        }

        # 신호 카운터
        self.daily_signal_count = 0
        self.last_reset_date = datetime.now().date()

        print("신호 알림 시스템 초기화 완료")
        print(f"저장된 신호 결과: {len(self.signal_results)}개")

        # 학습 데이터 상태 출력
        if len(self.signal_results) >= self.learning_config['min_results_for_learning']:
            success_rate = sum(1 for r in self.signal_results if r.success) / len(self.signal_results)
            print(f"현재 성공률: {success_rate:.1%}")

    def calculate_technical_indicators(self, symbol: str) -> Dict:
        """기술적 지표 계산"""
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

            # 추가 계산
            indicators['trend_strength'] = abs(indicators['momentum_10'])
            indicators['volatility_level'] = 'HIGH' if indicators['volatility'] > 0.05 else 'MEDIUM' if indicators['volatility'] > 0.02 else 'LOW'
            indicators['rsi_level'] = 'OVERBOUGHT' if indicators['rsi'] > 70 else 'OVERSOLD' if indicators['rsi'] < 30 else 'NORMAL'

            return indicators

        except Exception as e:
            print(f"기술적 지표 계산 오류 ({symbol}): {e}")
            return {}

    def analyze_market_condition(self, symbol: str) -> Dict:
        """시장 상황 분석"""
        indicators = self.calculate_technical_indicators(symbol)
        if not indicators:
            return {}

        analysis = {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'price_trend': self._analyze_price_trend(indicators),
            'momentum_analysis': self._analyze_momentum(indicators),
            'volatility_analysis': self._analyze_volatility(indicators),
            'support_resistance': self._find_support_resistance(indicators),
            'market_sentiment': self._analyze_sentiment(indicators),
            'risk_assessment': self._assess_risk(indicators)
        }

        return analysis

    def _analyze_price_trend(self, indicators: Dict) -> Dict:
        """가격 트렌드 분석"""
        sma_5 = indicators.get('sma_5_ratio', 1.0)
        sma_10 = indicators.get('sma_10_ratio', 1.0)
        sma_20 = indicators.get('sma_20_ratio', 1.0)

        if sma_5 > 1.02 and sma_10 > 1.01 and sma_20 > 1.005:
            trend = 'STRONG_UPTREND'
            strength = 'STRONG'
        elif sma_5 > 1.01 and sma_10 > 1.005:
            trend = 'UPTREND'
            strength = 'MEDIUM'
        elif sma_5 < 0.98 and sma_10 < 0.99 and sma_20 < 0.995:
            trend = 'STRONG_DOWNTREND'
            strength = 'STRONG'
        elif sma_5 < 0.99 and sma_10 < 0.995:
            trend = 'DOWNTREND'
            strength = 'MEDIUM'
        else:
            trend = 'SIDEWAYS'
            strength = 'WEAK'

        return {
            'trend': trend,
            'strength': strength,
            'sma_alignment': sma_5 > sma_10 > sma_20,
            'short_term_momentum': sma_5 - 1.0,
            'medium_term_momentum': sma_10 - 1.0
        }

    def _analyze_momentum(self, indicators: Dict) -> Dict:
        """모멘텀 분석"""
        mom_5 = indicators.get('momentum_5', 0)
        mom_10 = indicators.get('momentum_10', 0)
        mom_20 = indicators.get('momentum_20', 0)

        momentum_strength = (abs(mom_5) + abs(mom_10) + abs(mom_20)) / 3

        if momentum_strength > 0.05:
            strength = 'STRONG'
        elif momentum_strength > 0.02:
            strength = 'MEDIUM'
        else:
            strength = 'WEAK'

        direction = 'BULLISH' if (mom_5 + mom_10 + mom_20) > 0 else 'BEARISH'

        return {
            'direction': direction,
            'strength': strength,
            'short_term': mom_5,
            'medium_term': mom_10,
            'long_term': mom_20,
            'divergence': abs(mom_5 - mom_10) > 0.03
        }

    def _analyze_volatility(self, indicators: Dict) -> Dict:
        """변동성 분석"""
        volatility = indicators.get('volatility', 0.02)
        bollinger_pos = indicators.get('bollinger_position', 0.5)

        if volatility > 0.06:
            level = 'EXTREME'
            recommendation = '매우 주의'
        elif volatility > 0.04:
            level = 'HIGH'
            recommendation = '주의 필요'
        elif volatility > 0.02:
            level = 'NORMAL'
            recommendation = '정상 범위'
        else:
            level = 'LOW'
            recommendation = '안정적'

        return {
            'level': level,
            'value': volatility,
            'recommendation': recommendation,
            'bollinger_position': bollinger_pos,
            'squeeze': volatility < 0.015,  # 낮은 변동성 = 돌파 가능성
        }

    def _find_support_resistance(self, indicators: Dict) -> Dict:
        """지지/저항선 분석"""
        current_price = indicators.get('current_price', 0)
        price_position = indicators.get('price_position_20', 0.5)

        # 간단한 지지/저항선 계산
        resistance = current_price * (1 + (1 - price_position) * 0.05)
        support = current_price * (1 - price_position * 0.05)

        return {
            'support': support,
            'resistance': resistance,
            'price_position': price_position,
            'near_resistance': price_position > 0.8,
            'near_support': price_position < 0.2,
        }

    def _analyze_sentiment(self, indicators: Dict) -> Dict:
        """시장 심리 분석"""
        rsi = indicators.get('rsi', 50)
        price_change = indicators.get('price_change_24h', 0)
        volume_ratio = indicators.get('volume_ratio', 1.0)

        if rsi > 70 and price_change > 3:
            sentiment = 'EUPHORIC'
            warning = '과매수 경고'
        elif rsi > 60 and price_change > 1:
            sentiment = 'BULLISH'
            warning = '상승 심리'
        elif rsi < 30 and price_change < -3:
            sentiment = 'PANIC'
            warning = '과매도 상태'
        elif rsi < 40 and price_change < -1:
            sentiment = 'BEARISH'
            warning = '하락 심리'
        else:
            sentiment = 'NEUTRAL'
            warning = '중립 상태'

        return {
            'sentiment': sentiment,
            'warning': warning,
            'rsi': rsi,
            'volume_confirmation': volume_ratio > 1.2,
        }

    def _assess_risk(self, indicators: Dict) -> Dict:
        """위험도 평가"""
        volatility = indicators.get('volatility', 0.02)
        trend_strength = indicators.get('trend_strength', 0)
        rsi = indicators.get('rsi', 50)

        # 위험 점수 계산 (0-100)
        risk_score = 0

        # 변동성 위험
        if volatility > 0.05:
            risk_score += 30
        elif volatility > 0.03:
            risk_score += 15

        # RSI 위험
        if rsi > 75 or rsi < 25:
            risk_score += 25
        elif rsi > 65 or rsi < 35:
            risk_score += 10

        # 트렌드 불확실성
        if trend_strength < 0.01:
            risk_score += 20

        if risk_score > 60:
            level = 'HIGH'
            recommendation = '신중한 접근 필요'
        elif risk_score > 30:
            level = 'MEDIUM'
            recommendation = '적정 위험 수준'
        else:
            level = 'LOW'
            recommendation = '안정적 투자 환경'

        return {
            'level': level,
            'score': risk_score,
            'recommendation': recommendation,
            'factors': self._identify_risk_factors(indicators)
        }

    def _identify_risk_factors(self, indicators: Dict) -> List[str]:
        """위험 요소 식별"""
        factors = []

        if indicators.get('volatility', 0) > 0.05:
            factors.append('높은 변동성')

        rsi = indicators.get('rsi', 50)
        if rsi > 75:
            factors.append('과매수 상태')
        elif rsi < 25:
            factors.append('과매도 상태')

        if indicators.get('volume_ratio', 1.0) < 0.5:
            factors.append('낮은 거래량')

        if indicators.get('trend_strength', 0) < 0.005:
            factors.append('불분명한 방향성')

        return factors

    def generate_trading_signal(self, symbol: str) -> Optional[TradingSignal]:
        """거래 신호 생성"""
        try:
            # AI 모델 신호
            action, _, confidence = self.trading_model.get_portfolio_signal()

            # 시장 분석
            analysis = self.analyze_market_condition(symbol)
            if not analysis:
                return None

            indicators = self.calculate_technical_indicators(symbol)
            current_price = indicators.get('current_price', 0)

            if current_price == 0:
                return None

            # 신호 결정
            if action == "BUY" and symbol == "NVDL":
                signal_action = "BUY"
            elif action == "BUY" and symbol == "NVDQ":
                signal_action = "BUY"
            else:
                signal_action = "HOLD"

            # 목표가 및 손절가 계산
            target_price, stop_loss = self._calculate_targets(current_price, symbol, analysis)

            # 예상 수익률 계산
            if signal_action == "BUY":
                expected_return = ((target_price / current_price) - 1) * 100
                if symbol == 'NVDL':
                    expected_return *= 3  # 3x 레버리지
                elif symbol == 'NVDQ':
                    expected_return *= 2  # 2x 레버리지
            else:
                expected_return = 0

            # 보유 기간 예상
            volatility = indicators.get('volatility', 0.02)
            if volatility > 0.05:
                holding_period = "4-12시간"
            elif volatility > 0.03:
                holding_period = "8-24시간"
            else:
                holding_period = "1-3일"

            # 위험도 평가
            risk_assessment = analysis.get('risk_assessment', {})
            risk_level = risk_assessment.get('level', 'MEDIUM')

            # 고유 신호 ID 생성
            signal_id = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{confidence:.3f}"

            return TradingSignal(
                timestamp=datetime.now(),
                symbol=symbol,
                action=signal_action,
                confidence=confidence,
                current_price=current_price,
                target_price=target_price,
                stop_loss=stop_loss,
                expected_return=expected_return,
                holding_period=holding_period,
                risk_level=risk_level,
                analysis=analysis,
                signal_id=signal_id
            )

        except Exception as e:
            print(f"신호 생성 오류 ({symbol}): {e}")
            return None

    def _calculate_targets(self, current_price: float, symbol: str, analysis: Dict) -> Tuple[float, float]:
        """목표가 및 손절가 계산"""
        volatility = analysis.get('volatility_analysis', {}).get('value', 0.02)
        trend_strength = analysis.get('momentum_analysis', {}).get('strength', 'MEDIUM')

        # 기본 목표 수익률 설정
        if trend_strength == 'STRONG':
            target_pct = 0.05  # 5%
            stop_pct = 0.02    # 2%
        elif trend_strength == 'MEDIUM':
            target_pct = 0.03  # 3%
            stop_pct = 0.015   # 1.5%
        else:
            target_pct = 0.02  # 2%
            stop_pct = 0.01    # 1%

        # 변동성에 따른 조정
        if volatility > 0.05:
            target_pct *= 1.5
            stop_pct *= 1.3
        elif volatility < 0.02:
            target_pct *= 0.8
            stop_pct *= 0.8

        target_price = current_price * (1 + target_pct)
        stop_loss = current_price * (1 - stop_pct)

        return target_price, stop_loss

    def should_send_signal(self, signal: TradingSignal) -> bool:
        """신호 전송 여부 결정"""
        # 일일 신호 수 제한
        if self.daily_signal_count >= self.config['max_signals_per_day']:
            return False

        # 최소 신뢰도 체크
        if signal.confidence < self.config['min_confidence']:
            return False

        # 이전 신호와 비교
        last_signal = self.last_signals.get(signal.symbol)
        if last_signal:
            # 같은 신호면 전송하지 않음
            if (last_signal['action'] == signal.action and
                abs(last_signal['confidence'] - signal.confidence) < self.config['signal_change_threshold']):
                return False

            # 시간 간격 체크 (최소 10분)
            time_diff = (signal.timestamp - last_signal['timestamp']).total_seconds()
            if time_diff < 600:  # 10분
                return False

        return True

    def format_signal_message(self, signal: TradingSignal) -> str:
        """신호 메시지 포맷팅"""
        emoji_map = {
            'NVDL': '📈',
            'NVDQ': '📉',
            'BUY': '🟢',
            'SELL': '🔴',
            'HOLD': '🟡'
        }

        risk_emoji = {
            'LOW': '🟢',
            'MEDIUM': '🟡',
            'HIGH': '🔴'
        }

        # 기본 신호 정보
        message_parts = [
            f"{emoji_map.get(signal.action, '🔸')} **거래 신호 발생**",
            "",
            f"🎯 **종목**: {signal.symbol} {emoji_map.get(signal.symbol, '')}",
            f"📊 **액션**: {signal.action}",
            f"💪 **신뢰도**: {signal.confidence:.1%}",
            f"💰 **현재가**: ${signal.current_price:.2f}",
            ""
        ]

        # 거래 정보 (매수 신호일 때만)
        if signal.action == "BUY":
            leverage_text = "3배 레버리지" if signal.symbol == "NVDL" else "2배 역 레버리지"
            message_parts.extend([
                f"🎯 **목표가**: ${signal.target_price:.2f}",
                f"🛡️ **손절가**: ${signal.stop_loss:.2f}",
                f"📈 **예상수익**: {signal.expected_return:+.1f}% ({leverage_text})",
                f"⏰ **예상보유**: {signal.holding_period}",
                f"{risk_emoji.get(signal.risk_level, '🟡')} **위험도**: {signal.risk_level}",
                ""
            ])

        # 상세 분석
        analysis = signal.analysis
        if analysis:
            message_parts.extend([
                "📊 **시장 분석**:",
                ""
            ])

            # 트렌드 분석
            trend_analysis = analysis.get('price_trend', {})
            trend = trend_analysis.get('trend', 'UNKNOWN')
            strength = trend_analysis.get('strength', 'UNKNOWN')
            message_parts.append(f"📈 트렌드: {trend} ({strength})")

            # 모멘텀 분석
            momentum_analysis = analysis.get('momentum_analysis', {})
            direction = momentum_analysis.get('direction', 'UNKNOWN')
            mom_strength = momentum_analysis.get('strength', 'UNKNOWN')
            message_parts.append(f"⚡ 모멘텀: {direction} ({mom_strength})")

            # 기술적 지표
            sentiment = analysis.get('market_sentiment', {})
            rsi = sentiment.get('rsi', 50)
            sentiment_text = sentiment.get('sentiment', 'NEUTRAL')
            message_parts.append(f"📊 RSI: {rsi:.0f} ({sentiment_text})")

            # 변동성
            volatility_analysis = analysis.get('volatility_analysis', {})
            vol_level = volatility_analysis.get('level', 'NORMAL')
            vol_rec = volatility_analysis.get('recommendation', '정상')
            message_parts.append(f"📊 변동성: {vol_level} ({vol_rec})")

            message_parts.append("")

            # 위험 요소
            risk_factors = analysis.get('risk_assessment', {}).get('factors', [])
            if risk_factors:
                message_parts.append("⚠️ **주의사항**:")
                for factor in risk_factors:
                    message_parts.append(f"• {factor}")
                message_parts.append("")

        # 거래 가이드
        if signal.action == "BUY":
            message_parts.extend([
                "💡 **거래 가이드**:",
                f"1️⃣ {signal.symbol} 시장가 매수",
                f"2️⃣ 목표가 ${signal.target_price:.2f}에서 익절",
                f"3️⃣ 손절가 ${signal.stop_loss:.2f}에서 손절",
                f"4️⃣ 최대 보유기간: {signal.holding_period}",
                ""
            ])

        message_parts.extend([
            f"⏰ **발신시간**: {signal.timestamp.strftime('%H:%M:%S')}",
            "",
            "📝 *이 신호는 참고용이며, 투자 책임은 본인에게 있습니다.*"
        ])

        return "\n".join(message_parts)

    def send_signal_notification(self, signal: TradingSignal):
        """신호 알림 전송"""
        try:
            message = self.format_signal_message(signal)
            success = self.telegram.send_message(message)

            if success:
                # 신호 기록 업데이트
                self.last_signals[signal.symbol] = {
                    'action': signal.action,
                    'confidence': signal.confidence,
                    'timestamp': signal.timestamp
                }

                # 신호 히스토리 저장
                self.signal_history.append({
                    'timestamp': signal.timestamp.isoformat(),
                    'symbol': signal.symbol,
                    'action': signal.action,
                    'confidence': signal.confidence,
                    'current_price': signal.current_price,
                    'expected_return': signal.expected_return
                })

                # 매수 신호인 경우 활성 신호로 추가
                if signal.action == 'BUY':
                    self.add_active_signal(signal)

                # 카운터 증가
                self.daily_signal_count += 1

                print(f"✅ {signal.symbol} 신호 전송 완료: {signal.action} (신뢰도: {signal.confidence:.1%})")
            else:
                print(f"❌ {signal.symbol} 신호 전송 실패")

        except Exception as e:
            print(f"신호 알림 전송 오류: {e}")

    def reset_daily_counter(self):
        """일일 카운터 리셋"""
        today = datetime.now().date()
        if today > self.last_reset_date:
            self.daily_signal_count = 0
            self.last_reset_date = today
            print(f"일일 신호 카운터 리셋: {today}")

    def run_signal_monitor(self):
        """신호 모니터링 실행"""
        print("\n📡 신호 모니터링 시작")

        # 시작 알림
        start_message = f"""
📡 **NVDL/NVDQ 신호 알림 시작**

🎯 **모니터링 대상**: NVDL, NVDQ
⏰ **체크 간격**: {self.config['check_interval']//60}분
📊 **최소 신뢰도**: {self.config['min_confidence']:.0%}
📱 **일일 최대 신호**: {self.config['max_signals_per_day']}개
🧠 **학습 기능**: 활성화 (신호 결과 추적)

💡 **신호 해석**:
- 🟢 BUY: 해당 종목 매수 추천
- 🟡 HOLD: 현재 보유 유지 또는 관망
- 📈 NVDL: 3x 레버리지 NVIDIA ETF (상승 시 수익)
- 📉 NVDQ: 2x 역 레버리지 NASDAQ ETF (하락 시 수익)

⏰ **시작**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔔 실시간 신호를 받아보세요!
        """.strip()

        self.telegram.send_message(start_message)

        self.running = True

        try:
            while self.running:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 신호 체크 시작")

                # 일일 카운터 리셋 체크
                self.reset_daily_counter()

                # 활성 신호 결과 추적
                self.track_active_signals()

                # 학습 체크 (24시간마다)
                self.check_and_perform_learning()

                # 최신 데이터 업데이트
                for symbol in ['NVDL', 'NVDQ']:
                    realtime_data = self.data_collector.fetch_realtime_data(symbol)
                    if realtime_data:
                        self.data_collector.realtime_data[symbol] = realtime_data

                # 각 종목 신호 체크
                for symbol in ['NVDL', 'NVDQ']:
                    signal = self.generate_trading_signal(symbol)

                    if signal and self.should_send_signal(signal):
                        self.send_signal_notification(signal)

                # 상태 출력
                print(f"일일 신호 수: {self.daily_signal_count}/{self.config['max_signals_per_day']}")
                print(f"활성 신호: {len(self.active_signals)}개")
                print(f"총 결과 수: {len(self.signal_results)}개")

                # 대기
                print(f"다음 체크까지 {self.config['check_interval']//60}분 대기...")
                time.sleep(self.config['check_interval'])

        except KeyboardInterrupt:
            print("\n⏹️ 사용자에 의한 중단")
        except Exception as e:
            print(f"\n❌ 시스템 오류: {e}")
            self.telegram.notify_error("신호 모니터링 시스템 오류", str(e))
        finally:
            self.running = False
            self.save_signal_results()
            self.telegram.send_message("⏹️ **신호 알림 중단**\n\n시스템이 안전하게 종료되었습니다.")
            print("🔚 신호 모니터링 종료")

    def run(self):
        """메인 실행 함수"""
        print("📊 데이터 및 모델 준비 중...")

        # 데이터 수집 및 로드
        if not self.data_collector.load_data():
            print("새로운 데이터 수집 중...")
            self.data_collector.collect_all_data()
            self.data_collector.calculate_all_features()
            self.data_collector.save_data()

        # 모델 학습
        if not self.trading_model.mass_learning():
            print("❌ 모델 학습 실패")
            return

        print("✅ 시스템 준비 완료!")

        # 신호 모니터링 시작
        self.run_signal_monitor()

    def load_signal_results(self):
        """저장된 신호 결과 로드"""
        try:
            results_file = self.learning_data_path / 'signal_results.pkl'
            if results_file.exists():
                with open(results_file, 'rb') as f:
                    self.signal_results = pickle.load(f)
                print(f"{len(self.signal_results)}개 신호 결과 로드 완료")
            else:
                self.signal_results = []
        except Exception as e:
            print(f"❌ 신호 결과 로드 실패: {e}")
            self.signal_results = []

    def save_signal_results(self):
        """신호 결과 저장"""
        try:
            results_file = self.learning_data_path / 'signal_results.pkl'
            with open(results_file, 'wb') as f:
                pickle.dump(self.signal_results, f)
            print(f"💾 {len(self.signal_results)}개 신호 결과 저장 완료")
        except Exception as e:
            print(f"❌ 신호 결과 저장 실패: {e}")

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
        print(f"📝 활성 신호 추가: {signal.symbol} {signal.action}")

    def track_active_signals(self):
        """활성 신호 결과 추적"""
        if not self.active_signals:
            return

        current_time = datetime.now()
        completed_signals = []

        for signal_id, signal_result in self.active_signals.items():
            try:
                # 현재 가격 조회
                current_data = self.data_collector.realtime_data.get(signal_result.symbol, {})
                current_price = current_data.get('price', 0)

                if current_price == 0:
                    continue

                # 시간 경과 체크 (48시간 초과시 자동 종료)
                hours_elapsed = (current_time - signal_result.timestamp).total_seconds() / 3600

                if hours_elapsed > 48:
                    # 시간 초과로 종료
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
                    self.send_signal_result_notification(signal_result, "🎯 목표가 도달!")
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
                    self.send_signal_result_notification(signal_result, "🛑 손절가 도달")
                    continue

            except Exception as e:
                print(f"신호 추적 오류 ({signal_id}): {e}")

        # 완료된 신호 처리
        for signal_id in completed_signals:
            completed_signal = self.active_signals.pop(signal_id)
            self.signal_results.append(completed_signal)
            print(f"✅ 신호 완료: {completed_signal.symbol} ({completed_signal.outcome})")

        # 주기적으로 저장
        if completed_signals:
            self.save_signal_results()

    def send_signal_result_notification(self, result: SignalResult, title: str):
        """신호 결과 알림 전송"""
        try:
            emoji = "🎉" if result.success else "😔"
            outcome_emoji = {
                'TARGET_HIT': '🎯',
                'STOP_LOSS': '🛑',
                'TIME_EXIT': '⏰',
                'USER_EXIT': '👤'
            }

            message = f"""
{emoji} **{title}**

{outcome_emoji.get(result.outcome, '📊')} **신호 결과**:
🎯 **종목**: {result.symbol}
📈 **액션**: {result.action}
💪 **신뢰도**: {result.confidence:.1%}

💰 **진입가**: ${result.entry_price:.2f}
💰 **청산가**: ${result.actual_exit_price:.2f}
📊 **수익률**: {result.actual_return:+.2f}%
⏰ **보유시간**: {result.holding_duration:.1f}시간

🧠 **학습 적용**: 이 결과가 AI 모델 개선에 반영됩니다.
            """.strip()

            self.telegram.send_message(message)

        except Exception as e:
            print(f"결과 알림 전송 오류: {e}")

    def check_and_perform_learning(self):
        """학습 필요성 체크 및 실행"""
        current_time = datetime.now()
        hours_since_last_learning = (current_time - self.last_learning_time).total_seconds() / 3600

        # 24시간마다 또는 충분한 새 데이터가 있을 때 학습
        if (hours_since_last_learning >= self.learning_config['learning_frequency'] and
            len(self.signal_results) >= self.learning_config['min_results_for_learning']):

            print("🧠 신호 결과 기반 모델 학습 시작...")
            self.perform_signal_based_learning()
            self.last_learning_time = current_time

    def perform_signal_based_learning(self):
        """신호 결과 기반 학습 수행"""
        try:
            if len(self.signal_results) < self.learning_config['min_results_for_learning']:
                print(f"⚠️ 학습 데이터 부족: {len(self.signal_results)}/{self.learning_config['min_results_for_learning']}")
                return

            # 성공 패턴 분석
            successful_signals = [r for r in self.signal_results if r.success]
            failed_signals = [r for r in self.signal_results if not r.success]

            success_rate = len(successful_signals) / len(self.signal_results)
            print(f"📊 현재 성공률: {success_rate:.1%}")

            # 신뢰도별 성과 분석
            confidence_performance = self.analyze_confidence_performance()

            # 시장 조건별 성과 분석
            market_condition_performance = self.analyze_market_condition_performance()

            # 모델 신뢰도 조정
            self.adjust_model_confidence(confidence_performance)

            # 성공 패턴을 모델에 추가
            self.add_successful_patterns_to_model(successful_signals)

            # 학습 결과 알림
            self.send_learning_update_notification(success_rate, confidence_performance)

            print("✅ 신호 기반 학습 완료")

        except Exception as e:
            print(f"❌ 학습 수행 오류: {e}")

    def analyze_confidence_performance(self) -> Dict:
        """신뢰도별 성과 분석"""
        confidence_bins = [(0.0, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0)]
        performance = {}

        for min_conf, max_conf in confidence_bins:
            bin_results = [r for r in self.signal_results
                          if min_conf <= r.confidence < max_conf]

            if bin_results:
                success_rate = sum(1 for r in bin_results if r.success) / len(bin_results)
                avg_return = np.mean([r.actual_return for r in bin_results])

                performance[f"{min_conf:.1f}-{max_conf:.1f}"] = {
                    'success_rate': success_rate,
                    'avg_return': avg_return,
                    'count': len(bin_results)
                }

        return performance

    def analyze_market_condition_performance(self) -> Dict:
        """시장 조건별 성과 분석"""
        volatility_performance = {'HIGH': [], 'MEDIUM': [], 'LOW': []}
        trend_performance = {'UPTREND': [], 'DOWNTREND': [], 'SIDEWAYS': []}

        for result in self.signal_results:
            if result.market_features:
                # 변동성별 분석
                vol_analysis = result.market_features.get('volatility_analysis', {})
                vol_level = vol_analysis.get('level', 'MEDIUM')
                if vol_level in volatility_performance:
                    volatility_performance[vol_level].append(result.success)

                # 트렌드별 분석
                trend_analysis = result.market_features.get('price_trend', {})
                trend = trend_analysis.get('trend', 'SIDEWAYS')
                if 'UPTREND' in trend:
                    trend_performance['UPTREND'].append(result.success)
                elif 'DOWNTREND' in trend:
                    trend_performance['DOWNTREND'].append(result.success)
                else:
                    trend_performance['SIDEWAYS'].append(result.success)

        # 성공률 계산
        performance = {}
        for condition_type, conditions in [('volatility', volatility_performance), ('trend', trend_performance)]:
            performance[condition_type] = {}
            for condition, results in conditions.items():
                if results:
                    performance[condition_type][condition] = sum(results) / len(results)

        return performance

    def adjust_model_confidence(self, confidence_performance: Dict):
        """신뢰도 기반 모델 조정"""
        try:
            # 각 신뢰도 구간의 실제 성과에 따라 임계값 조정
            for conf_range, perf in confidence_performance.items():
                success_rate = perf['success_rate']

                # 성공률이 낮은 구간은 신뢰도 임계값 상향 조정
                if success_rate < self.learning_config['success_threshold']:
                    self.config['min_confidence'] = min(0.8,
                        self.config['min_confidence'] + self.learning_config['confidence_adjustment_factor'])
                    print(f"📈 최소 신뢰도 상향 조정: {self.config['min_confidence']:.2f}")
                    break
                elif success_rate > 0.8:
                    self.config['min_confidence'] = max(0.2,
                        self.config['min_confidence'] - self.learning_config['confidence_adjustment_factor'])
                    print(f"📉 최소 신뢰도 하향 조정: {self.config['min_confidence']:.2f}")
                    break

        except Exception as e:
            print(f"신뢰도 조정 오류: {e}")

    def add_successful_patterns_to_model(self, successful_signals: List[SignalResult]):
        """성공 패턴을 모델에 추가"""
        try:
            # 성공한 신호의 특징을 모델의 패턴 메모리에 추가
            for signal in successful_signals[-10:]:  # 최근 10개의 성공 패턴만
                if signal.market_features:
                    # 패턴 특징 추출
                    pattern_features = self.extract_pattern_features(signal)

                    # 트레이딩 모델의 패턴 메모리에 추가
                    self.trading_model.add_successful_pattern(pattern_features, signal.actual_return)

            print(f"✅ {min(10, len(successful_signals))}개 성공 패턴 모델에 추가")

        except Exception as e:
            print(f"패턴 추가 오류: {e}")

    def extract_pattern_features(self, signal: SignalResult) -> Dict:
        """신호에서 패턴 특징 추출"""
        try:
            market_features = signal.market_features or {}

            # 핵심 특징만 추출
            pattern = {
                'symbol': signal.symbol,
                'confidence': signal.confidence,
                'volatility_level': market_features.get('volatility_analysis', {}).get('level', 'MEDIUM'),
                'trend': market_features.get('price_trend', {}).get('trend', 'SIDEWAYS'),
                'momentum_direction': market_features.get('momentum_analysis', {}).get('direction', 'NEUTRAL'),
                'risk_level': market_features.get('risk_assessment', {}).get('level', 'MEDIUM'),
                'rsi': market_features.get('market_sentiment', {}).get('rsi', 50),
                'outcome': signal.outcome,
                'actual_return': signal.actual_return,
                'holding_duration': signal.holding_duration
            }

            return pattern

        except Exception as e:
            print(f"패턴 특징 추출 오류: {e}")
            return {}

    def send_learning_update_notification(self, success_rate: float, confidence_performance: Dict):
        """학습 업데이트 알림"""
        try:
            message = f"""
🧠 **AI 모델 학습 완료**

📊 **성과 요약**:
• 전체 성공률: {success_rate:.1%}
• 총 신호 수: {len(self.signal_results)}개
• 학습 데이터 업데이트: ✅

📈 **신뢰도별 성과**:
            """.strip()

            for conf_range, perf in confidence_performance.items():
                message += f"\n• {conf_range}: {perf['success_rate']:.1%} ({perf['count']}개)"

            message += f"""

⚙️ **모델 조정**:
• 현재 최소 신뢰도: {self.config['min_confidence']:.1%}
• 다음 학습: 24시간 후

💡 앞으로의 신호가 더욱 정확해집니다!
            """

            self.telegram.send_message(message)

        except Exception as e:
            print(f"학습 알림 전송 오류: {e}")

def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="NVDL/NVDQ 텔레그램 신호 알림 시스템")
    parser.add_argument('--api-key', type=str,
                       default="5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI",
                       help='FMP API 키')
    parser.add_argument('--interval', type=int, default=5,
                       help='체크 간격 (분)')
    parser.add_argument('--min-confidence', type=float, default=0.3,
                       help='최소 신뢰도 (0.0-1.0)')

    args = parser.parse_args()

    # 신호 알림 시스템 생성
    notifier = NVDLNVDQSignalNotifier(args.api_key)

    # 설정 조정
    notifier.config['check_interval'] = args.interval * 60
    notifier.config['min_confidence'] = args.min_confidence

    # 실행
    notifier.run()

if __name__ == "__main__":
    main()