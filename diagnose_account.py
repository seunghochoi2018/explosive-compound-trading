#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""계좌 진단 도구"""

import json
import requests
from datetime import datetime

# 설정
with open("kis_token.json", 'r') as f:
    token_data = json.load(f)
    token = token_data['access_token']

APP_KEY = "PSi3RlRt3DWtPPKTdYNALowIoeUBgM5mMLYO"
APP_SECRET = "Q7LxW5oIlCeg+doJCkmPDgXw7uy8bjC7ACRQR1GrAzgCF3zH7LziMix/QJgweS+IRU+uM/3GPELXVeOGocKQnHZ+RPeH4bqR1Ciwt3+1yp7yctt+bBc85eDrIsrX9KfOkrLY+wVuE1tthKYsDyiF2YKrOp/e1PsSD0mdI="

print("=" * 80)
print("KIS 계좌 종합 진단")
print("=" * 80)
print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"계좌: 43113014-01")
print(f"토큰 만료: {datetime.fromtimestamp(token_data['expires_at']).strftime('%Y-%m-%d %H:%M:%S')}")

# 테스트할 엔드포인트들
tests = [
    {
        "name": "해외주식 잔고 (실전)",
        "url": "https://openapi.koreainvestment.com:9943/uapi/overseas-stock/v1/trading/inquire-balance",
        "tr_id": "TTTS3012R",
        "params": {
            "CANO": "43113014",
            "ACNT_PRDT_CD": "01",
            "OVRS_EXCG_CD": "NASD",
            "TR_CRCY_CD": "USD",
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": ""
        }
    },
    {
        "name": "국내주식 잔고",
        "url": "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/trading/inquire-balance",
        "tr_id": "TTTC8434R",
        "params": {
            "CANO": "43113014",
            "ACNT_PRDT_CD": "01",
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
    }
]

for test in tests:
    print(f"\n{'=' * 80}")
    print(f"[테스트] {test['name']}")
    print(f"{'=' * 80}")
    print(f"URL: {test['url']}")
    print(f"TR_ID: {test['tr_id']}")

    headers = {
        "Content-Type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": test['tr_id']
    }

    try:
        response = requests.get(test['url'], headers=headers, params=test['params'], timeout=10)

        print(f"\n[응답]")
        print(f"HTTP 상태: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            rt_cd = result.get('rt_cd', 'N/A')
            msg1 = result.get('msg1', 'N/A')

            print(f"rt_cd: {rt_cd}")
            print(f"msg1: {msg1}")

            if rt_cd == '0':
                print("[성공]")

                # output 데이터 확인
                for key in ['output1', 'output2', 'output']:
                    if key in result:
                        data = result[key]
                        print(f"\n{key} (타입: {type(data).__name__}):")
                        if isinstance(data, list):
                            print(f"  길이: {len(data)}")
                            if data:
                                print(f"  첫 항목: {data[0]}")
                        elif isinstance(data, dict):
                            print(f"  항목 수: {len(data)}")
                            for k, v in list(data.items())[:5]:
                                print(f"  {k}: {v}")
            else:
                print(f"[실패] {msg1}")
        else:
            print(f"[HTTP 오류] {response.text[:200]}")

    except Exception as e:
        print(f"[예외] {e}")

print(f"\n{'=' * 80}")
print("진단 완료")
print("=" * 80)
