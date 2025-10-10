#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
해외주식 매수가능금액 조회 (공식 API 방식)
"""

import json
import requests

# 기존 토큰 사용
with open('kis_token.json', 'r') as f:
    token_data = json.load(f)

TOKEN = token_data['access_token']
APP_KEY = "PSi3RlRt3DWtPPKTdYNALowIoeUBgM5mMLYO"
APP_SECRET = "Q7LxW5oIlCeg+doJCkmPDgXw7uy8bjC7ACRQR1GrAzgCF3zH7LziMix/QJgweS+IRU+uM/3GPELXVeOGocKQnHZ+RPeH4bqR1CgFOs9tHmRtGmxCiwt3+1yp7yctt+bBc85eDrIsrX9KfOkrLY+wVuE1tthKYSDyiF2YKrOp/e1PsSD0mdI="
BASE_URL = "https://openapi.koreainvestment.com:9443"
CANO = "43113014"

print("=" * 60)
print("해외주식 매수가능금액 조회 (공식 방식)")
print("=" * 60)

# 해외주식 매수가능금액 조회 API (공식)
url = f"{BASE_URL}/uapi/overseas-stock/v1/trading/inquire-psamount"
headers = {
    "Content-Type": "application/json; charset=utf-8",
    "authorization": f"Bearer {TOKEN}",
    "appkey": APP_KEY,
    "appsecret": APP_SECRET,
    "tr_id": "TTTS3007R",  # 해외주식 매수가능금액 조회
    "custtype": "P"
}

# 여러 상품코드와 거래소 조합 테스트
test_configs = [
    {"prod_cd": "01", "excd": "NASD", "item": "NVDL"},
    {"prod_cd": "01", "excd": "NYSE", "item": "NVDL"},
    {"prod_cd": "02", "excd": "NASD", "item": "NVDL"},
    {"prod_cd": "03", "excd": "NASD", "item": "NVDL"},
    {"prod_cd": "01", "excd": "NAS", "item": "NVDL"},
]

for config in test_configs:
    print(f"\n[테스트] 계좌: {CANO}-{config['prod_cd']}, 거래소: {config['excd']}")

    params = {
        "CANO": CANO,
        "ACNT_PRDT_CD": config['prod_cd'],
        "OVRS_EXCG_CD": config['excd'],
        "OVRS_ORD_UNPR": "89.0",  # NVDL 현재가 기준
        "ITEM_CD": config['item']
    }

    response = requests.get(url, headers=headers, params=params)
    print(f"응답코드: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        if result.get("rt_cd") == "0":
            output = result.get("output", {})

            print(f"  [SUCCESS] 매수가능금액 조회 성공!")
            print(f"  주문가능현금: {output.get('ord_psbl_cash', 'N/A')}")
            print(f"  주문가능금액: {output.get('ord_psbl_frcr_amt', 'N/A')}")
            print(f"  매수가능수량: {output.get('max_ord_psbl_qty', 'N/A')}")

            # 실제 돈이 있는지 확인
            cash = output.get('ord_psbl_cash', '0')
            try:
                cash_val = float(cash.replace(',', ''))
                if cash_val > 0:
                    print(f"  [MONEY FOUND] 이 계좌에 ${cash_val:,.2f} 있습니다!")
            except:
                pass

        else:
            print(f"  [ERROR] {result.get('msg1', '')}")
    else:
        print(f"  [ERROR] HTTP 오류: {response.text}")

print("\n" + "=" * 60)
print("테스트 완료!")