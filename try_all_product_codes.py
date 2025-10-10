#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
모든 상품코드로 USD 잔고 조회 시도
"""

import yaml
import requests
import json
import os

yaml_path = os.path.join(os.path.dirname(__file__), 'kis_devlp.yaml')
with open(yaml_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

print("="*80)
print("모든 상품코드로 USD 잔고 조회")
print("="*80)

# 토큰 로드
try:
    with open('kis_token.json', 'r') as f:
        token_data = json.load(f)
        access_token = token_data['access_token']
        print(f"토큰 로드 성공\n")
except:
    print("토큰 파일 없음")
    exit(1)

# 계좌번호
cano = "43113014"

# 가능한 상품코드들
product_codes = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10"]

balance_url = "https://openapi.koreainvestment.com:9443/uapi/overseas-stock/v1/trading/inquire-balance"

for prod_cd in product_codes:
    print("="*80)
    print(f"상품코드: {cano}-{prod_cd}")
    print("="*80)

    balance_headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {access_token}",
        "appkey": config['my_app'],
        "appsecret": config['my_sec'],
        "tr_id": "JTTT3012R",
        "custtype": "P",
        "User-Agent": config['my_agent']
    }

    balance_params = {
        "CANO": cano,
        "ACNT_PRDT_CD": prod_cd,
        "OVRS_EXCG_CD": "NASD",
        "TR_CRCY_CD": "USD",
        "CTX_AREA_FK200": "",
        "CTX_AREA_NK200": ""
    }

    response = requests.get(balance_url, headers=balance_headers, params=balance_params, timeout=10)

    if response.status_code == 200:
        result = response.json()

        if result.get('rt_cd') == '0':
            output1 = result.get('output1', [])
            output2 = result.get('output2', {})

            # 보유 종목
            holdings = []
            for item in output1:
                symbol = item.get('ovrs_pdno', '')
                qty = float(item.get('ovrs_cblc_qty', '0'))
                if qty > 0:
                    holdings.append(f"{symbol} {qty}주")

            print(f"[SUCCESS] 계좌 조회 성공!")
            print(f"  보유종목: {', '.join(holdings) if holdings else '없음'}")

            # output2에서 값이 0이 아닌 필드
            non_zero_fields = {}
            for key, value in output2.items():
                try:
                    if float(value) != 0:
                        non_zero_fields[key] = value
                except:
                    if value:
                        non_zero_fields[key] = value

            if non_zero_fields:
                print(f"  output2 (0이 아닌 값):")
                for key, value in non_zero_fields.items():
                    print(f"    {key}: {value}")

                # USD 현금 후보
                cash_fields = ['frcr_dncl_amt_2', 'frcr_buy_amt_smtl1', 'ovrs_ord_psbl_amt']
                for field in cash_fields:
                    if field in non_zero_fields:
                        try:
                            cash_val = float(non_zero_fields[field])
                            if cash_val > 0:
                                print(f"\n  *** USD 현금 발견: {field} = ${cash_val:.2f}")
                        except:
                            pass
            else:
                print(f"  output2: 모든 값이 0 또는 빈값")

        else:
            print(f"[FAIL] {result.get('msg1')}")

    else:
        print(f"[HTTP ERROR] {response.status_code}")

    print()

print("="*80)
print("완료")
print("="*80)
