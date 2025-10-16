#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KIS 시장가 매수 테스트 (Method 2)"""
import json
import yaml
import requests

print("="*80)
print("KIS 시장가 매수 테스트 (SOXL)")
print("="*80)

# 설정 로드
with open('kis_devlp.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

with open('kis_token.json', 'r', encoding='utf-8') as f:
    token_data = json.load(f)

app_key = config['my_app']
app_secret = config['my_sec']
account_no = config['my_acct']
access_token = token_data['access_token']
base_url = "https://openapi.koreainvestment.com:9443"

# SOXL 현재가
print("\n[1] SOXL 현재가 조회...")
fmp_url = "https://financialmodelingprep.com/api/v3/quote/SOXL"
fmp_response = requests.get(fmp_url, params={'apikey': '5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI'}, timeout=10)
current_price = 0
if fmp_response.status_code == 200:
    fmp_data = fmp_response.json()
    if fmp_data:
        current_price = fmp_data[0].get('price', 0)
        print(f"SOXL 현재가: ${current_price:.2f}")

if current_price <= 0:
    print("[ERROR] 가격 조회 실패")
    exit(1)

# 시장가 매수
print(f"\n[2] SOXL 1주 시장가 매수...")
order_url = f"{base_url}/uapi/overseas-stock/v1/trading/order"

headers = {
    "authorization": f"Bearer {access_token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": "JTTT1002U",
    "custtype": "P",
    "content-type": "application/json; charset=utf-8"
}

# 시장가: ORD_DVSN="01"
order_data = {
    "CANO": account_no.split('-')[0],
    "ACNT_PRDT_CD": account_no.split('-')[1],
    "OVRS_EXCG_CD": "NASD",
    "PDNO": "SOXL",  # 티커명 직접 사용
    "ORD_QTY": "1",
    "OVRS_ORD_UNPR": "0",  # 시장가는 0
    "ORD_SVR_DVSN_CD": "0",
    "SLL_TYPE": "",
    "ORD_DVSN": "01"  # 01=시장가
}

print("\n[3] 주문 데이터 (시장가):")
print(json.dumps(order_data, indent=2, ensure_ascii=False))

try:
    response = requests.post(order_url, headers=headers, json=order_data, timeout=30)

    print(f"\n[4] 응답:")
    print(f"  HTTP 상태: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"  rt_cd: {result.get('rt_cd')}")
        print(f"  msg_cd: {result.get('msg_cd')}")
        print(f"  msg1: {result.get('msg1')}")

        if result.get('rt_cd') == '0':
            print(f"\n[SUCCESS] 시장가 매수 성공!")
            exit(0)
        else:
            print(f"\n[ERROR] 시장가 실패")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            exit(1)
    else:
        print(f"\n[ERROR] HTTP {response.status_code}")
        print(response.text)
        exit(1)

except Exception as e:
    print(f"\n[ERROR] 예외: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
