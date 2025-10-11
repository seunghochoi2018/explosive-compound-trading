import requests
from datetime import datetime, timedelta

FMP_API_KEY = '5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI'
days = 90

# SOXL 1hour candle data (90 days)
url = f'https://financialmodelingprep.com/api/v3/historical-chart/1hour/SOXL?apikey={FMP_API_KEY}'

print(f'SOXL 1-hour candle data test (last {days} days)')
print(f'URL: {url}')
print()

response = requests.get(url, timeout=30)
print(f'HTTP Status: {response.status_code}')

if response.status_code == 200:
    data = response.json()
    print(f'Total candles: {len(data)}')

    # Filter last N days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    filtered_data = []
    for candle in data:
        try:
            candle_time = datetime.fromisoformat(candle['date'].replace('Z', '+00:00'))
            if candle_time >= start_date:
                filtered_data.append(candle)
        except:
            continue

    print(f'Filtered (last {days} days): {len(filtered_data)} candles')
    print()

    if len(filtered_data) >= 50:
        print(f'SUCCESS! Data sufficient ({len(filtered_data)} >= 50 minimum)')
    else:
        print(f'FAIL! Data insufficient ({len(filtered_data)} < 50 minimum)')

    print()
    print('Latest 3 candles:')
    for i, candle in enumerate(filtered_data[-3:]):
        print(f'  {i+1}. {candle["date"]} - Close: ${candle["close"]:.2f}')

else:
    print(f'API Error: HTTP {response.status_code}')
