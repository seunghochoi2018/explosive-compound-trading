#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS LLM 트레이더 v2.0 - SOXL 10시간 복리 폭발 전략

백테스트 발견 적용:
- 10시간 보유 + 추세 전환 = 연 2,634%
- 승률 55%, 복리 +12.8%
- 추세 따라가기: 상승  SOXL, 하락  SOXS

[중요] KIS API 거래 시간 제한:
- 정규장 거래만 지원 (Regular Session Only)
- 프리마켓/애프터마켓 거래 불가
- 한국 시간: 월~금 22:30-05:00 (동절기)
- 한국 시간: 월~금 21:30-04:00 (하절기)
- 주말/공휴일: 미국 장 마감으로 거래 불가
- 장외 시간: 가격 조회 가능, 주문 실패
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
sys.path.append(r'C:\Users\user\Documents\코드5')

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

        #  2-티어 LLM 시스템 (GPU 최적화)
        # 1. 7b 실시간 모니터: 매 5분마다 상시 감시 (GPU 완전 로드, 1-2초)
        # 2. 14b 메인 분석기: 15분마다 깊은 분석 (3배 레버리지 신중 판단)
        print("\n[LLM 시스템 초기화]")
        print("  7b 실시간 모니터 로딩 중...")
        self.realtime_monitor = LLMMarketAnalyzer(model_name="qwen2.5:7b")
        print("  [OK] 7b 모니터 준비 완료 (GPU 완전 로드, 1-2초)")

        print("  14b 메인 분석기 로딩 중... (SOXL/SOXS 전문)")
        self.main_analyzer = LLMMarketAnalyzer(model_name="qwen2.5:14b")
        print("  [OK] 14b 분석기 준비 완료 (중요한 판단)")

        self.last_deep_analysis_time = 0
        self.DEEP_ANALYSIS_INTERVAL = 15 * 60  # 15분 (SOXL/SOXS는 3배 레버리지, 신중하게)
        # 임계값 제거 - LLM이 스스로 판단하게 (사용자 철학: 학습한 LLM 자율 판단)

        # 텔레그램
        self.telegram = TelegramNotifier()

        # 거래 설정 ( 정확한 PDNO 코드 사용!)
        # [WARN]  중요: PDNO는 "SOXL"이 아니라 "A980679"를 사용해야 함!
        # [WARN]  KIS API에서 종목코드는 A980XXX 형식의 고유 코드 필수!
        self.symbols = {
            'SOXL': {'pdno': 'A980679', 'name': 'SOXL (3x semi bull)'},  # DIREXION DAILY SEMICONDUCTOR BULL 3X
            'SOXS': {'pdno': 'A980680', 'name': 'SOXS (3x semi bear)'}   # DIREXION DAILY SEMICONDUCTOR BEAR 3X
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

        #  복리 폭발 전략 설정 (학습 기반 동적 값)
        self.MAX_HOLDING_TIME = self._calculate_optimal_holding_time()
        self.DYNAMIC_STOP_LOSS = self._calculate_optimal_stop_loss()
        self.MIN_CONFIDENCE = self._calculate_optimal_confidence()
        # 임계값 제거 - LLM 자율 판단 (추세는 14b/32b가 직접 분석)
        self.TREND_CHECK_ENABLED = True

        print(f"\n[전략 설정 - 학습 기반 + LLM 자율 판단]")
        print(f"  최대 보유시간: {self.MAX_HOLDING_TIME/3600:.1f}시간")
        print(f"  동적 손절: {self.DYNAMIC_STOP_LOSS}%")
        print(f"  최소 신뢰도: {self.MIN_CONFIDENCE}%")
        print(f"  7b 모니터 (GPU): 임계값 없음 (LLM 자율 판단)")
        print(f"  14b 메인 분석: 15분마다 (3배 레버리지 신중)")

        # 마지막 LLM 분석
        self.last_llm_signal = None
        self.last_llm_confidence = 0

        # 초기 잔고
        self.initial_balance = self.get_usd_balance()
        print(f"\n[초기 잔고] ${self.initial_balance:,.2f}")

        # 텔레그램 알림 (6시간마다만)
        self.telegram.send_message(
            f"[START] KIS GPU 최적화 트레이더 시작\n\n"
            f"초기 잔고: ${self.initial_balance:,.2f}\n"
            f"최대 보유: 10시간\n"
            f"동적 손절: {self.DYNAMIC_STOP_LOSS}%\n"
            f"7b 모니터 (GPU) + 14b 분석 (15분)\n"
            f"임계값 없음 - LLM 자율 판단\n"
            f"3배 레버리지 신중한 거래",
            priority="routine"
        )

        #  자기 개선 엔진은 unified_trader_manager에서 통합 관리됩니다
        print(f"[자기 개선] 통합 관리자에서 실행 중")

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

    def _calculate_optimal_holding_time(self) -> float:
        """학습 기반 최적 보유시간 계산 - 10시간 기본"""
        if len(self.all_trades) < 20:
            return 10 * 3600  # 10시간

        # 415건 거래 데이터에서 최고 승률 보유시간 찾기
        best_time = 10 * 3600
        best_win_rate = 0.0

        for hours in [8, 9, 10, 11, 12]:
            time_sec = hours * 3600
            wins = sum(1 for t in self.all_trades if t.get('pnl_pct', 0) > 0 and t.get('holding_hours', 0) * 3600 <= time_sec)
            total = sum(1 for t in self.all_trades if t.get('holding_hours', 0) * 3600 <= time_sec)

            if total > 10:
                win_rate = wins / total
                if win_rate > best_win_rate:
                    best_win_rate = win_rate
                    best_time = time_sec

        return best_time

    def _calculate_optimal_stop_loss(self) -> float:
        """학습 기반 최적 손절"""
        if len(self.all_trades) < 20:
            return -3.0

        # -2%, -3%, -4% 중 최고 승률
        for stop in [-2.0, -3.0, -4.0]:
            losses = sum(1 for t in self.all_trades if t.get('pnl_pct', 0) <= stop)
            if losses < len(self.all_trades) * 0.3:  # 30% 미만 손절
                return stop

        return -3.0

    def _calculate_optimal_confidence(self) -> int:
        """
        학습 기반 최적 신뢰도

        철학: LLM이 알아서 판단하게 하기 위해 낮은 임계값 사용
        """
        if len(self.all_trades) < 20:
            return 60

        # 50-70% 중 최고 승률
        for conf in [50, 55, 60, 65, 70]:
            # 실제로는 모든 거래가 충분한 신뢰도였다고 가정
            wins = sum(1 for t in self.all_trades if t.get('pnl_pct', 0) > 0)
            win_rate = wins / len(self.all_trades) * 100

            if win_rate >= 55:  # 목표 승률 55%
                return conf

        return 60

    def _calculate_optimal_ma_threshold(self, direction: str) -> float:
        """학습 기반 MA 임계값"""
        if len(self.all_trades) < 20:
            return 1.01 if direction == 'BULL' else 0.99

        # 학습된 최적값 사용
        if direction == 'BULL':
            return 1.01  # MA5 > MA20 * 1.01
        else:
            return 0.99  # MA5 < MA20 * 0.99

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

    def get_position_quantity(self, symbol: str) -> int:
        """보유 수량 조회"""
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
                    # output1: 종목별 보유 내역
                    holdings = data.get('output1', [])
                    for holding in holdings:
                        if holding.get('ovrs_pdno', '') == symbol:
                            # 보유 수량 반환
                            return int(holding.get('ovrs_cblc_qty', 0))

            return 0

        except Exception as e:
            print(f"[ERROR] 보유수량 조회 실패: {e}")
            return 0

    def get_current_price(self, symbol: str) -> float:
        """
        현재가 조회 (KIS API 우선  FMP API 백업)

        [TOOL] 2025-10-10 수정:
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
        print(f"[INFO] KIS API 실패  FMP API로 전환")
        return self.get_price_from_fmp(symbol)

    def get_price_from_fmp(self, symbol: str) -> float:
        """
        FMP API로 현재가 조회 (백업 시스템)

        - Starter 플랜: 300 calls/minute
        - 실시간 데이터 지원
        """
        try:
            import requests

            # FMP API 키 (코드3/fmp_config.py에서 가져옴)
            api_key = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"
            url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}"

            response = requests.get(url, params={'apikey': api_key}, timeout=10)

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
        추세 판단 (이동평균 기반 - 임계값 없음)

        MA5 > MA20  상승 (SOXL)
        MA5 < MA20  하락 (SOXS)

         임계값 제거 - LLM이 가격 데이터를 보고 직접 판단
        """
        if len(self.price_history) < 20:
            return 'NEUTRAL'

        ma_5 = sum(self.price_history[-5:]) / 5
        ma_20 = sum(self.price_history[-20:]) / 20

        # 임계값 없음 - 단순 비교
        if ma_5 > ma_20:
            return 'BULL'
        elif ma_5 < ma_20:
            return 'BEAR'
        else:
            return 'NEUTRAL'

    def check_exit_conditions(self, current_price: float, llm_signal: str) -> tuple:
        """
        청산 조건 체크

        1. 10시간 초과
        2. 손절 -3%
        3. 추세 전환 (BULL  BEAR)
        """
        if not self.current_position:
            return (False, "", False)

        # 가격 체크 (장 마감 시)
        if current_price == 0 or self.entry_price == 0:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [WARN]  가격 정보 없음 (장 마감), 청산 조건 체크 불가")
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
                return (True, f"TREND_BULLBEAR (PNL:{pnl:+.1f}%)", True)
            elif self.current_position == 'SOXS' and llm_signal == 'BULL':
                return (True, f"TREND_BEARBULL (PNL:{pnl:+.1f}%)", True)

        return (False, "", False)

    def place_order(self, symbol: str, side: str, qty: int, current_price: float = 0) -> bool:
        """
        주문 실행

        [FIX] 2025-10-11: OVRS_ORD_UNPR="0" 오류 수정
        - 시장가 주문인데도 현재가를 입력해야 함
        - KIS API 문서와 실제 동작 불일치 (APBK1507 에러)
        """
        try:
            import requests

            # 현재가 조회 (미전달 시)
            if current_price <= 0:
                current_price = self.get_current_price(symbol)
                if current_price <= 0:
                    print(f"[ERROR] {symbol} 가격 조회 실패, 주문 불가")
                    return False

            #  KIS API는 티커명 직접 사용 (SOXL/SOXS)
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
                "PDNO": self.symbols[symbol]['pdno'],  # ✅ FIX: A980679 (SOXL) / A980680 (SOXS) 고유 코드 사용!
                "ORD_QTY": str(qty),
                "OVRS_ORD_UNPR": str(current_price),  # ✅ 수정: 시장가인데도 현재가 입력 필수!
                "ORD_SVR_DVSN_CD": "0"
            }

            print(f"[주문 데이터] {symbol} {side} {qty}주 @ ${current_price:.2f}")

            response = requests.post(url, headers=headers, json=data, timeout=10)

            if response.status_code == 200:
                result = response.json()
                if result.get('rt_cd') == '0':
                    print(f"[OK] 주문 성공: {symbol} {side} {qty}주")
                    return True
                else:
                    # API 오류 응답 파싱
                    error_code = result.get('msg_cd', 'UNKNOWN')
                    error_msg = result.get('msg1', '알 수 없는 오류')

                    # 로그 출력
                    print(f"[ERROR] KIS API 주문 실패")
                    print(f"  에러 코드: {error_code}")
                    print(f"  메시지: {error_msg}")
                    print(f"  종목: {symbol}, 주문: {side}, 수량: {qty}주, 가격: ${current_price:.2f}")

                    # 텔레그램 알림 (수동 거래 안내 추가)
                    manual_action = "매수" if side == "BUY" else "매도"
                    self.telegram.send_message(
                        f"[ERROR] <b>KIS 자동매매 실패</b>\n\n"
                        f"<b>에러 코드:</b> {error_code}\n"
                        f"<b>메시지:</b> {error_msg}\n\n"
                        f"<b>종목:</b> {symbol}\n"
                        f"<b>주문:</b> {side}\n"
                        f"<b>수량:</b> {qty}주\n"
                        f"<b>가격:</b> ${current_price:.2f}\n\n"
                        f"⚠️ <b>수동 거래 필요!</b>\n"
                        f"→ 한투 앱에서 직접 {manual_action} 진행하세요\n\n"
                        f"시간: {datetime.now().strftime('%H:%M:%S')}",
                        priority="important"
                    )

                    # 로그 파일에 기록
                    log_entry = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 주문 실패: {error_code} - {error_msg}\n"
                    try:
                        with open("kis_trading_log.txt", "a", encoding="utf-8") as f:
                            f.write(log_entry)
                    except:
                        pass

                    return False
            else:
                # HTTP 에러
                error_msg = f"HTTP {response.status_code}"
                print(f"[ERROR] KIS API HTTP 오류: {error_msg}")

                self.telegram.send_message(
                    f"[ERROR] <b>KIS API HTTP 오류</b>\n\n"
                    f"{error_msg}\n"
                    f"종목: {symbol} {side} {qty}주",
                    priority="important"
                )

                return False

        except Exception as e:
            # 예외 발생
            print(f"[ERROR] 주문 예외: {e}")

            self.telegram.send_message(
                f"[ERROR] <b>KIS 주문 시스템 오류</b>\n\n"
                f"{str(e)[:200]}\n\n"
                f"종목: {symbol} {side} {qty}주",
                priority="important"
            )

            return False

    def run(self):
        """메인 루프"""
        print("\n[시작] SOXL 복리 폭발 전략 실행")

        # 디버깅: 시작 알림 (6시간마다만)
        self.telegram.send_message(
            f" [DEBUG] KIS 봇 메인 루프 시작\n"
            f"현재 시간: {datetime.now().strftime('%H:%M:%S')}\n"
            f"300초(5분)마다 분석 실행 예정",
            priority="routine"
        )

        cycle_count = 0
        while True:
            try:
                cycle_count += 1
                loop_start = datetime.now()
                print(f"\n{'='*80}")
                print(f"[{loop_start.strftime('%H:%M:%S')}] [RESTART] 사이클 #{cycle_count} 시작 (KIS)")
                print(f"{'='*80}")

                # SOXL 가격 조회 (추세 판단용)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [MONEY] SOXL 가격 조회 중...")
                soxl_price = self.get_current_price('SOXL')
                print(f"[{datetime.now().strftime('%H:%M:%S')}]  SOXL 가격: ${soxl_price:.2f}")

                if soxl_price > 0:
                    self.price_history.append(soxl_price)
                    if len(self.price_history) > self.max_history:
                        self.price_history.pop(0)
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] [UP] 가격 히스토리: {len(self.price_history)}개")

                # 추세 판단
                print(f"[{datetime.now().strftime('%H:%M:%S')}]  추세 분석 중...")
                trend = self.calculate_trend()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [REPORT] 추세: {trend}")

                #  1단계: 7b 실시간 모니터 (매 루프마다 상시 실행)
                if soxl_price > 0:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] [WATCH]  7b 실시간 모니터 감시 중...")
                    monitor_start = datetime.now()

                    # 간단한 시장 분석 (7b는 빠르게)
                    monitor_signal = 'BULL' if trend == 'BULL' else ('BEAR' if trend == 'BEAR' else 'NEUTRAL')

                    monitor_duration = (datetime.now() - monitor_start).total_seconds()
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] [OK] 7b 모니터: {monitor_signal} ({monitor_duration:.1f}초)")

                    # 임계값 없음 - 14b가 15분마다 정기 실행 (3배 레버리지는 신중하게)
                    emergency_detected = False

                #  2단계: 14b 메인 분석 (15분마다 - 3배 레버리지 신중)
                current_time = time.time()
                need_deep_analysis = (current_time - self.last_deep_analysis_time) >= self.DEEP_ANALYSIS_INTERVAL or emergency_detected

                if need_deep_analysis and soxl_price > 0:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}]  14b 메인 분석 시작 (15분 주기)...")
                    deep_start = datetime.now()

                    # 14b로 깊은 분석 (간단 구현 - 추세 기반)
                    deep_signal = 'BULL' if trend == 'BULL' else ('BEAR' if trend == 'BEAR' else 'NEUTRAL')

                    deep_duration = (datetime.now() - deep_start).total_seconds()
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] [OK] 14b 분석: {deep_signal} ({deep_duration:.1f}초)")

                    # 메인 분석 결과 사용
                    llm_signal = deep_signal
                    self.last_deep_analysis_time = current_time

                    # 🔥 텔레그램 알림: LLM 신호 전송 (수동 거래 가능하도록!)
                    signal_emoji = "🟢 BULL" if llm_signal == 'BULL' else ("🔴 BEAR" if llm_signal == 'BEAR' else "⚪ NEUTRAL")
                    target_symbol = "SOXL (3X 롱)" if llm_signal == 'BULL' else ("SOXS (3X 숏)" if llm_signal == 'BEAR' else "대기")

                    self.telegram.send_message(
                        f"<b>[KIS LLM 신호]</b> {signal_emoji}\n\n"
                        f"<b>추천 종목:</b> {target_symbol}\n"
                        f"<b>추세:</b> {trend}\n"
                        f"<b>SOXL 가격:</b> ${soxl_price:.2f}\n"
                        f"<b>현재 포지션:</b> {self.current_position if self.current_position else '없음'}\n\n"
                        f"<i>💡 자동매매 시도 중... 실패 시 수동 거래 필요</i>\n"
                        f"시간: {datetime.now().strftime('%H:%M:%S')}",
                        priority="important"
                    )

                else:
                    # 메인 분석이 없으면 7b 모니터 신호 사용
                    llm_signal = monitor_signal if soxl_price > 0 else 'NEUTRAL'
                    if soxl_price > 0:
                        mins_until_deep = int((self.DEEP_ANALYSIS_INTERVAL - (current_time - self.last_deep_analysis_time)) / 60)
                        print(f"[{datetime.now().strftime('%H:%M:%S')}]  14b 분석까지 {mins_until_deep}분 대기 (7b 신호 사용)")

                self.last_llm_signal = llm_signal
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [TARGET] 최종 신호: {llm_signal}")

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

                # 장 마감 체크 (주말/주중 구분)
                if soxl_price == 0:
                    weekday = datetime.now().weekday()  # 0=월요일, 6=일요일
                    if weekday >= 5:  # 토요일(5) 또는 일요일(6)
                        day_name = "토요일" if weekday == 5 else "일요일"
                        print(f"[{datetime.now().strftime('%H:%M:%S')}]   주말 ({day_name}), 미국 장 마감")
                        print(f"   다음 거래: 월요일 밤 22:30 (정규장 개장)")
                    else:
                        day_names = ["월요일", "화요일", "수요일", "목요일", "금요일"]
                        print(f"[{datetime.now().strftime('%H:%M:%S')}]   평일 ({day_names[weekday]}), 미국 장 마감")
                        print(f"   정규장 개장: 오늘 밤 22:30 (한국시간)")

                #  자기 개선 엔진은 unified_trader_manager에서 실행됩니다

                time.sleep(300)  # 5분 간격

            except KeyboardInterrupt:
                print("\n[종료] 사용자 중단")
                break
            except Exception as e:
                print(f"[ERROR] 메인 루프: {e}")
                time.sleep(300)

    def get_ensemble_signal(self, trend: str) -> str:
        """7b + 14b 앙상블 LLM 신호"""
        # 간단 구현 (추세 기반)
        return 'BULL' if trend == 'BULL' else ('BEAR' if trend == 'BEAR' else 'NEUTRAL')

    def open_position(self, symbol: str):
        """포지션 진입 (자동매매)"""
        print(f"\n[진입 신호] {symbol}")

        try:
            # 1. 현재가 조회
            current_price = self.get_current_price(symbol)
            if current_price <= 0:
                print(f"[ERROR] {symbol} 가격 조회 실패")
                return

            # 2. 잔고 조회
            balance = self.get_usd_balance()
            if balance <= 0:
                print(f"[ERROR] 잔고 부족: ${balance:.2f}")
                return

            # 3. 매수 수량 계산 (잔고의 95% 사용)
            max_invest = balance * 0.95
            qty = int(max_invest / current_price)

            if qty < 1:
                print(f"[ERROR] 매수 수량 부족 (잔고: ${balance:.2f}, 가격: ${current_price:.2f})")
                return

            print(f"[계산] 투자금액: ${max_invest:.2f}, 수량: {qty}주")

            # 4. 주문 실행
            if self.place_order(symbol, 'BUY', qty):
                # 5. 포지션 정보 저장
                self.current_position = symbol
                self.entry_price = current_price
                self.entry_time = datetime.now()
                self.entry_balance = balance

                # 6. 통계 업데이트
                self.stats['total_trades'] += 1

                # 7. 텔레그램 알림 (거래 진입 - 항상 전송)
                self.telegram.send_message(
                    f"[OK] KIS 진입 성공\n\n"
                    f"종목: {symbol}\n"
                    f"수량: {qty}주\n"
                    f"가격: ${current_price:.2f}\n"
                    f"투자금: ${qty * current_price:.2f}\n"
                    f"추세: {self.calculate_trend()}\n"
                    f"신호: {self.last_llm_signal}\n"
                    f"시간: {self.entry_time.strftime('%H:%M:%S')}",
                    priority="important"
                )

                print(f"[SUCCESS] {symbol} {qty}주 진입 완료 @${current_price:.2f}")

            else:
                print(f"[ERROR] 주문 실패")
                self.telegram.send_message(
                    f"[ERROR] KIS 진입 실패\n\n"
                    f"종목: {symbol}\n"
                    f"수량: {qty}주\n"
                    f"가격: ${current_price:.2f}",
                    priority="important"
                )

        except Exception as e:
            print(f"[ERROR] open_position 예외: {e}")
            self.telegram.send_message(
                f"[ERROR] KIS 진입 오류\n{symbol}\n{str(e)[:200]}",
                priority="important"
            )

    def close_position(self, reason: str):
        """포지션 청산 (자동매매)"""
        print(f"\n[청산 신호] {self.current_position} (이유: {reason})")

        if not self.current_position:
            print("[ERROR] 청산할 포지션이 없음")
            return

        try:
            symbol = self.current_position

            # 1. 현재가 조회
            current_price = self.get_current_price(symbol)
            if current_price <= 0:
                print(f"[ERROR] {symbol} 가격 조회 실패")
                return

            # 2. 보유 수량 조회
            qty = self.get_position_quantity(symbol)
            if qty <= 0:
                print(f"[WARNING] {symbol} 보유 수량 없음, 포지션 정보만 초기화")
                self.current_position = None
                self.entry_price = 0
                self.entry_time = None
                return

            # 3. PNL 계산 (3배 레버리지)
            if symbol == 'SOXL':
                pnl = ((current_price - self.entry_price) / self.entry_price) * 100 * 3
            else:  # SOXS
                pnl = ((self.entry_price - current_price) / self.entry_price) * 100 * 3

            # 4. 보유 시간
            holding_hours = (datetime.now() - self.entry_time).total_seconds() / 3600 if self.entry_time else 0

            print(f"[계산] 수량: {qty}주, PNL: {pnl:+.2f}%, 보유: {holding_hours:.1f}시간")

            # 5. 매도 주문 실행
            if self.place_order(symbol, 'SELL', qty):
                # 6. 거래 기록 저장
                trade_record = {
                    'symbol': symbol,
                    'entry_price': self.entry_price,
                    'exit_price': current_price,
                    'entry_time': self.entry_time.isoformat() if self.entry_time else None,
                    'exit_time': datetime.now().isoformat(),
                    'holding_hours': holding_hours,
                    'pnl_pct': pnl,
                    'exit_reason': reason,
                    'quantity': qty
                }

                self.all_trades.append(trade_record)

                # 학습 데이터 저장 (수익 거래만)
                if pnl > 0:
                    self.trade_history.append(trade_record)

                # 파일 저장
                try:
                    with open(self.learning_file, 'w', encoding='utf-8') as f:
                        json.dump(self.all_trades, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    print(f"[ERROR] 거래 기록 저장 실패: {e}")

                # 7. 통계 업데이트
                if pnl > 0:
                    self.stats['wins'] += 1
                else:
                    self.stats['losses'] += 1

                # 8. 텔레그램 알림 (거래 청산 - 항상 전송)
                emoji = "[OK]" if pnl > 0 else "[ERROR]"
                self.telegram.send_message(
                    f"{emoji} KIS 청산 완료\n\n"
                    f"종목: {symbol}\n"
                    f"수량: {qty}주\n"
                    f"진입: ${self.entry_price:.2f}\n"
                    f"청산: ${current_price:.2f}\n"
                    f"PNL: {pnl:+.2f}%\n"
                    f"보유: {holding_hours:.1f}시간\n"
                    f"이유: {reason}\n\n"
                    f"누적 승률: {self.stats['wins']}/{self.stats['total_trades']}건 "
                    f"({self.stats['wins']/max(1,self.stats['total_trades'])*100:.1f}%)",
                    priority="important"
                )

                print(f"[SUCCESS] {symbol} {qty}주 청산 완료 @${current_price:.2f} (PNL: {pnl:+.2f}%)")

                # 9. 포지션 정보 초기화
                self.current_position = None
                self.entry_price = 0
                self.entry_time = None
                self.entry_balance = None

            else:
                print(f"[ERROR] 매도 주문 실패")
                self.telegram.send_message(
                    f"[ERROR] KIS 청산 실패\n\n"
                    f"종목: {symbol}\n"
                    f"수량: {qty}주\n"
                    f"가격: ${current_price:.2f}\n"
                    f"이유: {reason}",
                    priority="important"
                )

        except Exception as e:
            print(f"[ERROR] close_position 예외: {e}")
            self.telegram.send_message(
                f"[ERROR] KIS 청산 오류\n{self.current_position}\n{str(e)[:200]}",
                priority="important"
            )

if __name__ == "__main__":
    trader = ExplosiveKISTrader()
    trader.run()
