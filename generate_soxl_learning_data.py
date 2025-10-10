#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SOXL/SOXS 백테스팅으로 학습 데이터 생성
- FMP API로 과거 1년 데이터 불러오기
- 추세 돌파 전략 시뮬레이션
- kis_trade_history.json과 kis_meta_insights.json 생성
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict

# FMP API 설정
FMP_API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"
FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"

def fetch_historical_data(symbol: str, days: int = 365) -> List[Dict]:
    """FMP API로 과거 데이터 불러오기"""
    print(f"\n[데이터 수집] {symbol} 최근 {days}일")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    url = f"{FMP_BASE_URL}/historical-price-full/{symbol}"
    params = {
        "apikey": FMP_API_KEY,
        "from": start_date.strftime('%Y-%m-%d'),
        "to": end_date.strftime('%Y-%m-%d')
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            historical = data.get('historical', [])
            print(f"  [OK] {len(historical)}개 데이터 수집 완료")
            return historical
        else:
            print(f"  [ERROR] 오류: {response.status_code}")
            return []
    except Exception as e:
        print(f"  [ERROR] 예외: {e}")
        return []

def simulate_trades(soxl_data: List[Dict], soxs_data: List[Dict]) -> tuple:
    """
    간단한 추세 전환 전략으로 시뮬레이션

    전략:
    - 단기 MA > 장기 MA: SOXL 보유
    - 단기 MA < 장기 MA: SOXS 보유
    - 전환 시마다 거래 기록
    """
    print("\n[백테스팅 시작]")

    # 데이터를 날짜 기준으로 정렬
    soxl_data = sorted(soxl_data, key=lambda x: x['date'])
    soxs_data = sorted(soxs_data, key=lambda x: x['date'])

    trades = []
    current_position = None
    entry_price = 0
    entry_time = None

    ma_short_period = 5  # 단기 이동평균
    ma_long_period = 10  # 장기 이동평균

    for i in range(ma_long_period, len(soxl_data)):
        date = soxl_data[i]['date']

        # SOXL 이동평균 계산
        soxl_prices = [soxl_data[j]['close'] for j in range(i - ma_long_period, i)]
        soxl_ma_short = sum(soxl_prices[-ma_short_period:]) / ma_short_period
        soxl_ma_long = sum(soxl_prices) / ma_long_period
        soxl_price = soxl_data[i]['close']

        # SOXS 이동평균 계산
        soxs_prices = [soxs_data[j]['close'] for j in range(i - ma_long_period, i)]
        soxs_price = soxs_data[i]['close']

        # 신호 판단
        signal = 'BULL' if soxl_ma_short > soxl_ma_long else 'BEAR'
        target_position = 'SOXL' if signal == 'BULL' else 'SOXS'

        # 포지션 전환
        if current_position != target_position:
            # 이전 포지션 청산
            if current_position:
                exit_price = soxl_price if current_position == 'SOXL' else soxs_price
                pnl_pct = ((exit_price - entry_price) / entry_price * 100)

                # 거래 기록
                trades.append({
                    'symbol': current_position,
                    'action': 'SELL',
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct,
                    'entry_time': entry_time,
                    'exit_time': date,
                    'signal': signal,
                    'result': 'WIN' if pnl_pct > 0 else 'LOSS'
                })

            # 새 포지션 진입
            current_position = target_position
            entry_price = soxl_price if target_position == 'SOXL' else soxs_price
            entry_time = date

            trades.append({
                'symbol': current_position,
                'action': 'BUY',
                'price': entry_price,
                'time': entry_time,
                'signal': signal
            })

    print(f"  [OK] {len(trades)}개 거래 시뮬레이션 완료")
    return trades, None

def generate_meta_insights(trades: List[Dict]) -> List[Dict]:
    """거래 결과로부터 메타 인사이트 생성"""
    print("\n[메타 인사이트 생성]")

    # 완료된 거래만 (SELL)
    completed_trades = [t for t in trades if t.get('action') == 'SELL']

    if not completed_trades:
        return []

    # 통계 계산
    wins = [t for t in completed_trades if t['result'] == 'WIN']
    losses = [t for t in completed_trades if t['result'] == 'LOSS']

    total_trades = len(completed_trades)
    win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0
    avg_win = sum(t['pnl_pct'] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t['pnl_pct'] for t in losses) / len(losses) if losses else 0

    insights = [
        {
            'type': 'BACKTEST_SUMMARY',
            'total_trades': total_trades,
            'wins': len(wins),
            'losses': len(losses),
            'win_rate_pct': win_rate,
            'avg_win_pct': avg_win,
            'avg_loss_pct': avg_loss,
            'generated': datetime.now().isoformat()
        },
        {
            'type': 'OPTIMAL_TIMING_PATTERN',
            'patterns': {
                'avg_win': f"{avg_win:.2f}%",
                'avg_loss': f"{avg_loss:.2f}%"
            },
            'recommendation': f"평균 수익 {avg_win:.2f}%, 평균 손실 {avg_loss:.2f}%",
            'learning_note': f"백테스팅 {total_trades}건 기반, 승률 {win_rate:.1f}%"
        }
    ]

    print(f"  [OK] 메타 인사이트 생성 완료")
    print(f"    총 거래: {total_trades}건")
    print(f"    승률: {win_rate:.1f}%")
    print(f"    평균 수익: {avg_win:+.2f}%")
    print(f"    평균 손실: {avg_loss:+.2f}%")

    return insights

def main():
    """메인 실행"""
    print("="*80)
    print("SOXL/SOXS 학습 데이터 생성기")
    print("="*80)

    # 1. 과거 데이터 수집
    soxl_data = fetch_historical_data('SOXL', days=365)
    soxs_data = fetch_historical_data('SOXS', days=365)

    if not soxl_data or not soxs_data:
        print("\n[ERROR] 데이터 수집 실패")
        return

    # 2. 백테스팅
    trades, _ = simulate_trades(soxl_data, soxs_data)

    # 3. 메타 인사이트 생성
    meta_insights = generate_meta_insights(trades)

    # 4. 파일 저장
    print("\n[파일 저장]")

    with open('kis_trade_history.json', 'w', encoding='utf-8') as f:
        json.dump(trades, f, indent=2, ensure_ascii=False)
    print(f"  [OK] kis_trade_history.json 저장 ({len(trades)}건)")

    with open('kis_meta_insights.json', 'w', encoding='utf-8') as f:
        json.dump(meta_insights, f, indent=2, ensure_ascii=False)
    print(f"  [OK] kis_meta_insights.json 저장 ({len(meta_insights)}건)")

    print("\n" + "="*80)
    print("[COMPLETE] 학습 데이터 생성 완료!")
    print("="*80)
    print("\n이제 kis_llm_learner_with_telegram.py를 실행하세요.")

if __name__ == "__main__":
    main()
