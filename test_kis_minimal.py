#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KIS 최소 필드 매수 테스트 - 필수 필드만 사용"""
import json
import yaml
import requests

print("="*80)
print("KIS 최소 필드 매수 테스트")
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

# 현재가
print("\n[1] SOXL 현재가...")
fmp_url = "https://financialmodelingprep.com/api/v3/quote/SOXL"
fmp_response = requests.get(fmp_url, params={'apikey': '5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI'}, timeout=10)
current_price = 0
if fmp_response.status_code == 200:
    fmp_data = fmp_response.json()
    if fmp_data:
        current_price = fmp_data[0].get('price', 0)
        print(f"SOXL: ${current_price:.2f}")

if current_price <= 0:
    print("[ERROR] 가격 조회 실패")
    exit(1)

# 다양한 조합 시도
test_cases = [
    {
        "name": "Case 1: PDNO=A980679 (고유코드)",
        "data": {
            "CANO": account_no.split('-')[0],
            "ACNT_PRDT_CD": account_no.split('-')[1],
            "OVRS_EXCG_CD": "NASD",
            "PDNO": "A980679",
            "ORD_QTY": "1",
            "OVRS_ORD_UNPR": str(current_price),
            "ORD_SVR_DVSN_CD": "0"
        }
    },
    {
        "name": "Case 2: PDNO=SOXL (티커)",
        "data": {
            "CANO": account_no.split('-')[0],
            "ACNT_PRDT_CD": account_no.split('-')[1],
            "OVRS_EXCG_CD": "NASD",
            "PDNO": "SOXL",
            "ORD_QTY": "1",
            "OVRS_ORD_UNPR": str(current_price),
            "ORD_SVR_DVSN_CD": "0"
        }
    },
    {
        "name": "Case 3: 추가 필드 없이",
        "data": {
            "CANO": account_no.split('-')[0],
            "ACNT_PRDT_CD": account_no.split('-')[1],
            "OVRS_EXCG_CD": "NASD",
            "PDNO": "A980679",
            "ORD_QTY": "1",
            "OVRS_ORD_UNPR": str(current_price)
        }
    }
]

order_url = f"{base_url}/uapi/overseas-stock/v1/trading/order"

for idx, test in enumerate(test_cases, 1):
    print(f"\n{'='*80}")
    print(f"[TEST {idx}] {test['name']}")
    print(f"{'='*80}")

    headers = {
        "authorization": f"Bearer {access_token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": "JTTT1002U",
        "custtype": "P",
        "content-type": "application/json; charset=utf-8"
    }

    print(json.dumps(test['data'], indent=2, ensure_ascii=False))

    try:
        response = requests.post(order_url, headers=headers, json=test['data'], timeout=30)

        print(f"\n응답: HTTP {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"rt_cd: {result.get('rt_cd')}")
            print(f"msg_cd: {result.get('msg_cd')}")
            print(f"msg1: {result.get('msg1')}")

            if result.get('rt_cd') == '0':
                print(f"\n[SUCCESS] {test['name']} 성공!")
                exit(0)
            else:
                print(f"[FAIL] {test['name']}")
        else:
            print(f"[FAIL] HTTP {response.status_code}")
            try:
                print(response.json())
            except:
                print(response.text)

    except Exception as e:
        print(f"[ERROR] {e}")

print("\n모든 테스트 실패")
exit(1)
