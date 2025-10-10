#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TQQQ 테스트 - Rate Limit 고려
- 요청 간격 2초
- 실패 시 30초 대기 후 재시도
"""
import json
import requests
import time
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

def get_price_with_retry(token, symbol, excd="NAS", max_retries=3):
    """Rate Limit 고려한 가격 조회"""
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

    for attempt in range(1, max_retries + 1):
        print(f"\n{'='*70}")
        print(f"[시도 {attempt}/{max_retries}] {symbol} @ {excd}")
        print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}")

        try:
            print(f"[REQUEST] 전송 중...")
            response = requests.get(url, headers=headers, params=params, timeout=10)

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
                    base = output.get("base", "N/A")
                    pvol = output.get("pvol", "N/A")

                    print(f"\n[SUCCESS] {symbol} 조회 성공!")
                    print(f"  현재가 (last): ${price}")
                    print(f"  기준가 (base): ${base}")
                    print(f"  거래량 (pvol): {pvol}")
                    return True, price
                else:
                    print(f"\n[FAIL] rt_cd={rt_cd}, msg1={msg1}")
                    print(f"전체 응답: {response.text}")

            elif response.status_code == 500:
                print(f"[ERROR] HTTP 500 - Rate Limit 또는 서버 오류")
                print(f"응답: {response.text}")

            else:
                print(f"[ERROR] HTTP {response.status_code}")
                print(f"응답: {response.text}")

        except Exception as e:
            print(f"[ERROR] 예외 발생: {e}")

        # 재시도 대기
        if attempt < max_retries:
            wait_time = 30 if response.status_code == 500 else 10
            print(f"\n[WAIT] {wait_time}초 대기 후 재시도...")
            for i in range(wait_time, 0, -5):
                print(f"  {i}초 남음...")
                time.sleep(5)

    print(f"\n[FAIL] {symbol} 조회 실패 (최대 시도 횟수 초과)")
    return False, None

def main():
    print("="*70)
    print("TQQQ 테스트 - Rate Limit 고려")
    print("="*70)

    # 토큰 로드
    token = load_token()
    if not token:
        print("[X] 토큰 없음")
        return

    print(f"[OK] 토큰 로드 완료 (길이: {len(token)})")

    # 테스트 종목 목록
    test_symbols = [
        ("NVDL", "NAS"),   # 기준 종목 (이전에 성공)
        ("TQQQ", "NAS"),   # 목표 종목
    ]

    results = []

    for i, (symbol, excd) in enumerate(test_symbols, 1):
        print(f"\n\n{'#'*70}")
        print(f"# [{i}/{len(test_symbols)}] {symbol} 테스트")
        print(f"{'#'*70}")

        success, price = get_price_with_retry(token, symbol, excd, max_retries=2)
        results.append({
            "symbol": symbol,
            "excd": excd,
            "success": success,
            "price": price
        })

        # 다음 종목 전 대기 (Rate Limit 방지)
        if i < len(test_symbols):
            print(f"\n[WAIT] 다음 종목 전 3초 대기...")
            time.sleep(3)

    # 최종 결과
    print(f"\n\n{'='*70}")
    print("[최종 결과]")
    print(f"{'='*70}")
    for r in results:
        status = "[OK] 성공" if r['success'] else "[X] 실패"
        price_str = f"${r['price']}" if r['price'] else "N/A"
        print(f"{r['symbol']:<10} {r['excd']:<6} {status:<15} {price_str}")

    success_count = sum(1 for r in results if r['success'])
    print(f"\n성공: {success_count}/{len(results)}")
    print("="*70)

if __name__ == "__main__":
    main()
