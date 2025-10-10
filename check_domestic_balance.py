#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
국내주식 잔고 확인 (147,537원 찾기)
"""

import yaml
import requests
import json
import os

yaml_path = os.path.join(os.path.dirname(__file__), 'kis_devlp.yaml')
with open(yaml_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

print("="*80)
print("국내주식 잔고 확인 (147,537원 찾기)")
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

# 국내주식 잔고 조회
print(f"{'='*80}")
print(f"국내주식 잔고 조회 (계좌: {cano}-{acnt_prdt_cd})")
print(f"{'='*80}")

balance_url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/trading/inquire-balance"

balance_headers = {
    "Content-Type": "application/json; charset=utf-8",
    "authorization": f"Bearer {access_token}",
    "appkey": config['my_app'],
    "appsecret": config['my_sec'],
    "tr_id": "TTTC8434R",  # 실전투자 잔고조회
    "custtype": "P"
}

balance_params = {
    "CANO": cano,
    "ACNT_PRDT_CD": acnt_prdt_cd,
    "AFHR_FLPR_YN": "N",
    "OFL_YN": "",
    "INQR_DVSN": "02",
    "UNPR_DVSN": "01",
    "FUND_STTL_ICLD_YN": "N",
    "FNCG_AMT_AUTO_RDPT_YN": "N",
    "PRCS_DVSN": "01",
    "CTX_AREA_FK100": "",
    "CTX_AREA_NK100": ""
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
        if output1:
            print(f"보유종목:")
            for stock in output1:
                if int(stock.get('hldg_qty', '0')) > 0:
                    pdno = stock.get('pdno', '')
                    prdt_name = stock.get('prdt_name', '')
                    hldg_qty = stock.get('hldg_qty', '0')
                    evlu_amt = stock.get('evlu_amt', '0')
                    print(f"  {pdno} {prdt_name}: {hldg_qty}주, 평가액: {int(evlu_amt):,}원")

        # output2: 예수금 정보
        output2 = balance_result.get('output2', [])
        if output2:
            output2_data = output2[0] if isinstance(output2, list) else output2

            # 주요 금액 필드들
            print(f"\n[예수금 정보]")
            dnca_tot_amt = output2_data.get('dnca_tot_amt', '0')
            nxdy_excc_amt = output2_data.get('nxdy_excc_amt', '0')
            prvs_rcdl_excc_amt = output2_data.get('prvs_rcdl_excc_amt', '0')
            cma_evlu_amt = output2_data.get('cma_evlu_amt', '0')
            tot_evlu_amt = output2_data.get('tot_evlu_amt', '0')
            nass_amt = output2_data.get('nass_amt', '0')

            print(f"  예수금 총액 (dnca_tot_amt): {int(dnca_tot_amt):,}원")
            print(f"  익일 정산 금액 (nxdy_excc_amt): {int(nxdy_excc_amt):,}원")
            print(f"  전일 미수금 (prvs_rcdl_excc_amt): {int(prvs_rcdl_excc_amt):,}원")
            print(f"  CMA 평가금액 (cma_evlu_amt): {int(cma_evlu_amt):,}원")
            print(f"  총 평가금액 (tot_evlu_amt): {int(tot_evlu_amt):,}원")
            print(f"  순자산 (nass_amt): {int(nass_amt):,}원")

            # 147537원 찾기
            if int(dnca_tot_amt) == 147537:
                print(f"\n  >>> 147,537원 발견! (예수금 총액)")
                print(f"  >>> 이 금액은 국내주식 계좌 예수금입니다")
                print(f"  >>> 해외주식 거래를 위해서는 환전이 필요합니다")
    else:
        print(f"조회 실패: {balance_result.get('msg1')}")
else:
    print(f"HTTP 오류: {balance_response.status_code}")
    print(f"{balance_response.text}")

print(f"\n{'='*80}")
