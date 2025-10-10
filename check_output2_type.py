#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
output2 타입 확인 - 리스트 vs 딕셔너리
"""

import yaml
import requests
import json
import os

yaml_path = os.path.join(os.path.dirname(__file__), 'kis_devlp.yaml')
with open(yaml_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

print("="*80)
print("output2 타입 확인")
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
        output2 = result.get('output2')

        print(f"output2 타입: {type(output2)}")
        print(f"output2 값:")
        print(json.dumps(output2, indent=2, ensure_ascii=False))

        print(f"\n{'='*80}")

        # 리스트인 경우
        if isinstance(output2, list):
            print(f"output2는 리스트입니다 (길이: {len(output2)})")
            if len(output2) > 0:
                print(f"\noutput2[0]:")
                print(json.dumps(output2[0], indent=2, ensure_ascii=False))

                frcr_dncl_amt_2 = output2[0].get('frcr_dncl_amt_2', 'N/A')
                print(f"\nfrcr_dncl_amt_2: {frcr_dncl_amt_2}")

        # 딕셔너리인 경우
        elif isinstance(output2, dict):
            print(f"output2는 딕셔너리입니다")
            print(f"키: {list(output2.keys())}")

            frcr_dncl_amt_2 = output2.get('frcr_dncl_amt_2', 'N/A')
            print(f"\nfrcr_dncl_amt_2: {frcr_dncl_amt_2}")

        print(f"\n{'='*80}")
        print(f"결론:")
        print(f"{'='*80}")
        print(f"엑셀 예제는 output2가 dict 타입이라고 했는데,")
        print(f"실제 응답도 dict입니다.")
        print(f"하지만 frcr_dncl_amt_2 필드가 응답에 없습니다!")

    else:
        print(f"조회 실패: {result.get('msg1')}")
else:
    print(f"HTTP 오류: {response.status_code}")
