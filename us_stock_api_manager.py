#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
미국 주식 API 매니저
- 실제 NVDL/NVDQ 주문 실행
- 여러 브로커 API 지원 준비
- 포지션 관리 및 모니터링
"""

import json
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from abc import ABC, abstractmethod
import warnings
warnings.filterwarnings('ignore')

class BaseStockBroker(ABC):
    """주식 브로커 기본 클래스"""

    @abstractmethod
    def get_account_info(self) -> Dict:
        """계좌 정보 조회"""
        pass

    @abstractmethod
    def get_current_price(self, symbol: str) -> Optional[float]:
        """현재가 조회"""
        pass

    @abstractmethod
    def place_order(self, symbol: str, quantity: int, side: str, order_type: str = "MARKET") -> Dict:
        """주문 실행"""
        pass

    @abstractmethod
    def get_positions(self) -> List[Dict]:
        """포지션 조회"""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """주문 취소"""
        pass

class AlpacaBroker(BaseStockBroker):
    """Alpaca API 브로커 (예시)"""

    def __init__(self, api_key: str, secret_key: str, paper_trading: bool = True):
        self.api_key = api_key
        self.secret_key = secret_key
        self.paper_trading = paper_trading

        # API 엔드포인트
        if paper_trading:
            self.base_url = "https://paper-api.alpaca.markets"
        else:
            self.base_url = "https://api.alpaca.markets"

        self.headers = {
            'APCA-API-KEY-ID': api_key,
            'APCA-API-SECRET-KEY': secret_key,
            'Content-Type': 'application/json'
        }

        print(f"Alpaca 브로커 초기화 ({'페이퍼' if paper_trading else '실거래'})")

    def get_account_info(self) -> Dict:
        """계좌 정보 조회"""
        try:
            url = f"{self.base_url}/v2/account"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            account_data = response.json()
            return {
                'equity': float(account_data.get('equity', 0)),
                'cash': float(account_data.get('cash', 0)),
                'buying_power': float(account_data.get('buying_power', 0)),
                'portfolio_value': float(account_data.get('portfolio_value', 0))
            }

        except Exception as e:
            print(f"계좌 정보 조회 오류: {e}")
            return {}

    def get_current_price(self, symbol: str) -> Optional[float]:
        """현재가 조회"""
        try:
            url = f"{self.base_url}/v2/stocks/{symbol}/quotes/latest"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            quote_data = response.json()
            if 'quote' in quote_data:
                bid = float(quote_data['quote'].get('bid_price', 0))
                ask = float(quote_data['quote'].get('ask_price', 0))
                return (bid + ask) / 2 if bid > 0 and ask > 0 else None

            return None

        except Exception as e:
            print(f"{symbol} 현재가 조회 오류: {e}")
            return None

    def place_order(self, symbol: str, quantity: int, side: str, order_type: str = "market") -> Dict:
        """주문 실행"""
        try:
            url = f"{self.base_url}/v2/orders"

            order_data = {
                'symbol': symbol,
                'qty': str(quantity),
                'side': side.lower(),  # 'buy' or 'sell'
                'type': order_type.lower(),  # 'market', 'limit', 'stop'
                'time_in_force': 'day'
            }

            response = requests.post(url, headers=self.headers, json=order_data, timeout=10)
            response.raise_for_status()

            order_result = response.json()
            return {
                'success': True,
                'order_id': order_result.get('id'),
                'symbol': symbol,
                'quantity': quantity,
                'side': side,
                'status': order_result.get('status'),
                'filled_qty': order_result.get('filled_qty', 0),
                'filled_avg_price': order_result.get('filled_avg_price')
            }

        except Exception as e:
            print(f"주문 실행 오류 ({symbol} {side} {quantity}): {e}")
            return {
                'success': False,
                'error': str(e),
                'symbol': symbol,
                'quantity': quantity,
                'side': side
            }

    def get_positions(self) -> List[Dict]:
        """포지션 조회"""
        try:
            url = f"{self.base_url}/v2/positions"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            positions_data = response.json()
            positions = []

            for pos in positions_data:
                positions.append({
                    'symbol': pos.get('symbol'),
                    'quantity': int(pos.get('qty', 0)),
                    'side': 'long' if int(pos.get('qty', 0)) > 0 else 'short',
                    'avg_price': float(pos.get('avg_entry_price', 0)),
                    'current_price': float(pos.get('market_value', 0)) / max(abs(int(pos.get('qty', 1))), 1),
                    'unrealized_pnl': float(pos.get('unrealized_pl', 0)),
                    'unrealized_pnl_pct': float(pos.get('unrealized_plpc', 0)) * 100
                })

            return positions

        except Exception as e:
            print(f"포지션 조회 오류: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        """주문 취소"""
        try:
            url = f"{self.base_url}/v2/orders/{order_id}"
            response = requests.delete(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return True

        except Exception as e:
            print(f"주문 취소 오류 ({order_id}): {e}")
            return False

class MockBroker(BaseStockBroker):
    """모의 브로커 (테스트용)"""

    def __init__(self, initial_balance: float = 100000):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.positions = {}  # {symbol: {'qty': int, 'avg_price': float}}
        self.order_history = []
        print(f"모의 브로커 초기화 (초기 자금: ${initial_balance:,.2f})")

    def get_account_info(self) -> Dict:
        """계좌 정보 조회"""
        total_value = self.balance

        # 포지션 가치 계산
        for symbol, pos in self.positions.items():
            if pos['qty'] != 0:
                current_price = self._get_mock_price(symbol)
                total_value += pos['qty'] * current_price

        return {
            'equity': total_value,
            'cash': self.balance,
            'buying_power': self.balance,
            'portfolio_value': total_value
        }

    def _get_mock_price(self, symbol: str) -> float:
        """모의 현재가 (실제로는 FMP API에서 가져옴)"""
        # 기본 가격 (실제로는 FMP API 연동)
        mock_prices = {
            'NVDL': 45.0,
            'NVDQ': 18.5
        }
        return mock_prices.get(symbol, 100.0)

    def get_current_price(self, symbol: str) -> Optional[float]:
        """현재가 조회"""
        return self._get_mock_price(symbol)

    def place_order(self, symbol: str, quantity: int, side: str, order_type: str = "market") -> Dict:
        """주문 실행 (모의)"""
        try:
            current_price = self._get_mock_price(symbol)
            total_cost = quantity * current_price

            if side.lower() == 'buy':
                # 매수
                if self.balance >= total_cost:
                    self.balance -= total_cost

                    if symbol in self.positions:
                        # 기존 포지션에 추가
                        old_qty = self.positions[symbol]['qty']
                        old_avg = self.positions[symbol]['avg_price']
                        new_qty = old_qty + quantity
                        new_avg = (old_qty * old_avg + quantity * current_price) / new_qty

                        self.positions[symbol] = {'qty': new_qty, 'avg_price': new_avg}
                    else:
                        # 새로운 포지션
                        self.positions[symbol] = {'qty': quantity, 'avg_price': current_price}

                    order_result = {
                        'success': True,
                        'order_id': f"MOCK_{int(time.time())}",
                        'symbol': symbol,
                        'quantity': quantity,
                        'side': side,
                        'status': 'filled',
                        'filled_qty': quantity,
                        'filled_avg_price': current_price
                    }

                    print(f"모의 매수 완료: {symbol} {quantity}주 @ ${current_price:.2f}")
                    return order_result

                else:
                    return {
                        'success': False,
                        'error': '잔액 부족',
                        'symbol': symbol,
                        'quantity': quantity,
                        'side': side
                    }

            elif side.lower() == 'sell':
                # 매도
                if symbol in self.positions and self.positions[symbol]['qty'] >= quantity:
                    self.balance += total_cost
                    self.positions[symbol]['qty'] -= quantity

                    if self.positions[symbol]['qty'] == 0:
                        del self.positions[symbol]

                    order_result = {
                        'success': True,
                        'order_id': f"MOCK_{int(time.time())}",
                        'symbol': symbol,
                        'quantity': quantity,
                        'side': side,
                        'status': 'filled',
                        'filled_qty': quantity,
                        'filled_avg_price': current_price
                    }

                    print(f"모의 매도 완료: {symbol} {quantity}주 @ ${current_price:.2f}")
                    return order_result

                else:
                    return {
                        'success': False,
                        'error': '보유 수량 부족',
                        'symbol': symbol,
                        'quantity': quantity,
                        'side': side
                    }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'symbol': symbol,
                'quantity': quantity,
                'side': side
            }

    def get_positions(self) -> List[Dict]:
        """포지션 조회"""
        positions = []

        for symbol, pos in self.positions.items():
            if pos['qty'] != 0:
                current_price = self._get_mock_price(symbol)
                unrealized_pnl = (current_price - pos['avg_price']) * pos['qty']
                unrealized_pnl_pct = ((current_price / pos['avg_price']) - 1) * 100

                positions.append({
                    'symbol': symbol,
                    'quantity': pos['qty'],
                    'side': 'long' if pos['qty'] > 0 else 'short',
                    'avg_price': pos['avg_price'],
                    'current_price': current_price,
                    'unrealized_pnl': unrealized_pnl,
                    'unrealized_pnl_pct': unrealized_pnl_pct
                })

        return positions

    def cancel_order(self, order_id: str) -> bool:
        """주문 취소 (모의)"""
        print(f"모의 주문 취소: {order_id}")
        return True

class USStockAPIManager:
    """미국 주식 API 매니저"""

    def __init__(self, broker_type: str = "mock", **broker_config):
        """
        미국 주식 API 매니저 초기화

        Args:
            broker_type: 브로커 타입 ('alpaca', 'mock')
            **broker_config: 브로커별 설정
        """
        self.broker_type = broker_type

        if broker_type == "alpaca":
            self.broker = AlpacaBroker(
                api_key=broker_config.get('api_key'),
                secret_key=broker_config.get('secret_key'),
                paper_trading=broker_config.get('paper_trading', True)
            )
        elif broker_type == "mock":
            self.broker = MockBroker(
                initial_balance=broker_config.get('initial_balance', 100000)
            )
        else:
            raise ValueError(f"지원하지 않는 브로커 타입: {broker_type}")

        self.trading_symbols = ['NVDL', 'NVDQ']
        self.position_size_usd = broker_config.get('position_size_usd', 1000)  # 기본 $1000
        self.last_orders = {}

        print(f"미국 주식 API 매니저 초기화 완료: {broker_type}")

    def get_account_summary(self) -> Dict:
        """계좌 요약 정보"""
        account_info = self.broker.get_account_info()
        positions = self.broker.get_positions()

        summary = {
            'account_info': account_info,
            'positions': positions,
            'total_positions': len(positions),
            'nvdl_position': None,
            'nvdq_position': None
        }

        # NVDL/NVDQ 포지션 찾기
        for pos in positions:
            if pos['symbol'] == 'NVDL':
                summary['nvdl_position'] = pos
            elif pos['symbol'] == 'NVDQ':
                summary['nvdq_position'] = pos

        return summary

    def calculate_position_size(self, symbol: str, current_price: float) -> int:
        """포지션 크기 계산"""
        if current_price <= 0:
            return 0

        # 달러 기준 포지션 크기를 주식 수로 변환
        quantity = int(self.position_size_usd / current_price)
        return max(1, quantity)  # 최소 1주

    def open_position(self, symbol: str) -> Dict:
        """포지션 열기"""
        try:
            current_price = self.broker.get_current_price(symbol)
            if not current_price:
                return {'success': False, 'error': f'{symbol} 현재가 조회 실패'}

            quantity = self.calculate_position_size(symbol, current_price)

            # 기존 반대 포지션 확인 및 청산
            self.close_opposite_position(symbol)

            # 새로운 포지션 열기
            order_result = self.broker.place_order(symbol, quantity, 'buy', 'market')

            if order_result.get('success'):
                self.last_orders[symbol] = {
                    'order_id': order_result.get('order_id'),
                    'timestamp': datetime.now(),
                    'action': 'open',
                    'quantity': quantity,
                    'price': current_price
                }

                print(f"✅ {symbol} 포지션 열기 성공: {quantity}주 @ ${current_price:.2f}")
                return {
                    'success': True,
                    'symbol': symbol,
                    'quantity': quantity,
                    'price': current_price,
                    'order_id': order_result.get('order_id')
                }
            else:
                print(f"❌ {symbol} 포지션 열기 실패: {order_result.get('error')}")
                return order_result

        except Exception as e:
            error_msg = f"{symbol} 포지션 열기 오류: {e}"
            print(f"❌ {error_msg}")
            return {'success': False, 'error': error_msg}

    def close_position(self, symbol: str) -> Dict:
        """포지션 닫기"""
        try:
            # 현재 포지션 확인
            positions = self.broker.get_positions()
            target_position = None

            for pos in positions:
                if pos['symbol'] == symbol and pos['quantity'] != 0:
                    target_position = pos
                    break

            if not target_position:
                return {'success': False, 'error': f'{symbol} 포지션이 없습니다'}

            quantity = abs(target_position['quantity'])
            side = 'sell' if target_position['quantity'] > 0 else 'buy'

            # 청산 주문 실행
            order_result = self.broker.place_order(symbol, quantity, side, 'market')

            if order_result.get('success'):
                current_price = order_result.get('filled_avg_price') or self.broker.get_current_price(symbol)

                self.last_orders[symbol] = {
                    'order_id': order_result.get('order_id'),
                    'timestamp': datetime.now(),
                    'action': 'close',
                    'quantity': quantity,
                    'price': current_price
                }

                print(f"✅ {symbol} 포지션 닫기 성공: {quantity}주 @ ${current_price:.2f}")
                return {
                    'success': True,
                    'symbol': symbol,
                    'quantity': quantity,
                    'price': current_price,
                    'order_id': order_result.get('order_id'),
                    'pnl': target_position.get('unrealized_pnl', 0),
                    'pnl_pct': target_position.get('unrealized_pnl_pct', 0)
                }
            else:
                print(f"❌ {symbol} 포지션 닫기 실패: {order_result.get('error')}")
                return order_result

        except Exception as e:
            error_msg = f"{symbol} 포지션 닫기 오류: {e}"
            print(f"❌ {error_msg}")
            return {'success': False, 'error': error_msg}

    def close_opposite_position(self, new_symbol: str):
        """반대 포지션 청산"""
        opposite_symbol = 'NVDQ' if new_symbol == 'NVDL' else 'NVDL'

        positions = self.broker.get_positions()
        for pos in positions:
            if pos['symbol'] == opposite_symbol and pos['quantity'] != 0:
                print(f"반대 포지션 {opposite_symbol} 청산 중...")
                self.close_position(opposite_symbol)
                break

    def close_all_positions(self) -> List[Dict]:
        """모든 포지션 청산"""
        results = []
        positions = self.broker.get_positions()

        for pos in positions:
            if pos['quantity'] != 0 and pos['symbol'] in self.trading_symbols:
                result = self.close_position(pos['symbol'])
                results.append(result)

        return results

    def get_current_position(self) -> Optional[str]:
        """현재 보유 포지션 확인"""
        positions = self.broker.get_positions()

        for pos in positions:
            if pos['symbol'] in self.trading_symbols and pos['quantity'] != 0:
                return pos['symbol']

        return None

    def is_market_open(self) -> bool:
        """미국 시장 개장 여부 확인"""
        now = datetime.now()

        # 단순 시간 체크 (실제로는 휴일 등도 고려해야 함)
        # 미국 동부시간 기준 9:30 - 16:00 (한국시간으로는 복잡함)
        # 여기서는 24시간 거래 가능한 것으로 가정
        return True

    def print_account_status(self):
        """계좌 상태 출력"""
        print("\n" + "="*50)
        print("📊 계좌 상태")
        print("="*50)

        summary = self.get_account_summary()
        account_info = summary['account_info']

        if account_info:
            print(f"💰 총 자산: ${account_info.get('equity', 0):,.2f}")
            print(f"💵 현금: ${account_info.get('cash', 0):,.2f}")
            print(f"📈 포트폴리오: ${account_info.get('portfolio_value', 0):,.2f}")

        positions = summary['positions']
        if positions:
            print(f"\n📊 포지션 ({len(positions)}개):")
            for pos in positions:
                symbol = pos['symbol']
                qty = pos['quantity']
                pnl_pct = pos['unrealized_pnl_pct']
                print(f"  {symbol}: {qty}주 | PnL: {pnl_pct:+.2f}%")
        else:
            print("\n📊 포지션: 없음")

        print("="*50)

def main():
    """테스트 실행"""
    print("미국 주식 API 매니저 테스트")

    # 모의 브로커로 테스트
    api_manager = USStockAPIManager(
        broker_type="mock",
        initial_balance=50000,
        position_size_usd=2000
    )

    # 계좌 상태 확인
    api_manager.print_account_status()

    # NVDL 포지션 열기
    result = api_manager.open_position('NVDL')
    print(f"NVDL 포지션 열기 결과: {result}")

    # 계좌 상태 재확인
    api_manager.print_account_status()

    # NVDQ로 전환 (NVDL 자동 청산됨)
    result = api_manager.open_position('NVDQ')
    print(f"NVDQ 포지션 열기 결과: {result}")

    # 최종 계좌 상태
    api_manager.print_account_status()

    # 모든 포지션 청산
    results = api_manager.close_all_positions()
    print(f"모든 포지션 청산 결과: {results}")

    # 최종 상태
    api_manager.print_account_status()

if __name__ == "__main__":
    main()