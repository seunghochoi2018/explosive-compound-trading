#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
한국투자증권 API 잔고 조회 헬퍼 클래스
- 해외주식 잔고 조회
- 실시간 현재가 조회
- USD 현금 잔고 조회 (가능한 경우)
"""

import yaml
import requests
import json
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime

class KISBalanceChecker:
    """한국투자증권 잔고 조회 클래스"""

    def __init__(self, config_path: str = None):
        """
        초기화

        Args:
            config_path: kis_devlp.yaml 파일 경로 (None이면 현재 디렉토리)
        """
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), 'kis_devlp.yaml')

        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        # 토큰 로드
        self.access_token = self._load_token()

        # 계좌번호
        acct_parts = self.config['my_acct'].split('-')
        self.cano = acct_parts[0]
        self.acnt_prdt_cd = acct_parts[1] if len(acct_parts) > 1 else "01"

        # API URL
        self.base_url = "https://openapi.koreainvestment.com:9443"

        print(f"[KISBalanceChecker] 초기화 완료 - 계좌: {self.cano}-{self.acnt_prdt_cd}")

    def _load_token(self) -> str:
        """토큰 로드"""
        try:
            with open('kis_token.json', 'r') as f:
                token_data = json.load(f)
                return token_data['access_token']
        except Exception as e:
            print(f"[ERROR] 토큰 로드 실패: {e}")
            return ""

    def get_buying_power(self, symbol: str = "SOXL", price: float = 40.0, exchange_cd: str = "AMEX") -> Dict:
        """
        매수가능금액 조회 (USD 현금 잔고 확인용)

        [매우 중요] 한국투자 OpenAPI 챗봇 답변:
        USD 현금 잔고는 직접 조회 불가능하지만,
        매수가능금액 API로 간접 확인 가능!

        Args:
            symbol: 종목 코드
            price: 예상 가격
            exchange_cd: 거래소 코드 (AMEX가 가장 잘 작동)

        Returns:
            {
                'ord_psbl_cash': float,  # 주문가능현금
                'ord_psbl_frcr_amt': float,  # 주문가능외화금액 (USD)
                'max_ord_psbl_qty': int,  # 최대주문가능수량
                'success': bool
            }
        """
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-psamount"

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.config['my_app'],
            "appsecret": self.config['my_sec'],
            "tr_id": "JTTT3007R",  # 실전투자
            "custtype": "P",
            "User-Agent": self.config.get('my_agent', 'Mozilla/5.0')
        }

        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": exchange_cd,
            "OVRS_ORD_UNPR": str(price),
            "ITEM_CD": symbol
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code != 200:
                return {'success': False, 'error': f'HTTP {response.status_code}'}

            result = response.json()

            if result.get('rt_cd') != '0':
                return {'success': False, 'error': result.get('msg1', '')}

            output = result.get('output', {})

            # 주요 필드 파싱
            ord_psbl_cash = float(output.get('ord_psbl_cash', '0').replace(',', ''))
            ord_psbl_frcr_amt = float(output.get('ord_psbl_frcr_amt', '0').replace(',', ''))
            max_ord_psbl_qty = int(float(output.get('max_ord_psbl_qty', '0')))

            return {
                'success': True,
                'ord_psbl_cash': ord_psbl_cash,
                'ord_psbl_frcr_amt': ord_psbl_frcr_amt,  # 이게 실제 USD 잔고!
                'max_ord_psbl_qty': max_ord_psbl_qty,
                'raw_output': output
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_overseas_balance(self, exchange_cd: str = "NASD", currency: str = "USD") -> Dict:
        """
        해외주식 잔고 조회

        Args:
            exchange_cd: 거래소 코드 (NASD, NYSE, AMEX 등)
            currency: 통화 코드 (USD, HKD 등)

        Returns:
            {
                'holdings': [{'symbol': str, 'qty': float, 'avg_price': float, 'current_price': float, 'eval_amt': float, 'pnl': float, 'pnl_pct': float}],
                'total_invested': float,
                'total_value': float,
                'total_pnl': float,
                'total_pnl_pct': float,
                'usd_cash': float,  # 0 if not available
                'timestamp': str
            }
        """
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-balance"

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.config['my_app'],
            "appsecret": self.config['my_sec'],
            "tr_id": "JTTT3012R",  # 실전투자
            "custtype": "P",
            "User-Agent": self.config.get('my_agent', 'Mozilla/5.0')
        }

        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": exchange_cd,
            "TR_CRCY_CD": currency,
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": ""
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code != 200:
                print(f"[ERROR] HTTP {response.status_code}")
                return self._empty_balance()

            result = response.json()

            if result.get('rt_cd') != '0':
                print(f"[ERROR] 잔고 조회 실패: {result.get('msg1')}")
                return self._empty_balance()

            output1 = result.get('output1', [])
            output2 = result.get('output2', {})

            # 보유 종목 파싱
            holdings = []
            for item in output1:
                symbol = item.get('ovrs_pdno', '')
                qty = float(item.get('ovrs_cblc_qty', '0'))

                if qty > 0:
                    avg_price = float(item.get('pchs_avg_pric', '0'))
                    current_price = float(item.get('now_pric2', '0'))  # 야간시세
                    eval_amt = float(item.get('ovrs_stck_evlu_amt', '0'))

                    pnl = eval_amt - (qty * avg_price)
                    pnl_pct = (pnl / (qty * avg_price) * 100) if avg_price > 0 else 0

                    holdings.append({
                        'symbol': symbol,
                        'qty': qty,
                        'avg_price': avg_price,
                        'current_price': current_price,
                        'eval_amt': eval_amt,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'exchange_cd': item.get('ovrs_excg_cd', exchange_cd)
                    })

            # output2에서 전체 정보
            total_invested = float(output2.get('frcr_pchs_amt1', '0'))
            total_pnl = float(output2.get('ovrs_tot_pfls', '0'))
            total_value = float(output2.get('tot_evlu_pfls_amt', '0'))
            total_pnl_pct = float(output2.get('tot_pftrt', '0'))

            # USD 현금 (대부분 0으로 나옴)
            usd_cash = float(output2.get('frcr_buy_amt_smtl1', '0'))

            return {
                'holdings': holdings,
                'total_invested': total_invested,
                'total_value': total_value,
                'total_pnl': total_pnl,
                'total_pnl_pct': total_pnl_pct,
                'usd_cash': usd_cash,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            print(f"[ERROR] 잔고 조회 오류: {e}")
            return self._empty_balance()

    def get_realtime_price(self, symbol: str, exchange_cd: str = "NASD") -> Optional[float]:
        """
        실시간 현재가 조회

        Args:
            symbol: 종목 코드 (SOXL, NVDL 등)
            exchange_cd: 거래소 코드 (NASD, NYSE 등)

        Returns:
            현재가 (실패시 None)
        """
        # 거래소 코드 변환 (NASD -> NAS)
        excd_map = {
            'NASD': 'NAS',
            'NYSE': 'NYS',
            'AMEX': 'AMS',
            'SEHK': 'HKS',
            'SHAA': 'SHS',
            'SZAA': 'SZS',
            'TKSE': 'TSE',
            'HASE': 'HNX',
            'VNSE': 'HSX'
        }
        excd = excd_map.get(exchange_cd, 'NAS')

        url = f"{self.base_url}/uapi/overseas-price/v1/quotations/price"

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.config['my_app'],
            "appsecret": self.config['my_sec'],
            "tr_id": "HHDFS00000300",
            "custtype": "P",
            "User-Agent": self.config.get('my_agent', 'Mozilla/5.0')
        }

        params = {
            "AUTH": "",
            "EXCD": excd,
            "SYMB": symbol
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code != 200:
                return None

            result = response.json()

            if result.get('rt_cd') != '0':
                return None

            price = result.get('output', {}).get('last', '')
            return float(price) if price else None

        except Exception as e:
            print(f"[ERROR] {symbol} 가격 조회 오류: {e}")
            return None

    def get_holdings_with_realtime_price(self, exchange_cd: str = "NASD") -> List[Dict]:
        """
        보유 종목 + 실시간 현재가 조회

        Returns:
            [{'symbol': str, 'qty': float, 'avg_price': float, 'realtime_price': float, 'pnl': float, 'pnl_pct': float}]
        """
        balance = self.get_overseas_balance(exchange_cd)
        holdings_with_realtime = []

        for holding in balance['holdings']:
            symbol = holding['symbol']

            # 실시간 가격 조회
            realtime_price = self.get_realtime_price(symbol, holding.get('exchange_cd', exchange_cd))

            if realtime_price:
                qty = holding['qty']
                avg_price = holding['avg_price']
                pnl = (realtime_price - avg_price) * qty
                pnl_pct = ((realtime_price / avg_price) - 1) * 100 if avg_price > 0 else 0

                holdings_with_realtime.append({
                    'symbol': symbol,
                    'qty': qty,
                    'avg_price': avg_price,
                    'balance_price': holding['current_price'],  # 야간시세
                    'realtime_price': realtime_price,  # 실시간시세
                    'eval_amt': realtime_price * qty,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct
                })
            else:
                # 실시간 가격 조회 실패시 잔고의 가격 사용
                holdings_with_realtime.append(holding)

        return holdings_with_realtime

    def has_position(self, symbol: str, exchange_cd: str = "NASD") -> Tuple[bool, float]:
        """
        특정 종목 보유 여부 확인

        Args:
            symbol: 종목 코드
            exchange_cd: 거래소 코드

        Returns:
            (보유여부, 수량)
        """
        balance = self.get_overseas_balance(exchange_cd)

        for holding in balance['holdings']:
            if holding['symbol'] == symbol:
                return True, holding['qty']

        return False, 0.0

    def get_total_balance_summary(self) -> Dict:
        """
        전체 잔고 요약

        Returns:
            {
                'total_invested': float,
                'total_value': float,
                'total_pnl': float,
                'total_pnl_pct': float,
                'usd_cash': float,
                'num_holdings': int,
                'holdings': List[Dict]
            }
        """
        balance = self.get_overseas_balance()

        return {
            'total_invested': balance['total_invested'],
            'total_value': balance['total_value'],
            'total_pnl': balance['total_pnl'],
            'total_pnl_pct': balance['total_pnl_pct'],
            'usd_cash': balance['usd_cash'],
            'num_holdings': len(balance['holdings']),
            'holdings': balance['holdings']
        }

    def print_balance_summary(self):
        """잔고 요약 출력"""
        summary = self.get_total_balance_summary()

        print("\n" + "="*80)
        print("계좌 잔고 요약")
        print("="*80)
        print(f"총 투자금액: ${summary['total_invested']:.2f}")
        print(f"총 평가금액: ${summary['total_value']:.2f}")
        print(f"총 손익: ${summary['total_pnl']:.2f} ({summary['total_pnl_pct']:+.2f}%)")
        print(f"USD 현금: ${summary['usd_cash']:.2f}")
        print(f"\n보유 종목 ({summary['num_holdings']}개):")

        for holding in summary['holdings']:
            print(f"  {holding['symbol']}: {holding['qty']}주 @ ${holding['avg_price']:.2f} "
                  f"| 평가: ${holding['eval_amt']:.2f} | 손익: {holding['pnl_pct']:+.2f}%")

        print("="*80)

    def _empty_balance(self) -> Dict:
        """빈 잔고 반환"""
        return {
            'holdings': [],
            'total_invested': 0.0,
            'total_value': 0.0,
            'total_pnl': 0.0,
            'total_pnl_pct': 0.0,
            'usd_cash': 0.0,
            'timestamp': datetime.now().isoformat()
        }


def main():
    """테스트 실행"""
    checker = KISBalanceChecker()

    # 잔고 요약 출력
    checker.print_balance_summary()

    # [NEW] 매수가능금액 조회 (실제 USD 현금)
    print("\n" + "="*80)
    print("매수가능금액 조회 (실제 USD 현금)")
    print("="*80)
    buying_power = checker.get_buying_power(symbol="SOXL", price=40.0, exchange_cd="AMEX")

    if buying_power.get('success'):
        print(f"주문가능현금: ${buying_power['ord_psbl_cash']:.2f}")
        print(f"주문가능외화(USD): ${buying_power['ord_psbl_frcr_amt']:.2f} [중요]")
        print(f"최대주문가능수량: {buying_power['max_ord_psbl_qty']}주")
        print(f"\n>>> 실제 USD 현금: ${buying_power['ord_psbl_frcr_amt']:.2f}")
    else:
        print(f"조회 실패: {buying_power.get('error')}")

    # 실시간 가격 확인
    print("\n" + "="*80)
    print("실시간 가격 조회")
    print("="*80)
    symbols = ['SOXL', 'SOXS', 'NVDL', 'NVDQ']
    for symbol in symbols:
        price = checker.get_realtime_price(symbol)
        if price:
            print(f"  {symbol}: ${price:.2f}")

    # SOXL 보유 여부
    has_soxl, qty = checker.has_position('SOXL')
    print(f"\nSOXL 보유: {has_soxl}, 수량: {qty}")


if __name__ == "__main__":
    main()
