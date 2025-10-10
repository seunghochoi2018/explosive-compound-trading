#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVDL/NVDQ 향상된 트레이더 테스트
"""

from nvdl_nvdq_enhanced_trader import NVDLNVDQEnhancedTrader

if __name__ == "__main__":
    print("NVDL/NVDQ 향상된 트레이더 테스트 시작")

    try:
        trader = NVDLNVDQEnhancedTrader()

        print("\n한 번의 시장 분석 및 거래 시뮬레이션 수행:")
        trader.analyze_market_and_trade()

        print("\n통계 출력:")
        trader.show_stats()

        print("\n테스트 완료!")

    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()