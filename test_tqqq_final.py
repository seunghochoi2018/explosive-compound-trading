#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TQQQ 최종 테스트 - 개장 시간, Rate Limit 복구 후
"""
import json
import requests
from datetime import datetime

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

def test_single_request(token, symbol, excd="NAS"):
    """단일 요청 테스트"""
    print("="*70)
    print(f"TQQQ 최종 테스트")
    print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

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

    print(f"\n[REQUEST]")
    print(f"  종목: {symbol}")
    print(f"  거래소: {excd}")
    print(f"  URL: {url}")
    print(f"\n전송 중...")

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)

        print(f"\n[RESPONSE]")
        print(f"  HTTP Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            rt_cd = result.get("rt_cd")
            msg1 = result.get("msg1", "")
            msg_cd = result.get("msg_cd", "")

            print(f"  rt_cd: {rt_cd}")
            print(f"  msg_cd: {msg_cd}")
            print(f"  msg1: {msg1}")

            if rt_cd == "0":
                output = result.get("output", {})

                print(f"\n{'='*70}")
                print(f"[SUCCESS] {symbol} 조회 성공!")
                print(f"{'='*70}")
                print(f"\n주요 정보:")
                print(f"  현재가 (last): {output.get('last', 'N/A')}")
                print(f"  기준가 (base): {output.get('base', 'N/A')}")
                print(f"  고가 (high): {output.get('high', 'N/A')}")
                print(f"  저가 (low): {output.get('low', 'N/A')}")
                print(f"  거래량 (pvol): {output.get('pvol', 'N/A')}")
                print(f"  등락률 (rate): {output.get('rate', 'N/A')}")

                print(f"\n전체 응답:")
                print(json.dumps(output, indent=2, ensure_ascii=False))

                return True
            else:
                print(f"\n[FAIL] API 오류")
                print(f"\n전체 응답:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return False
        else:
            print(f"  응답 본문: {response.text}")
            return False

    except Exception as e:
        print(f"\n[ERROR] 예외: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n" + "#"*70)
    print("# TQQQ 개장시간 최종 테스트")
    print("#"*70 + "\n")

    token = load_token()
    if not token:
        print("[X] 토큰 없음")
        return

    print(f"[OK] 토큰 준비 완료\n")

    # TQQQ 단일 테스트
    result = test_single_request(token, "TQQQ", "NAS")

    print("\n" + "="*70)
    if result:
        print("[결론] TQQQ 조회 가능 - API 정상")
    else:
        print("[결론] TQQQ 조회 실패 - 추가 조사 필요")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
