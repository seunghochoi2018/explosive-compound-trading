# -*- coding: utf-8 -*-
"""
주기적으로 status.html을 생성하는 스크립트
브라우저에서 file:///C:/Users/user/Documents/코드5/status.html 열면 됨
"""
import json
import os
from datetime import datetime
import psutil
import time

def get_current_position_eth(trades):
    """ETH 현재 포지션 확인"""
    if not trades:
        return None

    # 최근 거래부터 역순으로 확인
    for trade in reversed(trades):
        action = trade.get('action', '')
        if action in ['LONG_ENTRY', 'SHORT_ENTRY', 'BUY', 'SELL']:
            # 진입 거래 발견
            return {
                'side': 'LONG' if 'LONG' in action or action == 'BUY' else 'SHORT',
                'entry_price': trade.get('entry_price', 0) or trade.get('price', 0),
                'timestamp': trade.get('timestamp', 'N/A'),
                'size': trade.get('size', 0)
            }
        elif action in ['LONG_EXIT', 'SHORT_EXIT', 'CLOSE']:
            # 청산 거래 발견 = 포지션 없음
            return None

    return None

def get_current_position_kis(trades):
    """KIS 현재 포지션 확인"""
    if not trades:
        return None

    # 최근 거래부터 역순으로 확인
    for trade in reversed(trades):
        action = trade.get('action', '')
        if action in ['BUY', 'LONG_ENTRY']:
            # 진입 거래 발견
            return {
                'side': 'LONG',
                'entry_price': trade.get('entry_price', 0) or trade.get('price', 0),
                'timestamp': trade.get('timestamp', 'N/A'),
                'symbol': trade.get('symbol', 'SOXL')
            }
        elif action in ['SELL', 'LONG_EXIT', 'CLOSE']:
            # 청산 거래 발견 = 포지션 없음
            return None

    return None

