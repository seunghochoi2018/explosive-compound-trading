#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
최종 잔고 테스트 - 엑셀 문서 기준
"""

import json
import requests

# 토큰 로드
with open("kis_token.json", 'r') as f:
    token = json.load(f)['access_token']

APP_KEY = "PSi3RlRt3DWtPPKTdYNALowIoeUBgM5mMLYO"
APP_SECRET = "Q7LxW5oIlCeg+doJCkmPDgXw7uy8bjC7ACRQR1GrAzgCF3zH7LziMix/QJgweS+IRU+uM/3GPELXVeOGocKQnHZ+RPeH4bqR1Ciwt3+1yp7yctt+bBc85eDrIsrX9KfOkrLY+wVuE1tthKYsDyiF2YKrOp/e1PsSD0mdI="
BASE_URL = "https://openapi.koreainvestment.com:9443"

print("=" * 80)
print("잔고 조회 최종 테스트 (엑셀 문서 기준)")
print("=" * 80)

# 엑셀 문서 기준 정확한 파라미터
url = f"{BASE_URL}/uapi/overseas-stock/v1/trading/inquire-balance"
headers = {
    "Content-Type": "application/json; charset=utf-8",
    "authorization": f"Bearer {token}",
    "appkey": APP_KEY,
    "appsecret": APP_SECRET,
    "tr_id": "TTTS3012R",
    "custtype": "P"
}

params = {
    "CANO": "43113014",
    "ACNT_PRDT_CD": "01",
    "OVRS_EXCG_CD": "NASD",
    "TR_CRCY_CD": "USD",
    "CTX_AREA_FK200": "",
    "CTX_AREA_NK200": ""
}

print(f"\n[요청 정보]")
print(f"URL: {url}")
print(f"TR_ID: TTTS3012R")
print(f"계좌: 43113014-01")
print(f"거래소: NASD (나스닥)")
print(f"통화: USD")

response = requests.get(url, headers=headers, params=params, timeout=10)

print(f"\n[응답 정보]")
print(f"HTTP 상태: {response.status_code}")

if response.status_code == 200:
    result = response.json()
    rt_cd = result.get('rt_cd')
    msg1 = result.get('msg1', '')
    msg_cd = result.get('msg_cd', '')

    print(f"rt_cd: {rt_cd}")
    print(f"msg_cd: {msg_cd}")
    print(f"msg1: {msg1}")

    if rt_cd == '0':
        print("\n[성공] 잔고 조회 성공!")

        # output2 확인 (엑셀 문서: object 타입)
        output2 = result.get('output2')

        print(f"\noutput2 존재: {output2 is not None}")
        print(f"output2 타입: {type(output2).__name__}")

        if output2:
            # output2가 list인 경우
            if isinstance(output2, list):
                if len(output2) > 0:
                    balance_info = output2[0]
                    print(f"output2는 list, 길이: {len(output2)}")
                else:
                    print("output2는 빈 list")
                    balance_info = {}
            # output2가 dict인 경우
            elif isinstance(output2, dict):
                balance_info = output2
                print(f"output2는 dict, 키 개수: {len(output2)}")
            else:
                print(f"output2는 예상하지 못한 타입: {type(output2)}")
                balance_info = {}

            if balance_info:
                print(f"\n[잔고 정보 전체]")
                for key, value in balance_info.items():
                    print(f"  {key}: {value}")

                print(f"\n[핵심 USD 잔고 필드]")

                # 엑셀 문서 기준 주요 필드
                key_fields = {
                    'frcr_buy_amt_smtl1': '외화매수금액합계1 (매수 가능)',
                    'frcr_buy_amt_smtl2': '외화매수금액합계2',
                    'frcr_pchs_amt1': '외화매입금액1',
                    'ovrs_tot_pfls': '해외총손익',
                    'tot_evlu_pfls_amt': '총평가손익금액'
                }

                for field, desc in key_fields.items():
                    if field in balance_info:
                        value = balance_info[field]
                        try:
                            num_val = float(value) if value else 0
                            print(f"  {field} ({desc}): ${num_val:,.2f}")
                        except:
                            print(f"  {field} ({desc}): {value}")

                # 최종 USD 잔고 결정
                usd_balance = 0
                for field in ['frcr_buy_amt_smtl1', 'frcr_buy_amt_smtl2', 'frcr_pchs_amt1']:
                    if field in balance_info:
                        try:
                            val = float(balance_info[field]) if balance_info[field] else 0
                            if val > 0:
                                usd_balance = val
                                print(f"\n>>> USD 잔고: ${usd_balance:,.2f} (필드: {field})")
                                break
                        except:
                            continue

                if usd_balance == 0:
                    print(f"\n>>> 모든 필드가 $0 또는 파싱 실패")

        # output1 확인 (보유 종목)
        output1 = result.get('output1', [])
        if output1:
            print(f"\n[보유 종목]")
            print(f"종목 수: {len(output1)}")
            for item in output1[:5]:
                symbol = item.get('ovrs_pdno', '')
                qty = item.get('ovrs_cblc_qty', 0)
                if symbol:
                    print(f"  {symbol}: {qty}주")
    else:
        print(f"\n[실패] rt_cd != 0")
        print(f"전체 응답: {json.dumps(result, indent=2, ensure_ascii=False)}")
else:
    print(f"\n[HTTP 오류]")
    print(f"응답 본문: {response.text}")

print("\n" + "=" * 80)
