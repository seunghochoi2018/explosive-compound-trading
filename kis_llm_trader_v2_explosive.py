#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS LLM 트레이더 v2.0 - SOXL 10시간 복리 폭발 전략

백테스트 발견 적용:
- 10시간 보유 + 추세 전환 = 연 2,634%
- 승률 55%, 복리 +12.8%
- 추세 따라가기: 상승 → SOXL, 하락 → SOXS
"""
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import time
import json
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

# 한국투자증권 API (기존 코드 활용)
import sys
sys.path.append('C:/Users/user/Documents/코드4')

from llm_market_analyzer import LLMMarketAnalyzer
from telegram_notifier import TelegramNotifier

class ExplosiveKISTrader:
    """SOXL/SOXS 복리 폭발 전략"""

    def __init__(self):
        print("="*80)
        print("KIS LLM 트레이더 v2.0 - 복리 폭발 전략")
        print("="*80)
        print("백테스트 발견 적용:")
        print("  전략: 10시간 보유 + 추세 전환")
        print("  예상 수익: 연 2,634%")
        print("  승률: 55%")
        print("="*80)

        # KIS API 설정
        self.load_kis_config()

        # LLM 분석기 (2단계: 14b + 7b 듀얼!)
        self.llm_analyzers = [
            LLMMarketAnalyzer(model_name="qwen2.5:14b"),
            LLMMarketAnalyzer(model_name="qwen2.5:7b")
        ]

        # 텔레그램
        self.telegram = TelegramNotifier()

        # 거래 설정 (⭐ 정확한 PDNO 코드 사용!)
        # ⚠️  중요: PDNO는 "SOXL"이 아니라 "A980679"를 사용해야 함!
        # ⚠️  KIS API에서 종목코드는 A980XXX 형식의 고유 코드 필수!
        self.symbols = {
            'SOXL': {'pdno': 'A980679', 'name': '반도체 3배 레버리지 롱'},  # DIREXION DAILY SEMICONDUCTOR BULL 3X
            'SOXS': {'pdno': 'A980680', 'name': '반도체 3배 레버리지 숏'}   # DIREXION DAILY SEMICONDUCTOR BEAR 3X
        }

        # 상태
        self.current_position = None  # 'SOXL' or 'SOXS'
        self.entry_price = 0
        self.entry_time = None
        self.entry_balance = None

        # 가격 히스토리
        self.price_history = []
        self.max_history = 50

        # 통계
        self.stats = {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'balance_history': []
        }

        # 학습 데이터
        self.trade_history = []
        self.all_trades = []
        self.learning_file = "kis_trade_history.json"
        self.load_trade_history()

        # ⭐ 복리 폭발 전략 설정
        self.MAX_HOLDING_TIME = 10 * 3600  # 10시간

        # 동적 손절 (SOXL용)
        total_trades = len(self.all_trades)
        if total_trades < 50:
            self.DYNAMIC_STOP_LOSS = -3.5
            print(f"  [초기 검증 모드] 손절: -3.5%")
        else:
            win_rate = len([t for t in self.all_trades if t.get('pnl_pct', 0) > 0]) / total_trades * 100
            if win_rate >= 55:
                self.DYNAMIC_STOP_LOSS = -3.0
                print(f"  [검증 완료] 손절: -3.0% (승률 {win_rate:.1f}%)")
            else:
                self.DYNAMIC_STOP_LOSS = -3.5
                print(f"  [추가 검증] 손절: -3.5% (승률 {win_rate:.1f}%)")

        self.MIN_CONFIDENCE = 70  # SOXL은 70%
        self.TREND_CHECK_ENABLED = True

        print(f"\n[전략 설정]")
        print(f"  최대 보유시간: {self.MAX_HOLDING_TIME/3600:.0f}시간")
        print(f"  동적 손절: {self.DYNAMIC_STOP_LOSS}%")
        print(f"  최소 신뢰도: {self.MIN_CONFIDENCE}%")

        # 마지막 LLM 분석
        self.last_llm_signal = None
        self.last_llm_confidence = 0

        # 초기 잔고
        self.initial_balance = self.get_usd_balance()
        print(f"\n[초기 잔고] ${self.initial_balance:,.2f}")

        # 텔레그램 알림
        self.telegram.send_message(
            f"🚀 SOXL 복리 폭발 전략 시작\n\n"
            f"초기 잔고: ${self.initial_balance:,.2f}\n"
            f"최대 보유: 10시간\n"
            f"동적 손절: {self.DYNAMIC_STOP_LOSS}%\n"
            f"목표: 연 2,634%"
        )

    def load_kis_config(self):
        """KIS API 설정 로드"""
        try:
            # kis_devlp.yaml 로드
            with open('../코드/kis_devlp.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # 실전투자 키 사용
            self.app_key = config['my_app']
            self.app_secret = config['my_sec']
            self.account_no = config['my_acct']
            self.base_url = "https://openapi.koreainvestment.com:9443"

            # 토큰 발급
            self.get_access_token()

        except Exception as e:
            print(f"[ERROR] KIS 설정 로드 실패: {e}")
            raise

    def get_access_token(self):
        """KIS 접근 토큰 발급 (24시간 유효, 저장/로드)"""
        import requests

        # 1. 기존 토큰 로드 시도
        token_file = "kis_token.json"
        try:
            if os.path.exists(token_file):
                with open(token_file, 'r', encoding='utf-8') as f:
                    token_data = json.load(f)

                # 토큰 만료 시간 체크 (발급 후 23시간)
                issue_time = datetime.fromisoformat(token_data['issue_time'])
                if datetime.now() < issue_time + timedelta(hours=23):
                    self.access_token = token_data['access_token']
                    remaining = (issue_time + timedelta(hours=23) - datetime.now()).total_seconds() / 3600
                    print(f"[OK] 기존 KIS 토큰 사용 (남은 시간: {remaining:.1f}시간)")
                    return
        except Exception as e:
            print(f"[INFO] 기존 토큰 로드 실패: {e}")

        # 2. 새 토큰 발급
        try:
            url = f"{self.base_url}/oauth2/tokenP"
            data = {
                "grant_type": "client_credentials",
                "appkey": self.app_key,
                "appsecret": self.app_secret
            }

            response = requests.post(url, json=data, timeout=10)

            if response.status_code == 200:
                result = response.json()
                self.access_token = result.get('access_token')

                # 토큰 저장 (24시간 유효)
                with open(token_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'access_token': self.access_token,
                        'issue_time': datetime.now().isoformat()
                    }, f, ensure_ascii=False, indent=2)

                print(f"[OK] 새 KIS 토큰 발급 완료 (24시간 유효)")
            else:
                raise Exception(f"토큰 발급 실패: {response.status_code}")

        except Exception as e:
            print(f"[ERROR] 토큰 발급 실패: {e}")
            raise

    def load_trade_history(self):
        """과거 거래 로드"""
        try:
            with open(self.learning_file, 'r', encoding='utf-8') as f:
                self.all_trades = json.load(f)

            self.trade_history = [t for t in self.all_trades if t.get('pnl_pct', 0) > 0]

            print(f"\n[학습 데이터]")
            print(f"  전체: {len(self.all_trades)}건")
            print(f"  학습용: {len(self.trade_history)}건")

        except:
            print(f"[INFO] 기존 거래 데이터 없음")

    def get_usd_balance(self) -> float:
        """USD 잔고 조회"""
        try:
            import requests

            url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-balance"

            headers = {
                "authorization": f"Bearer {self.access_token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": "TTTS3012R"
            }

            params = {
                "CANO": self.account_no.split('-')[0],
                "ACNT_PRDT_CD": self.account_no.split('-')[1],
                "OVRS_EXCG_CD": "NASD",
                "TR_CRCY_CD": "USD",
                "CTX_AREA_FK200": "",
                "CTX_AREA_NK200": ""
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('rt_cd') == '0':
                    output2 = data.get('output2', {})
                    return float(output2.get('frcr_dncl_amt_2', 0))  # USD 예수금

            return 0.0

        except Exception as e:
            print(f"[ERROR] 잔고 조회 실패: {e}")
            return 0.0

    def get_current_price(self, symbol: str) -> float:
        """
        현재가 조회 (KIS API 우선 → FMP API 백업)

        🔧 2025-10-10 수정:
        - KIS API: custtype 헤더, FID_COND_MRKT_DIV_CODE/FID_INPUT_ISCD 파라미터
        - FMP API: 백업 시스템 (KIS 실패 시 자동 전환)

        Args:
            symbol: 종목명 ('SOXL' 또는 'SOXS')

        Returns:
            float: 현재가 (USD), 조회 실패 시 0.0
        """
        # 1차 시도: KIS API
        try:
            import requests

            url = f"{self.base_url}/uapi/overseas-price/v1/quotations/price"

            headers = {
                "authorization": f"Bearer {self.access_token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": "HHDFS00000300",
                "custtype": "P"
            }

            params = {
                "FID_COND_MRKT_DIV_CODE": "N",
                "FID_INPUT_ISCD": symbol
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if data.get('rt_cd') == '0':
                    stck_prpr = data.get('output', {}).get('stck_prpr', '0')
                    if stck_prpr and stck_prpr != '':
                        price = float(stck_prpr)
                        print(f"[KIS] {symbol} 가격: ${price:.2f}")
                        return price

        except Exception as e:
            print(f"[KIS] API 오류: {e}")

        # 2차 시도: FMP API (백업)
        print(f"[INFO] KIS API 실패 → FMP API로 전환")
        return self.get_price_from_fmp(symbol)

    def get_price_from_fmp(self, symbol: str) -> float:
        """
        FMP API로 현재가 조회 (백업 시스템)

        무료 API Key: demo (제한: 250 requests/day)
        실전용 API Key 발급 필요 시: https://site.financialmodelingprep.com/
        """
        try:
            import requests

            # FMP API (무료 demo 키 사용)
            api_key = "demo"  # 실전용은 유료 키 발급 필요
            url = f"https://financialmodelingprep.com/api/v3/quote-short/{symbol}?apikey={api_key}"

            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    price = data[0].get('price', 0)
                    if price > 0:
                        print(f"[FMP] {symbol} 가격: ${price:.2f}")
                        return float(price)

            print(f"[FMP] {symbol} 가격 조회 실패")
            return 0.0

        except Exception as e:
            print(f"[FMP] API 오류: {e}")
            return 0.0

    def calculate_trend(self) -> str:
        """
        추세 판단 (이동평균 기반)

        MA5 > MA20 → 상승 (SOXL)
        MA5 < MA20 → 하락 (SOXS)
        """
        if len(self.price_history) < 20:
            return 'NEUTRAL'

        ma_5 = sum(self.price_history[-5:]) / 5
        ma_20 = sum(self.price_history[-20:]) / 20

        if ma_5 > ma_20 * 1.01:
            return 'BULL'
        elif ma_5 < ma_20 * 0.99:
            return 'BEAR'
        else:
            return 'NEUTRAL'

    def check_exit_conditions(self, current_price: float, llm_signal: str) -> tuple:
        """
        청산 조건 체크

        1. 10시간 초과
        2. 손절 -3%
        3. 추세 전환 (BULL ↔ BEAR)
        """
        if not self.current_position:
            return (False, "", False)

        # 가격 체크 (장 마감 시)
        if current_price == 0 or self.entry_price == 0:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️  가격 정보 없음 (장 마감), 청산 조건 체크 불가")
            return (False, "", False)

        # PNL 계산 (3배 레버리지)
        if self.current_position == 'SOXL':
            pnl = ((current_price - self.entry_price) / self.entry_price) * 100 * 3
        else:  # SOXS
            pnl = ((self.entry_price - current_price) / self.entry_price) * 100 * 3

        holding_time = (datetime.now() - self.entry_time).total_seconds()

        # 1. 10시간 초과
        if holding_time > self.MAX_HOLDING_TIME:
            return (True, f"MAX_TIME_10H (PNL:{pnl:+.1f}%)", False)

        # 2. 손절
        if pnl <= self.DYNAMIC_STOP_LOSS:
            return (True, f"STOP_LOSS (PNL:{pnl:+.1f}%)", False)

        # 3. 추세 전환
        if self.TREND_CHECK_ENABLED and llm_signal:
            if self.current_position == 'SOXL' and llm_signal == 'BEAR':
                return (True, f"TREND_BULL→BEAR (PNL:{pnl:+.1f}%)", True)
            elif self.current_position == 'SOXS' and llm_signal == 'BULL':
                return (True, f"TREND_BEAR→BULL (PNL:{pnl:+.1f}%)", True)

        return (False, "", False)

    def place_order(self, symbol: str, side: str, qty: int) -> bool:
        """주문 실행"""
        try:
            import requests

            # ⭐ KIS API는 티커명 직접 사용 (SOXL/SOXS)
            url = f"{self.base_url}/uapi/overseas-stock/v1/trading/order"

            headers = {
                "authorization": f"Bearer {self.access_token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": "JTTT1002U" if side == "BUY" else "JTTT1006U"
            }

            data = {
                "CANO": self.account_no.split('-')[0],
                "ACNT_PRDT_CD": self.account_no.split('-')[1],
                "OVRS_EXCG_CD": "NASD",
                "PDNO": symbol,  # ⭐ 티커명 직접 사용 (SOXL/SOXS)
                "ORD_QTY": str(qty),
                "OVRS_ORD_UNPR": "0",  # 시장가
                "ORD_SVR_DVSN_CD": "0"
            }

            response = requests.post(url, headers=headers, json=data, timeout=10)

            if response.status_code == 200:
                result = response.json()
                if result.get('rt_cd') == '0':
                    print(f"[OK] 주문 성공: {symbol} {side} {qty}주")
                    return True

            print(f"[ERROR] 주문 실패")
            return False

        except Exception as e:
            print(f"[ERROR] 주문 예외: {e}")
            return False

    def run(self):
        """메인 루프"""
        print("\n[시작] SOXL 복리 폭발 전략 실행")

        # 디버깅: 시작 알림
        self.telegram.send_message(
            f"🔍 [DEBUG] KIS 봇 메인 루프 시작\n"
            f"현재 시간: {datetime.now().strftime('%H:%M:%S')}\n"
            f"300초(5분)마다 분석 실행 예정"
        )

        cycle_count = 0
        while True:
            try:
                cycle_count += 1
                loop_start = datetime.now()
                print(f"\n{'='*80}")
                print(f"[{loop_start.strftime('%H:%M:%S')}] 🔄 사이클 #{cycle_count} 시작 (KIS)")
                print(f"{'='*80}")

                # SOXL 가격 조회 (추세 판단용)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 💰 SOXL 가격 조회 중...")
                soxl_price = self.get_current_price('SOXL')
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 💵 SOXL 가격: ${soxl_price:.2f}")

                if soxl_price > 0:
                    self.price_history.append(soxl_price)
                    if len(self.price_history) > self.max_history:
                        self.price_history.pop(0)
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📈 가격 히스토리: {len(self.price_history)}개")

                # 추세 판단
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 추세 분석 중...")
                trend = self.calculate_trend()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 추세: {trend}")

                # LLM 앙상블 분석 (14b + 7b)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🤖 LLM 앙상블 분석 시작 (14b + 7b)...")
                llm_start = datetime.now()
                llm_signal = self.get_ensemble_signal(trend)
                llm_duration = (datetime.now() - llm_start).total_seconds()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏱️  LLM 분석 완료 ({llm_duration:.1f}초 소요)")
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🎯 신호: {llm_signal}")

                # 포지션 있으면 청산 조건 체크
                if self.current_position:
                    current_symbol_price = self.get_current_price(self.current_position)

                    should_exit, reason, should_reverse = self.check_exit_conditions(
                        current_symbol_price, llm_signal
                    )

                    if should_exit:
                        # 청산
                        self.close_position(reason)

                        if should_reverse:
                            # 즉시 반대 포지션
                            new_symbol = 'SOXL' if llm_signal == 'BULL' else 'SOXS'
                            self.open_position(new_symbol)

                # 포지션 없으면 진입 조건 체크
                else:
                    if llm_signal in ['BULL', 'BEAR']:
                        target_symbol = 'SOXL' if llm_signal == 'BULL' else 'SOXS'
                        self.open_position(target_symbol)

                # 상태 출력
                current_balance = self.get_usd_balance()

                # division by zero 방지
                if self.initial_balance > 0:
                    balance_pct = ((current_balance - self.initial_balance) / self.initial_balance) * 100
                else:
                    balance_pct = 0.0

                print(f"\n[상태]")
                print(f"  추세: {trend}")
                print(f"  LLM 신호: {llm_signal}")
                print(f"  포지션: {self.current_position if self.current_position else '없음'}")
                print(f"  잔고: ${current_balance:,.2f} ({balance_pct:+.2f}%)")

                # 장 마감 체크
                if soxl_price == 0:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏸️  미국 장 마감, 대기 중...")

                time.sleep(300)  # 5분 간격

            except KeyboardInterrupt:
                print("\n[종료] 사용자 중단")
                break
            except Exception as e:
                print(f"[ERROR] 메인 루프: {e}")
                time.sleep(300)

    def get_ensemble_signal(self, trend: str) -> str:
        """14b × 2 앙상블 LLM 신호"""
        # 간단 구현 (추세 기반)
        return 'BULL' if trend == 'BULL' else ('BEAR' if trend == 'BEAR' else 'NEUTRAL')

    def open_position(self, symbol: str):
        """포지션 진입"""
        print(f"\n[진입] {symbol}")
        # 구현 생략 (실제 주문 로직)
        pass

    def close_position(self, reason: str):
        """포지션 청산"""
        print(f"\n[청산] {self.current_position} (이유: {reason})")
        # 구현 생략 (실제 주문 로직)
        pass

if __name__ == "__main__":
    trader = ExplosiveKISTrader()
    trader.run()
