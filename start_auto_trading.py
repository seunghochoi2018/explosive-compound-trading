#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVDL/NVDQ 자동매매 간편 실행기
- 24시간 자동매매
- 적응형 거래 주기
- 실시간 학습
"""

import os
import sys
import subprocess
from datetime import datetime

def print_banner():
    """시작 배너"""
    print("=" * 70)
    print(" NVDL/NVDQ 24시간 자동매매 시스템")
    print(" 적응형 거래 주기 + 실시간 학습")
    print(" 미국 장시간 자동 거래")
    print("=" * 70)
    print(" NVDL: 3x 레버리지 NVIDIA ETF (상승 시 수익)")
    print(" NVDQ: 2x 역 레버리지 NASDAQ ETF (하락 시 수익)")
    print(" AI가 시장 상황에 따라 자동 선택")
    print("=" * 70)

def check_files():
    """필요한 파일들 확인"""
    required_files = [
        'full_auto_trading_system.py',
        'nvdl_nvdq_adaptive_auto_trader.py',
        'us_stock_api_manager.py',
        'nvdl_nvdq_data_collector.py',
        'nvdl_nvdq_trading_model.py',
        'telegram_notifier.py'
    ]

    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)

    if missing_files:
        print(f" 누락된 파일: {', '.join(missing_files)}")
        return False

    print(" 모든 파일이 준비되었습니다.")
    return True

def show_trading_frequency_info():
    """거래 주기 정보 안내"""
    print("\n 적응형 거래 주기 시스템:")
    print("   시스템이 자동으로 최적 거래 주기를 찾습니다")
    print("  ⏰ 15분 ~ 24시간 사이에서 동적 조정")
    print("   수익률과 승률을 고려한 최적화")
    print("   실시간 학습으로 지속적 개선")
    print("\n 예상 거래 패턴:")
    print("  • 고변동성: 2-6시간마다 체크, 하루 2-4회 거래")
    print("  • 중간변동성: 4-12시간마다 체크, 하루 1-2회 거래")
    print("  • 저변동성: 8-24시간마다 체크, 2-3일에 1회 거래")
    print("  • 평균적으로 하루 1-3회 포지션 변경 예상")

def get_user_preferences():
    """사용자 설정 입력"""
    print("\n 자동매매 설정:")

    # 거래 모드 선택
    print("\n1⃣ 거래 모드 선택:")
    print("  1. 시뮬레이션 모드 (가상 거래, 안전)")
    print("  2. 실제 거래 모드 (주의 필요)")

    while True:
        mode_choice = input("\n선택 (1-2): ").strip()
        if mode_choice == '1':
            simulation_mode = True
            break
        elif mode_choice == '2':
            print(" 실제 거래 모드는 실제 돈을 사용합니다!")
            confirm = input("정말 실제 거래 모드로 진행하시겠습니까? (yes/no): ").lower()
            if confirm in ['yes', 'y']:
                simulation_mode = False
                break
            else:
                continue
        else:
            print(" 잘못된 선택입니다. 1 또는 2를 입력하세요.")

    # 초기 자금 설정
    if simulation_mode:
        print(f"\n2⃣ 초기 가상 자금 설정:")
        while True:
            try:
                initial_balance = float(input("초기 자금 ($, 기본값 50000): ") or "50000")
                if initial_balance > 0:
                    break
                else:
                    print(" 양수를 입력하세요.")
            except ValueError:
                print(" 숫자를 입력하세요.")
    else:
        initial_balance = 50000  # 실제 거래에서는 실제 계좌 잔고 사용

    # 포지션 크기 설정
    print(f"\n3⃣ 포지션 크기 설정:")
    while True:
        try:
            position_size = float(input("한 번에 거래할 금액 ($, 기본값 2000): ") or "2000")
            if position_size > 0:
                if position_size > initial_balance * 0.5:
                    print(f" 포지션 크기가 초기 자금의 50%를 초과합니다.")
                    confirm = input("계속 진행하시겠습니까? (y/n): ").lower()
                    if confirm in ['y', 'yes']:
                        break
                    else:
                        continue
                else:
                    break
            else:
                print(" 양수를 입력하세요.")
        except ValueError:
            print(" 숫자를 입력하세요.")

    return {
        'simulation_mode': simulation_mode,
        'initial_balance': initial_balance,
        'position_size': position_size
    }

def show_settings_summary(settings):
    """설정 요약 출력"""
    print("\n" + "="*50)
    print(" 설정 요약")
    print("="*50)
    print(f" 모드: {'시뮬레이션' if settings['simulation_mode'] else '실제 거래'}")
    print(f" 초기 자금: ${settings['initial_balance']:,.2f}")
    print(f" 포지션 크기: ${settings['position_size']:,.2f}")
    print(f" 거래 주기: 적응형 (자동 최적화)")
    print(f" 대상: NVDL (롱) / NVDQ (숏)")
    print("="*50)

def run_auto_trading(settings):
    """자동매매 실행"""
    try:
        args = [
            sys.executable,
            'full_auto_trading_system.py',
            '--initial-balance', str(settings['initial_balance']),
            '--position-size', str(settings['position_size'])
        ]

        if settings['simulation_mode']:
            args.append('--simulation')

        print(f"\n 자동매매 시스템 시작...")
        print(f"⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f" 중단하려면 Ctrl+C를 누르세요.")
        print("\n" + "="*70)

        # 자동매매 실행
        subprocess.run(args)

    except KeyboardInterrupt:
        print(f"\n⏹ 사용자에 의한 중단")
    except Exception as e:
        print(f"\n 실행 오류: {e}")

def main():
    """메인 함수"""
    print_banner()

    # 파일 확인
    if not check_files():
        print("\n 필요한 파일들을 먼저 준비해주세요.")
        input("Enter를 눌러 종료...")
        return

    # 거래 주기 정보 안내
    show_trading_frequency_info()

    # 사용자 설정
    print("\n" + "="*70)
    settings = get_user_preferences()

    # 설정 요약
    show_settings_summary(settings)

    # 최종 확인
    print(f"\n 위 설정으로 자동매매를 시작하시겠습니까?")
    if settings['simulation_mode']:
        print(" 시뮬레이션 모드이므로 실제 거래는 발생하지 않습니다.")
    else:
        print(" 실제 거래 모드입니다. 실제 돈이 사용됩니다!")

    final_confirm = input("\n시작하시겠습니까? (y/n): ").lower()

    if final_confirm in ['y', 'yes']:
        run_auto_trading(settings)
    else:
        print(" 자동매매를 취소했습니다.")

    print(f"\n 프로그램 종료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()