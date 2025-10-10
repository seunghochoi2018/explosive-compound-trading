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

with open('../코드/kis_devlp.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

app_key = config['my_app']
app_secret = config['my_sec']
account_no = config['my_acct']
base_url = "https://openapi.koreainvestment.com:9443"

with open('kis_token.json', 'r') as f:
    access_token = json.load(f)['access_token']

def generate_hashkey(data_dict):
    try:
        hash_url = f"{base_url}/uapi/hashkey"
        hash_headers = {
            "appkey": app_key,
            "appsecret": app_secret,
            "content-type": "application/json"
        }
        hash_response = requests.post(hash_url, headers=hash_headers, json=data_dict, timeout=5)
        if hash_response.status_code == 200:
            return hash_response.json().get('HASH', '')
        return ""
    except:
        return ""

print("="*60)
print("SOXL 매도 (NASD)")
print("="*60)

# NASD로 조회
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
                current_price = float(stock.get('now_pric2', 0))

                print(f"\n보유:")
                print(f"  수량: {qty}주")
                print(f"  현재가: ${current_price:.2f}")

                if qty > 0:
                    # 매도 주문 Body (NASD 사용)
                    sell_data = {
                        "CANO": account_no.split('-')[0],
                        "ACNT_PRDT_CD": account_no.split('-')[1],
                        "OVRS_EXCG_CD": "NASD",
                        "PDNO": "A980679",
                        "ORD_QTY": str(qty),
                        "OVRS_ORD_UNPR": "0",  # 시장가
                        "ORD_SVR_DVSN_CD": "0"
                    }

                    hashkey = generate_hashkey(sell_data)

                    print(f"\n전체 Body:")
                    print(json.dumps(sell_data, indent=2))

                    sell_url = f"{base_url}/uapi/overseas-stock/v1/trading/order"
                    sell_headers = {
                        "authorization": f"Bearer {access_token}",
                        "appkey": app_key,
                        "appsecret": app_secret,
                        "tr_id": "TTTT1006U",
                        "custtype": "P",
                        "hashkey": hashkey,
                        "content-type": "application/json"
                    }

                    print(f"\n매도 시도...")
                    sell_resp = requests.post(sell_url, headers=sell_headers, json=sell_data, timeout=10)

                    print(f"Status: {sell_resp.status_code}")
                    result = sell_resp.json()
                    print(f"rt_cd: {result.get('rt_cd')}")
                    print(f"msg_cd: {result.get('msg_cd')}")
                    print(f"msg1: {result.get('msg1')}")

                    if result.get('rt_cd') == '0':
                        print(f"\n✅ 청산 완료!")
                    else:
                        print(f"\n❌ 실패")
                break
