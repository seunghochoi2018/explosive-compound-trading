#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SOXS 보유 수량 확인"""
import sys
import yaml
import requests

# KIS API 설정 로드
with open('kis_devlp.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

app_key = config['my_app']
app_secret = config['my_sec']
account_no = config['my_acct']
base_url = "https://openapi.koreainvestment.com:9443"

# 토큰 로드
try:
    import json
    with open('kis_token.json', 'r', encoding='utf-8') as f:
        token_data = json.load(f)
        access_token = token_data['access_token']
except:
    print("토큰 로드 실패")
    sys.exit(1)

# SOXS 보유 수량 조회
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

response = requests.get(url, headers=headers, params=params, timeout=10)

if response.status_code == 200:
    data = response.json()
    if data.get('rt_cd') == '0':
        holdings = data.get('output1', [])

        print("="*60)
        print("SOXS 보유 수량 확인")
        print("="*60)

        soxs_found = False
        for holding in holdings:
            pdno = holding.get('ovrs_pdno', '')
            if pdno == 'A980680':  # SOXS 종목코드
                qty = holding.get('ovrs_cblc_qty', '0')
                price = holding.get('now_pric2', '0')
                print(f"\n[SOXS 발견]")
                print(f"  종목코드: {pdno}")
                print(f"  보유 수량: {qty}주")
                print(f"  현재가: ${float(price):.2f}")
                soxs_found = True

                if int(float(qty)) == 184:
                    print("\n[상태] 아직 청산되지 않음 (184주 보유 중)")
                elif int(float(qty)) == 0:
                    print("\n[상태] 청산 완료! (보유 수량 0주)")
                else:
                    print(f"\n[상태] 부분 청산 (현재 {int(float(qty))}주 보유)")

        if not soxs_found:
            print("\n[상태] SOXS 보유 없음 (청산 완료 또는 미보유)")

        print("\n" + "="*60)
    else:
        print(f"API 오류: {data.get('msg1', 'Unknown')}")
else:
    print(f"HTTP 오류: {response.status_code}")
