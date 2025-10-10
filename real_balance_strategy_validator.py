#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실제 잔고 증가 기준 전략 검증
- PNL% 아니라 실제 USD/ETH 잔고 증가만 측정
- 수수료, 슬리피지 모두 반영
- 잔고가 실제로 늘어나는 전략만 유효
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict

FMP_API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"
FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"

print("="*80)
print("실제 잔고 증가 기준 전략 검증")
print("="*80)

# 수수료 및 슬리피지 설정
TAKER_FEE = 0.055 / 100  # 0.055% (Bybit/KIS 일반 수수료)
SLIPPAGE = 0.05 / 100    # 0.05% (시장가 슬리피지)
TOTAL_COST = (TAKER_FEE + SLIPPAGE) * 2  # 진입 + 청산

print(f"\n[거래 비용]")
print(f"  수수료: {TAKER_FEE*100:.3f}% × 2 = {TAKER_FEE*2*100:.3f}%")
print(f"  슬리피지: {SLIPPAGE*100:.3f}% × 2 = {SLIPPAGE*2*100:.3f}%")
print(f"  총 비용: {TOTAL_COST*100:.3f}%")

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

def analyze_patterns(data: List[Dict]) -> List[Dict]:
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
            'close': curr['close'],
            'daily_return': daily_return,
            'direction': direction,
            'consecutive': consecutive
        })

    return patterns

def simulate_with_real_balance(soxl: List[Dict], soxs: List[Dict],
                               holding_days: int,
                               take_profit: float,
                               stop_loss: float,
                               consecutive: int) -> Dict:
    """
    실제 잔고 기준 시뮬레이션

    중요: PNL% 아니라 USD 잔고만 추적!
    """
    print(f"\n[시뮬레이션] 실제 잔고 추적")
    print(f"  전략: 보유{holding_days}일, 익절+{take_profit}%, 손절{stop_loss}%, 연속{consecutive}일")

    # 초기 설정
    initial_balance = 10000.0  # $10,000 시작
    balance = initial_balance

    position = None
    entry_price = 0
    entry_date = None
    entry_idx = 0
    position_size = 0  # 진입 시 사용한 금액

    trades = []
    balance_history = [initial_balance]

    for i in range(consecutive, len(soxl)):
        soxl_curr = soxl[i]
        soxs_curr = soxs[i] if i < len(soxs) else None

        if not soxs_curr:
            continue

        # 진입
        if position is None:
            # SOXL 진입
            if soxl_curr['consecutive'] >= consecutive and soxl_curr['direction'] == 'UP':
                position = 'SOXL'
                entry_price = soxl_curr['close']
                entry_date = soxl_curr['date']
                entry_idx = i

                # 진입 비용 (수수료 + 슬리피지)
                entry_cost = balance * (TAKER_FEE + SLIPPAGE)
                position_size = balance - entry_cost
                balance = 0  # 전액 투입

                trades.append({
                    'type': 'ENTRY',
                    'symbol': 'SOXL',
                    'date': entry_date,
                    'price': entry_price,
                    'position_size': position_size,
                    'entry_cost': entry_cost
                })

            # SOXS 진입
            elif soxl_curr['consecutive'] >= consecutive and soxl_curr['direction'] == 'DOWN':
                position = 'SOXS'
                entry_price = soxs_curr['close']
                entry_date = soxs_curr['date']
                entry_idx = i

                entry_cost = balance * (TAKER_FEE + SLIPPAGE)
                position_size = balance - entry_cost
                balance = 0

                trades.append({
                    'type': 'ENTRY',
                    'symbol': 'SOXS',
                    'date': entry_date,
                    'price': entry_price,
                    'position_size': position_size,
                    'entry_cost': entry_cost
                })

        # 청산
        else:
            if position == 'SOXL':
                current_price = soxl_curr['close']
            else:
                current_price = soxs_curr['close']

            pnl_pct = (current_price - entry_price) / entry_price * 100
            days_held = i - entry_idx

            should_exit = False
            reason = ""

            if pnl_pct >= take_profit:
                should_exit = True
                reason = "TAKE_PROFIT"
            elif pnl_pct <= stop_loss:
                should_exit = True
                reason = "STOP_LOSS"
            elif days_held >= holding_days:
                should_exit = True
                reason = "TIME_LIMIT"
            elif position == 'SOXL' and soxl_curr['consecutive'] >= consecutive and soxl_curr['direction'] == 'DOWN':
                should_exit = True
                reason = "TREND_REVERSE"
            elif position == 'SOXS' and soxl_curr['consecutive'] >= consecutive and soxl_curr['direction'] == 'UP':
                should_exit = True
                reason = "TREND_REVERSE"

            if should_exit:
                # 실제 잔고 계산
                # 1. 포지션 가치 = 진입금액 × (1 + PNL%)
                position_value = position_size * (1 + pnl_pct / 100)

                # 2. 청산 비용 (수수료 + 슬리피지)
                exit_cost = position_value * (TAKER_FEE + SLIPPAGE)

                # 3. 실제 받는 금액
                balance = position_value - exit_cost

                # 4. 실제 수익 (USD)
                actual_profit = balance - (position_size + trades[-1]['entry_cost'])

                trades.append({
                    'type': 'EXIT',
                    'symbol': position,
                    'entry_date': entry_date,
                    'exit_date': soxl_curr['date'],
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'pnl_pct': pnl_pct,
                    'position_size': position_size,
                    'position_value': position_value,
                    'exit_cost': exit_cost,
                    'balance': balance,
                    'actual_profit': actual_profit,
                    'reason': reason
                })

                balance_history.append(balance)

                # 포지션 초기화
                position = None
                entry_price = 0
                position_size = 0

    # 결과 집계
    exits = [t for t in trades if t['type'] == 'EXIT']
    wins = [t for t in exits if t['actual_profit'] > 0]
    losses = [t for t in exits if t['actual_profit'] <= 0]

    return {
        'initial_balance': initial_balance,
        'final_balance': balance if position is None else position_size,
        'total_profit': balance - initial_balance if position is None else (position_size - initial_balance),
        'total_return_pct': ((balance - initial_balance) / initial_balance * 100) if position is None else
                           ((position_size - initial_balance) / initial_balance * 100),
        'total_trades': len(exits),
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': len(wins) / len(exits) * 100 if exits else 0,
        'avg_profit_per_trade': sum(t['actual_profit'] for t in exits) / len(exits) if exits else 0,
        'balance_history': balance_history,
        'trades': trades
    }

