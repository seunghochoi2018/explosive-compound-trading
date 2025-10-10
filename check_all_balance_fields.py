#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
모든 잔고 필드 확인
"""

import yaml
import requests
import json
import os

yaml_path = os.path.join(os.path.dirname(__file__), 'kis_devlp.yaml')
with open(yaml_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

print("="*80)
print("모든 잔고 필드 확인")
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

print(f"계좌: {cano}-{acnt_prdt_cd}\n")

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
        output2 = result.get('output2', {})

        print(f"{'='*80}")
        print(f"output2 모든 필드 (값이 0이 아닌 것만)")
        print(f"{'='*80}\n")

        for key, value in output2.items():
            try:
                float_val = float(value)
                if float_val != 0:
                    print(f"{key}: {value}")
            except:
                if value and str(value).strip() != '':
                    print(f"{key}: {value}")

        print(f"\n{'='*80}")
        print(f"주요 USD 잔고 관련 필드")
        print(f"{'='*80}\n")

        # 엑셀 문서에서 확인한 필드들
        important_fields = {
            'frcr_buy_amt_smtl1': '외화매수금액합계1 (매수가능금액)',
            'frcr_buy_amt_smtl2': '외화매수금액합계2',
            'frcr_dncl_amt_2': '외화예수금액2',
            'frcr_evlu_amt2': '외화평가금액2',
            'tot_evlu_pfls_amt': '총평가손익금액',
            'frcr_pchs_amt1': '외화매입금액1',
            'ovrs_tot_pfls': '해외총손익',
            'ord_psbl_frcr_amt': '주문가능외화금액',
            'frcr_use_psbl_amt': '외화사용가능금액',
        }

        for key, desc in important_fields.items():
            value = output2.get(key, 'N/A')
            print(f"{key} ({desc}): {value}")

        print(f"\n{'='*80}")
        print(f"계산")
        print(f"{'='*80}\n")

        # 10만원 환전 금액 추정
        krw = 100000
        usd_rate = 1300  # 대략적인 환율
        expected_usd = krw / usd_rate

        print(f"10만원 환전 예상: ${expected_usd:.2f} (환율 1,300원 가정)")

        soxl_2_cost = 39.00 * 2
        print(f"SOXL 2주 매수 비용: ${soxl_2_cost:.2f}")

        expected_remaining = expected_usd - soxl_2_cost
        print(f"예상 남은 금액: ${expected_remaining:.2f}")

        print(f"\n실제 frcr_buy_amt_smtl1: {output2.get('frcr_buy_amt_smtl1', '0')}")

        if float(output2.get('frcr_buy_amt_smtl1', '0')) == 0:
            print(f"\n[문제] USD 잔고가 0으로 나옵니다!")
            print(f"다른 필드를 확인해야 합니다.")

    else:
        print(f"조회 실패: {result.get('msg1')}")
        print(json.dumps(result, indent=2, ensure_ascii=False))
else:
    print(f"HTTP 오류: {response.status_code}")
    print(response.text)
