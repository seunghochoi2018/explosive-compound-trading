#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
패턴 학습 적용 시스템 (KIS 버전)

핵심 원칙:
1. 승률 60% 미만 패턴은 절대 거래 금지
2. 실제 USD 잔고 변화만 학습
3. 학습할수록 승률 상승
4. 거래할수록 잔고 증가
"""
import json
from pathlib import Path
from pattern_reinforcement_learning_kis import PatternReinforcementLearning

def apply_pattern_adjustment(current_market: dict, base_confidence: float) -> tuple:
    """
    패턴 기반 신뢰도 조정 적용

    Args:
        current_market: 현재 시장 데이터
        base_confidence: LLM이 반환한 기본 신뢰도

    Returns:
        (조정된 신뢰도, 설명, 거래 허용 여부)
    """
    # 최소 거래 수 확인
    trade_file = Path(r"C:\Users\user\Documents\코드4\kis_trade_history.json")
    if not trade_file.exists():
        return (base_confidence, "초기 거래 (학습 데이터 없음)", True)

    with open(trade_file, 'r', encoding='utf-8') as f:
        trades = json.load(f)

    # 최소 100건 이상부터 패턴 학습 적용
    if len(trades) < 100:
        return (base_confidence, f"학습 준비 중 ({len(trades)}/100건)", True)

    # 강화학습 시스템 초기화
    learner = PatternReinforcementLearning(str(trade_file))

    # 패턴 학습 (매 거래마다 갱신)
    learner.learn_from_all_trades()

    # 현재 패턴의 신뢰도 조정값 가져오기
    adjustment, explanation = learner.get_confidence_adjustment(current_market)

    # 조정값 적용
    adjusted_confidence = base_confidence + adjustment
    adjusted_confidence = max(0, min(100, adjusted_confidence))  # 0-100 범위

    # 승률 기반 거래 허용 여부 결정
    pattern_key = learner.extract_pattern_features(current_market)
    patterns = learner.pattern_db.get("patterns", {})

    allow_trade = True
    if pattern_key in patterns:
        pattern_data = patterns[pattern_key]
        win_rate = pattern_data.get("win_rate", 0)
        total = pattern_data.get("total_trades", 0)

        # 🚨 핵심: 승률 60% 미만 패턴은 절대 거래 금지!
        if total >= 10 and win_rate < 60:
            allow_trade = False
            explanation += f" | 🚨 승률 {win_rate}% < 60% → 거래 금지!"
        elif total >= 10:
            explanation += f" | ✅ 승률 {win_rate}% ≥ 60% → 거래 허용"

    return (adjusted_confidence, explanation, allow_trade)

if __name__ == "__main__":
    # 테스트
    test_market = {
        "market_1m_trend": "up",
        "market_5m_trend": "up",
        "llm_confidence": 70,
        "volume_surge": True,
        "breakout": False
    }

    conf, exp, allow = apply_pattern_adjustment(test_market, 70)
    print(f"기본 신뢰도: 70")
    print(f"조정 신뢰도: {conf}")
    print(f"설명: {exp}")
    print(f"거래 허용: {allow}")
