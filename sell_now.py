#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import requests
import yaml
import json

# KIS API 설정
with open('../코드/kis_devlp.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

app_key = config['my_app']
app_secret = config['my_sec']
account_no = config['my_acct']
base_url = "https://openapi.koreainvestment.com:9443"

# 기존 토큰 사용
with open('kis_token.json', 'r', encoding='utf-8') as f:
    token_data = json.load(f)
access_token = token_data['access_token']

print("SOXL 긴급 청산 (기존 토큰 사용)")

# 보유 수량 확인
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
            if stock.get('ovrs_pdno') == 'SOXL':
                qty = int(stock.get('ovrs_cblc_qty', 0))
                avg = float(stock.get('pchs_avg_pric', 0))
                now = float(stock.get('now_pric2', 0))
                pnl = float(stock.get('evlu_pfls_rt', 0))

                print(f"SOXL {qty}주, ${avg:.2f} -> ${now:.2f}, {pnl}%")

                if qty > 0:
                    print(f"매도 주문 전송...")

                    sell_url = f"{base_url}/uapi/overseas-stock/v1/trading/order"
                    sell_headers = {
                        "authorization": f"Bearer {access_token}",
                        "appkey": app_key,
                        "appsecret": app_secret,
                        "tr_id": "TTTT1006U"
                    }
                    sell_data = {
                        "CANO": account_no.split('-')[0],
                        "ACNT_PRDT_CD": account_no.split('-')[1],
                        "OVRS_EXCG_CD": "NASD",
                        "PDNO": "SOXL",
                        "ORD_QTY": str(qty),
                        "OVRS_ORD_UNPR": "0",
                        "ORD_SVR_DVSN_CD": "0"
                    }

                    sell_resp = requests.post(sell_url, headers=sell_headers, json=sell_data, timeout=10)
                    print(f"Status: {sell_resp.status_code}")

                    if sell_resp.status_code == 200:
                        result = sell_resp.json()
                        print(f"Response: {result}")
                        if result.get('rt_cd') == '0':
                            print(f"OK 청산 완료!")
                        else:
                            print(f"FAIL: {result.get('msg1')}")
                else:
                    print("보유 없음")
                break
