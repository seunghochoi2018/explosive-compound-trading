#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
refresh_kis_token.py와 동일한 방식으로 TQQQ 테스트
"""
import json
import requests

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

def test_symbol(token, symbol, excd="NAS"):
    """refresh_kis_token.py와 완전히 동일한 방식"""
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
    print(f"Params: {params}")
    print(f"\n[REQUEST] 전송 중...")

    response = requests.get(url, headers=headers, params=params)

    print(f"[RESPONSE] HTTP {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        rt_cd = result.get("rt_cd")
        msg1 = result.get("msg1", "")

        print(f"rt_cd: {rt_cd}")
        print(f"msg1: {msg1}")

        if rt_cd == "0":
            output = result.get("output", {})
            price = output.get("last", "N/A")
            print(f"\n[SUCCESS] {symbol} 현재가: ${price}")
            print(f"전체 output: {json.dumps(output, indent=2, ensure_ascii=False)}")
            return True
        else:
            print(f"\n[FAIL] API 오류")
            print(f"전체 응답: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return False
    else:
        print(f"\n[ERROR] HTTP 오류: {response.status_code}")
        print(f"응답: {response.text}")
        return False

def main():
    print("="*70)
    print("refresh_kis_token.py 방식으로 TQQQ 테스트")
    print("="*70)

    token = load_token()
    if not token:
        print("[X] 토큰 없음")
        return

    print(f"[OK] 토큰 로드 완료 (길이: {len(token)})")

    # 1. NVDL 테스트 (성공해야 함)
    print("\n[1/2] NVDL 테스트 (기준)")
    nvdl_result = test_symbol(token, "NVDL", "NAS")

    # 2. TQQQ 테스트
    print("\n[2/2] TQQQ 테스트")
    tqqq_result = test_symbol(token, "TQQQ", "NAS")

    print("\n" + "="*70)
    print("[SUMMARY]")
    print(f"  NVDL: {'성공' if nvdl_result else '실패'}")
    print(f"  TQQQ: {'성공' if tqqq_result else '실패'}")
    print("="*70)

if __name__ == "__main__":
    main()
