#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SOXL 포지션 확인
"""

import yaml
import requests
import json
import os

yaml_path = os.path.join(os.path.dirname(__file__), 'kis_devlp.yaml')
with open(yaml_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

print("="*80)
print("SOXL 포지션 확인")
print("="*80)

# 토큰 발급
token_url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
headers = {
    "Content-Type": "application/json",
    "User-Agent": config['my_agent']
}
data = {
    "grant_type": "client_credentials",
    "appkey": config['my_app'],
    "appsecret": config['my_sec']
}

response = requests.post(token_url, headers=headers, json=data, timeout=30)

if response.status_code != 200:
    print(f"토큰 발급 실패: {response.text}")
    exit(1)

access_token = response.json().get("access_token")
print(f"토큰 발급 성공!\n")

# 계좌번호 파싱
acct_parts = config['my_acct'].split('-')
cano = acct_parts[0]
acnt_prdt_cd = acct_parts[1] if len(acct_parts) > 1 else "01"

# 해외주식 잔고 조회
print(f"{'='*80}")
print(f"해외주식 잔고 조회 (계좌: {cano}-{acnt_prdt_cd})")
print(f"{'='*80}")

balance_url = "https://openapi.koreainvestment.com:9443/uapi/overseas-stock/v1/trading/inquire-balance"

balance_headers = {
    "Content-Type": "application/json; charset=utf-8",
    "authorization": f"Bearer {access_token}",
    "appkey": config['my_app'],
    "appsecret": config['my_sec'],
    "tr_id": "TTTS3012R",
    "custtype": "P"
}

balance_params = {
    "CANO": cano,
    "ACNT_PRDT_CD": acnt_prdt_cd,
    "OVRS_EXCG_CD": "NASD",
    "TR_CRCY_CD": "USD",
    "CTX_AREA_FK200": "",
    "CTX_AREA_NK200": ""
}

balance_response = requests.get(balance_url, headers=balance_headers, params=balance_params, timeout=10)

print(f"HTTP: {balance_response.status_code}")

if balance_response.status_code == 200:
    balance_result = balance_response.json()
    print(f"rt_cd: {balance_result.get('rt_cd')}")
    print(f"msg1: {balance_result.get('msg1')}")

    if balance_result.get('rt_cd') == '0':
        print(f"\n[조회 성공!]\n")

        # output1: 보유종목
        output1 = balance_result.get('output1', [])

        soxl_found = False

        if output1:
            print(f"=== 보유종목 ===")
            for stock in output1:
                qty = float(stock.get('ovrs_cblc_qty', '0'))
                if qty > 0:
                    symbol = stock.get('ovrs_pdno', '')
                    item_name = stock.get('ovrs_item_name', '')
                    avg_price = float(stock.get('pchs_avg_pric', '0'))
                    current_price = float(stock.get('now_pric2', '0'))
                    eval_amt = float(stock.get('ovrs_stck_evlu_amt', '0'))
                    profit_loss = float(stock.get('frcr_evlu_pfls_amt', '0'))
                    profit_rate = float(stock.get('evlu_pfls_rt', '0'))

                    print(f"\n[{symbol}] {item_name}")
                    print(f"  보유수량: {qty}주")
                    print(f"  평균단가: ${avg_price:.2f}")
                    print(f"  현재가: ${current_price:.2f}")
                    print(f"  평가금액: ${eval_amt:.2f}")
                    print(f"  평가손익: ${profit_loss:.2f} ({profit_rate:+.2f}%)")

                    if symbol == "SOXL":
                        soxl_found = True
                        print(f"\n  >>> SOXL 포지션 확인!")
        else:
            print(f"보유종목 없음")

        # output2: 계좌요약
        output2 = balance_result.get('output2', {})
        if output2:
            print(f"\n{'='*80}")
            print(f"=== 계좌요약 ===")

            usd_balance = float(output2.get('frcr_buy_amt_smtl1', '0'))
            total_eval = float(output2.get('tot_evlu_pfls_amt', '0'))
            total_profit = float(output2.get('ovrs_tot_pfls', '0'))
            frcr_pchs_amt1 = float(output2.get('frcr_pchs_amt1', '0'))

            print(f"  USD 매수가능금액: ${usd_balance:.2f}")
            print(f"  총평가금액: ${total_eval:.2f}")
            print(f"  해외총손익: ${total_profit:.2f}")
            print(f"  외화매입금액: ${frcr_pchs_amt1:.2f}")

        if not soxl_found:
            print(f"\n[경고] SOXL 포지션이 아직 확인되지 않습니다")
            print(f"매수 체결이 완료되지 않았거나, 조회에 시간이 걸릴 수 있습니다")

    else:
        print(f"조회 실패: {balance_result.get('msg1')}")
        print(f"\n전체 응답:")
        print(json.dumps(balance_result, indent=2, ensure_ascii=False))
else:
    print(f"HTTP 오류: {balance_response.status_code}")
    print(f"{balance_response.text}")

print(f"\n{'='*80}")
