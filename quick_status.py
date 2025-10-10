# -*- coding: utf-8 -*-
import json
import os
from datetime import datetime

print("=" * 70)
print("TRADING SYSTEM STATUS")
print("=" * 70)

# ETH Trader
print("\n[ETH Trader]")
try:
    with open(r'C:\Users\user\Documents\코드3\eth_trade_history.json', 'r', encoding='utf-8') as f:
        eth_trades = json.load(f)
    print(f"   Trades: {len(eth_trades)}")

    if eth_trades and 'timestamp' in eth_trades[-1]:
        latest = datetime.fromisoformat(eth_trades[-1]['timestamp'].replace('Z', '+00:00'))
        print(f"   Latest: {latest.strftime('%m/%d %H:%M')}")
    else:
        print(f"   Latest: N/A")
except:
    print("   [X] File not found")

try:
    with open(r'C:\Users\user\Documents\코드3\eth_learning_insights.json', 'r', encoding='utf-8') as f:
        eth_insights = json.load(f)
    print(f"   Learning: {len(eth_insights)} items")
except:
    print(f"   Learning: Waiting...")

# KIS Trader
print("\n[KIS Trader - SOXL/TQQQ]")
try:
    with open(r'C:\Users\user\Documents\코드4\kis_trade_history.json', 'r', encoding='utf-8') as f:
        kis_trades = json.load(f)
    print(f"   Trades: {len(kis_trades)}")

    if kis_trades and 'timestamp' in kis_trades[-1]:
        latest = datetime.fromisoformat(kis_trades[-1]['timestamp'].replace('Z', '+00:00'))
        print(f"   Latest: {latest.strftime('%m/%d %H:%M')}")
    else:
        print(f"   Latest: N/A")
except:
    print("   [X] File not found")

try:
    with open(r'C:\Users\user\Documents\코드4\kis_learning_insights.json', 'r', encoding='utf-8') as f:
        kis_insights = json.load(f)
    print(f"   Learning: {len(kis_insights)} items")
except:
    print(f"   Learning: Waiting...")

# System
print("\n[System Config]")
print("   Monitor: Every 30min")
print("   Telegram: Every 6hr")
print("   Analysis: Every 30min")

# Process check
print("\n[Process Status]")
import psutil
python_count = sum(1 for p in psutil.process_iter(['name']) if 'python' in p.info['name'].lower())
print(f"   Python: {python_count} processes {'[OK]' if python_count == 3 else '[WARN]'}")

ollama_count = sum(1 for p in psutil.process_iter(['name']) if 'ollama' in p.info['name'].lower())
print(f"   Ollama: {ollama_count} processes {'[OK]' if ollama_count > 0 else '[FAIL]'}")

print("\n" + "=" * 70)
print(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)
