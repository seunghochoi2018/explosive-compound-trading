#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 기반 NVIDIA 주식 트레이더 v1.0
- AI가 NVIDIA 주식 시장을 직접 분석하여 거래 결정
- 한투 KIS API를 통한 실시간 자동매매
- 변경 가능한 분석 주기 설정
"""

import time
import json
import os
import requests
import hashlib
import hmac
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

class KISAPIManager:
    """한국투자증권 KIS API 관리자"""

    def __init__(self, app_key: str, app_secret: str, account_num: str, account_code: str):
        self.app_key = app_key
        self.app_secret = app_secret
        self.account_num = account_num
        self.account_code = account_code
        self.base_url = "https://openapi.koreainvestment.com:9443"
        self.access_token = None

        # 토큰 발급
        self._get_access_token()

    def _get_access_token(self):
        """토큰 발급"""
        url = f"{self.base_url}/oauth2/tokenP"
        data = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }

        response = requests.post(url, json=data)
        if response.status_code == 200:
            result = response.json()
            self.access_token = result['access_token']
            print(f"[KIS] 토큰 발급 성공")
        else:
            print(f"[KIS ERROR] 토큰 발급 실패: {response.text}")

    def get_current_price(self, symbol: str) -> float:
        """현재가 조회 (미국 주식)"""
        url = f"{self.base_url}/uapi/overseas-price/v1/quotations/price"
        headers = {
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "HHDFS00000300"  # 미국 주식 현재가
        }
        params = {
            "AUTH": "",
            "EXCD": "NAS",  # NASDAQ
            "SYMB": symbol
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            if data['rt_cd'] == '0':
                return float(data['output']['last'])
        return 0.0

    def get_account_balance(self) -> Dict:
        """계좌 잔고 조회"""
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-psbl-order"
        headers = {
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "TTTC8434R"
        }
        params = {
            "CANO": self.account_num,
            "ACNT_PRDT_CD": self.account_code,
            "PDNO": "",
            "ORD_UNPR": "",
            "ORD_DVSN": "01",
            "CMA_EVLU_AMT_ICLD_YN": "Y",
            "OVRS_ICLD_YN": "N"
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            if data['rt_cd'] == '0':
                return {
                    'cash_balance': float(data['output'].get('ord_psbl_cash', 0)),
                    'total_balance': float(data['output'].get('tot_evlu_amt', 0))
                }
        return {'cash_balance': 0, 'total_balance': 0}

    def place_order(self, symbol: str, side: str, quantity: int, price: float = None) -> bool:
        """주문 실행"""
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/order"

        # 시장가/지정가 결정
        ord_dvsn = "00" if price is None else "01"  # 00: 시장가, 01: 지정가

        headers = {
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "JTTT1002U" if side == "BUY" else "JTTT1006U"
        }

        data = {
            "CANO": self.account_num,
            "ACNT_PRDT_CD": self.account_code,
            "OVRS_EXCG_CD": "NASD",  # NASDAQ
            "PDNO": symbol,
            "ORD_QTY": str(quantity),
            "OVRS_ORD_UNPR": str(price) if price else "0",
            "ORD_DVSN": ord_dvsn
        }

        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            if result['rt_cd'] == '0':
                print(f"[KIS] {side} 주문 성공: {quantity}주 @ ${price}")
                return True

        print(f"[KIS ERROR] 주문 실패: {response.text}")
        return False

class LLMStockAnalyzer:
    """LLM 기반 주식 시장 분석기"""

    def __init__(self, model_name: str = "qwen2.5:7b"):
        self.model_name = model_name
        self.ollama_url = "http://localhost:11434/api/generate"

    def analyze_market(self, symbol: str, current_price: float, price_history: List[float]) -> Dict:
        """시장 분석"""
        # 가격 변화율 계산
        price_changes = []
        if len(price_history) > 1:
            for i in range(1, len(price_history)):
                change = ((price_history[i] - price_history[i-1]) / price_history[i-1]) * 100
                price_changes.append(f"{change:.2f}%")

        # LLM 프롬프트 구성
        prompt = f"""
당신은 NVIDIA 주식 전문 AI 트레이더입니다. 다음 시장 데이터를 분석하여 거래 결정을 내리세요.

[현재 시장 상황]
- 종목: {symbol}
- 현재가: ${current_price}
- 최근 가격 흐름: {price_changes[-10:] if price_changes else 'N/A'}
- 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

[분석 요청]
NVIDIA 주식의 현재 상황을 종합적으로 분석하여 다음을 제공하세요:

