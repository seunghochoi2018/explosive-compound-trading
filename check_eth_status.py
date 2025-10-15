#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from pathlib import Path
from datetime import datetime

print("="*80)
print("ETH 트레이더 상태 확인")
print("="*80)

# 1. 거래 통계
trade_file = Path(r'C:\Users\user\Documents\코드3\eth_trade_history.json')
if trade_file.exists():
    with open(trade_file, 'r', encoding='utf-8') as f:
        trades = json.load(f)

    total = len(trades)
    recent = trades[-20:]
    wins = [t for t in recent if t.get('balance_change', 0) > 0]
    losses = [t for t in recent if t.get('balance_change', 0) <= 0]

    total_change = sum(t.get('balance_change', 0) for t in recent)

    print(f"\n[거래 통계]")
    print(f"전체 거래: {total}건")
    print(f"최근 20거래: 승={len(wins)}건, 패={len(losses)}건")
    print(f"최근 승률: {len(wins)/20*100:.1f}%")
    print(f"최근 잔고 변화: {total_change:+.6f} ETH")
else:
    print(f"\n[ERROR] 거래 기록 없음: {trade_file}")

# 2. 학습 반영 상태
events_file = Path(r'C:\Users\user\Documents\코드3\eth_learning_events.json')
if events_file.exists():
    with open(events_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    recent_events = []
    for line in lines[-10:]:
        if line.strip():
            try:
                recent_events.append(json.loads(line))
            except:
                pass

    default_count = 0
    for e in recent_events:
        if (e.get('7b_buy') == 50 and
            e.get('7b_sell') == 50 and
            e.get('7b_confidence') == 50):
            default_count += 1

    print(f"\n[학습 상태]")
    print(f"최근 LLM 호출: {len(recent_events)}회")
    print(f"기본값(50:50:50) 반환: {default_count}/10회")

    if default_count >= 7:
        print(f"상태: ❌ 학습 미반영 (LLM 우회 모드)")
    else:
        print(f"상태: ✅ 학습 작동 중")

    # 최근 이벤트 상세
    if recent_events:
        last = recent_events[-1]
        print(f"\n[최근 신호]")
        print(f"시간: {last.get('timestamp', 'N/A')}")
        print(f"7b - BUY:{last.get('7b_buy')}, SELL:{last.get('7b_sell')}, CONF:{last.get('7b_confidence')}")
else:
    print(f"\n[ERROR] 학습 이벤트 없음: {events_file}")

# 3. 프로세스 상태
import psutil
eth_running = False
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmdline = proc.info.get('cmdline', [])
        if cmdline and any('llm_eth_trader' in str(arg) for arg in cmdline):
            eth_running = True
            print(f"\n[프로세스]")
            print(f"상태: ✅ 실행 중 (PID: {proc.info['pid']})")
            break
    except:
        pass

if not eth_running:
    print(f"\n[프로세스]")
    print(f"상태: ❌ 중지됨")

print("="*80)
