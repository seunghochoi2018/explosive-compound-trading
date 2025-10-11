#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVDL/NVDQ 스마트 자동매매 시스템
- 일봉 기반 추세 감지
- 87% 정확도 ETH 시스템을 주식에 적용
- 텔레그램 알림 통합
- 순수 시장 학습 기반
"""

import time
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

from daily_trend_detector import DailyTrendDetector
from telegram_notifier import TelegramNotifier

class NVDLNVDQSmartTrader:
    """NVDL/NVDQ 스마트 자동매매 시스템"""

    def __init__(self):
        print(" NVDL/NVDQ 스마트 자동매매 시스템 v2.0")
        print(" 일봉 기반 87% 정확도 추세 감지 적용")
        print(" 순수 시장 학습 + 노이즈 필터링 손절 + 텔레그램 알림")

        # 핵심 시스템 초기화
        self.trend_detector = DailyTrendDetector()
        self.telegram = TelegramNotifier()

        # 거래 설정
        self.symbols = ['NVDL', 'NVDQ']
        self.position_size_ratio = 0.5  # 포트폴리오의 50%
        self.min_confidence = 0.05      # 최소 신뢰도 (더 낮춤 - 5%)
        self.max_positions = 1          # 최대 1개 포지션

        # 현재 상태
        self.current_positions = {}     # {symbol: {'side': 'LONG/SHORT', 'entry_price': float, 'entry_time': datetime, 'confidence': float}}
        self.balance = 10000.0          # 시작 잔고
        self.total_trades = 0
        self.winning_trades = 0
        self.total_profit = 0.0

        # 거래 기록
        self.trade_history = []
        self.progress_file = "nvdl_nvdq_smart_progress.json"
        self.load_progress()

        # 순수 학습 패턴 (ETH 시스템에서 검증됨)
        self.learning_patterns = {}
        self.pattern_weights = {}
        self.min_pattern_length = 3
        self.max_pattern_length = 7

        # 적응형 리스크 관리 (ETH 시스템에서 검증된 노이즈 필터링 손절)
        self.adaptive_stop_loss = True
        self.base_stop_loss_pct = 0.08   # 기본 8% 손절
        self.take_profit_pct = 0.15      # 15% 익절
        self.max_holding_days = 10       # 최대 10일 보유

        # 노이즈 필터링 손절 학습 시스템 (ETH 87% 정확도 시스템 적용)
        self.stop_loss_learning = {
            'volatility_history': [],        # 최근 변동성 추적
            'noise_patterns': {},            # 노이즈 패턴 학습
            'adaptive_threshold': 0.08,      # 현재 적응형 손절값
            'market_regime': 'normal',       # 시장 상황 (normal/volatile/trending)
            'false_signals': 0,             # 거짓 신호 카운트
            'successful_filters': 0,         # 성공적 필터링 카운트
            'recent_moves': [],             # 최근 가격 움직임 (노이즈 패턴 분석용)
            'pattern_thresholds': {},       # 패턴별 적응형 임계값
            'daily_volatility': 0.0,       # 일일 변동성
            'trend_strength': 0.0           # 추세 강도
        }

        print(f" 시작 잔고: ${self.balance:,.2f}")
        print(f" 거래 대상: {', '.join(self.symbols)}")
        print(f" 최소 신뢰도: {self.min_confidence:.1%}")

        # 텔레그램 연결 테스트
        if self.telegram.test_connection():
            print(" 텔레그램 알림 연결 성공")
        else:
            print(" 텔레그램 연결 실패 (계속 진행)")

    def load_progress(self):
        """진행 상황 로드"""
        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.balance = data.get('balance', 10000.0)
                self.total_trades = data.get('total_trades', 0)
                self.winning_trades = data.get('winning_trades', 0)
                self.total_profit = data.get('total_profit', 0.0)
                self.trade_history = data.get('trade_history', [])
                self.current_positions = data.get('current_positions', {})
                self.learning_patterns = data.get('learning_patterns', {})
                self.pattern_weights = data.get('pattern_weights', {})
                print(f" 진행 상황 로드: 거래 {self.total_trades}회, 수익 {self.total_profit:+.2f}%")
        except FileNotFoundError:
            print(" 새로운 거래 시작")

    def save_progress(self):
        """진행 상황 저장"""
        data = {
            'timestamp': datetime.now().isoformat(),
            'balance': self.balance,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'total_profit': self.total_profit,
            'win_rate': self.winning_trades / max(1, self.total_trades) * 100,
            'trade_history': self.trade_history[-100:],  # 최근 100개 거래만 저장
            'current_positions': self.current_positions,
            'learning_patterns': self.learning_patterns,
            'pattern_weights': self.pattern_weights
        }

        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_current_price(self, symbol: str) -> float:
        """현재 가격 조회 (시뮬레이션)"""
        # 실제 구현시 Alpha Vantage나 다른 API 사용
        base_prices = {'NVDL': 45.0, 'NVDQ': 18.0}
        base_price = base_prices.get(symbol, 50.0)

        # 시뮬레이션용 가격 변동
        variation = np.random.normal(0, 0.02)  # 2% 변동
        return base_price * (1 + variation)

    def encode_price_pattern(self, prices: List[float]) -> str:
        """가격 패턴을 문자열로 인코딩 (ETH 시스템과 동일한 로직)"""
        if len(prices) < 2:
            return ""

        pattern = []
        for i in range(1, len(prices)):
            change_pct = (prices[i] - prices[i-1]) / prices[i-1] * 100

            if change_pct > 1.0:        # 1% 이상 상승
                pattern.append('U')
            elif change_pct < -1.0:     # 1% 이상 하락
                pattern.append('D')
            else:                       # 횡보
                pattern.append('S')

        return ''.join(pattern)

    def learn_from_outcome(self, pattern: str, was_profitable: bool, confidence: float):
        """결과로부터 학습 (ETH 시스템의 핵심 로직)"""
        if not pattern or len(pattern) < self.min_pattern_length:
            return

        if pattern not in self.learning_patterns:
            self.learning_patterns[pattern] = {'wins': 0, 'total': 0, 'confidence_sum': 0}

        self.learning_patterns[pattern]['total'] += 1
        self.learning_patterns[pattern]['confidence_sum'] += confidence

        if was_profitable:
            self.learning_patterns[pattern]['wins'] += 1

        # 패턴 가중치 업데이트
        if self.learning_patterns[pattern]['total'] >= 3:  # 최소 3번 관찰
            win_rate = self.learning_patterns[pattern]['wins'] / self.learning_patterns[pattern]['total']
            avg_confidence = self.learning_patterns[pattern]['confidence_sum'] / self.learning_patterns[pattern]['total']

            # 승률과 평균 신뢰도를 결합한 가중치
            self.pattern_weights[pattern] = win_rate * 0.7 + avg_confidence * 0.3

    def get_pattern_confidence(self, current_pattern: str) -> float:
        """현재 패턴의 신뢰도 계산"""
        if not current_pattern:
            return 0.0

        # 정확히 일치하는 패턴 찾기
        if current_pattern in self.pattern_weights:
            return self.pattern_weights[current_pattern]

        # 부분 일치 패턴 찾기
        max_confidence = 0.0
        for pattern, weight in self.pattern_weights.items():
            if len(pattern) >= 3 and current_pattern.endswith(pattern[-3:]):
                max_confidence = max(max_confidence, weight * 0.5)  # 부분 일치는 50% 가중치

        return max_confidence

    def update_volatility_learning(self, symbol: str):
        """변동성 패턴 학습 및 적응형 손절값 조정 (ETH 시스템 적용)"""
        if not self.adaptive_stop_loss:
            return

        current_price = self.get_current_price(symbol)

        # 일봉 기준 가격 히스토리 사용
        if len(self.trend_detector.price_history.get('1d', [])) < 10:
            return

        recent_prices = list(self.trend_detector.price_history['1d'])[-20:]  # 최근 20일

        # Type-safe price data handling
        numeric_prices = []
        for price in recent_prices:
            try:
                if isinstance(price, (int, float)):
                    numeric_prices.append(float(price))
                elif isinstance(price, dict):
                    continue  # dict인 경우 건너뛰기
                else:
                    numeric_prices.append(float(price))
            except (ValueError, TypeError):
                continue

        if len(numeric_prices) < 10:
            return

        # 일일 변동성 계산 (일봉 기준)
        daily_returns = []
        for i in range(1, len(numeric_prices)):
            daily_return = abs(numeric_prices[i] - numeric_prices[i-1]) / numeric_prices[i-1]
            daily_returns.append(daily_return)

        if daily_returns:
            current_volatility = sum(daily_returns) / len(daily_returns)
            self.stop_loss_learning['daily_volatility'] = current_volatility

            # 변동성 히스토리 업데이트
            self.stop_loss_learning['volatility_history'].append(current_volatility)
            if len(self.stop_loss_learning['volatility_history']) > 50:
                self.stop_loss_learning['volatility_history'] = self.stop_loss_learning['volatility_history'][-50:]

            # 시장 상황 판단
            avg_volatility = sum(self.stop_loss_learning['volatility_history']) / len(self.stop_loss_learning['volatility_history'])

            if current_volatility > avg_volatility * 1.5:
                self.stop_loss_learning['market_regime'] = 'volatile'
                # 변동성 높을 때 손절선 완화
                self.stop_loss_learning['adaptive_threshold'] = min(0.12, self.base_stop_loss_pct * 1.5)
            elif current_volatility < avg_volatility * 0.7:
                self.stop_loss_learning['market_regime'] = 'trending'
                # 안정적 추세일 때 손절선 강화
                self.stop_loss_learning['adaptive_threshold'] = max(0.05, self.base_stop_loss_pct * 0.7)
            else:
                self.stop_loss_learning['market_regime'] = 'normal'
                self.stop_loss_learning['adaptive_threshold'] = self.base_stop_loss_pct

    def get_adaptive_stop_loss(self, symbol: str, current_pnl: float) -> float:
        """상황별 적응형 손절값 계산 (ETH 시스템의 노이즈 필터링 적용)"""
        if not self.adaptive_stop_loss:
            return self.base_stop_loss_pct

        # 변동성 학습 업데이트
        self.update_volatility_learning(symbol)

        base_threshold = self.stop_loss_learning['adaptive_threshold']

        # 현재 손익에 따른 동적 조정
        if current_pnl > 0.05:  # 5% 이상 수익일 때
            # 수익 보호 모드 - 손절선 강화
            adjusted_threshold = base_threshold * 0.6
        elif current_pnl < -0.03:  # 3% 이상 손실일 때
            # 추가 손실 방지 - 손절선 완화하여 노이즈 필터링
            adjusted_threshold = base_threshold * 1.2
        else:
            adjusted_threshold = base_threshold

        # 시장 상황별 추가 조정
        regime = self.stop_loss_learning['market_regime']
        if regime == 'volatile':
            adjusted_threshold *= 1.3  # 변동성 장에서 노이즈 필터링
        elif regime == 'trending':
            adjusted_threshold *= 0.8  # 추세장에서 엄격한 손절

        # 최종 범위 제한 (3% ~ 15%)
        final_threshold = min(0.15, max(0.03, adjusted_threshold))

        return final_threshold

    def calculate_position_size(self, symbol: str, confidence: float) -> float:
        """포지션 크기 계산"""
        if self.balance < 100:  # 최소 잔고
            return 0

        # 신뢰도에 따른 포지션 크기 조정
        base_size = self.balance * self.position_size_ratio
        confidence_multiplier = min(confidence * 2, 1.0)  # 최대 1.0

        position_value = base_size * confidence_multiplier
        current_price = self.get_current_price(symbol)

        return position_value / current_price

    def should_exit_position(self, symbol: str) -> Tuple[bool, str]:
        """포지션 청산 여부 판단"""
        if symbol not in self.current_positions:
            return False, ""

        position = self.current_positions[symbol]
        current_price = self.get_current_price(symbol)
        entry_price = position['entry_price']
        entry_time = datetime.fromisoformat(position['entry_time'])
        holding_days = (datetime.now() - entry_time).days

        # 1. 추세 변환 감지 (최우선)
        trend_result = self.trend_detector.detect_multi_timeframe_reversal(symbol, position['side'])
        if trend_result['should_exit']:
            return True, f"추세 변환: {trend_result['reason']}"

        # 2. 시간 기반 청산
        if holding_days >= self.max_holding_days:
            return True, f"최대 보유 기간 도달 ({holding_days}일)"

        # 3. 적응형 손익 기반 청산 (노이즈 필터링 적용)
        if position['side'] == 'LONG':
            profit_pct = (current_price - entry_price) / entry_price
        else:
            profit_pct = (entry_price - current_price) / entry_price

        # 적응형 손절값 계산
        adaptive_stop_loss = self.get_adaptive_stop_loss(symbol, profit_pct)

        if profit_pct <= -adaptive_stop_loss:
            regime = self.stop_loss_learning.get('market_regime', 'normal')
            return True, f"적응형 손절: {profit_pct*100:.1f}% (임계값: {adaptive_stop_loss*100:.1f}%, 시장: {regime})"

        if profit_pct >= self.take_profit_pct:
            return True, f"익절: {profit_pct*100:.1f}%"

        return False, ""

    def open_position(self, symbol: str, side: str, confidence: float, reason: str):
        """포지션 오픈"""
        if len(self.current_positions) >= self.max_positions:
            print(f" 최대 포지션 수 도달 ({self.max_positions})")
            return False

        current_price = self.get_current_price(symbol)
        position_size = self.calculate_position_size(symbol, confidence)

        if position_size <= 0:
            print(f" {symbol} 포지션 크기 계산 실패")
            return False

        # 포지션 기록
        self.current_positions[symbol] = {
            'side': side,
            'entry_price': current_price,
            'entry_time': datetime.now().isoformat(),
            'confidence': confidence,
            'size': position_size,
            'reason': reason
        }

        position_value = position_size * current_price
        print(f" {symbol} {side} 포지션 오픈: ${current_price:.2f} (신뢰도: {confidence:.2f}, 금액: ${position_value:.0f})")

        # 텔레그램 알림
        self.telegram.notify_position_change(
            old_position="없음",
            new_position=f"{symbol} {side}",
            confidence=confidence,
            analysis=reason
        )

        return True

    def close_position(self, symbol: str, reason: str):
        """포지션 청산"""
        if symbol not in self.current_positions:
            return False

        position = self.current_positions[symbol]
        current_price = self.get_current_price(symbol)
        entry_price = position['entry_price']
        entry_time = datetime.fromisoformat(position['entry_time'])

        # 수익률 계산
        if position['side'] == 'LONG':
            profit_pct = (current_price - entry_price) / entry_price
        else:
            profit_pct = (entry_price - current_price) / entry_price

        # 거래 기록
        holding_time = datetime.now() - entry_time
        trade_record = {
            'symbol': symbol,
            'side': position['side'],
            'entry_price': entry_price,
            'exit_price': current_price,
            'profit_pct': profit_pct * 100,
            'holding_time': str(holding_time),
            'reason': reason,
            'confidence': position['confidence'],
            'timestamp': datetime.now().isoformat(),
            'profitable': profit_pct > 0
        }

        self.trade_history.append(trade_record)
        self.total_trades += 1

        if profit_pct > 0:
            self.winning_trades += 1

        # 잔고 업데이트
        position_value = position['size'] * entry_price
        profit_amount = position_value * profit_pct
        self.balance += profit_amount
        self.total_profit += profit_pct * 100

        print(f" {symbol} {position['side']} 청산: {profit_pct*100:+.2f}% (이유: {reason})")

        # 학습 (핵심!) - 일봉 기준으로 변경
        if len(self.trend_detector.price_history['1d']) >= self.min_pattern_length:
            recent_prices = list(self.trend_detector.price_history['1d'])[-self.max_pattern_length:]
            pattern = self.encode_price_pattern(recent_prices)
            self.learn_from_outcome(pattern, profit_pct > 0, position['confidence'])

        # 텔레그램 알림
        win_rate = self.winning_trades / max(1, self.total_trades) * 100
        self.telegram.notify_trade_result(
            symbol=symbol,
            profit_pct=profit_pct * 100,
            entry_price=entry_price,
            exit_price=current_price,
            holding_time=str(holding_time).split('.')[0],
            total_profit=self.total_profit,
            win_rate=win_rate
        )

        # 포지션 제거
        del self.current_positions[symbol]
        return True

    def check_entry_signals(self):
        """진입 신호 체크"""
        print(f"\n 진입 신호 분석 시작 (현재 포지션: {len(self.current_positions)}/{self.max_positions})")

        if len(self.current_positions) >= self.max_positions:
            print(f" 최대 포지션 수 도달 - 신규 진입 불가")
            return

        position_recommendations = []

        for symbol in self.symbols:
            if symbol in self.current_positions:
                print(f"   {symbol}: 포지션 유지 중 - 건너뛰기")
                continue

            print(f"\n {symbol} 신호 분석:")
            # 추세 감지기에서 신호 받기 (이미 상세 로깅 포함)
            signal = self.trend_detector.get_trading_signal(symbol)

            if signal['action'] in ['BUY', 'SELL']:
                if signal['confidence'] >= self.min_confidence:
                    # 학습된 패턴 신뢰도 추가 (일봉 기준)
                    if len(self.trend_detector.price_history.get('1d', [])) >= self.min_pattern_length:
                        recent_prices = list(self.trend_detector.price_history['1d'])[-self.max_pattern_length:]
                        pattern = self.encode_price_pattern(recent_prices)
                        pattern_confidence = self.get_pattern_confidence(pattern)

                        # 추세 신뢰도와 패턴 신뢰도 결합
                        combined_confidence = signal['confidence'] * 0.6 + pattern_confidence * 0.4

                        print(f"    패턴 학습 신뢰도: {pattern_confidence:.3f}")
                        print(f"    최종 신뢰도: {combined_confidence:.3f} (최소: {self.min_confidence:.2f})")

                        if combined_confidence >= self.min_confidence:
                            side = 'LONG' if signal['action'] == 'BUY' else 'SHORT'
                            reason = f"{signal['reason']} + 패턴학습({pattern_confidence:.2f})"

                            position_recommendations.append({
                                'symbol': symbol,
                                'side': side,
                                'confidence': combined_confidence,
                                'reason': reason
                            })

                            print(f"    강력한 {symbol} {side} 신호 감지!")
                            self.open_position(symbol, side, combined_confidence, reason)
                        else:
                            print(f"   ⏸ {symbol} 신뢰도 부족: {combined_confidence:.3f} < {self.min_confidence:.2f}")
                    else:
                        print(f"   ⏳ {symbol} 학습 데이터 부족")
                else:
                    print(f"   ⏸ {symbol} 기본 신뢰도 부족: {signal['confidence']:.3f} < {self.min_confidence:.2f}")
                    print(f"      신호 상세: {signal['action']} ({signal['reason']})")

        # 추천 포지션 요약 (항상 표시)
        print(f"\n 추천 포지션 분석 결과:")
        if position_recommendations:
            print(f"    발견된 신호: {len(position_recommendations)}개")
            for rec in position_recommendations:
                print(f"    {rec['symbol']} {rec['side']} (신뢰도: {rec['confidence']:.3f}) - {rec['reason']}")
        else:
            print(f"   ⏸ 현재 추천 포지션 없음 - 모든 신호가 임계값 미달")
            print(f"    신뢰도 임계값: {self.min_confidence:.3f} ({self.min_confidence*100:.1f}%)")

            # 모든 심볼의 신호 상태 요약
            for symbol in self.symbols:
                signal = self.trend_detector.generate_signal(symbol)
                if signal and signal['confidence'] > 0:
                    print(f"    {symbol}: {signal['action']} (신뢰도: {signal['confidence']:.3f}, 사유: {signal['reason']})")
                else:
                    print(f"    {symbol}: 신호 없음")

    def run_daily_check(self):
        """일일 체크 실행"""
        print(f"\n {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 일일 체크")
        print("="*60)

        # 현재 포지션 청산 신호 체크
        positions_to_close = []
        for symbol in list(self.current_positions.keys()):
            should_exit, reason = self.should_exit_position(symbol)
            if should_exit:
                positions_to_close.append((symbol, reason))

        for symbol, reason in positions_to_close:
            self.close_position(symbol, reason)

        # 신규 진입 신호 체크
        self.check_entry_signals()

        # 현재 상태 출력
        print(f"\n 현재 잔고: ${self.balance:,.2f}")
        print(f" 총 거래: {self.total_trades}회")
        if self.total_trades > 0:
            win_rate = self.winning_trades / self.total_trades * 100
            print(f" 승률: {win_rate:.1f}% ({self.winning_trades}/{self.total_trades})")
            print(f" 누적 수익: {self.total_profit:+.2f}%")

        if self.current_positions:
            print(f"\n 현재 포지션:")
            for symbol, pos in self.current_positions.items():
                current_price = self.get_current_price(symbol)
                if pos['side'] == 'LONG':
                    pnl = (current_price - pos['entry_price']) / pos['entry_price'] * 100
                    pnl_ratio = (current_price - pos['entry_price']) / pos['entry_price']
                else:
                    pnl = (pos['entry_price'] - current_price) / pos['entry_price'] * 100
                    pnl_ratio = (pos['entry_price'] - current_price) / pos['entry_price']

                # 적응형 손절값 계산
                adaptive_stop_loss = self.get_adaptive_stop_loss(symbol, pnl_ratio) * 100
                regime = self.stop_loss_learning.get('market_regime', 'normal')

                holding_time = datetime.now() - datetime.fromisoformat(pos['entry_time'])
                print(f"  {symbol} {pos['side']}: ${pos['entry_price']:.2f} → ${current_price:.2f}")
                print(f"    손익: {pnl:+.1f}% | 적응형 손절: {adaptive_stop_loss:.1f}% | 시장: {regime} | {holding_time.days}일")

        # 학습 상태
        if self.learning_patterns:
            profitable_patterns = sum(1 for p in self.learning_patterns.values() if p['wins'] > p['total'] * 0.6)
            print(f" 학습된 패턴: {len(self.learning_patterns)}개 (수익패턴: {profitable_patterns}개)")

        self.save_progress()
        print("="*60)

    def run_continuous_trading(self):
        """연속 자동매매 실행"""
        print("\n NVDL/NVDQ 스마트 자동매매 시작!")
        print(" 일봉 기준 87% 정확도 시스템 적용")
        print(" 순수 시장 학습 + 추세 감지 + 노이즈 필터링 손절 + 텔레그램 알림")
        print("⏰ 일봉 기준 매일 분석")

        last_daily_check = datetime.now().date()

        try:
            while True:
                current_time = datetime.now()

                # 일봉 기준 일일 체크 (하루에 한 번)
                if current_time.date() > last_daily_check:
                    print(f" {current_time.strftime('%Y-%m-%d')} 일봉 기준 데일리 체크")
                    self.run_daily_check()
                    last_daily_check = current_time.date()

                time.sleep(21600)  # 일봉 기준 6시간마다 체크 (4회/일)

        except KeyboardInterrupt:
            print("\n 자동매매 중지됨")

            # 현재 포지션 정보
            if self.current_positions:
                print(" 현재 포지션 유지 중:")
                for symbol, pos in self.current_positions.items():
                    print(f"  {symbol} {pos['side']}: ${pos['entry_price']:.2f}")

            self.save_progress()
            print(" 진행 상황 저장 완료")

if __name__ == "__main__":
    trader = NVDLNVDQSmartTrader()

    print("\n" + "="*50)
    print(" NVDL/NVDQ 스마트 자동매매 시스템 v2.0")
    print(" ETH 87% 정확도 시스템의 일봉 적용")
    print(" 일봉 + 순수학습 + 노이즈필터링 손절 + 텔레그램 알림")
    print("="*50)

    # 현재 상태 체크
    trader.run_daily_check()

    # 연속 거래 시작
    trader.run_continuous_trading()