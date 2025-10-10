#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합 포지션 실시간 모니터링 & 텔레그램 알림
- 30초마다 Bybit ETH + KIS 포지션 체크
- 거래 발생 시 즉시 텔레그램 알림
- 손익률 실시간 추적
"""
import os
import sys
import time
import requests
import yaml
import json
import hmac
import hashlib
from datetime import datetime

# 텔레그램 설정 (api_config에서 가져오기)
sys.path.insert(0, '../코드3')
from api_config import TELEGRAM_CONFIG, BYBIT_CONFIG

TELEGRAM_TOKEN = TELEGRAM_CONFIG['token']
TELEGRAM_CHAT_ID = TELEGRAM_CONFIG['chat_id']

# Bybit 설정
BYBIT_API_KEY = BYBIT_CONFIG['api_key']
BYBIT_API_SECRET = BYBIT_CONFIG['api_secret']
BYBIT_BASE_URL = 'https://api.bybit.com'

# KIS 설정
with open('../코드/kis_devlp.yaml', 'r', encoding='utf-8') as f:
    KIS_CONFIG = yaml.safe_load(f)

# 모니터링 설정
CHECK_INTERVAL = 30  # 30초마다 체크
ALERT_LOSS_THRESHOLD = -3.5  # -3.5% 손실 시 경고
CRITICAL_LOSS_THRESHOLD = -7.0  # -7% 손실 시 긴급 알림

last_position = None
last_alert_time = {}

def send_telegram(message):
    """텔레그램 메시지 전송"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, data=data, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"텔레그램 전송 실패: {e}")
        return False

def get_kis_token():
    """KIS 토큰 가져오기"""
    try:
        with open('kis_token.json', 'r') as f:
            return json.load(f)['access_token']
    except:
        return None

