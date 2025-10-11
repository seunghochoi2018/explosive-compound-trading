#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""현재 포지션 확인"""
import json
import sys
import io
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("=" * 60)
print("현재 포지션 및 거래 상태 확인")
print("=" * 60)
print()

# ETH 거래 내역 확인
try:
    with open(r'C:\Users\user\Documents\코드3\eth_trade_history.json', 'r', encoding='utf-8') as f:
        eth_trades = json.load(f)
    print(f"[ETH] 총 거래 횟수: {len(eth_trades)}회")
    if eth_trades:
        last_trade = eth_trades[-1]
        print(f"[ETH] 마지막 거래: {last_trade.get('timestamp', 'N/A')}")
        print(f"[ETH] 마지막 액션: {last_trade.get('side', 'N/A')}")

        # 현재 포지션 추정 (마지막 거래가 BUY면 롱, SELL이면 포지션 없음)
        if last_trade.get('side') == 'BUY':
            print(f"[ETH] 예상 포지션: LONG (보유 중)")
        elif last_trade.get('side') == 'SELL':
            print(f"[ETH] 예상 포지션: NONE (청산 완료)")
        else:
            print(f"[ETH] 예상 포지션: 알 수 없음")
except Exception as e:
    print(f"[ETH] 거래 내역 확인 실패: {e}")

print()

# KIS 거래 내역 확인
try:
    with open(r'C:\Users\user\Documents\코드4\kis_trade_history.json', 'r', encoding='utf-8') as f:
        kis_trades = json.load(f)
    print(f"[KIS] 총 거래 횟수: {len(kis_trades)}회")
    if kis_trades:
        last_trade = kis_trades[-1]
        print(f"[KIS] 마지막 거래: {last_trade.get('timestamp', 'N/A')}")
        print(f"[KIS] 마지막 종목: {last_trade.get('symbol', 'N/A')}")
        print(f"[KIS] 마지막 액션: {last_trade.get('action', 'N/A')}")

        # 최근 10개 거래 확인
        recent_10 = kis_trades[-10:]
        soxl_count = sum(1 for t in recent_10 if t.get('symbol') == 'SOXL' and t.get('action') == 'BUY')
        soxs_count = sum(1 for t in recent_10 if t.get('symbol') == 'SOXS' and t.get('action') == 'BUY')
        print(f"[KIS] 최근 10개 중 SOXL 매수: {soxl_count}회, SOXS 매수: {soxs_count}회")
except Exception as e:
    print(f"[KIS] 거래 내역 확인 실패: {e}")

print()
print("=" * 60)
