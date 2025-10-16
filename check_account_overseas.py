#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KIS 계좌 해외주식 거래 권한 확인"""
import json
import yaml
import requests

print("="*80)
print("KIS 계좌 정보 및 해외주식 거래 권한 확인")
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

# 1. 해외주식 잔고 조회
print("\n[1] 해외주식 잔고 조회...")
url = f"{base_url}/uapi/overseas-stock/v1/trading/inquire-balance"

headers = {
    "authorization": f"Bearer {access_token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": "TTTS3012R"
}

params = {
    "CANO": account_no.split('-')[0],
    "ACNT_PRDT_CD": account_no.split('-')[1],
    "WCRC_FRCR_DVSN_CD": "02",
    "NATN_CD": "840",
    "TR_MKET_CD": "01",
    "OVRS_EXCG_CD": "NASD",
    "TR_CRCY_CD": "USD",
    "CTX_AREA_FK100": "",
    "CTX_AREA_NK100": "",
    "CTX_AREA_FK200": "",
    "CTX_AREA_NK200": ""
}

try:
    response = requests.get(url, headers=headers, params=params, timeout=10)
    print(f"HTTP 상태: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"rt_cd: {data.get('rt_cd')}")
        print(f"msg_cd: {data.get('msg_cd')}")
        print(f"msg1: {data.get('msg1')}")

        if data.get('rt_cd') == '0':
            print("\n[OK] 해외주식 잔고 조회 성공")

            output1 = data.get('output1', [])
            output2 = data.get('output2', {})

            print(f"\n보유 종목: {len(output1)}개")
            for item in output1:
                print(f"  - {item.get('ovrs_item_name', 'N/A')}: {item.get('ovrs_cblc_qty', 0)}주")

            print(f"\n잔고 정보:")
            print(f"  USD 예수금: {output2.get('ovrs_ncash_blce_amt', 'N/A')}")
            print(f"  매수가능금액: {output2.get('ovrs_buy_psbl_amt', 'N/A')}")
            print(f"  평가금액: {output2.get('tot_evlu_pfls_amt', 'N/A')}")

            print("\n[분석]")
            if len(output1) > 0 or float(output2.get('ovrs_ncash_blce_amt', 0) or 0) > 0:
                print("  ✓ 해외주식 거래 권한 있음")
                print("  ✓ 계좌 정상")
            else:
                print("  ! USD 잔고 0")
                print("  ! 해외주식 보유 없음")
                print("\n[가능한 원인]")
                print("  1. 해외주식 거래 신청이 필요할 수 있음")
                print("  2. USD 입금 필요")
                print("  3. 실전투자 환경에서 EGW00356 에러는 타임스탬프 관련 문제")
        else:
            print(f"\n[ERROR] 잔고 조회 실패")
            print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"[ERROR] HTTP {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"[ERROR] 예외: {e}")
    import traceback
    traceback.print_exc()

# 2. 계좌 기본 정보
print(f"\n{'='*80}")
print("[2] 계좌 정보")
print(f"{'='*80}")
print(f"계좌번호: {account_no}")
print(f"API 키: {app_key[:10]}...")
print(f"환경: 실전투자 (https://openapi.koreainvestment.com:9443)")

print(f"\n{'='*80}")
print("[결론]")
print(f"{'='*80}")
print("EGW00356 에러 원인:")
print("  '타임 스탬프가 올바르지 않습니다'")
print("  → TR ID에 따라 첫 필드에 타임스탬프가 필요")
print("  → 하지만 KIS API 문서에 명시되지 않음")
print("\n권장 해결 방법:")
print("  1. KIS 고객센터 문의 (1544-5000)")
print("  2. 해외주식 주문 API 정확한 필드 확인")
print("  3. 모의투자 환경으로 우선 테스트")
print("  4. 또는 한투 앱에서 수동 거래")
