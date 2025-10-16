#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
# ⚠️ 중요: 기존 kis_token.json의 토큰 사용!
# 새로 발급하지 말 것!
"""
import json
import yaml
import requests

print("="*80)
print("미체결 주문 확인")
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

print(f"\n[1] 기존 토큰 사용: {access_token[:20]}...")

# 미체결 주문 조회
print(f"\n[2] 미체결 주문 조회...")
url = f"{base_url}/uapi/overseas-stock/v1/trading/inquire-nccs"

headers = {
    "authorization": f"Bearer {access_token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": "TTTS3018R",  # 미체결 조회
    "custtype": "P"
}

params = {
    "CANO": account_no.split('-')[0],
    "ACNT_PRDT_CD": account_no.split('-')[1],
    "OVRS_EXCG_CD": "NASD",
    "SORT_SQN": "DS",  # 정렬
    "CTX_AREA_FK200": "",
    "CTX_AREA_NK200": ""
}

response = requests.get(url, headers=headers, params=params, timeout=10)

print(f"\n[3] 응답:")
print(f"HTTP: {response.status_code}")

if response.status_code == 200:
    result = response.json()
    print(f"rt_cd: {result.get('rt_cd')}")
    print(f"msg1: {result.get('msg1')}")

    if result.get('rt_cd') == '0':
        orders = result.get('output', [])
        print(f"\n미체결 주문 수: {len(orders)}개")

        if len(orders) > 0:
            print(f"\n{'='*80}")
            print(f"[미체결 주문 목록]")
            print(f"{'='*80}")
            for order in orders:
                pdno = order.get('pdno', 'N/A')
                ord_qty = order.get('ord_qty', '0')
                ord_unpr = order.get('ft_ord_unpr3', '0')
                sll_buy_dvsn = order.get('sll_buy_dvsn_cd', '0')
                sll_buy_text = "매도" if sll_buy_dvsn == '01' else "매수"

                print(f"\n종목코드: {pdno}")
                print(f"주문구분: {sll_buy_text}")
                print(f"주문수량: {ord_qty}주")
                print(f"주문가격: ${ord_unpr}")
                print("-"*80)
        else:
            print(f"\n미체결 주문 없음 ✓")
    else:
        print(f"조회 실패: {result}")
else:
    print(f"HTTP 오류: {response.text[:200]}")

print(f"\n{'='*80}")
