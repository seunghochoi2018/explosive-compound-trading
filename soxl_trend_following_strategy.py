#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SOXL/SOXS 추세 추종 전략 (ETH 스타일)

ETH 봇이 성공한 이유:
- 추세를 정확히 판단
- 상승 → LONG, 하락 → SHORT
- 빠른 전환 (0-60분)

SOXL/SOXS도 동일 전략:
- 상승 추세 → SOXL 매수
- 하락 추세 → SOXS 매수 (= SOXL 숏)
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict
import numpy as np

# FMP API
FMP_API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"
FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"

TAKER_FEE = 0.055 / 100
SLIPPAGE = 0.05 / 100
TOTAL_FEE = TAKER_FEE + SLIPPAGE

print("="*80)
print("SOXL/SOXS 추세 추종 전략 (ETH 복제)")
print("="*80)

def fetch_hourly_data(symbol: str) -> List[Dict]:
    """1시간봉 데이터"""
    print(f"\n[데이터] {symbol} 1시간봉...")

    url = f"{FMP_BASE_URL}/historical-chart/1hour/{symbol}"
    params = {"apikey": FMP_API_KEY}

    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            data = sorted(data, key=lambda x: x['date'])
            print(f"  [OK] {len(data)}개 ({data[0]['date'][:10]} ~ {data[-1]['date'][:10]})")
            return data
        else:
            return []
    except:
        return []

def calculate_trend(prices: List[float], short_period: int = 5, long_period: int = 20) -> str:
    """
    추세 판단 (ETH 봇 스타일)

    단기 MA > 장기 MA → 상승
    단기 MA < 장기 MA → 하락
    """
    if len(prices) < long_period:
        return 'NEUTRAL'

    recent_prices = prices[-long_period:]

    ma_short = sum(recent_prices[-short_period:]) / short_period
    ma_long = sum(recent_prices) / long_period

    if ma_short > ma_long * 1.01:  # 1% 이상 위
        return 'UP'
    elif ma_short < ma_long * 0.99:  # 1% 이상 아래
        return 'DOWN'
    else:
        return 'NEUTRAL'

def test_trend_strategy(soxl_data: List[Dict], soxs_data: List[Dict],
                       holding_candles: int = 1) -> Dict:
    """
    추세 추종 전략 백테스트

    상승 추세 → SOXL 보유
    하락 추세 → SOXS 보유
    횡보 → 포지션 없음

    보유 시간: ETH에서 발견한 최적값 (1~12캔들)
    """
    print(f"\n[백테스트] 보유시간 {holding_candles}캔들...")

    balance = 10000.0
    trades = []

    current_position = None  # 'SOXL' or 'SOXS'
    entry_price = 0
    entry_idx = 0
    entry_symbol = ''

    # 가격 히스토리
    soxl_prices = []

    for i in range(len(soxl_data)):
        soxl_price = soxl_data[i]['close']
        soxs_price = soxs_data[i]['close']

        soxl_prices.append(soxl_price)

        # 추세 판단 (SOXL 기준)
        if len(soxl_prices) < 20:
            continue

        trend = calculate_trend(soxl_prices)

        # 목표 포지션
        if trend == 'UP':
            target_symbol = 'SOXL'
            target_price = soxl_price
        elif trend == 'DOWN':
            target_symbol = 'SOXS'
            target_price = soxs_price
        else:
            target_symbol = None
            target_price = 0

        # 포지션 전환
        if current_position != target_symbol:
            # 기존 포지션 청산
            if current_position:
                exit_price = soxl_price if current_position == 'SOXL' else soxs_price
                pnl_pct = (exit_price - entry_price) / entry_price * 100

                # 수수료 적용
                exit_cost = balance * TOTAL_FEE
                balance = balance - exit_cost

                actual_balance = balance * (1 + pnl_pct / 100)

                trades.append({
                    'symbol': current_position,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct,
                    'balance': actual_balance,
                    'candles_held': i - entry_idx,
                    'date': soxl_data[i]['date']
                })

                balance = actual_balance
                current_position = None

            # 새 포지션 진입
            if target_symbol:
                current_position = target_symbol
                entry_price = target_price
                entry_idx = i
                entry_symbol = target_symbol

                # 수수료
                entry_cost = balance * TOTAL_FEE
                balance = balance - entry_cost

        # 보유시간 초과 시 청산 (손익 관계없이)
        elif current_position:
            candles_held = i - entry_idx

            if candles_held >= holding_candles:
                exit_price = soxl_price if current_position == 'SOXL' else soxs_price
                pnl_pct = (exit_price - entry_price) / entry_price * 100

                exit_cost = balance * TOTAL_FEE
                balance = balance - exit_cost

                actual_balance = balance * (1 + pnl_pct / 100)

                trades.append({
                    'symbol': current_position,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct,
                    'balance': actual_balance,
                    'candles_held': candles_held,
                    'date': soxl_data[i]['date'],
                    'reason': 'TIME_LIMIT'
                })

                balance = actual_balance
                current_position = None

    # 결과
    if trades:
        wins = [t for t in trades if t['pnl_pct'] > 0]
        winrate = len(wins) / len(trades) * 100
        avg_pnl = sum(t['pnl_pct'] for t in trades) / len(trades)

        compound_return = (balance - 10000) / 10000 * 100

        # 총 시간
        total_hours = sum(t['candles_held'] for t in trades)
        total_days = total_hours / 24

        # 연환산
        if total_days > 0 and balance > 0:
            daily_return = (balance / 10000) ** (1 / total_days) - 1
            annual_return = (1 + daily_return) ** 365 - 1
        else:
            annual_return = 0

        return {
            'holding_candles': holding_candles,
            'trades': len(trades),
            'winrate': winrate,
            'avg_pnl': avg_pnl,
            'final_balance': balance,
            'compound_return': compound_return,
            'annual_return': annual_return * 100,
            'total_days': total_days,
            'trades_detail': trades
        }
    else:
        return None

