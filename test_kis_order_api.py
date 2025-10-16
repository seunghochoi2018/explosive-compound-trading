#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KIS API 주문 테스트 - 왜 500 에러가 나는지 확인"""
import json
import yaml
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

print("="*80)
print("KIS API 주문 시스템 진단")
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

# 1. 토큰 유효성 확인
print("\n[1] 토큰 상태 확인")
issue_time = datetime.fromisoformat(token_data['issue_time'])
age = (datetime.now() - issue_time).total_seconds() / 3600
remaining = 24 - age
print(f"  발급 시간: {issue_time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"  경과 시간: {age:.1f}시간")
print(f"  남은 시간: {remaining:.1f}시간")
print(f"  상태: {'정상' if remaining > 0 else '만료됨'}")

# 2. 정규장 시간 확인
print("\n[2] 정규장 시간 확인")
now_et = datetime.now(ZoneInfo("America/New_York"))
hour = now_et.hour
minute = now_et.minute
total_minutes = hour * 60 + minute
is_regular = 570 <= total_minutes <= 960

print(f"  미국 시각(ET): {now_et.strftime('%H:%M:%S')}")
print(f"  정규장 시간: {'YES' if is_regular else 'NO'}")

# 3. 잔고 조회 테스트 (READ API)
print("\n[3] 잔고 조회 API 테스트 (토큰 확인)")
balance_url = f"{base_url}/uapi/overseas-stock/v1/trading/inquire-balance"
balance_headers = {
    "authorization": f"Bearer {access_token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": "TTTS3012R"
}
balance_params = {
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
    balance_response = requests.get(balance_url, headers=balance_headers, params=balance_params, timeout=10)
    print(f"  HTTP 상태: {balance_response.status_code}")
    if balance_response.status_code == 200:
        data = balance_response.json()
        print(f"  rt_cd: {data.get('rt_cd')}")
        print(f"  메시지: {data.get('msg1', 'OK')}")
        print(f"  결과: {'정상' if data.get('rt_cd') == '0' else '오류'}")
    else:
        print(f"  오류: HTTP {balance_response.status_code}")
except Exception as e:
    print(f"  예외: {e}")

# 4. SOXS 가격 조회 테스트
print("\n[4] SOXS 가격 조회 API 테스트")
price_url = f"{base_url}/uapi/overseas-price/v1/quotations/price"
price_headers = {
    "authorization": f"Bearer {access_token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": "HHDFS00000300",
    "custtype": "P"
}
price_params = {
    "FID_COND_MRKT_DIV_CODE": "N",
    "FID_INPUT_ISCD": "SOXS"
}

try:
    price_response = requests.get(price_url, headers=price_headers, params=price_params, timeout=10)
    print(f"  HTTP 상태: {price_response.status_code}")
    if price_response.status_code == 200:
        data = price_response.json()
        print(f"  rt_cd: {data.get('rt_cd')}")
        current_price = float(data.get('output', {}).get('stck_prpr', '0'))
        print(f"  SOXS 현재가: ${current_price:.2f}")
    else:
        print(f"  오류: HTTP {price_response.status_code}")
except Exception as e:
    print(f"  예외: {e}")

# 5. 주문 API 헤더/데이터 형식 확인
print("\n[5] 주문 API 요청 형식 검증")
print(f"  매도 TR_ID: JTTT1006U")
print(f"  계좌번호: {account_no}")
print(f"  CANO: {account_no.split('-')[0]}")
print(f"  ACNT_PRDT_CD: {account_no.split('-')[1]}")
print(f"  거래소: NASD (NASDAQ)")
print(f"  종목코드: A980680 (SOXS)")

# 6. 최근 주문 내역 확인
print("\n[6] 오늘 주문 내역 확인")
order_url = f"{base_url}/uapi/overseas-stock/v1/trading/inquire-ccnl"
order_headers = {
    "authorization": f"Bearer {access_token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": "TTTS3035R"
}
order_params = {
    "CANO": account_no.split('-')[0],
    "ACNT_PRDT_CD": account_no.split('-')[1],
    "PDNO": "",
    "ORD_STRT_DT": datetime.now().strftime("%Y%m%d"),
    "ORD_END_DT": datetime.now().strftime("%Y%m%d"),
    "SLL_BUY_DVSN": "",  # 전체
    "CCLD_NCCS_DVSN": "",
    "OVRS_EXCG_CD": "NASD",
    "SORT_SQN": "DS",
    "ORD_DT": "",
    "ORD_GNO_BRNO": "",
    "ODNO": "",
    "CTX_AREA_FK200": "",
    "CTX_AREA_NK200": ""
}

try:
    order_response = requests.get(order_url, headers=order_headers, params=order_params, timeout=10)
    print(f"  HTTP 상태: {order_response.status_code}")
    if order_response.status_code == 200:
        data = order_response.json()
        orders = data.get('output1', [])
        print(f"  오늘 주문: {len(orders)}건")

        # SOXS 주문만 필터
        soxs_orders = [o for o in orders if 'SOXS' in o.get('prdt_name', '').upper()]
        if soxs_orders:
            print(f"\n  [SOXS 주문 발견]")
            for order in soxs_orders[:3]:
                print(f"    주문번호: {order.get('odno', 'N/A')}")
                print(f"    수량: {order.get('ord_qty', 'N/A')}주")
                print(f"    상태: {order.get('ord_stat_name', 'N/A')}")
        else:
            print(f"  SOXS 주문 없음")
except Exception as e:
    print(f"  예외: {e}")

print("\n" + "="*80)
print("진단 완료")
print("="*80)
