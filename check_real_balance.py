#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실제 계좌 잔고 상세 확인
"""

import json
import requests
import time

# 기존 토큰 사용
with open('kis_token.json', 'r') as f:
    token_data = json.load(f)

TOKEN = token_data['access_token']
APP_KEY = "PSi3RlRt3DWtPPKTdYNALowIoeUBgM5mMLYO"
APP_SECRET = "Q7LxW5oIlCeg+doJCkmPDgXw7uy8bjC7ACRQR1GrAzgCF3zH7LziMix/QJgweS+IRU+uM/3GPELXVeOGocKQnHZ+RPeH4bqR1CgFOs9tHmRtGmxCiwt3+1yp7yctt+bBc85eDrIsrX9KfOkrLY+wVuE1tthKYSDyiF2YKrOp/e1PsSD0mdI="
BASE_URL = "https://openapi.koreainvestment.com:9443"
CANO = "43113014"

print("=" * 60)
print("실제 계좌 잔고 상세 확인")
print("=" * 60)

# 해외주식 잔고 조회
url = f"{BASE_URL}/uapi/overseas-stock/v1/trading/inquire-balance"
headers = {
    "Content-Type": "application/json; charset=utf-8",
    "authorization": f"Bearer {TOKEN}",
    "appkey": APP_KEY,
    "appsecret": APP_SECRET,
    "tr_id": "TTTS3012R",
    "custtype": "P"
}

# 여러 계좌 상품코드 테스트
product_codes = ["01", "02", "03", "10", "11", "20", "21", "31", "41", "51"]

for code in product_codes:
    print(f"\n[계좌 {CANO}-{code}]")

    params = {
        "CANO": CANO,
        "ACNT_PRDT_CD": code,
        "OVRS_EXCG_CD": "NASD",
        "TR_CRCY_CD": "USD",
        "CTX_AREA_FK200": "",
        "CTX_AREA_NK200": ""
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        result = response.json()
        if result.get("rt_cd") == "0":
            print(f"[OK] 해외주식 거래 가능!")

            # 계좌 잔고 정보
            output2 = result.get("output2", {})
            if output2:
                cash = output2.get("frcr_buy_amt_smtl1", "0")
                total_amount = output2.get("tot_asst_amt", "0")

                try:
                    cash_val = float(cash)
                    total_val = float(total_amount)
                    print(f"  매수가능금액: ${cash_val:,.2f}")
                    print(f"  총 자산: ${total_val:,.2f}")

                    if cash_val > 0 or total_val > 0:
                        print(f"  [MONEY] 이 계좌에 돈이 있습니다!")

                except Exception as e:
                    print(f"  매수가능금액: {cash}")
                    print(f"  총 자산: {total_amount}")

            # 보유종목 확인
            output1 = result.get("output1", [])
            if output1:
                print(f"  보유종목: {len(output1)}개")
                for item in output1[:5]:  # 상위 5개만 표시
                    symbol = item.get("ovrs_pdno", "")
                    qty = item.get("ovrs_cblc_qty", "0")
                    eval_amt = item.get("now_pric2", "0")
                    if symbol:
                        print(f"    - {symbol}: {qty}주 (현재가: ${eval_amt})")
        else:
            error_msg = result.get('msg1', '')
            if "해외주식" not in error_msg and "INPUT_FILED" not in error_msg:
                print(f"  [ERROR] 오류: {error_msg}")
            else:
                print(f"  [WARNING] 해외주식 거래 불가")
    else:
        print(f"  [ERROR] HTTP 오류: {response.status_code}")

    time.sleep(0.3)  # API 호출 간격

print("\n" + "=" * 60)
print("확인 완료!")