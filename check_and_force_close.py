#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""포지션 확인 후 손절 조건이면 강제 청산"""
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import requests
import yaml
import json

# KIS 설정
with open('../코드/kis_devlp.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

app_key = config['my_app']
app_secret = config['my_sec']
account_no = config['my_acct']
base_url = "https://openapi.koreainvestment.com:9443"

# 토큰 로드
with open('kis_token.json', 'r', encoding='utf-8') as f:
    access_token = json.load(f)['access_token']

print("="*60)
print("포지션 확인 및 손절 조건 체크")
print("="*60)

# 거래 내역에서 진입가 확인
with open('kis_trade_history.json', 'r', encoding='utf-8') as f:
    trades = json.load(f)

last_buy = None
for t in reversed(trades):
    if t.get('action') == 'BUY' and t.get('symbol') == 'SOXL':
        last_buy = t
        break

if not last_buy:
    print("SOXL 매수 기록 없음")
    sys.exit(0)

entry_price = last_buy['price']
entry_date = last_buy['time']
print(f"\n마지막 SOXL 매수:")
print(f"  진입가: ${entry_price}")
print(f"  일자: {entry_date}")

# 현재 보유 확인
url = f"{base_url}/uapi/overseas-stock/v1/trading/inquire-balance"
headers = {
    "authorization": f"Bearer {access_token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": "TTTS3012R"
}
params = {
    "CANO": account_no.split('-')[0],
    "ACNT_PRDT_CD": account_no.split('-')[1],
    "OVRS_EXCG_CD": "NASD",
    "TR_CRCY_CD": "USD",
    "CTX_AREA_FK200": "",
    "CTX_AREA_NK200": ""
}

response = requests.get(url, headers=headers, params=params, timeout=10)
if response.status_code == 200:
    data = response.json()
    if data.get('rt_cd') == '0':
        for stock in data.get('output1', []):
            if stock.get('ovrs_pdno') == 'SOXL':
                qty = int(stock.get('ovrs_cblc_qty', 0))
                current_price = float(stock.get('now_pric2', 0))
                pnl_pct = float(stock.get('evlu_pfls_rt', 0))

                print(f"\n현재 포지션:")
                print(f"  수량: {qty}주")
                print(f"  현재가: ${current_price:.2f}")
                print(f"  손익률: {pnl_pct:.2f}%")

                # 손절 조건 체크 (SOXL 3배 레버리지 적용)
                price_change_pct = ((current_price - entry_price) / entry_price) * 100
                leveraged_pnl = price_change_pct * 3

                print(f"\n손익 계산:")
                print(f"  가격 변동: {price_change_pct:.2f}%")
                print(f"  3배 레버리지 손익: {leveraged_pnl:.2f}%")
                print(f"  손절선: -3.5%")

                if leveraged_pnl <= -3.5:
                    print(f"\n⚠️  손절 조건 충족! 즉시 청산 필요!")
                    print(f"매도 주문 전송 중...")

                    # 실전투자 매도
                    sell_url = f"{base_url}/uapi/overseas-stock/v1/trading/order"
                    sell_headers = {
                        "authorization": f"Bearer {access_token}",
                        "appkey": app_key,
                        "appsecret": app_secret,
                        "tr_id": "TTTT1006U"
                    }
                    # 시장가라도 현재가 입력 필수 (KIS API 특성)
                    sell_data = {
                        "CANO": account_no.split('-')[0],
                        "ACNT_PRDT_CD": account_no.split('-')[1],
                        "OVRS_EXCG_CD": "NASD",
                        "PDNO": "A980679",  # SOXL 정식 종목코드
                        "ORD_QTY": str(qty),
                        "OVRS_ORD_UNPR": str(current_price),  # 현재가 입력
                        "ORD_SVR_DVSN_CD": "0",
                        "ORD_DVSN": "00"
                    }

                    sell_resp = requests.post(sell_url, headers=sell_headers, json=sell_data, timeout=10)
                    print(f"Status: {sell_resp.status_code}")
                    print(f"Response: {sell_resp.text}")

                    if sell_resp.status_code == 200:
                        result = sell_resp.json()
                        if result.get('rt_cd') == '0':
                            print(f"\n✅ 청산 완료!")

                            # 거래 기록 업데이트
                            trades.append({
                                "symbol": "SOXL",
                                "action": "SELL",
                                "entry_price": entry_price,
                                "exit_price": current_price,
                                "entry_time": entry_date,
                                "exit_time": "2025-10-10",
                                "pnl_pct": leveraged_pnl,
                                "result": "LOSS",
                                "reason": "STOP_LOSS",
                                "signal": "EMERGENCY"
                            })

                            with open('kis_trade_history.json', 'w', encoding='utf-8') as f:
                                json.dump(trades, f, indent=2, ensure_ascii=False)

                            print("거래 기록 업데이트 완료")
                        else:
                            print(f"❌ 실패: {result.get('msg1')}")
                else:
                    print(f"\n✅ 손절선 미도달, 유지")

                break
        else:
            print("\nSOXL 보유 없음")
