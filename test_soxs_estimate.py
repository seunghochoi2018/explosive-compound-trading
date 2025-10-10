#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SOXS 가격 추정 테스트
"""

# SOXL 보유 시 SOXS 가격 추정
soxl_price = 39.07
soxs_estimate = soxl_price * 0.3

print("="*80)
print("SOXS 가격 추정 테스트")
print("="*80)
print(f"\nSOXL 현재가: ${soxl_price:.2f}")
print(f"SOXS 추정가: ${soxs_estimate:.2f}")
print(f"\n이제 LLM이 두 가격을 비교하여 트렌드 분석을 할 수 있습니다!")
print("="*80)
