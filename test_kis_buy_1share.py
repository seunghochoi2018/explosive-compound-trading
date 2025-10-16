#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KIS 1주 매수 테스트 - EGW00356 에러 해결 검증"""
import json
import yaml
import requests
import time

print("="*80)
print("KIS 1주 매수 테스트 (SOXL)")
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
    print("[ERROR] 가격 조회 실패")
    exit(1)

# 매수 주문 (1주)
print(f"\n[2] SOXL 1주 매수 주문 (${current_price:.2f})...")
order_url = f"{base_url}/uapi/overseas-stock/v1/trading/order"

headers = {
    "authorization": f"Bearer {access_token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": "JTTT1002U",  # 매수
    "custtype": "P",
    "content-type": "application/json; charset=utf-8",
    "tr_cont": "N",
    "tr_cont_key": ""
}

order_data = {
    "CANO": account_no.split('-')[0],
    "ACNT_PRDT_CD": account_no.split('-')[1],
    "OVRS_EXCG_CD": "NASD",
    "PDNO": "A980679",  # SOXL
    "ORD_QTY": "1",
    "OVRS_ORD_UNPR": str(current_price),
    "ORD_SVR_DVSN_CD": "0",
    "SLL_TYPE": "",  # 매수는 빈 문자열
    "ORD_DVSN": "00"  # 지정가
}

print("\n[3] 주문 데이터:")
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
            output = result.get('output', {})
            order_no = output.get('ODNO', 'N/A')

            print(f"\n{'='*80}")
            print(f"[SUCCESS] 매수 주문 성공!")
            print(f"{'='*80}")
            print(f"  주문번호: {order_no}")
            print(f"  종목: SOXL")
            print(f"  수량: 1주")
            print(f"  가격: ${current_price:.2f}")
            print(f"{'='*80}")

            # 주문번호 저장 (매도용)
            with open('kis_test_order.json', 'w', encoding='utf-8') as f:
                json.dump({
                    'order_no': order_no,
                    'symbol': 'SOXL',
                    'qty': 1,
                    'price': current_price
                }, f, ensure_ascii=False, indent=2)

            exit(0)  # 성공
        else:
            print(f"\n[ERROR] 주문 실패")
            print(f"  에러 코드: {result.get('msg_cd')}")
            print(f"  에러 메시지: {result.get('msg1')}")

            # 전체 응답 출력
            print(f"\n[FULL RESPONSE]")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            exit(1)  # 실패
    else:
        print(f"\n[ERROR] HTTP 오류")
        try:
            error_data = response.json()
            print(json.dumps(error_data, indent=2, ensure_ascii=False))
        except:
            print(f"  응답: {response.text}")
        exit(1)  # 실패

except Exception as e:
    print(f"\n[ERROR] 예외: {e}")
    import traceback
    traceback.print_exc()
    exit(1)  # 실패
