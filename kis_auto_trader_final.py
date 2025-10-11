#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
한국투자증권 완전 자동매매 시스템
- 추세돌파 전략 (코드3 LLM ETH Trader 로직 기반)
- 신호 변경 시 자동 포지션 전환
- 수익 0 수렴 시 조기 청산
- USD 현금 잔고 실시간 추적

[매우 중요] 한국투자 OpenAPI USD 현금 잔고 조회 방법:
===================================================================
Q: USD 현금 잔고는 API로 조회되지 않나요?

A: 직접 조회는 불가능하지만, 매수가능금액 API로 간접 확인 가능!

핵심 발견:
1. 해외주식 잔고 조회 API (/inquire-balance)
   → 보유 종목만 반환, USD 현금은 반환 안 함 

2. 매수가능금액 조회 API (/inquire-psamount) 
   → TR_ID: JTTT3007R (실전), TTTS3007R (모의)
   → 거래소 코드: AMEX (중요! NASD/NYSE는 실패)
   → 반환 필드: ord_psbl_frcr_amt = 실제 USD 현금

사용 예시:
    params = {
        "CANO": "계좌번호",
        "ACNT_PRDT_CD": "01",
        "OVRS_EXCG_CD": "AMEX",  # 필수: AMEX만 작동
        "OVRS_ORD_UNPR": "40.0",  # 종목 현재가
        "ITEM_CD": "SOXL"
    }

    result['output']['ord_psbl_frcr_amt']  # <- 이게 실제 USD 현금!
