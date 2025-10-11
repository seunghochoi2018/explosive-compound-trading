#!/usr/bin/env python3
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SOXL/SOXS 추세돌파 자동매매 봇

전략:
- 상승 추세: SOXL 매수 (반도체 3배 레버리지 Bull)
- 하락 추세: SOXS 매수 (반도체 3배 레버리지 Bear)
- 추세 전환 시 포지션 스위칭

리스크 관리:
- 손절: -3%
- 익절: +5%
- 1회 최대 투자금: 계좌 잔고의 20%
"""

import json
import requests
import time
from datetime import datetime
import sys

# KIS API 설정
APP_KEY = "PSi3RlRt3DWtPPKTdYNALowIoeUBgM5mMLYO"
APP_SECRET = "Q7LxW5oIlCeg+doJCkmPDgXw7uy8bjC7ACRQR1GrAzgCF3zH7LziMix/QJgweS+IRU+uM/3GPELXVeOGocKQnHZ+RPeH4bqR1Ciwt3+1yp7yctt+bBc85eDrIsrX9KfOkrLY+wVuE1tthKYsDyiF2YKrOp/e1PsSD0mdI="
BASE_URL = "https://openapi.koreainvestment.com:9443"
ACCOUNT_NO = "43113014"
ACCOUNT_CODE = "01"

# 거래 설정
SYMBOLS = ["TQQQ", "SQQQ"]  #  TQQQ/SQQQ로 변경
STOP_LOSS = -0.03  # -3% 손절
TAKE_PROFIT = 0.05  # +5% 익절
POSITION_SIZE = 0.20  # 계좌 잔고의 20%
CHECK_INTERVAL = 10  # 10초마다 체크

#  PDNO 매핑 (KIS API 실전 종목코드)
PDNO_MAP = {
    "TQQQ": "A206892",
    "SQQQ": "A206893"
}

class SOXLSOXSTradingBot:
    def __init__(self):
        self.token = None
        self.positions = {}  # {symbol: {'qty': 수량, 'avg_price': 평균단가}}
        self.last_trend = None  # 'bull' or 'bear'
        self.initial_balance = 0  # 초기 잔고
        self.total_profit = 0  # 누적 수익금
        self.trade_count = 0  # 거래 횟수

    def load_token(self):
        """토큰 로드"""
        try:
            with open("kis_token.json", 'r') as f:
                token_data = json.load(f)
                self.token = token_data.get('access_token')
                print(f"[{self.timestamp()}] 토큰 로드 성공")
                return True
        except Exception as e:
            print(f"[{self.timestamp()}] 토큰 로드 실패: {e}")
            print("[INFO] python refresh_kis_token.py 실행 후 다시 시도하세요.")
            return False

    def timestamp(self):
        """현재 시간 반환"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def get_current_price(self, symbol):
        """현재가 조회"""
        url = f"{BASE_URL}/uapi/overseas-price/v1/quotations/price"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.token}",
            "appkey": APP_KEY,
            "appsecret": APP_SECRET,
            "tr_id": "HHDFS00000300",
            "custtype": "P"
        }
        params = {
            "AUTH": "",
            "EXCD": "NAS",
            "SYMB": symbol
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get("rt_cd") == "0":
                    output = result.get("output", {})
                    price_str = output.get('last', '0')

                    # 빈 문자열이나 공백 처리
                    if not price_str or price_str.strip() == '':
                        # 장 마감 시 종가 시도
                        price_str = output.get('base', '0')

                    try:
                        price = float(price_str)
                        if price > 0:
                            return price
                    except:
                        pass
        except Exception as e:
            print(f"[{self.timestamp()}] {symbol} 가격 조회 실패: {e}")
        return None

    def get_balance(self):
        """USD 잔고 조회"""
        url = f"{BASE_URL}/uapi/overseas-stock/v1/trading/inquire-balance"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.token}",
            "appkey": APP_KEY,
            "appsecret": APP_SECRET,
            "tr_id": "TTTS3012R",
            "custtype": "P"
        }
        params = {
            "CANO": ACCOUNT_NO,
            "ACNT_PRDT_CD": ACCOUNT_CODE,
            "OVRS_EXCG_CD": "NASD",
            "TR_CRCY_CD": "USD",
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": ""
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get("rt_cd") == "0":
                    output = result.get("output2", [{}])[0]
                    balance = float(output.get('frcr_dncl_amt_2', 0))  # 외화예수금
                    return balance
        except Exception as e:
            print(f"[{self.timestamp()}] 잔고 조회 실패: {e}")
        return 0

    def get_positions(self):
        """보유 포지션 조회"""
        url = f"{BASE_URL}/uapi/overseas-stock/v1/trading/inquire-balance"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.token}",
            "appkey": APP_KEY,
            "appsecret": APP_SECRET,
            "tr_id": "TTTS3012R",
            "custtype": "P"
        }
        params = {
            "CANO": ACCOUNT_NO,
            "ACNT_PRDT_CD": ACCOUNT_CODE,
            "OVRS_EXCG_CD": "NASD",
            "TR_CRCY_CD": "USD",
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": ""
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get("rt_cd") == "0":
                    output1 = result.get("output1", [])
                    positions = {}

                    for item in output1:
                        symbol = item.get('ovrs_pdno', '')
                        qty = int(item.get('ovrs_cblc_qty', 0))
                        avg_price = float(item.get('pchs_avg_pric', 0))

                        if symbol in SYMBOLS and qty > 0:
                            positions[symbol] = {
                                'qty': qty,
                                'avg_price': avg_price
                            }

                    self.positions = positions
                    return positions
        except Exception as e:
            print(f"[{self.timestamp()}] 포지션 조회 실패: {e}")
        return {}

    def buy_order(self, symbol, qty):
        """매수 주문"""
        url = f"{BASE_URL}/uapi/overseas-stock/v1/trading/order"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.token}",
            "appkey": APP_KEY,
            "appsecret": APP_SECRET,
            "tr_id": "TTTT1002U",  # 해외주식 매수 주문
            "custtype": "P"
        }

        # 현재가 조회
        current_price = self.get_current_price(symbol)
        if not current_price:
            print(f"[{self.timestamp()}] {symbol} 가격 조회 실패 - 주문 취소")
            return False

        data = {
            "CANO": ACCOUNT_NO,
            "ACNT_PRDT_CD": ACCOUNT_CODE,
            "OVRS_EXCG_CD": "NASD",
            "PDNO": symbol,
            "ORD_QTY": str(qty),
            "OVRS_ORD_UNPR": "0",  # 시장가
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": "00"  # 지정가(00), 시장가(00)
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get("rt_cd") == "0":
                    print(f"[{self.timestamp()}]  {symbol} 매수 성공: {qty}주 @ ${current_price:.2f}")
                    return True
                else:
                    error_msg = result.get('msg1', 'Unknown error')
                    print(f"[{self.timestamp()}]  {symbol} 매수 실패: {error_msg}")
            else:
                print(f"[{self.timestamp()}]  {symbol} 매수 HTTP 오류: {response.status_code}")
        except Exception as e:
            print(f"[{self.timestamp()}]  {symbol} 매수 예외: {e}")
        return False

    def sell_order(self, symbol, qty):
        """매도 주문"""
        url = f"{BASE_URL}/uapi/overseas-stock/v1/trading/order"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.token}",
            "appkey": APP_KEY,
            "appsecret": APP_SECRET,
            "tr_id": "TTTT1006U",  # 해외주식 매도 주문
            "custtype": "P"
        }

        # 현재가 조회
        current_price = self.get_current_price(symbol)
        if not current_price:
            print(f"[{self.timestamp()}] {symbol} 가격 조회 실패 - 주문 취소")
            return False

        # 수익금 계산 (매도 전 평균단가 확인)
        if symbol in self.positions:
            avg_price = self.positions[symbol]['avg_price']
            profit = (current_price - avg_price) * qty
            self.total_profit += profit
            self.trade_count += 1

        data = {
            "CANO": ACCOUNT_NO,
            "ACNT_PRDT_CD": ACCOUNT_CODE,
            "OVRS_EXCG_CD": "NASD",
            "PDNO": symbol,
            "ORD_QTY": str(qty),
            "OVRS_ORD_UNPR": "0",  # 시장가
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": "00"
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get("rt_cd") == "0":
                    print(f"[{self.timestamp()}]  {symbol} 매도 성공: {qty}주 @ ${current_price:.2f}")
                    return True
                else:
                    error_msg = result.get('msg1', 'Unknown error')
                    print(f"[{self.timestamp()}]  {symbol} 매도 실패: {error_msg}")
            else:
                print(f"[{self.timestamp()}]  {symbol} 매도 HTTP 오류: {response.status_code}")
        except Exception as e:
            print(f"[{self.timestamp()}]  {symbol} 매도 예외: {e}")
        return False

    def detect_trend(self):
        """추세 감지 (SOXL vs SOXS 상대 강도 비교)"""
        soxl_price = self.get_current_price("SOXL")
        soxs_price = self.get_current_price("SOXS")

        if not soxl_price or not soxs_price:
            print(f"[{self.timestamp()}] 가격 조회 실패 - SOXL: {soxl_price}, SOXS: {soxs_price}")
            return None

        # SOXL과 SOXS의 상대적 강도 비교
        # SOXL이 SOXS보다 비싸면 상승장 (Bull)
        # SOXS가 SOXL보다 비싸면 하락장 (Bear)

        print(f"[{self.timestamp()}] 가격 - SOXL: ${soxl_price:.2f}, SOXS: ${soxs_price:.2f}")

        # 비율 계산 (정상적인 경우 SOXL > SOXS)
        ratio = soxl_price / soxs_price

        if ratio > 5:  # SOXL이 SOXS보다 5배 이상 비싸면 강한 상승장
            return 'bull'
        elif ratio < 3:  # 비율이 낮으면 하락장 신호
            return 'bear'
        else:  # 중립
            # 기존 추세 유지
            return self.last_trend if self.last_trend else 'bull'

    def display_profit_status(self):
        """수익 현황 표시"""
        current_balance = self.get_balance()
        positions = self.get_positions()

        # 보유 포지션 평가금액 계산
        position_value = 0
        unrealized_profit = 0

        for symbol, pos in positions.items():
            current_price = self.get_current_price(symbol)
            if current_price:
                qty = pos['qty']
                avg_price = pos['avg_price']
                value = current_price * qty
                position_value += value
                unrealized_profit += (current_price - avg_price) * qty

        # 총 자산 = 잔고 + 보유 포지션 평가금액
        total_assets = current_balance + position_value

        # 수익률 계산
        if self.initial_balance > 0:
            profit_rate = ((total_assets - self.initial_balance) / self.initial_balance) * 100
        else:
            profit_rate = 0

        # 실현 수익 + 미실현 수익
        total_profit_with_unrealized = self.total_profit + unrealized_profit

        print(f"\n{'='*70}")
        print(f" 수익 현황")
        print(f"{'='*70}")
        print(f"초기 잔고:     ${self.initial_balance:.2f}")
        print(f"현재 잔고:     ${current_balance:.2f}")
        print(f"포지션 평가액: ${position_value:.2f}")
        print(f"총 자산:       ${total_assets:.2f}")
        print(f"─"*70)
        print(f"실현 수익:     ${self.total_profit:.2f}")
        print(f"미실현 수익:   ${unrealized_profit:.2f}")
        print(f"총 수익:       ${total_profit_with_unrealized:.2f}")
        print(f"수익률:        {profit_rate:+.2f}%")
        print(f"거래 횟수:     {self.trade_count}회")
        print(f"{'='*70}\n")

    def check_stop_loss_take_profit(self):
        """손절/익절 체크"""
        positions = self.get_positions()

        for symbol, pos in positions.items():
            current_price = self.get_current_price(symbol)
            if not current_price:
                continue

            avg_price = pos['avg_price']
            qty = pos['qty']
            profit_rate = (current_price - avg_price) / avg_price

            # 손절 체크
            if profit_rate <= STOP_LOSS:
                print(f"[{self.timestamp()}]  {symbol} 손절 발동: {profit_rate*100:.2f}%")
                self.sell_order(symbol, qty)

            # 익절 체크
            elif profit_rate >= TAKE_PROFIT:
                print(f"[{self.timestamp()}]  {symbol} 익절 발동: {profit_rate*100:.2f}%")
                self.sell_order(symbol, qty)

    def execute_strategy(self):
        """추세돌파 전략 실행"""
        trend = self.detect_trend()

        if not trend:
            print(f"[{self.timestamp()}]  추세 감지 실패")
            return

        print(f"[{self.timestamp()}]  현재 추세: {trend.upper()}")

        # 추세 전환 감지
        if self.last_trend and self.last_trend != trend:
            print(f"[{self.timestamp()}]  추세 전환 감지: {self.last_trend.upper()} → {trend.upper()}")

            # 기존 포지션 청산
            positions = self.get_positions()
            for symbol, pos in positions.items():
                print(f"[{self.timestamp()}] 포지션 청산: {symbol} {pos['qty']}주")
                self.sell_order(symbol, pos['qty'])
                time.sleep(1)

        # 새로운 포지션 진입
        self.last_trend = trend

        if trend == 'bull':
            target_symbol = "SOXL"
        else:
            target_symbol = "SOXS"

        # 이미 해당 종목을 보유 중인지 체크
        positions = self.get_positions()
        if target_symbol in positions:
            print(f"[{self.timestamp()}] ℹ️ {target_symbol} 이미 보유 중")
            return

        # 매수 실행
        balance = self.get_balance()
        current_price = self.get_current_price(target_symbol)

        if balance > 0 and current_price:
            invest_amount = balance * POSITION_SIZE
            qty = int(invest_amount / current_price)

            if qty > 0:
                print(f"[{self.timestamp()}]  {target_symbol} 매수 준비: {qty}주 (${invest_amount:.2f})")
                self.buy_order(target_symbol, qty)

    def run(self):
        """봇 실행"""
        print("="*70)
        print("=== SOXL/SOXS 추세돌파 자동매매 봇 시작 ===")
        print("="*70)
        print(f"[설정] 손절: {STOP_LOSS*100}%, 익절: {TAKE_PROFIT*100}%")
        print(f"[설정] 포지션 크기: 잔고의 {POSITION_SIZE*100}%")
        print(f"[설정] 체크 간격: {CHECK_INTERVAL}초")
        print("="*70)

        # 토큰 로드
        if not self.load_token():
            return

        # 초기 상태 확인
        balance = self.get_balance()
        positions = self.get_positions()

        # 초기 잔고 저장 (포지션 포함)
        position_value = 0
        for symbol, pos in positions.items():
            current_price = self.get_current_price(symbol)
            if current_price:
                position_value += current_price * pos['qty']

        self.initial_balance = balance + position_value

        print(f"\n[{self.timestamp()}]  USD 잔고: ${balance:.2f}")
        print(f"[{self.timestamp()}] 📦 보유 포지션: {len(positions)}개")
        for symbol, pos in positions.items():
            print(f"  - {symbol}: {pos['qty']}주 @ ${pos['avg_price']:.2f}")

        print(f"\n[{self.timestamp()}]  자동매매 시작...\n")

        # 수익 현황 표시 카운터
        status_counter = 0

        try:
            while True:
                # 손절/익절 체크
                self.check_stop_loss_take_profit()

                # 추세돌파 전략 실행
                self.execute_strategy()

                # 30초마다 수익 현황 표시
                status_counter += 1
                if status_counter >= 3:  # 10초 * 3 = 30초
                    self.display_profit_status()
                    status_counter = 0

                # 대기
                time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print(f"\n[{self.timestamp()}] ⛔ 사용자 중단")

            # 최종 수익 현황 표시
            self.display_profit_status()

            print("="*70)
            print("봇 종료")
            print("="*70)

if __name__ == "__main__":
    bot = SOXLSOXSTradingBot()
    bot.run()
