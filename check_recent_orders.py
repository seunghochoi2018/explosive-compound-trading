#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KIS 최근 주문 내역 및 SOXS 보유 수량 재확인"""
import sys
import yaml
import requests
import json
from datetime import datetime

# KIS API 설정
with open('kis_devlp.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

app_key = config['my_app']
app_secret = config['my_sec']
account_no = config['my_acct']
base_url = "https://openapi.koreainvestment.com:9443"

# 토큰 로드
with open('kis_token.json', 'r', encoding='utf-8') as f:
    token_data = json.load(f)
    access_token = token_data['access_token']

print("="*80)
print("KIS 최근 거래 내역 및 SOXS 보유 확인")
print("="*80)

# 1. 오늘 주문 내역 조회
print("\n[1] 오늘 주문 내역 조회 중...")
url_orders = f"{base_url}/uapi/overseas-stock/v1/trading/inquire-ccnl"

headers = {
    "authorization": f"Bearer {access_token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": "TTTS3035R"  # 해외주식 체결내역 조회
}

params = {
    "CANO": account_no.split('-')[0],
    "ACNT_PRDT_CD": account_no.split('-')[1],
    "PDNO": "",
    "ORD_STRT_DT": datetime.now().strftime("%Y%m%d"),
    "ORD_END_DT": datetime.now().strftime("%Y%m%d"),
    "SLL_BUY_DVSN": "02",  # 02: 매도
    "CCLD_NCCS_DVSN": "",
    "OVRS_EXCG_CD": "NASD",
    "SORT_SQN": "DS",
    "ORD_DT": "",
    "ORD_GNO_BRNO": "",
    "ODNO": "",
    "CTX_AREA_FK200": "",
    "CTX_AREA_NK200": ""
}

response = requests.get(url_orders, headers=headers, params=params, timeout=10)

if response.status_code == 200:
    data = response.json()
    if data.get('rt_cd') == '0':
        orders = data.get('output1', [])

        print(f"총 {len(orders)}건의 매도 주문 발견")

        soxs_orders = []
        for order in orders:
            if 'SOXS' in order.get('prdt_name', '').upper() or order.get('pdno') == 'SOXS':
                soxs_orders.append(order)
                print(f"\n[SOXS 주문 발견]")
                print(f"  주문번호: {order.get('odno', 'N/A')}")
                print(f"  종목명: {order.get('prdt_name', 'N/A')}")
                print(f"  주문수량: {order.get('ord_qty', 'N/A')}주")
                print(f"  체결수량: {order.get('ccld_qty', 'N/A')}주")
                print(f"  주문상태: {order.get('ord_stat_name', 'N/A')}")
                print(f"  주문시간: {order.get('ord_tmd', 'N/A')}")

        if len(soxs_orders) == 0:
            print("\n[경고] 오늘 SOXS 매도 주문 없음!")
    else:
        print(f"주문 내역 조회 실패: {data.get('msg1', 'Unknown')}")
else:
    print(f"HTTP 오류: {response.status_code}")

# 2. 현재 SOXS 보유 수량 재확인
print("\n" + "="*80)
print("[2] SOXS 현재 보유 수량 재확인")
print("="*80)

url_balance = f"{base_url}/uapi/overseas-stock/v1/trading/inquire-balance"

headers_balance = {
    "authorization": f"Bearer {access_token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": "TTTS3012R"
}

params_balance = {
    "CANO": account_no.split('-')[0],
    "ACNT_PRDT_CD": account_no.split('-')[1],
    "WCRC_FRCR_DVSN_CD": "02",
    "NATN_CD": "840",
    "TR_MKET_CD": "01",
    "OVRS_EXCG_CD": "NASD",
    "TR_CRCY_CD": "USD",
    "CTX_AREA_FK100": "",
    "CTX_AREA_NK100": "",
    "CTX_AREA_FK200": "",
    "CTX_AREA_NK200": ""
}

response_balance = requests.get(url_balance, headers=headers_balance, params=params_balance, timeout=10)

if response_balance.status_code == 200:
    data_balance = response_balance.json()
    if data_balance.get('rt_cd') == '0':
        holdings = data_balance.get('output1', [])

        print(f"\n총 {len(holdings)}개 종목 보유 중")

        soxs_found = False
        for holding in holdings:
            pdno = holding.get('ovrs_pdno', '')
            name = holding.get('ovrs_item_name', '')

            if 'SOXS' in name.upper() or pdno == 'A980680':
                qty = holding.get('ovrs_cblc_qty', '0')
                price = holding.get('now_pric2', '0')
                total_value = holding.get('ovrs_stck_evlu_amt', '0')

                print(f"\n[SOXS 보유 확인]")
                print(f"  종목코드: {pdno}")
                print(f"  종목명: {name}")
                print(f"  보유수량: {qty}주")
                print(f"  현재가: ${float(price):.2f}")
                print(f"  평가금액: ${float(total_value):.2f}")

                soxs_found = True

                if int(float(qty)) == 184:
                    print("\n[상태] 아직 청산 안됨 - 184주 그대로 보유 중!")
                    print("[조치 필요] 자동 청산 스크립트가 작동하지 않았습니다")
                elif int(float(qty)) == 0:
                    print("\n[상태] 청산 완료")
                else:
                    print(f"\n[상태] 부분 청산 - 현재 {int(float(qty))}주 보유")

        if not soxs_found:
            print("\n[상태] SOXS 보유 없음 (청산 완료 또는 미보유)")
    else:
        print(f"잔고 조회 실패: {data_balance.get('msg1', 'Unknown')}")
else:
    print(f"HTTP 오류: {response_balance.status_code}")

print("\n" + "="*80)
