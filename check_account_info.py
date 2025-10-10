#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
계좌 정보 확인 - 실전 vs 모의, 국내 vs 해외
"""

import json
import requests

with open("kis_token.json", 'r') as f:
    token = json.load(f)['access_token']

APP_KEY = "PSi3RlRt3DWtPPKTdYNALowIoeUBgM5mMLYO"
APP_SECRET = "Q7LxW5oIlCeg+doJCkmPDgXw7uy8bjC7ACRQR1GrAzgCF3zH7LziMix/QJgweS+IRU+uM/3GPELXVeOGocKQnHZ+RPeH4bqR1Ciwt3+1yp7yctt+bBc85eDrIsrX9KfOkrLY+wVuE1tthKYSDyiF2YKrOp/e1PsSD0mdI="

print("=" * 80)
print("한국투자증권 계좌 유형 확인")
print("=" * 80)

tests = [
    {
        "name": "실전 - 해외주식 잔고",
        "base_url": "https://openapi.koreainvestment.com:9443",
        "tr_id": "TTTS3012R",
        "endpoint": "/uapi/overseas-stock/v1/trading/inquire-balance",
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
        "name": "모의 - 해외주식 잔고",
        "base_url": "https://openapivts.koreainvestment.com:29443",
        "tr_id": "VTTS3012R",
        "endpoint": "/uapi/overseas-stock/v1/trading/inquire-balance",
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
        "name": "실전 - 국내주식 잔고",
        "base_url": "https://openapi.koreainvestment.com:9443",
        "tr_id": "TTTC8434R",
        "endpoint": "/uapi/domestic-stock/v1/trading/inquire-balance",
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
    },
    {
        "name": "실전 - 해외주식 현재가 (SOXL)",
        "base_url": "https://openapi.koreainvestment.com:9443",
        "tr_id": "HHDFS00000300",
        "endpoint": "/uapi/overseas-price/v1/quotations/price",
        "params": {
            "AUTH": "",
            "EXCD": "NAS",
            "SYMB": "SOXL"
        }
    }
]

for test in tests:
    print(f"\n{'=' * 80}")
    print(f"[테스트] {test['name']}")
    print(f"{'=' * 80}")
    print(f"URL: {test['base_url']}{test['endpoint']}")
    print(f"TR_ID: {test['tr_id']}")

    url = f"{test['base_url']}{test['endpoint']}"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": test['tr_id'],
        "custtype": "P"
    }

    try:
        response = requests.get(url, headers=headers, params=test['params'], timeout=10)

        print(f"\nHTTP: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            rt_cd = result.get('rt_cd', 'N/A')
            msg1 = result.get('msg1', '')

            print(f"rt_cd: {rt_cd}")
            print(f"msg1: {msg1}")

            if rt_cd == '0':
                print(">>> [성공] 이 API는 작동합니다!")

                # 간단한 데이터 확인
                if 'output' in result:
                    print(f"output 타입: {type(result['output']).__name__}")
                if 'output1' in result:
                    print(f"output1 길이: {len(result.get('output1', []))}")
                if 'output2' in result:
                    output2 = result['output2']
                    if isinstance(output2, list):
                        print(f"output2 길이: {len(output2)}")
                        if output2:
                            print(f"output2[0] 키 개수: {len(output2[0]) if isinstance(output2[0], dict) else 0}")
                    elif isinstance(output2, dict):
                        print(f"output2 키 개수: {len(output2)}")
            else:
                print(f">>> [실패] rt_cd != 0")
        else:
            print(f">>> HTTP 오류")

    except Exception as e:
        print(f">>> 예외: {e}")

print(f"\n{'=' * 80}")
print("결론:")
print("- 작동하는 API를 찾으면 그것으로 계좌 유형을 확인할 수 있습니다")
print("- 모든 API가 실패하면 APP_KEY 권한 문제일 가능성이 높습니다")
print("=" * 80)