def test_multiple_strategies(soxl: List[Dict], soxs: List[Dict]) -> List[Dict]:
    """여러 전략 테스트"""
    print(f"\n[전략 테스트] 실제 잔고 증가 기준")

    strategies = [
        # 기존 최고 전략
        {'holding': 2, 'tp': 1, 'sl': -1, 'consec': 3, 'name': '기존 최고'},
        # 보수적 (손절 -0.5%)
        {'holding': 2, 'tp': 1, 'sl': -0.5, 'consec': 3, 'name': '보수적'},
        # 공격적 (익절 +2%)
        {'holding': 2, 'tp': 2, 'sl': -1, 'consec': 3, 'name': '공격적'},
        # ETH 스타일 (빠른 회전)
        {'holding': 1, 'tp': 0.5, 'sl': -0.3, 'consec': 2, 'name': 'ETH스타일'},
        # 장기 (5일)
        {'holding': 5, 'tp': 3, 'sl': -2, 'consec': 3, 'name': '장기'},
    ]

    results = []

    for s in strategies:
        result = simulate_with_real_balance(
            soxl, soxs,
            holding_days=s['holding'],
            take_profit=s['tp'],
            stop_loss=s['sl'],
            consecutive=s['consec']
        )
        result['strategy_name'] = s['name']
        results.append(result)

    return results

def main():
    # 데이터 수집
    soxl_data = fetch_daily_data('SOXL', 365)
    soxs_data = fetch_daily_data('SOXS', 365)

    if not soxl_data or not soxs_data:
        print("\n[ERROR] 데이터 수집 실패")
        return

    # 패턴 분석
    soxl_patterns = analyze_patterns(soxl_data)
    soxs_patterns = analyze_patterns(soxs_data)

    # 전략 테스트
    results = test_multiple_strategies(soxl_patterns, soxs_patterns)

    # 정렬: 실제 잔고 증가 순
    results.sort(key=lambda x: x['final_balance'], reverse=True)

    # 결과 출력
    print("\n" + "="*80)
    print("[결과] 실제 잔고 증가 기준 랭킹")
    print("="*80)

    for i, r in enumerate(results, 1):
        print(f"\n{i}. {r['strategy_name']}")
        print(f"   초기: ${r['initial_balance']:,.0f}")
        print(f"   최종: ${r['final_balance']:,.0f}")
        print(f"   수익: ${r['total_profit']:,.0f} ({r['total_return_pct']:+.1f}%)")
        print(f"   거래: {r['total_trades']}건, 승률: {r['win_rate']:.1f}%")
        print(f"   거래당 평균 수익: ${r['avg_profit_per_trade']:+.2f}")

        # 잔고 감소 경고
        if r['final_balance'] < r['initial_balance']:
            print(f"   [WARNING] 잔고 감소! 이 전략은 사용하지 마세요!")

    # 최고 전략
    best = results[0]
    print("\n" + "="*80)
    print("[최종 추천]")
    print("="*80)
    print(f"\n전략: {best['strategy_name']}")
    print(f"최종 잔고: ${best['final_balance']:,.0f}")
    print(f"수익률: {best['total_return_pct']:+.1f}%")

    if best['final_balance'] > best['initial_balance'] * 2:
        print(f"\n[***] 실제 잔고 2배 이상! 검증된 전략입니다!")
    elif best['final_balance'] > best['initial_balance']:
        print(f"\n[OK] 실제 잔고 증가 확인. 사용 가능한 전략입니다.")
    else:
        print(f"\n[ERROR] 잔고가 늘지 않습니다. 다른 방법을 찾아야 합니다!")

    print("="*80)

    # 저장
    with open('real_balance_validation.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("\n[OK] real_balance_validation.json 저장")

if __name__ == "__main__":
    main()
