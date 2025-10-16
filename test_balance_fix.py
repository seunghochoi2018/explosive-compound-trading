#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""잔고 조회 수정 테스트"""
import json
import yaml
import requests

print("="*80)
print("잔고 조회 테스트 - 보유종목 포함")
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

# 잔고 조회
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

response = requests.get(url, headers=headers, params=params, timeout=10)

if response.status_code == 200:
    data = response.json()
    if data.get('rt_cd') == '0':
        output1 = data.get('output1', [])
        output2 = data.get('output2', {})

        print(f"\n[2] 보유종목 수: {len(output1)}개")

        # 보유종목 평가금액 합산
        holdings_value = 0.0
        for holding in output1:
            eval_amt = holding.get('ovrs_stck_evlu_amt', '0')
            try:
                holdings_value += float(str(eval_amt).replace(',', ''))
            except:
                pass

        print(f"[3] 보유종목 평가금액: ${holdings_value:.2f}")

        # 현금잔고
        cand = {
            'ovrs_ncash_blce_amt': output2.get('ovrs_ncash_blce_amt'),
            'ovrs_buy_psbl_amt': output2.get('ovrs_buy_psbl_amt'),
            'frcr_buy_amt_smtl1': output2.get('frcr_buy_amt_smtl1'),
        }

        cash_balance = 0.0
        raw_val = (
            cand['ovrs_ncash_blce_amt']
            or cand['ovrs_buy_psbl_amt']
            or cand['frcr_buy_amt_smtl1']
            or 0
        )
        try:
            cash_balance = float(str(raw_val).replace(',', ''))
        except:
            cash_balance = 0.0

        print(f"[4] 현금잔고: ${cash_balance:.2f}")

        # 총 잔고
        total_balance = cash_balance + holdings_value
        print(f"\n[5] 총 잔고 (현금 + 보유종목): ${total_balance:.2f}")

        print(f"\n{'='*80}")
        if total_balance > 0:
            print(f"[SUCCESS] 잔고 확인 완료!")
            print(f"{'='*80}")
            print(f"  현금: ${cash_balance:.2f}")
            print(f"  보유종목: ${holdings_value:.2f}")
            print(f"  합계: ${total_balance:.2f}")
            print(f"\n자동매매 가능: YES")
        else:
            print(f"[FAIL] 잔고가 0입니다")
    else:
        print(f"[FAIL] API 오류: {data.get('msg1')}")
else:
    print(f"[FAIL] HTTP {response.status_code}")

print(f"\n{'='*80}")
