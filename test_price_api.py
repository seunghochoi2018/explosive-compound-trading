#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
가격 조회 API 디버깅
"""

import yaml
import requests
import json
import os

yaml_path = os.path.join(os.path.dirname(__file__), 'kis_devlp.yaml')
with open(yaml_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

print("="*80)
print("가격 조회 API 디버깅")
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

# SOXL 가격 조회
symbol = "SOXL"
url = "https://openapi.koreainvestment.com:9443/uapi/overseas-price/v1/quotations/price"

headers = {
    "Content-Type": "application/json; charset=utf-8",
    "authorization": f"Bearer {access_token}",
    "appkey": config['my_app'],
    "appsecret": config['my_sec'],
    "tr_id": "HHDFS00000300",
    "custtype": "P",
    "User-Agent": config['my_agent']
}

params = {
    "AUTH": "",
    "EXCD": "NAS",
    "SYMB": symbol
}

print(f"{'='*80}")
print(f"[{symbol} 가격 조회]")
print(f"{'='*80}")
print(f"URL: {url}")
print(f"TR_ID: HHDFS00000300")
print(f"EXCD: NAS")
print(f"SYMB: {symbol}\n")

response = requests.get(url, headers=headers, params=params, timeout=10)

print(f"HTTP Status: {response.status_code}\n")

if response.status_code == 200:
    result = response.json()

    print(f"rt_cd: {result.get('rt_cd')}")
    print(f"msg_cd: {result.get('msg_cd')}")
    print(f"msg1: {result.get('msg1')}\n")

    if result.get('rt_cd') == '0':
        output = result.get('output', {})

        print(f"[가격 데이터]")
        print(f"  last (현재가): {output.get('last', 'N/A')}")
        print(f"  open (시가): {output.get('open', 'N/A')}")
        print(f"  high (고가): {output.get('high', 'N/A')}")
        print(f"  low (저가): {output.get('low', 'N/A')}")
        print(f"  volume (거래량): {output.get('tvol', 'N/A')}")

        price = float(output.get('last', 0))
        if price > 0:
            print(f"\n[OK] SOXL 가격: ${price:.2f}")
        else:
            print(f"\n[ERROR] 가격이 0입니다")
            print(f"\n전체 output:")
            print(json.dumps(output, indent=2))
    else:
        print(f"[ERROR] 가격 조회 실패")
        print(f"\n전체 응답:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
else:
    print(f"[ERROR] HTTP {response.status_code}")
    print(f"\n응답 내용:")
    print(response.text)

print(f"\n{'='*80}")
