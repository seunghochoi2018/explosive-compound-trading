import requests
import json
from datetime import datetime

print('='*70)
print('SYSTEM PRE-CHECK')
print('='*70)

# 1. Ollama 11436 LLM call test
print('\n1. Ollama 11436 LLM Test')
try:
    response = requests.post(
        'http://127.0.0.1:11436/api/generate',
        json={'model': 'deepseek-coder-v2:16b', 'prompt': 'Hello', 'stream': False},
        timeout=15
    )
    if response.status_code == 200:
        result = response.json()
        print(f'   OK: LLM response received ({len(result.get("response", ""))} chars)')
    else:
        print(f'   FAIL: HTTP {response.status_code}')
except Exception as e:
    print(f'   ERROR: {e}')

# 2. KIS trader status
print('\n2. KIS Trader Status')
try:
    with open(r'C:\Users\user\Documents\코드4\kis_trade_history.json', 'r', encoding='utf-8') as f:
        kis_trades = json.load(f)
    print(f'   OK: {len(kis_trades)} trades')
    if kis_trades:
        latest = kis_trades[-1]
        print(f'   Latest: {latest.get("timestamp", "?")}')
except FileNotFoundError:
    print('   FAIL: Trade history file not found')
except Exception as e:
    print(f'   ERROR: {e}')

# 3. ETH trader status
print('\n3. ETH Trader Status')
try:
    with open(r'C:\Users\user\Documents\코드3\eth_trade_history.json', 'r', encoding='utf-8') as f:
        eth_trades = json.load(f)
    print(f'   OK: {len(eth_trades)} trades')
    if eth_trades:
        latest = eth_trades[-1]
        print(f'   Latest: {latest.get("timestamp", "?")}')
except FileNotFoundError:
    print('   FAIL: Trade history file not found')
except Exception as e:
    print(f'   ERROR: {e}')

# 4. FMP API test (SOXL 90-day)
print('\n4. FMP API Test (SOXL 90-day)')
try:
    from datetime import timedelta
    url = 'https://financialmodelingprep.com/api/v3/historical-chart/1hour/SOXL?apikey=5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI'
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        data = response.json()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        filtered = [c for c in data if datetime.fromisoformat(c['date'].replace('Z', '+00:00')) >= start_date]
        print(f'   OK: {len(filtered)} candles (90 days)')
        if len(filtered) >= 50:
            print(f'   PASS: Sufficient data for learning')
        else:
            print(f'   FAIL: Insufficient data ({len(filtered)} < 50)')
    else:
        print(f'   FAIL: HTTP {response.status_code}')
except Exception as e:
    print(f'   ERROR: {e}')

# 5. Learning insights status
print('\n5. Learning Insights Status')
try:
    import os
    eth_exists = os.path.exists(r'C:\Users\user\Documents\코드3\eth_learning_insights.json')
    kis_exists = os.path.exists(r'C:\Users\user\Documents\코드4\kis_learning_insights.json')
    print(f'   ETH insights: {"EXISTS" if eth_exists else "NOT FOUND (waiting for first session)"}')
    print(f'   KIS insights: {"EXISTS" if kis_exists else "NOT FOUND (waiting for first session)"}')
except Exception as e:
    print(f'   ERROR: {e}')

print('\n' + '='*70)
print('PRE-CHECK COMPLETE')
print('='*70)
