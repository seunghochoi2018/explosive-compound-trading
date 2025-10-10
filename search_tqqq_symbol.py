#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TQQQ 종목 코드 검색 - KIS API 지원 여부 확인
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

def search_symbol(token, keyword):
    """종목 검색 API"""
    print("="*70)
    print(f"종목 검색: {keyword}")
    print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    # 해외주식 종목 검색 API (TR_ID: CTPF1702R)
    url = f"{BASE_URL}/uapi/overseas-price/v1/quotations/search-info"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "CTPF1702R",
        "custtype": "P"
    }
    params = {
        "AUTH": "",
        "EXCD": "NAS",  # NASDAQ
        "CO_YN_PRICECUR": "",
        "CO_ST_PRICECUR": "",
        "PRDT_TYPE_CD": "512",  # 해외주식
    }

    print(f"\n[REQUEST]")
    print(f"  URL: {url}")
    print(f"  검색어: {keyword}")
    print(f"\n전송 중...")

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)

        print(f"\n[RESPONSE]")
        print(f"  HTTP Status: {response.status_code}")
        print(f"  응답 본문: {response.text[:500]}")

        if response.status_code == 200:
            result = response.json()
            rt_cd = result.get("rt_cd")

            if rt_cd == "0":
                output = result.get("output", [])
                print(f"\n[SUCCESS] 검색 결과: {len(output)}건")

                # TQQQ 포함된 결과 필터링
                tqqq_results = [item for item in output if "TQQQ" in item.get("prdt_name", "").upper() or "TQQQ" in item.get("symb", "").upper()]

                if tqqq_results:
                    print(f"\nTQQQ 관련 종목:")
                    for item in tqqq_results:
                        print(f"  - {item}")
                else:
                    print(f"\nTQQQ 관련 종목을 찾을 수 없습니다.")

                return True
            else:
                print(f"\n[FAIL] rt_cd={rt_cd}")
                print(f"전체 응답: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print(f"\n[ERROR] HTTP {response.status_code}")

    except Exception as e:
        print(f"\n[ERROR] 예외: {e}")
        import traceback
        traceback.print_exc()

    return False

def check_condition_search(token):
    """조건 검색으로 TQQQ 확인"""
    print("\n" + "="*70)
    print("조건 검색 API로 TQQQ 확인")
    print("="*70)

    # 해외주식 기본 시세 API로 다양한 EXCD 시도
    test_cases = [
        ("TQQQ", "NAS"),
        ("TQQQ", "NASD"),
        ("TQQQ", "NYS"),
        ("TQQQ", "AMS"),
    ]

    url = f"{BASE_URL}/uapi/overseas-price/v1/quotations/price"

    for symbol, excd in test_cases:
        print(f"\n시도: {symbol} @ {excd}")

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

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            print(f"  HTTP {response.status_code}: {response.text[:100]}")
        except Exception as e:
            print(f"  오류: {e}")

def main():
    print("\n" + "#"*70)
    print("# TQQQ 종목 코드 검색")
    print("#"*70 + "\n")

    token = load_token()
    if not token:
        print("[X] 토큰 없음")
        return

    print(f"[OK] 토큰 준비 완료\n")

    # 1. 종목 검색 시도
    search_symbol(token, "TQQQ")

    # 2. 다양한 EXCD로 조건 검색
    check_condition_search(token)

    print("\n" + "="*70)
    print("[완료]")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
