#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 자동매매 시스템
- 잔고 확인
- 실시간 가격 조회
- 매수/매도 로직
"""

import yaml
import requests
import json
import time
from datetime import datetime
from kis_balance_checker import KISBalanceChecker

class SimpleAutoTrader:
    """간단한 자동매매 시스템"""

    def __init__(self, config_path: str = None):
        """초기화"""
        if config_path is None:
            config_path = 'kis_devlp.yaml'

        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        # 잔고 조회 클래스
        self.balance_checker = KISBalanceChecker(config_path)

        # 토큰
        with open('kis_token.json', 'r') as f:
            token_data = json.load(f)
            self.access_token = token_data['access_token']

        # 계좌번호
        acct_parts = self.config['my_acct'].split('-')
        self.cano = acct_parts[0]
        self.acnt_prdt_cd = acct_parts[1] if len(acct_parts) > 1 else "01"

        # API URL
        self.base_url = "https://openapi.koreainvestment.com:9443"

        # 거래 파라미터
        self.exchange_cd = "NASD"
        self.currency = "USD"

        print(f"[SimpleAutoTrader] 초기화 완료")

    def get_hashkey(self, data: dict) -> str:
        """해시키 생성"""
        url = f"{self.base_url}/uapi/hashkey"

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "appkey": self.config['my_app'],
            "appsecret": self.config['my_sec'],
            "User-Agent": self.config.get('my_agent', 'Mozilla/5.0')
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                return result.get('HASH', '')
        except Exception as e:
            print(f"[ERROR] 해시키 생성 실패: {e}")

        return ""

    def buy_stock(self, symbol: str, quantity: int, price: float = 0) -> dict:
        """
        해외주식 매수

        Args:
            symbol: 종목 코드
            quantity: 수량
            price: 가격 (0이면 시장가)

        Returns:
            주문 결과
        """
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/order"

        order_data = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": self.exchange_cd,
            "PDNO": symbol,
            "ORD_QTY": str(quantity),
            "OVRS_ORD_UNPR": "0" if price == 0 else str(price),
            "ORD_SVR_DVSN_CD": "0",  # 0:일반, 1:예약
            "ORD_DVSN": "00" if price == 0 else "01"  # 00:시장가, 01:지정가
        }

        hashkey = self.get_hashkey(order_data)

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.config['my_app'],
            "appsecret": self.config['my_sec'],
            "tr_id": "JTTT1002U",  # 해외주식 매수
            "custtype": "P",
            "hashkey": hashkey,
            "User-Agent": self.config.get('my_agent', 'Mozilla/5.0')
        }

        try:
            response = requests.post(url, headers=headers, json=order_data, timeout=10)

            if response.status_code != 200:
                return {'success': False, 'error': f'HTTP {response.status_code}', 'response': response.text}

            result = response.json()

            if result.get('rt_cd') == '0':
                return {
                    'success': True,
                    'order_no': result.get('output', {}).get('odno', ''),
                    'symbol': symbol,
                    'quantity': quantity,
                    'message': result.get('msg1', '')
                }
            else:
                return {
                    'success': False,
                    'error': result.get('msg1', ''),
                    'msg_cd': result.get('msg_cd', ''),
                    'response': result
                }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def sell_stock(self, symbol: str, quantity: int, price: float = 0) -> dict:
        """
        해외주식 매도

        Args:
            symbol: 종목 코드
            quantity: 수량
            price: 가격 (0이면 시장가)

        Returns:
            주문 결과
        """
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/order"

        order_data = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": self.exchange_cd,
            "PDNO": symbol,
            "ORD_QTY": str(quantity),
            "OVRS_ORD_UNPR": "0" if price == 0 else str(price),
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": "00" if price == 0 else "01"
        }

        hashkey = self.get_hashkey(order_data)

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.config['my_app'],
            "appsecret": self.config['my_sec'],
            "tr_id": "JTTT1006U",  # 해외주식 매도
            "custtype": "P",
            "hashkey": hashkey,
            "User-Agent": self.config.get('my_agent', 'Mozilla/5.0')
        }

        try:
            response = requests.post(url, headers=headers, json=order_data, timeout=10)

            if response.status_code != 200:
                return {'success': False, 'error': f'HTTP {response.status_code}', 'response': response.text}

            result = response.json()

            if result.get('rt_cd') == '0':
                return {
                    'success': True,
                    'order_no': result.get('output', {}).get('odno', ''),
                    'symbol': symbol,
                    'quantity': quantity,
                    'message': result.get('msg1', '')
                }
            else:
                return {
                    'success': False,
                    'error': result.get('msg1', ''),
                    'msg_cd': result.get('msg_cd', ''),
                    'response': result
                }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def check_and_trade(self, target_symbol: str, buy_threshold_pct: float = -2.0, sell_threshold_pct: float = 5.0):
        """
        잔고 확인 후 매매 결정

        Args:
            target_symbol: 거래할 종목 (SOXL, NVDL 등)
            buy_threshold_pct: 매수 기준 (하락률 %)
            sell_threshold_pct: 매도 기준 (상승률 %)
        """
        print("\n" + "="*80)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 매매 체크 시작")
        print("="*80)

        # 1. 잔고 확인
        balance = self.balance_checker.get_overseas_balance(self.exchange_cd, self.currency)

        print(f"\n[잔고 현황]")
        print(f"  총 투자금액: ${balance['total_invested']:.2f}")
        print(f"  총 평가금액: ${balance['total_value']:.2f}")
        print(f"  총 손익: ${balance['total_pnl']:.2f} ({balance['total_pnl_pct']:+.2f}%)")
        print(f"  USD 현금: ${balance['usd_cash']:.2f}")

        # 2. 보유 종목 확인
        has_position = False
        position_qty = 0
        position_avg_price = 0
        position_pnl_pct = 0

        for holding in balance['holdings']:
            if holding['symbol'] == target_symbol:
                has_position = True
                position_qty = holding['qty']
                position_avg_price = holding['avg_price']
                position_pnl_pct = holding['pnl_pct']
                print(f"\n[보유중] {target_symbol}: {position_qty}주 @ ${position_avg_price:.2f} (손익: {position_pnl_pct:+.2f}%)")
                break

        # 3. 실시간 가격 조회 (실패시 잔고의 야간시세 사용)
        current_price = self.balance_checker.get_realtime_price(target_symbol, self.exchange_cd)

        if not current_price:
            # 실시간 가격 조회 실패 -> 잔고의 야간시세 사용
            if has_position:
                for holding in balance['holdings']:
                    if holding['symbol'] == target_symbol:
                        current_price = holding['current_price']
                        print(f"\n[야간시세] {target_symbol}: ${current_price:.2f} (실시간 가격 조회 실패, 잔고의 가격 사용)")
                        break

            if not current_price:
                print(f"\n[ERROR] {target_symbol} 가격 정보 없음 (실시간/야간시세 모두 실패)")
                return
        else:
            print(f"\n[실시간 가격] {target_symbol}: ${current_price:.2f}")

        # 4. 매매 결정
        if has_position:
            # 보유중: 익절/손절 체크
            if position_pnl_pct >= sell_threshold_pct:
                print(f"\n[매도 시그널] 익절 기준 도달 ({position_pnl_pct:+.2f}% >= {sell_threshold_pct}%)")
                print(f"  매도 예정: {target_symbol} {position_qty}주")

                # 실제 매도 (주석 해제시 실행)
                # result = self.sell_stock(target_symbol, position_qty)
                # print(f"  매도 결과: {result}")

                # 테스트용
                print(f"  [테스트 모드] 실제 주문은 하지 않습니다")

            elif position_pnl_pct <= buy_threshold_pct:
                print(f"\n[추가매수 고려] 손실 확대 ({position_pnl_pct:+.2f}% <= {buy_threshold_pct}%)")
                print(f"  평균단가 낮추기 전략을 고려하세요")

            else:
                print(f"\n[보유 유지] 손익률 {position_pnl_pct:+.2f}% (매도기준: {sell_threshold_pct}%)")

        else:
            # 미보유: 매수 기회 체크
            print(f"\n[미보유] {target_symbol} 매수 기회 탐색")
            print(f"  현재가: ${current_price:.2f}")
            print(f"  USD 현금: ${balance['usd_cash']:.2f}")

            if balance['usd_cash'] > 0:
                max_qty = int(balance['usd_cash'] / current_price)
                print(f"  최대 매수 가능: {max_qty}주")

                # 매수 로직 (예: 1주 매수)
                buy_qty = min(1, max_qty)

                if buy_qty > 0:
                    print(f"\n[매수 시그널] {target_symbol} {buy_qty}주 매수 예정")

                    # 실제 매수 (주석 해제시 실행)
                    # result = self.buy_stock(target_symbol, buy_qty)
                    # print(f"  매수 결과: {result}")

                    # 테스트용
                    print(f"  [테스트 모드] 실제 주문은 하지 않습니다")
                else:
                    print(f"\n[매수 불가] 현금 부족")
            else:
                print(f"\n[매수 불가] USD 현금 없음")

        print("\n" + "="*80)

    def run_trading_loop(self, target_symbol: str = "SOXL", interval_seconds: int = 60):
        """
        자동매매 루프 실행

        Args:
            target_symbol: 거래할 종목
            interval_seconds: 체크 간격 (초)
        """
        print(f"[자동매매 시작] 종목: {target_symbol}, 체크 간격: {interval_seconds}초")

        while True:
            try:
                self.check_and_trade(target_symbol)
                print(f"\n{interval_seconds}초 대기 중...")
                time.sleep(interval_seconds)

            except KeyboardInterrupt:
                print("\n\n[종료] 사용자가 중단했습니다")
                break
            except Exception as e:
                print(f"\n[ERROR] 오류 발생: {e}")
                time.sleep(interval_seconds)


def main():
    """테스트 실행"""
    trader = SimpleAutoTrader()

    # 1회 체크
    trader.check_and_trade("SOXL")

    # 자동매매 루프 (주석 해제시 실행)
    # trader.run_trading_loop("SOXL", interval_seconds=300)


if __name__ == "__main__":
    main()
