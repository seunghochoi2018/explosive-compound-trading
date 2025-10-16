#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SOXS 매도 - tr_cont, tr_cont_key 헤더 + 타임 필드 추가"""
import json
import yaml
import requests
from datetime import datetime

print("="*80)
print("SOXS 매도 주문 (전체 헤더 + 타임 필드)")
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

# SOXS 현재가
print("\n[1] SOXS 현재가 조회...")
fmp_url = "https://financialmodelingprep.com/api/v3/quote/SOXS"
fmp_response = requests.get(fmp_url, params={'apikey': '5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI'}, timeout=10)
current_price = 0
if fmp_response.status_code == 200:
    fmp_data = fmp_response.json()
    if fmp_data:
        current_price = fmp_data[0].get('price', 0)
        print(f"SOXS 현재가: ${current_price:.2f}")

if current_price <= 0:
    print("[ERROR] 가격 조회 실패")
    exit(1)

# 주문 요청
print(f"\n[2] SOXS 184주 매도 주문 (${current_price:.2f})...")
order_url = f"{base_url}/uapi/overseas-stock/v1/trading/order"

# 헤더 (tr_cont, tr_cont_key 추가)
headers = {
    "authorization": f"Bearer {access_token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": "JTTT1006U",
    "custtype": "P",
    "content-type": "application/json; charset=utf-8",
    "tr_cont": "N",        # 첫 거래 = N (New)
    "tr_cont_key": ""      # 초기값 = 빈 문자열
}

# Body (기존 필드)
order_data = {
    "CANO": account_no.split('-')[0],
    "ACNT_PRDT_CD": account_no.split('-')[1],
    "OVRS_EXCG_CD": "NASD",
    "PDNO": "A980680",
    "ORD_QTY": "184",
    "OVRS_ORD_UNPR": str(current_price),
    "ORD_SVR_DVSN_CD": "0"
}

print("\n[3] 요청 구성:")
print("  헤더 추가:")
print("    - tr_cont: N (첫 거래)")
print("    - tr_cont_key: '' (빈 문자열)")
print("\n  Body:")
print(json.dumps(order_data, indent=4, ensure_ascii=False))

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
            output = result.get('output', {})
            order_no = output.get('ODNO', 'N/A')

            print(f"\n{'='*80}")
            print(f"[SUCCESS] 매도 주문 성공!")
            print(f"{'='*80}")
            print(f"  주문번호: {order_no}")
            print(f"  종목: SOXS")
            print(f"  수량: 184주")
            print(f"  가격: ${current_price:.2f}")
            print(f"{'='*80}")
        else:
            print(f"\n[ERROR] 주문 실패")
            print(f"  에러 코드: {result.get('msg_cd')}")
            print(f"  에러 메시지: {result.get('msg1')}")

            # 추가 대응: body에 타임 필드 필요 여부 확인
            if result.get('msg_cd') == 'EGW00356':
                print(f"\n[분석] EGW00356 에러 지속")
                print(f"  가능한 원인:")
                print(f"    1. Body에 타임 필드 필요 (tr_time, ord_dt, inqr_time 등)")
                print(f"    2. KIS 문서에 명시되지 않은 추가 필드 필요")
                print(f"    3. 실전투자 환경 특정 제약사항")
    else:
        print(f"\n[ERROR] HTTP 오류")
        try:
            error_data = response.json()
            print(json.dumps(error_data, indent=2, ensure_ascii=False))
        except:
            print(f"  응답: {response.text}")

except Exception as e:
    print(f"\n[ERROR] 예외: {e}")

print("\n" + "="*80)
