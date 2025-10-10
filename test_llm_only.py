#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 듀얼 모델 앙상블 단독 테스트 (API 없이)
"""

from llm_market_analyzer import LLMMarketAnalyzer

print("=" * 70)
print("LLM 듀얼 모델 앙상블 테스트")
print("=" * 70)

# LLM 분석기 초기화
analyzer = LLMMarketAnalyzer()

# 가상의 시장 데이터 (실제 가격 대신 시뮬레이션)
test_scenarios = [
    {
        "name": "강한 상승 추세",
        "data": {
            'soxl_price': 25.50,
            'soxs_price': 8.20,
            'change_1m': 1.2,   # 1분: +1.2%
            'change_5m': 3.5,   # 5분: +3.5%
            'change_15m': 5.8,  # 15분: +5.8%
            'current_position': 'NONE',
            'position_pnl': 0
        }
    },
    {
        "name": "강한 하락 추세",
        "data": {
            'soxl_price': 24.80,
            'soxs_price': 8.50,
            'change_1m': -1.5,
            'change_5m': -3.2,
            'change_15m': -4.5,
            'current_position': 'NONE',
            'position_pnl': 0
        }
    },
    {
        "name": "횡보 (추세 없음)",
        "data": {
            'soxl_price': 25.20,
            'soxs_price': 8.30,
            'change_1m': 0.1,
            'change_5m': -0.2,
            'change_15m': 0.3,
            'current_position': 'NONE',
            'position_pnl': 0
        }
    },
    {
        "name": "SOXL 보유 중 수익",
        "data": {
            'soxl_price': 26.00,
            'soxs_price': 8.10,
            'change_1m': 0.5,
            'change_5m': 1.2,
            'change_15m': 2.0,
            'current_position': 'SOXL',
            'position_pnl': 3.5  # +3.5% 수익
        }
    }
]

for scenario in test_scenarios:
    print(f"\n{'=' * 70}")
    print(f"시나리오: {scenario['name']}")
    print(f"{'=' * 70}")

    data = scenario['data']
    print(f"\n[시장 데이터]")
    print(f"SOXL: ${data['soxl_price']:.2f}")
    print(f"SOXS: ${data['soxs_price']:.2f}")
    print(f"1분 변화: {data['change_1m']:+.2f}%")
    print(f"5분 변화: {data['change_5m']:+.2f}%")
    print(f"15분 변화: {data['change_15m']:+.2f}%")
    print(f"현재 포지션: {data['current_position']}")
    print(f"포지션 수익률: {data['position_pnl']:+.2f}%")

    # LLM 듀얼 모델 분석
    print(f"\n[LLM 분석 시작...]")
    result = analyzer.analyze_with_dual_models(data)

    print(f"\n[결과]")
    print(f"신호: {result.get('signal', 'N/A')}")
    print(f"신뢰도: {result.get('confidence', 0):.0f}%")
    print(f"거래 여부: {'예' if result.get('trade') else '아니오'}")

    if not result.get('trade'):
        print(f"사유: 모델 간 합의 부족 또는 신뢰도 낮음")

print(f"\n{'=' * 70}")
print("테스트 완료!")
print("=" * 70)
print(f"\n[학습 현황]")
print(f"총 거래 학습: {len(analyzer.trade_history)}건")
print(f"승률: {analyzer.win_rate:.1f}%")
