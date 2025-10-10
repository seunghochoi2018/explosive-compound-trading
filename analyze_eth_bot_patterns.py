#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
현재 운영 중인 ETH 봇 심층 분석
- 최근 거래 패턴 분석
- 수익 패턴 찾기
- 시간대별 성과
- 복리 효과 계산
"""

import json
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

print("="*80)
print("ETH 봇 심층 분석")
print("="*80)

# 데이터 로드
with open('C:/Users/user/Documents/코드3/eth_trade_history.json', 'r', encoding='utf-8') as f:
    trades = json.load(f)

print(f"\n전체 거래: {len(trades)}건")

# 완료된 거래만 (exit_price 있는 것)
completed = [t for t in trades if 'pnl_pct' in t and t.get('exit_price')]
print(f"완료된 거래: {len(completed)}건")

# ============================================================================
# 1. 시간대별 분석
# ============================================================================
print("\n" + "="*80)
print("[1] 보유 시간별 성과")
print("="*80)

time_groups = {
    '초단타 (0-10분)': (0, 10),
    '단타 (10-30분)': (10, 30),
    '중기 (30-60분)': (30, 60),
    '중장기 (60-120분)': (60, 120),
    '장기 (120분+)': (120, 99999)
}

for name, (min_t, max_t) in time_groups.items():
    group = [t for t in completed if 'holding_time_min' in t and min_t <= t['holding_time_min'] < max_t]

    if group:
        wins = [t for t in group if t['pnl_pct'] > 0]
        winrate = len(wins) / len(group) * 100
        avg_pnl = sum(t['pnl_pct'] for t in group) / len(group)
        avg_win = sum(t['pnl_pct'] for t in wins) / len(wins) if wins else 0
        losses = [t for t in group if t['pnl_pct'] <= 0]
        avg_loss = sum(t['pnl_pct'] for t in losses) / len(losses) if losses else 0

        # 복리 계산 (연속 거래 시)
        balance = 10000
        for t in group:
            balance = balance * (1 + t['pnl_pct'] / 100)
        compound_return = (balance - 10000) / 10000 * 100

        print(f"\n{name}")
        print(f"  거래수: {len(group)}건")
        print(f"  승률: {winrate:.1f}%")
        print(f"  평균 수익: {avg_pnl:+.2f}%")
        print(f"  평균 익절: {avg_win:+.2f}%")
        print(f"  평균 손절: {avg_loss:+.2f}%")
        print(f"  복리 효과: {compound_return:+.1f}%")

        if compound_return > 50:
            print(f"  *** 복리 폭발 가능성! ***")

# ============================================================================
# 2. 롱/숏 분석
# ============================================================================
print("\n" + "="*80)
print("[2] 롱/숏 성과")
print("="*80)

longs = [t for t in completed if t.get('side') == 'BUY']
shorts = [t for t in completed if t.get('side') == 'SELL']

for side_name, side_trades in [('롱 (BUY)', longs), ('숏 (SELL)', shorts)]:
    if side_trades:
        wins = [t for t in side_trades if t['pnl_pct'] > 0]
        winrate = len(wins) / len(side_trades) * 100
        avg_pnl = sum(t['pnl_pct'] for t in side_trades) / len(side_trades)

        # 복리
        balance = 10000
        for t in side_trades:
            balance = balance * (1 + t['pnl_pct'] / 100)
        compound_return = (balance - 10000) / 10000 * 100

        print(f"\n{side_name}")
        print(f"  거래수: {len(side_trades)}건")
        print(f"  승률: {winrate:.1f}%")
        print(f"  평균 수익: {avg_pnl:+.2f}%")
        print(f"  복리 효과: {compound_return:+.1f}%")

# ============================================================================
# 3. 큰 수익 패턴 분석
# ============================================================================
print("\n" + "="*80)
print("[3] 큰 수익 거래 패턴 (PNL +5% 이상)")
print("="*80)

big_wins = [t for t in completed if t['pnl_pct'] >= 5]
print(f"\n큰 수익 거래: {len(big_wins)}건 ({len(big_wins)/len(completed)*100:.1f}%)")

if big_wins:
    # 패턴 찾기
    patterns = {
        '볼륨 급증': len([t for t in big_wins if t.get('volume_surge')]),
        '돌파 패턴': len([t for t in big_wins if t.get('breakout')]),
        '상승 추세': len([t for t in big_wins if t.get('market_1m_trend') == 'up']),
        '하락 추세': len([t for t in big_wins if t.get('market_1m_trend') == 'down']),
        '횡보 추세': len([t for t in big_wins if t.get('market_1m_trend') == 'sideways']),
    }

    print("\n패턴 분포:")
    for pattern, count in patterns.items():
        if count > 0:
            print(f"  {pattern}: {count}건 ({count/len(big_wins)*100:.1f}%)")

    # 평균 보유 시간
    avg_holding = sum(t.get('holding_time_min', 0) for t in big_wins) / len(big_wins)
    print(f"\n평균 보유 시간: {avg_holding:.0f}분")

    # 최근 큰 수익 거래
    print("\n최근 큰 수익 거래 5건:")
    for i, t in enumerate(big_wins[-5:], 1):
        print(f"{i}. {t.get('timestamp', 'N/A')[:16]}: {t['pnl_pct']:+.2f}%, "
              f"{t.get('holding_time_min', 0)}분, "
              f"{t.get('side', 'N/A')}, "
              f"추세:{t.get('market_1m_trend', 'N/A')}")

# ============================================================================
# 4. 연속 거래 시 복리 효과
# ============================================================================
print("\n" + "="*80)
print("[4] 복리 효과 계산")
print("="*80)

# 최근 100거래
recent_100 = completed[-100:]
balance = 10000

for t in recent_100:
    balance = balance * (1 + t['pnl_pct'] / 100)

compound_100 = (balance - 10000) / 10000 * 100
print(f"\n최근 100거래 복리 효과: {compound_100:+.1f}%")
print(f"잔고: $10,000 → ${balance:,.0f}")

# 거래당 평균 복리 기여
avg_contribution = (balance / 10000) ** (1/100) - 1
print(f"거래당 평균 기여: {avg_contribution*100:+.3f}%")

# 연간 환산 (최근 100거래 기간)
if recent_100:
    first_date = datetime.fromisoformat(recent_100[0]['timestamp'].replace('Z', '+00:00'))
    last_date = datetime.fromisoformat(recent_100[-1]['timestamp'].replace('Z', '+00:00'))
    days = (last_date - first_date).days

    if days > 0:
        trades_per_day = 100 / days
        daily_return = (balance / 10000) ** (1/days) - 1
        annual_return = (1 + daily_return) ** 365 - 1

        print(f"\n기간: {days}일")
        print(f"일 평균 거래: {trades_per_day:.1f}건")
        print(f"일 평균 수익: {daily_return*100:+.2f}%")
        print(f"연 환산 수익: {annual_return*100:+.1f}%")

        if annual_return > 1.0:
            print(f"\n*** 연 100% 이상 달성! ***")

# ============================================================================
# 5. 최적 전략 추천
# ============================================================================
print("\n" + "="*80)
print("[5] 최적 전략 추천")
print("="*80)

# 각 보유 시간대별 연환산 수익 계산
best_strategy = None
best_annual_return = 0

for name, (min_t, max_t) in time_groups.items():
    group = [t for t in completed if 'holding_time_min' in t and min_t <= t['holding_time_min'] < max_t]

    if len(group) >= 10:  # 최소 10거래
        # 복리 계산
        balance = 10000
        for t in group:
            balance = balance * (1 + t['pnl_pct'] / 100)

        # 총 시간 계산
        total_minutes = sum(t['holding_time_min'] for t in group)
        total_days = total_minutes / (60 * 24)

        if total_days > 0:
            daily_return = (balance / 10000) ** (1/total_days) - 1
            annual_return = (1 + daily_return) ** 365 - 1

            if annual_return > best_annual_return:
                best_annual_return = annual_return
                best_strategy = {
                    'name': name,
                    'trades': len(group),
                    'winrate': len([t for t in group if t['pnl_pct'] > 0]) / len(group) * 100,
                    'annual_return': annual_return * 100,
                    'avg_pnl': sum(t['pnl_pct'] for t in group) / len(group)
                }

if best_strategy:
    print(f"\n최적 전략: {best_strategy['name']}")
    print(f"  거래수: {best_strategy['trades']}건")
    print(f"  승률: {best_strategy['winrate']:.1f}%")
    print(f"  평균 수익: {best_strategy['avg_pnl']:+.2f}%")
    print(f"  연 환산 수익: {best_strategy['annual_return']:+.1f}%")

    if best_strategy['annual_return'] >= 100:
        print(f"\n*** 연 100% 달성 가능! ***")
    else:
        print(f"\n목표 미달 (목표: 연 100%)")

print("\n" + "="*80)
