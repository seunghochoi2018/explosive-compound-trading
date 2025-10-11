#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS Access Token 재발급 스크립트
"""
import yaml
import requests
import json
import os

# 설정 로드
config_path = os.path.join(os.path.dirname(__file__), 'kis_devlp.yaml')
with open(config_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 토큰 발급 API 호출
url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
headers = {
    "content-type": "application/json"
}
body = {
    "grant_type": "client_credentials",
    "appkey": config['my_app'],
    "appsecret": config['my_sec']
}

print("[토큰 발급 시작]")
print(f"AppKey: {config['my_app'][:20]}...")
print(f"URL: {url}")

response = requests.post(url, headers=headers, json=body)

print(f"\n[응답] HTTP {response.status_code}")
print(response.text)

if response.status_code == 200:
    token_data = response.json()

    if 'access_token' in token_data:
        # 토큰 파일 저장
        token_file = os.path.join(os.path.dirname(__file__), 'kis_token.json')
        with open(token_file, 'w', encoding='utf-8') as f:
            json.dump(token_data, f, indent=2)

        print(f"\n [토큰 발급 성공]")
        print(f"Access Token: {token_data['access_token'][:30]}...")
        print(f"Expires In: {token_data.get('expires_in', 'N/A')} 초")
        print(f"저장 경로: {token_file}")
    else:
        print("\n [토큰 발급 실패] access_token이 응답에 없습니다")
else:
    print(f"\n [토큰 발급 실패] HTTP {response.status_code}")
