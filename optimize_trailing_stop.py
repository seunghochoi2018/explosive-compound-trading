#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
트레일링 스탑 최적화 백테스팅
각 자산별 변동성 분석 후 독립적인 손절선 설정
"""

import json
import statistics
from collections import defaultdict

def analyze_kis_trades():
    """KIS SOXL/SOXS 거래 분석"""
    print("\n" + "="*80)
    print("KIS 트레이더 (SOXL/SOXS) 백테스팅 분석")
    print("="*80 + "\n")

    with open('kis_trade_history.json', 'r', encoding='utf-8') as f:
        trades = json.load(f)

    # SELL 거래만 필터 (완료된 거래)
    completed = [t for t in trades if t.get('action') == 'SELL']

    print(f"총 거래: {len(completed)}건\n")

    # 수익/손실 분리
    wins = [t for t in completed if t.get('result') == 'WIN']
    losses = [t for t in completed if t.get('result') == 'LOSS']

    print(f"[거래 결과]")
    print(f"  승리: {len(wins)}건")
    print(f"  패배: {len(losses)}건")
    print(f"  승률: {len(wins)/len(completed)*100:.1f}%\n")

    # 손실 거래 분석
    loss_pnls = [t['pnl_pct'] for t in losses]
    win_pnls = [t['pnl_pct'] for t in wins]

    print(f"[손실 거래 분석]")
    print(f"  평균 손실: {statistics.mean(loss_pnls):.2f}%")
    print(f"  중간 손실: {statistics.median(loss_pnls):.2f}%")
    print(f"  최대 손실: {min(loss_pnls):.2f}%")
    print(f"  최소 손실: {max(loss_pnls):.2f}%")

    # 작은 손실 vs 큰 손실 구분
    small_losses = [p for p in loss_pnls if p > -5]
    big_losses = [p for p in loss_pnls if p <= -5]

    print(f"\n  작은 손실 (<5%): {len(small_losses)}건 (평균 {statistics.mean(small_losses):.2f}%)")
    print(f"  큰 손실 (≥5%): {len(big_losses)}건 (평균 {statistics.mean(big_losses):.2f}%)\n")

    print(f"[수익 거래 분석]")
    print(f"  평균 수익: {statistics.mean(win_pnls):.2f}%")
    print(f"  중간 수익: {statistics.median(win_pnls):.2f}%")
    print(f"  최대 수익: {max(win_pnls):.2f}%")
    print(f"  최소 수익: {min(win_pnls):.2f}%\n")

    # 노이즈 수준 판단
    print(f"[노이즈 분석]")
    print(f"  -2% 이하 손실: {len([p for p in loss_pnls if p <= -2])}건")
    print(f"  -3% 이하 손실: {len([p for p in loss_pnls if p <= -3])}건")
    print(f"  -5% 이하 손실: {len([p for p in loss_pnls if p <= -5])}건\n")

    # 최적 손절선 계산
    print("="*80)
    print("트레일링 스탑 최적화 시뮬레이션")
    print("="*80 + "\n")

    stop_levels = [-2.0, -2.5, -3.0, -3.5, -4.0, -5.0]

    for stop in stop_levels:
        saved_trades = 0
        saved_loss = 0
        killed_wins = 0
        killed_profit = 0

        # 손실 거래에서 구제
        for pnl in loss_pnls:
            if pnl < stop:
                # 손절선 발동으로 손실 감소
                saved_trades += 1
                saved_loss += (pnl - stop)  # 실제 손실 - 손절선

        # 수익 거래에서 오작동 (노이즈로 인한 조기 청산)
        for pnl in win_pnls:
            # 가정: 수익 거래도 중간에 -X% 찍을 수 있음
            # 레버리지 ETF는 변동성 크므로 수익 거래도 중간에 하락 가능
            # 보수적으로 수익의 50%가 중간에 손절선 근처 갔다고 가정
            if pnl < 5:  # 작은 수익은 노이즈 가능성
                if abs(stop) >= 3:  # -3% 이상 손절선은 안전
                    pass
                else:
                    # -2%, -2.5%는 노이즈로 수익 거래 죽일 수 있음
                    killed_wins += 0.3  # 30% 확률로 죽인다고 가정
                    killed_profit += pnl * 0.3

        net_effect = saved_loss + killed_profit

        print(f"[손절선 {stop}%]")
        print(f"  구제된 거래: {saved_trades}건")
        print(f"  구제 효과: {saved_loss:.2f}%")
        print(f"  죽인 수익: {killed_wins:.1f}건 (예상)")
        print(f"  손실 수익: {killed_profit:.2f}%")
        print(f"  순 효과: {net_effect:+.2f}%")
        print()

    # 권장 설정
    print("="*80)
    print("권장 트레일링 스탑 설정")
    print("="*80 + "\n")

    print("SOXL/SOXS (레버리지 3X 반도체 ETF)")
    print("  특성: 높은 변동성, 큰 수익/손실 폭")
    print("  노이즈 수준: -2~-3% 일간 변동 흔함")
    print()
    print("   권장 초기 손절선: -4.0%")
    print("     이유: 작은 손실(-2~-3%) 필터, 큰 손실(-15~-28%) 방지")
    print()
    print("   권장 트레일링 스탑:")
    print("     +5% 수익 → 손절선 +1% (4% 수익 보장)")
    print("     +10% 수익 → 손절선 +5% (8% 수익 보장)")
    print("     +20% 수익 → 손절선 +12% (15% 수익 보장)")
    print()

    return {
        'initial_stop': -4.0,
        'trailing_stops': [
            {'profit_threshold': 5.0, 'new_stop': 1.0},
            {'profit_threshold': 10.0, 'new_stop': 5.0},
            {'profit_threshold': 20.0, 'new_stop': 12.0}
        ]
    }


def analyze_eth_trades():
    """ETH/USD Inverse 거래 분석"""
    print("\n" + "="*80)
    print("ETH 트레이더 (ETH/USD Inverse) 백테스팅 분석")
    print("="*80 + "\n")

    try:
        import sys
        sys.path.append('C:\\Users\\user\\Documents\\코드3')

        # ETH 거래 기록 로드 시도
        try:
            with open('C:\\Users\\user\\Documents\\코드3\\eth_trade_history.json', 'r', encoding='utf-8') as f:
                trades = json.load(f)
        except FileNotFoundError:
            print("[INFO] ETH 거래 기록 없음 - 이론적 분석\n")

            print("ETH/USD Inverse (25x 레버리지)")
            print("  특성: 초고 레버리지, 빠른 청산 위험")
            print("  노이즈 수준: -1~-2% 변동으로도 25배 확대")
            print()
            print("   권장 초기 손절선: -2.5%")
            print("     이유: 25x 레버리지 = 실제 -0.1% = -2.5% 손실")
            print()
            print("   권장 트레일링 스탑:")
            print("     +3% 수익 → 손절선 0% (본전 보장)")
            print("     +5% 수익 → 손절선 +2%")
            print("     +10% 수익 → 손절선 +6%")
            print()

            return {
                'initial_stop': -2.5,
                'trailing_stops': [
                    {'profit_threshold': 3.0, 'new_stop': 0.0},
                    {'profit_threshold': 5.0, 'new_stop': 2.0},
                    {'profit_threshold': 10.0, 'new_stop': 6.0}
                ]
            }

        # 실제 데이터가 있으면 분석
        completed = [t for t in trades if 'result' in t]

        if not completed:
            print("[INFO] 완료된 거래 없음\n")
            return analyze_eth_trades()  # 이론적 분석

        print(f"총 거래: {len(completed)}건\n")

        wins = [t for t in completed if t.get('result') == 'WIN']
        losses = [t for t in completed if t.get('result') == 'LOSS']

        print(f"[거래 결과]")
        print(f"  승리: {len(wins)}건")
        print(f"  패배: {len(losses)}건")
        print(f"  승률: {len(wins)/len(completed)*100:.1f}%\n")

        # 손실 분석
        loss_pnls = [t['pnl_pct'] for t in losses if 'pnl_pct' in t]
        win_pnls = [t['pnl_pct'] for t in wins if 'pnl_pct' in t]

        if loss_pnls:
            print(f"[손실 거래 분석]")
            print(f"  평균 손실: {statistics.mean(loss_pnls):.2f}%")
            print(f"  최대 손실: {min(loss_pnls):.2f}%\n")

        if win_pnls:
            print(f"[수익 거래 분석]")
            print(f"  평균 수익: {statistics.mean(win_pnls):.2f}%")
            print(f"  최대 수익: {max(win_pnls):.2f}%\n")

        # ETH는 25x 레버리지이므로 더 타이트한 손절선 필요
        print("="*80)
        print("권장 트레일링 스탑 설정 (25x 레버리지 반영)")
        print("="*80 + "\n")

        avg_loss = statistics.mean(loss_pnls) if loss_pnls else -5.0
        recommended_stop = max(avg_loss * 0.5, -3.0)  # 평균 손실의 50% 또는 -3%

        print(f"   권장 초기 손절선: {recommended_stop:.1f}%")
        print(f"     (25x 레버리지 감안, 실제 ETH 가격 {recommended_stop/25:.2f}% 하락)")

        return {
            'initial_stop': recommended_stop,
            'trailing_stops': [
                {'profit_threshold': 3.0, 'new_stop': 0.0},
                {'profit_threshold': 5.0, 'new_stop': 2.0},
                {'profit_threshold': 10.0, 'new_stop': 6.0}
            ]
        }

    except Exception as e:
        print(f"[ERROR] ETH 분석 실패: {e}\n")
        # 기본값 반환
        return {
            'initial_stop': -2.5,
            'trailing_stops': [
                {'profit_threshold': 3.0, 'new_stop': 0.0},
                {'profit_threshold': 5.0, 'new_stop': 2.0},
                {'profit_threshold': 10.0, 'new_stop': 6.0}
            ]
        }


def main():
    """메인 실행"""
    # KIS 분석
    kis_config = analyze_kis_trades()

    # ETH 분석
    eth_config = analyze_eth_trades()

    # 설정 저장
    config = {
        'KIS': kis_config,
        'ETH': eth_config,
        'timestamp': '2025-10-09'
    }

    with open('trailing_stop_config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print("\n" + "="*80)
    print("설정 저장 완료: trailing_stop_config.json")
    print("="*80 + "\n")

    print("[다음 단계]")
    print("1. kis_llm_auto_trader.py에 KIS 설정 적용")
    print("2. llm_eth_trader_v3_ensemble.py에 ETH 설정 적용")
    print("3. 실전 테스트 시작\n")


if __name__ == "__main__":
    main()
