#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
한국투자증권 추세돌파 트레이더
- 추세 신호 변경 시 포지션 전환
- 수익 0 수렴 시 조기 청산
- USD 잔고 추적 통합
"""

import time
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from kis_balance_checker import KISBalanceChecker
from kis_usd_balance_tracker import KISUSDBalanceTracker
from simple_auto_trader import SimpleAutoTrader

class TrendBreakthroughTrader(SimpleAutoTrader):
    """추세돌파 전략 트레이더"""

    def __init__(self, initial_usd: float = 104.0, target_symbols: List[str] = None):
        """
        초기화

        Args:
            initial_usd: 초기 USD 입금액
            target_symbols: 거래 대상 종목 리스트
        """
        super().__init__()

        # USD 잔고 추적기
        self.usd_tracker = KISUSDBalanceTracker(initial_usd=initial_usd)

        # 거래 대상 종목 (레버리지 ETF 쌍)
        self.target_symbols = target_symbols or ['SOXL', 'SOXS']

        # 추세돌파 설정
        self.trend_signal = None  # 'BULL' or 'BEAR'
        self.last_signal_change = None
        self.position_entry_time = None

        # 수익 추적
        self.max_profit_pct = 0.0  # 최고 수익률 (0 수렴 감지용)
        self.profit_peak_time = None

        # 전략 파라미터
        self.min_profit_to_hold = 0.3  # 최소 유지 수익률 0.3%
        self.profit_decay_threshold = 0.1  # 수익 0.1% 이하로 떨어지면 청산
        self.max_position_time = 30 * 60  # 최대 보유 시간 30분
        self.take_profit_target = 1.0  # 목표 수익률 1.0%
        self.stop_loss_pct = -0.5  # 손절 -0.5%

        # 추세 판단용 가격 히스토리
        self.price_history = []
        self.max_history_len = 20

        print(f"[TrendTrader] 초기화 완료")
        print(f"  초기 자금: ${initial_usd:.2f}")
        print(f"  거래 종목: {', '.join(self.target_symbols)}")
        print(f"  목표 수익: {self.take_profit_target}%")
        print(f"  손절: {self.stop_loss_pct}%")

    def detect_trend_signal(self) -> Optional[str]:
        """
        추세 신호 감지 (간단한 이동평균 기반)

        Returns:
            'BULL': 상승 추세 (SOXL 매수)
            'BEAR': 하락 추세 (SOXS 매수)
            None: 신호 없음
        """
        if len(self.price_history) < 10:
            return None

        # 최근 10개 가격의 이동평균
        recent_prices = self.price_history[-10:]
        ma_short = sum(recent_prices[-5:]) / 5  # 단기 MA (5)
        ma_long = sum(recent_prices[-10:]) / 10  # 장기 MA (10)

        # 현재 가격
        current_price = recent_prices[-1]

        # 골든크로스/데드크로스
        if ma_short > ma_long and current_price > ma_short:
            return 'BULL'
        elif ma_short < ma_long and current_price < ma_short:
            return 'BEAR'

        return None

    def should_switch_position(self, current_signal: str, current_position: Optional[str]) -> bool:
        """
        포지션 전환 필요 여부

        Args:
            current_signal: 현재 추세 신호
            current_position: 현재 포지션 종목

        Returns:
            전환 필요 여부
        """
        if not current_signal:
            return False

        # 신호와 포지션 매칭
        signal_to_symbol = {
            'BULL': 'SOXL',
            'BEAR': 'SOXS'
        }

        target_symbol = signal_to_symbol.get(current_signal)

        # 신호가 바뀌면 포지션 전환
        if current_position and current_position != target_symbol:
            return True

        return False

    def should_exit_for_profit_decay(self, current_pnl_pct: float) -> bool:
        """
        수익 0 수렴으로 인한 청산 필요 여부

        로직:
        1. 수익이 min_profit_to_hold (0.3%) 이상 발생
        2. 수익이 profit_decay_threshold (0.1%) 이하로 하락
        3. -> 수수료 고려해서 미리 청산

        Args:
            current_pnl_pct: 현재 손익률 (%)

        Returns:
            청산 필요 여부
        """
        # 최고 수익 갱신
        if current_pnl_pct > self.max_profit_pct:
            self.max_profit_pct = current_pnl_pct
            self.profit_peak_time = datetime.now()

        # 수익이 한번이라도 0.3% 이상 발생했는가?
        if self.max_profit_pct >= self.min_profit_to_hold:
            # 현재 수익이 0.1% 이하로 떨어졌는가?
            if current_pnl_pct <= self.profit_decay_threshold:
                print(f"\n[수익 0 수렴 감지] 최고 {self.max_profit_pct:.2f}% -> 현재 {current_pnl_pct:.2f}%")
                print(f"  수수료 고려하여 조기 청산")
                return True

        return False

    def execute_trend_strategy(self):
        """추세돌파 전략 실행"""
        print("\n" + "="*80)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 추세돌파 전략 실행")
        print("="*80)

        # 1. 잔고 확인
        balance = self.balance_checker.get_overseas_balance(self.exchange_cd, self.currency)
        usd_summary = self.usd_tracker.get_summary()

        print(f"\n[계좌 현황]")
        print(f"  USD 현금: ${usd_summary['current_usd']:.2f}")
        print(f"  주식 평가: ${usd_summary['stock_value']:.2f}")
        print(f"  총 자산: ${usd_summary['total_value']:.2f}")
        print(f"  총 손익: ${usd_summary['total_pnl']:+.2f} ({usd_summary['total_pnl']/usd_summary['initial_usd']*100:+.2f}%)")

        # 2. 현재 포지션 확인
        current_position = None
        current_qty = 0
        current_avg_price = 0
        current_pnl_pct = 0

        for holding in balance['holdings']:
            symbol = holding['symbol']
            if symbol in self.target_symbols:
                current_position = symbol
                current_qty = holding['qty']
                current_avg_price = holding['avg_price']
                current_pnl_pct = holding['pnl_pct']

                print(f"\n[보유중] {symbol}: {current_qty}주 @ ${current_avg_price:.2f}")
                print(f"  손익: {current_pnl_pct:+.2f}%")
                break

        # 3. 가격 조회 및 히스토리 업데이트
        if current_position:
            current_price = self.balance_checker.get_realtime_price(current_position, self.exchange_cd)

            if not current_price:
                # 실시간 가격 조회 실패시 잔고의 가격 사용
                current_price = current_avg_price * (1 + current_pnl_pct / 100)

            self.price_history.append(current_price)
            if len(self.price_history) > self.max_history_len:
                self.price_history.pop(0)

            print(f"\n[현재가] {current_position}: ${current_price:.2f}")

        # 4. 추세 신호 감지
        new_signal = self.detect_trend_signal()

        if new_signal:
            print(f"\n[추세 신호] {new_signal}")

            if new_signal != self.trend_signal:
                print(f"  신호 변경: {self.trend_signal} -> {new_signal}")
                self.last_signal_change = datetime.now()

            self.trend_signal = new_signal

        # 5. 청산 조건 체크
        should_exit = False
        exit_reason = ""

        if current_position:
            # 5-1. 신호 변경으로 인한 포지션 전환
            if self.should_switch_position(self.trend_signal, current_position):
                should_exit = True
                exit_reason = f"신호 변경 ({self.trend_signal})"

            # 5-2. 수익 0 수렴
            elif self.should_exit_for_profit_decay(current_pnl_pct):
                should_exit = True
                exit_reason = "수익 0 수렴"

            # 5-3. 목표 수익 달성
            elif current_pnl_pct >= self.take_profit_target:
                should_exit = True
                exit_reason = f"목표 수익 달성 ({current_pnl_pct:.2f}% >= {self.take_profit_target}%)"

            # 5-4. 손절
            elif current_pnl_pct <= self.stop_loss_pct:
                should_exit = True
                exit_reason = f"손절 ({current_pnl_pct:.2f}% <= {self.stop_loss_pct}%)"

            # 5-5. 최대 보유 시간 초과
            if self.position_entry_time:
                holding_time = (datetime.now() - self.position_entry_time).total_seconds()
                if holding_time > self.max_position_time:
                    should_exit = True
                    exit_reason = f"최대 보유 시간 초과 ({holding_time/60:.0f}분)"

        # 6. 청산 실행
        if should_exit:
            print(f"\n[청산 시그널] {exit_reason}")
            print(f"  매도 예정: {current_position} {current_qty}주")

            # 실제 매도 (주석 해제시 실행)
            # result = self.sell_stock(current_position, int(current_qty))
            # if result.get('success'):
            #     self.usd_tracker.record_sell(current_position, int(current_qty), current_price, current_avg_price)
            #     self.max_profit_pct = 0.0
            #     self.position_entry_time = None

            # 테스트 모드
            print(f"  [테스트 모드] 실제 주문은 하지 않습니다")

        # 7. 신규 진입 (청산 후 또는 무포지션)
        if not current_position or should_exit:
            if self.trend_signal:
                signal_to_symbol = {
                    'BULL': 'SOXL',
                    'BEAR': 'SOXS'
                }

                target_symbol = signal_to_symbol[self.trend_signal]
                target_price = self.balance_checker.get_realtime_price(target_symbol, self.exchange_cd)

                if target_price and usd_summary['current_usd'] > 0:
                    max_qty = int(usd_summary['current_usd'] / target_price)
                    buy_qty = min(1, max_qty)  # 1주씩 매수

                    if buy_qty > 0:
                        print(f"\n[신규 진입] {target_symbol} {buy_qty}주 @ ${target_price:.2f}")

                        # 실제 매수 (주석 해제시 실행)
                        # result = self.buy_stock(target_symbol, buy_qty)
                        # if result.get('success'):
                        #     self.usd_tracker.record_buy(target_symbol, buy_qty, target_price)
                        #     self.position_entry_time = datetime.now()
                        #     self.max_profit_pct = 0.0

                        # 테스트 모드
                        print(f"  [테스트 모드] 실제 주문은 하지 않습니다")

        print("\n" + "="*80)

    def run(self, interval_seconds: int = 60):
        """
        자동매매 실행

        Args:
            interval_seconds: 체크 간격 (초)
        """
        print(f"\n[추세돌파 트레이더 시작] 체크 간격: {interval_seconds}초")

        while True:
            try:
                self.execute_trend_strategy()
                print(f"\n{interval_seconds}초 대기 중...")
                time.sleep(interval_seconds)

            except KeyboardInterrupt:
                print("\n\n[종료] 사용자가 중단했습니다")
                break
            except Exception as e:
                print(f"\n[ERROR] 오류 발생: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(interval_seconds)


def main():
    """테스트"""
    # 초기 USD $104 (SOXL 2주 매수 후 남은 금액 포함)
    trader = TrendBreakthroughTrader(initial_usd=104.0, target_symbols=['SOXL', 'SOXS'])

    # 1회 실행
    trader.execute_trend_strategy()

    # 자동매매 루프 (주석 해제시 실행)
    # trader.run(interval_seconds=60)


if __name__ == "__main__":
    main()
