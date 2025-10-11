#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
포지션 전환을 가로막는 모든 조건 점검
"""

print("="*80)
print("포지션 전환 차단 조건 분석")
print("="*80 + "\n")

print("[KIS 트레이더] 포지션 전환 차단 조건\n")

blocking_conditions = {
    "KIS": [
        {
            "위치": "kis_llm_auto_trader.py:1914",
            "조건": "confidence < self.min_confidence",
            "값": "confidence < 40%",
            "설명": "신뢰도 40% 미만이면 거래 자체를 안 함",
            "차단 위험": " 중간"
        },
        {
            "위치": "kis_llm_auto_trader.py:1952",
            "조건": "confidence >= 65",
            "값": "신뢰도 65% 이상이어야 즉시 전환",
            "설명": "수익 중일 때 신뢰도 65% 이상이면 전환",
            "차단 위험": " 낮음 (방금 수정함)"
        },
        {
            "위치": "kis_llm_auto_trader.py:1961",
            "조건": "current_pnl_pct >= 1.0",
            "값": "수익 1% 이상이어야 전환 (신뢰도 낮을 때)",
            "설명": "신뢰도 낮으면 수익 1% 이상 있어야 전환",
            "차단 위험": " 낮음"
        },
        {
            "위치": "kis_llm_auto_trader.py:1972-1976",
            "조건": "수익 < 1% AND 신뢰도 < 65%",
            "값": "둘 다 낮으면 대기",
            "설명": "노이즈 필터 - 약한 신호는 무시",
            "차단 위험": " 중간 (하지만 필요한 필터)"
        },
        {
            "위치": "kis_llm_auto_trader.py:1927",
            "조건": "pyramiding_qty is not None",
            "값": "피라미딩 로직이 우선",
            "설명": "같은 종목 보유 중이면 전환 대신 피라미딩 체크",
            "차단 위험": " 낮음 (피라미딩은 신뢰도 75% 필요)"
        },
        {
            "위치": "kis_llm_auto_trader.py:1931",
            "조건": "current_pnl_pct < self.trailing_stop_loss",
            "값": "트레일링 스탑 발동",
            "설명": "손절선 발동 시 강제 청산 (전환 아님)",
            "차단 위험": " 없음 (트레일링 스탑 = 백업)"
        }
    ],
    "ETH": [
        {
            "위치": "llm_eth_trader_v3_ensemble.py:1608",
            "조건": "confidence < self.min_confidence",
            "값": "confidence < 80%",
            "설명": "신뢰도 80% 미만이면 신규 진입 안 함",
            "차단 위험": " 높음 (진입만 차단, 전환은 별도)"
        },
        {
            "위치": "llm_eth_trader_v3_ensemble.py:1568-1571",
            "조건": "signal_diff >= 30 AND confidence >= 85",
            "값": "신호차 30 이상 + 신뢰도 85% 이상",
            "설명": "추세 전환 조건 (둘 다 충족 필요)",
            "차단 위험": " 매우 높음!"
        },
        {
            "위치": "llm_eth_trader_v3_ensemble.py:1791",
            "조건": "pnl_pct < self.trailing_stop_loss",
            "값": "트레일링 스탑 -2.5%",
            "설명": "손절선 발동 시 강제 청산",
            "차단 위험": " 없음 (백업)"
        },
        {
            "위치": "llm_eth_trader_v3_ensemble.py:731",
            "조건": "pnl <= -50.0",
            "값": "파산 방지 -50%",
            "설명": "파산 방지 긴급 청산",
            "차단 위험": " 없음 (극한 상황)"
        }
    ]
}

for trader, conditions in blocking_conditions.items():
    print(f"\n{'='*80}")
    print(f"{trader} 트레이더")
    print(f"{'='*80}\n")

    for i, cond in enumerate(conditions, 1):
        print(f"[{i}] {cond['조건']}")
        print(f"    위치: {cond['위치']}")
        print(f"    값: {cond['값']}")
        print(f"    설명: {cond['설명']}")
        print(f"    차단 위험: {cond['차단 위험']}")
        print()

print("\n" + "="*80)
print("결론 및 권장 사항")
print("="*80 + "\n")

print("[KIS 트레이더]")
print("   추세 전환 로직: 양호 (방금 개선됨)")
print("   min_confidence=40% 유지 (너무 낮추면 노이즈)")
print("   신뢰도 65% → 즉시 전환 (빠른 반응)")
print()

print("[ETH 트레이더]")
print("   문제: MIN_REVERSAL_DIFF=30, CONFIDENCE=85 너무 높음!")
print("   추세 전환이 거의 안 일어날 수 있음")
print("   백테스팅 필요: 최적값 찾기")
print()

print("[백테스팅 대상 파라미터]")
print("  1. KIS min_confidence: 현재 40% (30~50% 범위 테스트)")
print("  2. KIS 전환 신뢰도: 현재 65% (60~70% 범위 테스트)")
print("  3. ETH MIN_REVERSAL_DIFF: 현재 30 (15~35 범위 테스트)")
print("  4. ETH MIN_REVERSAL_CONFIDENCE: 현재 85% (70~85% 범위 테스트)")
print()

print("[ 트레일링 스탑은 건들지 않음]")
print("  KIS: -3.5% (백테스팅 완료)")
print("  ETH: -2.5% (25x 레버리지 맞춤)")
print()
