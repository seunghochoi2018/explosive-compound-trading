#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TQQQ PDNO 기반 테스트
"""
import requests
import json

# 실전 환경용 설정
APP_KEY = "PSi3RlRt3DWtPPKTdYNALowIoeUBgM5mMLYO"
APP_SECRET = "Q7LxW5oIlCeg+doJCkmPDgXw7uy8bjC7ACRQR1GrAzgCF3zH7LziMix/QJgweS+IRU+uM/3GPELXVeOGocKQnHZ+RPeH4bqR1Ciwt3+1yp7yctt+bBc85eDrIsrX9KfOkrLY+wVuE1tthKYsDyiF2YKrOp/e1PsSD0mdI="
BASE_URL = "https://openapi.koreainvestment.com:9443"

# 토큰 로드
def load_token():
    try:
        with open("kis_token.json", 'r') as f:
            token_data = json.load(f)
            return token_data.get('access_token')
    except Exception as e:
        print(f"[X] 토큰 로드 실패: {e}")
        return None

# 테스트 대상 종목
SYMBOL = "TQQQ"
PDNO = "A206892"       # TQQQ 정식 종목코드
EXCD = "NASD"          # 거래소 코드

# 요청 및 예외 처리
def get_price(access_token):
    # API 경로 (PDNO 기반 사용 권장)
    URL = f"{BASE_URL}/uapi/overseas-price/v1/quotations/price?EXCD={EXCD}&PDNO={PDNO}"

    headers = {
        "authorization": f"Bearer {access_token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "HHDFS00000300",  # 시세조회용 TR
        "custtype": "P"
    }

    print("="*70)
    print("[TEST] TQQQ PDNO 기반 조회")
    print("="*70)
    print(f"URL: {URL}")
    print(f"EXCD: {EXCD}")
    print(f"PDNO: {PDNO}")
    print(f"SYMBOL: {SYMBOL}")
    print(f"\n[REQUEST] 전송 중...")

    try:
        response = requests.get(URL, headers=headers, timeout=10)
        print(f"\n[HTTP 응답 코드] {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            rt_cd = data.get("rt_cd", "")
            msg1 = data.get("msg1", "")

            print(f"rt_cd: {rt_cd}")
            print(f"msg1: {msg1}")

            if rt_cd == "0":
                output = data.get("output", {})
                print(f"\n[SUCCESS] TQQQ 조회 성공!")
                print(f"응답 데이터:")
                print(json.dumps(output, indent=2, ensure_ascii=False))

                # 주요 필드 출력
                print(f"\n[주요 정보]")
                print(f"  stck_prpr (현재가): {output.get('stck_prpr', 'N/A')}")
                print(f"  last: {output.get('last', 'N/A')}")
                print(f"  base: {output.get('base', 'N/A')}")
                print(f"  pvol (거래량): {output.get('pvol', 'N/A')}")
                return True
            else:
                print(f"\n[FAIL] API 오류")
                print(f"전체 응답: {json.dumps(data, indent=2, ensure_ascii=False)}")
                return False
        else:
            print(f"\n[ERROR] HTTP 오류")
            print(f"응답: {response.text}")
            return False

    except Exception as e:
        print(f"\n[ERROR] 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*70)
    print("TQQQ PDNO 기반 테스트")
    print("="*70)

    # 토큰 로드
    access_token = load_token()
    if not access_token:
        print("[X] 토큰을 로드할 수 없습니다.")
        return

    print(f"[OK] 토큰 로드 완료 (길이: {len(access_token)})")

    # TQQQ 조회
    result = get_price(access_token)

    print("\n" + "="*70)
    if result:
        print("[RESULT] 테스트 성공!")
    else:
        print("[RESULT] 테스트 실패")
    print("="*70)

if __name__ == "__main__":
    main()
