#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SOXL/SOXS 깊이 파기 (ETH 스타일 분석)

목표: ETH에서 발견한 복리 폭발 패턴을 SOXL/SOXS에 적용
- 1시간봉 데이터 수집 (최대한 많이)
- 모든 보유시간 조합 테스트
- 복리 효과 계산
- 연환산 수익률 도출
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict
from collections import defaultdict

# FMP API
FMP_API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"
FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"

TAKER_FEE = 0.055 / 100
SLIPPAGE = 0.05 / 100
TOTAL_FEE = TAKER_FEE + SLIPPAGE  # 0.105%

print("="*80)
print("SOXL/SOXS 깊이 파기 (복리 폭발 전략 찾기)")
print("="*80)

def fetch_hourly_data(symbol: str) -> List[Dict]:
    """1시간봉 데이터 수집 (최대한 많이)"""
    print(f"\n[데이터 수집] {symbol} 1시간봉...")

    url = f"{FMP_BASE_URL}/historical-chart/1hour/{symbol}"
    params = {"apikey": FMP_API_KEY}

    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            data = sorted(data, key=lambda x: x['date'])

            print(f"  [OK] {len(data)}개 캔들 수집")

            if data:
                # 기간 계산
                start = datetime.fromisoformat(data[0]['date'].replace('Z', ''))
                end = datetime.fromisoformat(data[-1]['date'].replace('Z', ''))
                days = (end - start).days

                print(f"  기간: {data[0]['date'][:10]} ~ {data[-1]['date'][:10]} ({days}일)")
                print(f"  시작가: ${data[0]['close']:.2f}")
                print(f"  종료가: ${data[-1]['close']:.2f}")
                print(f"  변화: {(data[-1]['close']-data[0]['close'])/data[0]['close']*100:+.1f}%")

            return data
        else:
            print(f"  [ERROR] HTTP {response.status_code}")
            return []
    except Exception as e:
        print(f"  [ERROR] {e}")
        return []

def test_all_holding_times(data: List[Dict], symbol: str) -> List[Dict]:
    """
    모든 보유 시간 조합 테스트

    ETH에서 발견:
    - 초단타 (0-10분): 복리 +95.9%
    - 단타 (10-30분): 복리 +180.7%
    - 중기 (30-60분): 복리 +191.8%

    1시간봉이므로 캔들 단위로 변환:
    - 초단타: 1-2 캔들
    - 단타: 3-5 캔들
    - 중기: 6-12 캔들
    - 중장기: 13-24 캔들
    """
    print(f"\n[백테스팅] {symbol}")

    holding_periods = [1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 24, 30, 40, 50]
    results = []

    for holding in holding_periods:
        balance = 10000.0
        trades = []

        position = False
        entry_price = 0
        entry_idx = 0
        position_size = 0

        for i in range(len(data)):
            current_price = data[i]['close']

            # 진입 (항상 롱)
            if not position:
                position = True
                entry_price = current_price
                entry_idx = i

                entry_cost = balance * TOTAL_FEE
                position_size = balance - entry_cost
                balance = 0

            # 청산 (보유 시간 도달)
            else:
                candles_held = i - entry_idx

                if candles_held >= holding:
                    pnl_pct = (current_price - entry_price) / entry_price * 100

                    position_value = position_size * (1 + pnl_pct / 100)
                    exit_cost = position_value * TOTAL_FEE
                    balance = position_value - exit_cost

                    trades.append({
                        'entry': entry_price,
                        'exit': current_price,
                        'pnl_pct': pnl_pct,
                        'candles': candles_held,
                        'date': data[i]['date']
                    })

                    position = False

        # 결과 계산
        if trades and len(trades) >= 10:  # 최소 10거래
            wins = [t for t in trades if t['pnl_pct'] > 0]
            winrate = len(wins) / len(trades) * 100
            avg_pnl = sum(t['pnl_pct'] for t in trades) / len(trades)

            # 복리 효과
            compound_return = (balance - 10000) / 10000 * 100

            # 총 시간 계산
            total_hours = sum(t['candles'] for t in trades)
            total_days = total_hours / 24

            # 연환산 수익
            if total_days > 0 and balance > 0:
                daily_return = (balance / 10000) ** (1 / total_days) - 1
                annual_return = (1 + daily_return) ** 365 - 1
            else:
                annual_return = 0

            results.append({
                'holding_candles': holding,
                'holding_hours': holding,
                'trades': len(trades),
                'winrate': winrate,
                'avg_pnl': avg_pnl,
                'final_balance': balance,
                'compound_return': compound_return,
                'annual_return': annual_return * 100,
                'total_days': total_days
            })

    return results

