#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SOXS 자동 청산 스크립트 - 개장 시간 대기 후 자동 매도
"""
import time
import json
import yaml
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

def is_us_regular_hours() -> bool:
    """미국(ET) 정규장 여부"""
    now_et = datetime.now(ZoneInfo("America/New_York"))
    if now_et.weekday() >= 5:  # 주말
        return False
    total_minutes = now_et.hour * 60 + now_et.minute
    return 570 <= total_minutes <= 960  # 09:30~16:00

def sell_soxs():
    """SOXS 184주 매도"""
    # KIS 설정 로드
    with open('kis_devlp.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        app_key = config['my_app']
        app_secret = config['my_sec']
        account_no = config['my_acct']

    # 토큰 로드
    with open('kis_token.json', 'r', encoding='utf-8') as f:
        token_data = json.load(f)
        access_token = token_data['access_token']

    # 1. SOXS 현재가 조회
    print('[1] SOXS 현재가 조회...')
    price_url = 'https://openapi.koreainvestment.com:9443/uapi/overseas-price/v1/quotations/price'
    price_headers = {
        'authorization': f'Bearer {access_token}',
        'appkey': app_key,
        'appsecret': app_secret,
        'tr_id': 'HHDFS00000300',
        'custtype': 'P'
    }
    price_params = {
        'FID_COND_MRKT_DIV_CODE': 'N',
        'FID_INPUT_ISCD': 'SOXS'
    }

    price_response = requests.get(price_url, headers=price_headers, params=price_params, timeout=10)
    current_price = 0

    if price_response.status_code == 200:
        price_data = price_response.json()
        if price_data.get('rt_cd') == '0':
            current_price = float(price_data.get('output', {}).get('stck_prpr', '0'))
            print(f'[OK] SOXS 현재가: ${current_price:.2f}')

    if current_price <= 0:
        print('[ERROR] 가격 조회 실패')
        return False

    # 2. SOXS 매도 주문
    print(f'\n[2] SOXS 184주 매도 주문 @ ${current_price:.2f}...')
    order_url = 'https://openapi.koreainvestment.com:9443/uapi/overseas-stock/v1/trading/order'
    order_headers = {
        'authorization': f'Bearer {access_token}',
        'appkey': app_key,
        'appsecret': app_secret,
        'tr_id': 'JTTT1006U'  # 매도
    }

    order_data = {
        'CANO': account_no.split('-')[0],
        'ACNT_PRDT_CD': account_no.split('-')[1],
        'OVRS_EXCG_CD': 'NASD',
        'PDNO': 'A980680',  # SOXS
        'ORD_QTY': '184',
        'OVRS_ORD_UNPR': str(current_price),
        'ORD_SVR_DVSN_CD': '0'
    }

    order_response = requests.post(order_url, headers=order_headers, json=order_data, timeout=10)

    if order_response.status_code == 200:
        result = order_response.json()
        if result.get('rt_cd') == '0':
            print('\n[SUCCESS] SOXS 청산 주문 성공!')
            print(f'  주문번호: {result.get("output", {}).get("ODNO", "N/A")}')
            return True
        else:
            print(f'\n[ERROR] 주문 실패: {result.get("msg1")}')
            return False
    else:
        print(f'\n[ERROR] HTTP {order_response.status_code}')
        return False

def main():
    print("="*60)
    print("SOXS 자동 청산 스크립트")
    print("="*60)
    print("목표: SOXS 184주 매도")
    print("조건: 미국 정규장 개장 시")
    print("="*60)

    while True:
        now_et = datetime.now(ZoneInfo("America/New_York"))
        now_kr = datetime.now(ZoneInfo("Asia/Seoul"))

        print(f"\n[{now_kr.strftime('%H:%M:%S')}] 상태 체크...")
        print(f"  미국(ET): {now_et.strftime('%H:%M:%S')}")
        print(f"  한국(KST): {now_kr.strftime('%H:%M:%S')}")

        if is_us_regular_hours():
            print("\n[개장] 미국 정규장 개장! 청산 시도...")
            if sell_soxs():
                print("\n[완료] SOXS 청산 완료!")
                break
            else:
                print("\n[대기] 청산 실패, 5분 후 재시도...")
                time.sleep(300)
        else:
            # 개장까지 남은 시간 계산
            hour = now_et.hour
            minute = now_et.minute

            if hour < 9 or (hour == 9 and minute < 30):
                # 오늘 개장 전
                minutes_until = (9 * 60 + 30) - (hour * 60 + minute)
            else:
                # 내일 개장
                minutes_until = (24 - hour) * 60 - minute + (9 * 60 + 30)

            print(f"  장 마감 중... 개장까지 약 {minutes_until}분")
            print(f"  다음 체크: 10분 후")
            time.sleep(600)  # 10분 대기

if __name__ == "__main__":
    main()
