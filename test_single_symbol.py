#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
단일 종목 테스트 (Rate Limiting 확인)
"""
import json
import requests
import time

# KIS API 설정
APP_KEY = "PSi3RlRt3DWtPPKTdYNALowIoeUBgM5mMLYO"
APP_SECRET = "Q7LxW5oIlCeg+doJCkmPDgXw7uy8bjC7ACRQR1GrAzgCF3zH7LziMix/QJgweS+IRU+uM/3GPELXVeOGocKQnHZ+RPeH4bqR1Ciwt3+1yp7yctt+bBc85eDrIsrX9KfOkrLY+wVuE1tthKYsDyiF2YKrOp/e1PsSD0mdI="
BASE_URL = "https://openapi.koreainvestment.com:9443"

def load_token():
    """토큰 로드"""
    try:
        with open("kis_token.json", 'r') as f:
            token_data = json.load(f)
            return token_data.get('access_token')
    except Exception as e:
        print(f"[X] 토큰 로드 실패: {e}")
        return None

def test_price(token, symbol, excd="NAS"):
    """현재가 조회 (refresh_kis_token.py와 동일한 로직)"""
    print(f"\n{'='*70}")
    print(f"[TEST] {symbol} @ {excd}")
    print(f"{'='*70}")

    url = f"{BASE_URL}/uapi/overseas-price/v1/quotations/price"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "HHDFS00000300",
        "custtype": "P"
    }

    params = {
        "AUTH": "",
        "EXCD": excd,
        "SYMB": symbol
    }

    print(f"URL: {url}")
    print(f"Headers: {json.dumps({k: v[:20] + '...' if len(v) > 20 else v for k, v in headers.items()}, indent=2)}")
    print(f"Params: {json.dumps(params, indent=2)}")

    try:
        print(f"\n[REQUEST] Sending...")
        response = requests.get(url, headers=headers, params=params, timeout=10)

        print(f"[RESPONSE] HTTP {response.status_code}")
        print(f"Response Text: {response.text}")

        if response.status_code == 200:
            result = response.json()
            rt_cd = result.get("rt_cd")
            msg1 = result.get("msg1", "")

            if rt_cd == "0":
                output = result.get("output", {})
                price = output.get("last", "N/A")
                print(f"\n[SUCCESS] 가격: ${price}")
                return True
            else:
                print(f"\n[FAIL] rt_cd={rt_cd}, msg1={msg1}")
                return False
        else:
            print(f"\n[ERROR] HTTP Error {response.status_code}")
            return False

    except Exception as e:
        print(f"\n[ERROR] Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*70)
    print("단일 종목 테스트 (Rate Limiting 확인)")
    print("="*70)

    token = load_token()
    if not token:
        print("[X] 토큰 없음")
        return

    print(f"[OK] 토큰 로드 완료 (길이: {len(token)})")

    # TQQQ 테스트
    test_price(token, "TQQQ", "NAS")

    print("\n" + "="*70)
    print("대기 3초...")
    time.sleep(3)

    # NVDL 테스트
    test_price(token, "NVDL", "NAS")

    print("\n" + "="*70)
    print("테스트 완료")
    print("="*70)

if __name__ == "__main__":
    main()
