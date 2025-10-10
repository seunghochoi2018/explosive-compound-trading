#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SOXL/SOXS 궁극의 학습 데이터 생성기
- 1년치 실제 일봉 데이터 수집
- 모든 시간대/주기 조합 백테스트
- 지표 없이 순수 가격 패턴으로 학습
- 승률 70%+ 수익률 최대화 전략 발굴
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict
import itertools

# FMP API
FMP_API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"
FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"

print("="*80)
print("SOXL/SOXS 궁극의 학습 데이터 생성기")
print("- 1년치 실제 시장 데이터")
print("- 모든 전략 조합 테스트")
print("- 승률 70%+ 수익률 최대화")
print("="*80)

# ============================================================================
# 1단계: 실제 시장 데이터 수집
# ============================================================================

def fetch_daily_data(symbol: str, days: int = 365) -> List[Dict]:
    """FMP API로 실제 일봉 데이터 수집"""
    print(f"\n[1단계] {symbol} 실제 일봉 데이터 수집 (최근 {days}일)")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    url = f"{FMP_BASE_URL}/historical-price-full/{symbol}"
    params = {
        "apikey": FMP_API_KEY,
        "from": start_date.strftime('%Y-%m-%d'),
        "to": end_date.strftime('%Y-%m-%d')
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            historical = data.get('historical', [])
            # 시간 순 정렬
            historical = sorted(historical, key=lambda x: x['date'])
            print(f"  [OK] {len(historical)}일 데이터 수집 완료")
            return historical
        else:
            print(f"  [ERROR] HTTP {response.status_code}")
            return []
    except Exception as e:
        print(f"  [ERROR] {e}")
        return []

# ============================================================================
# 2단계: 순수 가격 패턴 분석 (지표 없이)
# ============================================================================

def analyze_pure_price_patterns(data: List[Dict]) -> Dict:
    """
    지표 없이 순수 가격 패턴 분석
    - 연속 상승/하락 일수
    - 변동성 (일일 변화율)
    - 캔들 패턴 (고가-저가 범위)
    """
    print(f"\n[2단계] 순수 가격 패턴 분석 (지표 없이)")

    patterns = []

    for i in range(1, len(data)):
        prev = data[i-1]
        curr = data[i]

        # 일일 수익률
        daily_return = (curr['close'] - prev['close']) / prev['close'] * 100

        # 일중 변동성
        intraday_volatility = (curr['high'] - curr['low']) / curr['open'] * 100

        # 캔들 바디 (종가 - 시가)
        body = (curr['close'] - curr['open']) / curr['open'] * 100

        # 상승/하락 방향
        direction = 'UP' if daily_return > 0 else 'DOWN'

        # 연속 상승/하락 계산
        consecutive = 1
        for j in range(i-1, 0, -1):
            prev_direction = 'UP' if data[j]['close'] > data[j-1]['close'] else 'DOWN'
            if prev_direction == direction:
                consecutive += 1
            else:
                break

        patterns.append({
            'date': curr['date'],
            'open': curr['open'],
            'high': curr['high'],
            'low': curr['low'],
            'close': curr['close'],
            'volume': curr['volume'],
            'daily_return': daily_return,
            'volatility': intraday_volatility,
            'body': body,
            'direction': direction,
            'consecutive_days': consecutive
        })

    print(f"  [OK] {len(patterns)}개 가격 패턴 분석 완료")
    return patterns

# ============================================================================
# 3단계: 모든 전략 조합 백테스트
# ============================================================================

def backtest_all_strategies(soxl_patterns: List[Dict], soxs_patterns: List[Dict]) -> List[Dict]:
    """
    모든 시간대/전략 조합으로 백테스트
    - 보유 기간: 1일, 2일, 3일, 5일, 7일, 10일, 15일
    - 익절: +1%, +2%, +3%, +5%, +7%, +10%, +15%, +20%
    - 손절: -0.5%, -1%, -2%, -3%, -5%
    - 전환 조건: 연속 상승/하락 N일
    """
    print(f"\n[3단계] 모든 전략 조합 백테스트")

    # 전략 파라미터 조합
    holding_days_list = [1, 2, 3, 5, 7, 10, 15]
    take_profits = [1, 2, 3, 5, 7, 10, 15, 20]
    stop_losses = [-0.5, -1, -2, -3, -5]
    consecutive_triggers = [2, 3, 4, 5]  # N일 연속 상승/하락 시 전환

    print(f"  총 조합 수: {len(holding_days_list) * len(take_profits) * len(stop_losses) * len(consecutive_triggers)}")

    all_results = []
    combo_count = 0

    for holding_days in holding_days_list:
        for tp in take_profits:
            for sl in stop_losses:
                for consec in consecutive_triggers:
                    combo_count += 1

                    # 백테스트 실행
                    trades = simulate_strategy(
                        soxl_patterns,
                        soxs_patterns,
                        holding_days=holding_days,
                        take_profit=tp,
                        stop_loss=sl,
                        consecutive_trigger=consec
                    )

                    # 결과 평가
                    if trades:
                        completed = [t for t in trades if t.get('action') == 'SELL']
                        if completed:
                            wins = [t for t in completed if t['result'] == 'WIN']
                            win_rate = len(wins) / len(completed) * 100
                            avg_pnl = sum(t['pnl_pct'] for t in completed) / len(completed)

                            # 복리 계산
                            balance = 1000.0
                            for t in completed:
                                balance = balance * (1 + t['pnl_pct'] / 100)
                            compound = (balance / 1000.0 - 1) * 100

                            all_results.append({
                                'holding_days': holding_days,
                                'take_profit': tp,
                                'stop_loss': sl,
                                'consecutive': consec,
                                'trades': len(completed),
                                'win_rate': win_rate,
                                'avg_pnl': avg_pnl,
                                'compound': compound
                            })

                    # 진행률 표시
                    if combo_count % 100 == 0:
                        print(f"    진행: {combo_count} 조합 테스트 완료...")

    print(f"  [OK] {len(all_results)}개 전략 백테스트 완료")
    return all_results

def simulate_strategy(soxl_patterns: List[Dict],
                     soxs_patterns: List[Dict],
                     holding_days: int,
                     take_profit: float,
                     stop_loss: float,
                     consecutive_trigger: int) -> List[Dict]:
    """
    특정 전략으로 시뮬레이션

    전략:
    1. 연속 N일 상승 → SOXL 진입
    2. 연속 N일 하락 → SOXS 진입
    3. 익절/손절/시간 도달 시 청산 후 반대 포지션
    """
    trades = []
    position = None  # 'SOXL' or 'SOXS'
    entry_price = 0
    entry_date = None
    entry_idx = 0

    for i in range(consecutive_trigger, len(soxl_patterns)):
        soxl = soxl_patterns[i]
        soxs = soxs_patterns[i] if i < len(soxs_patterns) else None

        if not soxs:
            continue

        # 포지션 없으면 진입 신호 체크
        if position is None:
            # SOXL 진입: 연속 상승
            if soxl['consecutive_days'] >= consecutive_trigger and soxl['direction'] == 'UP':
                position = 'SOXL'
                entry_price = soxl['close']
                entry_date = soxl['date']
                entry_idx = i
                trades.append({
                    'symbol': 'SOXL',
                    'action': 'BUY',
                    'price': entry_price,
                    'time': entry_date,
                    'signal': 'BULL'
                })

            # SOXS 진입: 연속 하락
            elif soxl['consecutive_days'] >= consecutive_trigger and soxl['direction'] == 'DOWN':
                position = 'SOXS'
                entry_price = soxs['close']
                entry_date = soxs['date']
                entry_idx = i
                trades.append({
                    'symbol': 'SOXS',
                    'action': 'BUY',
                    'price': entry_price,
                    'time': entry_date,
                    'signal': 'BEAR'
                })

        # 포지션 있으면 청산 조건 체크
        else:
            if position == 'SOXL':
                current_price = soxl['close']
                pnl_pct = (current_price - entry_price) / entry_price * 100
                days_held = i - entry_idx

                should_exit = False
                exit_reason = ""

                if pnl_pct >= take_profit:
                    should_exit = True
                    exit_reason = "TAKE_PROFIT"
                elif pnl_pct <= stop_loss:
                    should_exit = True
                    exit_reason = "STOP_LOSS"
                elif days_held >= holding_days:
                    should_exit = True
                    exit_reason = "TIME_LIMIT"
                elif soxl['consecutive_days'] >= consecutive_trigger and soxl['direction'] == 'DOWN':
                    should_exit = True
                    exit_reason = "TREND_REVERSE"

                if should_exit:
                    trades.append({
                        'symbol': 'SOXL',
                        'action': 'SELL',
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'entry_time': entry_date,
                        'exit_time': soxl['date'],
                        'pnl_pct': pnl_pct,
                        'result': 'WIN' if pnl_pct > 0 else 'LOSS',
                        'reason': exit_reason,
                        'signal': 'BEAR'
                    })

                    # SOXS로 전환
                    position = 'SOXS'
                    entry_price = soxs['close']
                    entry_date = soxs['date']
                    entry_idx = i
                    trades.append({
                        'symbol': 'SOXS',
                        'action': 'BUY',
                        'price': entry_price,
                        'time': entry_date,
                        'signal': 'BEAR'
                    })

            elif position == 'SOXS':
                current_price = soxs['close']
                pnl_pct = (current_price - entry_price) / entry_price * 100
                days_held = i - entry_idx

                should_exit = False
                exit_reason = ""

                if pnl_pct >= take_profit:
                    should_exit = True
                    exit_reason = "TAKE_PROFIT"
                elif pnl_pct <= stop_loss:
                    should_exit = True
                    exit_reason = "STOP_LOSS"
                elif days_held >= holding_days:
                    should_exit = True
                    exit_reason = "TIME_LIMIT"
                elif soxl['consecutive_days'] >= consecutive_trigger and soxl['direction'] == 'UP':
                    should_exit = True
                    exit_reason = "TREND_REVERSE"

                if should_exit:
                    trades.append({
                        'symbol': 'SOXS',
                        'action': 'SELL',
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'entry_time': entry_date,
                        'exit_time': soxs['date'],
                        'pnl_pct': pnl_pct,
                        'result': 'WIN' if pnl_pct > 0 else 'LOSS',
                        'reason': exit_reason,
                        'signal': 'BULL'
                    })

                    # SOXL로 전환
                    position = 'SOXL'
                    entry_price = soxl['close']
                    entry_date = soxl['date']
                    entry_idx = i
                    trades.append({
                        'symbol': 'SOXL',
                        'action': 'BUY',
                        'price': entry_price,
                        'time': entry_date,
                        'signal': 'BULL'
                    })

    return trades

# ============================================================================
# 4단계: 최고 전략 찾기
# ============================================================================

def find_best_strategies(results: List[Dict]) -> List[Dict]:
    """승률 70%+ 또는 복리 100%+ 전략 찾기"""
    print(f"\n[4단계] 최고 전략 찾기")

    # 필터링: 최소 거래 20건, 승률 50%+, 복리 양수
    filtered = [r for r in results
                if r['trades'] >= 20
                and r['win_rate'] >= 50
                and r['compound'] > 0]

    print(f"  필터링 후: {len(filtered)}개 전략")

    # 정렬: 복리 높은 순
    sorted_by_compound = sorted(filtered, key=lambda x: x['compound'], reverse=True)

    # 정렬: 승률 높은 순
    sorted_by_winrate = sorted(filtered, key=lambda x: x['win_rate'], reverse=True)

    print(f"\n  [TOP 10] 복리 최대화 전략:")
    for i, r in enumerate(sorted_by_compound[:10], 1):
        print(f"    {i}. 보유{r['holding_days']}일 익절+{r['take_profit']}% 손절{r['stop_loss']}% 연속{r['consecutive']}일")
        print(f"       거래{r['trades']}건, 승률{r['win_rate']:.1f}%, 복리{r['compound']:+.1f}%\n")

    print(f"\n  [TOP 10] 승률 최대화 전략:")
    for i, r in enumerate(sorted_by_winrate[:10], 1):
        print(f"    {i}. 보유{r['holding_days']}일 익절+{r['take_profit']}% 손절{r['stop_loss']}% 연속{r['consecutive']}일")
        print(f"       거래{r['trades']}건, 승률{r['win_rate']:.1f}%, 복리{r['compound']:+.1f}%\n")

    return sorted_by_compound[:10]

# ============================================================================
# 5단계: 학습 데이터 생성
# ============================================================================

def generate_learning_data(soxl_patterns: List[Dict],
                          soxs_patterns: List[Dict],
                          best_strategy: Dict) -> List[Dict]:
    """최고 전략으로 학습 데이터 생성"""
    print(f"\n[5단계] 학습 데이터 생성")
    print(f"  전략: 보유{best_strategy['holding_days']}일 "
          f"익절+{best_strategy['take_profit']}% "
          f"손절{best_strategy['stop_loss']}% "
          f"연속{best_strategy['consecutive']}일")

    trades = simulate_strategy(
        soxl_patterns,
        soxs_patterns,
        holding_days=best_strategy['holding_days'],
        take_profit=best_strategy['take_profit'],
        stop_loss=best_strategy['stop_loss'],
        consecutive_trigger=best_strategy['consecutive']
    )

    print(f"  [OK] {len(trades)}건 학습 데이터 생성")
    return trades

# ============================================================================
# 메인 실행
# ============================================================================

def main():
    # 1. 데이터 수집
    soxl_data = fetch_daily_data('SOXL', days=365)
    soxs_data = fetch_daily_data('SOXS', days=365)

    if not soxl_data or not soxs_data:
        print("\n[ERROR] 데이터 수집 실패")
        return

    # 2. 가격 패턴 분석
    soxl_patterns = analyze_pure_price_patterns(soxl_data)
    soxs_patterns = analyze_pure_price_patterns(soxs_data)

    # 3. 모든 전략 백테스트
    all_results = backtest_all_strategies(soxl_patterns, soxs_patterns)

    # 4. 최고 전략 찾기
    best_strategies = find_best_strategies(all_results)

    if not best_strategies:
        print("\n[ERROR] 승률 50%+ 전략 없음")
        return

    # 5. 학습 데이터 생성 (1위 전략 사용)
    learning_trades = generate_learning_data(soxl_patterns, soxs_patterns, best_strategies[0])

    # 6. 저장
    print(f"\n[6단계] 파일 저장")

    with open('kis_trade_history.json', 'w', encoding='utf-8') as f:
        json.dump(learning_trades, f, indent=2, ensure_ascii=False)
    print(f"  [OK] kis_trade_history.json 저장 ({len(learning_trades)}건)")

    # 메타 인사이트
    completed = [t for t in learning_trades if t.get('action') == 'SELL']
    wins = [t for t in completed if t['result'] == 'WIN']
    losses = [t for t in completed if t['result'] == 'LOSS']

    meta_insights = [{
        'type': 'ULTIMATE_BACKTEST',
        'strategy': best_strategies[0],
        'total_trades': len(completed),
        'wins': len(wins),
        'losses': len(losses),
        'win_rate_pct': len(wins) / len(completed) * 100 if completed else 0,
        'avg_win_pct': sum(t['pnl_pct'] for t in wins) / len(wins) if wins else 0,
        'avg_loss_pct': sum(t['pnl_pct'] for t in losses) / len(losses) if losses else 0,
        'generated': datetime.now().isoformat()
    }]

    with open('kis_meta_insights.json', 'w', encoding='utf-8') as f:
        json.dump(meta_insights, f, indent=2, ensure_ascii=False)
    print(f"  [OK] kis_meta_insights.json 저장")

    print("\n" + "="*80)
    print("[COMPLETE] 궁극의 학습 데이터 생성 완료!")
    print("="*80)
    print(f"\n최고 전략 적용됨:")
    print(f"  보유 기간: {best_strategies[0]['holding_days']}일")
    print(f"  익절: +{best_strategies[0]['take_profit']}%")
    print(f"  손절: {best_strategies[0]['stop_loss']}%")
    print(f"  추세전환: 연속 {best_strategies[0]['consecutive']}일")
    print(f"  승률: {best_strategies[0]['win_rate']:.1f}%")
    print(f"  복리: {best_strategies[0]['compound']:+.1f}%")
    print("\n이제 kis_llm_trader.py를 재시작하세요!")
    print("="*80)

if __name__ == "__main__":
    main()
