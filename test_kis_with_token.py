#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
기존 토큰으로 KIS API 테스트
"""

import json
import requests

# 토큰 로드
with open('kis_token.json', 'r') as f:
    token_data = json.load(f)

TOKEN = token_data['access_token']
APP_KEY = "PSi3RlRt3DWtPPKTdYNALowIoeUBgM5mMLYO"
APP_SECRET = "Q7LxW5oIlCeg+doJCkmPDgXw7uy8bjC7ACRQR1GrAzgCF3zH7LziMix/QJgweS+IRU+uM/3GPELXVeOGocKQnHZ+RPeH4bqR1CgFOs9tHmRtGmxCiwt3+1yp7yctt+bBc85eDrIsrX9KfOkrLY+wVuE1tthKYSDyiF2YKrOp/e1PsSD0mdI="
BASE_URL = "https://openapi.koreainvestment.com:9443"

print("KIS API 테스트 (기존 토큰 사용)")
print("="*50)

# 1. NVDL 가격 조회
print("\n1. NVDL 현재가 조회...")
url = f"{BASE_URL}/uapi/overseas-price/v1/quotations/price"
headers = {
    "Content-Type": "application/json; charset=utf-8",
    "authorization": f"Bearer {TOKEN}",
    "appkey": APP_KEY,
    "appsecret": APP_SECRET,
    "tr_id": "HHDFS00000300",
    "custtype": "P"
}

params = {
    "AUTH": "",
    "EXCD": "NAS",
    "SYMB": "NVDL"
}

response = requests.get(url, headers=headers, params=params)
print(f"응답 코드: {response.status_code}")

if response.status_code == 200:
    result = response.json()
    if result.get("rt_cd") == "0":
        output = result.get("output", {})
        print(f"[SUCCESS] NVDL 정보:")
        print(f"  현재가: ${output.get('last', 'N/A')}")
        print(f"  시가: ${output.get('open', 'N/A')}")
        print(f"  고가: ${output.get('high', 'N/A')}")
        print(f"  저가: ${output.get('low', 'N/A')}")
        print(f"  거래량: {output.get('tvol', 'N/A')}")
    else:
        print(f"오류: {result.get('msg1', '')}")
else:
    print(f"HTTP 오류: {response.text}")

# 2. NVDD 가격 조회
print("\n2. NVDD 현재가 조회...")
params["SYMB"] = "NVDD"

response = requests.get(url, headers=headers, params=params)
print(f"응답 코드: {response.status_code}")

if response.status_code == 200:
    result = response.json()
    if result.get("rt_cd") == "0":
        output = result.get("output", {})
        print(f"[SUCCESS] NVDD 정보:")
        print(f"  현재가: ${output.get('last', 'N/A')}")
        print(f"  시가: ${output.get('open', 'N/A')}")
        print(f"  고가: ${output.get('high', 'N/A')}")
        print(f"  저가: ${output.get('low', 'N/A')}")
        print(f"  거래량: {output.get('tvol', 'N/A')}")
    else:
        print(f"오류: {result.get('msg1', '')}")

# 3. 계좌 테스트
print("\n3. 계좌 잔고 조회...")
url = f"{BASE_URL}/uapi/overseas-stock/v1/trading/inquire-balance"
headers["tr_id"] = "TTTS3012R"

for account_code in ["01", "02", "03"]:
    params = {
        "CANO": "43113014",
        "ACNT_PRDT_CD": account_code,
        "OVRS_EXCG_CD": "NASD",
        "TR_CRCY_CD": "USD",
        "CTX_AREA_FK200": "",
        "CTX_AREA_NK200": ""
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        result = response.json()
        if result.get("rt_cd") == "0":
            print(f"[SUCCESS] 계좌 43113014-{account_code}: 해외주식 거래 가능!")
            output2 = result.get("output2", {})
            if output2:
                cash = output2.get("frcr_buy_amt_smtl1", "0")
                print(f"  매수가능금액: ${cash}")
            break
        else:
            if "해외주식" not in result.get('msg1', ''):
                print(f"  계좌 {account_code}: {result.get('msg1', '')}")

print("\n테스트 완료!")