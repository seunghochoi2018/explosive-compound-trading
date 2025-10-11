#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KIS 계좌 실제 포지션 확인"""
import requests
import json
import os

# KIS 설정 로드
config_file = r'C:\Users\user\Documents\코드4\config.json'
token_file = r'C:\Users\user\Documents\코드4\kis_token.json'

if os.path.exists(config_file):
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
else:
    # config.json이 없으면 환경변수나 다른 파일에서 로드
    config = {}

if os.path.exists(token_file):
    with open(token_file, 'r', encoding='utf-8') as f:
        token_data = json.load(f)
        access_token = token_data.get('access_token', '')
else:
    access_token = ''

# 계좌번호 찾기
account_no = config.get('account_no', '')
app_key = config.get('app_key', '')
app_secret = config.get('app_secret', '')

if not account_no or not app_key or not app_secret:
    print("설정 파일 확인 필요")
    print(f"config.json 존재: {os.path.exists(config_file)}")
    print(f"Keys in config: {list(config.keys())}")
    exit(1)

# 해외주식 잔고 조회
url = "https://openapi.koreainvestment.com:9443/uapi/overseas-stock/v1/trading/inquire-balance"
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

try:
    response = requests.get(url, headers=headers, params=params, timeout=10)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        if data.get('rt_cd') == '0':
            print("\n=== 현재 보유 포지션 ===")
            holdings = data.get('output1', [])

            has_position = False
            for holding in holdings:
                symbol = holding.get('ovrs_pdno', '')
                qty = int(holding.get('ovrs_cblc_qty', 0))
                if qty > 0 and (symbol == 'SOXL' or symbol == 'SOXS'):
                    has_position = True
                    avg_price = float(holding.get('pchs_avg_pric', 0))
                    current_price = float(holding.get('now_pric2', 0))
                    pnl_pct = ((current_price - avg_price) / avg_price) * 100 if avg_price > 0 else 0

                    print(f"\n종목: {symbol}")
                    print(f"수량: {qty}주")
                    print(f"평단가: ${avg_price:.2f}")
                    print(f"현재가: ${current_price:.2f}")
                    print(f"손익: {pnl_pct:+.2f}%")

            if not has_position:
                print("현재 SOXL/SOXS 포지션 없음")
                print("\n=== USD 잔고 ===")
                output2 = data.get('output2', [])
                if output2:
                    for item in output2:
                        if item.get('crcy_cd') == 'USD':
                            balance = float(item.get('frcr_dncl_amt_2', 0))
                            print(f"사용 가능: ${balance:.2f}")
        else:
            print(f"API Error: {data.get('msg1', 'Unknown error')}")
    else:
        print(f"HTTP Error: {response.text}")

except Exception as e:
    print(f"Exception: {e}")
    import traceback
    traceback.print_exc()
