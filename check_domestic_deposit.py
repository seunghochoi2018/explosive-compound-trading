#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
국내 계좌의 외화 예수금 조회
"""

import yaml
import requests
import json
import os

yaml_path = os.path.join(os.path.dirname(__file__), 'kis_devlp.yaml')
with open(yaml_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

print("="*80)
print("국내 계좌 예수금 조회 (외화 포함)")
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
acct_parts = config['my_acct'].split('-')
cano = acct_parts[0]
acnt_prdt_cd = acct_parts[1] if len(acct_parts) > 1 else "01"

# API: 국내주식 예수금 조회 (TTTC8908R / VTTC8908R)
print("="*80)
print("API: 국내주식 예수금 조회")
print("="*80)

deposit_url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/trading/inquire-psbl-deposit"

tr_ids = [
    ("TTTC8908R", "실전"),
    ("VTTC8908R", "모의"),
]

for tr_id, acc_type in tr_ids:
    print(f"\n[{acc_type}계좌 - {tr_id}]")

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {access_token}",
        "appkey": config['my_app'],
        "appsecret": config['my_sec'],
        "tr_id": tr_id,
        "custtype": "P",
        "User-Agent": config['my_agent']
    }

    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "INQR_DVSN_1": "",
        "INQR_DVSN_2": ""
    }

    response = requests.get(deposit_url, headers=headers, params=params, timeout=10)

    print(f"HTTP: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"rt_cd: {result.get('rt_cd')}")
        print(f"msg1: {result.get('msg1')}")

        if result.get('rt_cd') == '0':
            output = result.get('output', {})

            print(f"\n[예수금 정보]")
            for key, value in output.items():
                print(f"  {key}: {value}")

            # 주요 필드
            dnca_tot_amt = output.get('dnca_tot_amt', '0')  # 예수금총액
            nxdy_excc_amt = output.get('nxdy_excc_amt', '0')  # 익일정산금액
            prvs_rcdl_excc_amt = output.get('prvs_rcdl_excc_amt', '0')  # 가수도정산금액

            try:
                total_deposit = float(dnca_tot_amt.replace(',', ''))
                print(f"\n*** 예수금총액: {total_deposit:,.0f}원")
            except:
                print(f"\n변환 오류")

        else:
            print(f"[실패] {result.get('msg1')}")
    else:
        print(f"응답: {response.text[:200]}")

print("\n" + "="*80)
print("결론: 국내 원화 예수금만 조회됩니다.")
print("USD 현금은 별도로 관리되므로 다른 방법이 필요합니다.")
print("="*80)
