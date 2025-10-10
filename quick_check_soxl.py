#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

r = requests.get(url, headers=headers, params=params, timeout=10)
data = r.json()

found = False
for s in data.get('output1', []):
    if s.get('ovrs_pdno') == 'SOXL':
        found = True
        print(f"SOXL: {s.get('ovrs_cblc_qty')}주 @ ${s.get('now_pric2')} | 손익: {s.get('evlu_pfls_rt')}%")

if not found:
    print("SOXL 보유 없음")
