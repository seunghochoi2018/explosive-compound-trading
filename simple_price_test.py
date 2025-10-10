#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""간단한 가격 조회 테스트"""

import json
import requests

# 토큰 새로 로드
with open("kis_token.json", 'r') as f:
    token_data = json.load(f)
    token = token_data['access_token']

print(f"토큰: {token[:50]}...")
print(f"만료: {token_data.get('expires_at')}")

APP_KEY = "PSi3RlRt3DWtPPKTdYNALowIoeUBgM5mMLYO"
APP_SECRET = "Q7LxW5oIlCeg+doJCkmPDgXw7uy8bjC7ACRQR1GrAzgCF3zH7LziMix/QJgweS+IRU+uM/3GPELXVeOGocKQnHZ+RPeH4bqR1Ciwt3+1yp7yctt+bBc85eDrIsrX9KfOkrLY+wVuE1tthKYSDyiF2YKrOp/e1PsSD0mdI="
BASE_URL = "https://openapi.koreainvestment.com:9443"

# SOXL 가격
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
    "EXCD": "NAS",
    "SYMB": "SOXL"
}

print("\n[SOXL 가격 조회]")
r = requests.get(url, headers=headers, params=params, timeout=10)
print(f"HTTP: {r.status_code}")

if r.status_code == 200:
    data = r.json()
    print(f"rt_cd: {data.get('rt_cd')}")
    print(f"msg1: {data.get('msg1')}")

    if data.get('rt_cd') == '0':
        price = data.get('output', {}).get('last', 'N/A')
        print(f">>> SOXL 가격: ${price}")
    else:
        print(f">>> 실패")
        print(f"응답: {json.dumps(data, indent=2)}")
else:
    print(f">>> HTTP 오류")
    print(f"응답: {r.text}")

# SOXS 가격
params['SYMB'] = 'SOXS'
print("\n[SOXS 가격 조회]")
r2 = requests.get(url, headers=headers, params=params, timeout=10)
print(f"HTTP: {r2.status_code}")

if r2.status_code == 200:
    data2 = r2.json()
    if data2.get('rt_cd') == '0':
        price2 = data2.get('output', {}).get('last', 'N/A')
        print(f">>> SOXS 가격: ${price2}")
