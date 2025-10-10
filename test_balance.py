#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""잔고 조회 디버깅"""

import json
import requests

# KIS API 설정
APP_KEY = "PSi3RlRt3DWtPPKTdYNALowIoeUBgM5mMLYO"
APP_SECRET = "Q7LxW5oIlCeg+doJCkmPDgXw7uy8bjC7ACRQR1GrAzgCF3zH7LziMix/QJgweS+IRU+uM/3GPELXVeOGocKQnHZ+RPeH4bqR1Ciwt3+1yp7yctt+bBc85eDrIsrX9KfOkrLY+wVuE1tthKYsDyiF2YKrOp/e1PsSD0mdI="
BASE_URL = "https://openapi.koreainvestment.com:9443"
ACCOUNT_NO = "43113014"
ACCOUNT_CODE = "01"

# 토큰 로드
with open("kis_token.json", 'r') as f:
    token = json.load(f)['access_token']

print("토큰 로드 성공")

# 잔고 조회
url = f"{BASE_URL}/uapi/overseas-stock/v1/trading/inquire-balance"
headers = {
    "Content-Type": "application/json; charset=utf-8",
    "authorization": f"Bearer {token}",
    "appkey": APP_KEY,
    "appsecret": APP_SECRET,
    "tr_id": "TTTS3012R",
    "custtype": "P"
}
params = {
    "CANO": ACCOUNT_NO,
    "ACNT_PRDT_CD": ACCOUNT_CODE,
    "OVRS_EXCG_CD": "NASD",
    "TR_CRCY_CD": "USD",
    "CTX_AREA_FK200": "",
    "CTX_AREA_NK200": ""
}

print("\n잔고 조회 중...")
response = requests.get(url, headers=headers, params=params, timeout=10)

print(f"\nHTTP 상태 코드: {response.status_code}")

# HTTP 500이 아닌 경우만 JSON 파싱
if response.status_code == 200:
    result = response.json()
    print(f"\n응답 전체:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
else:
    print(f"\nHTTP 오류 발생")
    print(f"응답 텍스트: {response.text}")
    result = None

if result and result.get("rt_cd") == "0":
    print("\n✅ 조회 성공!")

    # output2 확인
    output2 = result.get("output2", [])
    print(f"\noutput2: {output2}")

    if output2:
        balance_info = output2[0]
        print(f"\n잔고 정보:")
        for key, value in balance_info.items():
            print(f"  {key}: {value}")

        # USD 잔고
        usd_balance = float(balance_info.get('frcr_dncl_amt_2', 0))
        print(f"\n💵 USD 잔고: ${usd_balance:.2f}")

    # output1 확인 (보유 종목)
    output1 = result.get("output1", [])
    print(f"\n보유 종목 수: {len(output1)}")

    for item in output1:
        symbol = item.get('ovrs_pdno', '')
        qty = item.get('ovrs_cblc_qty', 0)
        if symbol and int(qty) > 0:
            print(f"  {symbol}: {qty}주")
else:
    print(f"\n❌ 조회 실패: {result.get('msg1') if result else 'HTTP 오류'}")
