#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS SOXL/SOXS 승률 70% 패턴 찾기
- 모든 조합 테스트
- 승률 70% 이상 패턴 발굴
"""

import json
from datetime import datetime, timedelta
from collections import defaultdict

# 거래 데이터 로드
with open('kis_trade_history.json', 'r', encoding='utf-8') as f:
    all_trades = json.load(f)

print("="*80)
print("KIS SOXL/SOXS 승률 70% 패턴 찾기")
print("="*80)
print(f"\n총 거래 데이터: {len(all_trades)}건\n")

# 1. 기본 통계
wins = [t for t in all_trades if t.get('pnl_pct', 0) > 0]
losses = [t for t in all_trades if t.get('pnl_pct', 0) <= 0]
print(f"전체 승률: {len(wins)/len(all_trades)*100:.1f}%\n")

# 2. SOXL vs SOXS 상세 분석
print("="*80)
print("패턴 1: SOXL vs SOXS 비교")
print("="*80)

soxl_trades = [t for t in all_trades if 'SOXL' in t.get('symbol', '')]
soxs_trades = [t for t in all_trades if 'SOXS' in t.get('symbol', '')]

soxl_wins = [t for t in soxl_trades if t.get('pnl_pct', 0) > 0]
soxs_wins = [t for t in soxs_trades if t.get('pnl_pct', 0) > 0]

print(f"SOXL: {len(soxl_trades)}건, 승률 {len(soxl_wins)/len(soxl_trades)*100:.1f}%")
print(f"SOXS: {len(soxs_trades)}건, 승률 {len(soxs_wins)/len(soxs_trades)*100:.1f}%")
print(f"\n[OK] 결론: SOXL만 거래 시 승률 = {len(soxl_wins)/len(soxl_trades)*100:.1f}%\n")

# 3. 보유 기간별 분석 (상세)
print("="*80)
print("패턴 2: 보유 기간별 승률")
print("="*80)

# 보유 기간 계산 (거래 데이터에 holding_days 추가)
for trade in all_trades:
    if 'entry_timestamp' in trade and 'timestamp' in trade:
        try:
            entry_time = datetime.fromisoformat(trade['entry_timestamp'])
            exit_time = datetime.fromisoformat(trade['timestamp'])
            holding_days = (exit_time - entry_time).total_seconds() / 86400
            trade['holding_days'] = holding_days
        except:
            trade['holding_days'] = None

# 보유 기간별 그룹
holding_groups = {
    '0-1일': (0, 1),
    '1-2일': (1, 2),
    '2-3일': (2, 3),
    '3-5일': (3, 5),
    '5-7일': (5, 7),
    '1-2주': (7, 14),
    '2주+': (14, 999)
}

for name, (min_days, max_days) in holding_groups.items():
    group_trades = [t for t in all_trades if t.get('holding_days') and min_days <= t['holding_days'] < max_days]
    if group_trades:
        group_wins = [t for t in group_trades if t.get('pnl_pct', 0) > 0]
        win_rate = len(group_wins) / len(group_trades) * 100
        avg_pnl = sum(t.get('pnl_pct', 0) for t in group_trades) / len(group_trades)

        marker = "[***]" if win_rate >= 70 else "[OK]" if win_rate >= 60 else ""
        print(f"{name}: {len(group_trades)}건, 승률 {win_rate:.1f}%, 평균 {avg_pnl:+.2f}% {marker}")

# 4. 수익 범위별 분석
print("\n" + "="*80)
print("패턴 3: 목표 수익별 청산 시뮬레이션")
print("="*80)

# 각 거래의 최고점 PNL 시뮬레이션 (실제론 모르지만 가정)
# 현재 청산 PNL이 최고점이라고 가정하고 중간에 익절했으면?

take_profit_targets = [3, 5, 7, 10, 15, 20]
for target in take_profit_targets:
    simulated_wins = []
    simulated_losses = []

    for trade in all_trades:
        pnl = trade.get('pnl_pct', 0)

        # 수익이 목표치 이상이면 목표치에서 청산했다고 가정
        if pnl >= target:
            simulated_wins.append(target)
        # 손실이거나 목표 미달이면 그대로
        else:
            if pnl > 0:
                simulated_losses.append(pnl)  # 목표 못 채운 수익
            else:
                simulated_losses.append(pnl)  # 손실

    total_trades = len(simulated_wins) + len(simulated_losses)
    win_rate = len(simulated_wins) / total_trades * 100 if total_trades > 0 else 0

    marker = "[***]" if win_rate >= 70 else "[OK]" if win_rate >= 60 else ""
    print(f"목표 +{target}% 익절: 달성 {len(simulated_wins)}건, 승률 {win_rate:.1f}% {marker}")

# 5. 손절선별 분석
print("\n" + "="*80)
print("패턴 4: 손절선별 시뮬레이션")
print("="*80)

stop_loss_targets = [-3, -5, -7, -10]
for sl_target in stop_loss_targets:
    prevented_losses = [t for t in all_trades if t.get('pnl_pct', 0) < sl_target]
    remaining_trades = [t for t in all_trades if t.get('pnl_pct', 0) >= sl_target]

    if remaining_trades:
        remaining_wins = [t for t in remaining_trades if t.get('pnl_pct', 0) > 0]
        win_rate = len(remaining_wins) / len(remaining_trades) * 100

        marker = "[***]" if win_rate >= 70 else "[OK]" if win_rate >= 60 else ""
        print(f"손절 {sl_target}%: 방지 {len(prevented_losses)}건, 잔여 승률 {win_rate:.1f}% {marker}")

# 6. SOXL 전용 + 보유 기간 조합
print("\n" + "="*80)
print("패턴 5: SOXL 전용 + 보유 기간 조합")
print("="*80)

for name, (min_days, max_days) in holding_groups.items():
    soxl_group = [t for t in soxl_trades if t.get('holding_days') and min_days <= t['holding_days'] < max_days]
    if soxl_group:
        soxl_group_wins = [t for t in soxl_group if t.get('pnl_pct', 0) > 0]
        win_rate = len(soxl_group_wins) / len(soxl_group) * 100
        avg_pnl = sum(t.get('pnl_pct', 0) for t in soxl_group) / len(soxl_group)

        marker = "[***]" if win_rate >= 70 else "[OK]" if win_rate >= 60 else ""
        print(f"SOXL + {name}: {len(soxl_group)}건, 승률 {win_rate:.1f}%, 평균 {avg_pnl:+.2f}% {marker}")

# 7. 종합 최적 패턴 찾기
print("\n" + "="*80)
print("[***] 승률 70% 이상 달성 가능한 전략 조합")
print("="*80)

best_strategies = []

# 조합 1: SOXL + 특정 보유기간 + 익절
for name, (min_days, max_days) in holding_groups.items():
    for tp_target in take_profit_targets:
        for sl_target in stop_loss_targets:
            # SOXL만, 특정 보유기간
            filtered = [t for t in soxl_trades
                       if t.get('holding_days')
                       and min_days <= t['holding_days'] < max_days]

            if len(filtered) < 5:  # 최소 5건은 있어야 의미 있음
                continue

            # 익절/손절 시뮬레이션
            simulated_trades = []
            for trade in filtered:
                pnl = trade.get('pnl_pct', 0)

                # 손절
                if pnl < sl_target:
                    simulated_trades.append(('LOSS', sl_target))
                # 익절
                elif pnl >= tp_target:
                    simulated_trades.append(('WIN', tp_target))
                # 중간
                else:
                    simulated_trades.append(('WIN' if pnl > 0 else 'LOSS', pnl))

            wins_count = len([t for t in simulated_trades if t[0] == 'WIN'])
            win_rate = wins_count / len(simulated_trades) * 100

            if win_rate >= 70:
                avg_pnl = sum(t[1] for t in simulated_trades) / len(simulated_trades)
                best_strategies.append({
                    'strategy': f"SOXL + {name} + 익절{tp_target}% + 손절{sl_target}%",
                    'trades': len(simulated_trades),
                    'win_rate': win_rate,
                    'avg_pnl': avg_pnl
                })

# 정렬 (승률 높은 순)
best_strategies.sort(key=lambda x: x['win_rate'], reverse=True)

if best_strategies:
    print(f"\n찾은 전략: {len(best_strategies)}개\n")
    for i, strategy in enumerate(best_strategies[:10], 1):  # 상위 10개만
        print(f"{i}. {strategy['strategy']}")
        print(f"   거래 {strategy['trades']}건, 승률 {strategy['win_rate']:.1f}%, 평균 {strategy['avg_pnl']:+.2f}%\n")
else:
    print("\n[X] 승률 70% 이상 전략을 찾지 못했습니다.")
    print("   → 더 많은 데이터 수집 필요")
    print("   → 또는 다른 접근 필요 (앙상블, 시장 환경 필터 등)")

print("\n" + "="*80)
print("분석 완료")
print("="*80)
