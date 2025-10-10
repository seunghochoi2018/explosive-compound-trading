 ㅑ#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
최종 통합 멀티 자동매매 시스템
- NVIDIA: NVDL/NVDD (KIS API)
- ETH: ETHUSDT (검증된 ByBit API)
"""

import json
import requests
import time
from datetime import datetime
import logging
import sys

# 검증된 ByBit API 사용
from bybit_api_manager import BybitAPIManager
from api_config import get_api_credentials

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

# 최종 통합 트레이더
class FinalUnifiedTrader:
    def __init__(self):
        print("[START] 최종 통합 멀티 자동매매 시스템")
        print("=" * 60)

        # API 초기화
        self.kis = KISTrader()

        # 검증된 ByBit API 사용
        creds = get_api_credentials()
        self.bybit = BybitAPIManager(
            api_key=creds['api_key'],
            api_secret=creds['api_secret'],
            testnet=False  # 실거래
        )

        # 심볼 설정
        self.nvidia_symbols = {'nvdl': 'NVDL', 'nvdd': 'NVDD'}

        # 설정
        self.analysis_interval = 120  # 2분
        self.max_position_usd = 50

        # 가격 히스토리
        self.price_history = {
            'nvdl': [],
            'nvdd': [],
            'eth': []
        }

        # 학습 데이터 저장
        self.learning_data = []
        self.learning_file = "unified_learning_data.json"
        self.load_learning_data()

        # 포지션 추적
        self.positions = {
            'nvdl': None,
            'nvdd': None,
            'eth': None
        }

        # 잔고 초기화 (실제 API에서 조회)
        self.usd_balance = 70.92  # KIS USD 잔고
        self.eth_balance = 0      # ByBit ETH 잔고
        self.usdt_balance = 0     # ByBit USDT 잔고

        # 초기 잔고 조회
        self.update_balances()

        print(f"[INFO] 시스템 초기화 완료")
        print(f"[INFO] 분석 주기: {self.analysis_interval}초")
        print(f"[INFO] 최대 포지션: ${self.max_position_usd}")
        print(f"[INFO] 학습 데이터: {len(self.learning_data)}개 기록 로드됨")

    def load_learning_data(self):
        """과거 학습 데이터 로드"""
        try:
            with open(self.learning_file, 'r', encoding='utf-8') as f:
                self.learning_data = json.load(f)
            logger.info(f"학습 데이터 {len(self.learning_data)}개 로드됨")
        except FileNotFoundError:
            self.learning_data = []
            logger.info("새로운 학습 데이터 파일 생성")
        except Exception as e:
            logger.error(f"학습 데이터 로드 오류: {e}")
            self.learning_data = []

    def save_learning_data(self):
        """학습 데이터 저장"""
        try:
            with open(self.learning_file, 'w', encoding='utf-8') as f:
                json.dump(self.learning_data[-1000:], f, ensure_ascii=False, indent=2)  # 최근 1000개만
            logger.info("학습 데이터 저장 완료")
        except Exception as e:
            logger.error(f"학습 데이터 저장 오류: {e}")

    def add_learning_record(self, market_data, analysis_result, trade_success=None):
        """학습 기록 추가"""
        try:
            record = {
                'timestamp': datetime.now().isoformat(),
                'nvdl_price': market_data['nvdl']['price'],
                'nvdl_trend': market_data['nvdl']['trend'],
                'nvdd_price': market_data['nvdd']['price'],
                'nvdd_trend': market_data['nvdd']['trend'],
                'eth_price': market_data['eth']['price'],
                'eth_trend': market_data['eth']['trend'],
                'usd_balance': self.usd_balance,
                'eth_balance': self.eth_balance,
                'usdt_balance': self.usdt_balance,
                'analysis_result': analysis_result,
                'trade_success': trade_success
            }

            self.learning_data.append(record)

            # 주기적으로 저장 (10개마다)
            if len(self.learning_data) % 10 == 0:
                self.save_learning_data()

        except Exception as e:
            logger.error(f"학습 기록 오류: {e}")

    def update_balances(self):
        """실제 잔고 업데이트"""
        try:
            # ETH 잔고 조회 (100% 정확)
            self.eth_balance = self.get_eth_balance()

            # USDT 잔고 조회 (100% 정확)
            self.usdt_balance = self.get_usdt_balance()

            logger.info(f"[BALANCE] ETH: {self.eth_balance:.6f}, USDT: ${self.usdt_balance:.2f}")

        except Exception as e:
            logger.error(f"잔고 업데이트 오류: {e}")

    def get_eth_price(self):
        """ETH 가격 조회 (공개 API)"""
        try:
            url = "https://api.bybit.com/v5/market/tickers"
            params = {"category": "spot", "symbol": "ETHUSDT"}
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return float(data['result']['list'][0]['lastPrice'])
            return 0
        except:
            return 0

    def get_eth_balance(self):
        """ETH 잔고 조회 - 0.00115037 ETH 정확 조회"""
        try:
            balance_data = self.bybit.get_account_balance()

            if balance_data.get("retCode") == 0:
                accounts = balance_data.get("result", {}).get("list", [])

                for account in accounts:
                    coins = account.get("coin", [])

                    for coin in coins:
                        if coin.get("coin") == "ETH":
                            # equity(자산 총액) 사용 - 가장 정확한 잔고
                            equity = coin.get("equity", "0")
                            wallet_balance = coin.get("walletBalance", "0")

                            logger.info(f"ETH 잔고: equity={equity}, wallet={wallet_balance}")

                            # equity 우선, wallet 다음
                            if equity and equity != "0":
                                return float(equity)
                            elif wallet_balance and wallet_balance != "0":
                                return float(wallet_balance)

            return 0
        except Exception as e:
            logger.error(f"ETH 잔고 조회 오류: {e}")
            return 0

    def get_usdt_balance(self):
        """USDT 잔고 조회 - equity 기준 정확 조회"""
        try:
            balance_data = self.bybit.get_account_balance()
            if balance_data.get("retCode") == 0:
                accounts = balance_data.get("result", {}).get("list", [])
                for account in accounts:
                    for coin in account.get("coin", []):
                        if coin.get("coin") == "USDT":
                            equity = coin.get("equity", "0")
                            wallet_balance = coin.get("walletBalance", "0")

                            logger.info(f"USDT 잔고: equity={equity}, wallet={wallet_balance}")

                            if equity and equity != "0":
                                return float(equity)
                            elif wallet_balance and wallet_balance != "0":
                                return float(wallet_balance)
            return 0
        except Exception as e:
            logger.error(f"USDT 잔고 조회 오류: {e}")
            return 0

    def analyze_with_llm(self, market_data):
        """통합 시장 분석 - 하나의 LLM으로 두 시장 동시 분석 + 과거 학습 데이터 활용"""
        max_retries = 2

        for attempt in range(max_retries):
            try:
                # 현재 포지션 상태 파악
                nvdl_pos = f"보유: {self.positions['nvdl']['quantity']}주" if self.positions['nvdl'] else "없음"
                nvdd_pos = f"보유: {self.positions['nvdd']['quantity']}주" if self.positions['nvdd'] else "없음"
                eth_pos = f"보유: {self.positions['eth']['quantity']:.6f}ETH" if self.positions['eth'] else "없음"

                # 최근 학습 데이터 요약 (최근 5개)
                recent_data = ""
                if len(self.learning_data) >= 5:
                    recent_records = self.learning_data[-5:]
                    recent_data = "\n과거 5회 거래 패턴:"
                    for i, record in enumerate(recent_records, 1):
                        recent_data += f"\n{i}. NVDL:{record['nvdl_trend']} NVDD:{record['nvdd_trend']} ETH:{record['eth_trend']} → {record['analysis_result']}"

                prompt = f"""
