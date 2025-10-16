#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚠️ 중요: 기존 kis_token.json의 토큰 사용!
SOXL PDNO 확인
"""
import json
import yaml
import requests

# 설정 로드
with open('kis_devlp.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# ⚠️ 기존 토큰 사용!
with open('kis_token.json', 'r', encoding='utf-8') as f:
    token_data = json.load(f)

app_key = config['my_app']
app_secret = config['my_sec']
account_no = config['my_acct']
access_token = token_data['access_token']
base_url = "https://openapi.koreainvestment.com:9443"

print("="*80)
print("SOXL PDNO 확인")
print("="*80)

url = f"{base_url}/uapi/overseas-stock/v1/trading/inquire-balance"

headers = {
    "authorization": f"Bearer {access_token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": "TTTS3012R"
}

params = {
    "CANO": account_no.split('-')[0],
    "ACNT_PRDT_CD": account_no.split('-')[1],
    "OVRS_EXCG_CD": "NASD",
    "TR_CRCY_CD": "USD",
    "CTX_AREA_FK200": "",
    "CTX_AREA_NK200": ""
}

response = requests.get(url, headers=headers, params=params, timeout=10)

if response.status_code == 200:
    data = response.json()
    if data.get('rt_cd') == '0':
        for stock in data.get('output1', []):
            print(f"\nRaw Data:")
            print(json.dumps(stock, indent=2, ensure_ascii=False))

            if 'SOXL' in stock.get('ovrs_pdno', '').upper() or 'SOXL' in stock.get('ovrs_item_name', '').upper():
                print(f"\n*** SOXL 발견! ***")
                print(f"ovrs_pdno: {stock.get('ovrs_pdno')}")
                print(f"pdno: {stock.get('pdno')}")
                print(f"ovrs_item_name: {stock.get('ovrs_item_name')}")
                break
    else:
        print(f"조회 실패: {data.get('msg1')}")
else:
    print(f"HTTP 오류: {response.status_code}")

print("="*80)
