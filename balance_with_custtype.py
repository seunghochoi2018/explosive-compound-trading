#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""custtype 포함 잔고 조회"""

import json
import requests

with open("kis_token.json", 'r') as f:
    token = json.load(f)['access_token']

APP_KEY = "PSi3RlRt3DWtPPKTdYNALowIoeUBgM5mMLYO"
APP_SECRET = "Q7LxW5oIlCeg+doJCkmPDgXw7uy8bjC7ACRQR1GrAzgCF3zH7LziMix/QJgweS+IRU+uM/3GPELXVeOGocKQnHZ+RPeH4bqR1Ciwt3+1yp7yctt+bBc85eDrIsrX9KfOkrLY+wVuE1tthKYSDyiF2YKrOp/e1PsSD0mdI="
BASE = "https://openapi.koreainvestment.com:9443"

print("=== 잔고 조회 (custtype 포함) ===\n")

# 현재가 먼저 테스트
print("[1] 현재가 조회 테스트")
url_price = f"{BASE}/uapi/overseas-price/v1/quotations/price"
headers_price = {
    "Content-Type": "application/json; charset=utf-8",
    "authorization": f"Bearer {token}",
    "appkey": APP_KEY,
    "appsecret": APP_SECRET,
    "tr_id": "HHDFS00000300",
    "custtype": "P"
}
params_price = {
    "AUTH": "",
    "EXCD": "NAS",
    "SYMB": "SOXL"
}

r = requests.get(url_price, headers=headers_price, params=params_price)
print(f"HTTP: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    if data.get('rt_cd') == '0':
        price = data.get('output', {}).get('last', 'N/A')
        print(f"성공! SOXL: ${price}\n")
    else:
        print(f"실패: {data.get('msg1')}\n")

# 잔고 조회
print("[2] 잔고 조회")
url_balance = f"{BASE}/uapi/overseas-stock/v1/trading/inquire-balance"
headers_balance = {
    "Content-Type": "application/json; charset=utf-8",
    "authorization": f"Bearer {token}",
    "appkey": APP_KEY,
    "appsecret": APP_SECRET,
    "tr_id": "TTTS3012R",
    "custtype": "P"
}
params_balance = {
    "CANO": "43113014",
    "ACNT_PRDT_CD": "01",
    "OVRS_EXCG_CD": "NASD",
    "TR_CRCY_CD": "USD",
    "CTX_AREA_FK200": "",
    "CTX_AREA_NK200": ""
}

r2 = requests.get(url_balance, headers=headers_balance, params=params_balance)
print(f"HTTP: {r2.status_code}")

if r2.status_code == 200:
    result = r2.json()
    rt_cd = result.get('rt_cd')
    msg1 = result.get('msg1', '')

    print(f"rt_cd: {rt_cd}")
    print(f"msg1: {msg1}")

    if rt_cd == '0':
        print("\n[성공] 잔고 조회 성공!")

        # output2 확인
        if 'output2' in result:
            output2 = result['output2']
            print(f"\noutput2 타입: {type(output2)}")

            if isinstance(output2, list) and output2:
                balance_info = output2[0]
                print("\n[USD 잔고 관련 필드]")
                for key in ['frcr_buy_amt_smtl1', 'frcr_dncl_amt_2', 'tot_asst_amt', 'frcr_evlu_amt2']:
                    if key in balance_info:
                        val = balance_info[key]
                        try:
                            print(f"  {key}: ${float(val):,.2f}")
                        except:
                            print(f"  {key}: {val}")

                print("\n[전체 필드]")
                for k, v in balance_info.items():
                    print(f"  {k}: {v}")
    else:
        print(f"\n[실패] {msg1}")
else:
    print(f"HTTP 오류: {r2.text[:100]}")
