#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVDL/NVDQ 24시간 적응형 자동매매 시스템
- 미국 장시간 자동 거래
- 실시간 학습 및 전략 적응
- 거래 주기 동적 최적화
- 텔레그램 실시간 알림
"""

import json
import time
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import threading
import warnings
warnings.filterwarnings('ignore')

# 자체 모듈 임포트
from nvdl_nvdq_data_collector import NVDLNVDQDataCollector
from nvdl_nvdq_trading_model import NVDLNVDQTradingModel
from telegram_notifier import TelegramNotifier

@dataclass
class MarketCondition:
    """시장 상황 분석 결과"""
    symbol: str
    current_price: float
    price_change_24h: float
    volume_change_24h: float
    volatility: float
    trend_strength: float
    signal_confidence: float
    recommended_action: str
    optimal_hold_time: float  # 시간 단위

@dataclass
class TradingState:
    """현재 거래 상태"""
    position: Optional[str]  # 'NVDL', 'NVDQ', None
    entry_time: Optional[datetime]
    entry_price: Optional[float]
    current_pnl: float
    hold_duration: float  # 시간 단위
    exit_signal_strength: float

class AdaptiveFrequencyManager:
    """적응형 거래 주기 관리자"""

    def __init__(self):
        self.frequency_performance = {
            '15min': {'trades': 0, 'wins': 0, 'total_pnl': 0.0, 'avg_hold': 0.0},
            '30min': {'trades': 0, 'wins': 0, 'total_pnl': 0.0, 'avg_hold': 0.0},
            '1hour': {'trades': 0, 'wins': 0, 'total_pnl': 0.0, 'avg_hold': 0.0},
            '2hour': {'trades': 0, 'wins': 0, 'total_pnl': 0.0, 'avg_hold': 0.0},
            '4hour': {'trades': 0, 'wins': 0, 'total_pnl': 0.0, 'avg_hold': 0.0},
            '8hour': {'trades': 0, 'wins': 0, 'total_pnl': 0.0, 'avg_hold': 0.0},
            '12hour': {'trades': 0, 'wins': 0, 'total_pnl': 0.0, 'avg_hold': 0.0},
            '24hour': {'trades': 0, 'wins': 0, 'total_pnl': 0.0, 'avg_hold': 0.0}
        }
        self.current_optimal_frequency = '1hour'
        self.last_optimization = datetime.now()

    def get_frequency_minutes(self, frequency: str) -> int:
        """주기를 분 단위로 변환"""
        freq_map = {
            '15min': 15, '30min': 30, '1hour': 60, '2hour': 120,
            '4hour': 240, '8hour': 480, '12hour': 720, '24hour': 1440
        }
        return freq_map.get(frequency, 60)

    def record_trade_result(self, frequency: str, pnl: float, hold_time_hours: float):
        """거래 결과 기록"""
        if frequency in self.frequency_performance:
            perf = self.frequency_performance[frequency]
            perf['trades'] += 1
            perf['total_pnl'] += pnl
            if pnl > 0:
                perf['wins'] += 1

            # 평균 보유 시간 업데이트
            perf['avg_hold'] = (perf['avg_hold'] * (perf['trades'] - 1) + hold_time_hours) / perf['trades']

    def optimize_frequency(self) -> str:
        """최적 거래 주기 계산"""
        best_frequency = self.current_optimal_frequency
        best_score = -float('inf')

        for freq, perf in self.frequency_performance.items():
            if perf['trades'] < 5:  # 최소 5회 거래 필요
                continue

            win_rate = perf['wins'] / perf['trades']
            avg_pnl = perf['total_pnl'] / perf['trades']

            # 샤프 비율 유사 점수 (수익률 / 변동성 근사)
            score = (win_rate * avg_pnl) / max(abs(avg_pnl), 0.1)

            # 거래 빈도 보너스 (너무 드문 거래는 펜티)
            if perf['avg_hold'] > 48:  # 48시간 이상 보유 시 펜티
                score *= 0.8
            elif perf['avg_hold'] < 2:  # 2시간 미만 보유 시 펜티 (과도한 빈도)
                score *= 0.9

            if score > best_score:
                best_score = score
                best_frequency = freq

        self.current_optimal_frequency = best_frequency
        self.last_optimization = datetime.now()
        return best_frequency

    def should_reoptimize(self) -> bool:
        """재최적화 필요 여부"""
        hours_since_last = (datetime.now() - self.last_optimization).total_seconds() / 3600
        return hours_since_last >= 24  # 24시간마다 재최적화

class NVDLNVDQAdaptiveAutoTrader:
    def __init__(self, fmp_api_key: str, auto_trading: bool = True):
        """
        NVDL/NVDQ 적응형 자동매매 시스템 초기화

        Args:
            fmp_api_key: Financial Modeling Prep API 키
            auto_trading: 실제 자동매매 실행 여부
        """
        print("=" * 70)
        print("🤖 NVDL/NVDQ 24시간 적응형 자동매매 시스템")
        print("📊 실시간 학습 + 거래 주기 최적화")
        print("🌙 미국 장시간 24시간 자동 거래")
        print("=" * 70)

        # 기본 설정
        self.fmp_api_key = fmp_api_key
        self.auto_trading = auto_trading
        self.running = False
        self.start_time = datetime.now()

        # 컴포넌트 초기화
        self.data_collector = NVDLNVDQDataCollector(fmp_api_key)
        self.trading_model = NVDLNVDQTradingModel(fmp_api_key)
        self.telegram = TelegramNotifier()
        self.frequency_manager = AdaptiveFrequencyManager()

        # 거래 상태
        self.trading_state = TradingState(
            position=None, entry_time=None, entry_price=None,
            current_pnl=0.0, hold_duration=0.0, exit_signal_strength=0.0
        )

        # 성과 추적
        self.total_trades = 0
        self.winning_trades = 0
        self.total_profit = 0.0
        self.daily_trades = 0
        self.daily_profit = 0.0

        # 적응형 설정
        self.adaptive_config = {
            'base_check_interval': 900,     # 기본 15분
            'min_confidence': 0.3,          # 최소 신뢰도
            'volatility_threshold': 0.05,   # 변동성 임계값
            'learning_rate': 0.1,           # 학습률
            'max_position_time': 24,        # 최대 포지션 보유 시간
            'night_mode': True,             # 야간 모드 (미국 장시간)
            'risk_multiplier': 1.0,         # 위험 승수
        }

        # 시장 상황별 전략 가중치
        self.strategy_weights = {
            'trend_following': 0.3,
            'mean_reversion': 0.2,
            'momentum': 0.3,
            'volatility_breakout': 0.2
        }

        # 데이터 저장 파일
        self.state_file = "adaptive_auto_trader_state.json"
        self.performance_file = "adaptive_performance_log.json"

        print("✅ 적응형 자동매매 시스템 초기화 완료")

    def load_state(self):
        """봇 상태 로드"""
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)

                # 거래 상태 복원
                if state.get('position'):
                    self.trading_state.position = state['position']
                    self.trading_state.entry_time = datetime.fromisoformat(state['entry_time'])
                    self.trading_state.entry_price = state['entry_price']

                # 성과 복원
                self.total_trades = state.get('total_trades', 0)
                self.winning_trades = state.get('winning_trades', 0)
                self.total_profit = state.get('total_profit', 0.0)

                # 주기 관리자 복원
                if 'frequency_performance' in state:
                    self.frequency_manager.frequency_performance = state['frequency_performance']
                    self.frequency_manager.current_optimal_frequency = state.get('optimal_frequency', '1hour')

                print(f"상태 로드 완료: 포지션={self.trading_state.position}, 거래={self.total_trades}회")

        except FileNotFoundError:
            print("기존 상태 파일이 없습니다. 새로 시작합니다.")
        except Exception as e:
            print(f"상태 로드 오류: {e}")

    def save_state(self):
        """봇 상태 저장"""
        try:
            state = {
                'position': self.trading_state.position,
                'entry_time': self.trading_state.entry_time.isoformat() if self.trading_state.entry_time else None,
                'entry_price': self.trading_state.entry_price,
                'total_trades': self.total_trades,
                'winning_trades': self.winning_trades,
                'total_profit': self.total_profit,
                'frequency_performance': self.frequency_manager.frequency_performance,
                'optimal_frequency': self.frequency_manager.current_optimal_frequency,
                'last_update': datetime.now().isoformat()
            }

            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"상태 저장 오류: {e}")

    def analyze_market_condition(self, symbol: str) -> MarketCondition:
        """시장 상황 분석"""
        try:
            # 실시간 데이터 가져오기
            realtime_data = self.data_collector.fetch_realtime_data(symbol)
            if not realtime_data:
                return MarketCondition(
                    symbol=symbol, current_price=0, price_change_24h=0,
                    volume_change_24h=0, volatility=0, trend_strength=0,
                    signal_confidence=0, recommended_action="HOLD", optimal_hold_time=4
                )

            current_price = realtime_data.get('price', 0)
            price_change_24h = realtime_data.get('changesPercentage', 0) / 100

            # 기술적 지표 계산
            features = self.data_collector.get_latest_features(symbol)
            if features is None:
                volatility = abs(price_change_24h)
                trend_strength = 0
            else:
                volatility = features[4] if len(features) > 4 else abs(price_change_24h)
                momentum = features[7] if len(features) > 7 else 0
                trend_strength = abs(momentum)

            # AI 모델 신호
            action, _, confidence = self.trading_model.get_portfolio_signal()
            if action == "BUY" and symbol == "NVDL":
                recommended_action = "BUY_NVDL"
            elif action == "BUY" and symbol == "NVDQ":
                recommended_action = "BUY_NVDQ"
            else:
                recommended_action = "HOLD"

            # 최적 보유 시간 계산 (변동성과 트렌드 강도 기반)
            if volatility > 0.05:  # 고변동성
                optimal_hold_time = 2 + trend_strength * 4  # 2-6시간
            elif volatility > 0.02:  # 중간 변동성
                optimal_hold_time = 4 + trend_strength * 8  # 4-12시간
            else:  # 저변동성
                optimal_hold_time = 8 + trend_strength * 16  # 8-24시간

            return MarketCondition(
                symbol=symbol,
                current_price=current_price,
                price_change_24h=price_change_24h,
                volume_change_24h=0,  # FMP에서 직접 제공하지 않음
                volatility=volatility,
                trend_strength=trend_strength,
                signal_confidence=confidence,
                recommended_action=recommended_action,
                optimal_hold_time=min(optimal_hold_time, 24)  # 최대 24시간
            )

        except Exception as e:
            print(f"시장 상황 분석 오류 ({symbol}): {e}")
            return MarketCondition(
                symbol=symbol, current_price=0, price_change_24h=0,
                volume_change_24h=0, volatility=0, trend_strength=0,
                signal_confidence=0, recommended_action="HOLD", optimal_hold_time=4
            )

    def should_enter_position(self, market_conditions: Dict[str, MarketCondition]) -> Tuple[bool, str, float]:
        """포지션 진입 여부 결정"""
        if self.trading_state.position is not None:
            return False, "NONE", 0.0

        # 두 심볼의 시장 상황 비교
        nvdl_condition = market_conditions.get('NVDL')
        nvdq_condition = market_conditions.get('NVDQ')

        if not nvdl_condition or not nvdq_condition:
            return False, "NONE", 0.0

        # 신호 강도 비교
        nvdl_score = nvdl_condition.signal_confidence if nvdl_condition.recommended_action == "BUY_NVDL" else 0
        nvdq_score = nvdq_condition.signal_confidence if nvdq_condition.recommended_action == "BUY_NVDQ" else 0

        min_confidence = self.adaptive_config['min_confidence']

        # 더 강한 신호 선택
        if nvdl_score > nvdq_score and nvdl_score > min_confidence:
            return True, "NVDL", nvdl_score
        elif nvdq_score > min_confidence:
            return True, "NVDQ", nvdq_score
        else:
            return False, "NONE", max(nvdl_score, nvdq_score)

    def should_exit_position(self, market_conditions: Dict[str, MarketCondition]) -> Tuple[bool, str]:
        """포지션 청산 여부 결정"""
        if self.trading_state.position is None:
            return False, "NO_POSITION"

        current_symbol = self.trading_state.position
        condition = market_conditions.get(current_symbol)

        if not condition:
            return True, "DATA_ERROR"

        # 시간 기반 청산
        if self.trading_state.entry_time:
            hold_hours = (datetime.now() - self.trading_state.entry_time).total_seconds() / 3600

            # 최대 보유 시간 초과
            if hold_hours > self.adaptive_config['max_position_time']:
                return True, "MAX_TIME"

            # 최적 보유 시간 기반 청산 (신호 약화 시)
            if hold_hours > condition.optimal_hold_time and condition.signal_confidence < 0.4:
                return True, "OPTIMAL_TIME"

        # 반대 신호 발생
        nvdl_condition = market_conditions.get('NVDL')
        nvdq_condition = market_conditions.get('NVDQ')

        if nvdl_condition and nvdq_condition:
            if (current_symbol == "NVDL" and
                nvdq_condition.recommended_action == "BUY_NVDQ" and
                nvdq_condition.signal_confidence > 0.5):
                return True, "OPPOSITE_SIGNAL"

            if (current_symbol == "NVDQ" and
                nvdl_condition.recommended_action == "BUY_NVDL" and
                nvdl_condition.signal_confidence > 0.5):
                return True, "OPPOSITE_SIGNAL"

        # 손절/익절 (실제 구현 시 필요)
        if self.auto_trading and self.trading_state.current_pnl < -5.0:  # 5% 손절
            return True, "STOP_LOSS"

        if self.auto_trading and self.trading_state.current_pnl > 10.0:  # 10% 익절
            return True, "TAKE_PROFIT"

        return False, "CONTINUE"

    def execute_trade(self, action: str, symbol: str, confidence: float):
        """거래 실행"""
        print(f"\n🔄 거래 실행: {action} {symbol} (신뢰도: {confidence:.2f})")

        # 현재가 조회
        current_price = self.get_current_price(symbol)
        if not current_price:
            print(f"❌ {symbol} 현재가 조회 실패")
            return

        if action == "ENTER":
            # 포지션 진입
            self.trading_state.position = symbol
            self.trading_state.entry_time = datetime.now()
            self.trading_state.entry_price = current_price
            self.trading_state.current_pnl = 0.0

            print(f"📈 {symbol} 포지션 진입: ${current_price:.2f}")

            # 텔레그램 알림
            self.telegram.notify_position_change(
                old_position="없음",
                new_position=symbol,
                confidence=confidence,
                analysis=f"AI 신호 기반 {symbol} 진입"
            )

            if self.auto_trading:
                # 실제 주문 실행 (API 연동 필요)
                print("🤖 실제 주문 실행 중...")
                # 여기에 실제 주문 로직 구현

        elif action == "EXIT":
            # 포지션 청산
            if self.trading_state.position and self.trading_state.entry_price:
                exit_price = current_price

                # 수익률 계산 (레버리지 적용)
                raw_pnl = (exit_price / self.trading_state.entry_price - 1) * 100
                if symbol == 'NVDL':
                    leveraged_pnl = raw_pnl * 3  # 3x 레버리지
                elif symbol == 'NVDQ':
                    leveraged_pnl = raw_pnl * 2  # 2x 역 레버리지
                else:
                    leveraged_pnl = raw_pnl

                # 보유 시간 계산
                hold_time = (datetime.now() - self.trading_state.entry_time).total_seconds() / 3600

                # 거래 기록
                self.record_trade_result(symbol, leveraged_pnl, hold_time)

                print(f"📊 {symbol} 포지션 청산: {leveraged_pnl:+.2f}% ({hold_time:.1f}시간)")

                # 텔레그램 알림
                self.telegram.notify_trade_result(
                    symbol=symbol,
                    profit_pct=leveraged_pnl,
                    entry_price=self.trading_state.entry_price,
                    exit_price=exit_price,
                    holding_time=f"{hold_time:.1f}시간",
                    total_profit=self.total_profit,
                    win_rate=self.get_win_rate()
                )

                # 상태 초기화
                self.trading_state.position = None
                self.trading_state.entry_time = None
                self.trading_state.entry_price = None
                self.trading_state.current_pnl = 0.0

                if self.auto_trading:
                    # 실제 청산 주문 실행
                    print("🤖 실제 청산 주문 실행 중...")

    def record_trade_result(self, symbol: str, pnl: float, hold_time: float):
        """거래 결과 기록 및 학습"""
        self.total_trades += 1
        self.daily_trades += 1
        self.total_profit += pnl
        self.daily_profit += pnl

        if pnl > 0:
            self.winning_trades += 1

        # 현재 주기에 대한 성과 기록
        current_freq = self.frequency_manager.current_optimal_frequency
        self.frequency_manager.record_trade_result(current_freq, pnl, hold_time)

        # 성공 거래 시 모델 학습
        if pnl > 0:
            features = self.data_collector.get_latest_features(symbol)
            if features is not None:
                self.trading_model.record_trade(
                    symbol, self.trading_state.entry_price,
                    self.trading_state.entry_price * (1 + pnl/100), features
                )

        print(f"거래 #{self.total_trades}: {symbol} {pnl:+.2f}% | 승률: {self.get_win_rate():.1f}%")

    def get_current_price(self, symbol: str) -> Optional[float]:
        """현재가 조회"""
        realtime_data = self.data_collector.fetch_realtime_data(symbol)
        if realtime_data:
            return realtime_data.get('price')
        return None

    def get_win_rate(self) -> float:
        """승률 계산"""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100

    def update_current_pnl(self):
        """현재 PnL 업데이트"""
        if self.trading_state.position and self.trading_state.entry_price:
            current_price = self.get_current_price(self.trading_state.position)
            if current_price:
                raw_pnl = (current_price / self.trading_state.entry_price - 1) * 100

                if self.trading_state.position == 'NVDL':
                    self.trading_state.current_pnl = raw_pnl * 3
                elif self.trading_state.position == 'NVDQ':
                    self.trading_state.current_pnl = raw_pnl * 2
                else:
                    self.trading_state.current_pnl = raw_pnl

    def adaptive_learning_cycle(self):
        """적응형 학습 사이클"""
        try:
            # 모델 점진적 학습
            self.trading_model.incremental_learning()

            # 거래 주기 최적화
            if self.frequency_manager.should_reoptimize():
                old_freq = self.frequency_manager.current_optimal_frequency
                new_freq = self.frequency_manager.optimize_frequency()

                if old_freq != new_freq:
                    print(f"📊 거래 주기 최적화: {old_freq} → {new_freq}")

                    # 새로운 체크 간격 적용
                    new_interval = self.frequency_manager.get_frequency_minutes(new_freq) * 60
                    self.adaptive_config['base_check_interval'] = new_interval

                    # 텔레그램 알림
                    self.telegram.send_message(
                        f"📊 **거래 주기 최적화**\n\n"
                        f"이전: {old_freq}\n"
                        f"신규: {new_freq}\n"
                        f"새로운 체크 간격: {new_interval//60}분"
                    )

        except Exception as e:
            print(f"적응형 학습 오류: {e}")

    def trading_cycle(self):
        """메인 거래 사이클"""
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 거래 사이클 시작")

            # 최신 데이터 업데이트
            for symbol in ['NVDL', 'NVDQ']:
                realtime_data = self.data_collector.fetch_realtime_data(symbol)
                if realtime_data:
                    self.data_collector.realtime_data[symbol] = realtime_data

            # 시장 상황 분석
            market_conditions = {}
            for symbol in ['NVDL', 'NVDQ']:
                market_conditions[symbol] = self.analyze_market_condition(symbol)

            # 현재 PnL 업데이트
            self.update_current_pnl()

            # 포지션 청산 검토
            should_exit, exit_reason = self.should_exit_position(market_conditions)
            if should_exit:
                print(f"청산 신호: {exit_reason}")
                self.execute_trade("EXIT", self.trading_state.position, 0.0)

            # 새로운 포지션 진입 검토
            should_enter, symbol, confidence = self.should_enter_position(market_conditions)
            if should_enter:
                print(f"진입 신호: {symbol} (신뢰도: {confidence:.2f})")
                self.execute_trade("ENTER", symbol, confidence)

            # 상태 출력
            if self.trading_state.position:
                hold_time = (datetime.now() - self.trading_state.entry_time).total_seconds() / 3600
                print(f"현재 포지션: {self.trading_state.position} | PnL: {self.trading_state.current_pnl:+.2f}% | 보유: {hold_time:.1f}h")
            else:
                print("현재 포지션: 없음")

            # 성과 요약
            print(f"총 거래: {self.total_trades} | 승률: {self.get_win_rate():.1f}% | 총 수익: {self.total_profit:+.2f}%")

        except Exception as e:
            print(f"거래 사이클 오류: {e}")
            self.telegram.notify_error("거래 사이클 오류", str(e))

    def run(self):
        """메인 실행 루프"""
        print("\n🚀 24시간 적응형 자동매매 시작")

        # 상태 로드
        self.load_state()

        # 초기 설정
        self.running = True

        # 시작 알림
        start_message = f"""
