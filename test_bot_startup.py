#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
봇 시작 부분만 테스트
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import yaml
import requests
import json

yaml_path = os.path.join(os.path.dirname(__file__), 'kis_devlp.yaml')
with open(yaml_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

print("="*80)
print("=== 봇 시작 테스트 ===")
print("="*80)

# 토큰 로드
try:
    with open('kis_token.json', 'r') as f:
        token_data = json.load(f)
        access_token = token_data['access_token']
        print(f"[OK] 토큰 로드 성공\n")
except:
    print("[ERROR] 토큰 파일 없음")
    exit(1)

# 계좌번호
acct_parts = config['my_acct'].split('-')
cano = acct_parts[0]
acnt_prdt_cd = acct_parts[1] if len(acct_parts) > 1 else "01"

# [FIX] 기존 포지션 로드
print("="*80)
print("[STEP 1] 기존 포지션 로드")
print("="*80)

balance_url = "https://openapi.koreainvestment.com:9443/uapi/overseas-stock/v1/trading/inquire-balance"

balance_headers = {
    "Content-Type": "application/json; charset=utf-8",
    "authorization": f"Bearer {access_token}",
    "appkey": config['my_app'],
    "appsecret": config['my_sec'],
    "tr_id": "TTTS3012R",
    "custtype": "P",
    "User-Agent": config['my_agent']
}

balance_params = {
    "CANO": cano,
    "ACNT_PRDT_CD": acnt_prdt_cd,
    "OVRS_EXCG_CD": "NASD",
    "TR_CRCY_CD": "USD",
    "CTX_AREA_FK200": "",
    "CTX_AREA_NK200": ""
}

response = requests.get(balance_url, headers=balance_headers, params=balance_params, timeout=10)

existing_symbol = None
existing_qty = 0
existing_avg_price = 0

if response.status_code == 200:
    result = response.json()
    if result.get('rt_cd') == '0':
        output1 = result.get('output1', [])

        SYMBOLS = ["SOXL", "SOXS"]

        for item in output1:
            symbol = item.get('ovrs_pdno', '')
            qty = float(item.get('ovrs_cblc_qty', '0'))
            avg_price = float(item.get('pchs_avg_pric', '0'))

            if symbol in SYMBOLS and qty > 0:
                existing_symbol = symbol
                existing_qty = qty
                existing_avg_price = avg_price
                print(f"\n[POSITION] 기존 포지션 발견: {existing_symbol} {existing_qty}주 @ ${existing_avg_price:.2f}")
                break

        if not existing_symbol:
            print(f"\n[INFO] 기존 포지션 없음")
    else:
        print(f"[ERROR] 잔고 조회 실패: {result.get('msg1')}")
else:
    print(f"[ERROR] HTTP {response.status_code}")

# 현재가 조회 테스트
print(f"\n{'='*80}")
print("[STEP 2] 현재가 조회 (SOXL, SOXS)")
print("="*80)

def get_current_price(symbol):
    url = "https://openapi.koreainvestment.com:9443/uapi/overseas-price/v1/quotations/price"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {access_token}",
        "appkey": config['my_app'],
        "appsecret": config['my_sec'],
        "tr_id": "HHDFS00000300",
        "custtype": "P",
        "User-Agent": config['my_agent']
    }
    params = {
        "AUTH": "",
        "EXCD": "NAS",
        "SYMB": symbol
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('rt_cd') == '0':
                price = float(result.get('output', {}).get('last', 0))
                return price
    except:
        pass
    return 0

soxl_price = get_current_price("SOXL")
soxs_price = get_current_price("SOXS")

print(f"SOXL: ${soxl_price:.2f}")
print(f"SOXS: ${soxs_price:.2f}")

# 포지션 손익 계산
if existing_symbol and existing_avg_price > 0:
    current_price = soxl_price if existing_symbol == "SOXL" else soxs_price
    if current_price > 0:
        pnl = ((current_price - existing_avg_price) / existing_avg_price) * 100
        pnl_usd = (current_price - existing_avg_price) * existing_qty

        print(f"\n{'='*80}")
        print(f"[포지션 손익]")
        print(f"{'='*80}")
        print(f"  진입가: ${existing_avg_price:.2f}")
        print(f"  현재가: ${current_price:.2f}")
        print(f"  손익률: {pnl:+.2f}%")
        print(f"  손익금: ${pnl_usd:+.2f}")

print(f"\n{'='*80}")
print(f"[OK] 봇 시작 준비 완료!")
print(f"{'='*80}\n")
