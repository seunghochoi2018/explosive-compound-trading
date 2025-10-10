#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS 피라미딩 복리 폭발 전략
- 기본: 보유 2일, 익절 +1%, 손절 -1%
- 추가: ETH 방식 피라미딩
- 목표: 복리 +529% → +1000%+
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict

FMP_API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"
FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"

print("="*80)
print("KIS 피라미딩 복리 폭발 전략")
print("="*80)

def fetch_daily_data(symbol: str, days: int = 365) -> List[Dict]:
    """일봉 데이터 수집"""
    print(f"\n[데이터] {symbol} 일봉 (최근 {days}일)")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    url = f"{FMP_BASE_URL}/historical-price-full/{symbol}"
    params = {
        "apikey": FMP_API_KEY,
        "from": start_date.strftime('%Y-%m-%d'),
        "to": end_date.strftime('%Y-%m-%d')
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            historical = data.get('historical', [])
            historical = sorted(historical, key=lambda x: x['date'])
            print(f"  [OK] {len(historical)}일")
            return historical
        else:
            return []
    except:
        return []

def analyze_price_patterns(data: List[Dict]) -> List[Dict]:
    """가격 패턴 분석"""
    patterns = []
    for i in range(1, len(data)):
        prev = data[i-1]
        curr = data[i]
        daily_return = (curr['close'] - prev['close']) / prev['close'] * 100
        direction = 'UP' if daily_return > 0 else 'DOWN'

        consecutive = 1
        for j in range(i-1, 0, -1):
            prev_dir = 'UP' if data[j]['close'] > data[j-1]['close'] else 'DOWN'
            if prev_dir == direction:
                consecutive += 1
            else:
                break

        patterns.append({
            'date': curr['date'],
            'open': curr['open'],
            'high': curr['high'],
            'low': curr['low'],
            'close': curr['close'],
            'daily_return': daily_return,
            'direction': direction,
            'consecutive': consecutive
        })

    return patterns

def simulate_with_pyramiding(soxl: List[Dict], soxs: List[Dict]) -> Dict:
    """
    피라미딩 전략 시뮬레이션

    기본:
    - 연속 3일 상승 → SOXL 진입
    - 연속 3일 하락 → SOXS 진입
    - 익절 +1%, 손절 -1%, 보유 2일

    피라미딩:
    - PNL +0.5% 달성: +15% 증액
    - PNL +1.0% 달성: +15% 증액
    - PNL +1.5% 달성: +15% 증액
    - PNL +2.0% 달성: +15% 증액
    → 최대 4단계, 총 160% 투입
    """
    print("\n[시뮬레이션] 피라미딩 전략")

    initial_balance = 10000  # 초기 잔고
    balance = initial_balance
    position = None
    entry_price = 0
    entry_date = None
    entry_idx = 0
    base_position_size = 0  # 기본 포지션 크기
    total_position_size = 0  # 총 포지션 크기
    pyramid_levels = []  # 피라미딩 단계별 가격

    trades = []

    for i in range(3, len(soxl)):
        soxl_curr = soxl[i]
        soxs_curr = soxs[i] if i < len(soxs) else None

        if not soxs_curr:
            continue

        # 진입 신호
        if position is None:
            # SOXL 진입
            if soxl_curr['consecutive'] >= 3 and soxl_curr['direction'] == 'UP':
                position = 'SOXL'
                entry_price = soxl_curr['close']
                entry_date = soxl_curr['date']
                entry_idx = i
                base_position_size = balance * 1.0  # 100% 투입
                total_position_size = base_position_size
                pyramid_levels = []

                trades.append({
                    'type': 'ENTRY',
                    'symbol': 'SOXL',
                    'price': entry_price,
                    'size': base_position_size,
                    'date': entry_date
                })

            # SOXS 진입
            elif soxl_curr['consecutive'] >= 3 and soxl_curr['direction'] == 'DOWN':
                position = 'SOXS'
                entry_price = soxs_curr['close']
                entry_date = soxs_curr['date']
                entry_idx = i
                base_position_size = balance * 1.0
                total_position_size = base_position_size
                pyramid_levels = []

                trades.append({
                    'type': 'ENTRY',
                    'symbol': 'SOXS',
                    'price': entry_price,
                    'size': base_position_size,
                    'date': entry_date
                })

        # 포지션 관리
        else:
            if position == 'SOXL':
                current_price = soxl_curr['close']
            else:
                current_price = soxs_curr['close']

            pnl_pct = (current_price - entry_price) / entry_price * 100
            days_held = i - entry_idx

            # 피라미딩 체크 (0.5%, 1.0%, 1.5%, 2.0%)
            pyramid_thresholds = [0.5, 1.0, 1.5, 2.0]
            for threshold in pyramid_thresholds:
                if pnl_pct >= threshold and threshold not in pyramid_levels:
                    # 피라미딩 실행
                    pyramid_size = base_position_size * 0.15  # 15% 증액
                    total_position_size += pyramid_size
                    pyramid_levels.append(threshold)

                    trades.append({
                        'type': 'PYRAMID',
                        'symbol': position,
                        'price': current_price,
                        'size': pyramid_size,
                        'date': soxl_curr['date'],
                        'pnl_pct': pnl_pct
                    })

            # 청산 조건
            should_exit = False
            reason = ""

            if pnl_pct >= 1.0:
                should_exit = True
                reason = "TAKE_PROFIT"
            elif pnl_pct <= -1.0:
                should_exit = True
                reason = "STOP_LOSS"
            elif days_held >= 2:
                should_exit = True
                reason = "TIME_LIMIT"
            elif position == 'SOXL' and soxl_curr['consecutive'] >= 3 and soxl_curr['direction'] == 'DOWN':
                should_exit = True
                reason = "TREND_REVERSE"
            elif position == 'SOXS' and soxl_curr['consecutive'] >= 3 and soxl_curr['direction'] == 'UP':
                should_exit = True
                reason = "TREND_REVERSE"

            if should_exit:
                # 청산
                # 가중 평균 진입가 계산
                avg_entry = entry_price  # 단순화: 기본 진입가 사용
                final_pnl = (current_price - avg_entry) / avg_entry
                pnl_amount = total_position_size * final_pnl
                balance = balance + pnl_amount

                trades.append({
                    'type': 'EXIT',
                    'symbol': position,
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'entry_date': entry_date,
                    'exit_date': soxl_curr['date'],
                    'pnl_pct': pnl_pct,
                    'pnl_amount': pnl_amount,
                    'balance': balance,
                    'pyramid_levels': len(pyramid_levels),
                    'reason': reason
                })

                # 포지션 초기화
                position = None
                entry_price = 0
                base_position_size = 0
                total_position_size = 0
                pyramid_levels = []

    # 결과 집계
    exits = [t for t in trades if t['type'] == 'EXIT']
    wins = [t for t in exits if t['pnl_pct'] > 0]

    return {
        'initial_balance': initial_balance,
        'final_balance': balance,
        'total_return_pct': (balance - initial_balance) / initial_balance * 100,
        'total_trades': len(exits),
        'wins': len(wins),
        'win_rate': len(wins) / len(exits) * 100 if exits else 0,
        'avg_pnl': sum(t['pnl_pct'] for t in exits) / len(exits) if exits else 0,
        'trades': trades
    }

def main():
    # 데이터 수집
    soxl_data = fetch_daily_data('SOXL', 365)
    soxs_data = fetch_daily_data('SOXS', 365)

    if not soxl_data or not soxs_data:
        print("\n[ERROR] 데이터 수집 실패")
        return

    # 패턴 분석
    soxl_patterns = analyze_price_patterns(soxl_data)
    soxs_patterns = analyze_price_patterns(soxs_data)

    # 피라미딩 시뮬레이션
    result = simulate_with_pyramiding(soxl_patterns, soxs_patterns)

    # 결과 출력
    print("\n" + "="*80)
    print("[결과] 피라미딩 전략")
    print("="*80)
    print(f"\n초기 잔고: ${result['initial_balance']:,.0f}")
    print(f"최종 잔고: ${result['final_balance']:,.0f}")
    print(f"총 수익률: {result['total_return_pct']:+.1f}%")
    print(f"\n총 거래: {result['total_trades']}건")
    print(f"승률: {result['win_rate']:.1f}%")
    print(f"평균 PNL: {result['avg_pnl']:+.2f}%")

    # 피라미딩 효과 분석
    exits = [t for t in result['trades'] if t['type'] == 'EXIT']
    with_pyramid = [t for t in exits if t['pyramid_levels'] > 0]
    without_pyramid = [t for t in exits if t['pyramid_levels'] == 0]

    print(f"\n피라미딩 활용:")
    print(f"  활용: {len(with_pyramid)}건 ({len(with_pyramid)/len(exits)*100:.1f}%)")
    print(f"  미활용: {len(without_pyramid)}건 ({len(without_pyramid)/len(exits)*100:.1f}%)")

    if with_pyramid:
        avg_pyramid_pnl = sum(t['pnl_pct'] for t in with_pyramid) / len(with_pyramid)
        print(f"  피라미딩 평균 수익: {avg_pyramid_pnl:+.2f}%")

    # 기존 전략과 비교
    print("\n" + "="*80)
    print("[비교]")
    print("="*80)
    print(f"\n기존 전략 (피라미딩 없음):")
    print(f"  복리: +529.8%")
    print(f"\n피라미딩 전략:")
    print(f"  복리: {result['total_return_pct']:+.1f}%")

    improvement = result['total_return_pct'] - 529.8
    if improvement > 0:
        print(f"\n[***] {improvement:+.1f}%p 개선!")
    else:
        print(f"\n[WARNING] {abs(improvement):.1f}%p 하락")

    print("="*80)

    # 저장
    with open('kis_pyramiding_result.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print("\n[OK] kis_pyramiding_result.json 저장")

if __name__ == "__main__":
    main()
