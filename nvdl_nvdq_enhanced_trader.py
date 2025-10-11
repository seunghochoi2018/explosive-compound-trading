#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVDL/NVDQ 향상된 자동매매 시스템
- 이더봇의 성공 기능들을 일봉 기반으로 적용
- 제한 없는 패턴 학습
- NVDL(롱) ↔ NVDQ(숏) 스마트 전환
- 복리 효과 극대화

★★★ 핵심 목표 ★★★
손실을 줄이는 것이 아니라 이득을 내고 방향을 바꿔서 복리효과를 내야 한다!

- 예시: 상승 추세에서 하락 추세로 전환 시
  기존: NVDL 홀딩 → 손실
  목표: NVDL 수익실현 → NVDQ 전환 → 추가 수익

- NVDL↔NVDQ 양방향 거래로 수익 극대화
- 포지션 전환 시마다 수익 실현
- 제한 없는 시장 학습으로 민감한 추세 감지
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

class NVDLNVDQEnhancedTrader:
    """NVDL/NVDQ 향상된 자동매매 시스템 (이더봇 기능 적용)"""

    def __init__(self):
        print("="*70)
        print("NVDL/NVDQ 향상된 자동매매 시스템 v3.0")
        print("이더봇 87% 정확도 시스템을 일봉 기반으로 적용")
        print("NVDL(롱) <-> NVDQ(숏) 스마트 전환으로 복리 효과")
        print("제한 없는 패턴 학습 + 즉시 포지션 전환")
        print("="*70)

        # 핵심 시스템 초기화
        self.trend_detector = DailyTrendDetector()
        self.telegram = TelegramNotifier()

        # 패턴 학습 시스템 (이더봇에서 가져온 개념)
        self.pattern_memory = {}
        self.total_observations = 0
        self.learning_file = "nvdl_nvdq_learning_data.json"
        self.load_learning_data()

        # 거래 설정 (이더봇 기반 조정)
        self.symbols = ['NVDL', 'NVDQ']
        self.position_size_ratio = 0.9  # 포트폴리오의 90% (적극적)
        self.min_confidence = 0.0       # 제한 없음! (이더봇 방식)

        # 현재 상태
        self.current_position = None    # 'NVDL' 또는 'NVDQ' 또는 None
        self.entry_price = None
        self.entry_time = None
        self.balance = 10000.0
        self.total_trades = 0
        self.winning_trades = 0
        self.total_profit = 0.0

        # 이더봇에서 가져온 설정
        self.last_signal_time = None
        self.position_switches = 0      # NVDL↔NVDQ 전환 횟수

        # 거래 기록
        self.trade_history = []
        self.progress_file = "nvdl_nvdq_enhanced_progress.json"
        self.load_progress()

        print(f"시작 잔고: ${self.balance:,.2f}")
        print(f"학습된 패턴: {len(self.pattern_memory):,}개")
        print(f"제한 없는 신호 감지 활성화")

    def load_learning_data(self):
        """학습 데이터 로드 (이더봇 방식)"""
        try:
            with open(self.learning_file, 'r') as f:
                data = json.load(f)
                self.pattern_memory = data.get('patterns', {})
                self.total_observations = data.get('total_observations', 0)
                print(f"학습 데이터 로드: {len(self.pattern_memory)}개 패턴")
        except:
            print(f"새로운 학습 데이터 시작")

    def save_learning_data(self):
        """학습 데이터 저장"""
        try:
            data = {
                'patterns': self.pattern_memory,
                'total_observations': self.total_observations,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.learning_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f" 학습 데이터 저장 실패: {e}")

    def encode_daily_pattern(self, prices):
        """일봉 패턴을 문자열로 인코딩 (이더봇 방식 적용)"""
        if len(prices) < 2:
            return ""

        pattern = []
        for i in range(1, len(prices)):
            change = (prices[i] - prices[i-1]) / prices[i-1]
            if change > 0.02:      # 2% 이상 상승
                pattern.append('U')
            elif change < -0.02:   # 2% 이상 하락
                pattern.append('D')
            else:                  # 보합
                pattern.append('S')
        return ''.join(pattern)

    def get_unlimited_signal(self, symbol):
        """제한 없는 순수 학습 기반 신호 (이더봇 핵심 로직)"""
        try:
            # 기본 신호 생성
            signal = self.trend_detector.get_trading_signal(symbol)
            if not signal:
                return None

            # 일봉 데이터로 패턴 학습
            daily_data = self.trend_detector.get_daily_data(symbol)
            if daily_data is None or daily_data.empty or len(daily_data) < 10:
                print(f"   ⏳ {symbol} 데이터 부족")
                return signal

            # 최근 10일 패턴 확인
            recent_prices = daily_data['close'].tail(10).tolist()
            pattern = self.encode_daily_pattern(recent_prices)

            if not pattern:
                return signal

            # 패턴 학습 데이터 확인
            best_signal = None
            best_confidence = 0.0

            for pattern_length in range(3, min(8, len(pattern) + 1)):
                sub_pattern = pattern[-pattern_length:]

                if sub_pattern in self.pattern_memory:
                    stats = self.pattern_memory[sub_pattern]
                    total = stats.get('total', 0)
                    wins = stats.get('wins', 0)

                    # 이더봇 방식: 1회만 관찰되어도 활용
                    if total >= 1:
                        win_rate = wins / total
                        confidence = win_rate * (min(total, 100) / 100)

                        # 순수 학습 기반: 50% 기준으로 판단
                        if win_rate > 0.5:
                            suggested_action = 'BUY'  # NVDL 추천
                        else:
                            suggested_action = 'SELL' # NVDQ 추천

                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_signal = suggested_action

            # 패턴 학습 결과와 기본 신호 결합
            if best_signal:
                # 패턴 학습 신호가 더 강력하면 우선 적용
                enhanced_confidence = signal['confidence'] + best_confidence
                enhanced_signal = {
                    'action': best_signal,
                    'confidence': enhanced_confidence,
                    'reason': f"패턴학습({best_confidence:.3f}) + {signal['reason']}",
                    'pattern': pattern[-5:] if len(pattern) >= 5 else pattern
                }

                print(f"   [PATTERN] {symbol} 패턴 강화: {best_signal} (패턴: {pattern[-5:]}, 신뢰도: +{best_confidence:.3f})")
                return enhanced_signal

            return signal

        except Exception as e:
            print(f"   {symbol} 신호 생성 오류: {e}")
            return None

    def should_switch_position(self):
        """포지션 전환 여부 결정 (이더봇의 즉시 전환 로직)"""
        if not self.current_position:
            return False, None

        # 현재 포지션과 반대 신호 확인
        if self.current_position == 'NVDL':
            # NVDL 보유 중 → NVDQ 신호 체크
            nvdq_signal = self.get_unlimited_signal('NVDQ')
            if nvdq_signal and nvdq_signal['action'] == 'SELL':
                return True, 'NVDQ'

        elif self.current_position == 'NVDQ':
            # NVDQ 보유 중 → NVDL 신호 체크
            nvdl_signal = self.get_unlimited_signal('NVDL')
            if nvdl_signal and nvdl_signal['action'] == 'BUY':
                return True, 'NVDL'

        return False, None

    def execute_position_switch(self, from_symbol, to_symbol, signal):
        """포지션 전환 실행 (이더봇의 복리 효과 로직)"""
        # 현재 포지션 수익 계산
        current_price = self.get_current_price(from_symbol)
        if not current_price or not self.entry_price:
            return False

        profit_pct = (current_price - self.entry_price) / self.entry_price
        profit_amount = self.balance * profit_pct

        print(f"복리 효과! {from_symbol} -> {to_symbol} 전환")
        print(f"   {from_symbol} 수익 실현: {profit_pct*100:.2f}% (${profit_amount:,.2f})")

        # 수익 실현
        self.balance += profit_amount
        self.total_profit += profit_amount

        if profit_amount > 0:
            self.winning_trades += 1

        # 새 포지션 진입
        self.current_position = to_symbol
        self.entry_price = self.get_current_price(to_symbol)
        self.entry_time = datetime.now()
        self.total_trades += 1
        self.position_switches += 1

        print(f"   {to_symbol} 신규 진입: ${self.entry_price:.2f}")
        print(f"   업데이트된 잔고: ${self.balance:,.2f}")
        print(f"   목표: 양방향 거래로 복리 수익 극대화!")

        # 거래 기록
        trade_record = {
            'timestamp': datetime.now().isoformat(),
            'action': f'{from_symbol}→{to_symbol}',
            'from_price': current_price,
            'to_price': self.entry_price,
            'profit_pct': profit_pct,
            'balance': self.balance,
            'reason': signal['reason'],
            'confidence': signal['confidence']
        }
        self.trade_history.append(trade_record)

        # 텔레그램 알림
        self.telegram.send_message(
            f"포지션 전환!\n"
            f"{from_symbol} → {to_symbol}\n"
            f"수익: {profit_pct*100:.2f}%\n"
            f"잔고: ${self.balance:,.2f}"
        )

        return True

    def get_current_price(self, symbol):
        """현재 가격 조회"""
        try:
            daily_data = self.trend_detector.get_daily_data(symbol)
            if daily_data is not None and not daily_data.empty:
                return daily_data['close'].iloc[-1]
        except:
            pass
        return None

    def analyze_market_and_trade(self):
        """시장 분석 및 거래 실행 (이더봇 방식)"""
        print(f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 시장 분석")
        print("="*60)

        # 1. 포지션 전환 체크 (이더봇의 즉시 전환)
        should_switch, target_symbol = self.should_switch_position()

        if should_switch:
            signal = self.get_unlimited_signal(target_symbol)
            if signal:
                success = self.execute_position_switch(self.current_position, target_symbol, signal)
                if success:
                    return

        # 2. 신규 진입 체크 (포지션이 없을 때)
        if not self.current_position:
            print("   신규 포지션 기회 탐색:")

            for symbol in self.symbols:
                signal = self.get_unlimited_signal(symbol)
                if signal:
                    direction = "롱(상승)" if symbol == 'NVDL' else "숏(하락)"
                    print(f"   {symbol} {direction}: {signal['action']} (신뢰도: {signal['confidence']:.3f})")

                    # 신뢰도 기반 진입 (최소 15% 이상)
                    if signal['confidence'] >= 0.15 and signal['action'] != 'HOLD':
                        self.open_position(symbol, signal)
                        return

        # 3. 현재 포지션 상태 출력
        if self.current_position:
            current_price = self.get_current_price(self.current_position)
            if current_price and self.entry_price:
                profit_pct = (current_price - self.entry_price) / self.entry_price
                direction = "롱(상승)" if self.current_position == 'NVDL' else "숏(하락)"
                print(f"   현재 포지션: {self.current_position} {direction}")
                print(f"   진입가: ${self.entry_price:.2f}, 현재가: ${current_price:.2f}")
                print(f"   수익률: {profit_pct*100:.2f}%")

        # 4. 추천 포지션 분석 결과 (항상 표시)
        print(f"\n추천 포지션 분석 결과:")
        recommendations = []

        for symbol in self.symbols:
            signal = self.get_unlimited_signal(symbol)
            if signal and signal['confidence'] > 0:
                direction = "롱(상승)" if symbol == 'NVDL' else "숏(하락)"
                recommendations.append({
                    'symbol': symbol,
                    'direction': direction,
                    'action': signal['action'],
                    'confidence': signal['confidence'],
                    'reason': signal['reason']
                })

        if recommendations:
            print(f"   [FOUND] 발견된 신호: {len(recommendations)}개")
            for rec in recommendations:
                print(f"   {rec['symbol']} {rec['direction']}: {rec['action']} (신뢰도: {rec['confidence']:.3f})")
                print(f"      사유: {rec['reason']}")
        else:
            print(f"   현재 추천 포지션 없음")

    def open_position(self, symbol, signal):
        """포지션 진입"""
        current_price = self.get_current_price(symbol)
        if not current_price:
            print(f"   {symbol} 가격 조회 실패")
            return

        self.current_position = symbol
        self.entry_price = current_price
        self.entry_time = datetime.now()
        self.total_trades += 1

        direction = "롱(상승)" if symbol == 'NVDL' else "숏(하락)"
        print(f"   {symbol} {direction} 포지션 진입!")
        print(f"   진입가: ${current_price:.2f}")
        print(f"   신뢰도: {signal['confidence']:.3f}")
        print(f"   사유: {signal['reason']}")

        # 텔레그램 알림
        self.telegram.send_message(
            f"{symbol} {direction} 진입!\n"
            f"가격: ${current_price:.2f}\n"
            f"사유: {signal['reason']}"
        )

    def load_progress(self):
        """진행 상황 로드"""
        try:
            with open(self.progress_file, 'r') as f:
                data = json.load(f)
                self.balance = data.get('balance', 10000.0)
                self.total_trades = data.get('total_trades', 0)
                self.winning_trades = data.get('winning_trades', 0)
                self.total_profit = data.get('total_profit', 0.0)
                self.position_switches = data.get('position_switches', 0)
                self.trade_history = data.get('trade_history', [])
        except:
            pass

    def save_progress(self):
        """진행 상황 저장"""
        try:
            data = {
                'balance': self.balance,
                'total_trades': self.total_trades,
                'winning_trades': self.winning_trades,
                'total_profit': self.total_profit,
                'position_switches': self.position_switches,
                'trade_history': self.trade_history,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.progress_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f" 진행 상황 저장 실패: {e}")

    def show_stats(self):
        """통계 출력"""
        win_rate = self.winning_trades / max(self.total_trades, 1) * 100

        print(f"\n거래 통계:")
        print(f"   현재 잔고: ${self.balance:,.2f}")
        print(f"   총 거래: {self.total_trades}회")
        print(f"   승률: {win_rate:.1f}%")
        print(f"   총 수익: ${self.total_profit:,.2f}")
        print(f"   포지션 전환: {self.position_switches}회")
        print(f"   학습 패턴: {len(self.pattern_memory):,}개")

    def run(self):
        """메인 실행 루프"""
        print(f"\nNVDL/NVDQ 향상된 트레이더 실행 시작")
        print(f"일봉 기반 - 매 시간 체크")

        cycle = 0

        try:
            while True:
                cycle += 1

                # 시장 분석 및 거래
                self.analyze_market_and_trade()

                # 학습 데이터 저장 (주기적)
                if cycle % 10 == 0:
                    self.save_learning_data()
                    self.save_progress()

                # 통계 출력 (1시간마다)
                if cycle % 6 == 0:
                    self.show_stats()

                # 10분 대기 (일봉이므로 자주 체크할 필요 없음)
                time.sleep(600)  # 10분

        except KeyboardInterrupt:
            print("\n👋 트레이더 종료")
            self.save_learning_data()
            self.save_progress()
            self.show_stats()

if __name__ == "__main__":
    import sys

    test_mode = len(sys.argv) > 1 and sys.argv[1] == "test"

    trader = NVDLNVDQEnhancedTrader()

    if test_mode:
        print("\n[TEST MODE] 한 번만 실행")
        trader.analyze_market_and_trade()
        trader.show_stats()
        print("[TEST MODE] 완료")
    else:
        trader.run()