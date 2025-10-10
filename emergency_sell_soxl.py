#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""긴급 SOXL 청산 스크립트"""
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import requests
import yaml
import json
from datetime import datetime, timedelta
import os

# KIS API 설정
with open('../코드/kis_devlp.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

app_key = config['my_app']
app_secret = config['my_sec']
account_no = config['my_acct']
base_url = "https://openapi.koreainvestment.com:9443"

# 토큰 로드
token_file = "kis_token.json"
with open(token_file, 'r', encoding='utf-8') as f:
    token_data = json.load(f)
access_token = token_data['access_token']

print("="*80)
print("긴급 SOXL 청산")
print("="*80)

# 1. 현재 보유 수량 확인
url = f"{base_url}/uapi/overseas-stock/v1/trading/inquire-balance"

headers = {
    "authorization": f"Bearer {access_token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": "TTTS3012R"
}

params = {
    "CANO": account_no.split('-')[0],
    "ACNT_PRDT_CD": account_no.split('-')[1],
    "OVRS_EXCG_CD": "NASD",
    "TR_CRCY_CD": "USD",
    "CTX_AREA_FK200": "",
    "CTX_AREA_NK200": ""
}

response = requests.get(url, headers=headers, params=params, timeout=10)

if response.status_code == 200:
    data = response.json()
    if data.get('rt_cd') == '0':
        output1 = data.get('output1', [])

        soxl_qty = 0
        soxl_avg_price = 0
        soxl_current_price = 0

        for stock in output1:
            if stock.get('ovrs_pdno') == 'SOXL':
                soxl_qty = int(stock.get('ovrs_cblc_qty', 0))
                soxl_avg_price = float(stock.get('pchs_avg_pric', 0))
                soxl_current_price = float(stock.get('now_pric2', 0))
                pnl_pct = float(stock.get('evlu_pfls_rt', 0))

                print(f"\n[보유 현황]")
                print(f"종목: SOXL")
                print(f"수량: {soxl_qty}주")
                print(f"평단가: ${soxl_avg_price:.2f}")
                print(f"현재가: ${soxl_current_price:.2f}")
                print(f"손익률: {pnl_pct}%")

                if soxl_qty > 0:
                    # 2. 매도 주문
                    print(f"\n[청산 시작] {soxl_qty}주 전량 매도...")

                    sell_url = f"{base_url}/uapi/overseas-stock/v1/trading/order"

                    sell_headers = {
                        "authorization": f"Bearer {access_token}",
                        "appkey": app_key,
                        "appsecret": app_secret,
                        "tr_id": "JTTT1006U"  # 매도
                    }

                    sell_data = {
                        "CANO": account_no.split('-')[0],
                        "ACNT_PRDT_CD": account_no.split('-')[1],
                        "OVRS_EXCG_CD": "NASD",
                        "PDNO": "SOXL",
                        "ORD_QTY": str(soxl_qty),
                        "OVRS_ORD_UNPR": "0",  # 시장가
                        "ORD_SVR_DVSN_CD": "0"
                    }

                    sell_response = requests.post(sell_url, headers=sell_headers, json=sell_data, timeout=10)

                    if sell_response.status_code == 200:
                        result = sell_response.json()
                        if result.get('rt_cd') == '0':
                            print(f"✅ 청산 성공!")
                            print(f"주문번호: {result.get('output', {}).get('ODNO', 'N/A')}")
                        else:
                            print(f"❌ 청산 실패: {result.get('msg1', '')}")
                    else:
                        print(f"❌ API 오류: {sell_response.status_code}")
                else:
                    print(f"\n[알림] SOXL 보유 없음")

                break
        else:
            print(f"\n[알림] SOXL 포지션 없음")
