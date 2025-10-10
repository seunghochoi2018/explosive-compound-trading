#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USD 현금 찾기 - 다양한 거래소/통화 조합 테스트
"""

import yaml
import requests
import json
import os

yaml_path = os.path.join(os.path.dirname(__file__), 'kis_devlp.yaml')
with open(yaml_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

print("="*80)
print("USD 현금 찾기 - 다양한 조합 테스트")
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

# 다양한 거래소/통화 조합
test_configs = [
    {"OVRS_EXCG_CD": "NASD", "TR_CRCY_CD": "USD", "desc": "나스닥-USD"},
    {"OVRS_EXCG_CD": "NYSE", "TR_CRCY_CD": "USD", "desc": "뉴욕-USD"},
    {"OVRS_EXCG_CD": "AMEX", "TR_CRCY_CD": "USD", "desc": "아멕스-USD"},
    {"OVRS_EXCG_CD": "NAS", "TR_CRCY_CD": "USD", "desc": "나스닥(NAS)-USD"},
    {"OVRS_EXCG_CD": "NYS", "TR_CRCY_CD": "USD", "desc": "뉴욕(NYS)-USD"},
    {"OVRS_EXCG_CD": "", "TR_CRCY_CD": "USD", "desc": "거래소없음-USD"},
    {"OVRS_EXCG_CD": "NASD", "TR_CRCY_CD": "", "desc": "나스닥-통화없음"},
]

for test_config in test_configs:
    print("="*80)
    print(f"테스트: {test_config['desc']}")
    print("="*80)

    balance_headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {access_token}",
        "appkey": config['my_app'],
        "appsecret": config['my_sec'],
        "tr_id": "JTTT3012R",  # 실전투자
        "custtype": "P",
        "User-Agent": config['my_agent']
    }

    balance_params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "OVRS_EXCG_CD": test_config["OVRS_EXCG_CD"],
        "TR_CRCY_CD": test_config["TR_CRCY_CD"],
        "CTX_AREA_FK200": "",
        "CTX_AREA_NK200": ""
    }

    response = requests.get(balance_url, headers=balance_headers, params=balance_params, timeout=10)

    if response.status_code == 200:
        result = response.json()

        if result.get('rt_cd') == '0':
            output2 = result.get('output2', {})

            print(f"[성공] output2 전체 필드:")

            # 값이 있는 필드만 출력
            has_value = False
            for key, value in output2.items():
                try:
                    float_val = float(value)
                    if float_val != 0:
                        print(f"  {key}: {value}")
                        has_value = True
                except:
                    if value and str(value).strip():
                        print(f"  {key}: {value}")
                        has_value = True

            if not has_value:
                print(f"  (모든 필드가 0 또는 빈값)")

            # 특별히 현금 관련 필드 확인
            cash_candidates = {
                'frcr_dncl_amt_2': output2.get('frcr_dncl_amt_2'),
                'frcr_buy_amt_smtl1': output2.get('frcr_buy_amt_smtl1'),
                'frcr_buy_amt_smtl2': output2.get('frcr_buy_amt_smtl2'),
                'ovrs_ord_psbl_amt': output2.get('ovrs_ord_psbl_amt'),
            }

            print(f"\n  [현금 후보 필드]")
            for field, value in cash_candidates.items():
                if value is not None:
                    print(f"    {field}: {value}")
                else:
                    print(f"    {field}: (없음)")

        else:
            print(f"[실패] {result.get('msg1')}")
    else:
        print(f"[HTTP 오류] {response.status_code}")

    print()

print("="*80)
print("결론: output2에서 USD 현금을 찾을 수 없는 경우,")
print("별도의 예수금 조회 API를 사용해야 합니다.")
print("="*80)
