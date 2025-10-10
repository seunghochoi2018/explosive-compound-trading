#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
해외주식 계좌 가용 현금 조회
"""

import yaml
import requests
import json
import os

yaml_path = os.path.join(os.path.dirname(__file__), 'kis_devlp.yaml')
with open(yaml_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

print("="*80)
print("해외주식 계좌 가용 현금 조회")
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

# 1. 해외주식 잔고 조회 (output2에 계좌 정보 포함)
print("="*80)
print("1. 해외주식 잔고 조회 (output2)")
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

if response.status_code == 200:
    result = response.json()

    if result.get('rt_cd') == '0':
        output1 = result.get('output1', [])
        output2 = result.get('output2', {})

        print("\n[output2 전체 필드]")
        print("-"*80)
        for key, value in output2.items():
            print(f"{key}: {value}")
        print()

        # 주요 금액 필드 분석
        print("\n[중요 금액 필드]")
        print("-"*80)

        # 가용 현금
        frcr_dncl_amt_2 = float(output2.get('frcr_dncl_amt_2', '0'))
        ovrs_ord_psbl_amt = float(output2.get('ovrs_ord_psbl_amt', '0'))

        # 투자 금액
        frcr_pchs_amt1 = float(output2.get('frcr_pchs_amt1', '0'))

        # 손익
        ovrs_tot_pfls = float(output2.get('ovrs_tot_pfls', '0'))
        tot_evlu_pfls_amt = float(output2.get('tot_evlu_pfls_amt', '0'))
        tot_pftrt = float(output2.get('tot_pftrt', '0'))

        print(f"[가용 현금]")
        print(f"  frcr_dncl_amt_2 (USD 현금 잔고): ${frcr_dncl_amt_2:.2f}")
        print(f"  ovrs_ord_psbl_amt (주문 가능 금액): ${ovrs_ord_psbl_amt:.2f}")
        print(f"\n[투자 현황]")
        print(f"  frcr_pchs_amt1 (주식 매입금액): ${frcr_pchs_amt1:.2f}")
        print(f"  ovrs_tot_pfls (총 손익): ${ovrs_tot_pfls:.2f} ({tot_pftrt:.2f}%)")

        # 보유 종목 평가금액 계산
        print("\n[보유 종목]")
        print("-"*80)
        total_stock_value = 0

        for stock in output1:
            symbol = stock.get('ovrs_pdno', '')
            qty = float(stock.get('ovrs_cblc_qty', '0'))

            if qty > 0:
                eval_amt = float(stock.get('ovrs_stck_evlu_amt', '0'))
                avg_price = float(stock.get('pchs_avg_pric', '0'))
                total_stock_value += eval_amt

                print(f"{symbol}: {qty}주 x ${avg_price:.2f} = ${eval_amt:.2f}")

        print(f"\n총 주식 평가금액: ${total_stock_value:.2f}")

        # 최종 요약
        print("\n" + "="*80)
        print(">> 자동매매를 위한 계좌 요약")
        print("="*80)
        print(f"[가용 현금]")
        print(f"  USD 현금 잔고: ${frcr_dncl_amt_2:.2f}")
        print(f"  주문 가능 금액: ${ovrs_ord_psbl_amt:.2f}")
        print()
        print(f"[보유 주식]")
        print(f"  주식 평가금액: ${total_stock_value:.2f}")
        print(f"  총 손익: ${ovrs_tot_pfls:.2f} ({tot_pftrt:+.2f}%)")
        print()
        print(f"[총 자산]")
        total_assets = frcr_dncl_amt_2 + total_stock_value
        print(f"  현금 + 주식: ${total_assets:.2f}")
        print("="*80)

    else:
        print(f"[ERROR] 조회 실패: {result.get('msg1')}")
else:
    print(f"[ERROR] HTTP 오류: {response.status_code}")

print()
