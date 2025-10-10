#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
모든 해외주식 보유 종목 확인
"""

import yaml
import requests
import json
import os

yaml_path = os.path.join(os.path.dirname(__file__), 'kis_devlp.yaml')
with open(yaml_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

print("="*80)
print("모든 해외주식 보유 종목 확인")
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

        print(f"output1 전체 항목 수: {len(output1)}\n")
        print(f"{'='*80}")
        print(f"모든 항목 (수량 0 포함)")
        print(f"{'='*80}\n")

        total_cost = 0
        total_value = 0

        for idx, item in enumerate(output1):
            symbol = item.get('ovrs_pdno', '')
            qty = float(item.get('ovrs_cblc_qty', '0'))
            avg_price = float(item.get('pchs_avg_pric', '0'))
            current_price = float(item.get('now_pric2', '0'))
            eval_amt = float(item.get('ovrs_stck_evlu_amt', '0'))

            # 수량이 0보다 큰 항목만 출력
            if qty > 0 or symbol:
                print(f"[{idx+1}] {symbol if symbol else '(빈칸)'}")
                print(f"  수량: {qty}주")
                if avg_price > 0:
                    print(f"  평균단가: ${avg_price:.2f}")
                    print(f"  현재가: ${current_price:.2f}")
                    print(f"  평가금액: ${eval_amt:.2f}")

                    cost = qty * avg_price
                    total_cost += cost
                    total_value += eval_amt
                print()

        print(f"{'='*80}")
        print(f"합계")
        print(f"{'='*80}")
        print(f"총 매입금액: ${total_cost:.2f}")
        print(f"총 평가금액: ${total_value:.2f}")
        print(f"총 손익: ${total_value - total_cost:.2f}")

        # 계산
        print(f"\n{'='*80}")
        print(f"USD 잔고 계산")
        print(f"{'='*80}")
        print(f"환전금액: $104.93")
        print(f"사용금액: ${total_cost:.2f}")
        print(f"남아야 할 금액: ${104.93 - total_cost:.2f}")

        output2 = result.get('output2', {})
        actual_balance = float(output2.get('frcr_buy_amt_smtl1', '0'))
        print(f"실제 잔고: ${actual_balance:.2f}")

        if actual_balance == 0 and (104.93 - total_cost) > 1:
            print(f"\n[문제] ${104.93 - total_cost:.2f}가 사라졌습니다!")

    else:
        print(f"조회 실패: {result.get('msg1')}")
else:
    print(f"HTTP 오류: {response.status_code}")
