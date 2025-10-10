#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""최소 테스트 - 어떤 엔드포인트든 작동하는지 확인"""

import json
import requests

with open("kis_token.json", 'r') as f:
    token = json.load(f)['access_token']

APP_KEY = "PSi3RlRt3DWtPPKTdYNALowIoeUBgM5mMLYO"
APP_SECRET = "Q7LxW5oIlCeg+doJCkmPDgXw7uy8bjC7ACRQR1GrAzgCF3zH7LziMix/QJgweS+IRU+uM/3GPELXVeOGocKQnHZ+RPeH4bqR1Ciwt3+1yp7yctt+bBc85eDrIsrX9KfOkrLY+wVuE1tthKYsDyiF2YKrOp/e1PsSD0mdI="
BASE = "https://openapi.koreainvestment.com:9443"

print("=== KIS API 테스트 ===\n")

# 테스트 1: 해외주식 현재가 (이건 작동함)
print("[1] 해외주식 현재가 조회 (NVDL)")
url1 = f"{BASE}/uapi/overseas-price/v1/quotations/price"
headers1 = {
    "Content-Type": "application/json",
    "authorization": f"Bearer {token}",
    "appkey": APP_KEY,
    "appsecret": APP_SECRET,
    "tr_id": "HHDFS00000300"
}
params1 = {
    "AUTH": "",
    "EXCD": "NAS",
    "SYMB": "NVDL"
}

r1 = requests.get(url1, headers=headers1, params=params1)
print(f"결과: HTTP {r1.status_code}")
if r1.status_code == 200:
    data1 = r1.json()
    if data1.get('rt_cd') == '0':
        price = data1.get('output', {}).get('last', 'N/A')
        print(f"성공! NVDL 가격: ${price}")
    else:
        print(f"실패: {data1.get('msg1')}")

# 테스트 2: 해외주식 잔고
print("\n[2] 해외주식 잔고 조회")
url2 = f"{BASE}/uapi/overseas-stock/v1/trading/inquire-balance"
headers2 = {
    "Content-Type": "application/json",
    "authorization": f"Bearer {token}",
    "appkey": APP_KEY,
    "appsecret": APP_SECRET,
    "tr_id": "TTTS3012R"
}
params2 = {
    "CANO": "43113014",
    "ACNT_PRDT_CD": "01",
    "OVRS_EXCG_CD": "NASD",
    "TR_CRCY_CD": "USD",
    "CTX_AREA_FK200": "",
    "CTX_AREA_NK200": ""
}

r2 = requests.get(url2, headers=headers2, params=params2)
print(f"결과: HTTP {r2.status_code}")
if r2.status_code == 200:
    data2 = r2.json()
    print(f"rt_cd: {data2.get('rt_cd')}")
    print(f"msg1: {data2.get('msg1')}")
    print(f"msg_cd: {data2.get('msg_cd')}")
else:
    print(f"실패: {r2.text[:100]}")

# 테스트 3: 실제로 사용자가 제공한 계좌번호로 주문 가능 여부 확인 (주문은 안하고 가능한지만)
print("\n[3] 주문 가능 여부 확인")
# 최소 금액 매수 시도 (dry run) - 실제로는 실행 안됨
url3 = f"{BASE}/uapi/overseas-stock/v1/trading/order"
headers3 = {
    "Content-Type": "application/json",
    "authorization": f"Bearer {token}",
    "appkey": APP_KEY,
    "appsecret": APP_SECRET,
    "tr_id": "TTTT1002U"  # 해외주식 주문 TR_ID
}

# 엔드포인트만 테스트 (실제 주문은 POST로 body 필요)
r3 = requests.post(url3, headers=headers3, json={})
print(f"결과: HTTP {r3.status_code}")
if r3.status_code == 200:
    data3 = r3.json()
    print(f"rt_cd: {data3.get('rt_cd')}")
    print(f"msg1: {data3.get('msg1')}")
else:
    print(f"결과: {r3.text[:100]}")

print("\n=== 테스트 완료 ===")
