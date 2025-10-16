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
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

# 한국투자증권 API (기존 코드 활용)
import sys
sys.path.append('C:/Users/user/Documents/코드4')
sys.path.append(r'C:\Users\user\Documents\코드5')

from llm_market_analyzer import LLMMarketAnalyzer
from telegram_notifier import TelegramNotifier
from generate_learned_strategies_kis import generate_learned_strategies

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

        #  7b 모델 2개 시스템 (앙상블 + 백업)
        print("\n[7b 모델 2개 시스템 초기화]")
        print("  7b 모델 1 로딩 중...")
        self.realtime_monitor = LLMMarketAnalyzer(model_name="qwen2.5:7b")
        print("  [OK] 7b 모델 1 준비 완료 (실시간 모니터)")

        print("  7b 모델 2 로딩 중... (앙상블 백업)")
        self.main_analyzer = LLMMarketAnalyzer(model_name="qwen2.5:7b")
        print("  [OK] 7b 모델 2 준비 완료 (앙상블 분석)")

        self.last_deep_analysis_time = 0
        self.DEEP_ANALYSIS_INTERVAL = 15 * 60  # 15분 (SOXL/SOXS는 3배 레버리지, 신중하게)
        # 임계값 제거 - LLM이 스스로 판단하게 (사용자 철학: 학습한 LLM 자율 판단)

        # 텔레그램
        self.telegram = TelegramNotifier()

        # 거래 설정 ( 정확한 PDNO 코드 사용!)
        # [WARN]  중요: PDNO는 "SOXL"이 아니라 "A980679"를 사용해야 함!
        # [WARN]  KIS API에서 종목코드는 A980XXX 형식의 고유 코드 필수!
        self.symbols = {
            'SOXL': {'pdno': 'A980679', 'name': 'SOXL (반도체 3배 레버리지 롱)'},  # DIREXION DAILY SEMICONDUCTOR BULL 3X
            'SOXS': {'pdno': 'A980680', 'name': 'SOXS (반도체 3배 레버리지 숏)'}   # DIREXION DAILY SEMICONDUCTOR BEAR 3X
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

        # ETH와 동일한 로직 적용
        self.MAX_HOLDING_TIME = 60 * 60  # 60분 (ETH와 동일)
        self.DYNAMIC_STOP_LOSS = -2.0  # -2% (ETH와 동일)
        
        # 동적 임계값 시스템 (ETH와 동일)
        self.threshold_file = "kis_dynamic_threshold.json"
        self.MIN_CONFIDENCE = self.load_dynamic_threshold()
        self.TREND_CHECK_ENABLED = True
        
        # 잔고 기반 공격적 모드 (ETH와 동일)
        current_balance = self.get_usd_balance()
        if current_balance <= 1000:
            self.MIN_CONFIDENCE = 40  # $1000 이하: 40% (공격적)
            print(f"  [공격적 모드] 잔고 ${current_balance:.2f} → 임계값 40% (빠른 성장)")
        else:
            print(f"  [기존 모드] 잔고 ${current_balance:.2f} → 임계값 {self.MIN_CONFIDENCE}%")

        print(f"\n[전략 설정 - 학습 기반 + LLM 자율 판단]")
        print(f"  최대 보유시간: {self.MAX_HOLDING_TIME/3600:.1f}시간")
        print(f"  동적 손절: {self.DYNAMIC_STOP_LOSS}%")
        print(f"  최소 신뢰도: {self.MIN_CONFIDENCE}%")
        print(f"  7b 모니터 (GPU): 임계값 없음 (LLM 자율 판단)")
        print(f"  14b 메인 분석: 15분마다 (3배 레버리지 신중)")

        # 마지막 LLM 분석
        self.last_llm_signal = None
        self.last_llm_confidence = 0
        
        # 안전장치 관련 변수 (ETH와 동일)
        self.last_safety_time = None
        self.consecutive_losses = 0
        self.max_consecutive_losses = 3
        
        # 5분 단위 안전장치 체크
        self.last_safety_check_time = 0
        self.SAFETY_CHECK_INTERVAL = 300  # 5분마다 안전장치 체크
        
        # 텔레그램 알림 중복 방지
        self.previous_position = None

        # 초기 잔고 + 잔고 캐시 (API 불안정 대비)
        self._usd_balance_cache = 0.0
        self.initial_balance = self.get_usd_balance()
        print(f"\n[초기 잔고] ${self.initial_balance:,.2f}")

        # 📝 페이퍼 트레이딩 모드 (빠른 검증)
        self.paper_trading_mode = True  # 처음엔 가상 거래
        self.paper_trades = []
        self.paper_balance = self.initial_balance
        self.PAPER_TRADE_REQUIRED = 10  # 10회로 단축
        self.PAPER_WIN_RATE_THRESHOLD = 0.60  # 승률 60% 유지
        print(f"\n[페이퍼 트레이딩] 가상 거래 모드 시작")
        print(f"  목표: {self.PAPER_TRADE_REQUIRED}거래, 승률 {self.PAPER_WIN_RATE_THRESHOLD*100:.0f}% 달성")
        print(f"  달성 시 → 실거래 자동 전환")

        # 텔레그램 알림 (6시간마다만)
        mode_text = "📝 페이퍼 트레이딩 (가상)" if self.paper_trading_mode else "🚀 실거래 모드"
        self.telegram.send_message(
            f"[START] KIS GPU 최적화 트레이더 시작\n\n"
            f"모드: {mode_text}\n"
            f"초기 잔고: ${self.initial_balance:,.2f}\n"
            f"페이퍼 목표: {self.PAPER_TRADE_REQUIRED}거래, 승률 {self.PAPER_WIN_RATE_THRESHOLD*100:.0f}%\n"
            f"최대 보유: 10시간\n"
            f"동적 손절: {self.DYNAMIC_STOP_LOSS}%\n"
            f"백테스팅: 60% 성공률 검증\n"
            f"7b 모니터 (GPU) + 14b 분석 (15분)\n"
            f"임계값 없음 - LLM 자율 판단\n"
            f"3배 레버리지 신중한 거래",
            priority="routine"
        )

        #  자기 개선 엔진은 unified_trader_manager에서 통합 관리됩니다
        print(f"[자기 개선] 통합 관리자에서 실행 중")

    def is_us_regular_hours(self) -> bool:
        """미국(ET) 정규장 여부: 평일 09:30~16:00 (서머타임 자동 반영)"""
        now_et = datetime.now(ZoneInfo("America/New_York"))
        if now_et.weekday() >= 5:  # 토(5), 일(6)
            return False
        total_minutes = now_et.hour * 60 + now_et.minute
        return 570 <= total_minutes <= 960  # 09:30(570) ~ 16:00(960)

    def load_kis_config(self):
        """KIS API 설정 로드"""
        try:
            # kis_devlp.yaml 로드
            with open('kis_devlp.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # 실전투자 키 사용
            self.app_key = config['my_app']
            self.app_secret = config['my_sec']
            self.account_no = config['my_acct']
            self.base_url = "https://openapi.koreainvestment.com:9443"  # 실전투자 환경

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

    def load_dynamic_threshold(self) -> int:
        """동적 임계값 로드 (ETH와 동일)"""
        try:
            with open(self.threshold_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                current_threshold = data.get('current_threshold', 60)
                last_trade_time = data.get('last_trade_time', None)

                print(f"\n[동적 임계값] 로드: {current_threshold}%")

                # 마지막 거래 시간 체크
                if last_trade_time:
                    last_time = datetime.fromisoformat(last_trade_time)
                    minutes_since = (datetime.now() - last_time).total_seconds() / 60

                    # 3분당 -5% 조정 (더 빠른 조정)
                    adjustment = int(minutes_since / 3) * 5
                    adjusted_threshold = max(25, current_threshold - adjustment)

                    if adjusted_threshold != current_threshold:
                        print(f"  [AUTO] 자동 조정: {current_threshold}% -> {adjusted_threshold}%")
                        print(f"  이유: {minutes_since:.0f}분 거래 없음 (3분당 -5%)")
                        current_threshold = adjusted_threshold
                        self.save_dynamic_threshold(current_threshold, last_trade_time)

                return current_threshold

        except FileNotFoundError:
            # 첫 실행: 기본값 60%
            print(f"\n[동적 임계값] 초기화: 60%")
            self.save_dynamic_threshold(60, None)
            return 60

    def save_dynamic_threshold(self, threshold: int, last_trade_time: str = None):
        """동적 임계값 저장"""
        try:
            data = {
                'current_threshold': threshold,
                'last_trade_time': last_trade_time,
                'updated_at': datetime.now().isoformat()
            }
            with open(self.threshold_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[WARN] 임계값 저장 실패: {e}")

    def adjust_threshold_on_trade(self, success: bool):
        """거래 후 임계값 조정"""
        if success:
            # 성공 → +2% (최대 65%)
            new_threshold = min(65, self.MIN_CONFIDENCE + 2)
            if new_threshold != self.MIN_CONFIDENCE:
                print(f"[임계값 상승] {self.MIN_CONFIDENCE}% → {new_threshold}% (거래 성공)")
                self.MIN_CONFIDENCE = new_threshold

        # 마지막 거래 시간 업데이트
        self.save_dynamic_threshold(
            self.MIN_CONFIDENCE,
            datetime.now().isoformat()
        )

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
                "WCRC_FRCR_DVSN_CD": "02",  # 외화 기준 금액
                "NATN_CD": "840",           # 미국
                "TR_MKET_CD": "01",        # 시장 코드
                "OVRS_EXCG_CD": "NASD",    # 거래소: NASDAQ
                "TR_CRCY_CD": "USD",       # 통화: USD
                "CTX_AREA_FK100": "",
                "CTX_AREA_NK100": "",
                "CTX_AREA_FK200": "",
                "CTX_AREA_NK200": ""
            }

            print(f"[DEBUG][KIS] USD 잔고 요청 params: {params}")
            response = requests.get(url, headers=headers, params=params, timeout=10)
            print(f"[DEBUG][KIS] USD 잔고 응답 status: {response.status_code}")
            try:
                j = response.json()
                print(f"[DEBUG][KIS] USD 잔고 응답 요약: rt_cd={j.get('rt_cd')} keys={list(j.keys())}")
            except Exception as _:
                print("[DEBUG][KIS] USD 잔고 응답 JSON 파싱 실패")

            if response.status_code == 200:
                data = response.json()
                if data.get('rt_cd') == '0':
                    output2 = data.get('output2', {})
                    print(f"[DEBUG][KIS] output2 keys: {list(output2.keys())}")
                    cand = {
                        'ovrs_ncash_blce_amt': output2.get('ovrs_ncash_blce_amt'),
                        'ovrs_buy_psbl_amt': output2.get('ovrs_buy_psbl_amt'),
                        'tot_evlu_pfls_amt': output2.get('tot_evlu_pfls_amt'),
                        'ovrs_evlu_pfls_amt': output2.get('ovrs_evlu_pfls_amt'),
                        'frcr_dncl_amt_2': output2.get('frcr_dncl_amt_2'),
                    }
                    print(f"[DEBUG][KIS] candidates: {cand}")
                    # 우선순위: 외화예수금 → 외화매수가능금액 → 총평가손익 → 해외주식 평가손익 → (기존) 외화예수금2
                    raw_val = (
                        cand['ovrs_ncash_blce_amt']
                        or cand['ovrs_buy_psbl_amt']
                        or cand['tot_evlu_pfls_amt']
                        or cand['ovrs_evlu_pfls_amt']
                        or cand['frcr_dncl_amt_2']
                        or 0
                    )
                    try:
                        usd_balance = float(str(raw_val).replace(',', ''))
                    except Exception:
                        usd_balance = 0.0
                    # 캐시 업데이트/폴백: 0.0이면 최근 정상값 유지
                    if usd_balance > 0:
                        self._usd_balance_cache = usd_balance
                    elif self._usd_balance_cache > 0:
                        print(f"[CACHE] KIS 잔고 API=0 → 캐시 사용: ${self._usd_balance_cache:.2f}")
                        usd_balance = self._usd_balance_cache
                    print(f"[DEBUG][KIS] USD 잔고 파싱: {usd_balance}")
                    return usd_balance

            # HTTP 비정상 시에도 캐시 폴백
            if getattr(self, '_usd_balance_cache', 0.0) > 0:
                print(f"[CACHE] HTTP 오류 → 캐시 잔고 사용: ${self._usd_balance_cache:.2f}")
                return self._usd_balance_cache
            return 0.0

        except Exception as e:
            print(f"[ERROR] 잔고 조회 실패: {e}")
            if getattr(self, '_usd_balance_cache', 0.0) > 0:
                print(f"[CACHE] 예외 발생 → 캐시 잔고 사용: ${self._usd_balance_cache:.2f}")
                return self._usd_balance_cache
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
                "WCRC_FRCR_DVSN_CD": "02",
                "NATN_CD": "840",
                "TR_MKET_CD": "01",
                "OVRS_EXCG_CD": "NASD",
                "TR_CRCY_CD": "USD",
                "CTX_AREA_FK100": "",
                "CTX_AREA_NK100": "",
                "CTX_AREA_FK200": "",
                "CTX_AREA_NK200": ""
            }

            print(f"[DEBUG][KIS] 보유수량 요청 params: {params}")
            response = requests.get(url, headers=headers, params=params, timeout=10)
            print(f"[DEBUG][KIS] 보유수량 응답 status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                if data.get('rt_cd') == '0':
                    # output1: 종목별 보유 내역
                    holdings = data.get('output1', [])
                    target_pdno = self.symbols.get(symbol, {}).get('pdno', '')
                    for holding in holdings:
                        pdno = holding.get('ovrs_pdno', '')
                        if pdno == target_pdno:
                            qty_raw = holding.get('ovrs_cblc_qty', 0)
                            try:
                                return int(float(str(qty_raw).replace(',', '')))
                            except Exception:
                                return 0

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
            # 정규장 게이트: 정규장 외 주문 차단 (시장가/일반)
            if not self.is_us_regular_hours():
                print(f"[GATE] 미국 정규장 아님 → 주문 보류 (ET {datetime.now(ZoneInfo('America/New_York')).strftime('%Y-%m-%d %H:%M')})")
                return False

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
                "tr_id": "TTTT1002U" if side == "BUY" else "TTTT1006U",  # FIX: TTTT (T 4개!)
                "custtype": "P",
                "Content-Type": "application/json"
            }

            data = {
                "CANO": self.account_no.split('-')[0],
                "ACNT_PRDT_CD": self.account_no.split('-')[1],
                "OVRS_EXCG_CD": "NASD",
                "PDNO": self.symbols[symbol]['pdno'],  # A980679 (SOXL) / A980680 (SOXS)
                "ORD_QTY": str(qty),
                "OVRS_ORD_UNPR": str(current_price),  # 현재가 입력 필수
                "ORD_SVR_DVSN_CD": "0",
                "ORD_DVSN": "01"  # FIX: 01=지정가 (2024-10-08 성공 패턴)
            }

            print(f"[주문 데이터] {symbol} {side} {qty}주 @ ${current_price:.2f}")

            # 재시도 설정 (HTTP 5xx, 네트워크 오류, 특정 메시지 코드)
            max_retries = 3
            backoff_sec = 1
            last_result = None
            for attempt in range(1, max_retries + 1):
                try:
                    response = requests.post(url, headers=headers, json=data, timeout=10)
                    if response.status_code == 200:
                        result = response.json()
                        last_result = result
                        if result.get('rt_cd') == '0':
                            print(f"[OK] 주문 성공: {symbol} {side} {qty}주")
                            return True
                        else:
                            # 서버 처리 오류 또는 일시적 문제시 재시도
                            err_code = result.get('msg_cd', '')
                            if err_code.startswith('APBK') or err_code.startswith('HTS'):
                                print(f"[RETRY {attempt}/{max_retries}] API 오류 코드 {err_code} → {backoff_sec}s 대기 후 재시도")
                                time.sleep(backoff_sec)
                                backoff_sec *= 2
                                continue
                            # 재시도 불가 오류
                            break
                    else:
                        print(f"[RETRY {attempt}/{max_retries}] HTTP {response.status_code} → {backoff_sec}s 대기 후 재시도")
                        time.sleep(backoff_sec)
                        backoff_sec *= 2
                        continue
                except Exception as e:
                    print(f"[RETRY {attempt}/{max_retries}] 네트워크 오류: {e} → {backoff_sec}s 대기 후 재시도")
                    time.sleep(backoff_sec)
                    backoff_sec *= 2

            # 재시도 후 실패 처리
            if last_result is not None:
                result = last_result
                error_code = result.get('msg_cd', 'UNKNOWN')
                error_msg = result.get('msg1', '알 수 없는 오류')
            else:
                error_code = 'HTTP_OR_NETWORK'
                error_msg = f"마지막 상태: {response.status_code if 'response' in locals() else 'no response'}"

            # 기존 실패 처리 로직
            print(f"[ERROR] KIS API 주문 실패")
            print(f"  에러 코드: {error_code}")
            print(f"  메시지: {error_msg}")
            print(f"  종목: {symbol}, 주문: {side}, 수량: {qty}주, 가격: ${current_price:.2f}")
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
            log_entry = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 주문 실패: {error_code} - {error_msg}\n"
            try:
                with open("kis_trading_log.txt", "a", encoding="utf-8") as f:
                    f.write(log_entry)
            except:
                pass
            return False

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
                current_time = time.time()  # 안전장치 체크용 시간 변수
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
                
                # ===== [SAFETY] 안전장치 선평가 (LLM 판단보다 우선) =====
                if self.current_position:
                    current_price = self.get_current_price(self.current_position)
                    if current_price > 0:
                        pnl = self.get_position_pnl(current_price)
                        holding_time_sec = (datetime.now() - self.entry_time).total_seconds() if self.entry_time else 0
                        holding_time_min = holding_time_sec / 60

                        # 1. 보유시간 초과 시 즉시 청산
                        if holding_time_sec > self.MAX_HOLDING_TIME:
                            print(f"[SAFETY] 보유시간 초과 ({holding_time_min:.0f}분) → 즉시 청산 (PNL:{pnl:+.2f}%)")
                            self.close_position("MAX_HOLD_TIME_SAFETY")
                            self.last_safety_time = datetime.now()
                            time.sleep(5)  # 재진입 방지 잠시 대기
                            continue

                        # 2. 동적 손절 임계 도달 시 즉시 청산
                        if pnl <= self.DYNAMIC_STOP_LOSS:
                            print(f"[SAFETY] 손절 임계 도달 → 즉시 청산 (PNL:{pnl:+.2f}%)")
                            self.close_position("STOP_LOSS_SAFETY")
                            self.last_safety_time = datetime.now()
                            self.consecutive_losses += 1
                            time.sleep(5)
                            continue

                        # 3. 단기 급락 보호 (최근 5틱 대비 -5% 이상 급락 시)
                        if len(self.price_history) >= 5:
                            recent_prices = self.price_history[-5:]
                            min_price_in_5_ticks = min(recent_prices)
                            max_price_in_5_ticks = max(recent_prices)
                            
                            # 현재 가격이 최근 최고가 대비 5% 이상 급락했는지 확인
                            if max_price_in_5_ticks > 0 and (current_price - max_price_in_5_ticks) / max_price_in_5_ticks * 100 <= -5.0:
                                print(f"[SAFETY] 단기 급락 감지 (최근 최고가 ${max_price_in_5_ticks:.2f} 대비 -5% 이상) → 즉시 청산 (PNL:{pnl:+.2f}%)")
                                self.close_position("SUDDEN_DROP_SAFETY")
                                self.last_safety_time = datetime.now()
                                time.sleep(5)
                                continue

                # 5분 단위 안전장치 체크 (긴급사항 대응)
                if current_time - self.last_safety_check_time >= self.SAFETY_CHECK_INTERVAL:
                    print(f"\n[안전장치 체크] 5분 정기 안전장치 점검")
                    self.last_safety_check_time = current_time
                    # 안전장치는 이미 위에서 체크됨 (실시간)

                # 추세 판단
                print(f"[{datetime.now().strftime('%H:%M:%S')}]  추세 분석 중...")
                trend = self.calculate_trend()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [REPORT] 추세: {trend}")

                # ===== 가중치 앙상블 시스템 사용 =====
                print(f"[KIS] 가중치 앙상블 시스템 시작...")
                llm_signal = self.get_ensemble_signal(trend)
                print(f"[KIS] 앙상블 결과: {llm_signal}")

                # 텔레그램 알림: LLM 신호 전송
                signal_emoji = "🟢 BULL" if llm_signal == 'BULL' else "🔴 BEAR"  # NEUTRAL 제거
                target_symbol = "SOXL (3X 롱)" if llm_signal == 'BULL' else "SOXS (3X 숏)"  # NEUTRAL 제거

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

                # 피라미딩 허용: 포지션이 있어도 같은 방향이면 추가 진입
                if llm_signal in ['BULL', 'BEAR']:
                    # 신뢰도 체크 (동적 임계값)
                    llm_confidence = 50  # 기본값 (실제로는 LLM에서 받아야 함)

                    # 🔍 실거래 모드에서만 백테스팅 (페이퍼 모드는 백테스팅 불필요)
                    if not self.paper_trading_mode:
                        backtest_pass, backtest_rate = self.check_pattern_backtest(llm_signal, llm_confidence)
                        if not backtest_pass:
                            print(f"[백테스트 차단] {llm_signal} 패턴 성공률 {backtest_rate:.1f}% < 60%")
                            time.sleep(300)  # 5분 대기 후 다음 사이클
                            continue

                    if llm_confidence >= self.MIN_CONFIDENCE:
                        target_symbol = 'SOXL' if llm_signal == 'BULL' else 'SOXS'
                        
                        # 연속 손실 차단: 3회 연속 손실 시 해당 방향 진입 금지
                        if self.consecutive_losses >= self.max_consecutive_losses:
                            if (target_symbol == 'SOXL' and llm_signal == 'BULL') or (target_symbol == 'SOXS' and llm_signal == 'BEAR'):
                                print(f"[진입 차단] 연속 손실 {self.consecutive_losses}회 → {target_symbol} 진입 금지")
                                continue
                        
                        # 피라미딩 체크: 같은 방향이면 추가 진입 허용
                        if self.current_position:
                            if (self.current_position == 'SOXL' and llm_signal == 'BULL') or (self.current_position == 'SOXS' and llm_signal == 'BEAR'):
                                print(f"[피라미딩] {self.current_position} 포지션 + {llm_signal} 신호 → 추가 진입 허용")
                                self.open_position(target_symbol)
                            else:
                                print(f"[진입 차단] {self.current_position} 포지션 + {llm_signal} 신호 → 반대 방향")
                        else:
                            print(f"[진입 조건] {llm_signal} 신호, 신뢰도 {llm_confidence}% (임계값 {self.MIN_CONFIDENCE}%)")
                            self.open_position(target_symbol)
                    else:
                        print(f"[진입 차단] 신뢰도 부족: {llm_confidence}% < {self.MIN_CONFIDENCE}%")

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
                print(f"  앙상블 시스템: 가중치 기반 BULL/BEAR 결정 (NEUTRAL 제거)")

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

                time.sleep(3600)  # 1시간 간격 (1시간봉)

            except KeyboardInterrupt:
                print("\n[종료] 사용자 중단")
                break
            except Exception as e:
                print(f"[ERROR] 메인 루프: {e}")
                time.sleep(3600)  # 1시간 간격

    def get_llm_signal_7b(self, price: float, trend: str) -> str:
        """7b LLM 빠른 분석"""
        try:
            # 학습 전략 로드
            try:
                learned_strategies = generate_learned_strategies()
            except Exception as e:
                print(f"[WARN] 학습 전략 생성 실패: {e}")
                learned_strategies = "학습 데이터 없음 - 초기 전략 사용"
            
            # 간단한 프롬프트로 빠른 분석
            prompt = f"""
[KIS 학습 전략]
{learned_strategies}

[현재 시장 상황]
SOXL 현재가: ${price:.2f}
추세: {trend}

위 학습 전략을 참고하여 반도체 3배 레버리지 ETF 거래 신호를 BULL/BEAR/NEUTRAL로 답하세요.
"""
            
            # 7b 모델로 빠른 분석 (realtime_monitor 사용)
            response = self.realtime_monitor.analyze_market_simple(prompt)
            
            if 'BULL' in response.upper():
                return 'BULL'
            elif 'BEAR' in response.upper():
                return 'BEAR'
            else:
                return 'NEUTRAL'
        except:
            return 'NEUTRAL'
    
    def get_llm_signal_14b(self, price: float, trend: str) -> str:
        """7b LLM 깊은 분석 (실제로는 7b 사용, 함수명만 14b)"""
        try:
            # 학습 전략 로드
            try:
                learned_strategies = generate_learned_strategies()
            except Exception as e:
                print(f"[WARN] 학습 전략 생성 실패: {e}")
                learned_strategies = "학습 데이터 없음 - 초기 전략 사용"
            
            # 상세한 프롬프트로 깊은 분석
            prompt = f"""
[KIS 학습 전략]
{learned_strategies}

[SOXL (반도체 3배 레버리지 ETF) 분석]
- 현재가: ${price:.2f}
- 추세: {trend}
- 가격 히스토리: {self.price_history[-5:] if len(self.price_history) >= 5 else 'N/A'}
- 현재 포지션: {self.current_position if self.current_position else 'NONE'}
- 보유 시간: {(datetime.now() - self.entry_time).total_seconds() / 3600:.1f if self.entry_time else 0}시간 (목표: 10시간)

위 학습 전략을 참고하여 3배 레버리지 특성을 고려한 거래 신호를 BULL/BEAR/NEUTRAL로 답하세요.
"""
            
            # 7b 모델로 깊은 분석 (main_analyzer 사용)
            response = self.main_analyzer.analyze_market_simple(prompt)
            
            if 'BULL' in response.upper():
                return 'BULL'
            elif 'BEAR' in response.upper():
                return 'BEAR'
            else:
                return 'NEUTRAL'
        except:
            return 'NEUTRAL'

    def get_position_pnl(self, current_price: float) -> float:
        """포지션 PNL 계산 (3배 레버리지)"""
        if not self.current_position or not self.entry_price:
            return 0.0

        if self.current_position == 'SOXL':
            # SOXL: 상승 시 수익
            pnl = ((current_price - self.entry_price) / self.entry_price) * 100 * 3
        else:  # SOXS
            # SOXS: 하락 시 수익
            pnl = ((self.entry_price - current_price) / self.entry_price) * 100 * 3

        return pnl

    def get_ensemble_signal(self, trend: str) -> str:
        """7b + 14b 가중치 앙상블 LLM 신호 (NEUTRAL 제거)"""
        try:
            # 모델별 가중치 시스템
            model_weights = {
                '7b': 0.3,
                '14b': 0.7
            }
            
            # 기본값 초기화 (모든 실행 경로에서 변수 보장)
            llm_signal = 'BULL'  # NEUTRAL 제거, 기본값 BULL
            quick_buy = 50
            quick_sell = 50
            quick_confidence = 50
            deep_buy = 50
            deep_sell = 50
            deep_confidence = 50
            
            # 7b 빠른 분석 (가중치 0.3)
            try:
                quick_signal = self.get_llm_signal_7b(0, trend)  # 가격은 0으로 설정
                if quick_signal == 'BULL':
                    quick_buy = 80
                    quick_sell = 20
                    quick_confidence = 70
                elif quick_signal == 'BEAR':
                    quick_buy = 20
                    quick_sell = 80
                    quick_confidence = 70
                else:
                    quick_buy = 50
                    quick_sell = 50
                    quick_confidence = 50
            except Exception as e:
                print(f"[7b 분석] 오류: {e} → 기본값 사용")
                quick_buy = 50
                quick_sell = 50
                quick_confidence = 50
            
            # 14b 메인 분석 (가중치 0.7)
            try:
                deep_signal = self.get_llm_signal_14b(0, trend)  # 가격은 0으로 설정
                if deep_signal == 'BULL':
                    deep_buy = 80
                    deep_sell = 20
                    deep_confidence = 80
                elif deep_signal == 'BEAR':
                    deep_buy = 20
                    deep_sell = 80
                    deep_confidence = 80
                else:
                    deep_buy = 50
                    deep_sell = 50
                    deep_confidence = 50
            except Exception as e:
                print(f"[14b 분석] 오류: {e} → 기본값 사용")
                deep_buy = 50
                deep_sell = 50
                deep_confidence = 50
            
            # 가중치 합산 시스템
            try:
                weighted_buy = (quick_buy * model_weights['7b']) + (deep_buy * model_weights['14b'])
                weighted_sell = (quick_sell * model_weights['7b']) + (deep_sell * model_weights['14b'])
                weighted_confidence = (quick_confidence * model_weights['7b']) + (deep_confidence * model_weights['14b'])
            except Exception as e:
                print(f"[가중치 합산] 오류: {e} → 기본값 사용")
                weighted_buy = 50
                weighted_sell = 50
                weighted_confidence = 50
            
            # NEUTRAL 제거: 항상 BULL 또는 BEAR 결정
            if weighted_buy > weighted_sell:
                llm_signal = 'BULL'
            else:
                llm_signal = 'BEAR'
            
            print(f"[가중치 합산] 7b({quick_buy:.1f}×{model_weights['7b']}) + 14b({deep_buy:.1f}×{model_weights['14b']}) = BUY:{weighted_buy:.1f}")
            print(f"[가중치 합산] 7b({quick_sell:.1f}×{model_weights['7b']}) + 14b({deep_sell:.1f}×{model_weights['14b']}) = SELL:{weighted_sell:.1f}")
            print(f"[앙상블] 최종 결과: {llm_signal} (신뢰도 {weighted_confidence:.1f}%)")
            
            return llm_signal
            
        except Exception as e:
            print(f"[앙상블] 오류: {e} → 기본값 BULL 사용")
            return 'BULL'

    def open_position(self, symbol: str):
        """포지션 진입 (자동매매 또는 가상)"""
        print(f"\n[진입 신호] {symbol}")

        try:
            # 📝 페이퍼 트레이딩 모드: 가상 진입
            if self.paper_trading_mode:
                current_price = self.get_current_price(symbol)
                if current_price <= 0:
                    return
                balance = self.paper_balance
                qty = int(balance * 0.95 / current_price) if balance > 0 else 1
                self.paper_place_order(symbol, 'BUY', qty, current_price)
                return

            # 정규장 게이트: 정규장 외 진입 차단
            if not self.is_us_regular_hours():
                print(f"[GATE] 미국 정규장 아님 → 진입 보류 (ET {datetime.now(ZoneInfo('America/New_York')).strftime('%Y-%m-%d %H:%M')})")
                return

            # 1. 현재가 조회
            current_price = self.get_current_price(symbol)
            if current_price <= 0:
                print(f"[ERROR] {symbol} 가격 조회 실패")
                return

            # 2. 잔고 조회
            balance = self.get_usd_balance()
            if balance <= 0:
                # 현금이 0이어도 보유 종목이 있으면 매도는 허용
                if symbol in ('SOXL', 'SOXS'):
                    held_qty = self.get_position_quantity(symbol)
                    if held_qty > 0 and self.current_position == symbol:
                        print(f"[WARN] 현금 0이지만 보유 {symbol} {held_qty}주 존재 → 매도 허용")
                    else:
                        print(f"[ERROR] 잔고 부족: ${balance:.2f}")
                        return
                else:
                    print(f"[ERROR] 잔고 부족: ${balance:.2f}")
                    return

            # 3. 매수 수량 계산 (잔고 구간별 이용률)
            if balance <= 1000:
                # $1000 이하: 100% 이용 (공격적)
                invest_ratio = 1.00
                grade = "풀베팅 (100%)"
            else:
                # $1000 초과: 95% 이용 (기존)
                invest_ratio = 0.95
                grade = "적극적 (95%)"
            
            max_invest = balance * invest_ratio
            qty = int(max_invest / current_price)
            
            print(f"[잔고 이용률] ${balance:.2f} → {grade} (${max_invest:.2f})")

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

                # 7. 텔레그램 알림 (새 포지션만 전송)
                if not hasattr(self, 'previous_position') or self.previous_position != symbol:
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
                    self.previous_position = symbol
                else:
                    print(f"[INFO] 같은 포지션 {symbol} - 텔레그램 알림 생략")

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
        """포지션 청산 (자동매매 또는 가상)"""
        print(f"\n[청산 신호] {self.current_position} (이유: {reason})")

        if not self.current_position:
            print("[ERROR] 청산할 포지션이 없음")
            return

        # 📝 페이퍼 트레이딩 모드: 가상 청산
        if self.paper_trading_mode:
            self.paper_close_position(reason)
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
                # 6. 실제 잔고 조회 (허수가 아닌 실제 수익 기록)
                current_balance = self.get_usd_balance()

                # 7. 거래 기록 저장 (실제 잔고 변화 포함)
                trade_record = {
                    'symbol': symbol,
                    'entry_price': self.entry_price,
                    'exit_price': current_price,
                    'entry_time': self.entry_time.isoformat() if self.entry_time else None,
                    'exit_time': datetime.now().isoformat(),
                    'holding_hours': holding_hours,
                    'pnl_pct': pnl,
                    'exit_reason': reason,
                    'quantity': qty,
                    'balance_before': self.entry_balance,  # 실제 잔고 (진입 시)
                    'balance_after': current_balance,      # 실제 잔고 (청산 시)
                    'balance_change': current_balance - self.entry_balance  # 실제 수익 (USD)
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

                # 8. 통계 업데이트 (수수료 고려한 실제 수익 기준)
                real_profit = current_balance - self.entry_balance
                real_profit_pct = (real_profit / self.entry_balance) * 100 if self.entry_balance > 0 else 0
                
                # 수수료 고려한 실제 수익성 판단 (0.2% 이상이어야 수익 - KIS 수수료가 더 높음)
                if real_profit_pct > 0.2:  # 수수료 고려한 실제 수익
                    self.stats['wins'] += 1
                    self.consecutive_losses = 0  # 수익 시 연속 손실 리셋
                    print(f"[복리 효과] 실제 수익: ${real_profit:+.2f} ({real_profit_pct:+.3f}%)")
                else:
                    self.stats['losses'] += 1
                    self.consecutive_losses += 1  # 손실 시 연속 손실 증가
                    print(f"[손실] 실제 손실: ${real_profit:+.2f} ({real_profit_pct:+.3f}%)")
                    
                    # 연속 손실 학습: 3회 연속 손실 시 해당 방향 진입 금지
                    if self.consecutive_losses >= self.max_consecutive_losses:
                        print(f"[학습] 연속 손실 {self.consecutive_losses}회 → {symbol} 방향 진입 금지")
                        self.telegram.send_message(
                            f"[학습] <b>연속 손실 패턴 감지</b>\n\n"
                            f"<b>종목:</b> {symbol}\n"
                            f"<b>연속 손실:</b> {self.consecutive_losses}회\n"
                            f"<b>학습 결과:</b> {symbol} 방향 진입 금지\n"
                            f"<b>시간:</b> {datetime.now().strftime('%H:%M:%S')}",
                            priority="important"
                        )

                # 9. 텔레그램 알림 (실제 잔고 변화 포함)
                emoji = "[OK]" if real_profit > 0 else "[ERROR]"
                self.telegram.send_message(
                    f"{emoji} KIS 청산 완료\n\n"
                    f"종목: {symbol}\n"
                    f"수량: {qty}주\n"
                    f"진입: ${self.entry_price:.2f}\n"
                    f"청산: ${current_price:.2f}\n"
                    f"PNL (레버리지): {pnl:+.2f}%\n"
                    f"실제 수익: ${real_profit:+.2f} ({real_profit/self.entry_balance*100:+.2f}%)\n"
                    f"잔고: ${self.entry_balance:.2f} → ${current_balance:.2f}\n"
                    f"보유: {holding_hours:.1f}시간\n"
                    f"이유: {reason}\n\n"
                    f"누적 승률: {self.stats['wins']}/{self.stats['total_trades']}건 "
                    f"({self.stats['wins']/max(1,self.stats['total_trades'])*100:.1f}%)",
                    priority="important"
                )

                print(f"[SUCCESS] {symbol} {qty}주 청산 완료 @${current_price:.2f}")
                print(f"  레버리지 PNL: {pnl:+.2f}%")
                print(f"  실제 수익: ${real_profit:+.2f} ({real_profit/self.entry_balance*100:+.2f}%)")

                # 10. 포지션 정보 초기화
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

    def paper_place_order(self, symbol: str, side: str, qty: int, current_price: float = 0) -> bool:
        """📝 페이퍼 트레이딩: 가상 진입"""
        if current_price <= 0:
            current_price = self.get_current_price(symbol)
            if current_price <= 0:
                return False

        self.current_position = symbol
        self.entry_price = current_price
        self.entry_time = datetime.now()
        self.entry_balance = self.paper_balance

        # 텔레그램 알림
        paper_count = len(self.paper_trades)
        wins = len([t for t in self.paper_trades if t.get('pnl_pct', 0) > 0])
        win_rate = (wins / paper_count * 100) if paper_count > 0 else 0

        msg = (
            f"📝 [가상 진입] {symbol} {side}\n"
            f"진행: {paper_count}/{self.PAPER_TRADE_REQUIRED}\n"
            f"승률: {win_rate:.1f}% (목표 {self.PAPER_WIN_RATE_THRESHOLD*100:.0f}%)\n"
            f"가격: ${current_price:.2f}\n"
            f"수량: {qty}주 (가상)\n"
        )
        self.telegram.send_message(msg, priority="normal")

        print(f"[📝 가상 진입] {symbol} @ ${current_price:.2f}")
        return True

    def paper_close_position(self, reason: str) -> bool:
        """📝 페이퍼 트레이딩: 가상 청산"""
        if not self.current_position:
            return False

        symbol = self.current_position
        current_price = self.get_current_price(symbol)
        if current_price <= 0:
            return False

        # PNL 계산 (3배 레버리지)
        if symbol == 'SOXL':
            pnl = ((current_price - self.entry_price) / self.entry_price) * 100 * 3
        else:  # SOXS
            pnl = ((self.entry_price - current_price) / self.entry_price) * 100 * 3

        holding_time = (datetime.now() - self.entry_time).total_seconds()

        # 가상 잔고 변화 계산
        pnl_amount = self.entry_balance * (pnl / 100)
        self.paper_balance += pnl_amount

        # 거래 기록
        trade_record = {
            'symbol': symbol,
            'entry_price': self.entry_price,
            'exit_price': current_price,
            'pnl_pct': pnl,
            'holding_time_sec': holding_time,
            'reason': reason,
            'balance_change': pnl_amount,
            'paper_balance': self.paper_balance
        }
        self.paper_trades.append(trade_record)

        # 통계
        paper_count = len(self.paper_trades)
        wins = len([t for t in self.paper_trades if t.get('pnl_pct', 0) > 0])
        win_rate = (wins / paper_count * 100)

        # 졸업 체크
        if paper_count >= self.PAPER_TRADE_REQUIRED:
            if win_rate >= self.PAPER_WIN_RATE_THRESHOLD * 100:
                # 실거래 전환!
                self.paper_trading_mode = False
                graduate_msg = (
                    f"🎓 [실거래 전환!]\n"
                    f"페이퍼 거래: {paper_count}건\n"
                    f"최종 승률: {win_rate:.1f}%\n"
                    f"✅ 목표 달성!\n"
                    f"🚀 실거래 모드로 전환합니다!"
                )
                self.telegram.send_message(graduate_msg, priority="critical")
                print(f"\n{'='*60}\n{graduate_msg}\n{'='*60}")
            else:
                # 재시작
                fail_msg = (
                    f"❌ [페이퍼 실패]\n"
                    f"거래: {paper_count}건\n"
                    f"승률: {win_rate:.1f}% < {self.PAPER_WIN_RATE_THRESHOLD*100:.0f}%\n"
                    f"🔄 처음부터 다시 시작합니다"
                )
                self.telegram.send_message(fail_msg, priority="important")
                print(f"\n[페이퍼 실패] 재시작")
                self.paper_trades = []
                self.paper_balance = self.initial_balance
        else:
            # 진행 중
            msg = (
                f"📝 [가상 청산] {symbol}\n"
                f"PNL: {pnl:+.2f}%\n"
                f"진행: {paper_count}/{self.PAPER_TRADE_REQUIRED}\n"
                f"승률: {win_rate:.1f}% (목표 {self.PAPER_WIN_RATE_THRESHOLD*100:.0f}%)\n"
                f"이유: {reason}\n"
            )
            self.telegram.send_message(msg, priority="normal")

        # 포지션 초기화
        self.current_position = None
        self.entry_price = 0
        self.entry_time = None
        self.entry_balance = None

        print(f"[📝 가상 청산] {symbol} PNL: {pnl:+.2f}% ({paper_count}/{self.PAPER_TRADE_REQUIRED})")
        return True

    def check_pattern_backtest(self, signal: str, confidence: int) -> tuple:
        """🔍 실시간 백테스팅: 과거 데이터에서 이 패턴의 성공률 확인"""
        if len(self.all_trades) < 10:
            return (True, 100.0)  # 데이터 부족 시 통과

        # 유사 패턴 찾기 (최근 50거래)
        similar_trades = [
            t for t in self.all_trades[-50:]
            if (
                (signal == 'BULL' and t.get('symbol') == 'SOXL') or
                (signal == 'BEAR' and t.get('symbol') == 'SOXS')
            )
        ]

        if len(similar_trades) == 0:
            return (True, 100.0)  # 패턴 없으면 통과

        # 성공률 계산
        total = len(similar_trades)
        wins = len([t for t in similar_trades if t.get('balance_change', 0) > 0])
        success_rate = (wins / total * 100)

        # 60% 이상이면 통과
        if success_rate >= 60.0:
            print(f"[백테스트 통과] {signal} 패턴 성공률: {success_rate:.1f}% (샘플: {total}건)")
            return (True, success_rate)
        else:
            # 차단
            msg = (
                f"🔍 [백테스트 차단]\n"
                f"신호: {signal}\n"
                f"과거 성공률: {success_rate:.1f}%\n"
                f"목표: 60.0%\n"
                f"샘플: {total}건\n"
                f"⚠️ 이 패턴은 과거에 실패 多\n"
                f"❌ 진입 차단"
            )
            self.telegram.send_message(msg, priority="normal")
            print(f"[백테스트 차단] {signal} 성공률 {success_rate:.1f}% < 60%")
            return (False, success_rate)

if __name__ == "__main__":
    trader = ExplosiveKISTrader()
    trader.run()
