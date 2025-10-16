#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚠️ 중요: 기존 kis_token.json의 토큰 사용!
SOXL 전량 매도
"""
import json
import yaml
import requests

print("="*80)
print("SOXL 전량 매도")
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

# 1. 잔고 조회로 SOXL 보유 수량 확인
print("\n[1] SOXL 보유 수량 확인...")
balance_url = f"{base_url}/uapi/overseas-stock/v1/trading/inquire-balance"

balance_headers = {
    "authorization": f"Bearer {access_token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": "TTTS3012R"
}

balance_params = {
    "CANO": account_no.split('-')[0],
    "ACNT_PRDT_CD": account_no.split('-')[1],
    "OVRS_EXCG_CD": "NASD",
    "TR_CRCY_CD": "USD",
    "CTX_AREA_FK200": "",
    "CTX_AREA_NK200": ""
}

response = requests.get(balance_url, headers=balance_headers, params=balance_params, timeout=10)

soxl_qty = 0
current_price = 0

if response.status_code == 200:
    data = response.json()
    if data.get('rt_cd') == '0':
        for stock in data.get('output1', []):
            if 'SOXL' in stock.get('ovrs_pdno', '').upper():
                soxl_qty = int(stock.get('ovrs_cblc_qty', 0))
                current_price = float(stock.get('now_pric2', 0))
                print(f"SOXL 보유: {soxl_qty}주")
                print(f"현재가: ${current_price:.2f}")
                break

if soxl_qty <= 0:
    print("\n[오류] SOXL 보유 없음!")
    exit(1)

# 2. 전량 매도
print(f"\n{'='*80}")
print(f"[2] SOXL {soxl_qty}주 전량 매도")
print(f"{'='*80}")

order_url = f"{base_url}/uapi/overseas-stock/v1/trading/order"

sell_data = {
    "CANO": account_no.split('-')[0],
    "ACNT_PRDT_CD": account_no.split('-')[1],
    "OVRS_EXCG_CD": "AMEX",  # ⚠️ AMEX
    "PDNO": "SOXL",  # ⚠️ 티커 직접
    "ORD_QTY": str(soxl_qty),  # 전량
    "OVRS_ORD_UNPR": f"{current_price:.2f}",  # ⚠️ 소수점 2자리
    "ORD_SVR_DVSN_CD": "0",
    "ORD_DVSN": "00"  # 지정가
}

print(f"\n매도 주문 데이터:")
print(json.dumps(sell_data, indent=2, ensure_ascii=False))

hashkey = generate_hashkey(sell_data)
print(f"\nHashkey: {hashkey[:20]}...")

sell_headers = {
    "authorization": f"Bearer {access_token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": "TTTT1006U",  # 매도
    "custtype": "P",
    "hashkey": hashkey,
    "Content-Type": "application/json"
}

print(f"\n매도 주문 전송 중...")
sell_response = requests.post(order_url, headers=sell_headers, json=sell_data, timeout=30)

print(f"\n응답:")
print(f"HTTP: {sell_response.status_code}")

if sell_response.status_code == 200:
    result = sell_response.json()
    print(f"rt_cd: {result.get('rt_cd')}")
    print(f"msg_cd: {result.get('msg_cd')}")
    print(f"msg1: {result.get('msg1')}")

    if result.get('rt_cd') == '0':
        order_id = result.get('output', {}).get('ODNO', 'N/A')
        print(f"\n{'='*80}")
        print(f"[SUCCESS] SOXL {soxl_qty}주 전량 매도 성공!")
        print(f"{'='*80}")
        print(f"주문번호: {order_id}")
        print(f"수량: {soxl_qty}주")
        print(f"가격: ${current_price:.2f}")
        print(f"총 금액: ${current_price * soxl_qty:.2f}")
    else:
        print(f"\n[FAIL] 매도 실패: {result.get('msg1')}")
        print(f"상세: {result}")
else:
    print(f"[FAIL] HTTP ERROR: {sell_response.text[:200]}")

print(f"\n{'='*80}")
