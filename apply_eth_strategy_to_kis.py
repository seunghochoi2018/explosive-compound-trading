#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETH 검증된 복리 폭발 전략을 KIS SOXL에 적용
- 익절 +2.0%, 손절 -0.3%
- 승률 50%+, 복리 극대화
"""

import requests
import json
from datetime import datetime, timedelta

# FMP API
FMP_API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"
FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"

def get_soxl_minute_data():
    """SOXL 1분봉 데이터 가져오기"""
    print("\n[데이터 수집] SOXL 1분봉 (최근 5일)")

    url = f"{FMP_BASE_URL}/historical-chart/1min/SOXL"
    params = {"apikey": FMP_API_KEY}

    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            print(f"  [OK] {len(data)}개 데이터 수집")
            return data
        else:
            print(f"  [ERROR] 오류: {response.status_code}")
            return []
    except Exception as e:
        print(f"  [ERROR] 예외: {e}")
        return []

def simulate_eth_strategy(data):
    """
    ETH 최고 전략 적용:
    - 익절: +2.0%
    - 손절: -0.3%
    - 보유 시간: 10-60분
    """
    print("\n[백테스팅] ETH 복리 폭발 전략 시뮬레이션")

    # 시간 순 정렬
    data = sorted(data, key=lambda x: x['date'])

    trades = []
    position = 'LONG'  # SOXL은 롱만
    entry_price = data[0]['close']
    entry_time = data[0]['date']
    entry_idx = 0

    for i in range(1, len(data)):
        current_price = data[i]['close']
        current_time = data[i]['date']

        # PNL 계산
        pnl_pct = (current_price - entry_price) / entry_price * 100

        # 보유 시간 (분)
        try:
            t1 = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
            t2 = datetime.fromisoformat(current_time.replace('Z', '+00:00'))
            holding_min = (t2 - t1).total_seconds() / 60
        except:
            holding_min = i - entry_idx

        # 청산 조건
        should_exit = False
        exit_reason = ""

        # 1. 손절 -0.3%
        if pnl_pct <= -0.3:
            should_exit = True
            exit_reason = "STOP_LOSS"

        # 2. 익절 +2.0%
        elif pnl_pct >= 2.0:
            should_exit = True
            exit_reason = "TAKE_PROFIT"

        # 3. 시간 초과 (60분)
        elif holding_min >= 60:
            should_exit = True
            exit_reason = "TIME_LIMIT"

        # 청산
        if should_exit:
            trades.append({
                'symbol': 'SOXL',
                'action': 'SELL',
                'entry_price': entry_price,
                'exit_price': current_price,
                'entry_time': entry_time,
                'exit_time': current_time,
                'pnl_pct': pnl_pct,
                'holding_min': holding_min,
                'result': 'WIN' if pnl_pct > 0 else 'LOSS',
                'reason': exit_reason
            })

            # 재진입
            entry_price = current_price
            entry_time = current_time
            entry_idx = i

            trades.append({
                'symbol': 'SOXL',
                'action': 'BUY',
                'price': entry_price,
                'time': entry_time,
                'signal': 'BULL'
            })

    print(f"  [OK] {len(trades)}개 거래 시뮬레이션 완료")
    return trades

def analyze_results(trades):
    """결과 분석"""
    print("\n" + "="*80)
    print("[RESULT] 백테스팅 결과 (ETH 전략 적용)")
    print("="*80)

    completed = [t for t in trades if t.get('action') == 'SELL']

    if not completed:
        print("  [ERROR] 완료된 거래 없음")
        return

    wins = [t for t in completed if t['result'] == 'WIN']
    losses = [t for t in completed if t['result'] == 'LOSS']

    win_rate = len(wins) / len(completed) * 100
    avg_win = sum(t['pnl_pct'] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t['pnl_pct'] for t in losses) / len(losses) if losses else 0
    avg_pnl = sum(t['pnl_pct'] for t in completed) / len(completed)

    print(f"\n총 거래: {len(completed)}건")
    print(f"승률: {win_rate:.1f}%")
    print(f"평균 수익: +{avg_win:.2f}%")
    print(f"평균 손실: {avg_loss:.2f}%")
    print(f"평균 PNL: {avg_pnl:+.3f}%")

    # 손익비
    if avg_loss != 0:
        profit_loss_ratio = abs(avg_win / avg_loss)
        print(f"손익비: {profit_loss_ratio:.2f}:1")

    # 복리 시뮬레이션
    balance = 1000.0
    for t in completed:
        balance = balance * (1 + t['pnl_pct'] / 100)

    compound_rate = (balance / 1000.0 - 1) * 100
    print(f"\n복리 효과: {len(completed)}회 거래 시 {compound_rate:+.1f}%")

    # 일일 예상
    if completed:
        # 평균 보유 시간
        avg_holding = sum(t.get('holding_min', 30) for t in completed) / len(completed)
        trades_per_day = (24 * 60) / avg_holding if avg_holding > 0 else 10

        daily_pnl = avg_pnl * trades_per_day
        print(f"평균 보유: {avg_holding:.1f}분")
        print(f"일일 예상 거래: {trades_per_day:.1f}회")
        print(f"일일 예상 수익: {daily_pnl:+.2f}%")

    # 청산 이유 통계
    print("\n청산 이유:")
    reasons = {}
    for t in completed:
        reason = t.get('reason', 'UNKNOWN')
        reasons[reason] = reasons.get(reason, 0) + 1

    for reason, count in reasons.items():
        print(f"  {reason}: {count}건 ({count/len(completed)*100:.1f}%)")

    print("\n" + "="*80)

    if win_rate >= 50:
        print("[***] 승률 50% 이상! 이 전략을 KIS에 적용하세요!")
    else:
        print("[WARNING] 승률 50% 미만. SOXL은 3배 레버리지라 변동성이 너무 큽니다.")
        print("   -> 손절을 -0.5%로 완화하거나")
        print("   -> 익절을 +3.0%로 상향 조정 필요")

    print("="*80)

def main():
    print("="*80)
    print("ETH 전략을 KIS SOXL에 적용")
    print("="*80)

    # 1. 데이터 수집
    data = get_soxl_minute_data()

    if not data:
        print("\n[ERROR] 데이터 수집 실패")
        return

    # 2. 시뮬레이션
    trades = simulate_eth_strategy(data)

    # 3. 분석
    analyze_results(trades)

if __name__ == "__main__":
    main()
