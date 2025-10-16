#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SOXS 184주 수동 매도"""
import json
import yaml
import requests

# KIS 설정
with open('kis_devlp.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)
    app_key = config['my_app']
    app_secret = config['my_sec']
    account_no = config['my_acct']

# 토큰
with open('kis_token.json', 'r', encoding='utf-8') as f:
    token_data = json.load(f)
    access_token = token_data['access_token']

base_url = "https://openapi.koreainvestment.com:9443"

print("="*80)
print("SOXS 184주 수동 매도 주문")
print("="*80)

# 1. SOXS 현재가 조회
print("\n[1단계] SOXS 현재가 조회...")
price_url = f"{base_url}/uapi/overseas-price/v1/quotations/price"
price_headers = {
    "authorization": f"Bearer {access_token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": "HHDFS00000300",
    "custtype": "P"
}
price_params = {
    "FID_COND_MRKT_DIV_CODE": "N",
    "FID_INPUT_ISCD": "SOXS"
}

price_response = requests.get(price_url, headers=price_headers, params=price_params, timeout=10)
current_price = 0

if price_response.status_code == 200:
    price_data = price_response.json()
    if price_data.get('rt_cd') == '0':
        current_price = float(price_data.get('output', {}).get('stck_prpr', '0'))
        print(f"SOXS 현재가: ${current_price:.2f}")
else:
    print(f"가격 조회 실패: HTTP {price_response.status_code}")

if current_price <= 0:
    print("\n[ERROR] 가격을 가져올 수 없습니다. FMP API로 시도...")
    # FMP API 백업
    fmp_url = "https://financialmodelingprep.com/api/v3/quote/SOXS"
    fmp_response = requests.get(fmp_url, params={'apikey': '5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI'}, timeout=10)
    if fmp_response.status_code == 200:
        fmp_data = fmp_response.json()
        if fmp_data:
            current_price = fmp_data[0].get('price', 0)
            print(f"[FMP] SOXS 현재가: ${current_price:.2f}")

if current_price <= 0:
    print("\n[ABORT] 가격 조회 실패")
    exit(1)

# 2. 매도 주문
print(f"\n[2단계] SOXS 184주 매도 주문 실행 (${current_price:.2f})...")
order_url = f"{base_url}/uapi/overseas-stock/v1/trading/order"
order_headers = {
    "authorization": f"Bearer {access_token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": "JTTT1006U"  # 매도
}

order_data = {
    "CANO": account_no.split('-')[0],
    "ACNT_PRDT_CD": account_no.split('-')[1],
    "OVRS_EXCG_CD": "NASD",
    "PDNO": "A980680",  # SOXS
    "ORD_QTY": "184",
    "OVRS_ORD_UNPR": str(current_price),
    "ORD_SVR_DVSN_CD": "0"
}

print(f"\n주문 데이터:")
print(f"  종목코드: A980680 (SOXS)")
print(f"  수량: 184주")
print(f"  가격: ${current_price:.2f}")
print(f"  거래소: NASDAQ")

order_response = requests.post(order_url, headers=order_headers, json=order_data, timeout=10)

print(f"\n[3단계] 주문 결과 확인...")
if order_response.status_code == 200:
    result = order_response.json()
    print(f"\nAPI 응답:")
    print(f"  rt_cd: {result.get('rt_cd')}")
    print(f"  msg_cd: {result.get('msg_cd')}")
    print(f"  msg1: {result.get('msg1')}")

    if result.get('rt_cd') == '0':
        output = result.get('output', {})
        order_no = output.get('ODNO', 'N/A')
        print(f"\n{'='*80}")
        print(f"[SUCCESS] 매도 주문 성공!")
        print(f"{'='*80}")
        print(f"  주문번호: {order_no}")
        print(f"  종목: SOXS")
        print(f"  수량: 184주")
        print(f"  가격: ${current_price:.2f}")
        print(f"  총 금액: ${184 * current_price:.2f}")
        print(f"{'='*80}")
    else:
        print(f"\n[ERROR] 주문 실패")
        print(f"  에러 코드: {result.get('msg_cd')}")
        print(f"  에러 메시지: {result.get('msg1')}")
else:
    print(f"\n[ERROR] HTTP 오류: {order_response.status_code}")
    print(f"응답: {order_response.text[:200]}")