===================================================================
"""

import os
import yaml
import json
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

class KISAutoTrader:
    """한국투자증권 완전 자동매매 시스템"""

    def __init__(self, config_path: str = "kis_devlp.yaml", initial_usd: float = None):
        """
        초기화

        Args:
            config_path: 설정 파일 경로
            initial_usd: 초기 USD 입금액 (None이면 실제 잔고로 자동 설정)
        """
        print("="*80)
        print("한국투자증권 완전 자동매매 시스템 v1.0")
        print("="*80)

        # 설정 로드
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        # 토큰 로드
        with open('kis_token.json', 'r') as f:
            token_data = json.load(f)
            self.access_token = token_data['access_token']

        # 계좌번호
        acct_parts = self.config['my_acct'].split('-')
        self.cano = acct_parts[0]
        self.acnt_prdt_cd = acct_parts[1] if len(acct_parts) > 1 else "01"

        # API URL
        self.base_url = "https://openapi.koreainvestment.com:9443"

        # 거래 설정
        self.exchange_cd = "NASD"  # 잔고 조회용
        self.exchange_cd_buy = "AMEX"  # 매수가능금액 조회용 (중요!)
        self.currency = "USD"

        # 거래 대상 종목 (레버리지 ETF 쌍)
        self.target_symbols = ['SOXL', 'SOXS']  # SOXL: 상승, SOXS: 하락

        # 추세돌파 전략 파라미터
        self.trend_signal = None  # 'BULL' or 'BEAR'
        self.last_signal_change = None
        self.position_entry_time = None
        self.max_profit_pct = 0.0  # 최고 수익률 기록

        # 전략 설정 (코드3 ETH Trader 기반)
        self.max_position_time = 30 * 60  # 30분 최대 보유
        self.take_profit_target = 1.0  # 목표 수익 1.0%
        self.stop_loss_pct = -0.5  # 손절 -0.5%
        self.min_profit_to_hold = 0.3  # 최소 유지 수익 0.3%
        self.profit_decay_threshold = 0.1  # 수익 0.1% 이하 청산

        # 가격 히스토리 (추세 판단용)
        self.price_history = []
        self.max_history_len = 20

        # 거래 기록
        self.trade_history = []
        self.stats = {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'total_pnl': 0.0
        }

        # 초기 USD 설정
        if initial_usd is None:
            # 실제 잔고 조회
            buying_power = self.get_usd_cash_balance("SOXL", 40.0)
            if buying_power['success']:
                self.initial_usd = buying_power['ord_psbl_frcr_amt']
            else:
                self.initial_usd = 0.0
        else:
            self.initial_usd = initial_usd

        print(f"[초기화 완료]")
        print(f"  계좌: {self.cano}-{self.acnt_prdt_cd}")
        print(f"  초기 USD: ${self.initial_usd:.2f}")
        print(f"  거래 종목: {', '.join(self.target_symbols)}")
        print(f"  목표 수익: {self.take_profit_target}%")
        print(f"  손절: {self.stop_loss_pct}%")
        print("="*80)

    def get_usd_cash_balance(self, symbol: str = "SOXL", price: float = 40.0) -> Dict:
        """
        USD 현금 잔고 조회 (매수가능금액 API 사용)

        [매우 중요] 이 함수가 실제 USD 현금을 조회하는 유일한 방법!

        Args:
            symbol: 종목 코드 (아무거나 가능)
            price: 종목 현재가 (대략적인 값)

        Returns:
            {
                'success': bool,
                'ord_psbl_cash': float,  # 주문가능현금
                'ord_psbl_frcr_amt': float,  # 주문가능외화금액 (실제 USD!) 
                'max_ord_psbl_qty': int  # 최대주문가능수량
            }
        """
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-psamount"

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.config['my_app'],
            "appsecret": self.config['my_sec'],
            "tr_id": "JTTT3007R",  # 실전투자 (모의: TTTS3007R)
            "custtype": "P",
            "User-Agent": self.config.get('my_agent', 'Mozilla/5.0')
        }

        # [중요] AMEX 거래소 코드 사용 필수!
        # NASD, NYSE는 "상품이 존재하지 않습니다" 오류 발생
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": "AMEX",  # 필수: AMEX만 작동!
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
                'ord_psbl_frcr_amt': ord_psbl_frcr_amt,  # 이게 실제 USD 현금! 
                'max_ord_psbl_qty': max_ord_psbl_qty
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_positions(self) -> List[Dict]:
        """
        보유 포지션 조회

        Returns:
            [{'symbol': str, 'qty': float, 'avg_price': float, 'current_price': float, 'pnl_pct': float}]
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
            "OVRS_EXCG_CD": self.exchange_cd,
            "TR_CRCY_CD": self.currency,
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": ""
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code != 200:
                return []

            result = response.json()

            if result.get('rt_cd') != '0':
                return []

            output1 = result.get('output1', [])
            positions = []

            for item in output1:
                symbol = item.get('ovrs_pdno', '')
                qty = float(item.get('ovrs_cblc_qty', '0'))

                if qty > 0 and symbol in self.target_symbols:
                    avg_price = float(item.get('pchs_avg_pric', '0'))
                    current_price = float(item.get('now_pric2', '0'))
                    eval_amt = float(item.get('ovrs_stck_evlu_amt', '0'))

                    pnl = eval_amt - (qty * avg_price)
                    pnl_pct = (pnl / (qty * avg_price) * 100) if avg_price > 0 else 0

                    positions.append({
                        'symbol': symbol,
                        'qty': qty,
                        'avg_price': avg_price,
                        'current_price': current_price,
                        'eval_amt': eval_amt,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct
                    })

            return positions

        except Exception as e:
            print(f"[ERROR] 포지션 조회 오류: {e}")
            return []

    def get_hashkey(self, data: dict) -> str:
        """해시키 생성 (주문 시 필요)"""
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

    def buy_stock(self, symbol: str, quantity: int) -> Dict:
        """
        해외주식 매수 (시장가)

        Args:
            symbol: 종목 코드
            quantity: 수량

        Returns:
            {'success': bool, 'order_no': str, 'message': str}
        """
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/order"

        order_data = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": self.exchange_cd,
            "PDNO": symbol,
            "ORD_QTY": str(quantity),
            "OVRS_ORD_UNPR": "0",  # 시장가
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": "00"  # 00: 시장가
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
                return {'success': False, 'error': f'HTTP {response.status_code}'}

            result = response.json()

            if result.get('rt_cd') == '0':
                return {
                    'success': True,
                    'order_no': result.get('output', {}).get('odno', ''),
                    'message': result.get('msg1', ''),
                    'symbol': symbol,
                    'quantity': quantity
                }
            else:
                return {
                    'success': False,
                    'error': result.get('msg1', ''),
                    'msg_cd': result.get('msg_cd', '')
                }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def sell_stock(self, symbol: str, quantity: int) -> Dict:
        """
        해외주식 매도 (시장가)

        Args:
            symbol: 종목 코드
            quantity: 수량

        Returns:
            {'success': bool, 'order_no': str, 'message': str}
        """
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/order"

        order_data = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": self.exchange_cd,
            "PDNO": symbol,
            "ORD_QTY": str(quantity),
            "OVRS_ORD_UNPR": "0",  # 시장가
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": "00"  # 00: 시장가
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
                return {'success': False, 'error': f'HTTP {response.status_code}'}

            result = response.json()

            if result.get('rt_cd') == '0':
                return {
                    'success': True,
                    'order_no': result.get('output', {}).get('odno', ''),
                    'message': result.get('msg1', ''),
                    'symbol': symbol,
                    'quantity': quantity
                }
            else:
                return {
                    'success': False,
                    'error': result.get('msg1', ''),
                    'msg_cd': result.get('msg_cd', '')
                }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def detect_trend_signal(self) -> Optional[str]:
        """
        추세 신호 감지 (간단한 이동평균 기반)

        Returns:
            'BULL': 상승 추세 (SOXL)
            'BEAR': 하락 추세 (SOXS)
            None: 신호 없음
        """
        if len(self.price_history) < 10:
            return None

        # 단기/장기 이동평균
        recent = self.price_history[-10:]
        ma_short = sum(recent[-5:]) / 5
        ma_long = sum(recent) / 10
        current = recent[-1]

        # 골든크로스/데드크로스
        if ma_short > ma_long and current > ma_short:
            return 'BULL'
        elif ma_short < ma_long and current < ma_short:
            return 'BEAR'

        return None

    def should_exit_for_profit_decay(self, current_pnl_pct: float) -> bool:
        """
        수익 0 수렴으로 청산 필요 여부

        로직:
        1. 수익이 0.3% 이상 발생
        2. 수익이 0.1% 이하로 하락
        3. -> 수수료 고려해서 미리 청산

        Args:
            current_pnl_pct: 현재 손익률 (%)

        Returns:
            청산 필요 여부
        """
        # 최고 수익 갱신
        if current_pnl_pct > self.max_profit_pct:
            self.max_profit_pct = current_pnl_pct

        # 수익이 0.3% 이상 났다가 0.1% 이하로 떨어지면
        if self.max_profit_pct >= self.min_profit_to_hold:
            if current_pnl_pct <= self.profit_decay_threshold:
                return True

        return False

    def execute_strategy(self):
        """
        추세돌파 전략 실행 (메인 로직)

        코드3 ETH Trader 로직 기반:
        1. 잔고 및 포지션 확인
        2. 추세 신호 감지
        3. 청산 조건 체크 (신호 변경, 수익 0 수렴, 목표 달성, 손절)
        4. 신규 진입 또는 포지션 전환
        """
        print("\n" + "="*80)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 전략 실행")
        print("="*80)

        # 1. USD 현금 잔고 조회
        buying_power = self.get_usd_cash_balance("SOXL", 40.0)

        if not buying_power['success']:
            print(f"[ERROR] USD 현금 조회 실패: {buying_power.get('error')}")
            return

        usd_cash = buying_power['ord_psbl_frcr_amt']

        # 2. 보유 포지션 조회
        positions = self.get_positions()

        print(f"\n[계좌 현황]")
        print(f"  USD 현금: ${usd_cash:.2f}")

        current_position = None
        current_qty = 0
        current_avg_price = 0
        current_pnl_pct = 0

        if positions:
            pos = positions[0]  # 한 종목만 보유 가정
            current_position = pos['symbol']
            current_qty = pos['qty']
            current_avg_price = pos['avg_price']
            current_pnl_pct = pos['pnl_pct']
            current_price = pos['current_price']

            print(f"  보유: {current_position} {current_qty}주 @ ${current_avg_price:.2f}")
            print(f"  손익: {current_pnl_pct:+.2f}%")

            # 가격 히스토리 업데이트
            self.price_history.append(current_price)
            if len(self.price_history) > self.max_history_len:
                self.price_history.pop(0)
        else:
            print(f"  보유: 없음")

        # 3. 추세 신호 감지
        new_signal = self.detect_trend_signal()

        if new_signal:
            print(f"\n[추세 신호] {new_signal}")
            if new_signal != self.trend_signal:
                print(f"  신호 변경: {self.trend_signal} -> {new_signal}")
                self.last_signal_change = datetime.now()
            self.trend_signal = new_signal

        # 4. 청산 조건 체크
        should_exit = False
        exit_reason = ""

        if current_position:
            # 4-1. 신호 변경
            signal_to_symbol = {'BULL': 'SOXL', 'BEAR': 'SOXS'}
            target_symbol = signal_to_symbol.get(self.trend_signal)

            if target_symbol and target_symbol != current_position:
                should_exit = True
                exit_reason = f"신호 변경 ({self.trend_signal})"

            # 4-2. 수익 0 수렴
            elif self.should_exit_for_profit_decay(current_pnl_pct):
                should_exit = True
                exit_reason = f"수익 0 수렴 (최고 {self.max_profit_pct:.2f}% -> 현재 {current_pnl_pct:.2f}%)"

            # 4-3. 목표 수익
            elif current_pnl_pct >= self.take_profit_target:
                should_exit = True
                exit_reason = f"목표 수익 달성 ({current_pnl_pct:.2f}%)"

            # 4-4. 손절
            elif current_pnl_pct <= self.stop_loss_pct:
                should_exit = True
                exit_reason = f"손절 ({current_pnl_pct:.2f}%)"

            # 4-5. 시간 초과
            if self.position_entry_time:
                holding_time = (datetime.now() - self.position_entry_time).total_seconds()
                if holding_time > self.max_position_time:
                    should_exit = True
                    exit_reason = f"최대 보유 시간 초과 ({holding_time/60:.0f}분)"

        # 5. 청산 실행
        if should_exit:
            print(f"\n[청산 실행] {exit_reason}")
            print(f"  매도: {current_position} {int(current_qty)}주")

            result = self.sell_stock(current_position, int(current_qty))

            if result['success']:
                print(f"  [SUCCESS] 주문번호: {result['order_no']}")
                print(f"  메시지: {result['message']}")

                # 통계 업데이트
                self.stats['total_trades'] += 1
                if current_pnl_pct > 0:
                    self.stats['wins'] += 1
                else:
                    self.stats['losses'] += 1
                self.stats['total_pnl'] += current_pnl_pct

                # 기록 저장
                self.trade_history.append({
                    'type': 'SELL',
                    'symbol': current_position,
                    'quantity': int(current_qty),
                    'pnl_pct': current_pnl_pct,
                    'reason': exit_reason,
                    'timestamp': datetime.now().isoformat()
                })

                # 리셋
                self.max_profit_pct = 0.0
                self.position_entry_time = None
                current_position = None

                # 청산 후 잔고 재조회
                time.sleep(2)
                buying_power = self.get_usd_cash_balance("SOXL", 40.0)
                if buying_power['success']:
                    usd_cash = buying_power['ord_psbl_frcr_amt']

            else:
                print(f"  [FAIL] {result.get('error')}")

        # 6. 신규 진입
        if not current_position and self.trend_signal:
            signal_to_symbol = {'BULL': 'SOXL', 'BEAR': 'SOXS'}
            target_symbol = signal_to_symbol[self.trend_signal]

            if usd_cash > 0:
                # 매수 가능 수량 계산 (보수적으로 $40 기준)
                max_qty = int(usd_cash / 40.0)
                buy_qty = min(max(1, max_qty), 10)  # 최소 1주, 최대 10주

                print(f"\n[신규 진입] {target_symbol} {buy_qty}주 매수")

                result = self.buy_stock(target_symbol, buy_qty)

                if result['success']:
                    print(f"  [SUCCESS] 주문번호: {result['order_no']}")
                    print(f"  메시지: {result['message']}")

                    self.position_entry_time = datetime.now()
                    self.max_profit_pct = 0.0

                    # 기록 저장
                    self.trade_history.append({
                        'type': 'BUY',
                        'symbol': target_symbol,
                        'quantity': buy_qty,
                        'reason': f"추세 진입 ({self.trend_signal})",
                        'timestamp': datetime.now().isoformat()
                    })

                else:
                    print(f"  [FAIL] {result.get('error')}")

        # 7. 통계 출력
        if self.stats['total_trades'] > 0:
            win_rate = self.stats['wins'] / self.stats['total_trades'] * 100
            print(f"\n[통계] 거래: {self.stats['total_trades']}회 | "
                  f"승률: {win_rate:.1f}% | "
                  f"누적 손익: {self.stats['total_pnl']:+.2f}%")

        print("="*80)

    def run(self, interval_seconds: int = 60):
        """
        자동매매 무한 루프 실행

        Args:
            interval_seconds: 체크 간격 (초)
        """
        print(f"\n[자동매매 시작] 체크 간격: {interval_seconds}초")
        print(f"종료: Ctrl+C")

        while True:
            try:
                self.execute_strategy()
                print(f"\n다음 실행까지 {interval_seconds}초 대기...")
                time.sleep(interval_seconds)

            except KeyboardInterrupt:
                print("\n\n[종료] 사용자가 중단했습니다")
                self.print_final_summary()
                break

            except Exception as e:
                print(f"\n[ERROR] 오류 발생: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(interval_seconds)

    def print_final_summary(self):
        """최종 요약"""
        print("\n" + "="*80)
        print("최종 거래 요약")
        print("="*80)
        print(f"총 거래 횟수: {self.stats['total_trades']}")
        print(f"승: {self.stats['wins']} | 패: {self.stats['losses']}")

        if self.stats['total_trades'] > 0:
            win_rate = self.stats['wins'] / self.stats['total_trades'] * 100
            print(f"승률: {win_rate:.1f}%")
            print(f"누적 손익: {self.stats['total_pnl']:+.2f}%")

        print("="*80)


def main():
    """메인 실행"""
    # 자동매매 시작
    trader = KISAutoTrader()

    # 1회 실행 (테스트)
    trader.execute_strategy()

    # 자동매매 루프 (실거래용) - 주석 해제하여 사용
    # trader.run(interval_seconds=60)  # 60초마다 체크


if __name__ == "__main__":
    main()
