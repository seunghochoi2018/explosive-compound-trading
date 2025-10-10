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
from datetime import datetime

# KIS API 설정
with open('../코드/kis_devlp.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

app_key = config['my_app']
app_secret = config['my_sec']
account_no = config['my_acct']
base_url = "https://openapi.koreainvestment.com:9443"

print("토큰 재발급 중...")
# 새 토큰 발급
url = f"{base_url}/oauth2/tokenP"
data = {
    "grant_type": "client_credentials",
    "appkey": app_key,
    "appsecret": app_secret
}

response = requests.post(url, json=data, timeout=10)
if response.status_code == 200:
    result = response.json()
    access_token = result.get('access_token')
    print(f"OK 토큰 발급 완료")

    # 토큰 저장
    with open('kis_token.json', 'w', encoding='utf-8') as f:
        json.dump({
            'access_token': access_token,
            'issue_time': datetime.now().isoformat()
        }, f, ensure_ascii=False, indent=2)
else:
    print(f"ERROR 토큰 발급 실패")
    sys.exit(1)

# 보유 수량 확인
print("\n보유 현황 조회 중...")
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
        output1 = data.get('output1', [])

        for stock in output1:
            if stock.get('ovrs_pdno') == 'SOXL':
                soxl_qty = int(stock.get('ovrs_cblc_qty', 0))
                soxl_avg = float(stock.get('pchs_avg_pric', 0))
                soxl_now = float(stock.get('now_pric2', 0))
                soxl_pnl = float(stock.get('evlu_pfls_rt', 0))

                print(f"SOXL: {soxl_qty}주, 평단 ${soxl_avg:.2f}, 현재 ${soxl_now:.2f}, 손익 {soxl_pnl}%")

                if soxl_qty > 0:
                    print(f"\n청산 시작... {soxl_qty}주")

                    sell_url = f"{base_url}/uapi/overseas-stock/v1/trading/order"
                    sell_headers = {
                        "authorization": f"Bearer {access_token}",
                        "appkey": app_key,
                        "appsecret": app_secret,
                        "tr_id": "TTTT1006U",  # 실전투자 매도
                        "content-type": "application/json"
                    }

                    sell_data = {
                        "CANO": account_no.split('-')[0],
                        "ACNT_PRDT_CD": account_no.split('-')[1],
                        "OVRS_EXCG_CD": "NASD",
                        "PDNO": "SOXL",
                        "ORD_QTY": str(soxl_qty),
                        "OVRS_ORD_UNPR": "0",
                        "ORD_SVR_DVSN_CD": "0"
                    }

                    sell_response = requests.post(sell_url, headers=sell_headers, json=sell_data, timeout=10)

                    print(f"Status Code: {sell_response.status_code}")
                    print(f"Response: {sell_response.text}")

                    if sell_response.status_code == 200:
                        result = sell_response.json()
                        if result.get('rt_cd') == '0':
                            print(f"OK 청산 완료!")
                        else:
                            print(f"ERROR {result.get('msg1', 'Unknown')}")
                    else:
                        print(f"ERROR API {sell_response.status_code}")
                break
