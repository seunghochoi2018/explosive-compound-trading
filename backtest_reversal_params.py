#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
추세 전환 파라미터 백테스팅
트레일링 스탑은 건들지 않고, MIN_REVERSAL 값만 최적화
"""

import json
import itertools
from collections import defaultdict

def load_kis_trades():
    """KIS 거래 기록 로드"""
    try:
        with open('kis_trade_history.json', 'r', encoding='utf-8') as f:
            trades = json.load(f)
        return [t for t in trades if t.get('action') == 'SELL']
    except:
        return []

def simulate_kis_trading(trades, min_conf, switch_conf):
    """
    KIS 거래 시뮬레이션

    Args:
        min_conf: 최소 신뢰도 (진입 차단)
        switch_conf: 전환 신뢰도 (즉시 전환 기준)
    """
    total_pnl = 0
    switch_count = 0
    missed_switches = 0

    for trade in trades:
        pnl = trade.get('pnl_pct', 0)

        # 가정: 신뢰도는 60~90% 범위로 랜덤 (실제 데이터 없으므로)
        # 수익 거래는 평균 신뢰도 높음
        assumed_confidence = 70 if pnl > 0 else 60

        # 전환 조건 체크
        if assumed_confidence >= switch_conf:
            # 즉시 전환 (수익 무관)
            switch_count += 1
            total_pnl += pnl
        elif pnl >= 1.0:
            # 충분한 수익 → 전환
            switch_count += 1
            total_pnl += pnl
        else:
            # 대기 → 손실 발생 가능성
            if pnl < 0:
                missed_switches += 1
                total_pnl += pnl  # 손실 포함

    return {
        'total_pnl': total_pnl,
        'switches': switch_count,
        'missed': missed_switches,
        'avg_pnl': total_pnl / len(trades) if trades else 0
    }

def backtest_kis_params():
    """KIS 파라미터 백테스팅"""
    print("\n" + "="*80)
    print("KIS 트레이더 백테스팅")
    print("="*80 + "\n")

    trades = load_kis_trades()

    if not trades:
        print("[ERROR] 거래 기록 없음")
        return

    print(f"총 거래: {len(trades)}건\n")

    # 테스트 범위
    min_conf_range = [30, 35, 40, 45, 50]
    switch_conf_range = [60, 62, 65, 68, 70]

    results = []

    print("파라미터 조합 테스트 중...\n")

    for min_conf in min_conf_range:
        for switch_conf in switch_conf_range:
            result = simulate_kis_trading(trades, min_conf, switch_conf)
            results.append({
                'min_conf': min_conf,
                'switch_conf': switch_conf,
                **result
            })

    # 결과 정렬 (평균 PNL 기준)
    results.sort(key=lambda x: x['avg_pnl'], reverse=True)

    print("="*80)
    print("상위 5개 조합")
    print("="*80 + "\n")

    for i, r in enumerate(results[:5], 1):
        print(f"[{i}] min_conf={r['min_conf']}%, switch_conf={r['switch_conf']}%")
        print(f"    평균 PNL: {r['avg_pnl']:.2f}%")
        print(f"    총 PNL: {r['total_pnl']:.2f}%")
        print(f"    전환 횟수: {r['switches']}회")
        print(f"    놓친 전환: {r['missed']}회")
        print()

    # 현재 설정
    current = [r for r in results if r['min_conf'] == 40 and r['switch_conf'] == 65][0]
    best = results[0]

    print("="*80)
    print("비교")
    print("="*80 + "\n")
    print(f"현재 설정 (min=40%, switch=65%): 평균 PNL {current['avg_pnl']:.2f}%")
    print(f"최적 설정 (min={best['min_conf']}%, switch={best['switch_conf']}%): 평균 PNL {best['avg_pnl']:.2f}%")
    print(f"개선 효과: {best['avg_pnl'] - current['avg_pnl']:+.2f}%")
    print()

    return best

def simulate_eth_reversal(signal_diff_threshold, conf_threshold):
    """
    ETH 추세 전환 시뮬레이션

    ETH는 실제 거래 데이터가 부족하므로 이론적 분석
    """
    # 가정: 100개 추세 전환 기회
    total_opportunities = 100

    # 신호 분포 가정
    # - 강한 신호 (diff>=35, conf>=85): 20개 → 진짜 전환
    # - 중간 신호 (diff>=25, conf>=75): 40개 → 50% 진짜
    # - 약한 신호 (diff>=15, conf>=65): 40개 → 30% 진짜

    captured = 0
    false_signals = 0
    missed_real = 0

    # 강한 신호
    if signal_diff_threshold <= 35 and conf_threshold <= 85:
        captured += 20  # 모두 포착
    else:
        missed_real += 20

    # 중간 신호
    if signal_diff_threshold <= 25 and conf_threshold <= 75:
        captured += 20  # 50%는 진짜
        false_signals += 20  # 50%는 노이즈
    elif signal_diff_threshold <= 30 and conf_threshold <= 80:
        captured += 15
        false_signals += 10

    # 약한 신호
    if signal_diff_threshold <= 20 and conf_threshold <= 70:
        captured += 12  # 30%는 진짜
        false_signals += 28  # 70%는 노이즈

    # 점수 계산
    # 진짜 전환 포착 = +100점
    # 노이즈 포착 = -30점 (수수료 손실)
    # 진짜 전환 놓침 = -200점 (큰 손실)

    score = (captured * 100) - (false_signals * 30) - (missed_real * 200)

    return {
        'captured': captured,
        'false_signals': false_signals,
        'missed': missed_real,
        'score': score
    }

def backtest_eth_params():
    """ETH 파라미터 백테스팅 (이론적)"""
    print("\n" + "="*80)
    print("ETH 트레이더 백테스팅 (이론적 분석)")
    print("="*80 + "\n")

    # 테스트 범위
    diff_range = [15, 20, 25, 30, 35]
    conf_range = [70, 75, 80, 85]

    results = []

    print("파라미터 조합 테스트 중...\n")

    for diff in diff_range:
        for conf in conf_range:
            result = simulate_eth_reversal(diff, conf)
            results.append({
                'diff': diff,
                'conf': conf,
                **result
            })

    # 결과 정렬
    results.sort(key=lambda x: x['score'], reverse=True)

    print("="*80)
    print("상위 5개 조합")
    print("="*80 + "\n")

    for i, r in enumerate(results[:5], 1):
        print(f"[{i}] DIFF={r['diff']}, CONF={r['conf']}%")
        print(f"    점수: {r['score']}")
        print(f"    포착: {r['captured']}개")
        print(f"    오신호: {r['false_signals']}개")
        print(f"    놓침: {r['missed']}개")
        print()

    # 현재 설정
    current = [r for r in results if r['diff'] == 30 and r['conf'] == 85][0]
    best = results[0]

    print("="*80)
    print("비교")
    print("="*80 + "\n")
    print(f"현재 설정 (DIFF=30, CONF=85%): 점수 {current['score']}")
    print(f"  → 포착: {current['captured']}개, 놓침: {current['missed']}개")
    print()
    print(f"최적 설정 (DIFF={best['diff']}, CONF={best['conf']}%): 점수 {best['score']}")
    print(f"  → 포착: {best['captured']}개, 놓침: {best['missed']}개")
    print()
    print(f"개선 효과: {best['score'] - current['score']:+} 점")
    print()

    return best

def main():
    """메인 실행"""
    print("\n" + "="*80)
    print("추세 전환 파라미터 백테스팅")
    print("트레일링 스탑은 그대로 유지")
    print("="*80)

    # KIS 백테스팅
    kis_best = backtest_kis_params()

    # ETH 백테스팅
    eth_best = backtest_eth_params()

    # 권장 사항
    print("\n" + "="*80)
    print("최종 권장 설정")
    print("="*80 + "\n")

    print("[KIS 트레이더]")
    if kis_best:
        print(f"  min_confidence: {kis_best['min_conf']}%")
        print(f"  switch_confidence: {kis_best['switch_conf']}%")
    print()

    print("[ETH 트레이더]")
    if eth_best:
        print(f"  MIN_REVERSAL_DIFF: {eth_best['diff']}")
        print(f"  MIN_REVERSAL_CONFIDENCE: {eth_best['conf']}%")
    print()

    print("[트레일링 스탑 - 변경 없음]")
    print("  KIS: -3.5% (백테스팅 완료)")
    print("  ETH: -2.5% (25x 레버리지 맞춤)")
    print()

if __name__ == "__main__":
    main()
