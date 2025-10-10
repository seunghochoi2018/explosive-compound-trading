#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합 멀티 자동매매 시스템
- NVIDIA: NVDL/NVDD (KIS API)
- ETH: ETH/USDT (ByBit API)
"""

import json
import requests
import time
import os
from datetime import datetime
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

# KIS API 클래스
class KISTrader:
    def __init__(self):
        self.app_key = "PSi3RlRt3DWtPPKTdYNALowIoeUBgM5mMLYO"
        self.app_secret = "Q7LxW5oIlCeg+doJCkmPDgXw7uy8bjC7ACRQR1GrAzgCF3zH7LziMix/QJgweS+IRU+uM/3GPELXVeOGocKQnHZ+RPeH4bqR1CgFOs9tHmRtGmxCiwt3+1yp7yctt+bBc85eDrIsrX9KfOkrLY+wVuE1tthKYSDyiF2YKrOp/e1PsSD0mdI="
        self.base_url = "https://openapi.koreainvestment.com:9443"
        self.cano = "43113014"
        self.access_token = ""
        self.token_file = "kis_token.json"
        self.account_code = "01"
        self.load_token()

    def load_token(self):
        try:
            with open(self.token_file, 'r') as f:
                data = json.load(f)
            self.access_token = data.get('access_token', '')
            return bool(self.access_token)
        except:
            return False

    def get_us_stock_price(self, symbol):
        try:
            url = f"{self.base_url}/uapi/overseas-price/v1/quotations/price"
            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "authorization": f"Bearer {self.access_token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": "HHDFS00000300",
                "custtype": "P"
            }
            params = {
                "AUTH": "",
                "EXCD": "NAS",
                "SYMB": symbol
            }
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                result = response.json()
                if result.get("rt_cd") == "0":
                    return float(result.get("output", {}).get("last", 0))
            return 0
        except:
            return 0

    def buy_stock(self, symbol, quantity):
        try:
            url = f"{self.base_url}/uapi/overseas-stock/v1/trading/order"
            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "authorization": f"Bearer {self.access_token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": "TTTT1002U",
                "custtype": "P"
            }
            data = {
                "CANO": self.cano,
                "ACNT_PRDT_CD": self.account_code,
                "OVRS_EXCG_CD": "NASD",
                "PDNO": symbol,
                "ORD_QTY": str(quantity),
                "OVRS_ORD_UNPR": "0",
                "ORD_SVR_DVSN_CD": "0",
                "ORD_DVSN": "00"
            }
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                result = response.json()
                return result.get("rt_cd") == "0", result.get("msg1", "")
            return False, "HTTP Error"
        except Exception as e:
            return False, str(e)

# ByBit API 클래스 (기존 코드에서 가져오기)
class ByBitTrader:
    def __init__(self):
        # 실제 API 키로 교체 필요
        self.api_key = "YOUR_BYBIT_API_KEY"
        self.api_secret = "YOUR_BYBIT_API_SECRET"
        self.base_url = "https://api.bybit.com"

    def get_eth_price(self):
        try:
            url = f"{self.base_url}/v5/market/tickers"
            params = {"category": "spot", "symbol": "ETHUSDT"}
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return float(data['result']['list'][0]['lastPrice'])
            return 0
        except:
            return 0

    def buy_eth(self, quantity):
        # ByBit 매수 로직 (실제 API 키 필요)
        logger.info(f"[SIMULATION] ETH {quantity} 매수")
        return True, "Simulated"

# 통합 트레이더
class UnifiedMultiTrader:
    def __init__(self):
        print("[START] 통합 멀티 자동매매 시스템")
        print("=" * 60)

        # API 초기화
        self.kis = KISTrader()
        self.bybit = ByBitTrader()

        # 심볼 설정
        self.nvidia_symbols = {'nvdl': 'NVDL', 'nvdd': 'NVDD'}
        self.eth_symbol = 'ETHUSDT'

        # 설정
        self.analysis_interval = 120  # 2분
        self.max_position_usd = 50   # 포지션당 $50 (작은 금액으로 시작)

        # 가격 히스토리
        self.price_history = {
            'nvdl': [],
            'nvdd': [],
            'eth': []
        }

        # 포지션 추적
        self.positions = {}
        self.balance_usd = 70.92  # 실제 잔고

    def analyze_with_llm(self, market_data):
        """통합 시장 분석"""
        max_retries = 2

        for attempt in range(max_retries):
            try:
                # 통합 프롬프트 생성
                prompt = f"""
