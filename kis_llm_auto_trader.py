#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 [매우 중요] 코드 수정 후 반드시 봇 재시작 필요!
================================================================================
- Python은 시작 시 코드를 메모리에 로드합니다
- 파일을 수정해도 실행 중인 봇은 이전 코드를 사용합니다
- 새 코드 적용하려면 반드시 봇을 중지하고 재시작해야 합니다!

 [즉시 알림 규칙] - 적극적으로 알려주세요!
================================================================================
다음 사항을 발견하면 사용자에게 즉시 알립니다:

1. 버그 및 오류:
   - 코드 오류, SyntaxError, 로직 버그
   - 거래 실패, API 오류
   - 데이터 누락, 계산 오류

2. 성능 저하 및 비효율:
   - 메모리 누수, CPU 과부하
   - LLM 응답 지연, 타임아웃 증가
   - 불필요한 연산, 중복 코드

3. 거래 시스템 문제:
   - 잔고 감소, 예상치 못한 손실
   - 포지션 동기화 실패
   - 손익 계산 오류

4. 개선 가능한 사항:
   - LLM 판단을 방해하는 하드코딩 조건
   - 불필요하거나 방해되는 기능
   - 더 나은 구현 방법

 중요: 수동적으로 기다리지 말 것!
- 사용자가 물어보기 전에 먼저 발견하고 알릴 것
- 한 가지 문제를 수정할 때, 관련된 다른 문제도 함께 확인할 것
  예: SOXS 거래소 코드 수정 → SOXL도 즉시 확인
- "혹시 이것도?"라고 물어보지 말고, 확인 후 바로 알릴 것

이런 것들을 발견하면 즉시 보고합니다!
================================================================================

한국투자증권 LLM 기반 자동매매 시스템
- 14b × 2 병렬 LLM 분석 (코드3 ETH Trader 로직)
- 추세돌파 학습 및 판단
- 거래 히스토리 Few-shot Learning
- 손실 최소화 자동 학습

[핵심 철학]
간단한 이동평균으로는 복잡한 주식시장을 이길 수 없다!
14b × 2 병렬 LLM이 추세돌파를 학습하고 판단해야 한다.
- 추세돌파로 수익
- 방향 바뀌면 포지션 전환하여 또 수익
- 반복하여 잔고 증가
- LLM이 똑똑하게 손실 최소화 학습

================================================================================
[매우 중요!!!] 핵심 전략 - 절대 변경 금지!
================================================================================

1. 익절 전략: 고정 익절 없음!
   - LLM이 "방향 전환 징후"를 감지할 때만 포지션 전환
   - 추세가 계속되면 계속 보유 (10%, 20% 수익도 가능)
   - 목표: 큰 추세를 끝까지 타기

2. LLM의 핵심 역할: "손실 전에 미리 방향 전환 감지"
   - 단순히 "지금 상승/하락"이 아님
   - "추세가 곧 꺾일 징후"를 선제적으로 포착 ← 이게 핵심!
   - 거래 히스토리로 학습하며 최적 타이밍 개선

   예시:
   SOXL 보유 (+10%)
   → LLM이 "상승 모멘텀 약화, 반전 징후" 감지
   → +10%에서 익절하고 SOXS 전환
   → SOXS +8% 수익
   → LLM이 다시 "하락 마무리, 상승 재개" 감지
   → +8%에서 익절하고 SOXL 전환
   → 반복하며 잔고 증가

3. 포지션 전환 조건:
   - LLM 신호가 BULL → BEAR 또는 BEAR → BULL 전환 시
   - 현재 수익/손실 무관 (LLM이 판단)
   - 신뢰도 70% 이상

4. 손절: -0.5% (급락 방어용)
   - 유일한 고정 손절선
   - LLM도 못 잡은 급락 방어

5. 학습:
   - 모든 거래 기록 저장 (Few-shot Learning)
   - 성공한 전환: +8% → 전환 → +7% (패턴 학습)
   - 실패한 전환: +3% → 전환 → -2% (패턴 회피)
   - LLM이 이 패턴을 학습해서 점점 똑똑해짐

6. 왜 14b × 2 병렬 앙상블을 쓰는가?
   - 작은 모델로는 미묘한 방향 전환 징후를 못 잡음
   - 14b × 2 = 높은 지능으로 조기 감지
   - 손실 전에 미리 전환 → 수익 극대화

================================================================================
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import sys
import io

# Windows 콘솔 한글 출력 강제 설정
if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if hasattr(sys.stderr, 'buffer') and not isinstance(sys.stderr, io.TextIOWrapper):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

"""
================================================================================
[중요] 한국투자증권 KIS API 해외주식 주문 스펙 정리
================================================================================

출처:
1. kis_auto_trader_final.py (동작 확인됨)
2. 해외주식 주문[v1_해외주식-001].xlsx
3. GitHub: https://github.com/koreainvestment/open-trading-api

================================================================================
1. TR_ID (실전투자)
================================================================================
매수: TTTT1002U
매도: TTTT1006U

모의투자: VTTT1002U / VTTT1001U (사용 안 함)

[중요] J로 시작 = 조회 API, T로 시작 = 거래 API
- JTTT = 조회용 (잔고, 매수가능금액)
- TTTT = 주문용 (매수, 매도)

================================================================================
2. 거래소 코드 (OVRS_EXCG_CD)
================================================================================
주문 시: "NASD"
- SOXL, SOXS는 실제로는 NYSE American(AMEX)에 상장
- 하지만 KIS API 주문 시에는 "NASD" 사용

매수가능금액 조회 시: "AMEX"
- get_usd_cash_balance() 함수에서만 "AMEX" 사용

================================================================================
3. 주문 가격 (OVRS_ORD_UNPR)
================================================================================
 [중요] 시장가도 현재가 입력 필수! 

시장가: 현재가 입력 (예: "40.17") + ORD_DVSN = "00"
지정가: 지정가 입력 (예: "45.50") + ORD_DVSN = "01"

 주의: 문서에는 "0"이라고 되어 있지만, 실제로는 현재가 필요!
- "0"을 보내면 "$0.01 미만" 오류 발생
- 시장가 주문이지만 현재가를 입력해야 함
- ORD_DVSN = "00"으로 시장가 구분

시장가 예시 (ChatGPT/한국투자 챗봇 확인):
{
  "OVRS_ORD_UNPR": "40.17", //  시장가도 현재가 입력!
  "ORD_DVSN": "00"          // 00 = 시장가
}

지정가 예시:
{
  "OVRS_ORD_UNPR": "45.50", // 지정가격 입력
  "ORD_DVSN": "01"          // 01 = 지정가
}

================================================================================
4. 주문 구분 (ORD_DVSN)
================================================================================
 시장가: "00" 
 지정가: "01" 

================================================================================
5. 필수 필드
================================================================================
order_data = {
    "CANO": "계좌번호",
    "ACNT_PRDT_CD": "01",
    "OVRS_EXCG_CD": "NASD",  # 주문 시 NASD 고정
    "PDNO": "SOXL",
    "ORD_QTY": "10",
    "OVRS_ORD_UNPR": "0",    # 시장가는 "0"
    "ORD_SVR_DVSN_CD": "0",
    "ORD_DVSN": "00"         # 시장가는 "00"
}

hashkey = get_hashkey(order_data)  # 반드시 필요

headers = {
    "authorization": f"Bearer {access_token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": "JTTT1002U",    # 매수: JTTT1002U, 매도: JTTT1006U
    "custtype": "P",
    "hashkey": hashkey
}

================================================================================
"""

import yaml
import json
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# LLM 분석기 (코드3에서 복사)
from llm_market_analyzer import LLMMarketAnalyzer
from ensemble_llm_analyzer import EnsembleLLMAnalyzer

# 텔레그램 및 Ollama 헬퍼
# from telegram_helpers import TelegramNotifier, start_ollama  # 자동매매 전용 - 텔레그램 비활성화

# FMP API 설정
FMP_API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"
FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"


