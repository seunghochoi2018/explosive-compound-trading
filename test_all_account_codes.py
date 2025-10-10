#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
모든 계좌 상품코드 테스트
"""

import yaml
import requests
import json
import os

yaml_path = os.path.join(os.path.dirname(__file__), 'kis_devlp.yaml')
with open(yaml_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

print("="*80)
print("모든 계좌 상품코드 잔고 조회 테스트")
print("="*80)

# 토큰 발급
token_url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
headers = {
    "Content-Type": "application/json",
    "User-Agent": config['my_agent']
}
data = {
    "grant_type": "client_credentials",
    "appkey": config['my_app'],
    "appsecret": config['my_sec']
}

response = requests.post(token_url, headers=headers, json=data, timeout=30)

if response.status_code != 200:
    print(f"토큰 발급 실패: {response.text}")
    exit(1)

access_token = response.json().get("access_token")
print(f"토큰 발급 성공!\n")

# 계좌번호 파싱
acct_parts = config['my_acct'].split('-')
cano = acct_parts[0]

# 모든 가능한 계좌 상품코드 시도
account_codes = ["01", "02", "03", "11", "12", "13"]

balance_url = "https://openapi.koreainvestment.com:9443/uapi/overseas-stock/v1/trading/inquire-balance"

for acnt_prdt_cd in account_codes:
    print(f"\n{'='*80}")
    print(f"계좌 상품코드: {acnt_prdt_cd} (계좌: {cano}-{acnt_prdt_cd})")
    print(f"{'='*80}")

    balance_headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {access_token}",
        "appkey": config['my_app'],
        "appsecret": config['my_sec'],
        "tr_id": "TTTS3012R",
        "custtype": "P"
    }

    balance_params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "OVRS_EXCG_CD": "NASD",
        "TR_CRCY_CD": "USD",
        "CTX_AREA_FK200": "",
        "CTX_AREA_NK200": ""
    }

    balance_response = requests.get(balance_url, headers=balance_headers, params=balance_params, timeout=10)

    print(f"HTTP: {balance_response.status_code}")

    if balance_response.status_code == 200:
        balance_result = balance_response.json()
        print(f"rt_cd: {balance_result.get('rt_cd')}")
        print(f"msg1: {balance_result.get('msg1')}")

        if balance_result.get('rt_cd') == '0':
            output2 = balance_result.get('output2')
            if output2:
                if isinstance(output2, list) and output2:
                    bal_info = output2[0]
                elif isinstance(output2, dict):
                    bal_info = output2
                else:
                    bal_info = {}

                # 모든 금액 필드 확인
                usd_balance = bal_info.get('frcr_buy_amt_smtl1', '0')
                frcr_pchs_amt1 = bal_info.get('frcr_pchs_amt1', '0')
                tot_evlu_pfls_amt = bal_info.get('tot_evlu_pfls_amt', '0')

                print(f"\n  frcr_buy_amt_smtl1 (외화매수금액합계1): ${usd_balance}")
                print(f"  frcr_pchs_amt1 (외화매입금액1): {frcr_pchs_amt1}")
                print(f"  tot_evlu_pfls_amt (총평가손익금액): ${tot_evlu_pfls_amt}")

                # USD 잔고가 0이 아니면 강조
                if float(usd_balance) > 0:
                    print(f"\n  >>> USD 잔고 발견! ${float(usd_balance):.2f}")
                    print(f"  >>> 이 계좌 상품코드를 사용하세요: {acnt_prdt_cd}")
        else:
            print(f"  (조회 실패 또는 오류)")
    else:
        print(f"  HTTP 오류: {balance_response.status_code}")

print(f"\n{'='*80}")
print(f"테스트 완료")
print(f"{'='*80}")
