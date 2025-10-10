#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
올바른 TR_ID로 가격 조회
"""

import yaml
import requests
import json
import os

yaml_path = os.path.join(os.path.dirname(__file__), 'kis_devlp.yaml')
with open(yaml_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

print("="*80)
print("엑셀 TR_ID로 가격 조회: HHDFS76200200")
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

# SOXL 가격 조회 (엑셀 TR_ID 사용)
symbol = "SOXL"
url = "https://openapi.koreainvestment.com:9443/uapi/overseas-price/v1/quotations/price-detail"

headers = {
    "Content-Type": "application/json; charset=utf-8",
    "authorization": f"Bearer {access_token}",
    "appkey": config['my_app'],
    "appsecret": config['my_sec'],
    "tr_id": "HHDFS76200200",  # 엑셀 TR_ID
    "custtype": "P",
    "User-Agent": config['my_agent']
}

params = {
    "AUTH": "",
    "EXCD": "NAS",
    "SYMB": symbol
}

print(f"[{symbol} 가격 조회 - HHDFS76200200]")
print(f"URL: {url}\n")

response = requests.get(url, headers=headers, params=params, timeout=10)

print(f"HTTP Status: {response.status_code}\n")

if response.status_code == 200:
    result = response.json()

    print(f"rt_cd: {result.get('rt_cd')}")
    print(f"msg1: {result.get('msg1')}\n")

    if result.get('rt_cd') == '0':
        output = result.get('output', {})

        # 모든 필드 출력
        print(f"[응답 데이터]")
        for key, value in output.items():
            if value and str(value).strip():
                print(f"  {key}: {value}")

        # 가격 필드들 확인
        price_fields = ['last', 'curr', 'base', 'pvol', 'stck_prpr']
        for field in price_fields:
            if field in output and output[field]:
                try:
                    price = float(output[field])
                    if price > 0:
                        print(f"\n[OK] {field} 필드에서 가격 발견: ${price:.2f}")
                        break
                except:
                    pass
    else:
        print(f"[ERROR] 조회 실패")
        print(json.dumps(result, indent=2, ensure_ascii=False))
else:
    print(f"[ERROR] HTTP {response.status_code}")
    print(response.text)

# 기존 TR_ID도 한번 더 시도 (다른 endpoint)
print(f"\n{'='*80}")
print(f"[기존 TR_ID 재시도: HHDFS00000300]")
print(f"{'='*80}\n")

url2 = "https://openapi.koreainvestment.com:9443/uapi/overseas-price/v1/quotations/price"
headers['tr_id'] = "HHDFS00000300"

response2 = requests.get(url2, headers=headers, params=params, timeout=10)

if response2.status_code == 200:
    result2 = response2.json()
    if result2.get('rt_cd') == '0':
        output2 = result2.get('output', {})

        print(f"[모든 필드 확인]")
        for key, value in output2.items():
            print(f"  {key}: '{value}'")

print(f"\n{'='*80}")
