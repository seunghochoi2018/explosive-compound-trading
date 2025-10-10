#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS 토큰 재발급 및 계좌 확인
"""

import json
import requests
import time
import os

# KIS API 설정
APP_KEY = "PSi3RlRt3DWtPPKTdYNALowIoeUBgM5mMLYO"
APP_SECRET = "Q7LxW5oIlCeg+doJCkmPDgXw7uy8bjC7ACRQR1GrAzgCF3zH7LziMix/QJgweS+IRU+uM/3GPELXVeOGocKQnHZ+RPeH4bqR1CgFOs9tHmRtGmxCiwt3+1yp7yctt+bBc85eDrIsrX9KfOkrLY+wVuE1tthKYsDyiF2YKrOp/e1PsSD0mdI="
CANO = "43113014"  # 8자리 버전
BASE_URL = "https://openapi.koreainvestment.com:9443"

def get_new_token():
    """새로운 토큰 발급"""
    url = f"{BASE_URL}/oauth2/tokenP"
    headers = {"content-type": "application/json; charset=utf-8"}
    data = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
    }

    print("토큰 발급 중...")
    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        result = response.json()
        token = result.get("access_token")
        print(f"[SUCCESS] 토큰 발급 성공!")

        # 토큰을 파일로 저장
        token_data = {
            "access_token": token,
            "expires_at": time.time() + 23 * 3600,
            "created_at": time.time()
        }

        with open("kis_token.json", 'w') as f:
            json.dump(token_data, f, indent=2)
        print(f"[INFO] kis_token.json 파일 저장됨")

        return token
    else:
        print(f"[ERROR] 토큰 발급 실패: {response.status_code}")
        print(f"응답: {response.text}")
        return None

def test_overseas_account(token):
    """해외주식 계좌 테스트"""
    print("\n해외주식 계좌 확인 중...")

    # 현재가 조회 테스트
    url = f"{BASE_URL}/uapi/overseas-price/v1/quotations/price"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "HHDFS00000300",
        "custtype": "P"
    }

    params = {
        "AUTH": "",
        "EXCD": "NAS",
        "SYMB": "NVDL"
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        result = response.json()
        if result.get("rt_cd") == "0":
            output = result.get("output", {})
            price = output.get("last", "N/A")
            print(f"[SUCCESS] NVDL 현재가: ${price}")
            return True
        else:
            print(f"[ERROR] 가격 조회 실패: {result.get('msg1', '')}")
            return False
    else:
        print(f"[ERROR] HTTP 오류: {response.status_code}")
        return False

def main():
    print("="*60)
    print("KIS 토큰 재발급 및 시스템 확인")
    print("="*60)

    # 1. 새 토큰 발급
    token = get_new_token()
    if not token:
        print("\n[FAIL] 토큰 발급 실패 - API 키 확인 필요")
        return

    # 2. 해외계좌 테스트
    if test_overseas_account(token):
        print("\n[SUCCESS] 시스템 정상 작동!")
        print("NVIDIA 트레이더 사용 가능합니다.")
    else:
        print("\n[WARNING] 가격 조회 실패")

if __name__ == "__main__":
    main()