다음 시장 데이터를 분석하여 거래 결정을 내려주세요:

NVIDIA ETF:
- NVDL (2x Long): ${market_data['nvdl']['price']:.2f} (트렌드: {market_data['nvdl']['trend']})
- NVDD (-2x Short): ${market_data['nvdd']['price']:.2f} (트렌드: {market_data['nvdd']['trend']})

ETH:
- ETH/USDT: ${market_data['eth']['price']:.2f} (트렌드: {market_data['eth']['trend']})

시장 상관관계를 고려하여 다음 중 선택:
1. BUY_NVDL - NVIDIA 상승 전망
2. BUY_NVDD - NVIDIA 하락 전망
3. BUY_ETH - ETH 상승 전망
4. SELL_ETH - ETH 포지션 정리
5. HOLD - 대기

답변: [선택]
근거: [간단한 설명]
"""

                url = "http://localhost:11434/api/generate"
                data = {
                    "model": "qwen2.5:7b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "max_tokens": 200}
                }

                timeout = 20 + (attempt * 10)
                response = requests.post(url, json=data, timeout=timeout)

                if response.status_code == 200:
                    result = response.json()
                    return result.get('response', 'HOLD')
                else:
                    logger.warning(f"LLM 분석 실패 (시도 {attempt+1})")

            except Exception as e:
                logger.warning(f"LLM 오류 (시도 {attempt+1}): {e}")
                if attempt == max_retries - 1:
                    return self.fallback_analysis(market_data)
                time.sleep(2)

        return self.fallback_analysis(market_data)

    def fallback_analysis(self, market_data):
        """폴백 분석"""
        try:
            # NVIDIA 분석
            nvdl_trend = market_data['nvdl']['trend']
            eth_trend = market_data['eth']['trend']

            # 트렌드 기반 간단한 로직
            if nvdl_trend == "상승" and eth_trend == "상승":
                return "BUY_NVDL"
            elif nvdl_trend == "하락":
                return "BUY_NVDD"
            elif eth_trend == "상승":
                return "BUY_ETH"
            else:
                return "HOLD"
        except:
            return "HOLD"

    def collect_market_data(self):
        """시장 데이터 수집"""
        market_data = {}

        # NVIDIA ETF 가격
        for key, symbol in self.nvidia_symbols.items():
            try:
                price = self.kis.get_us_stock_price(symbol)

                # 히스토리 업데이트
                self.price_history[key].append({
                    'price': price,
                    'timestamp': datetime.now()
                })

                # 최근 5개만 유지
                if len(self.price_history[key]) > 5:
                    self.price_history[key] = self.price_history[key][-5:]

                # 트렌드 계산
                if len(self.price_history[key]) >= 3:
                    prices = [p['price'] for p in self.price_history[key][-3:]]
                    if prices[-1] > prices[0]:
                        trend = "상승"
                    elif prices[-1] < prices[0]:
                        trend = "하락"
                    else:
                        trend = "횡보"
                else:
                    trend = "불명"

                market_data[key] = {'price': price, 'trend': trend}
                logger.info(f"{symbol}: ${price:.2f} ({trend})")

            except Exception as e:
                logger.error(f"{symbol} 데이터 오류: {e}")
                market_data[key] = {'price': 0, 'trend': '오류'}

        # ETH 가격
        try:
            eth_price = self.bybit.get_eth_price()

            self.price_history['eth'].append({
                'price': eth_price,
                'timestamp': datetime.now()
            })

            if len(self.price_history['eth']) > 5:
                self.price_history['eth'] = self.price_history['eth'][-5:]

            # ETH 트렌드
            if len(self.price_history['eth']) >= 3:
                prices = [p['price'] for p in self.price_history['eth'][-3:]]
                if prices[-1] > prices[0]:
                    trend = "상승"
                elif prices[-1] < prices[0]:
                    trend = "하락"
                else:
                    trend = "횡보"
            else:
                trend = "불명"

            market_data['eth'] = {'price': eth_price, 'trend': trend}
            logger.info(f"ETH: ${eth_price:.2f} ({trend})")

        except Exception as e:
            logger.error(f"ETH 데이터 오류: {e}")
            market_data['eth'] = {'price': 0, 'trend': '오류'}

        return market_data

    def execute_trade(self, action, market_data):
        """거래 실행"""
        try:
            if action == "BUY_NVDL":
                price = market_data['nvdl']['price']
                if price > 0:
                    quantity = int(self.max_position_usd / price)
                    if quantity > 0:
                        success, msg = self.kis.buy_stock('NVDL', quantity)
                        if success:
                            logger.info(f"[SUCCESS] NVDL {quantity}주 매수 완료")
                            return True
                        else:
                            logger.error(f"NVDL 매수 실패: {msg}")

            elif action == "BUY_NVDD":
                price = market_data['nvdd']['price']
                if price > 0:
                    quantity = int(self.max_position_usd / price)
                    if quantity > 0:
                        success, msg = self.kis.buy_stock('NVDD', quantity)
                        if success:
                            logger.info(f"[SUCCESS] NVDD {quantity}주 매수 완료")
                            return True
                        else:
                            logger.error(f"NVDD 매수 실패: {msg}")

            elif action == "BUY_ETH":
                eth_price = market_data['eth']['price']
                if eth_price > 0:
                    quantity = self.max_position_usd / eth_price
                    success, msg = self.bybit.buy_eth(quantity)
                    if success:
                        logger.info(f"[SUCCESS] ETH {quantity:.4f} 매수 완료")
                        return True
                    else:
                        logger.error(f"ETH 매수 실패: {msg}")

            elif action == "HOLD":
                logger.info("[HOLD] 대기")
                return True

            return False

        except Exception as e:
            logger.error(f"거래 실행 오류: {e}")
            return False

    def print_status(self, market_data, analysis_result):
        """상태 출력"""
        print("\n" + "="*60)
        print(f"[TIME] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)

        print("[PRICES]")
        print(f"  NVDL: ${market_data['nvdl']['price']:.2f} ({market_data['nvdl']['trend']})")
        print(f"  NVDD: ${market_data['nvdd']['price']:.2f} ({market_data['nvdd']['trend']})")
        print(f"  ETH:  ${market_data['eth']['price']:.2f} ({market_data['eth']['trend']})")

        print(f"\n[ANALYSIS] {analysis_result}")
        print(f"[BALANCE] ${self.balance_usd:.2f}")

    def run(self):
        """메인 실행 루프"""
        logger.info("[START] 통합 트레이더 시작")

        while True:
            try:
                # 1. 시장 데이터 수집
                market_data = self.collect_market_data()

                # 2. LLM 분석
                analysis_result = self.analyze_with_llm(market_data)

                # 3. 상태 출력
                self.print_status(market_data, analysis_result)

                # 4. 거래 실행
                self.execute_trade(analysis_result, market_data)

                # 5. 대기
                logger.info(f"다음 분석까지 {self.analysis_interval}초 대기...")
                time.sleep(self.analysis_interval)

            except KeyboardInterrupt:
                logger.info("사용자 중단")
                break
            except Exception as e:
                logger.error(f"실행 오류: {e}")
                time.sleep(10)

if __name__ == "__main__":
    trader = UnifiedMultiTrader()
    trader.run()