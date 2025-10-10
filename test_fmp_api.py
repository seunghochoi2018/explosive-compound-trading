#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FMP API 간단 테스트
"""

import requests
import json

def test_fmp_api():
    """FMP API 간단 테스트"""
    print("=== FMP API 간단 테스트 ===")

    api_key = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"
    base_url = "https://financialmodelingprep.com/api/v3"

    # NVDL 테스트
    symbol = "NVDL"
    try:
        url = f"{base_url}/quote/{symbol}"
        params = {"apikey": api_key}

        print(f"API 호출: {url}")
        print(f"파라미터: {params}")

        response = requests.get(url, params=params, timeout=15)

        print(f"응답 코드: {response.status_code}")
        print(f"응답 헤더: {dict(response.headers)}")

        if response.status_code == 200:
            data = response.json()
            print(f"응답 데이터: {json.dumps(data, indent=2)}")

            if data and len(data) > 0:
                quote = data[0]
                price = quote.get('price', 0)
                change = quote.get('changesPercentage', 0)
                print(f"\n결과: {symbol} = ${price:.2f} ({change:+.2f}%)")
            else:
                print("데이터가 비어있습니다.")
        else:
            print(f"오류: {response.status_code}")
            print(f"응답 내용: {response.text}")

    except Exception as e:
        print(f"예외 발생: {e}")

if __name__ == "__main__":
    test_fmp_api()