def check_bybit_position():
    """Bybit ETH 포지션 조회"""
    try:
        timestamp = str(int(time.time() * 1000))
        recv_window = '5000'

        # 쿼리 파라미터
        params = {
            'category': 'linear',
            'symbol': 'ETHUSDT',
            'settleCoin': 'USDT'
        }
        query_string = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])

        # V5 서명: timestamp + api_key + recv_window + queryString
        sign_str = timestamp + BYBIT_API_KEY + recv_window + query_string
        signature = hmac.new(
            BYBIT_API_SECRET.encode('utf-8'),
            sign_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        headers = {
            'X-BAPI-API-KEY': BYBIT_API_KEY,
            'X-BAPI-SIGN': signature,
            'X-BAPI-SIGN-TYPE': '2',
            'X-BAPI-TIMESTAMP': timestamp,
            'X-BAPI-RECV-WINDOW': recv_window
        }

        url = f'{BYBIT_BASE_URL}/v5/position/list?{query_string}'
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()

        if data.get('retCode') == 0:
            positions = []
            for pos in data.get('result', {}).get('list', []):
                size = float(pos.get('size', 0))
                if size > 0:
                    entry_price = float(pos.get('avgPrice', 0))
                    mark_price = float(pos.get('markPrice', 0))
                    unrealized_pnl = float(pos.get('unrealisedPnl', 0))

                    if entry_price > 0:
                        pnl_pct = ((mark_price - entry_price) / entry_price) * 100
                    else:
                        pnl_pct = 0

                    positions.append({
                        'symbol': 'ETH',
                        'size': size,
                        'entry_price': entry_price,
                        'current_price': mark_price,
                        'pnl_pct': pnl_pct,
                        'pnl_usd': unrealized_pnl,
                        'side': pos.get('side'),
                        'leverage': pos.get('leverage')
                    })
            return positions if positions else None
        else:
            print(f"Bybit API 오류: {data.get('retMsg')}")
            return None

    except Exception as e:
        print(f"Bybit 포지션 체크 실패: {e}")
        return None

def check_kis_position():
    """KIS 포지션 조회"""
    try:
        token = get_kis_token()
        if not token:
            return None

        account_no = KIS_CONFIG['my_acct']
        url = 'https://openapi.koreainvestment.com:9443/uapi/overseas-stock/v1/trading/inquire-balance'

        headers = {
            'authorization': f'Bearer {token}',
            'appkey': KIS_CONFIG['my_app'],
            'appsecret': KIS_CONFIG['my_sec'],
            'tr_id': 'TTTS3012R'
        }

        params = {
            'CANO': account_no.split('-')[0],
            'ACNT_PRDT_CD': account_no.split('-')[1],
            'OVRS_EXCG_CD': 'NASD',
            'TR_CRCY_CD': 'USD',
            'CTX_AREA_FK200': '',
            'CTX_AREA_NK200': ''
        }

        r = requests.get(url, headers=headers, params=params, timeout=10)
        data = r.json()

        if data.get('rt_cd') == '0':
            positions = []
            for stock in data.get('output1', []):
                qty = int(stock.get('ovrs_cblc_qty', 0))
                if qty > 0:
                    positions.append({
                        'symbol': stock.get('ovrs_pdno'),
                        'name': stock.get('ovrs_item_name', ''),
                        'qty': qty,
                        'entry_price': float(stock.get('pchs_avg_pric', 0)),
                        'current_price': float(stock.get('now_pric2', 0)),
                        'pnl_pct': float(stock.get('evlu_pfls_rt', 0)),
                        'pnl_usd': float(stock.get('frcr_evlu_pfls_amt', 0)),
                        'total_value': float(stock.get('ovrs_stck_evlu_amt', 0))
                    })
            return positions if positions else None
        else:
            print(f"API 오류: {data.get('msg1')}")
            return None

    except Exception as e:
        print(f"포지션 체크 실패: {e}")
        return None

def format_position_message(bybit_positions, kis_positions):
    """포지션 정보를 텔레그램 메시지로 포맷"""
    if not bybit_positions and not kis_positions:
        return None

    msg = "📊 <b>통합 포지션 현황</b>\n\n"

    # Bybit ETH 포지션
    if bybit_positions:
        msg += "🔷 <b>Bybit ETH</b>\n"
        for pos in bybit_positions:
            pnl_emoji = "🟢" if pos['pnl_pct'] >= 0 else "🔴"
            pnl_sign = "+" if pos['pnl_pct'] >= 0 else ""

            side_emoji = "📈" if pos['side'] == 'Buy' else "📉"
            msg += f"{side_emoji} {pnl_emoji} <b>{pos['symbol']}</b> x{pos['leverage']}\n"
            msg += f"수량: {pos['size']} ETH\n"
            msg += f"진입: ${pos['entry_price']:.2f} → ${pos['current_price']:.2f}\n"
            msg += f"손익: {pnl_sign}{pos['pnl_pct']:.2f}% (${pos['pnl_usd']:+.2f})\n\n"

    # KIS 주식 포지션
    if kis_positions:
        msg += "🔶 <b>KIS 주식</b>\n"
        for pos in kis_positions:
            pnl_emoji = "🟢" if pos['pnl_pct'] >= 0 else "🔴"
            pnl_sign = "+" if pos['pnl_pct'] >= 0 else ""

            msg += f"{pnl_emoji} <b>{pos['symbol']}</b>\n"
            msg += f"수량: {pos['qty']}주\n"
            msg += f"진입: ${pos['entry_price']:.2f} → ${pos['current_price']:.2f}\n"
            msg += f"손익: {pnl_sign}{pos['pnl_pct']:.2f}% (${pos['pnl_usd']:+.2f})\n"
            msg += f"평가액: ${pos['total_value']:.2f}\n\n"

    msg += f"⏰ {datetime.now().strftime('%H:%M:%S')}"
    return msg

def main():
    """메인 모니터링 루프"""
    global last_position, last_alert_time

    print("="*60)
    print("통합 포지션 모니터 시작 (Bybit ETH + KIS)")
    print(f"체크 주기: {CHECK_INTERVAL}초")
    print(f"손절 경고: {ALERT_LOSS_THRESHOLD}%")
    print(f"긴급 알림: {CRITICAL_LOSS_THRESHOLD}%")
    print("="*60)

    # 시작 알림
    send_telegram("🛡️ <b>통합 포지션 모니터 시작</b>\n\nBybit ETH + KIS 주식\n30초마다 체크 중...")

    last_bybit_position = None
    last_kis_position = None

    while True:
        try:
            current_time = time.time()
            timestamp = datetime.now().strftime("%H:%M:%S")

            # 두 거래소 포지션 체크
            bybit_positions = check_bybit_position()
            kis_positions = check_kis_position()

            has_positions = bybit_positions or kis_positions

            if has_positions:
                total_count = (len(bybit_positions) if bybit_positions else 0) + \
                              (len(kis_positions) if kis_positions else 0)
                print(f"\n[{timestamp}] 포지션 감지: 총 {total_count}개")

                # Bybit 포지션 처리
                if bybit_positions:
                    for pos in bybit_positions:
                        print(f"  [Bybit] {pos['symbol']}: {pos['size']} ETH | "
                              f"${pos['entry_price']:.2f} → ${pos['current_price']:.2f} | "
                              f"{pos['pnl_pct']:+.2f}% (${pos['pnl_usd']:+.2f})")

                # KIS 포지션 처리
                if kis_positions:
                    for pos in kis_positions:
                        print(f"  [KIS] {pos['symbol']}: {pos['qty']}주 | "
                              f"${pos['entry_price']:.2f} → ${pos['current_price']:.2f} | "
                              f"{pos['pnl_pct']:+.2f}% (${pos['pnl_usd']:+.2f})")

                # 포지션 변경 감지
                bybit_changed = (
                    last_bybit_position is None and bybit_positions is not None or
                    last_bybit_position is not None and bybit_positions is None or
                    (bybit_positions and last_bybit_position and
                     (len(bybit_positions) != len(last_bybit_position) or
                      any(p['size'] != lp['size'] for p, lp in zip(bybit_positions, last_bybit_position))))
                )

                kis_changed = (
                    last_kis_position is None and kis_positions is not None or
                    last_kis_position is not None and kis_positions is None or
                    (kis_positions and last_kis_position and
                     (len(kis_positions) != len(last_kis_position) or
                      any(p['qty'] != lp['qty'] or p['symbol'] != lp['symbol']
                          for p, lp in zip(kis_positions, last_kis_position))))
                )

                # 거래 발생 시 즉시 알림
                if bybit_changed or kis_changed:
                    msg = format_position_message(bybit_positions, kis_positions)
                    if msg:
                        send_telegram(msg)
                        print(f"  📱 텔레그램 알림 전송 (포지션 변경)")

                # 손실 경고 체크
                all_positions = []
                if bybit_positions:
                    all_positions.extend([(p, 'Bybit') for p in bybit_positions])
                if kis_positions:
                    all_positions.extend([(p, 'KIS') for p in kis_positions])

                for pos, exchange in all_positions:
                    symbol = pos['symbol']
                    pnl = pos['pnl_pct']
                    alert_key = f"{exchange}_{symbol}_loss"

                    if pnl <= CRITICAL_LOSS_THRESHOLD:
                        if alert_key not in last_alert_time or (current_time - last_alert_time[alert_key]) > 1800:  # 30분마다
                            msg = f"🚨 <b>긴급! [{exchange}] {symbol} 큰 손실</b>\n\n"
                            msg += f"손익: {pnl:.2f}%\n"
                            msg += f"손실: ${pos['pnl_usd']:.2f}\n"
                            msg += f"진입: ${pos['entry_price']:.2f} → ${pos['current_price']:.2f}\n\n"
                            msg += f"⚠️ 즉시 확인 필요!"
                            send_telegram(msg)
                            last_alert_time[alert_key] = current_time
                            print(f"  🚨 긴급 알림 전송! [{exchange}] {symbol}")

                    elif pnl <= ALERT_LOSS_THRESHOLD:
                        if alert_key not in last_alert_time or (current_time - last_alert_time[alert_key]) > 3600:  # 1시간마다
                            msg = f"⚠️ <b>[{exchange}] {symbol} 손절선 근접</b>\n\n"
                            msg += f"손익: {pnl:.2f}%\n"
                            msg += f"손실: ${pos['pnl_usd']:.2f}"
                            send_telegram(msg)
                            last_alert_time[alert_key] = current_time
                            print(f"  ⚠️  손절 경고 전송 [{exchange}] {symbol}")

                last_bybit_position = bybit_positions
                last_kis_position = kis_positions

            else:
                if last_bybit_position is not None or last_kis_position is not None:
                    # 포지션 청산됨
                    send_telegram("✅ <b>모든 포지션 청산 완료</b>\n\nBybit ETH + KIS 주식 모두 정리되었습니다.")
                    print(f"[{timestamp}] ✅ 포지션 청산")
                    last_bybit_position = None
                    last_kis_position = None
                else:
                    print(f"[{timestamp}] 포지션 없음")

            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print("\n\n모니터 종료")
            send_telegram("🛡️ 통합 포지션 모니터 종료")
            break
        except Exception as e:
            print(f"에러: {e}")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
