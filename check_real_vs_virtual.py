#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실전계좌 vs 모의계좌 비교
"""

import yaml
import requests
import json
import os

yaml_path = os.path.join(os.path.dirname(__file__), 'kis_devlp.yaml')
with open(yaml_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

print("="*80)
print("실전계좌 vs 모의계좌 잔고 조회 비교")
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

balance_params = {
    "CANO": cano,
    "ACNT_PRDT_CD": acnt_prdt_cd,
    "OVRS_EXCG_CD": "NASD",
    "TR_CRCY_CD": "USD",
    "CTX_AREA_FK200": "",
    "CTX_AREA_NK200": ""
}

# 테스트할 TR_ID 목록
tr_ids = [
    ("TTTS3012R", "모의투자", "P"),
    ("JTTT3012R", "실전투자", "P"),
    ("VTTC3012R", "모의투자(대체)", "P"),
]

for tr_id, account_type, custtype in tr_ids:
    print("="*80)
    print(f"테스트: {account_type} ({tr_id})")
    print("="*80)

    balance_headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {access_token}",
        "appkey": config['my_app'],
        "appsecret": config['my_sec'],
        "tr_id": tr_id,
        "custtype": custtype,
        "User-Agent": config['my_agent']
    }

    response = requests.get(balance_url, headers=balance_headers, params=balance_params, timeout=10)

    print(f"HTTP 상태: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"rt_cd: {result.get('rt_cd')}")
        print(f"msg1: {result.get('msg1')}")

        if result.get('rt_cd') == '0':
            output1 = result.get('output1', [])
            output2 = result.get('output2', {})

            # 보유 종목 확인
            holdings = []
            for item in output1:
                symbol = item.get('ovrs_pdno', '')
                qty = float(item.get('ovrs_cblc_qty', '0'))
                if qty > 0:
                    holdings.append(f"{symbol} {qty}주")

            print(f"\n[보유종목] {', '.join(holdings) if holdings else '없음'}")

            # output2에서 USD 현금 찾기
            print(f"\n[output2 주요 필드]")

            # 가능한 현금 관련 필드들
            cash_fields = [
                'frcr_dncl_amt_2',  # 외화예수금액2
                'frcr_buy_amt_smtl1',  # 외화매수금액합계1
                'frcr_evlu_amt2',  # 외화평가금액2
                'ord_psbl_frcr_amt',  # 주문가능외화금액
                'frcr_use_psbl_amt',  # 외화사용가능금액
                'ovrs_ord_psbl_amt',  # 해외주문가능금액
            ]

            found_cash = False
            for field in cash_fields:
                value = output2.get(field, None)
                if value is not None:
                    try:
                        float_val = float(value)
                        if float_val > 0:
                            print(f"  {field}: ${float_val:.2f} *** 발견!")
                            found_cash = True
                        else:
                            print(f"  {field}: ${float_val:.2f}")
                    except:
                        print(f"  {field}: {value}")

            if not found_cash:
                print(f"  => USD 현금 필드를 찾지 못했습니다.")

            # 투자금액
            invested = float(output2.get('frcr_pchs_amt1', '0'))
            if invested > 0:
                print(f"\n  투자금액: ${invested:.2f}")

        else:
            print(f"[실패] {result.get('msg1')}")

    else:
        print(f"[HTTP 오류] {response.status_code}")
        print(f"응답: {response.text[:200]}")

    print()

print("="*80)
print("테스트 완료")
print("="*80)
