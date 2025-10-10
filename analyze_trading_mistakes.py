#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
과거 거래 기록 분석 - 무엇이 잘못되었는지 파악
"""

import yaml
import json
import requests
from datetime import datetime, timedelta
from collections import defaultdict

# 설정 로드
with open('kis_devlp.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

with open('kis_token.json', 'r') as f:
    token_data = json.load(f)
    access_token = token_data['access_token']

acct_parts = config['my_acct'].split('-')
cano = acct_parts[0]
acnt_prdt_cd = acct_parts[1] if len(acct_parts) > 1 else "01"
base_url = "https://openapi.koreainvestment.com:9443"

# FMP API
FMP_API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"
FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"

def get_historical_price(symbol, date):
    """특정 날짜의 가격 조회"""
    try:
        url = f"{FMP_BASE_URL}/historical-price-full/{symbol}"
        params = {
            "apikey": FMP_API_KEY,
            "from": date,
            "to": date
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            hist = data.get('historical', [])
            if hist:
                return hist[0]
    except:
        pass
    return None

def get_order_history(days=30):
    """주문 내역 조회"""
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
        "CCLD_NCCS_DVSN": "00",
        "OVRS_EXCG_CD": "NASD",
        "SORT_SQN": "DS",
        "ORD_DT": "",
        "ORD_GNO_BRNO": "",
        "ODNO": "",
        "CTX_AREA_NK200": "",
        "CTX_AREA_FK200": ""
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('rt_cd') == '0':
                return result.get('output', [])
    except:
        pass
    return []

def analyze_trades():
    """거래 패턴 분석"""
    print("\n" + "="*80)
    print("거래 패턴 분석 - 무엇이 잘못되었는가?")
    print("="*80 + "\n")

    orders = get_order_history(days=30)

    if not orders:
        print("[INFO] 주문 내역이 없습니다.")
        return

    # 종목별로 그룹화
    by_symbol = defaultdict(list)
    for order in orders:
        symbol = order.get('prdt_name', '').split()[0] if order.get('prdt_name') else 'UNKNOWN'
        if 'SOXL' in symbol or 'SOXS' in symbol:
            symbol = 'SOXL' if 'SOXL' in symbol else 'SOXS'
        by_symbol[symbol].append(order)

    print(f"[총 주문] {len(orders)}건")
    print(f"[종목] {', '.join(by_symbol.keys())}\n")

    # 시간순 정렬
    sorted_orders = sorted(orders, key=lambda x: (x.get('ord_dt', ''), x.get('ord_tmd', '')))

    print("="*80)
    print("시간순 거래 흐름 분석")
    print("="*80 + "\n")

    trades = []
    for idx, order in enumerate(sorted_orders, 1):
        ord_dt = order.get('ord_dt', '')
        ord_tmd = order.get('ord_tmd', '')
        prdt_name = order.get('prdt_name', '')
        sll_buy = order.get('sll_buy_dvsn_cd', '')
        ord_qty = order.get('ord_qty', '0')
        ccld_qty = order.get('ccld_qty', '0')

        symbol = 'SOXL' if 'SOXL' in prdt_name else 'SOXS' if 'SOXS' in prdt_name else '기타'
        action = '매수' if sll_buy == '02' else '매도'
        status = '체결' if int(ccld_qty) > 0 else '미체결'

        # 날짜 파싱
        date_str = f"{ord_dt[:4]}-{ord_dt[4:6]}-{ord_dt[6:8]}"
        time_str = f"{ord_tmd[:2]}:{ord_tmd[2:4]}"

        print(f"[{idx}] {date_str} {time_str} | {status} | {action} {symbol} {ord_qty}주")

        trades.append({
            'date': date_str,
            'time': time_str,
            'symbol': symbol,
            'action': action,
            'status': status,
            'qty': ord_qty
        })

    # 패턴 분석
    print("\n" + "="*80)
    print("문제점 분석")
    print("="*80 + "\n")

    # 1. 미체결 주문 확인
    unfilled = [t for t in trades if t['status'] == '미체결']
    if unfilled:
        print(f"[문제 1] 미체결 주문 {len(unfilled)}건 발견")
        for t in unfilled:
            print(f"  - {t['date']} {t['time']}: {t['action']} {t['symbol']} {t['qty']}주")
        print("  [원인] 주문 가격이 시장가와 맞지 않거나, 유동성 부족")
        print("  [해결] 시장가 주문 사용 또는 주문 가격 조정\n")

    # 2. 짧은 시간 내 반복 주문
    print("[문제 2] 짧은 시간 내 반복 주문")
    for i in range(len(trades) - 1):
        t1 = trades[i]
        t2 = trades[i + 1]

        if t1['date'] == t2['date'] and t1['symbol'] == t2['symbol'] and t1['action'] == t2['action']:
            print(f"  - {t1['date']} {t1['time']}~{t2['time']}: {t1['symbol']} {t1['action']} 중복")

    print("  [원인] 시스템이 같은 신호를 여러 번 보냄")
    print("  [해결] 주문 중복 방지 로직 추가 (마지막 주문 시간 체크)\n")

    # 3. 빠른 포지션 전환
    print("[문제 3] 빠른 포지션 전환")
    position_changes = []
    current_pos = None

    for t in trades:
        if t['status'] == '체결':
            if t['action'] == '매수':
                if current_pos and current_pos != t['symbol']:
                    position_changes.append({
                        'date': t['date'],
                        'time': t['time'],
                        'from': current_pos,
                        'to': t['symbol']
                    })
                current_pos = t['symbol']
            elif t['action'] == '매도':
                current_pos = None

    for change in position_changes:
        print(f"  - {change['date']} {change['time']}: {change['from']} → {change['to']}")

    if len(position_changes) >= 2:
        print(f"  [원인] {len(position_changes)}번의 포지션 전환 (과도한 매매)")
        print("  [해결] 신뢰도 기준 상향 (40% → 60%), 최소 보유 시간 설정\n")

    # 4. 가격 변동과 비교
    print("[문제 4] 매매 타이밍 분석")
    print("  실제 가격 변동과 매매 시점을 비교 중...\n")

    for change in position_changes[:3]:  # 최근 3개만
        date = change['date']

        # 해당 날짜의 SOXL/SOXS 가격 조회
        soxl_data = get_historical_price('SOXL', date)
        soxs_data = get_historical_price('SOXS', date)

        if soxl_data and soxs_data:
            soxl_change = ((soxl_data['close'] - soxl_data['open']) / soxl_data['open']) * 100
            soxs_change = ((soxs_data['close'] - soxs_data['open']) / soxs_data['open']) * 100

            print(f"  [{date}] {change['from']} → {change['to']}")
            print(f"    SOXL: ${soxl_data['open']:.2f} → ${soxl_data['close']:.2f} ({soxl_change:+.2f}%)")
            print(f"    SOXS: ${soxs_data['open']:.2f} → ${soxs_data['close']:.2f} ({soxs_change:+.2f}%)")

            # 전환 판단
            if change['from'] == 'SOXL' and change['to'] == 'SOXS':
                if soxl_change > 0:
                    print(f"    [판단 오류] SOXL이 상승 중({soxl_change:+.2f}%)인데 SOXS로 전환")
                else:
                    print(f"    [판단 적절] SOXL 하락({soxl_change:+.2f}%) → SOXS 전환")

            elif change['from'] == 'SOXS' and change['to'] == 'SOXL':
                if soxs_change > 0:
                    print(f"    [판단 오류] SOXS가 상승 중({soxs_change:+.2f}%)인데 SOXL로 전환")
                else:
                    print(f"    [판단 적절] SOXS 하락({soxs_change:+.2f}%) → SOXL 전환")

            print()

    # 종합 권장 사항
    print("="*80)
    print("종합 권장 사항")
    print("="*80 + "\n")

    print("[1] 신뢰도 기준 상향")
    print("    현재: 40% → 권장: 60~70%")
    print("    이유: 노이즈 신호를 줄여 과도한 매매 방지\n")

    print("[2] 주문 중복 방지")
    print("    마지막 주문 후 최소 30분~1시간 대기\n")

    print("[3] 최소 보유 시간 설정")
    print("    포지션 진입 후 최소 1~2시간 보유\n")

    print("[4] 시장가 주문 사용")
    print("    미체결 방지를 위해 시장가 주문 권장\n")

    print("[5] 백테스팅 검증")
    print("    실제 거래 전에 과거 데이터로 전략 검증\n")

if __name__ == "__main__":
    analyze_trades()
