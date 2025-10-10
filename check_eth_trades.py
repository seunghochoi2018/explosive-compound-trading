import json

# ETH 거래 히스토리 확인
with open(r'C:\Users\user\Documents\코드3\eth_trade_history.json', 'r', encoding='utf-8') as f:
    trades = json.load(f)

print(f"총 거래: {len(trades)}건")
print("\n최근 5건:")
for i, trade in enumerate(trades[-5:], 1):
    print(f"\n{i}. [{trade.get('timestamp', 'N/A')}]")
    print(f"   방향: {trade.get('side', 'N/A')}")
    print(f"   진입: ${trade.get('entry_price', 0):.2f}")
    print(f"   청산: ${trade.get('exit_price', 0):.2f}")
    print(f"   PNL: {trade.get('pnl_pct', 0):.2f}%")
    print(f"   이유: {trade.get('exit_reason', 'N/A')}")
