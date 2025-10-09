#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합 멀티 자동매매 시스템 v2.0
- NVIDIA: NVDL/NVDD (KIS API)
- ETH: ETH/USDT (ByBit API)
- 하나의 LLM으로 두 시장 동시 분석
"""

import json
import requests
import time
import hmac
import hashlib
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

# ByBit API 클래스
class ByBitTrader:
    def __init__(self):
        # 실제 API 키 사용
        self.api_key = "KLthPXAti9nWKLOeNX"
        self.api_secret = "ioRLGkzvHcmOoJeJhBkDmG2JJPuSROOEVm2S"
        self.base_url = "https://api.bybit.com"

    def generate_signature(self, params_str, timestamp):
        """ByBit API 서명 생성 (정확한 방식)"""
        sign_str = timestamp + self.api_key + params_str
        return hmac.new(
            self.api_secret.encode('utf-8'),
            sign_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

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

    def get_eth_balance(self):
        """ETH 잔고 조회 (정확한 ByBit API 방식)"""
        try:
            timestamp = str(int(time.time() * 1000))
            params = {"accountType": "UNIFIED", "coin": "ETH"}

            # GET 요청용 쿼리 스트링 생성
            query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
            signature = self.generate_signature(query_string, timestamp)

            headers = {
                "X-BAPI-API-KEY": self.api_key,
                "X-BAPI-SIGN": signature,
                "X-BAPI-SIGN-TYPE": "2",
                "X-BAPI-TIMESTAMP": timestamp,
                "Content-Type": "application/json"
            }

            url = f"{self.base_url}/v5/account/wallet-balance"
            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("retCode") == 0:
                    accounts = data.get("result", {}).get("list", [])
                    for account in accounts:
                        for coin in account.get("coin", []):
                            if coin.get("coin") == "ETH":
                                return float(coin.get("availableToWithdraw", 0))
            else:
                logger.error(f"ByBit ETH 잔고 조회 HTTP 오류: {response.status_code} - {response.text}")
            return 0
        except Exception as e:
            logger.error(f"ByBit ETH 잔고 조회 오류: {e}")
            return 0

    def get_usdt_balance(self):
        """USDT 잔고 조회 (정확한 ByBit API 방식)"""
        try:
            timestamp = str(int(time.time() * 1000))
            params = {"accountType": "UNIFIED", "coin": "USDT"}

            # GET 요청용 쿼리 스트링 생성
            query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
            signature = self.generate_signature(query_string, timestamp)

            headers = {
                "X-BAPI-API-KEY": self.api_key,
                "X-BAPI-SIGN": signature,
                "X-BAPI-SIGN-TYPE": "2",
                "X-BAPI-TIMESTAMP": timestamp,
                "Content-Type": "application/json"
            }

            url = f"{self.base_url}/v5/account/wallet-balance"
            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("retCode") == 0:
                    accounts = data.get("result", {}).get("list", [])
                    for account in accounts:
                        for coin in account.get("coin", []):
                            if coin.get("coin") == "USDT":
                                return float(coin.get("availableToWithdraw", 0))
            else:
                logger.error(f"ByBit USDT 잔고 조회 HTTP 오류: {response.status_code} - {response.text}")
            return 0
        except Exception as e:
            logger.error(f"ByBit USDT 잔고 조회 오류: {e}")
            return 0

    def buy_eth_spot(self, quantity_usdt):
        """ETH 현물 매수 (USDT 기준)"""
        try:
            eth_price = self.get_eth_price()
            if eth_price <= 0:
                return False, "ETH 가격 조회 실패"

            quantity_eth = quantity_usdt / eth_price

            timestamp = str(int(time.time() * 1000))
            params = {
                "category": "spot",
                "symbol": "ETHUSDT",
                "side": "Buy",
                "orderType": "Market",
                "qty": f"{quantity_eth:.6f}"
            }

            headers = {
                "X-BAPI-API-KEY": self.api_key,
                "X-BAPI-TIMESTAMP": timestamp,
                "X-BAPI-SIGN": self.generate_signature(timestamp, params),
                "Content-Type": "application/json"
            }

            url = f"{self.base_url}/v5/order/create"
            response = requests.post(url, json=params, headers=headers)

            if response.status_code == 200:
                data = response.json()
                if data.get("retCode") == 0:
                    logger.info(f"[SUCCESS] ETH {quantity_eth:.6f} (${quantity_usdt:.2f}) 매수 주문 성공")
                    return True, data.get("result", {})
                else:
                    return False, data.get("retMsg", "주문 실패")
            return False, f"HTTP {response.status_code}"

        except Exception as e:
            return False, str(e)

    def sell_eth_spot(self, quantity_eth):
        """ETH 현물 매도"""
        try:
            timestamp = str(int(time.time() * 1000))
            params = {
                "category": "spot",
                "symbol": "ETHUSDT",
                "side": "Sell",
                "orderType": "Market",
                "qty": f"{quantity_eth:.6f}"
            }

            headers = {
                "X-BAPI-API-KEY": self.api_key,
                "X-BAPI-TIMESTAMP": timestamp,
                "X-BAPI-SIGN": self.generate_signature(timestamp, params),
                "Content-Type": "application/json"
            }

            url = f"{self.base_url}/v5/order/create"
            response = requests.post(url, json=params, headers=headers)

            if response.status_code == 200:
                data = response.json()
                if data.get("retCode") == 0:
                    logger.info(f"[SUCCESS] ETH {quantity_eth:.6f} 매도 주문 성공")
                    return True, data.get("result", {})
                else:
                    return False, data.get("retMsg", "주문 실패")
            return False, f"HTTP {response.status_code}"

        except Exception as e:
            return False, str(e)

# 통합 트레이더
class UnifiedMultiTrader:
    def __init__(self):
        print("[START] 통합 멀티 자동매매 시스템 v2.0")
        print("=" * 60)

        # API 초기화
        self.kis = KISTrader()
        self.bybit = ByBitTrader()

        # 심볼 설정
        self.nvidia_symbols = {'nvdl': 'NVDL', 'nvdd': 'NVDD'}

        # 설정
        self.analysis_interval = 120  # 2분
        self.max_position_usd = 50   # 포지션당 $50

        # 가격 히스토리
        self.price_history = {
            'nvdl': [],
            'nvdd': [],
            'eth': []
        }

        # 포지션 추적
        self.positions = {
            'nvdl': None,
            'nvdd': None,
            'eth': None
        }

        # 잔고 추적
        self.usd_balance = 70.92  # KIS 계좌 USD
        self.eth_balance = 0      # ByBit ETH 보유량
        self.usdt_balance = 0     # ByBit USDT 잔고

        print(f"[INFO] 시스템 초기화 완료")
        print(f"[INFO] 분석 주기: {self.analysis_interval}초")
        print(f"[INFO] 최대 포지션: ${self.max_position_usd}")

    def analyze_with_llm(self, market_data):
        """통합 시장 분석 (재시도 포함)"""
        max_retries = 2

        for attempt in range(max_retries):
            try:
                # 통합 프롬프트 생성
                prompt = f"""
