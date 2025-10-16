#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KIS 최종 시도 - 모든 가능한 조합"""
import json
import yaml
import requests
from datetime import datetime

print("="*80)
print("KIS 최종 시도 - 모든 가능한 조합 테스트")
print("="*80)

# 설정 로드
with open('kis_devlp.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

with open('kis_token.json', 'r', encoding='utf-8') as f:
    token_data = json.load(f)

app_key = config['my_app']
app_secret = config['my_sec']
account_no = config['my_acct']
access_token = token_data['access_token']
base_url = "https://openapi.koreainvestment.com:9443"

# 현재가
fmp_url = "https://financialmodelingprep.com/api/v3/quote/SOXL"
fmp_response = requests.get(fmp_url, params={'apikey': '5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI'}, timeout=10)
current_price = 41.5
if fmp_response.status_code == 200:
    fmp_data = fmp_response.json()
    if fmp_data:
        current_price = fmp_data[0].get('price', 41.5)

print(f"SOXL 현재가: ${current_price:.2f}")

# 다양한 조합 시도
order_url = f"{base_url}/uapi/overseas-stock/v1/trading/order"

test_cases = [
    {
        "name": "방법 1: 헤더에 타임스탬프 추가",
        "headers": {
            "authorization": f"Bearer {access_token}",
            "appkey": app_key,
            "appsecret": app_secret,
            "tr_id": "JTTT1002U",
            "custtype": "P",
            "content-type": "application/json; charset=utf-8",
            "tr_cont": "N",
            "tr_cont_key": "",
            "timestamp": datetime.now().strftime("%Y%m%d%H%M%S")
        },
        "data": {
            "CANO": account_no.split('-')[0],
            "ACNT_PRDT_CD": account_no.split('-')[1],
            "OVRS_EXCG_CD": "NASD",
            "PDNO": "A980679",
            "ORD_QTY": "1",
            "OVRS_ORD_UNPR": str(current_price),
            "ORD_SVR_DVSN_CD": "0"
        }
    },
    {
        "name": "방법 2: Body에 TR_TIME 추가",
        "headers": {
            "authorization": f"Bearer {access_token}",
            "appkey": app_key,
            "appsecret": app_secret,
            "tr_id": "JTTT1002U",
            "custtype": "P",
            "content-type": "application/json; charset=utf-8"
        },
        "data": {
            "TR_TIME": datetime.now().strftime("%H%M%S"),
            "CANO": account_no.split('-')[0],
            "ACNT_PRDT_CD": account_no.split('-')[1],
            "OVRS_EXCG_CD": "NASD",
            "PDNO": "A980679",
            "ORD_QTY": "1",
            "OVRS_ORD_UNPR": str(current_price),
            "ORD_SVR_DVSN_CD": "0"
        }
    },
    {
        "name": "방법 3: Body에 ORD_DT 추가",
        "headers": {
            "authorization": f"Bearer {access_token}",
            "appkey": app_key,
            "appsecret": app_secret,
            "tr_id": "JTTT1002U",
            "custtype": "P",
            "content-type": "application/json; charset=utf-8"
        },
        "data": {
            "ORD_DT": datetime.now().strftime("%Y%m%d"),
            "CANO": account_no.split('-')[0],
            "ACNT_PRDT_CD": account_no.split('-')[1],
            "OVRS_EXCG_CD": "NASD",
            "PDNO": "A980679",
            "ORD_QTY": "1",
            "OVRS_ORD_UNPR": str(current_price),
            "ORD_SVR_DVSN_CD": "0"
        }
    },
    {
        "name": "방법 4: Body에 INQR_TIME 추가",
        "headers": {
            "authorization": f"Bearer {access_token}",
            "appkey": app_key,
            "appsecret": app_secret,
            "tr_id": "JTTT1002U",
            "custtype": "P",
            "content-type": "application/json; charset=utf-8"
        },
        "data": {
            "INQR_TIME": datetime.now().strftime("%H%M%S%f")[:10],
            "CANO": account_no.split('-')[0],
            "ACNT_PRDT_CD": account_no.split('-')[1],
            "OVRS_EXCG_CD": "NASD",
            "PDNO": "A980679",
            "ORD_QTY": "1",
            "OVRS_ORD_UNPR": str(current_price),
            "ORD_SVR_DVSN_CD": "0"
        }
    },
    {
        "name": "방법 5: 모든 타임 필드 추가",
        "headers": {
            "authorization": f"Bearer {access_token}",
            "appkey": app_key,
            "appsecret": app_secret,
            "tr_id": "JTTT1002U",
            "custtype": "P",
            "content-type": "application/json; charset=utf-8",
            "timestamp": datetime.now().strftime("%Y%m%d%H%M%S")
        },
        "data": {
            "TR_TIME": datetime.now().strftime("%H%M%S"),
            "ORD_DT": datetime.now().strftime("%Y%m%d"),
            "CANO": account_no.split('-')[0],
            "ACNT_PRDT_CD": account_no.split('-')[1],
            "OVRS_EXCG_CD": "NASD",
            "PDNO": "A980679",
            "ORD_QTY": "1",
            "OVRS_ORD_UNPR": str(current_price),
            "ORD_SVR_DVSN_CD": "0",
            "SLL_TYPE": "",
            "ORD_DVSN": "00"
        }
    }
]

for idx, test in enumerate(test_cases, 1):
    print(f"\n{'='*80}")
    print(f"[시도 {idx}/5] {test['name']}")
    print(f"{'='*80}")

    print("Body:")
    print(json.dumps(test['data'], indent=2, ensure_ascii=False))

    try:
        response = requests.post(order_url, headers=test['headers'], json=test['data'], timeout=30)

        print(f"\n응답: HTTP {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"rt_cd: {result.get('rt_cd')}")
            print(f"msg_cd: {result.get('msg_cd')}")
            print(f"msg1: {result.get('msg1')}")

            if result.get('rt_cd') == '0':
                print(f"\n{'='*80}")
                print(f"[SUCCESS] {test['name']} 성공!")
                print(f"{'='*80}")
                exit(0)
            else:
                print(f"[실패] {result.get('msg_cd')}: {result.get('msg1')}")
        else:
            result = response.json()
            print(f"[실패] {result.get('msg_cd')}: {result.get('msg1')}")

    except Exception as e:
        print(f"[ERROR] {e}")

print(f"\n{'='*80}")
print("모든 방법 실패")
print(f"{'='*80}")
print("\n[최종 결론]")
print("EGW00356 에러는 KIS API 문서에 명시되지 않은 필드가 필요합니다.")
print("\n권장 조치:")
print("1. KIS 고객센터 (1544-5000) 문의")
print("   → 해외주식 주문 API의 정확한 필드 구조 확인")
print("2. 또는 한투 HTS/MTS 앱에서 수동 거래")
print("3. 페이퍼 트레이딩으로 전략 검증 후 수동 실행")
