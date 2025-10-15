#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETH 잔고 손실 위기 분석
"""
import json
from datetime import datetime

# 거래 데이터 로드
with open(r'C:\Users\user\Documents\코드3\eth_trade_history.json', 'r', encoding='utf-8') as f:
    trades = json.load(f)

print("="*80)
print("ETH 거래 분석 - 잔고 손실 위기")
print("="*80)

# 전체 통계
total = len(trades)
wins = [t for t in trades if t.get('balance_change', 0) > 0]
losses = [t for t in trades if t.get('balance_change', 0) <= 0]

print(f"\n전체 거래: {total}건")
print(f"승리: {len(wins)}건 ({len(wins)/total*100:.1f}%)")
print(f"손실: {len(losses)}건 ({len(losses)/total*100:.1f}%)")

# 최근 20건 분석
recent_20 = trades[-20:]
recent_wins = [t for t in recent_20 if t.get('balance_change', 0) > 0]
recent_losses = [t for t in recent_20 if t.get('balance_change', 0) <= 0]

print(f"\n최근 20건:")
print(f"승리: {len(recent_wins)}건 ({len(recent_wins)/20*100:.1f}%)")
print(f"손실: {len(recent_losses)}건 ({len(recent_losses)/20*100:.1f}%)")

# 잔고 추이
print(f"\n잔고 추이:")
print(f"시작 (20건 전): {recent_20[0]['balance_before']:.6f} ETH")
print(f"현재: {recent_20[-1]['balance_after']:.6f} ETH")
total_change = recent_20[-1]['balance_after'] - recent_20[0]['balance_before']
print(f"변화: {total_change:+.6f} ETH ({total_change/recent_20[0]['balance_before']*100:+.1f}%)")

# 손실 원인 분석
print(f"\n손실 원인 분석 (최근 20건):")
stop_losses = [t for t in recent_20 if 'STOP_LOSS' in t.get('reason', '')]
trend_changes = [t for t in recent_20 if 'TREND_CHANGE' in t.get('reason', '')]
max_time = [t for t in recent_20 if 'MAX_TIME' in t.get('reason', '')]

print(f"손절 (STOP_LOSS): {len(stop_losses)}건")
print(f"추세 전환: {len(trend_changes)}건")
print(f"최대 보유시간: {len(max_time)}건")

# 손절 상세
print(f"\n손절 상세 분석:")
for t in stop_losses:
    pnl = t.get('pnl_pct', 0)
    balance_change = t.get('balance_change', 0)
    holding_sec = t.get('holding_time_sec', 0)
    print(f"  {t['timestamp'][:19]} | {t['side']:4s} | PNL:{pnl:+6.2f}% | 보유:{holding_sec:.0f}초 | 잔고변화:{balance_change:+.6f} ETH")

# 추세 전환 상세
print(f"\n추세 전환 상세 분석:")
for t in trend_changes:
    pnl = t.get('pnl_pct', 0)
    balance_change = t.get('balance_change', 0)
    holding_sec = t.get('holding_time_sec', 0)
    print(f"  {t['timestamp'][:19]} | {t['side']:4s} | PNL:{pnl:+6.2f}% | 보유:{holding_sec:.0f}초 | 잔고변화:{balance_change:+.6f} ETH")

# 평균 보유 시간
avg_holding = sum(t.get('holding_time_sec', 0) for t in recent_20) / len(recent_20)
print(f"\n평균 보유 시간: {avg_holding:.0f}초 ({avg_holding/60:.1f}분)")

# 최악의 거래 5건
print(f"\n최악의 거래 5건:")
worst_5 = sorted(recent_20, key=lambda x: x.get('balance_change', 0))[:5]
for t in worst_5:
    pnl = t.get('pnl_pct', 0)
    balance_change = t.get('balance_change', 0)
    reason = t.get('reason', '')
    print(f"  {t['timestamp'][:19]} | {t['side']:4s} | PNL:{pnl:+6.2f}% | 잔고:{balance_change:+.6f} ETH | {reason}")

print("\n" + "="*80)
