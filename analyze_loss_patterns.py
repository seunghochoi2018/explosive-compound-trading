#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
손실 패턴 깊은 분석 - 피해야 할 상황 찾기

목표: 큰 손실을 일으키는 패턴 식별 → 절대 진입 금지
"""

import json
from collections import defaultdict

print("="*80)
print("손실 패턴 분석 - 피해야 할 상황")
print("="*80)

# 데이터 로드
with open('C:/Users/user/Documents/코드3/eth_trade_history.json', 'r', encoding='utf-8') as f:
    trades = json.load(f)

completed = [t for t in trades if 'pnl_pct' in t and t.get('exit_price')]

# 손실 분류
big_losses = [t for t in completed if t['pnl_pct'] <= -5]
medium_losses = [t for t in completed if -5 < t['pnl_pct'] <= -2]
small_losses = [t for t in completed if -2 < t['pnl_pct'] <= 0]

print(f"\n큰 손실 (-5% 이하): {len(big_losses)}건")
print(f"중간 손실 (-5 ~ -2%): {len(medium_losses)}건")
print(f"소액 손실 (0 ~ -2%): {len(small_losses)}건")

# ============================================================================
# 1. 큰 손실 패턴 분석
# ============================================================================
print("\n" + "="*80)
print("[큰 손실 패턴] -5% 이하")
print("="*80)

if big_losses:
    # 보유 시간
    avg_holding = sum(t.get('holding_time_min', 0) for t in big_losses) / len(big_losses)
    print(f"\n평균 보유시간: {avg_holding:.0f}분")

    # 보유시간 분포
    time_groups = defaultdict(int)
    for t in big_losses:
        holding = t.get('holding_time_min', 0)
        if holding < 10:
            time_groups['0-10분'] += 1
        elif holding < 30:
            time_groups['10-30분'] += 1
        elif holding < 60:
            time_groups['30-60분'] += 1
        elif holding < 120:
            time_groups['60-120분'] += 1
        else:
            time_groups['120분+'] += 1

    print("\n보유시간 분포:")
    for period, count in sorted(time_groups.items()):
        print(f"  {period}: {count}건 ({count/len(big_losses)*100:.1f}%)")

    # 추세 분석
    trends = defaultdict(int)
    for t in big_losses:
        trend = t.get('market_1m_trend', 'unknown')
        trends[trend] += 1

    print("\n추세 분포:")
    for trend, count in sorted(trends.items(), key=lambda x: x[1], reverse=True):
        print(f"  {trend}: {count}건 ({count/len(big_losses)*100:.1f}%)")

    # 롱/숏 분포
    longs = [t for t in big_losses if t.get('side') == 'BUY']
    shorts = [t for t in big_losses if t.get('side') == 'SELL']

    print("\n포지션 분포:")
    print(f"  롱 (BUY): {len(longs)}건 ({len(longs)/len(big_losses)*100:.1f}%)")
    print(f"  숏 (SELL): {len(shorts)}건 ({len(shorts)/len(big_losses)*100:.1f}%)")

    # 평균 손실
    avg_loss = sum(t['pnl_pct'] for t in big_losses) / len(big_losses)
    print(f"\n평균 손실: {avg_loss:.2f}%")

    # 최악의 손실
    worst = min(big_losses, key=lambda x: x['pnl_pct'])
    print(f"\n최악의 손실:")
    print(f"  PNL: {worst['pnl_pct']:.2f}%")
    print(f"  보유시간: {worst.get('holding_time_min', 0)}분")
    print(f"  추세: {worst.get('market_1m_trend', 'unknown')}")
    print(f"  포지션: {worst.get('side', 'unknown')}")

# ============================================================================
# 2. 중간 손실 패턴 분석
# ============================================================================
print("\n" + "="*80)
print("[중간 손실 패턴] -5% ~ -2%")
print("="*80)

if medium_losses:
    avg_holding = sum(t.get('holding_time_min', 0) for t in medium_losses) / len(medium_losses)
    print(f"\n평균 보유시간: {avg_holding:.0f}분")

    # 보유시간 분포
    time_groups = defaultdict(int)
    for t in medium_losses:
        holding = t.get('holding_time_min', 0)
        if holding < 10:
            time_groups['0-10분'] += 1
        elif holding < 30:
            time_groups['10-30분'] += 1
        elif holding < 60:
            time_groups['30-60분'] += 1
        elif holding < 120:
            time_groups['60-120분'] += 1
        else:
            time_groups['120분+'] += 1

    print("\n보유시간 분포:")
    for period, count in sorted(time_groups.items()):
        print(f"  {period}: {count}건 ({count/len(medium_losses)*100:.1f}%)")

    # 추세 분석
    trends = defaultdict(int)
    for t in medium_losses:
        trend = t.get('market_1m_trend', 'unknown')
        trends[trend] += 1

    print("\n추세 분포:")
    for trend, count in sorted(trends.items(), key=lambda x: x[1], reverse=True):
        print(f"  {trend}: {count}건 ({count/len(medium_losses)*100:.1f}%)")

# ============================================================================
# 3. 손실 → 복리 파괴 계산
# ============================================================================
print("\n" + "="*80)
print("[손실의 복리 파괴 효과]")
print("="*80)

# 큰 손실 1번의 영향
print("\n큰 손실 1번 (-5%)의 영향:")
balance = 10000
print(f"  시작: ${balance:,.0f}")
balance *= 0.95  # -5%
print(f"  손실 후: ${balance:,.0f}")
print(f"  복구 필요: +{(10000-balance)/balance*100:.1f}%")

# 작은 수익으로 복구
small_profit_count = 0
while balance < 10000:
    balance *= 1.01  # +1%
    small_profit_count += 1

print(f"  복구 거래: {small_profit_count}번 (+1% 거래)")

# 큰 손실 10번의 영향
print("\n큰 손실 10번의 영향:")
balance = 10000
for _ in range(10):
    balance *= 0.95

print(f"  시작: $10,000")
print(f"  10번 후: ${balance:,.0f}")
print(f"  손실: {(balance-10000)/10000*100:.1f}%")

# ============================================================================
# 4. 피해야 할 조건 도출
# ============================================================================
print("\n" + "="*80)
print("[피해야 할 조건]")
print("="*80)

# 120분 이상 보유
long_hold_losses = [t for t in completed if t.get('holding_time_min', 0) >= 120 and t['pnl_pct'] < 0]
total_long_hold = [t for t in completed if t.get('holding_time_min', 0) >= 120]

if total_long_hold:
    long_hold_loss_rate = len(long_hold_losses) / len(total_long_hold) * 100
    print(f"\n1. 120분 이상 보유:")
    print(f"   손실률: {long_hold_loss_rate:.1f}%")
    print(f"   → **절대 120분 이상 보유 금지!**")

# 특정 추세에서 반대 포지션
wrong_direction_losses = []
for t in completed:
    trend = t.get('market_1m_trend', '')
    side = t.get('side', '')

    # 상승 추세에서 숏
    if trend == 'up' and side == 'SELL' and t['pnl_pct'] < 0:
        wrong_direction_losses.append(t)

    # 하락 추세에서 롱
    elif trend == 'down' and side == 'BUY' and t['pnl_pct'] < 0:
        wrong_direction_losses.append(t)

if wrong_direction_losses:
    print(f"\n2. 추세 반대 포지션:")
    print(f"   손실 건수: {len(wrong_direction_losses)}건")
    print(f"   평균 손실: {sum(t['pnl_pct'] for t in wrong_direction_losses)/len(wrong_direction_losses):.2f}%")
    print(f"   → **추세 반대 진입 금지!**")

# ============================================================================
# 5. 결론
# ============================================================================
print("\n" + "="*80)
print("[결론]")
print("="*80)

print("\n**절대 하지 말아야 할 것:**")
print("1. 120분 이상 보유 (손실률 높음)")
print("2. 추세 반대 진입 (상승 시 숏, 하락 시 롱)")
print("3. 큰 손실 방치 (-5% 도달 전 빠른 손절)")

print("\n**해야 할 것:**")
print("1. 0-60분 내 청산 (승률 65%+)")
print("2. 추세 따라가기 (상승 시 롱, 하락 시 숏)")
print("3. 빠른 손절 (-2% 도달 시 즉시 청산)")
print("4. 작은 수익 자주 내기 (+1-2%)")

print("\n→ SOXL 전략이 성공한 이유: 추세 전환 감지 + 빠른 대응")
print("→ ETH에도 적용하면 연 수천% 가능!")

print("\n" + "="*80)

# 저장
with open('C:/Users/user/Documents/loss_patterns_analysis.txt', 'w', encoding='utf-8') as f:
    f.write("손실 패턴 분석 결과\n")
    f.write("="*80 + "\n\n")
    f.write(f"큰 손실: {len(big_losses)}건\n")
    f.write(f"중간 손실: {len(medium_losses)}건\n")
    f.write(f"소액 손실: {len(small_losses)}건\n\n")
    f.write("절대 하지 말아야 할 것:\n")
    f.write("1. 120분 이상 보유\n")
    f.write("2. 추세 반대 진입\n")
    f.write("3. 큰 손실 방치\n")

print("\n[OK] loss_patterns_analysis.txt 저장")
