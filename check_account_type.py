#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
계좌 타입 확인 - 실전/모의 테스트
"""

import json
import requests

# KIS API 설정
with open("kis_token.json", 'r') as f:
    token = json.load(f)['access_token']

APP_KEY = "PSi3RlRt3DWtPPKTdYNALowIoeUBgM5mMLYO"
APP_SECRET = "Q7LxW5oIlCeg+doJCkmPDgXw7uy8bjC7ACRQR1GrAzgCF3zH7LziMix/QJgweS+IRU+uM/3GPELXVeOGocKQnHZ+RPeH4bqR1Ciwt3+1yp7yctt+bBc85eDrIsrX9KfOkrLY+wVuE1tthKYsDyiF2YKrOp/e1PsSD0mdI="
BASE_URL = "https://openapi.koreainvestment.com:9443"
ACCOUNT_NO = "43113014"
ACCOUNT_CODE = "01"

print("=" * 70)
print("계좌 타입 확인: 실전 vs 모의")
print("=" * 70)

url = f"{BASE_URL}/uapi/overseas-stock/v1/trading/inquire-balance"

# 테스트 1: 실전 TR_ID (TTTS3012R)
print("\n[테스트 1] 실전 TR_ID: TTTS3012R")
headers_real = {
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

response1 = requests.get(url, headers=headers_real, params=params)
print(f"HTTP 상태: {response1.status_code}")
if response1.status_code == 200:
    result1 = response1.json()
    print(f"rt_cd: {result1.get('rt_cd')}")
    print(f"msg1: {result1.get('msg1')}")
    if result1.get('rt_cd') == '0':
        print("[성공] 실전 계좌입니다!")
else:
    print(f"[실패] HTTP {response1.status_code}")

# 테스트 2: 모의 TR_ID (VTTS3012R)
print("\n[테스트 2] 모의 TR_ID: VTTS3012R")
headers_virtual = {
    "Content-Type": "application/json; charset=utf-8",
    "authorization": f"Bearer {token}",
    "appkey": APP_KEY,
    "appsecret": APP_SECRET,
    "tr_id": "VTTS3012R",
    "custtype": "P"
}

response2 = requests.get(url, headers=headers_virtual, params=params)
print(f"HTTP 상태: {response2.status_code}")
if response2.status_code == 200:
    result2 = response2.json()
    print(f"rt_cd: {result2.get('rt_cd')}")
    print(f"msg1: {result2.get('msg1')}")
    if result2.get('rt_cd') == '0':
        print("[성공] 모의 계좌입니다!")
else:
    print(f"[실패] HTTP {response2.status_code}")

print("\n" + "=" * 70)
