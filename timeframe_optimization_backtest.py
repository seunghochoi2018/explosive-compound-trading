#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
시간봉 주기 최적화 백테스트

현재 설정:
- ETH: 60초(1분) 정기 분석
- KIS: 15분(900초) 정기 분석

테스트 주기:
- 30초, 1분, 2분, 5분, 10분, 15분, 30분, 1시간
"""

import json
from datetime import datetime, timedelta
from collections import defaultdict

# ===== 현재 설정 =====
CURRENT_ETH_INTERVAL = 60  # 1분
CURRENT_KIS_INTERVAL = 900  # 15분

# ===== 테스트할 시간봉 (초 단위) =====
TEST_INTERVALS = {
    '30초': 30,
    '1분': 60,
    '2분': 120,
    '5분': 300,
    '10분': 600,
    '15분': 900,
    '30분': 1800,
    '1시간': 3600
}

def analyze_eth_timeframes():
    """ETH 거래 데이터로 최적 시간봉 분석"""
    print("="*80)
    print("ETH 시간봉 최적화 백테스트")
    print("="*80)

    # 거래 데이터 로드
    try:
        with open(r'C:\Users\user\Documents\코드3\eth_trade_history.json', 'r', encoding='utf-8') as f:
            all_trades = json.load(f)
    except:
        print("[ERROR] ETH 거래 데이터 로드 실패")
        return

    if not all_trades:
        print("[WARN] ETH 거래 데이터 없음")
        return

    print(f"\n총 거래: {len(all_trades)}건")

    # 시간봉별 성과 분석
    results = {}

    for interval_name, interval_sec in TEST_INTERVALS.items():
        # 해당 시간봉에서 거래 가능한 횟수 시뮬레이션
        trades_in_interval = []

        # 각 거래의 보유 시간을 시간봉과 비교
        for trade in all_trades:
            holding_time = trade.get('holding_time_sec', 0)
            pnl = trade.get('pnl_pct', 0)

            # 해당 시간봉에 맞는 거래인지 판단
            # (보유시간이 시간봉의 0.5배 ~ 2배 사이면 적합)
            if interval_sec * 0.5 <= holding_time <= interval_sec * 2:
                trades_in_interval.append({
                    'pnl': pnl,
                    'holding_time': holding_time,
                    'reason': trade.get('reason', ''),
                    'balance_change': trade.get('balance_change', 0)
                })

        if not trades_in_interval:
            results[interval_name] = {
                'total': 0,
                'win_rate': 0,
                'avg_pnl': 0,
                'profit_factor': 0,
                'suitable': False
            }
            continue

        # 승률 계산
        wins = [t for t in trades_in_interval if t['balance_change'] > 0]
        losses = [t for t in trades_in_interval if t['balance_change'] <= 0]

        win_rate = (len(wins) / len(trades_in_interval)) * 100 if trades_in_interval else 0

        # 평균 PNL
        avg_pnl = sum(t['pnl'] for t in trades_in_interval) / len(trades_in_interval)

        # Profit Factor
        total_profit = sum(t['balance_change'] for t in wins)
        total_loss = abs(sum(t['balance_change'] for t in losses))
        profit_factor = total_profit / total_loss if total_loss > 0 else 0

        results[interval_name] = {
            'total': len(trades_in_interval),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate,
            'avg_pnl': avg_pnl,
            'profit_factor': profit_factor,
            'total_profit': total_profit,
            'suitable': len(trades_in_interval) >= 50  # 최소 50건 필요
        }

    # 결과 출력
    print("\n" + "="*80)
    print("시간봉별 성과 분석 (ETH)")
    print("="*80)
    print(f"{'시간봉':<8} {'거래수':<8} {'승률':<10} {'평균PNL':<12} {'PF':<8} {'적합성':<8}")
    print("-"*80)

    best_interval = None
    best_score = -999999

    for interval_name, result in results.items():
        suitable = "[O] OK" if result['suitable'] else "[X] Low"

        # 종합 점수 (승률 * PF * 거래수)
        score = result['win_rate'] * result['profit_factor'] * (result['total'] / 100)

        if result['suitable'] and score > best_score:
            best_score = score
            best_interval = interval_name

        print(f"{interval_name:<8} {result['total']:<8} {result['win_rate']:>6.1f}%   "
              f"{result['avg_pnl']:>+8.2f}%   {result['profit_factor']:>6.2f}  {suitable}")

    # 현재 설정과 비교
    print("\n" + "="*80)
    print("현재 설정 vs 최적 설정")
    print("="*80)
    current_result = results.get('1분', {})
    best_result = results.get(best_interval, {})

    print(f"\n현재 설정: 1분 (60초)")
    print(f"  거래수: {current_result.get('total', 0)}건")
    print(f"  승률: {current_result.get('win_rate', 0):.1f}%")
    print(f"  평균 PNL: {current_result.get('avg_pnl', 0):+.2f}%")
    print(f"  Profit Factor: {current_result.get('profit_factor', 0):.2f}")

    if best_interval:
        print(f"\n추천 설정: {best_interval}")
        print(f"  거래수: {best_result.get('total', 0)}건")
        print(f"  승률: {best_result.get('win_rate', 0):.1f}%")
        print(f"  평균 PNL: {best_result.get('avg_pnl', 0):+.2f}%")
        print(f"  Profit Factor: {best_result.get('profit_factor', 0):.2f}")

        if best_interval != '1분':
            improvement = (best_result.get('profit_factor', 0) / current_result.get('profit_factor', 1) - 1) * 100
            print(f"\n개선 효과: {improvement:+.1f}% (Profit Factor 기준)")

    return best_interval, results

def analyze_kis_timeframes():
    """KIS 거래 데이터로 최적 시간봉 분석"""
    print("\n" + "="*80)
    print("KIS 시간봉 최적화 백테스트")
    print("="*80)

    try:
        with open(r'C:\Users\user\Documents\코드4\kis_trade_history.json', 'r', encoding='utf-8') as f:
            all_trades = json.load(f)
    except:
        print("[WARN] KIS 거래 데이터 없음 (신규 시스템)")
        print("\n권장 설정:")
        print("  - SOXL/SOXS는 3배 레버리지 → 신중한 진입 필요")
        print("  - 미국 정규장: 하루 6.5시간 (22:30-05:00)")
        print("  - 추천: 15분~30분 (현재 15분 유지 권장)")
        return None, {}

    if not all_trades:
        print("[WARN] KIS 거래 기록 없음")
        return None, {}

    print(f"총 거래: {len(all_trades)}건")

    # ETH와 동일한 분석 로직
    results = {}

    for interval_name, interval_sec in TEST_INTERVALS.items():
        trades_in_interval = []

        for trade in all_trades:
            holding_hours = trade.get('holding_hours', 0)
            holding_time = holding_hours * 3600  # 시간 -> 초

            if interval_sec * 0.5 <= holding_time <= interval_sec * 2:
                trades_in_interval.append({
                    'pnl': trade.get('pnl_pct', 0),
                    'balance_change': trade.get('balance_change', 0)
                })

        if not trades_in_interval:
            results[interval_name] = {
                'total': 0,
                'win_rate': 0,
                'avg_pnl': 0,
                'profit_factor': 0,
                'suitable': False
            }
            continue

        wins = [t for t in trades_in_interval if t['balance_change'] > 0]
        losses = [t for t in trades_in_interval if t['balance_change'] <= 0]

        win_rate = (len(wins) / len(trades_in_interval)) * 100
        avg_pnl = sum(t['pnl'] for t in trades_in_interval) / len(trades_in_interval)

        total_profit = sum(t['balance_change'] for t in wins)
        total_loss = abs(sum(t['balance_change'] for t in losses))
        profit_factor = total_profit / total_loss if total_loss > 0 else 0

        results[interval_name] = {
            'total': len(trades_in_interval),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate,
            'avg_pnl': avg_pnl,
            'profit_factor': profit_factor,
            'suitable': len(trades_in_interval) >= 20
        }

    # 결과 출력
    print("\n시간봉별 성과")
    print("-"*80)
    for interval_name, result in results.items():
        suitable = "[O]" if result['suitable'] else "[X]"
        print(f"{interval_name:<8} {result['total']:<8} {result['win_rate']:>6.1f}%   "
              f"{result['avg_pnl']:>+8.2f}%   {result['profit_factor']:>6.2f}  {suitable}")

    return None, results

def main():
    """메인 실행"""
    print("\n시간봉 최적화 백테스트 시작")
    print("="*80)

    # ETH 분석
    eth_best, eth_results = analyze_eth_timeframes()

    # KIS 분석
    kis_best, kis_results = analyze_kis_timeframes()

    # 최종 권장사항
    print("\n" + "="*80)
    print("최종 권장사항")
    print("="*80)

    print("\nETH 트레이더:")
    if eth_best:
        print(f"  현재: 1분 (60초)")
        print(f"  권장: {eth_best}")
        if eth_best == '1분':
            print(f"  [OK] 현재 설정이 최적입니다!")
        else:
            print(f"  [!] {eth_best}로 변경 권장")

    print("\nKIS 트레이더:")
    print(f"  현재: 15분 (900초)")
    if kis_best:
        print(f"  권장: {kis_best}")
    else:
        print(f"  [OK] 현재 15분 설정 유지 권장 (3배 레버리지 특성)")

    print("\n" + "="*80)
    print("분석 완료!")
    print("="*80)

if __name__ == "__main__":
    main()
