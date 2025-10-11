#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
포지션 모니터링 애드온 (통합 매니저에 추가할 코드)
"""

# ===== 설정에 추가할 내용 =====
POSITION_CHECK_INTERVAL = 30  # 30초마다 포지션 체크
EMERGENCY_STOP_LOSS = -5.0  # 긴급 손절: -5%
CRITICAL_STOP_LOSS = -10.0  # 강제 청산 경고: -10%

last_position_check = 0
last_position_alert = {}  # 중복 알림 방지

# ===== 포지션 체크 함수 =====
def check_eth_position_realtime():
    """ETH 포지션 실시간 체크"""
    try:
        import sys
        sys.path.insert(0, '../코드3')
        from api_config import BYBIT_CONFIG
        import ccxt

        exchange = ccxt.bybit({
            'apiKey': BYBIT_CONFIG['api_key'],
            'secret': BYBIT_CONFIG['api_secret']
        })

        positions = exchange.fetch_positions(['ETH/USDT:USDT'])

        for pos in positions:
            contracts = float(pos.get('contracts', 0))
            if contracts != 0:
                pnl_pct = pos.get('percentage', 0)
                unrealized_pnl = pos.get('unrealizedPnl', 0)
                side = pos['side']
                entry_price = pos.get('entryPrice', 0)
                mark_price = pos.get('markPrice', 0)

                return {
                    'active': True,
                    'side': side,
                    'size': contracts,
                    'entry': entry_price,
                    'current': mark_price,
                    'pnl_pct': pnl_pct,
                    'pnl_usd': unrealized_pnl,
                    'alert_level': 'critical' if pnl_pct <= CRITICAL_STOP_LOSS else 'warning' if pnl_pct <= EMERGENCY_STOP_LOSS else 'normal'
                }

        return {'active': False}
    except Exception as e:
        return {'active': False, 'error': str(e)}

def check_kis_position_realtime():
    """KIS 포지션 실시간 체크"""
    try:
        import yaml
        import json
        import requests

        with open('../코드/kis_devlp.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        with open('../코드4/kis_token.json', 'r') as f:
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
                    pnl_usd = float(stock.get('frcr_evlu_pfls_amt', 0))

                    return {
                        'active': True,
                        'symbol': symbol,
                        'size': qty,
                        'entry': entry_price,
                        'current': current_price,
                        'pnl_pct': pnl_pct,
                        'pnl_usd': pnl_usd,
                        'alert_level': 'critical' if pnl_pct <= CRITICAL_STOP_LOSS else 'warning' if pnl_pct <= EMERGENCY_STOP_LOSS else 'normal'
                    }

        return {'active': False}
    except Exception as e:
        return {'active': False, 'error': str(e)}

# ===== 메인 루프에 추가할 코드 =====
"""
#  실시간 포지션 모니터링 (30초마다)
if (current_time - last_position_check) >= POSITION_CHECK_INTERVAL:
    # ETH 포지션 체크
    eth_pos = check_eth_position_realtime()
    if eth_pos['active']:
        pnl = eth_pos['pnl_pct']

        # 긴급 상황 텔레그램 알림 (중복 방지)
        alert_key = f"ETH_{eth_pos['alert_level']}"
        if eth_pos['alert_level'] == 'critical' and alert_key not in last_position_alert:
            msg = f" <b>ETH 강제청산 경고!</b>\n\n"
            msg += f"손익: {pnl:.2f}%\n"
            msg += f"손실: ${eth_pos['pnl_usd']:.2f}\n"
            msg += f"진입: ${eth_pos['entry']:.2f} → ${eth_pos['current']:.2f}\n\n"
            msg += f" 즉시 확인 필요!"
            telegram.send_message(msg)
            last_position_alert[alert_key] = current_time
            colored_print(f" [ETH] 강제청산 경고! 손실 {pnl:.2f}%", "red")

        elif eth_pos['alert_level'] == 'warning' and alert_key not in last_position_alert:
            msg = f" <b>ETH 손절 경고</b>\n\n"
            msg += f"손익: {pnl:.2f}%\n"
            msg += f"손실: ${eth_pos['pnl_usd']:.2f}\n"
            msg += f"손절선 근접 중"
            telegram.send_message(msg)
            last_position_alert[alert_key] = current_time
            colored_print(f"  [ETH] 손절 경고! {pnl:.2f}%", "yellow")

        # 정상 상태로 복귀 시 알림 리셋
        if eth_pos['alert_level'] == 'normal':
            last_position_alert = {k: v for k, v in last_position_alert.items() if not k.startswith('ETH_')}

    # KIS 포지션 체크
    kis_pos = check_kis_position_realtime()
    if kis_pos['active']:
        pnl = kis_pos['pnl_pct']

        alert_key = f"KIS_{kis_pos['symbol']}_{kis_pos['alert_level']}"
        if kis_pos['alert_level'] == 'critical' and alert_key not in last_position_alert:
            msg = f" <b>KIS 강제청산 필요!</b>\n\n"
            msg += f"종목: {kis_pos['symbol']}\n"
            msg += f"손익: {pnl:.2f}%\n"
            msg += f"손실: ${kis_pos['pnl_usd']:.2f}\n\n"
            msg += f" HTS/MTS에서 수동 청산 필요!"
            telegram.send_message(msg)
            last_position_alert[alert_key] = current_time
            colored_print(f" [KIS] 강제청산 필요! {kis_pos['symbol']} {pnl:.2f}%", "red")

        elif kis_pos['alert_level'] == 'warning' and alert_key not in last_position_alert:
            msg = f" <b>KIS 손절 경고</b>\n\n"
            msg += f"종목: {kis_pos['symbol']}\n"
            msg += f"손익: {pnl:.2f}%"
            telegram.send_message(msg)
            last_position_alert[alert_key] = current_time
            colored_print(f"  [KIS] 손절 경고! {kis_pos['symbol']} {pnl:.2f}%", "yellow")

        if kis_pos['alert_level'] == 'normal':
            last_position_alert = {k: v for k, v in last_position_alert.items() if not k.startswith(f"KIS_{kis_pos['symbol']}_")}

    # 알림 만료 (1시간 후 재알림 가능)
    last_position_alert = {k: v for k, v in last_position_alert.items() if (current_time - v) < 3600}

    last_position_check = current_time
"""
