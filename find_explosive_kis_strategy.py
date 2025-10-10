#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS 복리 폭발 전략 재탐색
- 더 공격적인 파라미터 조합
- ETH처럼 빠른 회전율
- 수익률 극대화
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict

FMP_API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"
FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"

print("="*80)
print("KIS 복리 폭발 전략 재탐색")
print("="*80)

# 1. 기존 결과 로드
print("\n[기존 최고 전략]")
with open('kis_meta_insights.json', 'r', encoding='utf-8') as f:
    meta = json.load(f)
    best = meta[0]['strategy']
    print(f"  보유: {best['holding_days']}일")
    print(f"  익절: +{best['take_profit']}%")
    print(f"  손절: {best['stop_loss']}%")
    print(f"  승률: {best['win_rate']:.1f}%")
    print(f"  복리: {best['compound']:+.1f}%")

print("\n[문제점]")
print("  - 복리 +529%는 ETH 대비 너무 낮음")
print("  - 보유 2일은 회전율이 낮음")
print("  - 익절 +1%는 너무 보수적")

print("\n[해결책 탐색]")
print("  1. 더 빠른 회전: 보유 시간을 시간 단위로")
print("  2. 더 큰 목표: 익절 +3-5%")
print("  3. 타이트한 손절: -0.5%")
print("  4. SOXL 전용 (SOXS 제외)")

# ============================================================================
# 분봉/시간봉 데이터 수집
# ============================================================================

def fetch_intraday_data(symbol: str, interval: str = '15min') -> List[Dict]:
    """FMP API로 15분봉 데이터 수집 (최근 5일)"""
    print(f"\n[데이터 수집] {symbol} {interval} 봉 (최근 5일)")

    url = f"{FMP_BASE_URL}/historical-chart/{interval}/{symbol}"
    params = {"apikey": FMP_API_KEY}

    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            # 시간 순 정렬
            data = sorted(data, key=lambda x: x['date'])
            print(f"  [OK] {len(data)}개 데이터")
            return data
        else:
            print(f"  [ERROR] HTTP {response.status_code}")
            return []
    except Exception as e:
        print(f"  [ERROR] {e}")
        return []

# ============================================================================
# 공격적 전략 백테스트
# ============================================================================

def backtest_aggressive_strategies(data: List[Dict]) -> List[Dict]:
    """
    공격적 전략 조합:
    - 보유: 15분, 30분, 1시간, 2시간, 4시간
    - 익절: +0.5%, +1%, +2%, +3%, +5%
    - 손절: -0.3%, -0.5%, -1%
    """
    print(f"\n[백테스트] 공격적 전략 조합")

    # 파라미터 (캔들 수로 변환)
    holding_candles = [1, 2, 4, 8, 16]  # 15분봉 기준: 15분~4시간
    take_profits = [0.5, 1.0, 2.0, 3.0, 5.0]
    stop_losses = [-0.3, -0.5, -1.0]

    results = []
    total = len(holding_candles) * len(take_profits) * len(stop_losses)
    count = 0

    for holding in holding_candles:
        for tp in take_profits:
            for sl in stop_losses:
                count += 1
                trades = simulate_soxl_only(data, holding, tp, sl)

                if trades:
                    completed = [t for t in trades if t.get('action') == 'SELL']
                    if completed and len(completed) >= 10:  # 최소 10건
                        wins = [t for t in completed if t['result'] == 'WIN']
                        win_rate = len(wins) / len(completed) * 100
                        avg_pnl = sum(t['pnl_pct'] for t in completed) / len(completed)

                        # 복리 계산
                        balance = 1000.0
                        for t in completed:
                            balance = balance * (1 + t['pnl_pct'] / 100)
                        compound = (balance / 1000.0 - 1) * 100

                        results.append({
                            'holding_min': holding * 15,  # 15분봉 기준
                            'take_profit': tp,
                            'stop_loss': sl,
                            'trades': len(completed),
                            'win_rate': win_rate,
                            'avg_pnl': avg_pnl,
                            'compound': compound
                        })

                if count % 10 == 0:
                    print(f"    진행: {count}/{total}")

    print(f"  [OK] {len(results)}개 전략 백테스트 완료")
    return results

