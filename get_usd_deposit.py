#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USD 예수금(매수가능금액) 조회
"""

import yaml
import requests
import json
import os

yaml_path = os.path.join(os.path.dirname(__file__), 'kis_devlp.yaml')
with open(yaml_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

print("="*80)
print("USD 예수금 조회 (해외주식 매수가능금액)")
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

# API 1: 해외주식 매수가능금액 조회 (TTTS3007R / JTTT3007R)
print("="*80)
print("API 1: 해외주식 매수가능금액 조회")
print("="*80)

buy_power_url = "https://openapi.koreainvestment.com:9443/uapi/overseas-stock/v1/trading/inquire-psamount"

# 실전/모의 TR_ID 모두 시도
tr_ids = [("JTTT3007R", "실전"), ("TTTS3007R", "모의")]

for tr_id, acc_type in tr_ids:
    print(f"\n[{acc_type}계좌 - {tr_id}]")

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {access_token}",
        "appkey": config['my_app'],
        "appsecret": config['my_sec'],
        "tr_id": tr_id,
        "custtype": "P",
        "User-Agent": config['my_agent']
    }

    # OVRS_ORD_UNPR은 조회할 종목의 예상 가격 (필수 파라미터인 경우 사용)
    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "OVRS_EXCG_CD": "NASD",
        "OVRS_ORD_UNPR": "",  # 빈 문자열로 시도
        "ITEM_CD": ""
    }

    response = requests.get(buy_power_url, headers=headers, params=params, timeout=10)

    print(f"HTTP: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"rt_cd: {result.get('rt_cd')}")
        print(f"msg1: {result.get('msg1')}")

        if result.get('rt_cd') == '0':
            output = result.get('output', {})

            print(f"\n[매수가능금액 정보]")
            for key, value in output.items():
                print(f"  {key}: {value}")

            # 주요 필드
            ord_psbl_cash = output.get('ord_psbl_cash', '0')
            ord_psbl_frcr_amt = output.get('ord_psbl_frcr_amt', '0')

            try:
                cash = float(ord_psbl_cash.replace(',', ''))
                frcr_amt = float(ord_psbl_frcr_amt.replace(',', ''))

                print(f"\n*** 주문가능현금: ${cash:.2f}")
                print(f"*** 주문가능외화금액: ${frcr_amt:.2f}")

                if cash > 0 or frcr_amt > 0:
                    print(f"\n[성공] USD 현금을 찾았습니다!")
            except Exception as e:
                print(f"\n변환 오류: {e}")

        else:
            print(f"[실패] {result.get('msg1')}")
            # 파라미터 필수 여부 확인
            if "INPUT_FIELD" in result.get('msg1', ''):
                print(f"\n재시도: OVRS_ORD_UNPR에 기본값 입력")
                params['OVRS_ORD_UNPR'] = "40.0"  # SOXL 가격
                params['ITEM_CD'] = "SOXL"

                response2 = requests.get(buy_power_url, headers=headers, params=params, timeout=10)
                if response2.status_code == 200:
                    result2 = response2.json()
                    if result2.get('rt_cd') == '0':
                        output2 = result2.get('output', {})
                        print(f"\n[재시도 성공]")
                        for key, value in output2.items():
                            print(f"  {key}: {value}")
    else:
        print(f"응답: {response.text[:200]}")

print("\n" + "="*80)
print("완료")
print("="*80)