시장 데이터 분석:

NVIDIA ETF:
- NVDL (2x Long): ${market_data['nvdl']['price']:.2f} 트렌드:{market_data['nvdl']['trend']}
- NVDD (-2x Short): ${market_data['nvdd']['price']:.2f} 트렌드:{market_data['nvdd']['trend']}

ETH:
- ETH/USDT: ${market_data['eth']['price']:.2f} 트렌드:{market_data['eth']['trend']}

잔고:
- USD: ${self.usd_balance:.2f}
- ETH: {self.eth_balance:.6f}
- USDT: ${self.usdt_balance:.2f}

다음 중 하나를 선택:
1. BUY_NVDL - NVIDIA 상승 전망
2. BUY_NVDD - NVIDIA 하락 전망
3. BUY_ETH - ETH 상승 전망
4. SELL_ETH - ETH 매도
5. HOLD - 대기

답변: [선택만]
"""

                url = "http://localhost:11434/api/generate"
                data = {
                    "model": "qwen2.5:7b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "max_tokens": 100}
                }

                timeout = 15 + (attempt * 10)
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
        """폴백 분석 (LLM 실패시)"""
        try:
            # 간단한 트렌드 기반 로직
            nvdl_trend = market_data['nvdl']['trend']
            nvdd_trend = market_data['nvdd']['trend']
            eth_trend = market_data['eth']['trend']

            if nvdl_trend == "상승" and eth_trend == "상승":
                return "BUY_NVDL"
            elif nvdl_trend == "하락" or nvdd_trend == "상승":
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

            # ByBit 잔고 업데이트
            self.eth_balance = self.bybit.get_eth_balance()
            self.usdt_balance = self.bybit.get_usdt_balance()

        except Exception as e:
            logger.error(f"ETH 데이터 오류: {e}")
            market_data['eth'] = {'price': 0, 'trend': '오류'}

        return market_data

    def execute_trade(self, action, market_data):
        """거래 실행"""
        try:
            if action == "BUY_NVDL" and self.usd_balance >= self.max_position_usd:
                price = market_data['nvdl']['price']
                if price > 0:
                    quantity = int(self.max_position_usd / price)
                    if quantity > 0:
                        success, msg = self.kis.buy_stock('NVDL', quantity)
                        if success:
                            logger.info(f"[TRADE] NVDL {quantity}주 매수 완료")
                            self.positions['nvdl'] = {'quantity': quantity, 'price': price}
                            self.usd_balance -= quantity * price
                            return True

            elif action == "BUY_NVDD" and self.usd_balance >= self.max_position_usd:
                price = market_data['nvdd']['price']
                if price > 0:
                    quantity = int(self.max_position_usd / price)
                    if quantity > 0:
                        success, msg = self.kis.buy_stock('NVDD', quantity)
                        if success:
                            logger.info(f"[TRADE] NVDD {quantity}주 매수 완료")
                            self.positions['nvdd'] = {'quantity': quantity, 'price': price}
                            self.usd_balance -= quantity * price
                            return True

            elif action == "BUY_ETH" and self.usdt_balance >= self.max_position_usd:
                success, msg = self.bybit.buy_eth_spot(self.max_position_usd)
                if success:
                    eth_qty = self.max_position_usd / market_data['eth']['price']
                    self.positions['eth'] = {'quantity': eth_qty, 'price': market_data['eth']['price']}
                    self.usdt_balance -= self.max_position_usd
                    return True

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

        print(f"\n[BALANCE]")
        print(f"  USD (KIS): ${self.usd_balance:.2f}")
        print(f"  ETH (ByBit): {self.eth_balance:.6f}")
        print(f"  USDT (ByBit): ${self.usdt_balance:.2f}")

        print(f"\n[POSITIONS]")
        for key, pos in self.positions.items():
            if pos:
                if key == 'eth':
                    current_value = pos['quantity'] * market_data['eth']['price']
                    pnl = current_value - (pos['quantity'] * pos['price'])
                    print(f"  {key.upper()}: {pos['quantity']:.4f} (${current_value:.2f}, PnL: ${pnl:.2f})")
                else:
                    current_value = pos['quantity'] * market_data[key]['price']
                    pnl = current_value - (pos['quantity'] * pos['price'])
                    print(f"  {key.upper()}: {pos['quantity']}주 (${current_value:.2f}, PnL: ${pnl:.2f})")

        print(f"\n[ANALYSIS] {analysis_result}")

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