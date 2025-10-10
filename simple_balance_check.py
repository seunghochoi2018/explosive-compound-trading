#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""간단한 잔고 확인"""

import json
import requests

# 토큰 로드
with open("kis_token.json", 'r') as f:
    token = json.load(f)['access_token']

APP_KEY = "PSi3RlRt3DWtPPKTdYNALowIoeUBgM5mMLYO"
APP_SECRET = "Q7LxW5oIlCeg+doJCkmPDgXw7uy8bjC7ACRQR1GrAzgCF3zH7LziMix/QJgweS+IRU+uM/3GPELXVeOGocKQnHZ+RPeH4bqR1Ciwt3+1yp7yctt+bBc85eDrIsrX9KfOkrLY+wVuE1tthKYsDyiF2YKrOp/e1PsSD0mdI="
BASE_URL = "https://openapi.koreainvestment.com:9443"

print("=== 잔고 조회 테스트 ===")

# 해외주식 잔고조회
url = f"{BASE_URL}/uapi/overseas-stock/v1/trading/inquire-balance"
headers = {
    "Content-Type": "application/json",
    "authorization": f"Bearer {token}",
    "appkey": APP_KEY,
    "appsecret": APP_SECRET,
    "tr_id": "TTTS3012R"
}

params = {
    "CANO": "43113014",
    "ACNT_PRDT_CD": "01",
    "OVRS_EXCG_CD": "NASD",
    "TR_CRCY_CD": "USD",
    "CTX_AREA_FK200": "",
    "CTX_AREA_NK200": ""
}

print(f"\n[요청]")
print(f"URL: {url}")
print(f"TR_ID: TTTS3012R")
print(f"계좌: 43113014-01")

response = requests.get(url, headers=headers, params=params)

print(f"\n[응답]")
print(f"HTTP 상태: {response.status_code}")
print(f"응답 본문: {response.text[:500]}")

if response.status_code == 200:
    try:
        result = response.json()
        print(f"\nJSON 파싱 성공")
        print(f"rt_cd: {result.get('rt_cd')}")
        print(f"msg1: {result.get('msg1')}")
        print(f"msg_cd: {result.get('msg_cd')}")

        if 'output2' in result:
            print(f"\noutput2 존재!")
            print(f"output2 타입: {type(result['output2'])}")
            print(f"output2: {result['output2']}")

        if 'output1' in result:
            print(f"\noutput1 존재!")
            print(f"output1 길이: {len(result['output1'])}")
    except Exception as e:
        print(f"JSON 파싱 실패: {e}")
