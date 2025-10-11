#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
모의투자 계좌 잔고 확인
"""

import json
import requests

# KIS API 설정
with open("kis_token.json", 'r') as f:
    token = json.load(f)['access_token']

APP_KEY = "PSi3RlRt3DWtPPKTdYNALowIoeUBgM5mMLYO"
APP_SECRET = "Q7LxW5oIlCeg+doJCkmPDgXw7uy8bjC7ACRQR1GrAzgCF3zH7LziMix/QJgweS+IRU+uM/3GPELXVeOGocKQnHZ+RPeH4bqR1Ciwt3+1yp7yctt+bBc85eDrIsrX9KfOkrLY+wVuE1tthKYsDyiF2YKrOp/e1PsSD0mdI="
ACCOUNT_NO = "43113014"
ACCOUNT_CODE = "01"

print("=" * 70)
print("모의투자 계좌 잔고 확인")
print("=" * 70)

# 모의투자 URL
VIRTUAL_URL = "https://openapivts.koreainvestment.com:29443"
url = f"{VIRTUAL_URL}/uapi/overseas-stock/v1/trading/inquire-balance"

headers = {
    "Content-Type": "application/json; charset=utf-8",
    "authorization": f"Bearer {token}",
    "appkey": APP_KEY,
    "appsecret": APP_SECRET,
    "tr_id": "VTTS3012R",  # 모의투자 TR_ID
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

print("\n모의투자 잔고 조회 중...")
response = requests.get(url, headers=headers, params=params)

print(f"\nHTTP 상태: {response.status_code}")

if response.status_code == 200:
    result = response.json()
    print(f"\n응답 전체:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if result.get("rt_cd") == "0":
        print("\n 모의투자 계좌 조회 성공!")

        output2 = result.get("output2", [])
        if output2:
            balance_info = output2[0] if isinstance(output2, list) else output2
            print(f"\n잔고 정보:")
            for key, value in balance_info.items():
                print(f"  {key}: {value}")
else:
    print(f"HTTP 오류 발생: {response.text}")

print("\n" + "=" * 70)
