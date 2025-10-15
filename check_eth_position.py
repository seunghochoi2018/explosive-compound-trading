#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys

try:
    with open(r'C:\Users\user\Documents\코드3\eth_trade_history.json', 'r', encoding='utf-8') as f:
        trades = json.load(f)

    if trades:
        last_trade = trades[-1]
        print(f"최근 거래 시간: {last_trade.get('timestamp', 'N/A')}")
        print(f"포지션: {last_trade.get('side', 'N/A')}")
        print(f"진입가: ${last_trade.get('entry_price', 0):.2f}")
        print(f"청산가: ${last_trade.get('exit_price', 0):.2f}")
        print(f"PNL: {last_trade.get('pnl_pct', 0):+.2f}%")
        print(f"보유시간: {last_trade.get('holding_time_sec', 0)/60:.0f}분")
        print(f"청산 이유: {last_trade.get('reason', 'N/A')}")
        print(f"\n총 거래: {len(trades)}건")

        # 최근 10개 거래 통계
        recent_10 = trades[-10:] if len(trades) >= 10 else trades
        wins = sum(1 for t in recent_10 if t.get('pnl_pct', 0) > 0)
        print(f"최근 10거래 승률: {wins}/10 ({wins*10}%)")
    else:
        print("거래 기록 없음")
except Exception as e:
    print(f"오류: {e}")
