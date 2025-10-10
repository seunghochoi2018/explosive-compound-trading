#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
안전한 신호 알림 테스트 스크립트
"""

import sys
from datetime import datetime

def main():
    """테스트 실행"""
    print("=" * 60)
    print("NVDL/NVDQ Safe Signal Test")
    print("=" * 60)

    try:
        # 모듈 임포트
        from nvdl_nvdq_signal_notifier_final import PureAISignalNotifier

        # API 키
        api_key = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"

        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("Initializing system...")

        # 신호 알림 시스템 생성
        notifier = PureAISignalNotifier(api_key)

        # 간단한 테스트만 수행
        print("\nInitialization complete!")
        print(f"Base learning data: {len(notifier.signal_results)} patterns")

        # 테스트 신호 생성
        print("\nTesting signal generation...")
        for symbol in ['NVDL', 'NVDQ']:
            try:
                signal = notifier.generate_pure_ai_signal(symbol)
                if signal:
                    print(f"  {symbol}: {signal.action} (confidence: {signal.confidence:.1%})")
                else:
                    print(f"  {symbol}: No signal")
            except Exception as e:
                print(f"  {symbol}: Error - {e}")

        print("\nTest completed!")

    except KeyboardInterrupt:
        print("\nUser interrupted")
    except Exception as e:
        print(f"\nTest error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\nEnd Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()