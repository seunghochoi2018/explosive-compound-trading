#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAML 기반 KIS 인증 테스트 (공식 방식)
"""

import yaml
import requests
import json

print("=" * 80)
print("YAML 기반 KIS 인증 테스트")
print("=" * 80)

# YAML 설정 로드
import os
yaml_path = os.path.join(os.path.dirname(__file__), 'kis_devlp.yaml')
print(f"\n[YAML 경로] {yaml_path}")

with open(yaml_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

print(f"[로드된 키] {list(config.keys())}")

print(f"\n[설정 로드]")
print(f"APP_KEY: {config['my_app'][:20]}...")
print(f"계좌: {config['my_acct']}")
print(f"User-Agent: {config['my_agent']}")

# 토큰 발급
print(f"\n[토큰 발급]")
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

print(f"HTTP: {response.status_code}")

if response.status_code == 200:
    result = response.json()
    access_token = result.get("access_token")

    print(f"토큰 발급 성공!")
    print(f"Access Token: {access_token[:50]}...")

    # 토큰 저장
    token_data = {
        "access_token": access_token,
        "expires_at": result.get("access_token_token_expired"),
        "token_type": result.get("token_type")
    }

    with open("kis_token.json", 'w') as f:
        json.dump(token_data, f, indent=2)

    print(f"kis_token.json 저장 완료")

    # 가격 조회 테스트
    print(f"\n[가격 조회 테스트]")

    price_url = "https://openapi.koreainvestment.com:9443/uapi/overseas-price/v1/quotations/price"
    price_headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {access_token}",
        "appkey": config['my_app'],
        "appsecret": config['my_sec'],
        "tr_id": "HHDFS00000300",
        "custtype": "P"
    }

    price_params = {
        "AUTH": "",
        "EXCD": "NAS",
        "SYMB": "SOXL"
    }

    price_response = requests.get(price_url, headers=price_headers, params=price_params, timeout=10)

    print(f"HTTP: {price_response.status_code}")

    if price_response.status_code == 200:
        price_result = price_response.json()
        if price_result.get('rt_cd') == '0':
            price = price_result.get('output', {}).get('last', 'N/A')
            print(f"SOXL 가격: ${price}")
            print(f"\n>>> 성공! 가격 조회 작동")
        else:
            print(f"가격 조회 실패: {price_result.get('msg1')}")
    else:
        print(f"HTTP 오류: {price_response.text}")

    # 잔고 조회 테스트
    print(f"\n[잔고 조회 테스트]")

    # 계좌번호 파싱
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
            output2 = balance_result.get('output2')
            if output2:
                if isinstance(output2, list) and output2:
                    bal_info = output2[0]
                elif isinstance(output2, dict):
                    bal_info = output2
                else:
                    bal_info = {}

                usd_balance = bal_info.get('frcr_buy_amt_smtl1', '0')
                print(f"USD 잔고: ${usd_balance}")
                print(f"\n>>> 성공! 잔고 조회 작동")
            else:
                print(f"output2 없음")
        else:
            print(f"잔고 조회 실패")
            print(f"전체 응답: {json.dumps(balance_result, indent=2)}")
    else:
        print(f"HTTP 오류: {balance_response.text}")

else:
    print(f"토큰 발급 실패: {response.text}")

print(f"\n" + "=" * 80)