1. 매수 신호 강도 (0-100)
2. 매도 신호 강도 (0-100)
3. 분석 신뢰도 (0-100)
4. 근거 (구체적인 이유)

다음 JSON 형식으로 응답하세요:
{{
    "buy_signal": 65,
    "sell_signal": 35,
    "confidence": 80,
    "reasoning": "NVIDIA 주가가 최근 AI 시장 호재로 상승 추세를 보이고 있으며..."
}}
"""

        try:
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '')

                # JSON 파싱 시도
                try:
                    # JSON 부분만 추출
                    start_idx = response_text.find('{')
                    end_idx = response_text.rfind('}') + 1
                    if start_idx != -1 and end_idx != 0:
                        json_str = response_text[start_idx:end_idx]
                        analysis = json.loads(json_str)

                        return {
                            'buy_signal': analysis.get('buy_signal', 0),
                            'sell_signal': analysis.get('sell_signal', 0),
                            'confidence': analysis.get('confidence', 0),
                            'reasoning': analysis.get('reasoning', '분석 실패')
                        }
                except:
                    pass

        except Exception as e:
            print(f"[LLM ERROR] 분석 오류: {e}")

        return {
            'buy_signal': 0,
            'sell_signal': 0,
            'confidence': 0,
            'reasoning': '분석 실패'
        }

class NVIDIAStockTrader:
    """NVIDIA 주식 자동매매 시스템"""

    def __init__(self, analysis_interval: int = 60):
        print("=== NVIDIA 주식 자동매매 트레이더 v1.0 ===")
        print("AI가 NVIDIA 주식을 분석하는 자동화 시스템")

        # 설정 로드
        self.config = self.load_config()

        # KIS API 초기화
        self.api = KISAPIManager(
            app_key=self.config['kis_app_key'],
            app_secret=self.config['kis_app_secret'],
            account_num=self.config['account_num'],
            account_code=self.config['account_code']
        )

        # LLM 분석기 초기화
        self.llm_analyzer = LLMStockAnalyzer()

        # 거래 설정
        self.symbol = "NVDA"
        self.analysis_interval = analysis_interval  # 분석 주기 (초)
        self.position_size_usd = 1000  # 포지션 크기 ($)

        # 상태 관리
        self.position = None  # "BUY" or None
        self.position_quantity = 0
        self.entry_price = None
        self.entry_time = None
        self.price_history = []
        self.last_analysis_time = 0

        # 리스크 관리
        self.stop_loss_pct = -5.0    # -5% 손절
        self.take_profit_pct = 10.0  # +10% 익절
        self.min_confidence = 70     # 최소 신뢰도

        print(f"[INIT] 종목: {self.symbol}")
        print(f"[INIT] 분석 주기: {self.analysis_interval}초")
        print(f"[INIT] 포지션 크기: ${self.position_size_usd}")

    def load_config(self) -> Dict:
        """설정 파일 로드"""
        config_file = "nvidia_config.json"

        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # 기본 설정 생성
            default_config = {
                "kis_app_key": "YOUR_KIS_APP_KEY",
                "kis_app_secret": "YOUR_KIS_APP_SECRET",
                "account_num": "YOUR_ACCOUNT_NUMBER",
                "account_code": "01"
            }

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)

            print(f"[CONFIG] {config_file} 파일을 생성했습니다. API 키를 설정하세요.")
            return default_config

    def update_analysis_interval(self, interval: int):
        """분석 주기 업데이트"""
        self.analysis_interval = interval
        print(f"[CONFIG] 분석 주기 변경: {interval}초")

    def get_current_price(self) -> float:
        """현재가 조회"""
        return self.api.get_current_price(self.symbol)

    def calculate_position_size(self, price: float) -> int:
        """포지션 크기 계산 (주식 수)"""
        return max(1, int(self.position_size_usd / price))

    def execute_buy_order(self, price: float) -> bool:
        """매수 주문 실행"""
        quantity = self.calculate_position_size(price)

        if self.api.place_order(self.symbol, "BUY", quantity):
            self.position = "BUY"
            self.position_quantity = quantity
            self.entry_price = price
            self.entry_time = datetime.now()

            print(f"[BUY] {quantity}주 매수 @ ${price:.2f}")
            return True

        return False

    def execute_sell_order(self) -> bool:
        """매도 주문 실행"""
        if self.position_quantity > 0:
            current_price = self.get_current_price()

            if self.api.place_order(self.symbol, "SELL", self.position_quantity):
                pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100
                pnl_usd = (current_price - self.entry_price) * self.position_quantity

                print(f"[SELL] {self.position_quantity}주 매도 @ ${current_price:.2f}")
                print(f"[P&L] 수익률: {pnl_pct:.2f}%, 수익: ${pnl_usd:.2f}")

                # 포지션 초기화
                self.position = None
                self.position_quantity = 0
                self.entry_price = None
                self.entry_time = None

                return True

        return False

    def check_risk_management(self, current_price: float) -> bool:
        """리스크 관리 체크"""
        if not self.position or not self.entry_price:
            return False

        pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100

        # 손절 체크
        if pnl_pct <= self.stop_loss_pct:
            print(f"[STOP_LOSS] 손절 실행: {pnl_pct:.2f}%")
            return self.execute_sell_order()

        # 익절 체크
        if pnl_pct >= self.take_profit_pct:
            print(f"[TAKE_PROFIT] 익절 실행: {pnl_pct:.2f}%")
            return self.execute_sell_order()

        return False

    def make_trading_decision(self, analysis: Dict, current_price: float) -> Optional[str]:
        """거래 결정"""
        buy_signal = analysis.get('buy_signal', 0)
        sell_signal = analysis.get('sell_signal', 0)
        confidence = analysis.get('confidence', 0)

        print(f"[LLM] 매수신호: {buy_signal}, 매도신호: {sell_signal}, 신뢰도: {confidence}")
        print(f"[LLM] 근거: {analysis.get('reasoning', 'N/A')}")

        # 신뢰도 체크
        if confidence < self.min_confidence:
            print(f"[SKIP] 신뢰도 부족: {confidence} < {self.min_confidence}")
            return None

        # 거래 결정
        if buy_signal > sell_signal and buy_signal >= 60:
            if not self.position:
                return "BUY"
        elif sell_signal > buy_signal and sell_signal >= 60:
            if self.position:
                return "SELL"

        return None

    def execute_decision(self, decision: str, current_price: float):
        """거래 결정 실행"""
        if decision == "BUY":
            self.execute_buy_order(current_price)
        elif decision == "SELL":
            self.execute_sell_order()

    def print_status(self, current_price: float):
        """현재 상태 출력"""
        balance = self.api.get_account_balance()

        print(f"\n[STATUS] {self.symbol}: ${current_price:.2f}")

        if self.position:
            pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100
            pnl_usd = (current_price - self.entry_price) * self.position_quantity
            print(f"[POSITION] {self.position_quantity}주 보유")
            print(f"[P&L] {pnl_pct:+.2f}% (${pnl_usd:+.2f})")
        else:
            print(f"[POSITION] 포지션 없음")

        print(f"[BALANCE] 현금: ${balance['cash_balance']:,.0f}")
        print(f"[BALANCE] 총자산: ${balance['total_balance']:,.0f}")

    def run(self):
        """메인 실행 루프"""
        print(f"\n[RUN] NVIDIA 자동매매 시작")
        print(f"[RUN] 분석 주기: {self.analysis_interval}초")

        try:
            while True:
                current_time = time.time()

                # 분석 주기 체크
                if current_time - self.last_analysis_time >= self.analysis_interval:
                    # 현재가 조회
                    current_price = self.get_current_price()
                    if current_price <= 0:
                        print("[ERROR] 가격 조회 실패")
                        time.sleep(10)
                        continue

                    # 가격 히스토리 업데이트
                    self.price_history.append(current_price)
                    if len(self.price_history) > 100:  # 최근 100개만 유지
                        self.price_history.pop(0)

                    # 리스크 관리 우선 체크
                    if self.check_risk_management(current_price):
                        self.print_status(current_price)
                        time.sleep(5)
                        continue

                    # LLM 분석
                    if len(self.price_history) >= 5:  # 최소 5개 데이터 필요
                        analysis = self.llm_analyzer.analyze_market(
                            self.symbol, current_price, self.price_history
                        )

                        # 거래 결정
                        decision = self.make_trading_decision(analysis, current_price)
                        if decision:
                            self.execute_decision(decision, current_price)

                    # 상태 출력
                    self.print_status(current_price)
                    self.last_analysis_time = current_time

                time.sleep(1)  # 1초 대기

        except KeyboardInterrupt:
            print("\n[STOP] 사용자에 의해 중단됨")
        except Exception as e:
            print(f"\n[ERROR] 오류 발생: {e}")

def main():
    """메인 함수"""
    print("NVIDIA 주식 자동매매 트레이더")
    print("="*50)

    # 분석 주기 설정
    try:
        interval = int(input("분석 주기를 입력하세요 (초, 기본값: 60): ") or "60")
    except:
        interval = 60

    trader = NVIDIAStockTrader(analysis_interval=interval)
    trader.run()

if __name__ == "__main__":
    main()