class KISLLMTrader:
    """
    한국투자증권 LLM 기반 자동매매 시스템

    코드3 ETH Trader 핵심 로직 적용:
    1. 14b × 2 병렬 LLM 앙상블
    2. 추세돌파 학습 및 판단
    3. 거래 히스토리 Few-shot Learning
    4. 손실 최소화 자동 학습
    """

    def __init__(self, config_path: str = None):
        """초기화"""
        print("="*80)
        print("한국투자증권 LLM 기반 자동매매 시스템 v2.0")
        print("14b × 2 병렬 LLM 앙상블 (코드3 ETH Trader 로직)")
        print("="*80)

        # 설정 파일 경로 설정
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), 'kis_devlp.yaml')

        print(f"[설정] 파일 경로: {config_path}")

        # 설정 로드
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            print(f"[ERROR] 설정 파일 로드 실패: {e}")
            raise

        # 설정 검증
        required_keys = ['my_app', 'my_sec', 'my_acct']
        missing_keys = [key for key in required_keys if key not in self.config]
        if missing_keys:
            print(f"[ERROR] 설정 파일에 필수 키가 없습니다: {missing_keys}")
            print(f"현재 설정 키: {list(self.config.keys())}")
            raise KeyError(f"Missing keys: {missing_keys}")

        # 토큰 로드
        token_file = os.path.join(os.path.dirname(__file__), 'kis_token.json')
        try:
            with open(token_file, 'r') as f:
                token_data = json.load(f)
                self.access_token = token_data['access_token']
        except Exception as e:
            print(f"[ERROR] 토큰 파일 로드 실패 ({token_file}): {e}")
            raise

        # 계좌번호
        acct_parts = self.config['my_acct'].split('-')
        self.cano = acct_parts[0]
        self.acnt_prdt_cd = acct_parts[1] if len(acct_parts) > 1 else "01"

        # API URL
        self.base_url = "https://openapi.koreainvestment.com:9443"

        # 거래 설정
        self.exchange_cd = "NASD"  # 기본 거래소 코드
        self.exchange_cd_query = "AMEX"  # 매수가능금액 조회 시 사용

        #  종목별 PDNO 매핑 (KIS API 실전 종목코드) 
        self.symbol_pdno_map = {
            "TQQQ": "A206892",  # ProShares UltraPro QQQ
            "SQQQ": "A206893",  # ProShares UltraPro Short QQQ
            "SOXL": "A980679",  # Direxion Daily Semiconductor Bull 3X
            "SOXS": "A980680"   # Direxion Daily Semiconductor Bear 3X
        }

        #  PDNO → Symbol 역변환 맵 (포지션 조회용) 
        # KIS API가 "SOXL" 또는 "A980679" 둘 다 반환할 수 있으므로 양방향 매핑
        self.pdno_symbol_map = {v: k for k, v in self.symbol_pdno_map.items()}
        # 심볼 자체도 매핑에 추가 (SOXL → SOXL)
        for symbol in self.symbol_pdno_map.keys():
            self.pdno_symbol_map[symbol] = symbol

        #  종목별 거래소 코드 (ChatGPT/KIS 챗봇 확인) 
        self.symbol_exchange_map = {
            "TQQQ": "NASD",  # KIS 기준 NASD 등록
            "SQQQ": "NASD",  # KIS 기준 NASD 등록
            "SOXL": "NASD",  # KIS 기준 NASD 등록
            "SOXS": "NASD"   # KIS 기준 NASD 등록
        }

        self.currency = "USD"
        self.target_symbols = ['SOXL', 'SOXS']  #  SOXL/SOXS (반도체 3X 레버리지) 

        # [자동 시작] Ollama 서버 확인 및 실행
        self._ensure_ollama_server_running()

        # [핵심] LLM 분석기 초기화 (14b × 2 병렬)
        print("\n[LLM 초기화] 14b × 2 병렬 앙상블 시작...")
        print("예상 시간: 2-3분 (모델 로딩)")

        try:
            # [14b × 2] 심층 분석 (빠른 추세 전환 대응, 90초)
            # 앙상블 분석기 (14b × 2) - 깊은 사고
            self.ensemble_analyzer = EnsembleLLMAnalyzer(base_model="qwen2.5:14b")
            print("[OK] 앙상블 분석기 준비 완료 (14b × 2)")

            # 메인 분석기 (14b)
            self.llm_analyzer = LLMMarketAnalyzer(model_name="qwen2.5:14b")
            print("[OK] 메인 분석기 준비 완료 (14b)")

            # [14b] 전략 학습 LLM 활성화 (메타 러닝)
            self.strategy_llm = LLMMarketAnalyzer(model_name="qwen2.5:14b")
            print("[INFO] 전략 분석기 활성화 (14b, 승/패 패턴 학습)")

        except Exception as e:
            print(f"[ERROR] LLM 초기화 실패: {e}")
            print("[FALLBACK] LLM 없이 실행 (간단한 전략 사용)")
            self.ensemble_analyzer = None
            self.llm_analyzer = None
            self.strategy_llm = None

        # 거래 히스토리 (Few-shot Learning용)
        self.trade_history = []
        self.all_trades = []
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.learning_file = os.path.join(script_dir, "kis_trade_history.json")
        self.load_trade_history()

        # 메타 학습 인사이트 (LLM이 학습한 패턴)
        self.meta_insights = []
        self.meta_learning_file = os.path.join(script_dir, "kis_meta_insights.json")
        self.load_meta_insights()

        # 가격 히스토리 (다중 시간프레임)
        self.price_history_1m = []  # 1분봉
        self.price_history_5m = []  # 5분봉
        self.max_history = 50

        # 포지션 관리
        self.position = None  # 'SOXL' or 'SOXS'
        self.entry_price = None
        self.entry_time = None
        self.entry_balance = None

        # 추세 신호
        self.trend_signal = None  # 'BULL' or 'BEAR'
        self.last_signal_change = None

        # 성능 추적
        self.stats = {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'total_pnl': 0.0,
            'llm_calls': 0,
            'successful_analyses': 0,
            'win_streak': 0,
            'loss_streak': 0
        }

        # Ollama는 수동으로 미리 시작해두세요
        print("\n[Ollama 확인]")
        print("[INFO] Ollama가 http://127.0.0.1:11435 에서 실행 중이어야 합니다")
        print("[INFO] start_ollama_11435.bat 을 먼저 실행하세요")

        # 텔레그램 비활성화 (자동매매 전용)
        self.telegram = None
        self.enable_telegram = False
        print("\n[텔레그램] 비활성화 (자동매매 전용 모드)")

        # 전략 파라미터 (LLM이 동적으로 조정)
        self.take_profit_target = None  # 익절 없음 - LLM이 방향 전환 감지 시에만 매도
        self.max_position_time = 30 * 60  # 30분
        self.min_confidence = 40  # 최소 신뢰도 40% (빠른 시장 변화 감지)

        # 동적 손절 (트레일링 스탑) - 백테스팅 최적화
        # [백테스팅 결과] -3.5% 손절선 = 14건 구제, 146% 손실 방지
        self.trailing_stop_loss = -3.5     # 초기 손절선 -3.5% (노이즈 필터 + 큰 손실 방지)
        self.max_pnl = -999.0              # 최고 PNL 기록 (손절선 상향용)

        # 현재 포지션 방향 추적 (LLM 신호 전환 감지용)
        self.current_llm_direction = None  # 'BULL' or 'BEAR'

        # [NEW] 진입 시점 타이밍 정보 저장 (노이즈 vs 진짜 신호 학습용)
        self.entry_timing_info = {
            'entry_peak': None,              # 진입 당시 최근 고점
            'entry_decline_from_peak': None, # 고점 대비 몇 % 하락했을 때 전환했는지
            'entry_momentum_weakening': None,# 진입 당시 모멘텀 약화도
            'entry_pattern': None,           # 진입 당시 패턴 (하락_패턴/상승_패턴)
            'entry_timestamp': None,         # 진입 시간
            'entry_price': None              # 진입 가격
        }

        # 실제 자동매매 활성화 여부
        self.auto_trading_enabled = True  # [WARNING] 실제 거래 활성화!

        print("\n[초기화 완료]")
        print(f"  계좌: {self.cano}-{self.acnt_prdt_cd}")
        print(f"  거래 종목: {', '.join(self.target_symbols)}")
        print(f"  LLM: {'활성화' if self.llm_analyzer else '비활성화'}")
        print(f"  학습된 거래: {len(self.all_trades)}개")
        print(f"  메타 인사이트: {len(self.meta_insights)}개")
        print(f"  [WARNING] 실제 거래: {'활성화' if self.auto_trading_enabled else '비활성화'}")
        print(f"  [INFO] 자동매매 전용 모드 (텔레그램 비활성화)")
        print("="*80)

    def _ensure_ollama_server_running(self):
        """
        Ollama 서버(포트 11435)가 실행 중인지 확인하고, 없으면 자동으로 시작
        """
        import socket
        import subprocess

        def check_port(port):
            """포트가 열려 있는지 확인"""
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()
                return result == 0
            except:
                return False

        print("\n[Ollama 서버 확인]")

        # 포트 11435 확인
        if check_port(11435):
            print("[OK] Ollama 서버 실행 중 (포트 11435)")
            return

        print("[INFO] Ollama 서버가 실행되지 않음")
        print("[INFO] 자동으로 Ollama 서버를 시작합니다...")

        # 배치 파일 경로
        batch_file = os.path.join(os.path.dirname(__file__), 'start_ollama_11435.bat')

        if not os.path.exists(batch_file):
            print(f"[ERROR] 배치 파일을 찾을 수 없습니다: {batch_file}")
            print("[INFO] 수동으로 Ollama 서버를 시작하세요:")
            print("       set OLLAMA_HOST=127.0.0.1:11435")
            print("       C:\\Users\\user\\AppData\\Local\\Programs\\Ollama\\ollama.exe serve")
            return

        try:
            # 배치 파일 실행 (백그라운드)
            subprocess.Popen(
                batch_file,
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                shell=True
            )
            print("[INFO] Ollama 서버 시작 중...")

            # 최대 30초 대기 (5초마다 확인)
            for i in range(6):
                time.sleep(5)
                if check_port(11435):
                    print(f"[OK] Ollama 서버 시작 완료 (포트 11435)")
                    return
                print(f"[INFO] 대기 중... ({(i+1)*5}초)")

            print("[WARNING] Ollama 서버 시작 확인 실패 (30초 초과)")
            print("[INFO] 백그라운드에서 시작 중일 수 있습니다. 계속 진행합니다.")

        except Exception as e:
            print(f"[ERROR] Ollama 서버 시작 실패: {e}")
            print("[INFO] 수동으로 Ollama 서버를 시작하세요")

    def _log_trading_action(self, message: str):
        """
        거래 로그를 파일에 기록 (타임스탬프 포함)
        """
        try:
            log_file = os.path.join(os.path.dirname(__file__), 'kis_trading_log.txt')
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            print(f"[WARNING] 로그 기록 실패: {e}")

    def _check_order_filled(self, order_no: str) -> bool:
        """
        주문 체결 여부 확인

        TR_ID: TTTS3035R (해외주식 주문체결내역)
        """
        try:
            from datetime import timedelta

            # 오늘 날짜로 조회
            today = datetime.now()
            yesterday = today - timedelta(days=1)

            url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-nccs"

            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "authorization": f"Bearer {self.access_token}",
                "appkey": self.config['my_app'],
                "appsecret": self.config['my_sec'],
                "tr_id": "TTTS3035R",
                "custtype": "P"
            }

            params = {
                "CANO": self.cano,
                "ACNT_PRDT_CD": self.acnt_prdt_cd,
                "PDNO": "%",
                "ORD_STRT_DT": yesterday.strftime('%Y%m%d'),
                "ORD_END_DT": today.strftime('%Y%m%d'),
                "SLL_BUY_DVSN": "00",  # 전체
                "CCLD_NCCS_DVSN": "01",  # 체결만
                "OVRS_EXCG_CD": "NASD",
                "SORT_SQN": "DS",
                "ORD_DT": "",
                "ORD_GNO_BRNO": "",
                "ODNO": order_no,  # 특정 주문번호 조회
                "CTX_AREA_NK200": "",
                "CTX_AREA_FK200": ""
            }

            # Rate Limit 보호: 간격 조절
            time.sleep(1)

            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                result = response.json()
                if result.get('rt_cd') == '0':
                    output = result.get('output', [])
                    # 체결된 주문이 있으면 True
                    for order in output:
                        if order.get('odno') == order_no:
                            ccld_qty = int(order.get('ccld_qty', '0'))
                            if ccld_qty > 0:
                                print(f"[체결 확인] 주문번호 {order_no}: {ccld_qty}주 체결")
                                return True
                    print(f"[미체결] 주문번호 {order_no}: 아직 미체결")
                    return False
        except Exception as e:
            print(f"[WARNING] 체결 확인 실패: {e}")
            return False

        return False

    def check_ollama_health(self) -> bool:
        """
        Ollama 서버 상태 확인

        Returns:
            True: 정상, False: 비정상
        """
        try:
            response = requests.get("http://127.0.0.1:11435/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])
                if models:
                    print(f"[OK] Ollama 정상 (모델 {len(models)}개)")
                    return True
                else:
                    print(f"[WARNING] Ollama 응답하지만 모델 없음")
                    return False
            else:
                print(f"[ERROR] Ollama HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"[ERROR] Ollama 연결 실패: {e}")
            return False

    def restart_ollama(self) -> bool:
        """
        Ollama 서버 재시작

        Returns:
            True: 재시작 성공, False: 실패
        """
        print("\n" + "="*80)
        print("[AUTO_RECOVERY] Ollama 재시작 시작...")
        print("="*80)

        try:
            import subprocess

            # 1. 기존 Ollama 프로세스 종료
            print("[1/4] 기존 Ollama 프로세스 종료 중...")
            subprocess.run(
                ["taskkill", "/F", "/IM", "ollama.exe"],
                capture_output=True,
                timeout=10
            )
            print("[OK] Ollama 프로세스 종료 완료")
            time.sleep(3)

            # 2. Ollama 11435 포트로 재시작
            print("[2/4] Ollama 11435 포트로 재시작 중...")
            ollama_path = r"C:\Users\user\AppData\Local\Programs\Ollama\ollama.exe"

            # 환경변수 설정
            env = os.environ.copy()
            env['OLLAMA_HOST'] = '127.0.0.1:11435'
            env['OLLAMA_MODELS'] = r'C:\Users\user\.ollama\models'

            # 백그라운드 실행
            subprocess.Popen(
                [ollama_path, 'serve'],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            print("[OK] Ollama 시작 명령 실행 완료")

            # 3. 서버 준비 대기 (최대 30초)
            print("[3/4] Ollama 서버 준비 대기 중...")
            for i in range(15):
                time.sleep(2)
                if self.check_ollama_health():
                    print(f"[OK] Ollama 서버 준비 완료 ({i*2+2}초 소요)")

                    # 4. Express 서버 재시작
                    print("[4/4] Express 서버 재시작 중...")
                    self.restart_express_server()

                    print("="*80)
                    print("[AUTO_RECOVERY] Ollama 재시작 완료!")
                    print("="*80 + "\n")
                    self._log_trading_action("Ollama 자동 재시작 성공")
                    return True
                print(f"  대기 중... ({i+1}/15)")

            print("[ERROR] Ollama 재시작 실패 - 타임아웃")
            self._log_trading_action("Ollama 자동 재시작 실패 - 타임아웃")
            return False

        except Exception as e:
            print(f"[ERROR] Ollama 재시작 실패: {e}")
            self._log_trading_action(f"Ollama 재시작 예외: {e}")
            import traceback
            traceback.print_exc()
            return False

    def restart_express_server(self) -> bool:
        """
        Express 프록시 서버 재시작

        Returns:
            True: 재시작 성공, False: 실패
        """
        try:
            import subprocess

            # Node.js 프로세스 종료
            print("  [Express] 기존 프로세스 종료 중...")
            subprocess.run(
                ["taskkill", "/F", "/IM", "node.exe"],
                capture_output=True,
                timeout=5
            )
            time.sleep(2)

            # Express 서버 재시작 (백그라운드)
            print("  [Express] 서버 재시작 중...")
            express_path = r"C:\Users\user\Documents\코드4\ollama-express"

            subprocess.Popen(
                ["node", "server.js"],
                cwd=express_path,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            time.sleep(5)  # 서버 초기화 대기
            print("  [Express] 재시작 완료")
            return True

        except Exception as e:
            print(f"  [WARNING] Express 재시작 실패: {e}")
            return False

    def auto_recovery_on_llm_failure(self) -> bool:
        """
        LLM 응답 실패 시 자동 복구 시도

        Returns:
            True: 복구 성공, False: 복구 실패
        """
        print("\n" + "!"*80)
        print("!!! LLM 응답 비정상 감지 - 자동 복구 시작 !!!")
        print("!"*80 + "\n")

        max_retries = 3

        for retry in range(max_retries):
            print(f"\n[복구 시도 {retry+1}/{max_retries}]")

            # Ollama 재시작 시도
            if self.restart_ollama():
                print(f"[OK] 복구 성공! ({retry+1}번째 시도)")
                return True

            if retry < max_retries - 1:
                wait_time = 30
                print(f"[RETRY] {wait_time}초 후 재시도...")
                time.sleep(wait_time)

        print("\n" + "!"*80)
        print(f"!!! 자동 복구 실패 ({max_retries}번 시도) !!!")
        print("!!! 수동 개입 필요 !!!")
        print("!"*80 + "\n")

        self._log_trading_action(f"자동 복구 실패 - {max_retries}번 시도")
        return False

    def load_trade_history(self):
        """거래 히스토리 로드"""
        if os.path.exists(self.learning_file):
            try:
                with open(self.learning_file, 'r', encoding='utf-8') as f:
                    self.all_trades = json.load(f)
                print(f"[학습 데이터] {len(self.all_trades)}개 거래 로드")
            except:
                self.all_trades = []

    def save_trade_history(self):
        """거래 히스토리 저장"""
        try:
            with open(self.learning_file, 'w', encoding='utf-8') as f:
                json.dump(self.all_trades, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ERROR] 거래 히스토리 저장 실패: {e}")

    def load_meta_insights(self):
        """메타 학습 인사이트 로드"""
        if os.path.exists(self.meta_learning_file):
            try:
                with open(self.meta_learning_file, 'r', encoding='utf-8') as f:
                    self.meta_insights = json.load(f)
                print(f"[메타 학습] {len(self.meta_insights)}개 인사이트 로드")
            except:
                self.meta_insights = []

    def save_meta_insights(self):
        """메타 학습 인사이트 저장"""
        try:
            with open(self.meta_learning_file, 'w', encoding='utf-8') as f:
                json.dump(self.meta_insights, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ERROR] 메타 인사이트 저장 실패: {e}")

    def update_timing_insights(self):
        """
        타이밍 패턴 분석 및 메타 인사이트 업데이트

        최근 거래들을 분석해서:
        1. 최적 전환 타이밍 패턴 찾기
        2. 노이즈 vs 진짜 신호 구분 패턴
        3. 빠르면서 정확한 타이밍 학습
        """
        if len(self.all_trades) < 5:
            return  # 데이터 부족

        recent_trades = self.all_trades[-20:] if len(self.all_trades) >= 20 else self.all_trades

        # 타이밍 평가별 분류
        optimal_trades = []
        too_early_trades = []
        too_late_trades = []
        failed_trades = []

        for trade in recent_trades:
            if not isinstance(trade, dict):
                continue

            timing_eval = trade.get('timing_evaluation', 'UNKNOWN')
            if timing_eval == 'OPTIMAL':
                optimal_trades.append(trade)
            elif timing_eval == 'TOO_EARLY':
                too_early_trades.append(trade)
            elif timing_eval == 'TOO_LATE':
                too_late_trades.append(trade)
            elif timing_eval == 'FAILED':
                failed_trades.append(trade)

        # 최적 타이밍 패턴 분석
        if optimal_trades:
            # 성공한 진입 타이밍의 평균 계산
            optimal_declines = [t.get('entry_decline_from_peak', 0) for t in optimal_trades if t.get('entry_decline_from_peak') is not None]
            optimal_patterns = [t.get('entry_pattern', '') for t in optimal_trades]

            if optimal_declines:
                avg_decline = sum(optimal_declines) / len(optimal_declines)
                min_decline = min(optimal_declines)
                max_decline = max(optimal_declines)

                # 패턴 빈도 계산
                pattern_counts = {}
                for p in optimal_patterns:
                    pattern_counts[p] = pattern_counts.get(p, 0) + 1

                best_pattern = max(pattern_counts, key=pattern_counts.get) if pattern_counts else "알 수 없음"

                timing_insight = {
                    'type': 'OPTIMAL_TIMING_PATTERN',
                    'timestamp': datetime.now().isoformat(),
                    'sample_size': len(optimal_trades),
                    'success_rate': f"{len(optimal_trades)}/{len(recent_trades)} = {len(optimal_trades)/len(recent_trades)*100:.1f}%",
                    'patterns': {
                        'avg_entry_decline': f"{avg_decline:.2f}%",
                        'decline_range': f"{min_decline:.2f}% ~ {max_decline:.2f}%",
                        'best_pattern': best_pattern,
                        'pattern_frequency': pattern_counts
                    },
                    'recommendation': f"최적 전환: 고점 대비 {avg_decline:.1f}% 하락 시 ({min_decline:.1f}%~{max_decline:.1f}% 범위)",
                    'learning_note': f"성공한 {len(optimal_trades)}건 분석 결과, 평균 {avg_decline:.1f}% 하락 시점에서 전환이 최적"
                }

        # 노이즈 패턴 분석 (TOO_EARLY)
        if too_early_trades:
            early_declines = [t.get('entry_decline_from_peak', 0) for t in too_early_trades if t.get('entry_decline_from_peak') is not None]
            if early_declines:
                avg_early = sum(early_declines) / len(early_declines)

                noise_insight = {
                    'type': 'NOISE_PATTERN',
                    'timestamp': datetime.now().isoformat(),
                    'sample_size': len(too_early_trades),
                    'patterns': {
                        'avg_entry_decline': f"{avg_early:.2f}%",
                        'noise_frequency': f"{len(too_early_trades)}/{len(recent_trades)} = {len(too_early_trades)/len(recent_trades)*100:.1f}%"
                    },
                    'warning': f"고점 대비 {avg_early:.1f}% 하락 시점 = 노이즈 가능성 높음 (성급한 전환)",
                    'learning_note': f"{len(too_early_trades)}건의 성급한 전환 사례 학습"
                }

        # 늦은 전환 패턴 분석 (TOO_LATE)
        if too_late_trades:
            late_declines = [t.get('entry_decline_from_peak', 0) for t in too_late_trades if t.get('entry_decline_from_peak') is not None]
            if late_declines:
                avg_late = sum(late_declines) / len(late_declines)

                late_insight = {
                    'type': 'LATE_TIMING_PATTERN',
                    'timestamp': datetime.now().isoformat(),
                    'sample_size': len(too_late_trades),
                    'patterns': {
                        'avg_entry_decline': f"{avg_late:.2f}%",
                    },
                    'warning': f"고점 대비 {avg_late:.1f}% 하락 후 전환 = 수익 놓침 (늦은 전환)",
                    'learning_note': f"{len(too_late_trades)}건의 늦은 전환으로 수익 손실"
                }

        # 메타 인사이트 업데이트 (최신 3개만 유지)
        new_insights = []
        if optimal_trades:
            new_insights.append(timing_insight)
        if too_early_trades:
            new_insights.append(noise_insight)
        if too_late_trades:
            new_insights.append(late_insight)

        # 기존 타이밍 인사이트 제거하고 새로 추가
        self.meta_insights = [i for i in self.meta_insights if i.get('type') not in ['OPTIMAL_TIMING_PATTERN', 'NOISE_PATTERN', 'LATE_TIMING_PATTERN']]
        self.meta_insights.extend(new_insights)

        # 최신 10개만 유지
        self.meta_insights = self.meta_insights[-10:]

        self.save_meta_insights()

        if new_insights:
            print(f"\n[타이밍 학습] {len(new_insights)}개 패턴 업데이트")
            for insight in new_insights:
                print(f"  - {insight['type']}: {insight.get('learning_note', '')}")

    def get_usd_cash_balance(self, symbol: str = "TQQQ", price: float = 35.0) -> Dict:
        """
        USD 현금 잔고 조회

        [중요] KIS API 정책:
        - USD 현금 잔고는 직접 조회 API가 없음
        - /uapi/overseas-stock/v1/trading/inquire-balance는 보유 종목만 반환, USD 예수금 반환 안 함
        - 이 함수는 '매수가능금액 API'로 간접 확인
        - ord_psbl_frcr_amt (주문 가능 외화 금액) = 현금에서 미체결 차감한 실매수 가능액
        """
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-psamount"

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.config['my_app'],
            "appsecret": self.config['my_sec'],
            "tr_id": "JTTT3007R",
            "custtype": "P",
            "User-Agent": self.config.get('my_agent', 'Mozilla/5.0')
        }

        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": "AMEX",  # 필수!
            "OVRS_ORD_UNPR": str(price),
            "ITEM_CD": symbol
        }

        try:
            print("[DEBUG] get_usd_cash_balance() API 호출 중...")
            response = requests.get(url, headers=headers, params=params, timeout=10)
            print(f"[DEBUG] 응답 코드: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print(f"[DEBUG] rt_cd: {result.get('rt_cd')}")

                if result.get('rt_cd') == '0':
                    output = result.get('output', {})
                    ord_psbl_frcr_amt = float(output.get('ord_psbl_frcr_amt', '0').replace(',', ''))
                    print(f"[DEBUG] USD 주문 가능 금액: ${ord_psbl_frcr_amt:.2f}")
                    return {
                        'success': True,
                        'ord_psbl_frcr_amt': ord_psbl_frcr_amt
                    }
                else:
                    print(f"[DEBUG] rt_cd 오류: {result.get('msg1')}")
            else:
                print(f"[DEBUG] HTTP 오류: {response.text[:200]}")

            return {'success': False}
        except Exception as e:
            print(f"[DEBUG] 예외 발생: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False}

    def get_realtime_price(self, symbol: str) -> float:
        """FMP API로 실시간 가격 조회"""
        try:
            url = f"{FMP_BASE_URL}/quote/{symbol}"
            params = {"apikey": FMP_API_KEY}
            response = requests.get(url, params=params, timeout=5)

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    price = data[0].get('price', 0)
                    print(f"[FMP] {symbol} 실시간 가격: ${price:.2f}")
                    return float(price)

            print(f"[FMP] {symbol} 가격 조회 실패")
            return 40.0 if 'SOXL' in symbol else 20.0  # 기본값
        except Exception as e:
            print(f"[FMP] 오류: {e}")
            return 40.0 if 'SOXL' in symbol else 20.0

    def get_positions(self) -> List[Dict]:
        """보유 포지션 조회"""
        print("[DEBUG] get_positions() 시작")
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-balance"

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.config['my_app'],
            "appsecret": self.config['my_sec'],
            "tr_id": "JTTT3012R",
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
            print("[DEBUG] API 호출 중...")
            response = requests.get(url, headers=headers, params=params, timeout=10)
            print(f"[DEBUG] 응답 코드: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print(f"[DEBUG] rt_cd: {result.get('rt_cd')}")

                if result.get('rt_cd') == '0':
                    output1 = result.get('output1', [])
                    print(f"[DEBUG] output1 개수: {len(output1)}")
                    positions = []

                    for idx, item in enumerate(output1):
                        pdno = item.get('ovrs_pdno', '')
                        qty_str = item.get('ovrs_cblc_qty', '0')
                        print(f"[DEBUG] Item {idx}: pdno={pdno}, qty_str={qty_str}")

                        #  PDNO → Symbol 변환 
                        # pdno_symbol_map에 "SOXL"→"SOXL", "A980679"→"SOXL" 둘 다 있음
                        symbol = self.pdno_symbol_map.get(pdno, None)

                        if symbol is None:
                            print(f"[WARNING] PDNO {pdno}는 매핑되지 않은 종목 (스킵)")
                            print(f"[DEBUG] 지원 종목: {list(self.pdno_symbol_map.keys())}")
                            continue

                        print(f"[OK] PDNO {pdno} → Symbol {symbol}")

                        try:
                            qty = float(qty_str)
                        except:
                            print(f"[ERROR] qty 변환 실패: {qty_str}")
                            qty = 0

                        if qty > 0:
                            avg_price_str = item.get('pchs_avg_pric', '0')
                            current_price_str = item.get('now_pric2', '0')
                            eval_amt_str = item.get('ovrs_stck_evlu_amt', '0')
                            exchange_cd = item.get('ovrs_excg_cd', 'NASD')  # 거래소 코드 읽기 (AMEX, NASD 등)

                            print(f"[DEBUG] 가격 데이터: avg={avg_price_str}, current={current_price_str}, eval={eval_amt_str}, exchange={exchange_cd}")

                            try:
                                positions.append({
                                    'symbol': symbol,
                                    'qty': qty,
                                    'avg_price': float(avg_price_str),
                                    'current_price': float(current_price_str),
                                    'eval_amt': float(eval_amt_str),
                                    'pnl_pct': 0.0,  # 계산 필요
                                    'exchange_cd': exchange_cd  # 거래소 코드 저장
                                })
                                print(f"[DEBUG] 포지션 추가 성공: {symbol} (거래소: {exchange_cd})")
                            except Exception as e:
                                print(f"[ERROR] 포지션 데이터 변환 실패: {e}")

                    # 손익률 계산
                    for pos in positions:
                        if pos['avg_price'] > 0:
                            cost = pos['qty'] * pos['avg_price']
                            pos['pnl_pct'] = ((pos['eval_amt'] - cost) / cost) * 100
                            print(f"[DEBUG] 손익률 계산: {pos['symbol']} = {pos['pnl_pct']:.2f}%")

                    print(f"[DEBUG] get_positions() 완료, {len(positions)}개 반환")
                    return positions
            else:
                print(f"[ERROR] HTTP {response.status_code}")
                print(f"[ERROR] 응답 내용: {response.text[:200]}")
                return []
        except Exception as e:
            print(f"[ERROR] get_positions() 예외: {e}")
            import traceback
            traceback.print_exc()

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

    def send_trading_signal_notification(self, signal: str, symbol: str, confidence: float, reasoning: str, current_position: str = None, current_pnl_pct: float = 0):
        """LLM 분석 결과 알림 (자동매매 전용 - 텔레그램 비활성화)"""
        # 자동매매 전용 모드 - 텔레그램 알림 없음
        pass

    def place_order(self, symbol: str, order_type: str, quantity: int = None, price: float = None) -> Dict:
        """
        해외주식 주문 실행 (매수/매도)

        Args:
            symbol: 종목코드 (SOXL, SOXS)
            order_type: 'BUY' or 'SELL'
            quantity: 주문 수량 (None이면 전액/전량)
            price: 주문 가격 (None이면 시장가)

        Returns:
            {'success': bool, 'order_no': str, 'message': str}
        """
        if not self.auto_trading_enabled:
            print(f"[시뮬레이션] {order_type} {symbol} {quantity}주 (실제 주문 안 함)")
            return {'success': True, 'order_no': 'SIM-12345', 'message': '시뮬레이션'}

        # 로그 파일에 주문 시도 기록
        self._log_trading_action(f"주문 시도: {order_type} {symbol} {quantity}주 @ ${price}")

        try:
            # TR ID 결정
            if order_type == 'BUY':
                tr_id = "TTTT1002U"  # 해외주식 매수
            elif order_type == 'SELL':
                tr_id = "TTTT1006U"  # 해외주식 매도
            else:
                return {'success': False, 'message': f'잘못된 주문 타입: {order_type}'}

            # PDNO 변환
            if symbol not in self.symbol_pdno_map:
                return {'success': False, 'message': f'{symbol} PDNO 매핑 없음'}

            pdno = self.symbol_pdno_map[symbol]
            exchange_cd = self.symbol_exchange_map.get(symbol, self.exchange_cd)

            print(f"\n[종목 정보]")
            print(f"  심볼: {symbol}")
            print(f"  PDNO: {pdno}")
            print(f"  거래소: {exchange_cd}")

            # 현재가 조회 (시장가도 현재가 필수)
            if price is None or price <= 0:
                if hasattr(self, 'price_history_1m') and self.price_history_1m:
                    price = self.price_history_1m[-1]
                else:
                    # FMP API로 실시간 가격 조회
                    price = self.get_realtime_price(symbol)

            # 가격 안전성 검증 (최소값 체크)
            if price is None or price <= 1.0:
                print(f"[ERROR] 가격이 비정상적입니다: {price}")
                # 강제로 FMP에서 실시간 가격 조회
                price = self.get_realtime_price(symbol)
                print(f"[INFO] FMP 실시간 가격으로 대체: ${price:.2f}")

            # 최종 검증: 가격이 여전히 비정상적이면 에러
            if price <= 1.0:
                return {'success': False, 'message': f'가격 조회 실패 (가격: ${price:.2f})'}

            print(f"[OK] 현재가 확인: ${price:.2f}")

            # 수량 결정
            if quantity is None:
                if order_type == 'BUY':
                    # 매수: 가용 현금으로 최대 수량 계산
                    balance = self.get_usd_cash_balance(symbol, price)
                    if not balance['success']:
                        print("[ERROR] 잔고 조회 실패 - 기본 수량 10주 사용")
                        quantity = 10
                    else:
                        cash = balance['ord_psbl_frcr_amt']
                        quantity = int(cash / price)
                        if quantity < 1:
                            return {'success': False, 'message': f'주문 가능 수량 부족 (현금: ${cash:.2f})'}
                elif order_type == 'SELL':
                    # 매도: 보유 전량
                    positions = self.get_positions()
                    pos = next((p for p in positions if p['symbol'] == symbol), None)
                    if not pos:
                        return {'success': False, 'message': f'{symbol} 보유 없음'}
                    quantity = int(pos['qty'])
                    price = pos.get('current_price', price)

            # 가격 결정 (시장가도 현재가 입력)
            order_price = f"{float(price):.2f}"

            # 최종 가격 검증 (OVRS_ORD_UNPR 값이 "1.00" 이하면 에러)
            if float(order_price) <= 1.0:
                error_msg = f"[CRITICAL ERROR] OVRS_ORD_UNPR 값이 비정상: {order_price}"
                print(error_msg)
                self._log_trading_action(error_msg)
                return {'success': False, 'message': error_msg}

            # 주문 데이터 생성
            order_data = {
                "CANO": self.cano,
                "ACNT_PRDT_CD": self.acnt_prdt_cd,
                "OVRS_EXCG_CD": exchange_cd,
                "PDNO": pdno,
                "ORD_QTY": str(quantity),
                "OVRS_ORD_UNPR": order_price,  #  반드시 현재가여야 함!
                "ORD_SVR_DVSN_CD": "0",
                "ORD_DVSN": "00"  # 00=시장가
            }

            print(f"\n[주문 요청] {order_type} {symbol} ({pdno})")
            print(f"  수량: {quantity}주")
            print(f"  가격: ${order_price}")
            print(f"  [검증] OVRS_ORD_UNPR = '{order_price}' (OK)")
            print(f"  [전송할 Body]:")
            print(f"    OVRS_EXCG_CD: {exchange_cd}")
            print(f"    PDNO: {pdno}")
            print(f"    ORD_QTY: {quantity}")
            print(f"    OVRS_ORD_UNPR: {order_price}")
            print(f"    ORD_DVSN: 00 (시장가)")

            # 해시키 생성
            hashkey = self.get_hashkey(order_data)

            # API 호출
            url = f"{self.base_url}/uapi/overseas-stock/v1/trading/order"

            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "authorization": f"Bearer {self.access_token}",
                "appkey": self.config['my_app'],
                "appsecret": self.config['my_sec'],
                "tr_id": tr_id,
                "custtype": "P",
                "hashkey": hashkey,
                "User-Agent": self.config.get('my_agent', 'Mozilla/5.0')
            }

            # Rate Limit 보호: API 호출 간격 조절
            time.sleep(1)

            response = requests.post(url, headers=headers, json=order_data, timeout=10)

            print(f"\n[주문 응답] HTTP {response.status_code}")

            # Rate Limit 처리 (HTTP 500)
            if response.status_code == 500:
                print("[WARNING] HTTP 500 - Rate Limit 추정, 10분 후 재시도")
                self._log_trading_action("HTTP 500 오류 - 10분 대기")
                time.sleep(600)  # 10분 대기
                return self.place_order(symbol, order_type, quantity, price)  # 재시도

            if response.status_code == 200:
                result = response.json()
                rt_cd = result.get('rt_cd', '')
                msg = result.get('msg1', '')

                if rt_cd == '0':
                    order_no = result.get('output', {}).get('ODNO', 'N/A')
                    print(f"[OK] 주문 성공: 주문번호 {order_no}")

                    # 로그 기록
                    self._log_trading_action(f"주문 성공: {order_type} {symbol} {quantity}주 @ ${order_price}, 주문번호: {order_no}")

                    # 체결 확인 (5초 후)
                    time.sleep(5)
                    filled = self._check_order_filled(order_no)
                    if filled:
                        print(f"[OK] 체결 확인 완료")
                        self._log_trading_action(f"체결 확인: 주문번호 {order_no}")

                    return {
                        'success': True,
                        'order_no': order_no,
                        'message': msg,
                        'quantity': quantity
                    }
                else:
                    print(f"[ERROR] 주문 실패: {msg} (rt_cd: {rt_cd})")
                    self._log_trading_action(f"주문 실패: {msg}")
                    return {'success': False, 'message': msg}
            else:
                print(f"[ERROR] 주문 실패: HTTP {response.status_code}")
                self._log_trading_action(f"HTTP 오류: {response.status_code}")
                return {'success': False, 'message': f'HTTP {response.status_code}'}

        except Exception as e:
            print(f"[ERROR] 주문 예외: {e}")
            self._log_trading_action(f"주문 예외: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': str(e)}

    def sell_all(self, symbol: str) -> Dict:
        """보유 종목 전량 매도"""
        print(f"\n[전량 매도] {symbol}")
        return self.place_order(symbol, 'SELL', quantity=None, price=None)

    def buy_max(self, symbol: str) -> Dict:
        """가용 현금으로 최대 매수"""
        print(f"\n[최대 매수] {symbol}")
        return self.place_order(symbol, 'BUY', quantity=None, price=None)

    def _evaluate_timing(self, pnl_pct: float, exit_decline_from_peak: float) -> Dict:
        """
        타이밍 평가 (노이즈 vs 진짜 신호 학습용)

        평가 기준:
        - OPTIMAL: 빠르면서 정확한 전환 (수익 + 적시)
        - TOO_EARLY: 너무 성급 (노이즈였음, 더 가다렸으면 더 수익)
        - TOO_LATE: 너무 늦음 (안전하지만 수익 많이 날림)
        - FAILED: 실패 (손실)
        """
        entry_decline = self.entry_timing_info.get('entry_decline_from_peak', 0)

        # 1. 손실 = 실패
        if pnl_pct < 0:
            return {
                'evaluation': 'FAILED',
                'score': 0,
                'note': f'손실 {pnl_pct:.2f}% (진입: 고점대비{entry_decline:.1f}%)'
            }

        # 2. 수익이 났지만 타이밍 평가
        if pnl_pct > 0:
            # 큰 수익 (5% 이상) = 최적
            if pnl_pct >= 5.0:
                return {
                    'evaluation': 'OPTIMAL',
                    'score': 100,
                    'note': f'대성공! +{pnl_pct:.2f}% (진입: 고점대비{entry_decline:.1f}%에서 전환)'
                }

            # 적당한 수익 (2-5%)
            elif pnl_pct >= 2.0:
                # 진입이 빨랐는지 판단 (고점 대비 -1% 이내 진입 = 빨랐음)
                if abs(entry_decline) < 1.0:
                    # 조기 진입했는데 수익 = 좋은 판단
                    return {
                        'evaluation': 'OPTIMAL',
                        'score': 85,
                        'note': f'좋음! +{pnl_pct:.2f}% (조기진입 고점대비{entry_decline:.1f}%)'
                    }
                elif abs(entry_decline) < 2.0:
                    # 적절한 타이밍
                    return {
                        'evaluation': 'OPTIMAL',
                        'score': 90,
                        'note': f'적절! +{pnl_pct:.2f}% (진입: 고점대비{entry_decline:.1f}%)'
                    }
                else:
                    # 늦은 진입 (-2% 이상 하락 후)
                    return {
                        'evaluation': 'TOO_LATE',
                        'score': 70,
                        'note': f'늦음. +{pnl_pct:.2f}% (진입: 고점대비{entry_decline:.1f}%, 더 빨랐으면 +수익)'
                    }

            # 작은 수익 (0-2%)
            else:
                # 진입이 매우 빨랐다면 (고점 근처 -0.5% 이내) = 노이즈 가능성
                if abs(entry_decline) < 0.5:
                    return {
                        'evaluation': 'TOO_EARLY',
                        'score': 60,
                        'note': f'성급? +{pnl_pct:.2f}% (고점 근처 진입, 노이즈 가능성)'
                    }
                # 적당한 진입인데 수익 적음 = 괜찮음
                elif abs(entry_decline) < 2.0:
                    return {
                        'evaluation': 'OPTIMAL',
                        'score': 75,
                        'note': f'괜찮음 +{pnl_pct:.2f}% (적절한 진입 고점대비{entry_decline:.1f}%)'
                    }
                # 늦은 진입에 수익도 적음
                else:
                    return {
                        'evaluation': 'TOO_LATE',
                        'score': 50,
                        'note': f'늦음 +{pnl_pct:.2f}% (진입: 고점대비{entry_decline:.1f}%, 수익 적음)'
                    }

        # 기본값
        return {
            'evaluation': 'UNKNOWN',
            'score': 50,
            'note': f'평가불가 {pnl_pct:.2f}%'
        }

    def analyze_market_with_llm(self, current_price: float, price_history: List[float]) -> Dict:
        """
        LLM으로 시장 분석 (핵심 함수!)

        14b × 2 병렬 앙상블로 추세돌파 판단

        Returns:
            {
                'signal': 'BULL' or 'BEAR' or 'HOLD',
                'confidence': float (0-100),
                'reasoning': str,
                'predicted_trend': str
            }
        """
        if not self.ensemble_analyzer:
            # LLM 없으면 기술적 지표 기반 전략 (Fallback)
            print("[FALLBACK 전략] LLM 없이 기술적 지표로 분석")

            if len(price_history) < 5:
                return {'signal': 'HOLD', 'confidence': 0, 'reasoning': '데이터 부족'}

            # 간단한 추세 분석 (최근 5개 데이터 기준)
            recent_prices = price_history[-5:]
            avg_price = sum(recent_prices) / len(recent_prices)
            price_change_pct = ((current_price - recent_prices[0]) / recent_prices[0]) * 100

            # 모멘텀 계산
            upward_moves = sum(1 for i in range(1, len(recent_prices)) if recent_prices[i] > recent_prices[i-1])
            momentum_strength = (upward_moves / (len(recent_prices) - 1)) * 100

            # 신호 판단
            signal = 'HOLD'
            confidence = 50
            reasoning = f"가격 변화: {price_change_pct:.2f}%, 모멘텀: {momentum_strength:.0f}%"

            # 강한 상승 추세
            if price_change_pct > 0.5 and momentum_strength >= 75:
                signal = 'BULL'
                confidence = min(85, 60 + int(price_change_pct * 10))
                reasoning = f"상승 추세 감지 (+{price_change_pct:.2f}%, 모멘텀 {momentum_strength:.0f}%)"

            # 강한 하락 추세
            elif price_change_pct < -0.5 and momentum_strength <= 25:
                signal = 'BEAR'
                confidence = min(85, 60 + int(abs(price_change_pct) * 10))
                reasoning = f"하락 추세 감지 ({price_change_pct:.2f}%, 모멘텀 {momentum_strength:.0f}%)"

            # 약한 신호
            elif abs(price_change_pct) > 0.3:
                if price_change_pct > 0:
                    signal = 'BULL'
                    confidence = 65
                else:
                    signal = 'BEAR'
                    confidence = 65
                reasoning = f"약한 추세 ({price_change_pct:.2f}%)"

            print(f"[FALLBACK] 신호={signal}, 신뢰도={confidence}%, 이유={reasoning}")

            return {
                'signal': signal,
                'confidence': confidence,
                'reasoning': reasoning,
                'predicted_trend': signal
            }

        try:
            # 시장 데이터 준비
            market_data = {
                'current_price': current_price,
                'price_history_1m': price_history[-20:] if len(price_history) >= 20 else price_history,
                'timestamp': datetime.now().isoformat()
            }

            # 거래 히스토리 (Few-shot Learning)
            recent_trades = self.all_trades[-10:] if len(self.all_trades) >= 10 else self.all_trades

            # 메타 인사이트
            insights = self.meta_insights[-5:] if len(self.meta_insights) >= 5 else self.meta_insights

            # LLM 프롬프트 구성
            prompt = f"""
당신은 전문 트레이더입니다. SOXL(상승 레버리지 ETF)과 SOXS(하락 레버리지 ETF) 추세돌파 전략을 분석하세요.

[현재 시장 상황]
현재가: ${current_price:.2f}
최근 가격 추이: {price_history[-10:]}

[과거 거래 학습 데이터]
{json.dumps(recent_trades, indent=2, ensure_ascii=False) if recent_trades else '데이터 없음'}

[메타 학습 인사이트]
{json.dumps(insights, indent=2, ensure_ascii=False) if insights else '데이터 없음'}

[분석 요청]
1. 현재 추세가 상승(BULL)인가 하락(BEAR)인가?
2. 추세돌파가 발생했는가?
3. 신뢰도는? (0-100)
4. 이유는?

JSON 형식으로 답변:
{{
    "signal": "BULL" or "BEAR" or "HOLD",
    "confidence": 75,
    "reasoning": "상승 추세 돌파 확인. 최근 10분간 지속적 상승...",
    "predicted_trend": "단기 상승 예상"
}}
"""

            # 앙상블 분석 (14b × 2 병렬)
            print("[LLM 분석 중...] 14b × 2 병렬 실행 (예상 시간: 2-4분)")
            print(f"[DEBUG] analyze_market_with_llm 시작")
            print(f"[DEBUG] current_price: {current_price}")
            print(f"[DEBUG] price_history 길이: {len(price_history)}")
            print(f"[DEBUG] trade_history 개수: {len(recent_trades)}")

            self.stats['llm_calls'] += 1

            # ===================================================================
            # [핵심 개선] 추세 반전 감지를 위한 가격 분석 메트릭 계산
            # ===================================================================

            # 1. 최근 고점/저점 찾기 (지난 20개 데이터)
            recent_20 = price_history[-20:] if len(price_history) >= 20 else price_history
            recent_peak = max(recent_20) if recent_20 else current_price
            recent_bottom = min(recent_20) if recent_20 else current_price

            # 2. 고점 대비 하락률 계산 (핵심 지표!)
            decline_from_peak = ((current_price - recent_peak) / recent_peak * 100) if recent_peak > 0 else 0
            rise_from_bottom = ((current_price - recent_bottom) / recent_bottom * 100) if recent_bottom > 0 else 0

            # 3. 단기 vs 중기 모멘텀 비교 (추세 약화 감지)
            if len(price_history) >= 10:
                # 단기 모멘텀 (최근 5개)
                short_term = price_history[-5:]
                short_momentum = ((short_term[-1] - short_term[0]) / short_term[0] * 100) if short_term[0] > 0 else 0

                # 중기 모멘텀 (최근 10개)
                mid_term = price_history[-10:]
                mid_momentum = ((mid_term[-1] - mid_term[0]) / mid_term[0] * 100) if mid_term[0] > 0 else 0

                # 모멘텀 약화 감지 (단기가 중기보다 약함 = 추세 꺾임 신호)
                momentum_weakening = mid_momentum - short_momentum
            else:
                short_momentum = 0
                mid_momentum = 0
                momentum_weakening = 0

            # 4. 고점/저점 패턴 분석 (Lower Highs / Higher Lows)
            if len(price_history) >= 15:
                # 최근 3개 구간으로 나눔
                segment1 = price_history[-15:-10]
                segment2 = price_history[-10:-5]
                segment3 = price_history[-5:]

                high1 = max(segment1) if segment1 else current_price
                high2 = max(segment2) if segment2 else current_price
                high3 = max(segment3) if segment3 else current_price

                low1 = min(segment1) if segment1 else current_price
                low2 = min(segment2) if segment2 else current_price
                low3 = min(segment3) if segment3 else current_price

                # Lower Highs = 하락 추세 신호
                lower_highs = (high1 > high2 and high2 > high3)
                # Higher Lows = 상승 추세 신호
                higher_lows = (low1 < low2 and low2 < low3)

                pattern_signal = "하락_패턴" if lower_highs else "상승_패턴" if higher_lows else "횡보"
            else:
                pattern_signal = "데이터부족"

            # 5. 시장 데이터 준비 (강화된 분석 메트릭 포함)
            market_data = {
                'current_price': current_price,
                'price_history_1m': price_history,  # [FIX] ensemble_llm_analyzer.py가 이 키를 찾음
                'current_direction': self.current_llm_direction,  # 현재 LLM이 주고 있는 방향 (전환 감지용)
                'timestamp': datetime.now().isoformat(),

                # [NEW] 추세 반전 감지를 위한 핵심 메트릭
                'recent_peak': recent_peak,
                'recent_bottom': recent_bottom,
                'decline_from_peak_pct': decline_from_peak,
                'rise_from_bottom_pct': rise_from_bottom,
                'short_momentum_pct': short_momentum,
                'mid_momentum_pct': mid_momentum,
                'momentum_weakening': momentum_weakening,
                'pattern_signal': pattern_signal,

                # 디버깅 정보
                'price_range': f"${recent_bottom:.2f} ~ ${recent_peak:.2f}"
            }

            # 6. 추세 반전 경고 출력
            print(f"\n[추세 분석]")
            print(f"  현재가: ${current_price:.2f}")
            print(f"  최근 고점: ${recent_peak:.2f} → 하락률: {decline_from_peak:.2f}%")
            print(f"  최근 저점: ${recent_bottom:.2f} → 상승률: {rise_from_bottom:.2f}%")
            print(f"  단기 모멘텀: {short_momentum:.2f}% | 중기 모멘텀: {mid_momentum:.2f}%")
            print(f"  모멘텀 약화도: {momentum_weakening:.2f}% (양수=약화, 음수=강화)")
            print(f"  패턴: {pattern_signal}")

            if decline_from_peak < -1.5:
                print(f"  [WARNING] 경고: 고점 대비 {abs(decline_from_peak):.2f}% 하락 - 추세 반전 가능성!")
            if momentum_weakening > 1.0:
                print(f"  [WARNING] 경고: 모멘텀 약화 감지 ({momentum_weakening:.2f}%) - 추세 둔화!")

            # 메타 인사이트에 핵심 전략 추가 (강화된 추세 반전 감지 지침)
            enhanced_insights = self.meta_insights.copy() if self.meta_insights else []

            # [NEW] 타이밍 학습 데이터 추출
            timing_learning = ""
            optimal_timing_pattern = None
            noise_pattern = None

            for insight in self.meta_insights:
                if not isinstance(insight, dict):
                    continue

                if insight.get('type') == 'OPTIMAL_TIMING_PATTERN':
                    optimal_timing_pattern = insight
                elif insight.get('type') == 'NOISE_PATTERN':
                    noise_pattern = insight

            # 타이밍 학습 정보 구성
            if optimal_timing_pattern:
                recommendation = optimal_timing_pattern.get('recommendation', '')
                learning_note = optimal_timing_pattern.get('learning_note', '')
                timing_learning += f"\n 과거 성공 패턴:\n   {learning_note}\n   → {recommendation}"

            if noise_pattern:
                warning = noise_pattern.get('warning', '')
                learning_note = noise_pattern.get('learning_note', '')
                timing_learning += f"\n 노이즈 패턴 (피해야 함):\n   {learning_note}\n   → {warning}"

            # 현재 상황과 과거 패턴 비교
            timing_comparison = ""
            if optimal_timing_pattern and decline_from_peak < 0:
                patterns = optimal_timing_pattern.get('patterns', {})
                avg_entry = patterns.get('avg_entry_decline', '')
                if avg_entry:
                    try:
                        avg_val = float(avg_entry.replace('%', ''))
                        current_val = decline_from_peak

                        if abs(current_val - avg_val) < 0.5:
                            timing_comparison = f"\n[OPTIMAL] 현재 고점대비 {decline_from_peak:.1f}% ≈ 과거 최적 타이밍 {avg_entry} → 전환 고려!"
                        elif current_val > avg_val:  # 덜 떨어짐
                            timing_comparison = f"\n[WAIT] 현재 고점대비 {decline_from_peak:.1f}% < 과거 최적 {avg_entry} → 조금 더 지켜볼까?"
                        else:  # 더 떨어짐
                            timing_comparison = f"\n[WARNING] 현재 고점대비 {decline_from_peak:.1f}% > 과거 최적 {avg_entry} → 이미 늦을 수 있음!"
                    except:
                        pass

            enhanced_insights.insert(0, {
                'type': 'CORE_STRATEGY',
                'instruction': f"""
[핵심 임무] 방향 전환 징후 조기 감지!

현재 방향: {self.current_llm_direction or '미설정 (첫 진입)'}
과거 거래: {len(recent_trades)}건

[현재 추세 상태 분석]
고점: ${recent_peak:.2f} → 현재: ${current_price:.2f} (고점 대비: {decline_from_peak:+.2f}%)
단기 모멘텀: {short_momentum:+.2f}% | 중기 모멘텀: {mid_momentum:+.2f}%
모멘텀 약화도: {momentum_weakening:+.2f}% | 패턴: {pattern_signal}

[중요! 과거 학습한 타이밍 패턴]{timing_learning}{timing_comparison}

[추세 반전 판단 기준]
[WARNING] BULL 포지션 중 하락 신호:
  - 고점 대비 -2% 이상 하락 → BEAR 전환 강력 고려!
  - 모멘텀 약화 +1.5% 이상 → 상승세 둔화, 전환 준비
  - 하락 패턴 감지 (Lower Highs) → BEAR 신호

[WARNING] BEAR 포지션 중 반등 신호:
  - 고점 대비 하락폭 축소 (예: -3% → -1%) → BULL 전환 고려
  - 상승 패턴 감지 (Higher Lows) → BULL 신호

당신의 역할:
1. **과거 학습 패턴을 우선 참고** - 노이즈인지 진짜 신호인지 판단!
2. "추세가 곧 꺾일 징후"를 선제적으로 포착
3. **손실 전에 미리** 방향 전환을 감지
4. 빠르면서도 정확한 타이밍 (성급하지도, 늦지도 않게)

목표: 큰 수익 확보 후 손실 전에 전환!
예시:
- SOXL +10% → 고점 대비 -2.3% 하락 감지 → BEAR 전환 → 손실 회피
- SOXS +8% → 하락세 둔화 감지 → BULL 전환 → 반등 수익
"""
            })

            print(f"[DEBUG] current_direction: {self.current_llm_direction}")
            print(f"[DEBUG] ensemble_analyzer.analyze_sequential 호출 전")
            analysis = self.ensemble_analyzer.analyze_sequential(
                market_data=market_data,
                trade_history=recent_trades,
                meta_insights=enhanced_insights
            )
            print(f"[DEBUG] ensemble_analyzer.analyze_sequential 호출 완료")

            if analysis and analysis.get('final_decision'):
                #  LLM 응답 검증 - 빈 응답 차단 
                reasoning = analysis.get('reasoning', '')
                confidence = analysis.get('final_confidence', 0)

                print(f"[DEBUG] LLM 응답 검증 중...")
                print(f"[DEBUG] reasoning 길이: {len(reasoning)} chars")
                print(f"[DEBUG] confidence: {confidence}%")

                # 빈 응답 또는 너무 짧은 응답 차단 + 자동 복구
                if not reasoning or len(reasoning) < 20:
                    print(f"[ERROR] LLM 응답이 비정상적으로 짧습니다: '{reasoning}'")
                    print(f"[ERROR] 응답 길이: {len(reasoning)} chars (최소 20 필요)")
                    print(f"[SAFETY] 거래 중단 - LLM 응답 불충분")

                    #  자동 복구 시도 
                    if not hasattr(self, '_llm_failure_count'):
                        self._llm_failure_count = 0
                        self._last_recovery_time = 0

                    self._llm_failure_count += 1
                    current_time = time.time()

                    # 연속 실패 3회 이상 && 마지막 복구 시도로부터 10분 경과
                    if self._llm_failure_count >= 3 and (current_time - self._last_recovery_time) > 600:
                        print(f"[AUTO_RECOVERY] LLM 연속 실패 {self._llm_failure_count}회 - 자동 복구 시작")
                        self._last_recovery_time = current_time

                        if self.auto_recovery_on_llm_failure():
                            print("[AUTO_RECOVERY] 복구 성공 - 카운터 초기화")
                            self._llm_failure_count = 0
                        else:
                            print("[AUTO_RECOVERY] 복구 실패 - 다음 사이클 계속 시도")
                    else:
                        if self._llm_failure_count < 3:
                            print(f"[INFO] LLM 실패 카운트: {self._llm_failure_count}/3 (3회 도달 시 자동 복구)")
                        else:
                            print(f"[INFO] 마지막 복구 시도로부터 {int((current_time - self._last_recovery_time)/60)}분 경과 (10분 대기 필요)")

                    return {'signal': 'HOLD', 'confidence': 0, 'reasoning': 'LLM 응답 불충분 - 거래 중단'}

                # 신뢰도 검증
                if confidence < self.min_confidence:
                    print(f"[INFO] 신뢰도 부족: {confidence}% < {self.min_confidence}%")

                self.stats['successful_analyses'] += 1

                #  LLM 성공 시 실패 카운터 초기화 
                if hasattr(self, '_llm_failure_count'):
                    if self._llm_failure_count > 0:
                        print(f"[OK] LLM 정상 복구 - 실패 카운터 초기화 (이전: {self._llm_failure_count}회)")
                    self._llm_failure_count = 0

                # final_decision (BUY/SELL/HOLD) → signal (BULL/BEAR/HOLD) 변환
                decision_to_signal = {
                    'BUY': 'BULL',
                    'SELL': 'BEAR',
                    'HOLD': 'HOLD'
                }

                print(f"[OK] LLM 응답 검증 통과")
                return {
                    'signal': decision_to_signal.get(analysis.get('final_decision', 'HOLD'), 'HOLD'),
                    'confidence': confidence,
                    'reasoning': reasoning,
                    'predicted_trend': ''
                }

        except Exception as e:
            print(f"[ERROR] LLM 분석 실패: {e}")
            print("[자동 전환] Fallback 전략 사용")

            # LLM 실패 시에도 fallback 전략 사용
            if len(price_history) < 5:
                return {'signal': 'HOLD', 'confidence': 0, 'reasoning': '데이터 부족'}

            recent_prices = price_history[-5:]
            price_change_pct = ((current_price - recent_prices[0]) / recent_prices[0]) * 100
            upward_moves = sum(1 for i in range(1, len(recent_prices)) if recent_prices[i] > recent_prices[i-1])
            momentum_strength = (upward_moves / (len(recent_prices) - 1)) * 100

            signal = 'HOLD'
            confidence = 50
            reasoning = f"가격 변화: {price_change_pct:.2f}%, 모멘텀: {momentum_strength:.0f}%"

            if price_change_pct > 0.5 and momentum_strength >= 75:
                signal = 'BULL'
                confidence = min(85, 60 + int(price_change_pct * 10))
                reasoning = f"상승 추세 감지 (+{price_change_pct:.2f}%, 모멘텀 {momentum_strength:.0f}%)"
            elif price_change_pct < -0.5 and momentum_strength <= 25:
                signal = 'BEAR'
                confidence = min(85, 60 + int(abs(price_change_pct) * 10))
                reasoning = f"하락 추세 감지 ({price_change_pct:.2f}%, 모멘텀 {momentum_strength:.0f}%)"
            elif abs(price_change_pct) > 0.3:
                signal = 'BULL' if price_change_pct > 0 else 'BEAR'
                confidence = 65
                reasoning = f"약한 추세 ({price_change_pct:.2f}%)"

            return {'signal': signal, 'confidence': confidence, 'reasoning': reasoning, 'predicted_trend': signal}

    def execute_llm_strategy(self):
        """
        LLM 기반 전략 실행 (메인 로직)

        [핵심 로직]
        1. 현재 시장 상황 파악
        2. LLM 14b × 2 병렬 분석
        3. 추세돌파 판단
        4. 포지션 진입/청산/전환 결정
        5. 거래 실행 및 학습
        """
        print("\n" + "="*80)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] LLM 전략 실행")
        print("="*80)

        # 1. 포지션 확인 (잔고 조회는 생략)
        positions = self.get_positions()

        print(f"\n[계좌 현황]")
        print(f"  [INFO] 잔고 조회 건너뜀 - 포지션 기반 분석")

        current_position = None
        current_pnl_pct = 0
        current_price = 40.0  # 기본값

        #  중복 매수 방지 - 포지션 상세 정보 저장 
        held_symbols = set()

        try:
            if positions:
                pos = positions[0]
                current_position = pos['symbol']
                current_pnl_pct = pos['pnl_pct']
                held_symbols.add(current_position)  # 보유 중인 종목 기록

                print(f"  보유: {current_position} {pos['qty']}주")
                print(f"  손익: {current_pnl_pct:+.2f}%")
                print(f"  [SAFETY] 중복 매수 방지 활성화 - {current_position} 재매수 차단")

                # 가격 히스토리 업데이트
                current_price = pos['current_price']
                print(f"  [DEBUG] 현재 가격: ${current_price:.2f}")
                self.price_history_1m.append(current_price)
                if len(self.price_history_1m) > self.max_history:
                    self.price_history_1m.pop(0)

            else:
                print(f"  보유: 없음")
                # 포지션이 없으면 FMP로 실시간 가격 조회
                print(f"\n[실시간 시장 데이터 수집]")
                soxl_price = self.get_realtime_price('SOXL')
                soxs_price = self.get_realtime_price('SOXS')

                # SOXL을 기본으로 사용 (분석용)
                current_price = soxl_price
                self.price_history_1m.append(current_price)
                if len(self.price_history_1m) > self.max_history:
                    self.price_history_1m.pop(0)

                print(f"  [가격 업데이트] SOXL: ${soxl_price:.2f}, SOXS: ${soxs_price:.2f}")

            # 첫 실행 시 히스토리 채우기 (최소 10개 필요)
            if len(self.price_history_1m) < 10:
                print(f"  [가격 히스토리 생성 중: {len(self.price_history_1m)}/10개]")
                # 현재 가격을 기준으로 약간의 변동을 준 더미 데이터 생성
                while len(self.price_history_1m) < 10:
                    self.price_history_1m.insert(0, current_price * (1 + (len(self.price_history_1m) - 5) * 0.001))
                print(f"  [가격 히스토리 준비 완료: 10개]")

            print(f"  [가격 히스토리: {len(self.price_history_1m)}개]")
        except Exception as e:
            print(f"[ERROR] 계좌 현황 처리 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return

        # 1.5. 트레일링 스탑 체크 (자동매매 모드)
        if current_position:
            print(f"\n[리스크 관리 - 트레일링 스탑]")

            # 최고 PNL 갱신
            if current_pnl_pct > self.max_pnl:
                self.max_pnl = current_pnl_pct
                print(f"   최고 PNL 갱신: {self.max_pnl:.2f}%")

            # 최고 PNL에 따라 손절선 상향 조정 (백테스팅 최적화)
            old_stop = self.trailing_stop_loss
            if self.max_pnl >= 20.0:
                self.trailing_stop_loss = 12.0  # +20% 찍으면 손절선 +12% (15% 수익 보장)
            elif self.max_pnl >= 10.0:
                self.trailing_stop_loss = 5.0  # +10% 찍으면 손절선 +5% (8% 수익 보장)
            elif self.max_pnl >= 5.0:
                self.trailing_stop_loss = 1.0  # +5% 찍으면 손절선 +1% (4% 수익 보장)
            else:
                self.trailing_stop_loss = -3.5  # 초기 -3.5% (백테스팅 최적)

            if old_stop != self.trailing_stop_loss:
                print(f"  🔼 손절선 상향: {old_stop:.1f}% → {self.trailing_stop_loss:.1f}%")

            # 트레일링 스탑 체크
            if current_pnl_pct < self.trailing_stop_loss:
                print(f"  🚨 트레일링 스탑 발동!")
                print(f"     현재 PNL: {current_pnl_pct:.2f}% < 손절선: {self.trailing_stop_loss:.1f}%")
                print(f"     최고 PNL: {self.max_pnl:.2f}%")

                # 실제 전량 매도 실행
                sell_result = self.sell_all(current_position)

                if not sell_result['success']:
                    print(f"   매도 실패: {sell_result['message']}")
                    print("  → 다음 사이클에 재시도")
                    return

                # 거래 기록
                timing_eval = self._evaluate_timing(current_pnl_pct, 0)

                trade_record = {
                    'type': 'SELL',
                    'symbol': current_position,
                    'pnl_pct': current_pnl_pct,
                    'reason': 'TRAILING_STOP',
                    'timestamp': datetime.now().isoformat(),

                    # [NEW] 타이밍 학습 메트릭
                    'entry_peak': self.entry_timing_info.get('entry_peak'),
                    'entry_decline_from_peak': self.entry_timing_info.get('entry_decline_from_peak'),
                    'entry_pattern': self.entry_timing_info.get('entry_pattern'),
                    'exit_decline_from_peak': 0,
                    'timing_evaluation': timing_eval['evaluation'],
                    'timing_score': timing_eval['score'],
                    'timing_note': timing_eval['note']
                }
                self.all_trades.append(trade_record)
                self.save_trade_history()

                # [NEW] 타이밍 패턴 학습 업데이트
                self.update_timing_insights()

                # 통계
                self.stats['total_trades'] += 1
                self.stats['losses'] += 1
                self.stats['loss_streak'] += 1
                self.stats['win_streak'] = 0

                # LLM 방향 초기화
                self.current_llm_direction = None

                # 트레일링 스탑 초기화
                self.trailing_stop_loss = -3.5
                self.max_pnl = -999.0

                print("="*80)
                return

            else:
                print(f"  현재 손익: {current_pnl_pct:+.2f}%")
                print(f"  트레일링 스탑: {self.trailing_stop_loss:.1f}% (최고 PNL: {self.max_pnl:.2f}%)")
                print(f"  전략: LLM이 방향 전환 징후를 감지할 때까지 보유 (큰 추세 포착)")

        # 2. LLM 분석 (핵심!)
        print("\n[LLM 분석 시작]")
        print("14b × 2 병렬 앙상블 실행 중...")
        print(f"[DEBUG] 가격 히스토리 개수: {len(self.price_history_1m)}")
        print(f"[DEBUG] 현재 가격: ${self.price_history_1m[-1] if self.price_history_1m else 40.0:.2f}")

        try:
            llm_analysis = self.analyze_market_with_llm(
                current_price=self.price_history_1m[-1] if self.price_history_1m else 40.0,
                price_history=self.price_history_1m
            )
            print(f"[DEBUG] LLM 분석 완료")
        except Exception as e:
            print(f"[ERROR] LLM 분석 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return

        print(f"\n[LLM 분석 결과]")
        print(f"  신호: {llm_analysis['signal']}")
        print(f"  신뢰도: {llm_analysis['confidence']}%")
        print(f"  이유: {llm_analysis['reasoning'][:100]}...")

        # 3. 신호에 따른 행동 결정
        signal = llm_analysis['signal']
        confidence = llm_analysis['confidence']

        # 신뢰도가 낮으면 보류
        if confidence < self.min_confidence:
            print(f"\n[보류] 신뢰도 부족 ({confidence}% < {self.min_confidence}%)")
            return

        # 신호 → 종목 매핑
        signal_to_symbol = {'BULL': 'SOXL', 'BEAR': 'SOXS'}
        target_symbol = signal_to_symbol.get(signal)

        #  피라미딩 체크 (같은 종목 추가 매수) 
        pyramiding_qty = None
        if target_symbol and target_symbol in held_symbols:
            # 같은 종목 보유 중 → 피라미딩 가능성 체크
            if confidence >= 75 and target_symbol in self.pyramiding_count:
                current_count = self.pyramiding_count[target_symbol]
                if current_count < len(self.pyramiding_quantities):
                    pyramiding_qty = self.pyramiding_quantities[current_count]
                    print(f"\n[피라미딩 기회!] {target_symbol} 추가 매수")
                    print(f"  신뢰도: {confidence}% (≥75%)")
                    print(f"  현재: {current_count}차 매수 완료")
                    print(f"  추가: {pyramiding_qty}주 (총 {current_count + 1}차)")
                else:
                    print(f"\n[피라미딩 한계] {target_symbol} 최대 매수 횟수 도달")
                    print(f"  현재: {current_count}차 (최대 {len(self.pyramiding_quantities)}차)")
                    return
            else:
                print(f"\n[SAFETY] 중복 매수 차단")
                print(f"  신호: {signal} → {target_symbol}")
                print(f"  신뢰도: {confidence}% (피라미딩 최소: 75%)")
                print(f"  → 포지션 전환 신호 대기")
                return

        # 4. 포지션 전환 결정 (LLM이 방향 전환 징후를 감지했는가?)
        should_switch = False

        # LLM 방향 추적
        if self.current_llm_direction is None:
            # 첫 실행 - 현재 포지션 기준으로 방향 설정
            if current_position == 'SOXL':
                self.current_llm_direction = 'BULL'
            elif current_position == 'SOXS':
                self.current_llm_direction = 'BEAR'
            print(f"\n[LLM 방향 추적 시작] 현재 방향: {self.current_llm_direction}")

        if current_position:
            # LLM이 방향 전환을 감지했는가?
            #  HOLD 신호는 방향 전환이 아님 (현재 포지션 유지)
            if signal != self.current_llm_direction and signal != 'HOLD':
                # [안전장치] 수수료 + 노이즈 필터
                FEE_RATE = 0.25  # KIS 해외주식 수수료 0.25%
                ROUND_TRIP_FEE = FEE_RATE * 2  # 왕복 0.5%
                MIN_PROFIT_FOR_SWITCH = 1.0  # 최소 1% 수익 시 전환 (수수료 여유)

                # 수익 중 전환 -  빠른 추세 전환 우선 
                if current_pnl_pct > 0:
                    # [PRIORITY 1] 신뢰도 높음 → 즉시 전환 (수익 무관)
                    if confidence >= 65:
                        should_switch = True
                        print(f"\n[ 빠른 추세 전환!] 고신뢰도")
                        print(f"  이전: {self.current_llm_direction} → 새: {signal}")
                        print(f"  신뢰도: {confidence}% (≥65%)")
                        print(f"  수익: {current_pnl_pct:+.2f}%")
                        print(f"  → LLM 판단 신뢰 - 즉시 전환")

                    # [PRIORITY 2] 충분한 수익 → 전환 (신뢰도 낮아도 OK)
                    elif current_pnl_pct >= MIN_PROFIT_FOR_SWITCH:
                        should_switch = True
                        net_profit = current_pnl_pct - ROUND_TRIP_FEE
                        print(f"\n[ 빠른 추세 전환!] 충분한 수익")
                        print(f"  이전: {self.current_llm_direction} → 새: {signal}")
                        print(f"  수익: {current_pnl_pct:+.2f}% (실질: {net_profit:+.2f}%)")
                        print(f"  신뢰도: {confidence}%")
                        print(f"  → 수익 확보 + 방향 전환")

                    # [PRIORITY 3] 둘 다 애매 → 보수적 대기
                    else:
                        should_switch = False
                        print(f"\n[HOLD] 신호 약함 - 관망")
                        print(f"  수익: {current_pnl_pct:+.2f}% (< {MIN_PROFIT_FOR_SWITCH}%)")
                        print(f"  신뢰도: {confidence}% (< 65%)")
                        print(f"  → 더 강한 신호 대기")

                # 손실 중 전환 - 손실 차단 우선
                elif current_pnl_pct < 0:
                    should_switch = True
                    print(f"\n[ 손실 차단 전환!]")
                    print(f"  이전 방향: {self.current_llm_direction}")
                    print(f"  새 방향: {signal}")
                    print(f"  현재 손익: {current_pnl_pct:+.2f}%")
                    print(f"  LLM 신뢰도: {confidence}%")
                    print(f"  → 손실 차단 + 포지션 전환: {current_position} → {target_symbol}")

                else:
                    # PNL = 0
                    should_switch = True
                    print(f"\n[ 방향 전환 감지!]")
                    print(f"  → 포지션 전환: {current_position} → {target_symbol}")
            else:
                print(f"\n[포지션 유지]")
                print(f"  방향: {self.current_llm_direction} (변화 없음)")
                print(f"  현재 손익: {current_pnl_pct:+.2f}%")
                print(f"  전략: 추세가 계속되므로 보유 (큰 수익 추구)")

        # 5. 포지션 전환 실행 (자동매매)
        if should_switch:
            print(f"\n[포지션 전환 실행]")
            print(f"  현재: {current_position} (손익 {current_pnl_pct:+.2f}%)")
            print(f"  전환: {target_symbol} ({signal})")

            # 5-1. 기존 포지션 청산
            if current_position:
                print(f"\n[STEP 1/2] {current_position} 전량 매도")
                sell_result = self.sell_all(current_position)

                if not sell_result['success']:
                    print(f"   매도 실패: {sell_result['message']}")
                    return

                print(f"   매도 성공: {sell_result.get('order_no')}")

                # 피라미딩 카운터 리셋
                if current_position in self.pyramiding_count:
                    del self.pyramiding_count[current_position]
                    print(f"  [피라미딩 리셋] {current_position} 카운터 초기화")

            # 5-2. 새 포지션 진입 (복리 효과 - 잔고 기반)
            if target_symbol:
                print(f"\n[STEP 2/2] {target_symbol} 매수 (잔고 기반 수량)")
                #  복리 효과: quantity=None → 잔고 기반 자동 계산
                buy_result = self.place_order(target_symbol, 'BUY', quantity=None, price=None)

                if not buy_result['success']:
                    print(f"   매수 실패: {buy_result['message']}")
                    return

                print(f"   매수 성공: {buy_result.get('order_no')}")

                # 피라미딩 카운터 초기화 (1회 매수 완료)
                self.pyramiding_count[target_symbol] = 1
                print(f"  [피라미딩 시작] {target_symbol} 1차 매수 완료 (10주)")

            print(f"\n[완료] 포지션 전환: {current_position} → {target_symbol}")

        # 6. 피라미딩 추가 매수 실행
        elif pyramiding_qty is not None:
            print(f"\n[피라미딩 추가 매수 실행]")
            print(f"  종목: {target_symbol}")
            print(f"  수량: {pyramiding_qty}주")

            buy_result = self.place_order(target_symbol, 'BUY', quantity=pyramiding_qty, price=None)

            if buy_result['success']:
                print(f"   추가 매수 성공: {buy_result.get('order_no')}")

                # 피라미딩 카운터 증가
                self.pyramiding_count[target_symbol] += 1
                print(f"  [피라미딩] {target_symbol} {self.pyramiding_count[target_symbol]}차 매수 완료")
                print(f"  [누적] {sum(self.pyramiding_quantities[:self.pyramiding_count[target_symbol]])}주 보유 예상")
            else:
                print(f"   추가 매수 실패: {buy_result['message']}")

        # 7. 신규 포지션 진입 (포지션 없을 때) - 복리 효과
        elif current_position is None and target_symbol and not should_switch:
            print(f"\n[신규 포지션 진입]")
            print(f"  종목: {target_symbol}")
            print(f"  신호: {signal} (신뢰도 {confidence}%)")
            print(f"  수량: 잔고 기반 자동 계산 (복리 효과)")

            #  복리 효과: quantity=None → 잔고 기반 자동 계산
            buy_result = self.place_order(target_symbol, 'BUY', quantity=None, price=None)

            if buy_result['success']:
                print(f"   매수 성공: {buy_result.get('order_no')}")

                # 피라미딩 카운터 초기화
                self.pyramiding_count[target_symbol] = 1
                print(f"  [피라미딩 시작] {target_symbol} 1차 매수 완료 (10주)")
            else:
                print(f"   매수 실패: {buy_result['message']}")

        # 6. 신호가 바뀔 때만 텔레그램 알림 (HOLD 제외)
        if signal != self.current_llm_direction and signal != 'HOLD' and target_symbol:
            print(f"\n[신호 변화 감지!]")
            print(f"  이전 신호: {self.current_llm_direction or '없음'}")
            print(f"  새 신호: {signal} (신뢰도: {confidence}%)")
            print(f"  권장 종목: {target_symbol}")
            print(f"  이유: {llm_analysis['reasoning'][:100]}...")

            # 텔레그램 알림 전송
            self.send_trading_signal_notification(
                signal=signal,
                symbol=target_symbol,
                confidence=confidence,
                reasoning=llm_analysis['reasoning'],
                current_position=current_position,
                current_pnl_pct=current_pnl_pct
            )

            # LLM 방향 업데이트 (새 포지션 방향으로)
            self.current_llm_direction = signal
            print(f"  [LLM 방향 업데이트] {self.current_llm_direction}")
        else:
            if signal == self.current_llm_direction:
                print(f"\n[신호 유지] {signal} - 알림 건너뜀 (중복 방지)")
            else:
                print(f"\n[신호 없음] 조건 미충족")

        print("="*80)

        # 통계 출력
        if self.stats['total_trades'] > 0:
            win_rate = self.stats['wins'] / self.stats['total_trades'] * 100
            print(f"\n[통계] 거래: {self.stats['total_trades']} | "
                  f"승률: {win_rate:.1f}% | "
                  f"연승: {self.stats['win_streak']} | "
                  f"LLM 호출: {self.stats['llm_calls']}")

    def run(self, interval_seconds: int = 300):
        """
        자동매매 루프 실행

        Args:
            interval_seconds: 체크 간격 (초) - LLM 분석 시간 고려하여 5분 권장
        """
        print(f"\n[LLM 자동매매 시작]")
        print(f"  체크 간격: {interval_seconds}초 (LLM 분석 시간 포함)")
        print(f"  종료: Ctrl+C\n")

        # 자동 재시작 타이머 초기화
        last_ollama_restart = time.time()
        OLLAMA_RESTART_INTERVAL = 30 * 60  # 30분마다 Ollama 재시작 (CPU 과부하 방지)

        cycle_count = 0
        # [DISABLED] 자동 재시작 비활성화 - Ollama keep_alive로 메모리 관리
        # RESTART_CYCLE = 5

        while True:
            try:
                current_time = time.time()
                cycle_count += 1

                # [DISABLED] 자동 재시작 비활성화
                # - Ollama의 keep_alive=60m 설정으로 메모리 자동 정리
                # - 무한 실행이 더 안정적

                # Ollama 정기 재시작 체크 (30분마다)
                if current_time - last_ollama_restart >= OLLAMA_RESTART_INTERVAL:
                    print("\n" + "=" * 70)
                    print(f"[AUTO_RESTART] {OLLAMA_RESTART_INTERVAL // 3600}시간 경과 → Ollama 자동 재시작")
                    print("=" * 70)
                    try:
                        import subprocess
                        # Ollama 11435 종료
                        subprocess.run(
                            ["powershell", "-Command", "Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force"],
                            timeout=10,
                            capture_output=True
                        )
                        print("[AUTO_RESTART] Ollama 프로세스 종료 완료")
                        time.sleep(3)

                        # Ollama 11435 재시작
                        ps_path = r"C:\Users\user\Documents\코드4\start_ollama_11435.ps1"
                        subprocess.Popen(
                            ["powershell", "-File", ps_path],
                            creationflags=subprocess.CREATE_NEW_CONSOLE
                        )
                        print("[AUTO_RESTART] Ollama 11435 재시작 완료 (GPU 메모리 정리됨)")
                        time.sleep(10)  # Ollama 초기화 대기

                        last_ollama_restart = current_time
                        print(f"[AUTO_RESTART] 다음 재시작: {OLLAMA_RESTART_INTERVAL // 3600}시간 후")
                        print("=" * 70 + "\n")
                    except Exception as restart_error:
                        print(f"[AUTO_RESTART] Ollama 재시작 실패: {restart_error}")
                        print("[AUTO_RESTART] 계속 진행합니다...\n")

                self.execute_llm_strategy()
                print(f"\n다음 실행까지 {interval_seconds}초 대기...")
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
    """메인 실행"""
    # LLM 기반 자동매매 시작
    trader = KISLLMTrader()

    # 자동매매 무한 루프 (5분마다 LLM 분석)
    trader.run(interval_seconds=300)


if __name__ == "__main__":
    main()
