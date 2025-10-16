#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚠️ 중요: 기존 kis_token.json의 토큰 사용!
SOXL 1주 매도 → 재매수 테스트 (Hashkey 포함)
"""
import json
import yaml
import requests
import time
from datetime import datetime

print("="*80)
print("SOXL 1주 매도 → 재매수 테스트 (Hashkey 포함)")
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
access_token = token_data['access_token']  # ⚠️ 기존 토큰!
base_url = "https://openapi.koreainvestment.com:9443"

print(f"\n[INFO] 토큰: {access_token[:20]}...")

# Hashkey 생성 함수
def generate_hashkey(data_dict):
    """KIS API Hashkey 생성"""
    try:
        hash_url = f"{base_url}/uapi/hashkey"
        hash_headers = {
            "appkey": app_key,
            "appsecret": app_secret,
            "content-type": "application/json"
        }
        hash_response = requests.post(hash_url, headers=hash_headers, json=data_dict, timeout=5)
        if hash_response.status_code == 200:
            hashkey = hash_response.json().get('HASH', '')
            print(f"[DEBUG] Hashkey 생성 성공: {hashkey[:20]}...")
            return hashkey
        else:
            print(f"[ERROR] Hashkey 생성 실패: {hash_response.status_code}")
            print(f"Response: {hash_response.text}")
            return ""
    except Exception as e:
        print(f"[ERROR] Hashkey 생성 오류: {e}")
        return ""

# SOXL 현재가 조회
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
    print("가격 조회 실패!")
    exit(1)

# ========================================
# STEP 1: SOXL 1주 매도
# ========================================
print(f"\n{'='*80}")
print(f"[STEP 1] SOXL 1주 매도 주문 (Hashkey 포함)")
print(f"{'='*80}")

order_url = f"{base_url}/uapi/overseas-stock/v1/trading/order"

sell_data = {
    "CANO": account_no.split('-')[0],
    "ACNT_PRDT_CD": account_no.split('-')[1],
    "OVRS_EXCG_CD": "NASD",
    "PDNO": "A980679",  # SOXL
    "ORD_QTY": "1",
    "OVRS_ORD_UNPR": str(current_price),
    "ORD_SVR_DVSN_CD": "0",
    "ORD_DVSN": "00"  # 00=시장가
}

print(f"\n매도 주문 데이터:")
print(json.dumps(sell_data, indent=2, ensure_ascii=False))

# Hashkey 생성
hashkey = generate_hashkey(sell_data)
if not hashkey:
    print("\n[ERROR] Hashkey 생성 실패로 중단")
    exit(1)

sell_headers = {
    "authorization": f"Bearer {access_token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": "TTTT1006U",  # 매도
    "custtype": "P",
    "hashkey": hashkey,  # ⚠️ Hashkey 추가!
    "Content-Type": "application/json"
}

print(f"\n매도 주문 전송 중...")
sell_response = requests.post(order_url, headers=sell_headers, json=sell_data, timeout=30)

print(f"\n매도 응답:")
print(f"HTTP 상태: {sell_response.status_code}")

sell_success = False
if sell_response.status_code == 200:
    sell_result = sell_response.json()
    print(f"rt_cd: {sell_result.get('rt_cd')}")
    print(f"msg_cd: {sell_result.get('msg_cd')}")
    print(f"msg1: {sell_result.get('msg1')}")

    if sell_result.get('rt_cd') == '0':
        order_id = sell_result.get('output', {}).get('ODNO', 'N/A')
        print(f"\n{'='*80}")
        print(f"[SUCCESS] SOXL 1주 매도 성공!")
        print(f"{'='*80}")
        print(f"주문번호: {order_id}")
        print(f"가격: ${current_price:.2f}")
        sell_success = True
    else:
        print(f"\n[FAIL] 매도 실패: {sell_result.get('msg1')}")
        print(f"상세: {sell_result}")
else:
    print(f"[FAIL] HTTP ERROR: {sell_response.text[:200]}")

if not sell_success:
    print("\n매도 실패로 테스트 중단")
    exit(1)

# 5초 대기 (체결 시간)
print(f"\n[대기] 5초 후 재매수 진행...")
time.sleep(5)

# ========================================
# STEP 2: SOXL 1주 재매수
# ========================================
print(f"\n{'='*80}")
print(f"[STEP 2] SOXL 1주 재매수 주문 (Hashkey 포함)")
print(f"{'='*80}")

# 현재가 재조회
fmp_response = requests.get(fmp_url, params={'apikey': '5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI'}, timeout=10)
if fmp_response.status_code == 200:
    fmp_data = fmp_response.json()
    if fmp_data:
        current_price = fmp_data[0].get('price', 0)
        print(f"SOXL 현재가 (재조회): ${current_price:.2f}")

buy_data = {
    "CANO": account_no.split('-')[0],
    "ACNT_PRDT_CD": account_no.split('-')[1],
    "OVRS_EXCG_CD": "NASD",
    "PDNO": "A980679",  # SOXL
    "ORD_QTY": "1",
    "OVRS_ORD_UNPR": str(current_price),
    "ORD_SVR_DVSN_CD": "0",
    "ORD_DVSN": "00"  # 00=시장가
}

print(f"\n매수 주문 데이터:")
print(json.dumps(buy_data, indent=2, ensure_ascii=False))

# Hashkey 생성
hashkey = generate_hashkey(buy_data)
if not hashkey:
    print("\n[ERROR] Hashkey 생성 실패로 중단")
    exit(1)

buy_headers = {
    "authorization": f"Bearer {access_token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": "TTTT1002U",  # 매수
    "custtype": "P",
    "hashkey": hashkey,  # ⚠️ Hashkey 추가!
    "Content-Type": "application/json"
}

print(f"\n매수 주문 전송 중...")
buy_response = requests.post(order_url, headers=buy_headers, json=buy_data, timeout=30)

print(f"\n매수 응답:")
print(f"HTTP 상태: {buy_response.status_code}")

if buy_response.status_code == 200:
    buy_result = buy_response.json()
    print(f"rt_cd: {buy_result.get('rt_cd')}")
    print(f"msg_cd: {buy_result.get('msg_cd')}")
    print(f"msg1: {buy_result.get('msg1')}")

    if buy_result.get('rt_cd') == '0':
        order_id = buy_result.get('output', {}).get('ODNO', 'N/A')
        print(f"\n{'='*80}")
        print(f"[SUCCESS] SOXL 1주 재매수 성공!")
        print(f"{'='*80}")
        print(f"주문번호: {order_id}")
        print(f"가격: ${current_price:.2f}")
        print(f"\n[테스트 완료] 매도 → 재매수 성공!")
    else:
        print(f"\n[FAIL] 재매수 실패: {buy_result.get('msg1')}")
        print(f"상세: {buy_result}")
else:
    print(f"[FAIL] HTTP ERROR: {buy_response.text[:200]}")

print(f"\n{'='*80}")
print(f"[테스트 종료] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*80}")
