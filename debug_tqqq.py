#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TQQQ API 디버깅 스크립트
- Symbol 방식 vs PDNO 방식 비교
- 여러 종목 테스트
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

def test_price_symbol(token, symbol, excd="NAS"):
    """Symbol 방식 가격 조회"""
    print(f"\n{'='*70}")
    print(f"[Symbol 방식] {symbol} @ {excd}")
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

    print(f"[REQUEST] 요청 정보:")
    print(f"   URL: {url}")
    print(f"   EXCD: {excd}")
    print(f"   SYMB: {symbol}")
    print(f"   TR_ID: HHDFS00000300")
    print(f"   시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)

        print(f"\n[RESPONSE] 응답:")
        print(f"   HTTP Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            rt_cd = result.get('rt_cd')
            msg1 = result.get('msg1', '')

            print(f"   rt_cd: {rt_cd}")
            print(f"   msg1: {msg1}")

            if rt_cd == "0":
                output = result.get("output", {})
                print(f"\n[SUCCESS] 성공!")
                print(f"   stck_prpr (현재가): {output.get('stck_prpr', 'N/A')}")
                print(f"   last: {output.get('last', 'N/A')}")
                print(f"   base: {output.get('base', 'N/A')}")
                print(f"   pvol: {output.get('pvol', 'N/A')}")
                return True
            else:
                print(f"\n[FAIL] 실패!")
                print(f"   전체 응답: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return False
        else:
            print(f"   응답 본문: {response.text}")
            return False

    except Exception as e:
        print(f"\n[ERROR] 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_multiple_symbols(token):
    """여러 종목 테스트"""
    test_cases = [
        # (Symbol, EXCD, 설명)
        ("NVDL", "NAS", "NVDL - 작동 확인용"),
        ("TQQQ", "NAS", "TQQQ - 나스닥"),
        ("TQQQ", "NASD", "TQQQ - NASD"),
        ("AAPL", "NAS", "Apple"),
        ("MSFT", "NAS", "Microsoft"),
        ("NVDA", "NAS", "NVIDIA"),
        ("SQQQ", "NAS", "SQQQ"),
        ("QQQ", "NAS", "QQQ"),
    ]

    results = []

    for symbol, excd, desc in test_cases:
        success = test_price_symbol(token, symbol, excd)
        results.append({
            "symbol": symbol,
            "excd": excd,
            "desc": desc,
            "success": success
        })

    # 결과 요약
    print(f"\n\n{'='*70}")
    print(f"[SUMMARY] 테스트 결과 요약")
    print(f"{'='*70}")
    print(f"{'종목':<10} {'EXCD':<6} {'상태':<10} {'설명'}")
    print(f"{'-'*70}")

    for r in results:
        status = "[OK] 성공" if r['success'] else "[X] 실패"
        print(f"{r['symbol']:<10} {r['excd']:<6} {status:<10} {r['desc']}")

    success_count = sum(1 for r in results if r['success'])
    fail_count = len(results) - success_count

    print(f"\n성공: {success_count}/{len(results)}")
    print(f"실패: {fail_count}/{len(results)}")

def check_token_info(token):
    """토큰 정보 확인"""
    print(f"\n{'='*70}")
    print(f"[TOKEN] 토큰 정보 확인")
    print(f"{'='*70}")

    if not token:
        print("[X] 토큰 없음")
        return

    print(f"토큰 길이: {len(token)}")
    print(f"토큰 앞부분: {token[:30]}...")
    print(f"토큰 뒷부분: ...{token[-30:]}")

    try:
        with open("kis_token.json", 'r') as f:
            token_data = json.load(f)
            print(f"\n토큰 파일 내용:")
            print(f"   access_token 존재: {'access_token' in token_data}")
            print(f"   expires_in: {token_data.get('expires_in', 'N/A')}")

            # 토큰 경로 확인 (실전 vs 모의)
            if 'token_type' in token_data:
                print(f"   token_type: {token_data.get('token_type')}")
    except Exception as e:
        print(f"[X] 토큰 파일 읽기 오류: {e}")

def main():
    """메인 실행"""
    print("="*70)
    print("TQQQ API 디버깅 도구")
    print("="*70)

    # 1. 토큰 로드
    token = load_token()
    if not token:
        print("[X] 토큰을 로드할 수 없습니다.")
        return

    print("[OK] 토큰 로드 성공")

    # 2. 토큰 정보 확인
    check_token_info(token)

    # 3. 여러 종목 테스트
    test_multiple_symbols(token)

    print(f"\n{'='*70}")
    print("디버깅 완료")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
