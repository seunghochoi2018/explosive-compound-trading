#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
봇이 SOXL 포지션을 제대로 인식하는지 테스트
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# 봇의 잔고 조회 로직 테스트
import yaml
import requests

yaml_path = os.path.join(os.path.dirname(__file__), 'kis_devlp.yaml')
with open(yaml_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

print("="*80)
print("봇 포지션 인식 테스트")
print("="*80)

# 토큰 로드
try:
    with open('kis_token.json', 'r') as f:
        import json
        token_data = json.load(f)
        access_token = token_data['access_token']
        print(f"토큰 로드 성공\n")
except:
    print("토큰 파일 없음")
    exit(1)

# 계좌번호
acct_parts = config['my_acct'].split('-')
cano = acct_parts[0]
acnt_prdt_cd = acct_parts[1] if len(acct_parts) > 1 else "01"

# 잔고 조회
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

if response.status_code == 200:
    result = response.json()

    if result.get('rt_cd') == '0':
        output1 = result.get('output1', [])
        output2 = result.get('output2', {})

        # 봇이 인식할 USD 잔액
        usd_balance = float(output2.get('frcr_buy_amt_smtl1', '0'))

        print(f"[봇 로직 시뮬레이션]")
        print(f"USD 잔액: ${usd_balance:.2f}")

        # 포지션 확인
        soxl_qty = 0
        soxs_qty = 0

        for stock in output1:
            symbol = stock.get('ovrs_pdno', '')
            qty = float(stock.get('ovrs_cblc_qty', '0'))

            if symbol == 'SOXL' and qty > 0:
                soxl_qty = qty
                avg_price = float(stock.get('pchs_avg_pric', '0'))
                current_price = float(stock.get('now_pric2', '0'))
                print(f"\n[SOXL 포지션 인식]")
                print(f"  수량: {soxl_qty}주")
                print(f"  평균단가: ${avg_price:.2f}")
                print(f"  현재가: ${current_price:.2f}")

            elif symbol == 'SOXS' and qty > 0:
                soxs_qty = qty
                avg_price = float(stock.get('pchs_avg_pric', '0'))
                current_price = float(stock.get('now_pric2', '0'))
                print(f"\n[SOXS 포지션 인식]")
                print(f"  수량: {soxs_qty}주")
                print(f"  평균단가: ${avg_price:.2f}")
                print(f"  현재가: ${current_price:.2f}")

        # 봇 상태 판단
        print(f"\n{'='*80}")
        print(f"[봇 상태 판단]")

        if usd_balance == 0 and soxl_qty == 0 and soxs_qty == 0:
            print(f"  상태: 시뮬레이션 모드 (잔고 $0, 포지션 없음)")
        elif usd_balance == 0 and (soxl_qty > 0 or soxs_qty > 0):
            print(f"  상태: 포지션 보유 중 (USD 잔액 소진)")
            if soxl_qty > 0:
                print(f"  포지션: SOXL {soxl_qty}주 롱")
            if soxs_qty > 0:
                print(f"  포지션: SOXS {soxs_qty}주 쇼트")
            print(f"\n  >>> 봇이 이 포지션을 관리할 수 있습니다!")
            print(f"  >>> LLM이 시장을 분석하고 매도/포지션 전환 신호를 생성할 것입니다")
        elif usd_balance > 0:
            print(f"  상태: 거래 가능 (USD ${usd_balance:.2f})")
            if soxl_qty > 0:
                print(f"  추가 포지션: SOXL {soxl_qty}주")
            if soxs_qty > 0:
                print(f"  추가 포지션: SOXS {soxs_qty}주")

        print(f"{'='*80}")

else:
    print(f"HTTP 오류: {response.status_code}")
