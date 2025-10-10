#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
잔고 조회에서 현재가 가져오기 (now_pric2 필드)
"""

import yaml
import requests
import json
import os

yaml_path = os.path.join(os.path.dirname(__file__), 'kis_devlp.yaml')
with open(yaml_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

print("="*80)
print("잔고 조회 API에서 현재가 가져오기")
print("="*80)

# 토큰 로드
try:
    with open('kis_token.json', 'r') as f:
        token_data = json.load(f)
        access_token = token_data['access_token']
        print(f"토큰 로드 성공\n")
except:
    print("토큰 파일 없음")
    exit(1)

# 계좌번호
acct_parts = config['my_acct'].split('-')
cano = acct_parts[0]
acnt_prdt_cd = acct_parts[1] if len(acct_parts) > 1 else "01"

# 잔고 조회
balance_url = "https://openapi.koreainvestment.com:9443/uapi/overseas-stock/v1/trading/inquire-balance"

balance_headers = {
    "Content-Type": "application/json; charset=utf-8",
    "authorization": f"Bearer {access_token}",
    "appkey": config['my_app'],
    "appsecret": config['my_sec'],
    "tr_id": "TTTS3012R",
    "custtype": "P",
    "User-Agent": config['my_agent']
}

balance_params = {
    "CANO": cano,
    "ACNT_PRDT_CD": acnt_prdt_cd,
    "OVRS_EXCG_CD": "NASD",
    "TR_CRCY_CD": "USD",
    "CTX_AREA_FK200": "",
    "CTX_AREA_NK200": ""
}

response = requests.get(balance_url, headers=balance_headers, params=balance_params, timeout=10)

if response.status_code == 200:
    result = response.json()

    if result.get('rt_cd') == '0':
        output1 = result.get('output1', [])

        print(f"[보유종목 현재가 비교]")
        print(f"{'='*80}\n")

        # 실시간 현재가 조회 API 엔드포인트
        price_url = "https://openapi.koreainvestment.com:9443/uapi/overseas-price/v1/quotations/price"
        price_headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {access_token}",
            "appkey": config['my_app'],
            "appsecret": config['my_sec'],
            "tr_id": "HHDFS00000300",
            "custtype": "P",
            "User-Agent": config['my_agent']
        }

        for stock in output1:
            symbol = stock.get('ovrs_pdno', '')
            qty = float(stock.get('ovrs_cblc_qty', '0'))

            if qty > 0:
                balance_price = stock.get('now_pric2', '')  # 잔고 조회의 현재가 (야간시세)
                avg_price = stock.get('pchs_avg_pric', '')
                exchange_cd = stock.get('ovrs_excg_cd', 'NASD')

                # 거래소 코드 변환 (NASD -> NAS)
                excd_map = {
                    'NASD': 'NAS',
                    'NYSE': 'NYS',
                    'AMEX': 'AMS',
                    'SEHK': 'HKS',
                    'SHAA': 'SHS',
                    'SZAA': 'SZS',
                    'TKSE': 'TSE',
                    'HASE': 'HNX',
                    'VNSE': 'HSX'
                }
                excd = excd_map.get(exchange_cd, 'NAS')

                print(f"{symbol}:")
                print(f"  [잔고 API] now_pric2 (야간시세): {balance_price}")

                # 실시간 현재가 조회
                price_params = {
                    "AUTH": "",
                    "EXCD": excd,
                    "SYMB": symbol
                }

                try:
                    price_response = requests.get(price_url, headers=price_headers, params=price_params, timeout=10)
                    if price_response.status_code == 200:
                        price_result = price_response.json()
                        if price_result.get('rt_cd') == '0':
                            realtime_price = price_result.get('output', {}).get('last', '')
                            print(f"  [실시간 API] last (실시간 시세): {realtime_price}")

                            # 가격 비교
                            if balance_price and realtime_price:
                                balance_float = float(balance_price)
                                realtime_float = float(realtime_price)
                                diff = realtime_float - balance_float
                                diff_pct = (diff / balance_float) * 100 if balance_float > 0 else 0

                                print(f"\n  => 야간시세: ${balance_float:.2f}")
                                print(f"  => 실시간시세: ${realtime_float:.2f}")
                                print(f"  => 차이: ${diff:+.2f} ({diff_pct:+.2f}%)")

                                if avg_price and avg_price.strip():
                                    avg_float = float(avg_price)
                                    print(f"  => 평균단가: ${avg_float:.2f}")
                                    pnl = ((realtime_float - avg_float) / avg_float) * 100
                                    print(f"  => 실시간 손익률: {pnl:+.2f}%")
                        else:
                            print(f"  [ERROR] 실시간 시세 조회 실패: {price_result.get('msg1')}")
                    else:
                        print(f"  [ERROR] 실시간 시세 HTTP 오류: {price_response.status_code}")
                except Exception as e:
                    print(f"  [ERROR] 실시간 시세 조회 오류: {e}")

                print()

    else:
        print(f"조회 실패: {result.get('msg1')}")
else:
    print(f"HTTP 오류: {response.status_code}")

print(f"{'='*80}")
