#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
한국투자증권 USD 현금 잔고 추적기
- API로 조회 불가한 USD 현금을 시뮬레이션으로 추적
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional
from kis_balance_checker import KISBalanceChecker

class KISUSDBalanceTracker:
    """USD 현금 잔고 추적 클래스"""

    def __init__(self, initial_usd: float = 0.0, tracker_file: str = "usd_balance_tracker.json"):
        """
        초기화

        Args:
            initial_usd: 초기 USD 입금액
            tracker_file: 추적 데이터 파일
        """
        self.tracker_file = tracker_file
        self.balance_checker = KISBalanceChecker()

        # 추적 데이터 로드
        self.data = self._load_tracker_data()

        # 초기 USD 설정 (파일에 없으면 파라미터 값 사용)
        if 'initial_usd' not in self.data:
            self.data['initial_usd'] = initial_usd
            self.data['current_usd'] = initial_usd
            self.data['total_invested'] = 0.0
            self.data['realized_pnl'] = 0.0
            self.data['trade_history'] = []
            self._save_tracker_data()

        print(f"[USDTracker] 초기화 완료 - 초기금액: ${self.data['initial_usd']:.2f}")

    def _load_tracker_data(self) -> Dict:
        """추적 데이터 로드"""
        if os.path.exists(self.tracker_file):
            try:
                with open(self.tracker_file, 'r') as f:
                    return json.load(f)
            except:
                pass

        return {}

    def _save_tracker_data(self):
        """추적 데이터 저장"""
        try:
            with open(self.tracker_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"[ERROR] 추적 데이터 저장 실패: {e}")

    def get_current_usd_balance(self) -> float:
        """
        현재 USD 현금 잔고 계산

        계산 로직:
        초기금액 + 실현손익 - 보유주식평가금액
        """
        # 실제 보유 주식 평가금액 조회
        balance = self.balance_checker.get_overseas_balance()
        total_stock_value = balance['total_value']

        # 현금 = 초기금액 + 실현손익 - 보유주식
        estimated_cash = (
            self.data['initial_usd'] +
            self.data['realized_pnl'] -
            total_stock_value
        )

        # 음수 방지
        estimated_cash = max(0.0, estimated_cash)

        self.data['current_usd'] = estimated_cash
        self.data['last_check'] = datetime.now().isoformat()

        return estimated_cash

    def record_buy(self, symbol: str, quantity: int, price: float) -> bool:
        """
        매수 기록

        Args:
            symbol: 종목 코드
            quantity: 수량
            price: 가격

        Returns:
            성공 여부
        """
        cost = quantity * price
        current_cash = self.get_current_usd_balance()

        if current_cash < cost:
            print(f"[ERROR] 현금 부족: ${current_cash:.2f} < ${cost:.2f}")
            return False

        # 매수 기록
        trade = {
            'type': 'BUY',
            'symbol': symbol,
            'quantity': quantity,
            'price': price,
            'cost': cost,
            'timestamp': datetime.now().isoformat()
        }

        self.data['trade_history'].append(trade)
        self.data['current_usd'] -= cost
        self._save_tracker_data()

        print(f"[BUY] {symbol} {quantity}주 @ ${price:.2f} = ${cost:.2f}")
        print(f"  남은 현금: ${self.data['current_usd']:.2f}")

        return True

    def record_sell(self, symbol: str, quantity: int, price: float, buy_price: float):
        """
        매도 기록

        Args:
            symbol: 종목 코드
            quantity: 수량
            price: 매도 가격
            buy_price: 매수 평균가
        """
        revenue = quantity * price
        cost = quantity * buy_price
        pnl = revenue - cost

        # 매도 기록
        trade = {
            'type': 'SELL',
            'symbol': symbol,
            'quantity': quantity,
            'price': price,
            'revenue': revenue,
            'cost': cost,
            'pnl': pnl,
            'timestamp': datetime.now().isoformat()
        }

        self.data['trade_history'].append(trade)
        self.data['current_usd'] += revenue
        self.data['realized_pnl'] += pnl
        self._save_tracker_data()

        print(f"[SELL] {symbol} {quantity}주 @ ${price:.2f} = ${revenue:.2f}")
        print(f"  손익: ${pnl:+.2f} ({pnl/cost*100:+.2f}%)")
        print(f"  현금: ${self.data['current_usd']:.2f}")

    def get_buying_power(self) -> float:
        """매수 가능 금액"""
        return self.get_current_usd_balance()

    def can_buy(self, symbol: str, quantity: int, price: float) -> bool:
        """매수 가능 여부"""
        cost = quantity * price
        return self.get_current_usd_balance() >= cost

    def get_summary(self) -> Dict:
        """계좌 요약"""
        balance = self.balance_checker.get_overseas_balance()

        return {
            'initial_usd': self.data['initial_usd'],
            'current_usd': self.get_current_usd_balance(),
            'stock_value': balance['total_value'],
            'total_value': self.get_current_usd_balance() + balance['total_value'],
            'realized_pnl': self.data['realized_pnl'],
            'unrealized_pnl': balance['total_pnl'],
            'total_pnl': self.data['realized_pnl'] + balance['total_pnl'],
            'num_trades': len(self.data['trade_history']),
            'holdings': balance['holdings']
        }

    def print_summary(self):
        """요약 출력"""
        summary = self.get_summary()

        print("\n" + "="*80)
        print("USD 잔고 추적 요약")
        print("="*80)
        print(f"초기 입금: ${summary['initial_usd']:.2f}")
        print(f"현재 현금: ${summary['current_usd']:.2f}")
        print(f"주식 평가: ${summary['stock_value']:.2f}")
        print(f"총 자산: ${summary['total_value']:.2f}")
        print(f"\n실현 손익: ${summary['realized_pnl']:+.2f}")
        print(f"미실현 손익: ${summary['unrealized_pnl']:+.2f}")
        print(f"총 손익: ${summary['total_pnl']:+.2f} ({summary['total_pnl']/summary['initial_usd']*100:+.2f}%)")
        print(f"\n거래 횟수: {summary['num_trades']}")
        print("="*80)

    def reset(self, new_initial_usd: float):
        """추적 데이터 초기화"""
        self.data = {
            'initial_usd': new_initial_usd,
            'current_usd': new_initial_usd,
            'total_invested': 0.0,
            'realized_pnl': 0.0,
            'trade_history': []
        }
        self._save_tracker_data()
        print(f"[RESET] 추적 데이터 초기화 - 새 금액: ${new_initial_usd:.2f}")


def main():
    """테스트"""
    # 초기 입금 $104 (예시)
    tracker = KISUSDBalanceTracker(initial_usd=104.0)

    # 현재 잔고 확인
    tracker.print_summary()

    # 실제 보유 종목과 비교
    print("\n실제 보유 종목:")
    balance = tracker.balance_checker.get_overseas_balance()
    for holding in balance['holdings']:
        print(f"  {holding['symbol']}: {holding['qty']}주 @ ${holding['avg_price']:.2f}")

    # 계산된 현금 잔고
    estimated_cash = tracker.get_current_usd_balance()
    print(f"\n계산된 USD 현금: ${estimated_cash:.2f}")


if __name__ == "__main__":
    main()
