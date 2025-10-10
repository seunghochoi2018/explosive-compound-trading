#!/usr/bin/env python3
"""
NVDL/NVDQ API 테스트 스크립트
"""

import requests
from datetime import datetime
from config import FMP_API_KEY

def test_fmp_api():
    """FMP API 연결 테스트"""
    print("FMP API 연결 테스트")
    print("=" * 50)

    # 테스트할 종목
    symbols = ['NVDL', 'NVDQ']

    for symbol in symbols:
        print(f"\n{symbol} 테스트:")

        try:
            # 실시간 가격 조회 테스트
            url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}"
            params = {'apikey': FMP_API_KEY}

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    price_data = data[0]
                    print(f"  실시간 가격: ${price_data['price']:.2f}")
                    print(f"  변화: {price_data['change']:+.2f} ({price_data['changesPercentage']:+.2f}%)")
                    print(f"  마지막 업데이트: {price_data['timestamp']}")
                else:
                    print(f"  데이터가 비어있음")
            else:
                print(f"  HTTP 오류: {response.status_code}")
                print(f"  응답: {response.text}")

        except Exception as e:
            print(f"  오류: {e}")

    print("\n" + "=" * 50)

    # API 한도 확인
    try:
        print("API 한도 확인:")
        url = "https://financialmodelingprep.com/api/v3/profile/AAPL"
        params = {'apikey': FMP_API_KEY}

        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            print("  API 키 정상 작동")
        elif response.status_code == 429:
            print("  API 요청 한도 초과")
        else:
            print(f"  API 키 문제: {response.status_code}")

    except Exception as e:
        print(f"  API 테스트 오류: {e}")

    print("\nAPI 테스트 완료!")

if __name__ == "__main__":
    test_fmp_api()