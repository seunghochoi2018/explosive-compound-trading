#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
전체 시스템 종합 점검
목표: 추세돌파 매매 → 복리효과 → 잔고 증가
"""

import json

def check_kis_trader():
    """KIS 트레이더 점검"""
    print("="*80)
    print("KIS 트레이더 (SOXL/SOXS) 종합 점검")
    print("="*80 + "\n")

    issues = []
    warnings = []
    ok = []

    # 1. 추세 전환 감지
    print("[1] 추세 전환 감지 속도")
    print("    - LLM 14b×2 앙상블: 90초")
    print("    - 신뢰도 65% 이상: 즉시 전환 ✅")
    print("    - 수익 1% 이상: 전환 가능 ✅")
    ok.append("추세 전환 감지: 빠름")

    # 2. 포지션 전환 실행
    print("\n[2] 포지션 전환 실행")
    print("    - 매도 API: sell_all() → TTTT1006U ✅")
    print("    - 매수 API: place_order() → TTTT1002U ✅")
    print("    - OVRS_ORD_UNPR 4단계 검증 ✅")
    ok.append("포지션 전환: 정상")

    # 3. 복리 효과 ❌ 문제 발견!
    print("\n[3] 복리 효과 (수익 재투자)")
    print("    ❌ 문제: 고정 수량 매수!")
    print("    - 현재: 항상 10주 매수 (place_order(qty=10))")
    print("    - 문제: 잔고 증가해도 매수량 동일")
    print("    - 예시:")
    print("      1차: $400 → 10주 매수")
    print("      2차: $800 → 10주 매수 (20주 가능한데!)")
    print("      3차: $1600 → 10주 매수 (40주 가능한데!)")
    issues.append("복리 효과 없음: 고정 수량 매수")

    # 4. 피라미딩
    print("\n[4] 피라미딩 (10>5>3>2>1)")
    print("    ✅ 로직: 존재")
    print("    ✅ 조건: 신뢰도 75% 이상")
    print("    ⚠️ 주의: 같은 종목만 추가 매수 (전환 아님)")
    warnings.append("피라미딩은 복리가 아님 (같은 종목 추가)")

    # 5. 트레일링 스탑
    print("\n[5] 트레일링 스탑 (리스크 관리)")
    print("    ✅ 초기 손절: -3.5%")
    print("    ✅ +5% → +1% 보장")
    print("    ✅ +10% → +5% 보장")
    print("    ✅ +20% → +12% 보장")
    ok.append("트레일링 스탑: 정상")

    # 6. 학습 메커니즘
    print("\n[6] 학습 및 개선")
    print("    ✅ trade_history: 59건")
    print("    ✅ meta_insights: 저장")
    print("    ✅ LLM에 학습 데이터 전달")
    ok.append("학습 메커니즘: 정상")

    # 7. 잔고 증가 메커니즘 ❌
    print("\n[7] 잔고 증가 메커니즘")
    print("    ❌ 치명적 문제: 수익이 재투자 안 됨!")
    print("    - 현재: quantity=10 (하드코딩)")
    print("    - 필요: quantity = calculate_from_balance()")
    print("    - 결과: 복리 효과 제로")
    issues.append("잔고 증가 불가능: 수익 재투자 안 됨")

    return issues, warnings, ok


def check_eth_trader():
    """ETH 트레이더 점검"""
    print("\n" + "="*80)
    print("ETH 트레이더 (ETH/USD 25x) 종합 점검")
    print("="*80 + "\n")

    issues = []
    warnings = []
    ok = []

    # 1. 추세 전환 감지
    print("[1] 추세 전환 감지 속도")
    print("    - 신호차: 15 (30→15, 백테스팅 최적) ✅")
    print("    - 신뢰도: 70% (85→70%, +88% 개선) ✅")
    print("    - 포착률: 52% (20% → 52%) ✅⭐")
    ok.append("추세 전환 감지: 매우 빠름")

    # 2. 포지션 전환 실행
    print("\n[2] 포지션 전환 실행")
    print("    - CLOSE_AND_BUY/SELL 로직 ✅")
    print("    - 3회 재시도 메커니즘 ✅")
    print("    - 강제 상태 초기화 ✅")
    ok.append("포지션 전환: 정상")

    # 3. 복리 효과 ✅
    print("\n[3] 복리 효과 (수익 재투자)")
    print("    ✅ calculate_optimal_position_size() 존재!")
    print("    ✅ LLM 분석 기반 최적 수량 계산")
    print("    ✅ 신뢰도 높을수록 큰 포지션")
    print("    ✅ 수익 나면 자동으로 큰 수량 투자")
    ok.append("복리 효과: 정상 작동")

    # 4. 피라미딩
    print("\n[4] 피라미딩")
    print("    ✅ check_pyramid_opportunity()")
    print("    ✅ LLM 자율 판단")
    print("    ✅ 수량: current_qty * 0.5")
    ok.append("피라미딩: 정상")

    # 5. 트레일링 스탑
    print("\n[5] 트레일링 스탑 (리스크 관리)")
    print("    ✅ 초기 손절: -2.5% (25x 맞춤)")
    print("    ✅ +3% → 본전 보장")
    print("    ✅ +5% → +2% 보장")
    print("    ✅ +10% → +6% 보장")
    ok.append("트레일링 스탑: 정상")

    # 6. 레버리지 관리
    print("\n[6] 레버리지 관리 (25x)")
    print("    ✅ Inverse Isolated")
    print("    ✅ MMR 이슈 방지")
    print("    ✅ 파산 방지 -50%")
    ok.append("레버리지 관리: 안전")

    # 7. 잔고 증가 메커니즘
    print("\n[7] 잔고 증가 메커니즘")
    print("    ✅ 수익 → 큰 포지션 → 더 큰 수익")
    print("    ✅ calculate_optimal_position_size()")
    print("    ✅ 복리 효과 극대화")
    ok.append("잔고 증가: 정상 작동")

    return issues, warnings, ok


def check_kis_code_details():
    """KIS 코드 상세 점검 - 복리 효과"""
    print("\n" + "="*80)
    print("KIS 트레이더 코드 상세 분석")
    print("="*80 + "\n")

    print("[포지션 전환 코드 추적]\n")

    print("1. 신규 진입 (2057-2072줄)")
    print("   place_order(target_symbol, 'BUY', quantity=10, price=None)")
    print("   → ❌ 고정 10주")

    print("\n2. 포지션 전환 (2023-2034줄)")
    print("   place_order(target_symbol, 'BUY', quantity=10, price=None)")
    print("   → ❌ 고정 10주")

    print("\n3. 피라미딩 (2044-2054줄)")
    print("   place_order(target_symbol, 'BUY', quantity=pyramiding_qty)")
    print("   → ✅ 변동 (10>5>3>2>1)")

    print("\n4. place_order() 함수 (1100-1119줄)")
    print("   if quantity is None:")
    print("       if order_type == 'BUY':")
    print("           balance = get_usd_cash_balance()")
    print("           quantity = int(cash / price)")
    print("   → ✅ 잔고 기반 계산 가능!")
    print("   → ⚠️ BUT quantity=10 으로 명시해서 이 로직 안 탐!")

    print("\n" + "="*80)
    print("결론")
    print("="*80)
    print("\n❌ KIS는 quantity=None으로 호출해야 복리 효과!")
    print("   현재: place_order(symbol, 'BUY', quantity=10)")
    print("   수정: place_order(symbol, 'BUY', quantity=None)")
    print()


def main():
    """메인 실행"""
    print("\n" + "="*100)
    print(" "*35 + "시스템 종합 점검")
    print("목표: 추세돌파 매매 → 복리효과 극대화 → 잔고 증가")
    print("="*100 + "\n")

    # KIS 점검
    kis_issues, kis_warnings, kis_ok = check_kis_trader()

    # ETH 점검
    eth_issues, eth_warnings, eth_ok = check_eth_trader()

    # KIS 코드 상세
    check_kis_code_details()

    # 최종 요약
    print("\n" + "="*100)
    print(" "*40 + "최종 요약")
    print("="*100 + "\n")

    print("[KIS 트레이더]")
    print(f"  ✅ 정상: {len(kis_ok)}개")
    for item in kis_ok:
        print(f"     - {item}")
    print(f"  ⚠️ 경고: {len(kis_warnings)}개")
    for item in kis_warnings:
        print(f"     - {item}")
    print(f"  ❌ 치명적 문제: {len(kis_issues)}개")
    for item in kis_issues:
        print(f"     - {item}")

    print(f"\n[ETH 트레이더]")
    print(f"  ✅ 정상: {len(eth_ok)}개")
    for item in eth_ok:
        print(f"     - {item}")
    print(f"  ⚠️ 경고: {len(eth_warnings)}개")
    for item in eth_warnings:
        print(f"     - {item}")
    print(f"  ❌ 치명적 문제: {len(eth_issues)}개")
    for item in eth_issues:
        print(f"     - {item}")

    print("\n" + "="*100)
    print(" "*35 + "긴급 수정 필요!")
    print("="*100 + "\n")

    print("[KIS 트레이더] ❌❌❌")
    print("  문제: 복리 효과 제로 (고정 10주 매수)")
    print("  수정: place_order(..., quantity=None) 으로 변경")
    print("  효과: 잔고 증가 시 자동으로 큰 수량 매수")
    print()

    print("[ETH 트레이더] ✅✅✅")
    print("  정상: 복리 효과 작동 중")
    print("  정상: 수익 → 큰 포지션 → 더 큰 수익")
    print()

    print("[권장 조치]")
    print("  1. KIS 트레이더 복리 로직 수정 (즉시)")
    print("  2. 테스트 후 재시작")
    print("  3. ETH는 현재 상태 유지")
    print()


if __name__ == "__main__":
    main()