def get_current_price_eth():
    """ETH 현재가 조회 (Bybit)"""
    try:
        import requests
        response = requests.get('https://api.bybit.com/v5/market/tickers?category=linear&symbol=ETHUSDT', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('retCode') == 0:
                return float(data['result']['list'][0]['lastPrice'])
    except:
        pass
    return None

def get_current_price_kis(symbol='SOXL'):
    """KIS 현재가 조회 (FMP API)"""
    try:
        import requests
        response = requests.get(f'https://financialmodelingprep.com/api/v3/quote-short/{symbol}?apikey=5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                return float(data[0]['price'])
    except:
        pass
    return None

def generate_html():
    # 데이터 수집
    try:
        with open(r'C:\Users\user\Documents\코드3\eth_trade_history.json', 'r', encoding='utf-8') as f:
            eth_trades = json.load(f)
    except:
        eth_trades = []

    try:
        with open(r'C:\Users\user\Documents\코드4\kis_trade_history.json', 'r', encoding='utf-8') as f:
            kis_trades = json.load(f)
    except:
        kis_trades = []

    try:
        with open(r'C:\Users\user\Documents\코드3\eth_learning_insights.json', 'r', encoding='utf-8') as f:
            eth_insights = json.load(f)
    except:
        eth_insights = []

    try:
        with open(r'C:\Users\user\Documents\코드4\kis_learning_insights.json', 'r', encoding='utf-8') as f:
            kis_insights = json.load(f)
    except:
        kis_insights = []

    # 최근 10건 거래 (ETH)
    recent_eth = eth_trades[-10:] if len(eth_trades) > 10 else eth_trades
    eth_trades_html = ""
    for trade in reversed(recent_eth):
        profit = trade.get('profit_pct', 0)
        color = '#3fb950' if profit > 0 else '#f85149'
        eth_trades_html += f"""
        <div style="padding: 8px; border-bottom: 1px solid #21262d; display: flex; justify-content: space-between;">
            <span>{trade.get('timestamp', 'N/A')[:16]}</span>
            <span style="color: {color}; font-weight: bold;">{profit:+.2f}%</span>
        </div>
        """

    # 최근 10건 거래 (KIS)
    recent_kis = kis_trades[-10:] if len(kis_trades) > 10 else kis_trades
    kis_trades_html = ""
    for trade in reversed(recent_kis):
        profit = trade.get('profit_pct', 0)
        color = '#3fb950' if profit > 0 else '#f85149'
        kis_trades_html += f"""
        <div style="padding: 8px; border-bottom: 1px solid #21262d; display: flex; justify-content: space-between;">
            <span>{trade.get('timestamp', 'N/A')[:16] if trade.get('timestamp') else 'N/A'}</span>
            <span style="color: {color}; font-weight: bold;">{profit:+.2f}%</span>
        </div>
        """

    # 누적 손익 계산 (ETH)
    eth_total_profit = sum([t.get('profit_pct', 0) for t in eth_trades])
    eth_wins = len([t for t in eth_trades if t.get('profit_pct', 0) > 0])
    eth_win_rate = (eth_wins / len(eth_trades) * 100) if eth_trades else 0

    # 누적 손익 계산 (KIS)
    kis_total_profit = sum([t.get('profit_pct', 0) for t in kis_trades])
    kis_wins = len([t for t in kis_trades if t.get('profit_pct', 0) > 0])
    kis_win_rate = (kis_wins / len(kis_trades) * 100) if kis_trades else 0

    # 현재 포지션 및 미실현 손익 계산
    eth_position = get_current_position_eth(eth_trades)
    eth_current_price = get_current_price_eth()
    eth_unrealized_pnl = 0
    eth_position_html = '<div style="color: #8b949e; padding: 10px;">포지션 없음</div>'

    if eth_position and eth_current_price:
        entry_price = eth_position['entry_price']
        if entry_price > 0:
            if eth_position['side'] == 'LONG':
                eth_unrealized_pnl = ((eth_current_price - entry_price) / entry_price) * 100
            else:  # SHORT
                eth_unrealized_pnl = ((entry_price - eth_current_price) / entry_price) * 100

            pnl_color = '#3fb950' if eth_unrealized_pnl > 0 else '#f85149'
            eth_position_html = f"""
            <div style="padding: 15px; background: #0d1117; border-radius: 6px; border: 2px solid {pnl_color};">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="color: #8b949e;">포지션:</span>
                    <span style="color: #79c0ff; font-weight: bold;">{eth_position['side']}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="color: #8b949e;">진입가:</span>
                    <span style="color: #c9d1d9;">${entry_price:.2f}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="color: #8b949e;">현재가:</span>
                    <span style="color: #c9d1d9;">${eth_current_price:.2f}</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding-top: 8px; border-top: 1px solid #21262d;">
                    <span style="color: #8b949e;">미실현 손익:</span>
                    <span style="color: {pnl_color}; font-weight: bold; font-size: 18px;">{eth_unrealized_pnl:+.2f}%</span>
                </div>
            </div>
            """

    kis_position = get_current_position_kis(kis_trades)
    kis_current_price = get_current_price_kis()
    kis_unrealized_pnl = 0
    kis_position_html = '<div style="color: #8b949e; padding: 10px;">포지션 없음</div>'

    if kis_position and kis_current_price:
        entry_price = kis_position['entry_price']
        if entry_price > 0:
            kis_unrealized_pnl = ((kis_current_price - entry_price) / entry_price) * 100

            pnl_color = '#3fb950' if kis_unrealized_pnl > 0 else '#f85149'
            kis_position_html = f"""
            <div style="padding: 15px; background: #0d1117; border-radius: 6px; border: 2px solid {pnl_color};">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="color: #8b949e;">포지션:</span>
                    <span style="color: #79c0ff; font-weight: bold;">LONG {kis_position.get('symbol', 'SOXL')}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="color: #8b949e;">진입가:</span>
                    <span style="color: #c9d1d9;">${entry_price:.2f}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="color: #8b949e;">현재가:</span>
                    <span style="color: #c9d1d9;">${kis_current_price:.2f}</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding-top: 8px; border-top: 1px solid #21262d;">
                    <span style="color: #8b949e;">미실현 손익:</span>
                    <span style="color: {pnl_color}; font-weight: bold; font-size: 18px;">{kis_unrealized_pnl:+.2f}%</span>
                </div>
            </div>
            """

    # 최근 인사이트 (ETH)
    eth_insights_html = ""
    if not eth_insights:
        eth_insights_html = '<div style="color: #d29922; padding: 10px; background: #0d1117; border-radius: 6px; border: 1px solid #d29922;">⏳ 첫 학습 세션 대기 중 (15분 주기)</div>'
    else:
        for insight in eth_insights[-3:]:
            timestamp = insight.get('timestamp', 'N/A')[:16]
            strategies = insight.get('strategies', [])
            applied = insight.get('applied', [])
            validation_status = insight.get('validation_status', {})

            # 검증 상태 텍스트
            validation_text = ""
            if validation_status:
                pending = [f"{k}: {v}/3" for k, v in validation_status.items() if v < 3]
                if pending:
                    validation_text = f'<div style="color: #d29922; font-size: 11px; margin-top: 4px;"> 검증 중: {", ".join(pending[:2])}</div>'

            eth_insights_html += f"""
            <div style="padding: 8px; border-bottom: 1px solid #21262d;">
                <div style="color: #8b949e; font-size: 12px;">{timestamp}</div>
                <div style="color: #79c0ff;">발견: {len(strategies)}개 | 적용: {len(applied)}개</div>
                {validation_text}
            </div>
            """

    # 최근 인사이트 (KIS)
    kis_insights_html = ""
    if not kis_insights:
        kis_insights_html = '<div style="color: #d29922; padding: 10px; background: #0d1117; border-radius: 6px; border: 1px solid #d29922;">⏳ 첫 학습 세션 대기 중 (15분 주기)</div>'
    else:
        for insight in kis_insights[-3:]:
            timestamp = insight.get('timestamp', 'N/A')[:16]
            strategies = insight.get('strategies', [])
            applied = insight.get('applied', [])
            validation_status = insight.get('validation_status', {})

            # 검증 상태 텍스트
            validation_text = ""
            if validation_status:
                pending = [f"{k.replace('_', ' ')}: {v}/3" for k, v in validation_status.items() if v < 3]
                if pending:
                    validation_text = f'<div style="color: #d29922; font-size: 11px; margin-top: 4px;"> 검증 중: {", ".join(pending[:2])}</div>'

                # 검증 완료 항목
                completed = [f"{k.replace('_', ' ')}" for k, v in validation_status.items() if v >= 3]
                if completed:
                    validation_text += f'<div style="color: #3fb950; font-size: 11px; margin-top: 2px;"> 검증 완료: {", ".join(completed[:2])}</div>'

            kis_insights_html += f"""
            <div style="padding: 8px; border-bottom: 1px solid #21262d;">
                <div style="color: #8b949e; font-size: 12px;">{timestamp}</div>
                <div style="color: #79c0ff;">발견: {len(strategies)}개 | 적용: {len(applied)}개</div>
                {validation_text}
            </div>
            """

    # 다음 이벤트 계산
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
        now = datetime.now().timestamp()
        elapsed_sec = now - manager_start

        # 15분 주기
        next_analysis_sec = int(15 * 60 - (elapsed_sec % (15 * 60)))
        # 6시간 주기
        next_telegram_sec = int(6 * 60 * 60 - (elapsed_sec % (6 * 60 * 60)))

        countdown_js = f"""
        let nextAnalysis = {next_analysis_sec};
        let nextTelegram = {next_telegram_sec};
        """
    else:
        countdown_js = """
        let nextAnalysis = 0;
        let nextTelegram = 0;
        """

    # 프로세스 카운트
    python_count = sum(1 for p in psutil.process_iter(['name']) if 'python' in p.info['name'].lower())
    ollama_count = sum(1 for p in psutil.process_iter(['name']) if 'ollama' in p.info['name'].lower())

    # HTML 생성
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="10">
    <title>트레이딩 시스템 상태</title>
    <style>
        body {{
            font-family: 'Consolas', 'Courier New', monospace;
            background: #0d1117;
            color: #c9d1d9;
            padding: 20px;
            margin: 0;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            color: #58a6ff;
            border-bottom: 3px solid #58a6ff;
            padding-bottom: 15px;
            font-size: 28px;
        }}
        .status-box {{
            background: #161b22;
            border-left: 5px solid #238636;
            padding: 20px;
            margin: 20px 0;
            border-radius: 6px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }}
        .status-box h2 {{
            margin: 0 0 15px 0;
            color: #58a6ff;
            font-size: 20px;
        }}
        .metric {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #21262d;
        }}
        .metric:last-child {{
            border-bottom: none;
        }}
        .metric-label {{
            color: #8b949e;
            font-weight: 500;
        }}
        .metric-value {{
            color: #79c0ff;
            font-weight: bold;
        }}
        .ok {{ color: #3fb950 !important; }}
        .warn {{ color: #d29922 !important; }}
        .error {{ color: #f85149 !important; }}
        .countdown {{
            background: linear-gradient(135deg, #1f6feb 0%, #0969da 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            text-align: center;
            font-size: 24px;
            font-weight: bold;
            box-shadow: 0 6px 12px rgba(31, 111, 235, 0.4);
        }}
        .countdown-small {{
            font-size: 14px;
            margin-top: 8px;
            opacity: 0.9;
        }}
        .grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        .trade-list {{
            max-height: 300px;
            overflow-y: auto;
        }}
        .refresh-info {{
            text-align: center;
            color: #8b949e;
            margin-top: 30px;
            font-size: 13px;
            padding: 15px;
            background: #161b22;
            border-radius: 6px;
        }}
        @media (max-width: 768px) {{
            .grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1> 트레이딩 시스템 대시보드</h1>

        <div class="countdown">
            <div id="analysis-countdown">⏰ 다음 분석: 계산 중...</div>
            <div class="countdown-small" id="telegram-countdown">다음 텔레그램: 계산 중...</div>
        </div>

        <div class="grid">
            <!-- ETH Trader -->
            <div class="status-box">
                <h2> ETH Trader</h2>
                <div class="metric">
                    <span class="metric-label">총 거래</span>
                    <span class="metric-value ok">{len(eth_trades)}건</span>
                </div>
                <div class="metric">
                    <span class="metric-label">누적 수익률</span>
                    <span class="metric-value {'ok' if eth_total_profit > 0 else 'error'}">{eth_total_profit:+.2f}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">승률</span>
                    <span class="metric-value">{eth_win_rate:.1f}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">학습 세션</span>
                    <span class="metric-value">{len(eth_insights)}건</span>
                </div>

                <h3 style="color: #58a6ff; margin-top: 20px; font-size: 18px;">💼 현재 포지션</h3>
                {eth_position_html}

                <h3 style="color: #8b949e; margin-top: 20px; font-size: 16px;">최근 10건 거래</h3>
                <div class="trade-list">
                    {eth_trades_html if eth_trades_html else '<div style="color: #8b949e; padding: 10px;">거래 없음</div>'}
                </div>

                <h3 style="color: #8b949e; margin-top: 20px; font-size: 16px;">최근 학습 인사이트</h3>
                <div>
                    {eth_insights_html if eth_insights_html else '<div style="color: #8b949e; padding: 10px;">대기 중</div>'}
                </div>
            </div>

            <!-- KIS Trader -->
            <div class="status-box">
                <h2> KIS Trader (SOXL/TQQQ)</h2>
                <div class="metric">
                    <span class="metric-label">총 거래</span>
                    <span class="metric-value ok">{len(kis_trades)}건</span>
                </div>
                <div class="metric">
                    <span class="metric-label">누적 수익률</span>
                    <span class="metric-value {'ok' if kis_total_profit > 0 else 'error'}">{kis_total_profit:+.2f}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">승률</span>
                    <span class="metric-value">{kis_win_rate:.1f}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">학습 세션</span>
                    <span class="metric-value">{len(kis_insights)}건</span>
                </div>

                <h3 style="color: #58a6ff; margin-top: 20px; font-size: 18px;">💼 현재 포지션</h3>
                {kis_position_html}

                <h3 style="color: #8b949e; margin-top: 20px; font-size: 16px;">최근 10건 거래</h3>
                <div class="trade-list">
                    {kis_trades_html if kis_trades_html else '<div style="color: #8b949e; padding: 10px;">거래 없음</div>'}
                </div>

                <h3 style="color: #8b949e; margin-top: 20px; font-size: 16px;">최근 학습 인사이트</h3>
                <div>
                    {kis_insights_html if kis_insights_html else '<div style="color: #8b949e; padding: 10px;">대기 중</div>'}
                </div>
            </div>
        </div>

        <div class="status-box">
            <h2>⚙️ 시스템 설정</h2>
            <div class="metric">
                <span class="metric-label">거래 모니터링</span>
                <span class="metric-value">15분 주기</span>
            </div>
            <div class="metric">
                <span class="metric-label">자기개선 분석</span>
                <span class="metric-value">15분 주기 (Triple Validation)</span>
            </div>
            <div class="metric">
                <span class="metric-label">백그라운드 학습</span>
                <span class="metric-value">10분 주기 (FMP API)</span>
            </div>
            <div class="metric">
                <span class="metric-label">텔레그램 알림</span>
                <span class="metric-value">6시간 주기</span>
            </div>
        </div>

        <div class="status-box">
            <h2>🔧 프로세스 상태</h2>
            <div class="metric">
                <span class="metric-label">Python 프로세스</span>
                <span class="metric-value {'ok' if python_count == 3 else 'warn'}">{python_count}개 (예상: 3개)</span>
            </div>
            <div class="metric">
                <span class="metric-label">Ollama 프로세스</span>
                <span class="metric-value {'ok' if ollama_count > 0 else 'error'}">{ollama_count}개</span>
            </div>
            <div class="metric">
                <span class="metric-label">마지막 업데이트</span>
                <span class="metric-value">{datetime.now().strftime('%H:%M:%S')}</span>
            </div>
        </div>

        <div class="refresh-info">
            ✨ 자동 새로고침: 10초마다 | 수동: F5<br>
             파일 위치: C:\\Users\\user\\Documents\\코드5\\status.html
        </div>
    </div>

    <script>
        {countdown_js}

        function updateCountdown() {{
            if (nextAnalysis > 0) {{
                nextAnalysis--;
                const minutes = Math.floor(nextAnalysis / 60);
                const seconds = nextAnalysis % 60;
                document.getElementById('analysis-countdown').textContent =
                    `⏰ 다음 분석: ${{minutes}}분 ${{seconds}}초`;
            }}

            if (nextTelegram > 0) {{
                nextTelegram--;
                const hours = Math.floor(nextTelegram / 3600);
                const minutes = Math.floor((nextTelegram % 3600) / 60);
                document.getElementById('telegram-countdown').textContent =
                    `다음 텔레그램: ${{hours}}시간 ${{minutes}}분`;
            }}
        }}

        // 1초마다 카운트다운 업데이트
        setInterval(updateCountdown, 1000);
        updateCountdown(); // 즉시 실행
    </script>
</body>
</html>
"""

    # HTML 파일 저장
    with open(r'C:\Users\user\Documents\코드5\status.html', 'w', encoding='utf-8') as f:
        f.write(html)

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

    print("=" * 70)
    print("HTML Dashboard Generator")
    print("=" * 70)
    print("\nBrowser URL:")
    print("  file:///C:/Users/user/Documents/코드5/status.html")
    print("\nAuto-refresh: 10sec | Countdown: Real-time")
    print("Press Ctrl+C to stop\n")

    while True:
        try:
            generate_html()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] OK: HTML updated")
            time.sleep(10)
        except KeyboardInterrupt:
            print("\n\n종료됨")
            break
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ 오류: {e}")
            time.sleep(10)
