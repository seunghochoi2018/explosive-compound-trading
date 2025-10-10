#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SOXL 실시간 가격 조회 테스트
"""

import yaml
import requests
import json

with open('kis_devlp.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

with open('kis_token.json', 'r') as f:
    token_data = json.load(f)
    access_token = token_data['access_token']

url = "https://openapi.koreainvestment.com:9443/uapi/overseas-price/v1/quotations/price"

# 다양한 거래소 코드 시도
exchange_codes = ["NAS", "NASD", "NYS", "NYSE"]

for excd in exchange_codes:
    print(f"\n테스트: EXCD={excd}, SYMB=SOXL")
    print("="*60)

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {access_token}",
        "appkey": config['my_app'],
        "appsecret": config['my_sec'],
        "tr_id": "HHDFS00000300",
        "custtype": "P",
        "User-Agent": config.get('my_agent', 'Mozilla/5.0')
    }

    params = {
        "AUTH": "",
        "EXCD": excd,
        "SYMB": "SOXL"
    }

    response = requests.get(url, headers=headers, params=params, timeout=10)

    print(f"HTTP: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"rt_cd: {result.get('rt_cd')}")
        print(f"msg1: {result.get('msg1')}")

        if result.get('rt_cd') == '0':
            output = result.get('output', {})

            print(f"\n전체 output:")
            for key, value in output.items():
                if value:
                    print(f"  {key}: {value}")

            price = output.get('last', '')
            print(f"\nlast 필드: '{price}'")

            if price:
                print(f"[SUCCESS] SOXL 가격: ${float(price):.2f}")
            else:
                print(f"[NOTICE] 가격 정보 없음 (장 마감 후이거나 데이터 없음)")
        else:
            print(f"[FAIL] {result.get('msg1')}")
    else:
        print(f"[HTTP ERROR]")
        print(response.text[:200])
