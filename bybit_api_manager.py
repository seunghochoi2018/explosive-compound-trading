#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
바이비트 API 관리자
실제 계좌 연동 및 거래 기능
"""

import requests
import hashlib
import hmac
import time
import json
import logging
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

class BybitAPIManager:
    """바이비트 API 관리 클래스"""

    def __init__(self, api_key: str = "", api_secret: str = "", testnet: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet

        # API 엔드포인트
        if testnet:
            self.base_url = "https://api-testnet.bybit.com"
        else:
            self.base_url = "https://api.bybit.com"

        self.session = requests.Session()

    def _generate_signature(self, params: str, timestamp: str) -> str:
        """API 서명 생성"""
        if not self.api_secret:
            return ""

        sign_str = timestamp + self.api_key + params
        return hmac.new(
            self.api_secret.encode('utf-8'),
            sign_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def _make_request(self, method: str, endpoint: str, params: dict = None) -> dict:
        """API 요청 실행"""
        if params is None:
            params = {}

        timestamp = str(int(time.time() * 1000))

        if method.upper() == "GET":
            query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
        else:
            query_string = json.dumps(params) if params else ""

        signature = self._generate_signature(query_string, timestamp)

        headers = {
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-SIGN": signature,
            "X-BAPI-SIGN-TYPE": "2",
            "X-BAPI-TIMESTAMP": timestamp,
            "Content-Type": "application/json"
        }

        url = f"{self.base_url}{endpoint}"

        try:
            if method.upper() == "GET":
                response = self.session.get(url, params=params, headers=headers, timeout=10)
            elif method.upper() == "POST":
                response = self.session.post(url, json=params, headers=headers, timeout=10)
            else:
                raise ValueError(f"지원하지 않는 HTTP 메서드: {method}")

            return response.json()

        except Exception as e:
            return {"retCode": -1, "retMsg": f"API 요청 오류: {e}"}

    def get_account_balance(self) -> Dict:
        """계좌 잔고 조회 - 0.0011 ETH 확인"""
        if not self.api_key:
            return {"retCode": -1, "retMsg": "API 키가 설정되지 않음"}

        # 다양한 계좌 타입 시도
        account_types = ["UNIFIED", "SPOT", "CONTRACT"]

        for account_type in account_types:
            try:
                endpoint = "/v5/account/wallet-balance"
                params = {"accountType": account_type}

                result = self._make_request("GET", endpoint, params)
                logger.info(f"잔고 조회 ({account_type}): {result}")

                if result.get("retCode") == 0:
                    accounts = result.get("result", {}).get("list", [])
                    if accounts:
                        return result

            except Exception as e:
                logger.warning(f"{account_type} 계좌 조회 실패: {e}")
                continue

        return {"retCode": -1, "retMsg": "모든 계좌 타입 조회 실패"}

    def get_positions(self, category: str = "linear") -> Dict:
        """포지션 조회"""
        if not self.api_key:
            return {"retCode": -1, "retMsg": "API 키가 설정되지 않음"}

        endpoint = "/v5/position/list"
        params = {"category": category}

        return self._make_request("GET", endpoint, params)

    def place_order(self, symbol: str, side: str, order_type: str, qty: str,
                   price: str = None, leverage: int = None) -> Dict:
        """주문 실행"""
        if not self.api_key:
            return {"retCode": -1, "retMsg": "API 키가 설정되지 않음"}

        endpoint = "/v5/order/create"

        # ETHUSD는 inverse, ETHUSDT는 linear
        category = "inverse" if symbol.endswith("USD") and not symbol.endswith("USDT") else "linear"

        params = {
            "category": category,
            "symbol": symbol,
            "side": side,
            "orderType": order_type,
            "qty": qty
        }

        if price:
            params["price"] = price

        if leverage:
            # 레버리지 설정 (별도 API 호출 필요)
            self.set_leverage(symbol, leverage)

        return self._make_request("POST", endpoint, params)

    def set_leverage(self, symbol: str, leverage: int) -> Dict:
        """레버리지 설정"""
        if not self.api_key:
            return {"retCode": -1, "retMsg": "API 키가 설정되지 않음"}

        endpoint = "/v5/position/set-leverage"

        # ETHUSD는 inverse, ETHUSDT는 linear
        category = "inverse" if symbol.endswith("USD") and not symbol.endswith("USDT") else "linear"

        params = {
            "category": category,
            "symbol": symbol,
            "buyLeverage": str(leverage),
            "sellLeverage": str(leverage)
        }

        return self._make_request("POST", endpoint, params)

    def close_position(self, symbol: str) -> Dict:
        """포지션 전체 청산"""
        if not self.api_key:
            return {"retCode": -1, "retMsg": "API 키가 설정되지 않음"}

        # ETHUSD는 inverse, ETHUSDT는 linear
        category = "inverse" if symbol.endswith("USD") and not symbol.endswith("USDT") else "linear"

        # 먼저 현재 포지션 조회 (올바른 category로)
        positions = self.get_positions(category)
        if positions.get("retCode") != 0:
            return positions

        for pos in positions.get("result", {}).get("list", []):
            if pos["symbol"] == symbol and float(pos["size"]) > 0:
                side = "Sell" if pos["side"] == "Buy" else "Buy"
                qty = pos["size"]

                return self.place_order(symbol, side, "Market", qty)

        return {"retCode": 0, "retMsg": "청산할 포지션이 없음"}

    def get_market_data(self, symbol: str, interval: str = "15", limit: int = 100) -> Dict:
        """시장 데이터 조회 (공개 API - 인증 불필요)"""
        endpoint = "/v5/market/kline"
        params = {
            "category": "linear",
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }

        # 공개 API는 서명 없이 호출
        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.get(url, params=params, timeout=10)
            return response.json()
        except Exception as e:
            return {"retCode": -1, "retMsg": f"시장 데이터 조회 오류: {e}"}

    def test_connection(self) -> Dict:
        """API 연결 테스트"""
        if not self.api_key:
            # API 키가 없으면 공개 API로 테스트
            return self.get_market_data("BTCUSDT", "1", 1)
        else:
            # API 키가 있으면 계좌 정보로 테스트
            return self.get_account_balance()

def test_api():
    """API 테스트 함수"""
    print("바이비트 API 테스트")
    print("=" * 40)

    # API 키 없이 공개 데이터 테스트
    api = BybitAPIManager()

    print("1. 공개 API 테스트 (BTCUSDT 가격)")
    result = api.get_market_data("BTCUSDT", "1", 1)

    if result.get("retCode") == 0:
        price_data = result["result"]["list"][0]
        print(f"   BTCUSDT 현재가: ${float(price_data[4]):,.2f}")
        print("   공개 API 연결 성공!")
    else:
        print(f"   오류: {result.get('retMsg')}")

    print("\n2. API 키 설정 상태")
    if not api.api_key:
        print("   API 키 미설정 - 시뮬레이션 모드만 사용 가능")
        print("   실거래를 원하시면 API 키를 설정하세요.")
    else:
        print("   API 키 설정됨 - 실거래 가능")

        # 계좌 정보 테스트
        balance = api.get_account_balance()
        if balance.get("retCode") == 0:
            print("   계좌 연결 성공!")
        else:
            print(f"   계좌 연결 실패: {balance.get('retMsg')}")

    print("=" * 40)

if __name__ == "__main__":
    test_api()