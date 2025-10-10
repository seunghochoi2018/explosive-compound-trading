#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS API 직접 테스트 - 간단한 버전
"""

import requests
import json
import time

# API 정보
APP_KEY = "PSi3RlRt3DWtPPKTdYNALowIoeUBgM5mMLYO"
APP_SECRET = "Q7LxW5oIlCeg+doJCkmPDgXw7uy8bjC7ACRQR1GrAzgCF3zH7LziMix/QJgweS+IRU+uM/3GPELXVeOGocKQnHZ+RPeH4bqR1CgFOs9tHmRtGmxCiwt3+1yp7yctt+bBc85eDrIsrX9KfOkrLY+wVuE1tthKYSDyiF2YKrOp/e1PsSD0mdI="

print("KIS API 테스트")
print("="*50)

# 1. 실전 토큰 발급 시도
print("\n1. 실전 토큰 발급 시도...")
url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
headers = {"content-type": "application/json"}
data = {
    "grant_type": "client_credentials",
    "appkey": APP_KEY,
    "appsecret": APP_SECRET
}

response = requests.post(url, headers=headers, json=data)
print(f"응답 코드: {response.status_code}")
if response.status_code == 200:
    token = response.json().get("access_token")
    print(f"토큰 발급 성공!")
    print(f"토큰 앞 50자: {token[:50]}...")
else:
    print(f"오류: {response.text}")

    # 2. 모의투자 토큰 발급 시도
    print("\n2. 모의투자 토큰 발급 시도...")
    url = "https://openapivts.koreainvestment.com:29443/oauth2/tokenP"  # 모의투자 URL
    response = requests.post(url, headers=headers, json=data)
    print(f"응답 코드: {response.status_code}")
    if response.status_code == 200:
        token = response.json().get("access_token")
        print(f"모의투자 토큰 발급 성공!")
        print(f"토큰 앞 50자: {token[:50]}...")
    else:
        print(f"오류: {response.text}")

print("\n테스트 완료")