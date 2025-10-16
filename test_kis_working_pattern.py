#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KIS API 테스트 - Working 패턴 적용"""
import json
import yaml
import requests

print("="*80)
print("KIS API 테스트 - Working 패턴 (2024-10-08 성공 패턴)")
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
    current_price = 40.0  # Fallback
    print(f"SOXL 가격 조회 실패, fallback: ${current_price:.2f}")

# 매수 주문 시도 (Working 패턴)
print(f"\n[2] SOXL 1주 매수 주문 테스트 (Working 패턴)...")

order_url = f"{base_url}/uapi/overseas-stock/v1/trading/order"

# Working 패턴 헤더 (kis_sell_tsll_working.py에서 확인)
headers = {
    "authorization": f"Bearer {access_token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": "TTTT1002U",  # ✅ TTTT (T 4개!)
    "custtype": "P",
    "Content-Type": "application/json"
}

# Working 패턴 데이터 (지정가 주문)
order_data = {
    "CANO": account_no.split('-')[0],
    "ACNT_PRDT_CD": account_no.split('-')[1],
    "OVRS_EXCG_CD": "NASD",
    "PDNO": "A980679",  # SOXL
    "ORD_QTY": "1",
    "OVRS_ORD_UNPR": str(current_price),  # 현재가
    "ORD_SVR_DVSN_CD": "0",
    "ORD_DVSN": "01"  # ✅ 01=지정가 (working 코드 패턴)
}

print("\n[3] 요청 정보:")
print(f"TR_ID: TTTT1002U (해외주식 매수)")
print(f"종목코드: A980679 (SOXL)")
print(f"수량: 1주")
print(f"가격: ${current_price:.2f}")
print(f"주문구분: 01 (지정가)")

try:
    response = requests.post(order_url, headers=headers, json=order_data, timeout=30)

    print(f"\n[4] 응답:")
    print(f"HTTP 상태: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"rt_cd: {result.get('rt_cd')}")
        print(f"msg_cd: {result.get('msg_cd')}")
        print(f"msg1: {result.get('msg1')}")

        if result.get('rt_cd') == '0':
            order_id = result.get('output', {}).get('ODNO', 'N/A')
            print(f"\n{'='*80}")
            print(f"[SUCCESS] SOXL 1주 매수 주문 성공!")
            print(f"{'='*80}")
            print(f"주문번호: {order_id}")
            print(f"종목: SOXL (A980679)")
            print(f"가격: ${current_price:.2f}")
            print(f"패턴: Working 패턴 (2024-10-08 성공 방식)")
            print(f"\n[FIX] EGW00356 에러 해결:")
            print(f"  1. TR_ID: JTTT → TTTT (T 4개!)")
            print(f"  2. SLL_TYPE 필드 제거")
            print(f"  3. ORD_DVSN: 00 (시장가)")
            print(f"  4. Content-Type: 대문자 시작")
        else:
            print(f"\n[FAIL] 매수 주문 실패")
            print(f"오류: {result.get('msg1')}")
            print(f"상세: {result}")
    else:
        try:
            result = response.json()
            print(f"[FAIL] {result.get('msg_cd')}: {result.get('msg1')}")
        except:
            print(f"[FAIL] HTTP ERROR: {response.text[:200]}")

except Exception as e:
    print(f"\n[ERROR] 예외 발생: {e}")
    import traceback
    traceback.print_exc()

print(f"\n{'='*80}")
print("[테스트 완료]")
print(f"{'='*80}")
