#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SOXS 184주 즉시 매도 (kis_llm_trader 방식 사용)"""
import sys
sys.path.append(r'C:\Users\user\Documents\코드5')
sys.path.append(r'C:\Users\user\Documents\코드4')

from kis_llm_trader_v2_explosive import ExplosiveKISTrader

print("="*80)
print("SOXS 184주 즉시 매도")
print("="*80)

# KIS 트레이더 초기화 (간소화 버전)
trader = ExplosiveKISTrader()

# SOXS 현재가 조회
print("\n[1] SOXS 현재가 조회...")
current_price = trader.get_current_price('SOXS')
print(f"SOXS 현재가: ${current_price:.2f}")

if current_price <= 0:
    print("[ERROR] 가격 조회 실패")
    sys.exit(1)

# SOXS 184주 매도
print(f"\n[2] SOXS 184주 매도 주문 (${current_price:.2f})...")
success = trader.place_order('SOXS', 'SELL', 184, current_price)

if success:
    print("\n" + "="*80)
    print("[SUCCESS] SOXS 184주 매도 주문 성공!")
    print("="*80)
    print(f"  종목: SOXS")
    print(f"  수량: 184주")
    print(f"  가격: ${current_price:.2f}")
    print(f"  총 금액: ${184 * current_price:.2f}")
    print("="*80)
    print("\n한국투자증권 앱에서 주문번호를 확인하세요.")
else:
    print("\n[ERROR] 매도 주문 실패")
    print("수동으로 한국투자증권 앱에서 직접 매도해주세요.")