def simulate_soxl_only(data: List[Dict],
                       holding_candles: int,
                       take_profit: float,
                       stop_loss: float) -> List[Dict]:
    """SOXL 전용 롱 전략"""
    trades = []
    position = False
    entry_price = 0
    entry_idx = 0

    for i in range(len(data)):
        current = data[i]
        current_price = current['close']

        # 포지션 없으면 무조건 진입 (항상 롱)
        if not position:
            position = True
            entry_price = current_price
            entry_idx = i
            trades.append({
                'symbol': 'SOXL',
                'action': 'BUY',
                'price': entry_price,
                'time': current['date'],
                'signal': 'BULL'
            })

        # 포지션 있으면 청산 조건 체크
        else:
            pnl_pct = (current_price - entry_price) / entry_price * 100
            candles_held = i - entry_idx

            should_exit = False
            reason = ""

            if pnl_pct >= take_profit:
                should_exit = True
                reason = "TAKE_PROFIT"
            elif pnl_pct <= stop_loss:
                should_exit = True
                reason = "STOP_LOSS"
            elif candles_held >= holding_candles:
                should_exit = True
                reason = "TIME_LIMIT"

            if should_exit:
                trades.append({
                    'symbol': 'SOXL',
                    'action': 'SELL',
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'entry_time': data[entry_idx]['date'],
                    'exit_time': current['date'],
                    'pnl_pct': pnl_pct,
                    'result': 'WIN' if pnl_pct > 0 else 'LOSS',
                    'reason': reason
                })

                # 즉시 재진입
                position = True
                entry_price = current_price
                entry_idx = i
                trades.append({
                    'symbol': 'SOXL',
                    'action': 'BUY',
                    'price': entry_price,
                    'time': current['date'],
                    'signal': 'BULL'
                })

    return trades

# ============================================================================
# 메인 실행
# ============================================================================

def main():
    # 15분봉 데이터 수집
    soxl_data = fetch_intraday_data('SOXL', '15min')

    if not soxl_data or len(soxl_data) < 100:
        print("\n[ERROR] 데이터 부족")
        return

    # 공격적 전략 백테스트
    results = backtest_aggressive_strategies(soxl_data)

    if not results:
        print("\n[ERROR] 백테스트 실패")
        return

    # 정렬: 복리 높은 순
    results.sort(key=lambda x: x['compound'], reverse=True)

    print("\n" + "="*80)
    print("[TOP 15] 복리 폭발 전략")
    print("="*80)

    for i, r in enumerate(results[:15], 1):
        holding_str = f"{r['holding_min']}분" if r['holding_min'] < 60 else f"{r['holding_min']//60}시간"
        print(f"\n{i}. 보유{holding_str} 익절+{r['take_profit']}% 손절{r['stop_loss']}%")
        print(f"   거래{r['trades']}건, 승률{r['win_rate']:.1f}%, 평균{r['avg_pnl']:+.3f}%")
        print(f"   [***] 복리: {r['compound']:+.1f}%")

    # 최고 전략 비교
    if results:
        best = results[0]
        print("\n" + "="*80)
        print("[비교]")
        print("="*80)
        print(f"\n기존 전략 (일봉):")
        print(f"  보유 2일, 익절 +1%, 손절 -1%")
        print(f"  복리: +529.8%")

        holding_str = f"{best['holding_min']}분" if best['holding_min'] < 60 else f"{best['holding_min']//60}시간"
        print(f"\n신규 전략 (15분봉):")
        print(f"  보유 {holding_str}, 익절 +{best['take_profit']}%, 손절 {best['stop_loss']}%")
        print(f"  복리: {best['compound']:+.1f}%")

        if best['compound'] > 529.8:
            print(f"\n[***] 신규 전략이 {best['compound'] - 529.8:+.1f}%p 더 높습니다!")
            print("      이 전략을 적용하시겠습니까?")
        else:
            print(f"\n[WARNING] 신규 전략이 {529.8 - best['compound']:+.1f}%p 더 낮습니다.")
            print("          일봉 전략을 유지하는 것이 좋습니다.")

        print("="*80)

        # 저장
        with open('kis_aggressive_strategy.json', 'w', encoding='utf-8') as f:
            json.dump({
                'best_strategy': best,
                'top_15': results[:15],
                'generated': datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
        print("\n[OK] kis_aggressive_strategy.json 저장")

if __name__ == "__main__":
    main()
