# -*- coding: utf-8 -*-
import json
import os
from datetime import datetime
import psutil

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
print("   Monitor: Every 15min")
print("   Telegram: Every 6hr")
print("   Analysis: Every 15min")

# Time remaining calculation
try:
    import glob

    # Find unified_trader_manager process start time
    manager_start = None
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
        try:
            if 'python' in proc.info['name'].lower():
                cmdline = proc.info.get('cmdline', [])
                if cmdline and 'unified_trader_manager.py' in ' '.join(cmdline):
                    manager_start = proc.info['create_time']
                    break
        except:
            continue

    if manager_start:
        from datetime import datetime
        now = datetime.now().timestamp()
        elapsed_sec = now - manager_start

        # Calculate time until next analysis (15min interval)
        next_analysis_sec = 15 * 60 - (elapsed_sec % (15 * 60))
        next_analysis_min = next_analysis_sec / 60

        # Calculate time until next telegram (6hr interval)
        next_telegram_sec = 6 * 60 * 60 - (elapsed_sec % (6 * 60 * 60))
        next_telegram_hr = next_telegram_sec / 3600

        print("\n[Next Events]")
        print(f"   Next Analysis: {int(next_analysis_min)}min {int(next_analysis_sec % 60)}sec")
        print(f"   Next Telegram: {next_telegram_hr:.1f}hr")
    else:
        print("\n[Next Events]")
        print("   Manager not running")
except Exception as e:
    print(f"\n[Next Events] Error: {e}")

# Process check
print("\n[Process Status]")
python_count = sum(1 for p in psutil.process_iter(['name']) if 'python' in p.info['name'].lower())
print(f"   Python: {python_count} processes {'[OK]' if python_count == 3 else '[WARN]'}")

ollama_count = sum(1 for p in psutil.process_iter(['name']) if 'ollama' in p.info['name'].lower())
print(f"   Ollama: {ollama_count} processes {'[OK]' if ollama_count > 0 else '[FAIL]'}")

print("\n" + "=" * 70)
print(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)
