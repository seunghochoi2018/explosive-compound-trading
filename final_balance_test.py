#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""최종 잔고 테스트 - 정확한 형식 사용"""

import json
import requests
import time

# 토큰 새로 발급
APP_KEY = "PSi3RlRt3DWtPPKTdYNALowIoeUBgM5mMLYO"
APP_SECRET = "Q7LxW5oIlCeg+doJCkmPDgXw7uy8bjC7ACRQR1GrAzgCF3zH7LziMix/QJgweS+IRU+uM/3GPELXVeOGocKQnHZ+RPeH4bqR1Ciwt3+1yp7yctt+bBc85eDrIsrX9KfOkrLY+wVuE1tthKYSDyiF2YKrOp/e1PsSD0mdI="
BASE = "https://openapi.koreainvestment.com:9443"

print("=== 최종 잔고 테스트 ===\n")

# Step 1: 새 토큰 발급
print("[1] 토큰 발급")
token_url = f"{BASE}/oauth2/tokenP"
token_headers = {"content-type": "application/json; charset=utf-8"}
token_data = {
    "grant_type": "client_credentials",
    "appkey": APP_KEY,
    "appsecret": APP_SECRET
}

tr = requests.post(token_url, headers=token_headers, json=token_data)
if tr.status_code == 200:
    token = tr.json().get("access_token")
    print(f"토큰 발급 성공\n")
else:
    print(f"토큰 발급 실패: {tr.status_code}")
    exit(1)

# Step 2: 해외주식 잔고 조회 (refresh_kis_token.py 방식 그대로)
print("[2] 해외주식 잔고 조회")
balance_url = f"{BASE}/uapi/overseas-stock/v1/trading/inquire-balance"
balance_headers = {
    "Content-Type": "application/json; charset=utf-8",
    "authorization": f"Bearer {token}",
    "appkey": APP_KEY,
    "appsecret": APP_SECRET,
    "tr_id": "TTTS3012R",
    "custtype": "P"
}

# 여러 계좌번호 형식 시도
account_formats = [
    ("43113014", "01"),      # 분리 형식
    ("43113014-01", ""),     # 하이픈 포함
    ("43113014", "1"),       # 01 대신 1
]

for cano, prdt_cd in account_formats:
    print(f"\n테스트: CANO={cano}, ACNT_PRDT_CD={prdt_cd}")

    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": prdt_cd,
        "OVRS_EXCG_CD": "NASD",
        "TR_CRCY_CD": "USD",
        "CTX_AREA_FK200": "",
        "CTX_AREA_NK200": ""
    }

    r = requests.get(balance_url, headers=balance_headers, params=params)
    print(f"  HTTP: {r.status_code}")

    if r.status_code == 200:
        result = r.json()
        rt_cd = result.get('rt_cd')
        msg1 = result.get('msg1', 'N/A')

        print(f"  rt_cd: {rt_cd}")
        print(f"  msg1: {msg1}")

        if rt_cd == '0':
            print("  [성공!]")

            if 'output2' in result:
                output2 = result['output2']
                if isinstance(output2, list) and output2:
                    bal = output2[0]
                    usd_amt = bal.get('frcr_buy_amt_smtl1', '0')
                    print(f"  USD 매수가능금액: ${usd_amt}")
                    break  # 성공하면 중단
    else:
        print(f"  HTTP 오류")

    time.sleep(0.5)  # API 호출 간격

print("\n=== 테스트 완료 ===")