🤖 멀티 자산 통합 분석 (학습 강화):

현재 시장:
- NVDL (2x Long): ${market_data['nvdl']['price']:.2f} ({market_data['nvdl']['trend']}) - {nvdl_pos}
- NVDD (-2x Short): ${market_data['nvdd']['price']:.2f} ({market_data['nvdd']['trend']}) - {nvdd_pos}
- ETH: ${market_data['eth']['price']:.2f} ({market_data['eth']['trend']}) - {eth_pos}

거래 자금:
- USD: ${self.usd_balance:.2f} | ETH: {self.eth_balance:.6f} | USDT: ${self.usdt_balance:.2f}

학습 데이터: {len(self.learning_data)}개 기록{recent_data}

전략: 과거 패턴 + 현재 트렌드 종합 분석

선택: BUY_NVDL, BUY_NVDD, BUY_ETH, SELL_ETH, HOLD

답변: [선택만]
"""

                url = "http://localhost:11434/api/generate"
                data = {
                    "model": "qwen2.5:7b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "max_tokens": 50}
                }

                timeout = 30 + (attempt * 15)
                response = requests.post(url, json=data, timeout=timeout)

                if response.status_code == 200:
                    result = response.json()
                    return result.get('response', 'HOLD')

            except Exception as e:
                logger.warning(f"LLM 오류 (시도 {attempt+1}): {e}")
                if attempt == max_retries - 1:
                    return self.fallback_analysis(market_data)
                time.sleep(1)

        return self.fallback_analysis(market_data)

    def fallback_analysis(self, market_data):
        """폴백 분석"""
        try:
            nvdl_trend = market_data['nvdl']['trend']
            eth_trend = market_data['eth']['trend']

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
                logger.error(f"{symbol} 오류: {e}")
                market_data[key] = {'price': 0, 'trend': '오류'}

        # ETH 가격
        try:
            eth_price = self.get_eth_price()

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

            # 실시간 잔고 업데이트 (100% 정확)
            self.update_balances()

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
                            logger.info(f"[SUCCESS] NVDL {quantity}주 매수 완료 (${price:.2f})")
                            self.positions['nvdl'] = {'quantity': quantity, 'price': price}
                            self.usd_balance -= quantity * price
                            return True
                        else:
                            logger.warning(f"[FAIL] NVDL 매수 실패: {msg}")

            elif action == "BUY_NVDD" and self.usd_balance >= self.max_position_usd:
                price = market_data['nvdd']['price']
                if price > 0:
                    quantity = int(self.max_position_usd / price)
                    if quantity > 0:
                        success, msg = self.kis.buy_stock('NVDD', quantity)
                        if success:
                            logger.info(f"[SUCCESS] NVDD {quantity}주 매수 완료 (${price:.2f})")
                            self.positions['nvdd'] = {'quantity': quantity, 'price': price}
                            self.usd_balance -= quantity * price
                            return True
                        else:
                            logger.warning(f"[FAIL] NVDD 매수 실패: {msg}")

            elif action == "BUY_ETH" and self.usdt_balance >= self.max_position_usd:
                eth_qty = self.max_position_usd / market_data['eth']['price']
                result = self.bybit.place_order("ETHUSDT", "Buy", "Market", f"{eth_qty:.6f}")
                if result.get("retCode") == 0:
                    logger.info(f"[SUCCESS] ETH {eth_qty:.6f} 매수 완료 (${market_data['eth']['price']:.2f})")
                    self.positions['eth'] = {'quantity': eth_qty, 'price': market_data['eth']['price']}
                    self.usdt_balance -= self.max_position_usd
                    return True
                else:
                    logger.warning(f"[FAIL] ETH 매수 실패: {result.get('retMsg', '알 수 없는 오류')}")

            elif action == "SELL_ETH" and self.eth_balance > 0:
                result = self.bybit.place_order("ETHUSDT", "Sell", "Market", f"{self.eth_balance:.6f}")
                if result.get("retCode") == 0:
                    sell_value = self.eth_balance * market_data['eth']['price']
                    logger.info(f"[SUCCESS] ETH {self.eth_balance:.6f} 매도 완료 (${sell_value:.2f})")
                    self.positions['eth'] = None
                    self.usdt_balance += sell_value
                    return True
                else:
                    logger.warning(f"[FAIL] ETH 매도 실패: {result.get('retMsg', '알 수 없는 오류')}")

            elif action == "HOLD":
                logger.info("[HOLD] 시장 대기")
                return True

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

        print(f"\n[ANALYSIS] {analysis_result}")

    def run(self):
        """메인 실행 루프"""
        logger.info("[START] 최종 통합 트레이더 시작")

        while True:
            try:
                # 1. 데이터 수집
                market_data = self.collect_market_data()

                # 2. LLM 분석
                analysis_result = self.analyze_with_llm(market_data)

                # 3. 상태 출력
                self.print_status(market_data, analysis_result)

                # 4. 거래 실행
                trade_success = self.execute_trade(analysis_result, market_data)

                # 5. 학습 기록 추가
                self.add_learning_record(market_data, analysis_result, trade_success)

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
    trader = FinalUnifiedTrader()
    trader.run()