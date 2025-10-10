#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
정확한 잔고 확인
"""

import yaml
import requests
import json
import os

yaml_path = os.path.join(os.path.dirname(__file__), 'kis_devlp.yaml')
with open(yaml_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

print("="*80)
print("정확한 잔고 확인")
print("="*80)

# 토큰 로드
try:
    with open('kis_token.json', 'r') as f:
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

# 해외주식 잔고 조회
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
        print(f"={'='*80}")
        print(f"보유 종목")
        print(f"={'='*80}\n")

        output1 = result.get('output1', [])

        total_value = 0
        for stock in output1:
            symbol = stock.get('ovrs_pdno', '')
            qty = float(stock.get('ovrs_cblc_qty', '0'))

            if qty > 0:
                item_name = stock.get('ovrs_item_name', '')
                avg_price = float(stock.get('pchs_avg_pric', '0'))
                current_price = float(stock.get('now_pric2', '0'))
                eval_amt = float(stock.get('ovrs_stck_evlu_amt', '0'))
                profit_loss = float(stock.get('frcr_evlu_pfls_amt', '0'))
                profit_rate = float(stock.get('evlu_pfls_rt', '0'))

                print(f"[{symbol}] {item_name}")
                print(f"  보유수량: {qty}주")
                print(f"  평균단가: ${avg_price:.2f}")
                print(f"  현재가: ${current_price:.2f}")
                print(f"  평가금액: ${eval_amt:.2f}")
                print(f"  평가손익: ${profit_loss:.2f} ({profit_rate:+.2f}%)")
                print()

                total_value += eval_amt

        print(f"{'='*80}")
        print(f"계좌 요약")
        print(f"{'='*80}\n")

        output2 = result.get('output2', {})

        # 모든 필드 출력
        print(f"[output2 전체 데이터]")
        for key, value in output2.items():
            print(f"  {key}: {value}")

        print(f"\n[주요 잔고 정보]")

        usd_cash = float(output2.get('frcr_buy_amt_smtl1', '0'))  # USD 현금
        total_eval = float(output2.get('tot_evlu_pfls_amt', '0'))  # 총 평가금액
        total_profit = float(output2.get('ovrs_tot_pfls', '0'))  # 총 손익
        frcr_pchs_amt1 = float(output2.get('frcr_pchs_amt1', '0'))  # 외화매입금액

        print(f"  USD 현금 잔액 (frcr_buy_amt_smtl1): ${usd_cash:.2f}")
        print(f"  보유 종목 평가액: ${total_value:.2f}")
        print(f"  총 평가금액 (tot_evlu_pfls_amt): ${total_eval:.2f}")
        print(f"  총 손익 (ovrs_tot_pfls): ${total_profit:.2f}")
        print(f"  외화매입금액 (frcr_pchs_amt1): ${frcr_pchs_amt1:.2f}")

        print(f"\n{'='*80}")
        print(f"총 자산")
        print(f"{'='*80}")
        print(f"  USD 현금: ${usd_cash:.2f}")
        print(f"  보유 주식: ${total_value:.2f}")
        print(f"  총 자산: ${usd_cash + total_value:.2f}")
        print(f"{'='*80}")

    else:
        print(f"조회 실패: {result.get('msg1')}")
        print(f"\n전체 응답:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
else:
    print(f"HTTP 오류: {response.status_code}")
    print(f"{response.text}")