🤖 **24시간 자동매매 시작**

⚡ **모드**: {'실제 거래' if self.auto_trading else '시뮬레이션'}
📊 **현재 주기**: {self.frequency_manager.current_optimal_frequency}
🎯 **현재 포지션**: {self.trading_state.position or '없음'}

📈 **성과**:
- 총 거래: {self.total_trades}회
- 승률: {self.get_win_rate():.1f}%
- 총 수익: {self.total_profit:+.2f}%

⏰ **시작**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()

        self.telegram.send_message(start_message)

        try:
            last_learning_cycle = datetime.now()
            last_status_update = datetime.now()

            while self.running:
                # 거래 사이클 실행
                self.trading_cycle()

                # 적응형 학습 (1시간마다)
                if (datetime.now() - last_learning_cycle).total_seconds() >= 3600:
                    self.adaptive_learning_cycle()
                    last_learning_cycle = datetime.now()

                # 상태 업데이트 (6시간마다)
                if (datetime.now() - last_status_update).total_seconds() >= 21600:
                    self.send_status_update()
                    last_status_update = datetime.now()

                # 상태 저장
                self.save_state()

                # 대기 (현재 최적 주기)
                sleep_time = self.adaptive_config['base_check_interval']
                print(f"다음 체크까지 {sleep_time//60}분 대기...")
                time.sleep(sleep_time)

        except KeyboardInterrupt:
            print("\n⏹️ 사용자에 의한 중단")
        except Exception as e:
            print(f"\n❌ 시스템 오류: {e}")
            self.telegram.notify_error("자동매매 시스템 오류", str(e))
        finally:
            self.running = False
            self.save_state()

            # 종료 알림
            self.telegram.send_message(
                f"⏹️ **자동매매 중단**\n\n"
                f"실행 시간: {datetime.now() - self.start_time}\n"
                f"총 거래: {self.total_trades}회\n"
                f"승률: {self.get_win_rate():.1f}%\n"
                f"총 수익: {self.total_profit:+.2f}%"
            )

            print("🔚 24시간 자동매매 종료")

    def send_status_update(self):
        """상태 업데이트 전송"""
        uptime = datetime.now() - self.start_time
        uptime_str = f"{uptime.days}일 {uptime.seconds//3600}시간"

        current_pnl = self.trading_state.current_pnl if self.trading_state.position else 0.0

        status_message = f"""
📊 **자동매매 상태 업데이트**

⏱️ **가동 시간**: {uptime_str}
📊 **현재 주기**: {self.frequency_manager.current_optimal_frequency}
🎯 **포지션**: {self.trading_state.position or '없음'}
💰 **현재 PnL**: {current_pnl:+.2f}%

📈 **누적 성과**:
- 총 거래: {self.total_trades}회
- 승률: {self.get_win_rate():.1f}%
- 총 수익: {self.total_profit:+.2f}%

⚡ **시스템 상태**: 정상 운영 중
        """.strip()

        self.telegram.send_message(status_message)

def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="NVDL/NVDQ 24시간 적응형 자동매매 시스템")
    parser.add_argument('--api-key', type=str,
                       default="5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI",
                       help='FMP API 키')
    parser.add_argument('--simulation', action='store_true',
                       help='시뮬레이션 모드 (실제 거래 안함)')

    args = parser.parse_args()

    # 자동매매 시스템 생성
    auto_trading = not args.simulation
    trader = NVDLNVDQAdaptiveAutoTrader(args.api_key, auto_trading=auto_trading)

    # 데이터 및 모델 준비
    print("📊 데이터 수집 및 모델 학습 중...")
    if not trader.data_collector.load_data():
        trader.data_collector.collect_all_data()
        trader.data_collector.calculate_all_features()
        trader.data_collector.save_data()

    if not trader.trading_model.mass_learning():
        print("❌ 모델 학습 실패")
        return

    print("✅ 준비 완료!")

    # 자동매매 시작
    trader.run()

if __name__ == "__main__":
    main()