#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
import requests
import yaml
import json

with open('../코드/kis_devlp.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

with open('kis_token.json', 'r') as f:
    access_token = json.load(f)['access_token']

account_no = config['my_acct']
url = 'https://openapi.koreainvestment.com:9443/uapi/overseas-stock/v1/trading/inquire-balance'

headers = {
    'authorization': f'Bearer {access_token}',
    'appkey': config['my_app'],
    'appsecret': config['my_sec'],
    'tr_id': 'TTTS3012R'
}

params = {
    'CANO': account_no.split('-')[0],
    'ACNT_PRDT_CD': account_no.split('-')[1],
    'OVRS_EXCG_CD': 'NASD',
    'TR_CRCY_CD': 'USD',
    'CTX_AREA_FK200': '',
    'CTX_AREA_NK200': ''
}

print("="*60)
print("SOXL 보유 정보 상세 조회")
print("="*60)

r = requests.get(url, headers=headers, params=params, timeout=10)
print(f"\n응답 코드: {r.status_code}")

if r.status_code == 200:
    data = r.json()
    print(f"rt_cd: {data.get('rt_cd')}")
    print(f"msg_cd: {data.get('msg_cd')}")
    print(f"msg1: {data.get('msg1')}")

    if data.get('rt_cd') == '0':
        for stock in data.get('output1', []):
            if stock.get('ovrs_pdno') == 'SOXL':
                print(f"\nSOXL 상세 정보:")
                print(json.dumps(stock, indent=2))
                break
    else:
        print(f"\nAPI 오류: {data}")
else:
    print(f"HTTP 오류: {r.text}")
