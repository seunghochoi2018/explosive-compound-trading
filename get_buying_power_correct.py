#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
해외주식 매수가능금액 조회 (올바른 방식)

[매우 중요] 한국투자 Open API 챗봇 답변 요약:
===================================================================
Q: USD 현금 잔고는 API로 조회되지 않나요?

A: 결론부터 말씀드리면
"USD 현금 잔고"는 일부 제한된 형태로만 API를 통해 조회됩니다.
즉, 일반적인 의미의 '외화 예수금(미체결 자금 포함)'은 현재 OpenAPI에서는
별도 API로 직접 조회되지 않으며, 간접 정보 또는 주문가능금액을 통해
추정하는 방식만 지원됩니다.

 관련 근거:
1. 해외주식 잔고 조회 API
   /uapi/overseas-stock/v1/trading/inquire-balance
   → 보유 종목별 수량 및 평가금액(USD 기준)을 반환
   → USD 예수금(잔여 현금)은 반환하지 않음

2. 매수가능금액으로 간접 확인
   매수 가능 금액(USD 기준)  가능
   /inquire-psbl-order API로 확인
   간접 잔액 파악 가능 여부 ⭕ 가능
   잔고 - 미체결 기반 추정 가능

즉, USD 현금 잔고는:
- 직접 조회:  불가능
- 매수가능금액으로 간접 확인:  가능
===================================================================
"""

import yaml
import json
import requests
import os

# 설정 로드
yaml_path = os.path.join(os.path.dirname(__file__), 'kis_devlp.yaml')
with open(yaml_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 토큰 로드
with open('kis_token.json', 'r') as f:
    token_data = json.load(f)
    access_token = token_data['access_token']

# 계좌번호
acct_parts = config['my_acct'].split('-')
cano = acct_parts[0]
acnt_prdt_cd = acct_parts[1] if len(acct_parts) > 1 else "01"

print("="*80)
print("해외주식 매수가능금액 조회 (올바른 방식)")
print("="*80)
print(f"계좌: {cano}-{acnt_prdt_cd}\n")

# API 엔드포인트
base_url = "https://openapi.koreainvestment.com:9443"
url = f"{base_url}/uapi/overseas-stock/v1/trading/inquire-psamount"

# TR_ID 목록 (모의/실전)
tr_ids = [
    ("JTTT3007R", "실전투자"),
    ("TTTS3007R", "모의투자"),
    ("VTTT3007R", "모의투자(V)")
]

# 거래소 코드 목록
exchange_codes = ["NASD", "NYSE", "AMEX", "NAS", "NYS", "AMS"]

# 테스트할 종목
test_symbol = "SOXL"
test_price = "40.0"

success_found = False

for tr_id, acc_type in tr_ids:
    if success_found:
        break

    print(f"\n{'='*80}")
    print(f"[{acc_type}] TR_ID: {tr_id}")
    print(f"{'='*80}")

    for excd in exchange_codes:
        if success_found:
            break

        print(f"\n  거래소: {excd}, 종목: {test_symbol}")

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {access_token}",
            "appkey": config['my_app'],
            "appsecret": config['my_sec'],
            "tr_id": tr_id,
            "custtype": "P",
            "User-Agent": config.get('my_agent', 'Mozilla/5.0')
        }

        # 파라미터 (필수 항목만)
        params = {
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "OVRS_EXCG_CD": excd,
            "OVRS_ORD_UNPR": test_price,
            "ITEM_CD": test_symbol
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                result = response.json()

                if result.get('rt_cd') == '0':
                    output = result.get('output', {})

                    # 주요 필드
                    ord_psbl_cash = output.get('ord_psbl_cash', '0')
                    ord_psbl_frcr_amt = output.get('ord_psbl_frcr_amt', '0')
                    max_ord_psbl_qty = output.get('max_ord_psbl_qty', '0')

                    print(f"    [SUCCESS] 매수가능금액 조회 성공!")
                    print(f"    주문가능현금: {ord_psbl_cash}")
                    print(f"    주문가능외화금액: {ord_psbl_frcr_amt}")
                    print(f"    최대주문가능수량: {max_ord_psbl_qty}")

                    # 실제 사용 가능한 USD 확인
                    try:
                        cash_val = float(ord_psbl_cash.replace(',', ''))
                        frcr_val = float(ord_psbl_frcr_amt.replace(',', ''))

                        if cash_val > 0 or frcr_val > 0:
                            print(f"\n    *** USD 매수가능금액 발견! ***")
                            print(f"    주문가능현금: ${cash_val:,.2f}")
                            print(f"    주문가능외화: ${frcr_val:,.2f}")
                            success_found = True

                            # 전체 output 출력
                            print(f"\n    [전체 output]")
                            for key, value in output.items():
                                if value and str(value).strip() and value != '0':
                                    print(f"      {key}: {value}")
                    except Exception as e:
                        print(f"    변환 오류: {e}")

                else:
                    print(f"    [FAIL] {result.get('msg1', '')}")

            else:
                print(f"    [HTTP ERROR] {response.status_code}")

        except Exception as e:
            print(f"    [EXCEPTION] {e}")

if not success_found:
    print("\n" + "="*80)
    print("[결론] 매수가능금액 조회 실패")
    print("="*80)
    print("가능한 원인:")
    print("1. 계좌에 USD 잔고가 없음")
    print("2. 해외주식 거래 미신청")
    print("3. 거래 가능 시간이 아님")
    print("4. API 파라미터 오류")
else:
    print("\n" + "="*80)
    print("[결론] 매수가능금액 조회 성공!")
    print("="*80)
    print("이 API를 사용하여 USD 현금 잔고를 간접적으로 확인할 수 있습니다.")

print()
