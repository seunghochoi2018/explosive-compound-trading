#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS API 주문 내역 조회
"""

import yaml
import json
import requests
from datetime import datetime, timedelta

# 설정 로드
with open('kis_devlp.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 토큰 로드
with open('kis_token.json', 'r') as f:
    token_data = json.load(f)
    access_token = token_data['access_token']

# 계좌 정보
acct_parts = config['my_acct'].split('-')
cano = acct_parts[0]
acnt_prdt_cd = acct_parts[1] if len(acct_parts) > 1 else "01"

base_url = "https://openapi.koreainvestment.com:9443"

def get_order_history(days=7):
    """
    해외주식 주문내역 조회

    TR_ID: TTTS3035R (해외주식 주문체결내역)
    """
    print(f"\n{'='*80}")
    print(f"해외주식 주문 내역 조회 (최근 {days}일)")
    print(f"{'='*80}\n")

    # 날짜 범위
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    url = f"{base_url}/uapi/overseas-stock/v1/trading/inquire-nccs"

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {access_token}",
        "appkey": config['my_app'],
        "appsecret": config['my_sec'],
        "tr_id": "TTTS3035R",
        "custtype": "P"
    }

    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "PDNO": "%",  # 전체 종목
        "ORD_STRT_DT": start_date.strftime('%Y%m%d'),
        "ORD_END_DT": end_date.strftime('%Y%m%d'),
        "SLL_BUY_DVSN": "00",  # 00:전체, 01:매도, 02:매수
        "CCLD_NCCS_DVSN": "00",  # 00:전체, 01:체결, 02:미체결
        "OVRS_EXCG_CD": "NASD",  # 거래소 코드
        "SORT_SQN": "DS",  # DS:내림차순
        "ORD_DT": "",
        "ORD_GNO_BRNO": "",
        "ODNO": "",
        "CTX_AREA_NK200": "",
        "CTX_AREA_FK200": ""
    }

    try:
        print(f"[조회 기간] {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
        print(f"[API 호출] TR_ID: TTTS3035R")
        print(f"[계좌] {cano}-{acnt_prdt_cd}\n")

        response = requests.get(url, headers=headers, params=params, timeout=10)

        print(f"[응답 코드] {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            rt_cd = result.get('rt_cd', '')
            msg = result.get('msg1', '')

            print(f"[rt_cd] {rt_cd}")
            print(f"[msg] {msg}\n")

            if rt_cd == '0':
                output = result.get('output', [])

                if not output:
                    print("[INFO] 주문 내역이 없습니다.")
                    return []

                print(f"\n[총 {len(output)}건의 주문 내역]\n")
                print(f"{'='*100}")

                for idx, order in enumerate(output, 1):
                    ord_dt = order.get('ord_dt', '')  # 주문일자
                    ord_tmd = order.get('ord_tmd', '')  # 주문시각
                    pdno = order.get('pdno', '')  # 종목코드
                    prdt_name = order.get('prdt_name', '')  # 종목명
                    sll_buy_dvsn_cd = order.get('sll_buy_dvsn_cd', '')  # 매도매수구분
                    ord_qty = order.get('ord_qty', '0')  # 주문수량
                    ord_unpr = order.get('ord_unpr', '0')  # 주문단가
                    ccld_qty = order.get('ccld_qty', '0')  # 체결수량
                    ccld_unpr = order.get('ft_ccld_unpr', '0')  # 체결단가
                    ccld_amt = order.get('ft_ccld_amt3', '0')  # 체결금액
                    ord_dvsn_name = order.get('ord_dvsn_name', '')  # 주문구분명
                    odno = order.get('odno', '')  # 주문번호

                    # 매수/매도 표시
                    side = "[매수]" if sll_buy_dvsn_cd == '02' else "[매도]"

                    # 체결 여부
                    is_filled = int(ccld_qty) > 0
                    status = "[체결]" if is_filled else "[미체결]"

                    print(f"\n[{idx}] {status} {side} {prdt_name} ({pdno})")
                    print(f"  일시: {ord_dt[:4]}-{ord_dt[4:6]}-{ord_dt[6:]} {ord_tmd[:2]}:{ord_tmd[2:4]}:{ord_tmd[4:]}")
                    print(f"  주문: {ord_qty}주 @ ${ord_unpr}")

                    if is_filled:
                        print(f"  체결: {ccld_qty}주 @ ${ccld_unpr} (총 ${ccld_amt})")

                    print(f"  주문번호: {odno}")
                    print(f"  구분: {ord_dvsn_name}")

                print(f"\n{'='*100}\n")
                return output
            else:
                print(f"[ERROR] 오류: {msg}")
                return []
        else:
            print(f"[ERROR] HTTP 오류: {response.status_code}")
            print(f"응답: {response.text[:500]}")
            return []

    except Exception as e:
        print(f"[ERROR] 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return []

def get_execution_history(days=7):
    """
    해외주식 체결내역 조회 (체결된 것만)

    TR_ID: TTTS3035R
    """
    print(f"\n{'='*80}")
    print(f"해외주식 체결 내역 조회 (최근 {days}일)")
    print(f"{'='*80}\n")

    # 날짜 범위
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    url = f"{base_url}/uapi/overseas-stock/v1/trading/inquire-nccs"

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {access_token}",
        "appkey": config['my_app'],
        "appsecret": config['my_sec'],
        "tr_id": "TTTS3035R",
        "custtype": "P"
    }

    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "PDNO": "%",
        "ORD_STRT_DT": start_date.strftime('%Y%m%d'),
        "ORD_END_DT": end_date.strftime('%Y%m%d'),
        "SLL_BUY_DVSN": "00",
        "CCLD_NCCS_DVSN": "01",  # 01:체결만
        "OVRS_EXCG_CD": "NASD",
        "SORT_SQN": "DS",
        "ORD_DT": "",
        "ORD_GNO_BRNO": "",
        "ODNO": "",
        "CTX_AREA_NK200": "",
        "CTX_AREA_FK200": ""
    }

    try:
        print(f"[조회 기간] {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
        print(f"[조건] 체결된 주문만")

        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            result = response.json()
            rt_cd = result.get('rt_cd', '')

            if rt_cd == '0':
                output = result.get('output', [])

                if not output:
                    print("\n[INFO] 체결 내역이 없습니다.")
                    return []

                print(f"\n[총 {len(output)}건의 체결 내역]\n")

                total_buy = 0
                total_sell = 0

                for order in output:
                    sll_buy = order.get('sll_buy_dvsn_cd', '')
                    ccld_amt = float(order.get('ft_ccld_amt3', '0'))

                    if sll_buy == '02':  # 매수
                        total_buy += ccld_amt
                    else:  # 매도
                        total_sell += ccld_amt

                print(f"[총 매수] ${total_buy:,.2f}")
                print(f"[총 매도] ${total_sell:,.2f}")
                print(f"[순액] ${total_sell - total_buy:,.2f}\n")

                return output

    except Exception as e:
        print(f"[ERROR] 예외 발생: {e}")
        return []

if __name__ == "__main__":
    # 1. 전체 주문 내역 (체결 + 미체결)
    orders = get_order_history(days=30)  # 최근 30일

    # 2. 체결 내역만
    # executions = get_execution_history(days=30)