def analyze_soxl_vs_soxs(soxl_data: List[Dict], soxs_data: List[Dict]):
    """SOXL vs SOXS 비교 분석"""
    print("\n" + "="*80)
    print("[SOXL 분석]")
    print("="*80)

    soxl_results = test_all_holding_times(soxl_data, 'SOXL')

    if soxl_results:
        # 연수익 기준 정렬
        soxl_results.sort(key=lambda x: x['annual_return'], reverse=True)

        print(f"\n총 {len(soxl_results)}개 전략 테스트 완료")
        print("\n[TOP 5] 고수익 전략:")

        for i, r in enumerate(soxl_results[:5], 1):
            print(f"\n{i}. 보유시간: {r['holding_hours']}시간 ({r['holding_hours']/24:.1f}일)")
            print(f"   거래수: {r['trades']}건 ({r['total_days']:.0f}일간)")
            print(f"   승률: {r['winrate']:.1f}%")
            print(f"   평균 PNL: {r['avg_pnl']:+.2f}%")
            print(f"   복리 효과: {r['compound_return']:+.1f}%")
            print(f"   연환산 수익: {r['annual_return']:+.1f}%")

            if r['annual_return'] >= 100:
                print(f"   *** 연 100% 달성! ***")

    print("\n" + "="*80)
    print("[SOXS 분석]")
    print("="*80)

    soxs_results = test_all_holding_times(soxs_data, 'SOXS')

    if soxs_results:
        soxs_results.sort(key=lambda x: x['annual_return'], reverse=True)

        print(f"\n총 {len(soxs_results)}개 전략 테스트 완료")
        print("\n[TOP 5] 고수익 전략:")

        for i, r in enumerate(soxs_results[:5], 1):
            print(f"\n{i}. 보유시간: {r['holding_hours']}시간 ({r['holding_hours']/24:.1f}일)")
            print(f"   거래수: {r['trades']}건 ({r['total_days']:.0f}일간)")
            print(f"   승률: {r['winrate']:.1f}%")
            print(f"   평균 PNL: {r['avg_pnl']:+.2f}%")
            print(f"   복리 효과: {r['compound_return']:+.1f}%")
            print(f"   연환산 수익: {r['annual_return']:+.1f}%")

            if r['annual_return'] >= 100:
                print(f"   *** 연 100% 달성! ***")

    # 최종 비교
    print("\n" + "="*80)
    print("[최종 비교]")
    print("="*80)

    if soxl_results and soxs_results:
        soxl_best = soxl_results[0]
        soxs_best = soxs_results[0]

        print(f"\n[SOXL 최적 전략]")
        print(f"  보유시간: {soxl_best['holding_hours']}시간")
        print(f"  승률: {soxl_best['winrate']:.1f}%")
        print(f"  연수익: {soxl_best['annual_return']:+.1f}%")

        print(f"\n[SOXS 최적 전략]")
        print(f"  보유시간: {soxs_best['holding_hours']}시간")
        print(f"  승률: {soxs_best['winrate']:.1f}%")
        print(f"  연수익: {soxs_best['annual_return']:+.1f}%")

        # 평가
        print("\n" + "="*80)

        if soxl_best['annual_return'] >= 100:
            print("[SOXL] 연 100% 달성! ")
        else:
            print(f"[SOXL] 연 {soxl_best['annual_return']:.1f}% (목표 미달)")

        if soxs_best['annual_return'] >= 100:
            print("[SOXS] 연 100% 달성! ")
        else:
            print(f"[SOXS] 연 {soxs_best['annual_return']:.1f}% (목표 미달)")

        print("="*80)

        # 저장
        with open('C:/Users/user/Documents/deep_soxl_soxs_analysis.json', 'w', encoding='utf-8') as f:
            json.dump({
                'soxl_top10': soxl_results[:10],
                'soxs_top10': soxs_results[:10],
                'soxl_best': soxl_best,
                'soxs_best': soxs_best
            }, f, indent=2, ensure_ascii=False)

        print("\n[OK] deep_soxl_soxs_analysis.json 저장")

def main():
    # 데이터 수집
    soxl_data = fetch_hourly_data('SOXL')
    soxs_data = fetch_hourly_data('SOXS')

    if not soxl_data or not soxs_data:
        print("\n[ERROR] 데이터 수집 실패")
        return

    if len(soxl_data) < 100 or len(soxs_data) < 100:
        print("\n[ERROR] 데이터 부족 (최소 100개 필요)")
        return

    # 분석
    analyze_soxl_vs_soxs(soxl_data, soxs_data)

    print("\n" + "="*80)
    print("[다음 단계]")
    print("="*80)
    print("1. 연 100% 달성한 전략을 KIS 봇에 적용")
    print("2. LLM 학습 결과와 비교")
    print("3. 실시간 학습으로 지속 개선")

if __name__ == "__main__":
    main()
