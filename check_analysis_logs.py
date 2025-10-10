# -*- coding: utf-8 -*-
"""15분 분석이 실행됐는지 확인"""
import json
from datetime import datetime

print("=" * 70)
print("15-MINUTE ANALYSIS CHECK")
print("=" * 70)

# ETH 학습 인사이트
print("\n[ETH Learning Insights]")
try:
    with open(r'C:\Users\user\Documents\코드3\eth_learning_insights.json', 'r', encoding='utf-8') as f:
        eth_insights = json.load(f)
    print(f"  Total sessions: {len(eth_insights)}")
    if eth_insights:
        latest = eth_insights[-1]
        print(f"  Latest: {latest.get('timestamp', 'N/A')}")
        print(f"  Strategies: {len(latest.get('strategies', []))}")
        print(f"  Applied: {len(latest.get('applied', []))}")
except FileNotFoundError:
    print("  [NOT FOUND] File does not exist yet")
    print("  Reason: 15-min self-improvement analysis not executed yet")
except Exception as e:
    print(f"  [ERROR] {e}")

# KIS 학습 인사이트
print("\n[KIS Learning Insights]")
try:
    with open(r'C:\Users\user\Documents\코드4\kis_learning_insights.json', 'r', encoding='utf-8') as f:
        kis_insights = json.load(f)
    print(f"  Total sessions: {len(kis_insights)}")
    if kis_insights:
        latest = kis_insights[-1]
        print(f"  Latest: {latest.get('timestamp', 'N/A')}")
        print(f"  Strategies: {len(latest.get('strategies', []))}")
        print(f"  Applied: {len(latest.get('applied', []))}")

        # 검증 상태
        validation = latest.get('validation_status', {})
        if validation:
            print(f"  Validation status:")
            for strategy, count in validation.items():
                status = "READY" if count >= 3 else f"{count}/3"
                print(f"    - {strategy}: {status}")
except FileNotFoundError:
    print("  [NOT FOUND] File does not exist")
except Exception as e:
    print(f"  [ERROR] {e}")

# 예상 분석 시간
print("\n[Expected Analysis Times]")
import psutil
for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
    try:
        if 'python' in proc.info['name'].lower():
            cmdline = proc.info.get('cmdline', [])
            if cmdline and 'unified_trader_manager.py' in ' '.join(cmdline):
                start = datetime.fromtimestamp(proc.info['create_time'])
                elapsed_min = (datetime.now() - start).total_seconds() / 60

                print(f"  Manager started: {start.strftime('%H:%M:%S')}")
                print(f"  Elapsed: {elapsed_min:.1f} minutes")
                print(f"  Expected analysis count: {int(elapsed_min / 15)}")

                # 분석 예상 시간
                for i in range(1, int(elapsed_min / 15) + 2):
                    analysis_time = start.timestamp() + (i * 15 * 60)
                    dt = datetime.fromtimestamp(analysis_time)
                    status = "DONE" if (datetime.now().timestamp() - analysis_time) > 0 else "PENDING"
                    print(f"  Analysis #{i}: {dt.strftime('%H:%M:%S')} [{status}]")
                break
    except:
        pass

print("\n" + "=" * 70)
