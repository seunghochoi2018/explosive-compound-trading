#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
긴급 모니터링 & 손절 시스템
- 통합 매니저와 독립 실행
- 포지션 실시간 감시
- 손절선 초과 시 자동 청산
- 시스템 다운 감지
"""
import os
import sys
import time
import json
import requests
from datetime import datetime
from termcolor import colored

# ===== 설정 =====
EMERGENCY_STOP_LOSS = -5.0  # 긴급 손절: -5%
CRITICAL_STOP_LOSS = -10.0  # 강제 청산: -10%
CHECK_INTERVAL = 30  # 30초마다 체크
TELEGRAM_TOKEN = "YOUR_TOKEN"  # 텔레그램 토큰 설정 필요
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

# 파일 경로
ETH_CONFIG = "../코드3/bybit_config.json"
KIS_CONFIG = "../코드/kis_devlp.yaml"
KIS_TOKEN = "../코드4/kis_token.json"

def send_telegram(message):
    """텔레그램 알림"""
    try:
        if TELEGRAM_TOKEN == "YOUR_TOKEN":
            return  # 토큰 미설정
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
        requests.post(url, data=data, timeout=5)
    except Exception as e:
        print(f"텔레그램 전송 실패: {e}")

def check_eth_position():
    """ETH 포지션 체크"""
    try:
        sys.path.insert(0, '../코드3')
        from config import API_KEY, API_SECRET
        import ccxt

        exchange = ccxt.bybit({'apiKey': API_KEY, 'secret': API_SECRET})
        positions = exchange.fetch_positions(['ETH/USDT:USDT'])

        for pos in positions:
            contracts = float(pos.get('contracts', 0))
            if contracts != 0:
                pnl_pct = pos.get('percentage', 0)
                unrealized_pnl = pos.get('unrealizedPnl', 0)
                entry_price = pos.get('entryPrice', 0)
                mark_price = pos.get('markPrice', 0)
                side = pos['side']

                return {
                    'exchange': 'Bybit',
                    'symbol': 'ETH/USDT',
                    'side': side,
                    'size': contracts,
                    'entry_price': entry_price,
                    'current_price': mark_price,
                    'pnl_pct': pnl_pct,
                    'pnl_usd': unrealized_pnl
                }
        return None
    except Exception as e:
        print(colored(f"[ETH] 체크 실패: {e}", "red"))
        return None

def check_kis_position():
    """KIS 포지션 체크"""
    try:
        import yaml

        with open(KIS_CONFIG, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        with open(KIS_TOKEN, 'r') as f:
            token = json.load(f)['access_token']

        account_no = config['my_acct']
        url = 'https://openapi.koreainvestment.com:9443/uapi/overseas-stock/v1/trading/inquire-balance'

        headers = {
            'authorization': f'Bearer {token}',
            'appkey': config['my_app'],
            'appsecret': config['my_sec'],
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
            for stock in data.get('output1', []):
                qty = int(stock.get('ovrs_cblc_qty', 0))
                if qty > 0:
                    symbol = stock.get('ovrs_pdno')
                    pnl_pct = float(stock.get('evlu_pfls_rt', 0))
                    current_price = float(stock.get('now_pric2', 0))
                    entry_price = float(stock.get('pchs_avg_pric', 0))

                    return {
                        'exchange': 'KIS',
                        'symbol': symbol,
                        'side': 'LONG',
                        'size': qty,
                        'entry_price': entry_price,
                        'current_price': current_price,
                        'pnl_pct': pnl_pct,
                        'pnl_usd': float(stock.get('frcr_evlu_pfls_amt', 0))
                    }
        return None
    except Exception as e:
        print(colored(f"[KIS] 체크 실패: {e}", "red"))
        return None

def emergency_close_eth(position):
    """ETH 긴급 청산"""
    try:
        sys.path.insert(0, '../코드3')
        from config import API_KEY, API_SECRET
        import ccxt

        exchange = ccxt.bybit({'apiKey': API_KEY, 'secret': API_SECRET})

        side = 'sell' if position['side'] == 'long' else 'buy'

        order = exchange.create_market_order(
            symbol='ETH/USDT:USDT',
            side=side,
            amount=abs(position['size']),
            params={'reduce_only': True}
        )

        msg = f" <b>ETH 긴급 청산 완료</b>\n\n"
        msg += f"손익률: {position['pnl_pct']:.2f}%\n"
        msg += f"손익: ${position['pnl_usd']:.2f}\n"
        msg += f"사유: 손절선 초과"

        send_telegram(msg)
        return True
    except Exception as e:
        print(colored(f"[ETH] 청산 실패: {e}", "red"))
        send_telegram(f" ETH 청산 실패: {e}")
        return False

def main():
    """메인 모니터링 루프"""
    print(colored("="*70, "cyan"))
    print(colored("긴급 모니터링 & 손절 시스템 시작", "cyan"))
    print(colored(f"손절선: {EMERGENCY_STOP_LOSS}% / 강제청산: {CRITICAL_STOP_LOSS}%", "yellow"))
    print(colored(f"체크 주기: {CHECK_INTERVAL}초", "yellow"))
    print(colored("="*70, "cyan"))

    send_telegram(" <b>긴급 모니터 시작</b>\n\n손절 시스템 활성화")

    while True:
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{timestamp}] 포지션 체크...")

            # ETH 체크
            eth_pos = check_eth_position()
            if eth_pos:
                pnl = eth_pos['pnl_pct']
                status_color = "green" if pnl >= 0 else "red"

                print(colored(f"  ETH: {eth_pos['side']} {eth_pos['size']}개 | "
                             f"진입 ${eth_pos['entry_price']:.2f} → ${eth_pos['current_price']:.2f} | "
                             f"손익 {pnl:+.2f}% (${eth_pos['pnl_usd']:+.2f})", status_color))

                # 긴급 손절 체크
                if pnl <= CRITICAL_STOP_LOSS:
                    print(colored(f"\n 강제 청산 실행! (손실 {pnl:.2f}%)", "red"))
                    emergency_close_eth(eth_pos)
                elif pnl <= EMERGENCY_STOP_LOSS:
                    msg = f" <b>ETH 손절 경고</b>\n\n현재 손익: {pnl:.2f}%\n손절선 근접!"
                    send_telegram(msg)
                    print(colored(f"  손절 경고! 현재 {pnl:.2f}%", "yellow"))
            else:
                print(colored("  ETH: 포지션 없음", "white"))

            # KIS 체크
            kis_pos = check_kis_position()
            if kis_pos:
                pnl = kis_pos['pnl_pct']
                status_color = "green" if pnl >= 0 else "red"

                print(colored(f"  KIS: {kis_pos['symbol']} {kis_pos['size']}주 | "
                             f"진입 ${kis_pos['entry_price']:.2f} → ${kis_pos['current_price']:.2f} | "
                             f"손익 {pnl:+.2f}% (${kis_pos['pnl_usd']:+.2f})", status_color))

                # 경고만 (KIS 긴급 청산은 수동)
                if pnl <= CRITICAL_STOP_LOSS:
                    msg = f" <b>KIS 강제청산 필요!</b>\n\n"
                    msg += f"종목: {kis_pos['symbol']}\n"
                    msg += f"손익: {pnl:.2f}%\n"
                    msg += f"즉시 HTS/MTS에서 수동 청산 필요!"
                    send_telegram(msg)
                    print(colored(f" KIS 강제청산 필요! {pnl:.2f}%", "red"))
                elif pnl <= EMERGENCY_STOP_LOSS:
                    msg = f" <b>KIS 손절 경고</b>\n\n종목: {kis_pos['symbol']}\n현재 손익: {pnl:.2f}%"
                    send_telegram(msg)
                    print(colored(f"  KIS 손절 경고! {pnl:.2f}%", "yellow"))
            else:
                print(colored("  KIS: 포지션 없음", "white"))

            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print(colored("\n\n모니터 종료", "yellow"))
            send_telegram(" 긴급 모니터 종료")
            break
        except Exception as e:
            print(colored(f"에러: {e}", "red"))
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