def main():
    # 데이터 수집
    soxl_data = fetch_hourly_data('SOXL')
    soxs_data = fetch_hourly_data('SOXS')

    if not soxl_data or not soxs_data:
        print("\n[ERROR] 데이터 수집 실패")
        return

    print(f"\n총 {len(soxl_data)}개 캔들")

    # ETH에서 발견한 최적 보유시간 테스트
    # ETH: 0-60분 = 1~12 캔들 (5분봉 기준)
    # 1시간봉이므로: 1~12 캔들 = 1~12 시간

    holding_periods = [1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 24]

    results = []

    for holding in holding_periods:
        result = test_trend_strategy(soxl_data, soxs_data, holding)

        if result:
            results.append(result)

    # 정렬
    results.sort(key=lambda x: x['annual_return'], reverse=True)

    # 출력
    print("\n" + "="*80)
    print("[결과] 추세 추종 전략")
    print("="*80)

    print(f"\n총 {len(results)}개 전략 테스트")

    if results:
        print("\n[TOP 10] 고수익 전략:")

        for i, r in enumerate(results[:10], 1):
            print(f"\n{i}. 보유시간: {r['holding_candles']}시간")
            print(f"   거래수: {r['trades']}건 ({r['total_days']:.0f}일)")
            print(f"   승률: {r['winrate']:.1f}%")
            print(f"   평균 PNL: {r['avg_pnl']:+.2f}%")
            print(f"   복리 효과: {r['compound_return']:+.1f}%")
            print(f"   연환산 수익: {r['annual_return']:+.1f}%")

            if r['annual_return'] >= 100:
                print(f"   *** 연 100% 달성! ***")

        # 최적 전략
        best = results[0]

        print("\n" + "="*80)
        print("[최적 전략]")
        print("="*80)
        print(f"보유시간: {best['holding_candles']}시간")
        print(f"거래수: {best['trades']}건")
        print(f"승률: {best['winrate']:.1f}%")
        print(f"연수익: {best['annual_return']:+.1f}%")

        if best['annual_return'] >= 100:
            print("\n*** 연 100% 달성! 실전 적용 가능! ***")
        else:
            print(f"\n목표 미달 (현재: {best['annual_return']:.1f}%, 목표: 100%)")

        print("="*80)

        # 저장
        with open('C:/Users/user/Documents/soxl_trend_strategy_results.json', 'w', encoding='utf-8') as f:
            json.dump({
                'top10': results[:10],
                'best': best
            }, f, indent=2, ensure_ascii=False)

        print("\n[OK] soxl_trend_strategy_results.json 저장")

    else:
        print("\n[ERROR] 유효한 결과 없음")

if __name__ == "__main__":
    main()
