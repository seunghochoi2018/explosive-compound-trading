#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚠️ 중요: 기존 kis_token.json의 토큰 사용!
SOXL 1주 재매수 테스트
"""
import json
import yaml
import requests

print("="*80)
print("SOXL 1주 재매수")
print("="*80)

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

# Hashkey 생성 함수
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
    except Exception as e:
        print(f"Hashkey 생성 오류: {e}")
        return ""

# SOXL 현재가 재조회
fmp_url = "https://financialmodelingprep.com/api/v3/quote/SOXL"
fmp_response = requests.get(fmp_url, params={'apikey': '5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI'}, timeout=10)
current_price = 0
if fmp_response.status_code == 200:
    fmp_data = fmp_response.json()
    if fmp_data:
        current_price = fmp_data[0].get('price', 0)
        print(f"\nSOXL 현재가 (재조회): ${current_price:.2f}")

if current_price <= 0:
    print("가격 조회 실패!")
    exit(1)

order_url = f"{base_url}/uapi/overseas-stock/v1/trading/order"

# 매수 데이터
buy_data = {
    "CANO": account_no.split('-')[0],
    "ACNT_PRDT_CD": account_no.split('-')[1],
    "OVRS_EXCG_CD": "AMEX",  # ⚠️ AMEX
    "PDNO": "SOXL",  # ⚠️ 티커 그대로
    "ORD_QTY": "1",
    "OVRS_ORD_UNPR": f"{current_price:.2f}",  # ⚠️ 소수점 2자리
    "ORD_SVR_DVSN_CD": "0",
    "ORD_DVSN": "00"  # 지정가
}

print(f"\n매수 주문 데이터:")
print(json.dumps(buy_data, indent=2, ensure_ascii=False))

hashkey = generate_hashkey(buy_data)
print(f"\nHashkey: {hashkey[:20]}...")

buy_headers = {
    "authorization": f"Bearer {access_token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": "TTTT1002U",  # ⚠️ 매수
    "custtype": "P",
    "hashkey": hashkey,
    "Content-Type": "application/json"
}

print(f"\n매수 주문 전송 중...")
response = requests.post(order_url, headers=buy_headers, json=buy_data, timeout=30)

print(f"\n응답:")
print(f"HTTP: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"rt_cd: {result.get('rt_cd')}")
    print(f"msg_cd: {result.get('msg_cd')}")
    print(f"msg1: {result.get('msg1')}")

    if result.get('rt_cd') == '0':
        print(f"\n{'='*80}")
        print(f"[SUCCESS] SOXL 1주 재매수 성공!")
        print(f"{'='*80}")
        print(f"주문번호: {result.get('output', {}).get('ODNO', 'N/A')}")
        print(f"가격: ${current_price:.2f}")
        print(f"\n[테스트 완료] 매도 -> 재매수 성공!")
    else:
        print(f"\n[FAIL] {result.get('msg1')}")
else:
    print(f"HTTP ERROR: {response.text[:200]}")

print(f"\n{'='*80}")
